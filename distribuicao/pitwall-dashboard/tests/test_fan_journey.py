"""Fan journey keeps canonical routes, probabilities and absent states intact."""
import hashlib
import json
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest
from pitwall.dashboard.journey import calendar
from pitwall.dashboard.tarot import cards_html
from pitwall.i18n import set_language

ROOT=Path(__file__).resolve().parents[1]


class JourneyTests(unittest.TestCase):
    def test_calendar_keeps_context_and_selected_gp(self):
        options=[dict(valor='2026:{}'.format(n),rodada=n,corrida='Race {} Grand Prix'.format(n)) for n in range(1,25)]
        html=calendar(options,2026,'2026:19','Previsões','en')
        self.assertEqual(html.count('aria-current="true"'),1)
        self.assertEqual(html.count('<a '),7)
        self.assertIn('gp=19',html)
        self.assertIn('lang=en',html)
        self.assertIn('tela=Previs%C3%B5es',html)

    def test_tarot_does_not_turn_missing_values_into_probability(self):
        rows=[dict(driver_id='unknown',name='<driver>',team='Team',probability=v) for v in (None,False,float('nan'),-1,2)]
        self.assertNotIn('<article',cards_html(rows,ROOT))
        set_language('pt')
        html=cards_html([dict(driver_id='unknown',name='<driver>',team='Team',probability=.5)],ROOT)
        self.assertNotIn('%',html)
        self.assertIn('&lt;driver&gt;',html)
        self.assertNotIn('src="http',html)

    def test_mexico_sealed_cards_keep_the_recorded_faces_and_probabilities(self):
        path=ROOT/'frontend_assets/race_weekend.json'
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=40)
        app.query_params.update(tela='Previsões',temporada='2026',gp='19',cartas='1')
        app.run()
        self.assertFalse(app.exception)
        html='\n'.join(x.proto.body for x in app.get('html') if 'class="pw-tarot-reading"' in x.proto.body)
        self.assertIn('Max Verstappen',html)
        self.assertEqual(html.count('<template'),3)
        self.assertEqual(html.count('data-tarot-reveal'),3)
        self.assertIn('%',html)
        self.assertEqual(html.count('data-pw-face='),3)
        self.assertEqual(html.count('&lt;img '),3)
        self.assertIn('Lewis Hamilton',html)
        self.assertIn('George Russell',html)
        self.assertEqual(html.count('não indica uma posição de chegada.'), 1)
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())

    def test_historical_team_cannot_show_later_team_artwork(self):
        row=dict(driver_id='hamilton',name='Lewis Hamilton',team='Mercedes',probability=.5)
        html=cards_html([row],ROOT,2024,1)
        self.assertIn('data-team-id="mercedes"',html)
        self.assertIn('Mercedes',html)
        self.assertNotIn('Ferrari',html)
        row['team']='Ferrari'
        self.assertIn('<img ',cards_html([row],ROOT,2025,1))

    def test_gp_without_emission_does_not_open_cards(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=40)
        data=json.loads((ROOT/'frontend_assets/race_weekend.json').read_text())['dados_2026']
        issued={p['rodada'] for p in data['previsoes']}
        missing=[r['rodada'] for r in data['corridas'] if r['rodada'] not in issued]
        if not missing:self.skipTest('No unissued GP in the current public artifact.')
        app.query_params.update(tela='Previsões',temporada='2026',gp=str(missing[0]),cartas='1')
        app.run()
        self.assertFalse(app.exception)
        self.assertFalse(any('class="pw-tarot-reading"' in x.proto.body for x in app.get('html')))
        self.assertFalse(any(x.key=='open_tarot' for x in app.button))

    def test_unissued_forecast_explains_state_before_art_and_opens_its_sessions(self):
        data=json.loads((ROOT/'frontend_assets/race_weekend.json').read_text())['dados_2026']
        pending=next((row for row in data['corridas'] if row.get('estado_previsao')=='indisponivel'),None)
        if pending is None:self.skipTest('No unissued GP in the current public artifact.')
        gp=str(pending['rodada'])
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=40)
        app.query_params.update(tela='Previsões',temporada='2026',gp=gp,lang='en')
        app.run()
        self.assertFalse(app.exception)
        markup=[x.value for x in app.markdown]
        state=next(i for i,x in enumerate(markup) if 'data-forecast-state="unavailable"' in x)
        art=next(i for i,x in enumerate(markup) if x.startswith('<section class="pw-postcard') and 'data-hero-kind="forecast"' in x)
        self.assertLess(state,art)
        self.assertIn('No recorded forecast for this GP.',markup[state])
        self.assertNotIn('%',markup[state])
        action=next(x for x in app.button if x.label=='View sessions and laps')
        action.click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.query_params['gp'],gp)
        self.assertEqual(app.query_params['lang'],'en')
        self.assertEqual(app.query_params['aba'],'Tempos')

    def test_forecast_guidance_preserves_recorded_and_retrospective_distinction(self):
        from pitwall.dashboard.fan_views import forecast_context
        set_language('pt')
        recorded=forecast_context({'estado_previsao':'previsao_registrada'},2026)
        historical=forecast_context({'estado_previsao':'ensaio_retrospectivo'},2025)
        self.assertIn('registrada antes da corrida',recorded)
        self.assertNotIn('Estudo retrospectivo',recorded)
        self.assertIn('não é previsão emitida antes da corrida',historical)
        self.assertNotIn('data-forecast-state="recorded"',historical)


if __name__=='__main__':unittest.main()
