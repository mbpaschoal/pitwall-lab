"""Fan journey keeps canonical routes, probabilities and absent states intact."""
import hashlib
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

    def test_mexico_cards_show_art_without_percentages_or_emission_changes(self):
        path=ROOT/'frontend_assets/race_weekend.json'
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=40)
        app.query_params.update(tela='Previsões',temporada='2026',gp='19',cartas='1')
        app.run()
        self.assertFalse(app.exception)
        html='\n'.join(x.value for x in app.markdown if '<div class="tarot-cards">' in x.value)
        self.assertIn('Max Verstappen',html)
        self.assertNotIn('%',html)
        self.assertEqual(html.count('<img '),3)
        self.assertIn('Lewis Hamilton',html)
        self.assertIn('George Russell',html)
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
        import json
        data=json.loads((ROOT/'frontend_assets/race_weekend.json').read_text())['dados_2026']
        issued={p['rodada'] for p in data['previsoes']}
        missing=[r['rodada'] for r in data['corridas'] if r['rodada'] not in issued]
        if not missing:self.skipTest('No unissued GP in the current public artifact.')
        app.query_params.update(tela='Previsões',temporada='2026',gp=str(missing[0]),cartas='1')
        app.run()
        self.assertFalse(app.exception)
        self.assertFalse(any('<div class="tarot-cards">' in x.value for x in app.markdown))
        self.assertFalse(any(x.key=='open_tarot' for x in app.button))


if __name__=='__main__':unittest.main()
