"""Historical and forecast links retain GP context without changing identities."""
from html.parser import HTMLParser
import json
from urllib.parse import parse_qs, urlsplit, urljoin
from unittest.mock import patch
import unittest
from streamlit.testing.v1 import AppTest
from pathlib import Path
from pitwall.dashboard import journey, fan_views, pilot_views
from pitwall.i18n import set_language
ROOT=Path(__file__).resolve().parents[1]

class Links(HTMLParser):
    def __init__(self,html):super().__init__();self.links=[];self.feed(html)
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.links.append(dict(attrs))

def params(html):return parse_qs(urlsplit(Links(html).links[0]['href']).query)

class LinkContextTests(unittest.TestCase):
    def tearDown(self):set_language('pt')
    def test_brand_and_observed_podium_keep_historical_context(self):
        for lang in ('pt','en'):
            set_language(lang)
            brand=params(journey.masthead(lang,2024,1))
            self.assertEqual(brand,dict(tela=['Corridas'],lang=[lang],temporada=['2024'],gp=['1']))
            row=dict(id='max_verstappen',name='Max Verstappen',team='Red Bull',position=1)
            link=params(fan_views.podium([row],2024,round_=1))
            self.assertEqual(link['temporada'],['2024']);self.assertEqual(link['gp'],['1'])
            self.assertEqual(link['piloto'],['max_verstappen']);self.assertEqual(link['anos'],['2024'])
            self.assertNotIn('origem_tela',link)

    def test_forecast_podium_retains_strict_origin_for_return(self):
        row=dict(id='hamilton',name='Lewis Hamilton',team='Ferrari',position=2)
        link=params(fan_views.podium([row],2026,compact=True,round_=19))
        self.assertEqual(link['origem_tela'],['Previsões']);self.assertEqual(link['origem_gp'],['19'])

    def test_profile_navigation_preserves_valid_gp_and_rejects_invalid_context(self):
        valid=dict(temporada='2024',gp='1')
        self.assertEqual(pilot_views._navigation_context_params(valid),valid)
        for extra in [dict(gp='01'),dict(gp='0'),dict(gp='25'),dict(temporada='2023')]:
            self.assertEqual(pilot_views._navigation_context_params(dict(valid,**extra)),{})
        with patch.object(pilot_views.st,'query_params',valid):
            html=pilot_views._condition_chips([2024],'win_rate',5,'rain')
        for link in Links(html).links:
            query=parse_qs(urlsplit(link['href']).query)
            self.assertEqual(query['temporada'],['2024']);self.assertEqual(query['gp'],['1'])

    def test_profile_share_roundtrip_preserves_historical_gp(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=45)
        app.query_params.update(tela='Pilotos',visao='perfil',piloto='max_verstappen',anos='2024',temporada='2024',gp='1',lang='en')
        app.run();self.assertFalse(app.exception)
        self.assertEqual(app.query_params.get('temporada'),'2024');self.assertEqual(app.query_params.get('gp'),'1')
        fresh=AppTest.from_file(str(ROOT/'app.py'),default_timeout=45);fresh.query_params.update(**app.query_params);fresh.run();self.assertFalse(fresh.exception)
        self.assertEqual(fresh.selectbox(key='temporada').value,2024);self.assertEqual(fresh.selectbox(key='gp').value,'2024:1')

    def test_missing_profile_is_not_silently_replaced_by_another_driver(self):
        for view in ('perfil','duelo'):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=45)
            query=dict(tela='Pilotos',visao=view,piloto='ryo_hirakawa',anos='2026',temporada='2026',gp='19',lang='en')
            if view=='duelo':query.update(piloto='max_verstappen',rival='ryo_hirakawa')
            app.query_params.update(**query)
            # Exercise the preserved baseline where Hirakawa genuinely has no starts.
            baseline=json.loads((ROOT/'frontend_assets/pilotos_condicoes.json').read_text())
            with patch.object(pilot_views,'load',return_value=baseline):app.run()
            self.assertFalse(app.exception)
            markup='\n'.join(x.value for x in app.markdown)
            self.assertIn('Hirakawa',markup)
            self.assertNotIn('Alexander Albon',markup)
            self.assertTrue(app.info)
            self.assertEqual(app.query_params.get('rival' if view=='duelo' else 'piloto'),'ryo_hirakawa')
            self.assertEqual(app.query_params.get('gp'),'19')

    def test_search_retains_selected_gp_for_drivers_and_current_teams(self):
        from pitwall.dashboard.search import search
        for lang in ('pt','en'):
            for query,kind in [('Hamilton','driver'),('McLaren','team')]:
                match=next(x for x in search(ROOT,query,lang,year=2024,round_=1) if x['kind']==kind)
                params_=parse_qs(urlsplit(match['href']).query)
                self.assertEqual(params_['temporada'],['2024']);self.assertEqual(params_['gp'],['1'])
            match=next(x for x in search(ROOT,'Audi',lang,year=2024,round_=1) if x['kind']=='team')
            self.assertIn('2026',match['label'])
            self.assertEqual(parse_qs(urlsplit(match['href']).query)['temporada'],['2026'])
            self.assertTrue(any(x['kind']=='driver' for x in search(ROOT,'Hirakawa',lang,year=2026,round_=19)))

    def test_search_event_matches_do_not_change_team_context(self):
        from pitwall.dashboard.search import search
        for lang in ('pt','en'):
            results=search(ROOT,'sa',lang,year=2024,round_=1)
            self.assertTrue(any(x['kind']=='gp' for x in results))
            sauber=next(x for x in results if x['kind']=='team' and x['label'].startswith('Sauber'))
            self.assertEqual(parse_qs(urlsplit(sauber['href']).query)['temporada'],['2024'])
            self.assertEqual(parse_qs(urlsplit(sauber['href']).query)['gp'],['1'])
            audi=next(x for x in search(ROOT,'au',lang,year=2024,round_=1) if x['kind']=='team' and x['label'].startswith('Audi'))
            self.assertIn('2026',audi['label'])
            self.assertEqual(parse_qs(urlsplit(audi['href']).query)['temporada'],['2026'])

    def test_championship_profiles_keep_selected_gp_separate_from_snapshot_cutoff(self):
        from pitwall.dashboard.components import campeonatos
        snapshot=dict(disponivel=True,classificacao=[dict(posicao=1,piloto_id='max_verstappen',piloto='Max Verstappen',equipe='Red Bull Racing',equipe_id='red_bull',pontos=25)])
        for lang in ('pt','en'):
            set_language(lang)
            for year,round_ in ((2024,1),(2026,19)):
                circuit = 'marina_bay' if year == 2024 else 'americas'
                paineis=dict(temporada=year,rodada=18,circuito_id=circuit,
                    driver_standings=dict(snapshot,temporada=year,rodada_referencia=18,circuito_id=circuit),
                    constructor_standings=dict(disponivel=False))
                html=campeonatos(paineis,year,rodada=round_)
                link=params(html)
                self.assertEqual(link['temporada'],[str(year)])
                self.assertEqual(link['gp'],[str(round_)])
                self.assertEqual(link['anos'],[str(year)])
                self.assertIn('referência da rodada 18',html)

    def test_same_frame_shortcuts_preserve_hosted_app_path(self):
        from pitwall.dashboard.components import link_interno
        for lang in ('pt','en'):
            set_language(lang)
            for screen,chapter in [('Corridas','Clima'),('Previsões',None)]:
                href=link_interno(2024,1,tela=screen,aba=chapter)
                target=urlsplit(urljoin('https://pitwall-lab.streamlit.app/~/+/?documento=fontes-atuais',href))
                self.assertEqual(target.path,'/~/+/')
                self.assertEqual(parse_qs(target.query)['temporada'],['2024'])
                self.assertEqual(parse_qs(target.query)['gp'],['1'])

    def test_constructor_profile_preserves_context_and_keeps_title_credits_separate(self):
        from pitwall.dashboard.components import standings_table
        from pitwall.dashboard.team_views import load

        teams = load(ROOT)["equipes"]
        self.assertEqual(len(teams), 11)
        self.assertEqual(len(teams["mercedes"]["titulos_construtores"]), 9)
        self.assertEqual(teams["mercedes"]["titulos_construtores"][-1]["rodada"], 20)
        self.assertEqual(teams["mercedes"]["titulos_pilotos"][-1]["rodada"], 19)
        self.assertEqual(teams["alpine"]["titulos_construtores"], [])
        self.assertEqual([r["construtor"] for r in teams["alpine"]["titulos_anteriores"]],
                         ["Benetton", "Renault", "Renault"])
        snapshot = dict(disponivel=True, classificacao=[
            dict(posicao=10, equipe_id="sauber", equipe="Kick Sauber", pontos=0),
        ])
        html = standings_table(snapshot, teams=True, season=2024, round_=21)
        self.assertIn("Kick Sauber", html)
        self.assertEqual(params(html), dict(tela=["Campeonato"], lang=["pt"], painel=["equipes"],
                                            equipe=["audi"], temporada=["2024"], gp=["21"]))

    def test_constructor_campaign_uses_title_round_and_survives_language_change(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=45)
        app.query_params.update(tela="Campeonato", painel="equipes", equipe="mercedes",
                                campanha="2026-construtores", temporada="2025", gp="6", lang="en")
        app.run()
        self.assertFalse(app.exception)
        html = next(m.value for m in app.markdown if 'aria-label="Mercedes · 2026"' in m.value)
        links = [parse_qs(urlsplit(a["href"]).query) for a in Links(html).links]
        self.assertEqual(links[0]["gp"], ["20"])
        self.assertEqual(links[0]["painel"], ["equipes"])
        self.assertEqual([int(q["gp"][0]) for q in links[1:]], list(range(1, 21)))
        self.assertIn("652", html)
        self.assertEqual(app.selectbox(key="team_profile").value, "mercedes")
        language_button = next(b for b in app.button if b.key and b.key.startswith("pw_language_button_") and b.key.endswith("_pt"))
        language_button.click().run()
        self.assertFalse(app.exception)
        for name, value in (("equipe", "mercedes"), ("campanha", "2026-construtores"), ("gp", "6"), ("lang", "pt")):
            self.assertEqual(app.query_params.get(name), value)
        app.selectbox(key="team_profile").set_value("alpine").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.query_params.get("equipe"), "alpine")
        self.assertNotIn("campanha", app.query_params)

    def test_document_return_preserves_hosted_frame_without_nesting_wrapper(self):
        for lang in ('pt','en'):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=45)
            app.query_params.update(tela='Metodologia',documento='fontes-atuais',temporada='2024',gp='1',lang=lang)
            app.run();self.assertFalse(app.exception)
            app.button(key='fan-document-return').click().run()
            self.assertFalse(app.exception)
            self.assertNotIn('documento',app.query_params)
            self.assertNotIn('download',app.query_params)
            self.assertEqual(app.query_params.get('tela'),'Metodologia')
            self.assertEqual(app.query_params.get('temporada'),'2024');self.assertEqual(app.query_params.get('gp'),'1')
            self.assertEqual(app.query_params.get('lang'),lang)
            self.assertTrue(any('fan-hero' in item.value for item in app.markdown))

if __name__=='__main__':unittest.main()
