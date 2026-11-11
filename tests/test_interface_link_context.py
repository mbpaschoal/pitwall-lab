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

    def test_hall_covers_each_championship_and_preserves_historical_credits(self):
        from pitwall.dashboard.hall_views import load

        snapshot = load(ROOT)
        champions = snapshot["pilotos"]
        self.assertEqual(len(champions), 36)
        seasons = [title["ano"] for driver in champions.values() for title in driver["titulos"]]
        self.assertEqual(sorted(seasons), list(range(1950, 2027)))
        self.assertEqual(len(champions["lewis-hamilton"]["titulos"]), 7)
        self.assertEqual(len(champions["michael-schumacher"]["titulos"]), 7)
        fangio = next(t for t in champions["juan-manuel-fangio"]["titulos"] if t["ano"] == 1954)
        self.assertEqual([r["id"] for r in fangio["construtores"]], ["maserati", "mercedes"])
        antonelli = champions["kimi-antonelli"]["titulos"][0]
        self.assertEqual(antonelli["decisao"]["rodada"], 19)
        self.assertEqual(snapshot["corte"], "2026-11-08")

    def test_hall_directory_selection_and_language_preserve_gp_and_champion(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=45)
        app.query_params.update(tela="Pilotos", visao="hall", temporada="2026", gp="20", lang="pt")
        app.run()
        self.assertFalse(app.exception)
        table = next(m.value for m in app.markdown if 'aria-label="Campeões mundiais de Fórmula 1"' in m.value)
        self.assertEqual(table.count("<tr>"), 37)
        app.selectbox(key="hall_champion").set_value("kimi-antonelli").run()
        self.assertFalse(app.exception)
        title = next(m.value for m in app.markdown if 'aria-label="Títulos mundiais de pilotos"' in m.value)
        for label, expected in (("Campeonato", "19"), ("Corridas", "19")):
            self.assertTrue(any(parse_qs(urlsplit(a["href"]).query).get("tela") == [label]
                                and parse_qs(urlsplit(a["href"]).query).get("gp") == [expected]
                                for a in Links(title).links))
        english = next(b for b in app.button if b.key and b.key.startswith("pw_language_button_") and b.key.endswith("_en"))
        english.click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.query_params.get("campeao"), "kimi-antonelli")
        self.assertEqual(app.query_params.get("gp"), "20")
        self.assertEqual(app.query_params.get("lang"), "en")
        self.assertTrue(any("Mexico City Grand Prix" in m.value for m in app.markdown))

    def test_champions_duel_counts_raced_seasons_and_preserves_pair(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=45)
        app.query_params.update(tela="Pilotos", visao="duelo-campeoes", temporada="2026", gp="20", lang="pt")
        app.run()
        self.assertFalse(app.exception)
        first = app.selectbox(key="hall_duel_first")
        self.assertEqual(first.value, "ayrton-senna")
        self.assertEqual(len(first.options), 36)
        self.assertEqual(app.selectbox(key="hall_duel_second").value, "alain-prost")
        comparison = next(m.value for m in app.markdown if 'aria-label="Comparação de campeões"' in m.value)
        self.assertIn("28 anos e 223 dias", comparison)
        self.assertIn("30 anos e 224 dias", comparison)
        self.assertIn("<td>5</td><td>6</td>", comparison)
        timeline = next(m.value for m in app.markdown if 'aria-label="Títulos do duelo"' in m.value)
        years = [int(a["href"].split("/")[-2]) for a in Links(timeline).links if a["href"].endswith("/drivers")]
        self.assertEqual(years, [1985, 1986, 1988, 1989, 1990, 1991, 1993])

        first.set_value("alain-prost").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.info[0].value, "Escolha dois campeões diferentes para comparar.")
        app.selectbox(key="hall_duel_first").set_value("fernando-alonso").run()
        english = next(b for b in app.button if b.key and b.key.startswith("pw_language_button_") and b.key.endswith("_en"))
        english.click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.query_params.get("campeao"), "fernando-alonso")
        self.assertEqual(app.query_params.get("rival_campeao"), "alain-prost")
        self.assertEqual(app.query_params.get("gp"), "20")
        comparison = next(m.value for m in app.markdown if 'aria-label="Champion comparison"' in m.value)
        self.assertIn("<td>4</td><td>6</td>", comparison)

    def test_championship_photo_archive_preserves_model_and_credit(self):
        from pitwall.dashboard.photo_archive import load

        photos = load(ROOT)
        self.assertEqual(photos["senna-mp4-4"]["modelo"], "mclaren-mp4-4")
        self.assertEqual(photos["senna-mp4-4"]["temporadas"], [1988])
        self.assertEqual(photos["fangio-nurburgring-1957"]["gps"], ["1957:6"])
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=45)
        app.query_params.update(tela="Pilotos", visao="acervo", temporada="2026", gp="20", lang="en")
        app.run()
        self.assertFalse(app.exception)
        app.selectbox(key="archive_season").set_value(1988).run()
        self.assertFalse(app.exception)
        photo = next(item.value for item in app.markdown if 'data-archive-photo="senna-mp4-4"' in item.value)
        self.assertIn("Tony Hisgett", photo)
        self.assertIn("Resized version", photo)
        links = [anchor["href"] for anchor in Links(photo).links]
        self.assertTrue(any(link.startswith("https://creativecommons.org/") for link in links))
        self.assertIn(photos["senna-mp4-4"]["fonte"], links)
        self.assertNotIn('data-archive-photo="prost-mp4-5"', photo)
        app.radio(key="archive_mode").set_value("Momentos históricos").run()
        self.assertFalse(app.exception)
        app.selectbox(key="archive_event_season").set_value(1957).run()
        self.assertFalse(app.exception)
        event = next(item.value for item in app.markdown if 'data-archive-photo="fangio-nurburgring-1957"' in item.value)
        self.assertNotIn('data-archive-photo="hamilton-interlagos-2008"', event)
        app.selectbox(key="archive_event_season").set_value(1988).run()
        self.assertFalse(app.exception)
        self.assertIn("Objects from the collection", [item.value for item in app.subheader])
        self.assertTrue(any('data-archive-photo="mclaren-trofeu-suzuka-1988"' in item.value for item in app.markdown))
        self.assertFalse(app.info)

    def test_photo_archive_has_a_car_for_each_title_campaign_and_each_current_team(self):
        from pitwall.dashboard.photo_archive import INVENTORY, load

        inventory = json.loads((ROOT / INVENTORY).read_text(encoding="utf-8"))
        photos = load(ROOT)
        campaigns = {(entry["ano"], entry["equipe"]): entry for entry in inventory["campanhas"]}
        photographed = set()
        for photo in photos.values():
            for season in photo.get("temporadas", []):
                campaign = season, photo["construtor"]
                self.assertIn(photo["modelo"], campaigns[campaign]["modelos_candidatos"])
                photographed.add(campaign)
        self.assertEqual(photographed, set(campaigns))
        self.assertEqual(photos["ferrari-d50"]["temporadas"], [1956])
        self.assertIn("ferrari.com", campaigns[1956, "ferrari"]["modelos_documentados"]["ferrari-d50"]["fonte"])
        photographed_teams = {team for photo in photos.values() for team in photo.get("equipes", [])}
        self.assertTrue(set(inventory["equipes_atuais"]).issubset(photographed_teams))
        historic_gps = {f'{event["ano"]}:{event["rodada"]}' for event in inventory["momentos"]}
        for photo in photos.values():
            artifact_gps = set(photo.get("artefatos_gps", []))
            self.assertTrue(artifact_gps.issubset(historic_gps))
            self.assertTrue(artifact_gps.isdisjoint(photo.get("gps", [])))

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
