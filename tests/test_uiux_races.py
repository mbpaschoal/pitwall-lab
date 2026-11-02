"""Presentation parity and locale checks; no acquisition or model execution."""
from copy import deepcopy
import re
import unittest
from unittest.mock import Mock, patch

from pitwall.dashboard import components, weekend_views
from pitwall.i18n import set_language


class RacesPresentationTests(unittest.TestCase):
    def setUp(self):
        set_language('pt')
        self.addCleanup(set_language, 'pt')

    def test_short_dates_keep_the_selected_locale_after_year_is_removed(self):
        source = '2026-10-25'
        for lang, expected in [('pt', '25 out'), ('en', '25 Oct')]:
            with self.subTest(lang=lang):
                set_language(lang)
                displayed = components.data_editorial(source)
                self.assertEqual(displayed, expected + ' 2026')
                self.assertEqual(displayed.removesuffix('2026').strip(), expected)
                self.assertEqual(source, '2026-10-25')

    def test_dates_localise_all_months_without_interpreting_invalid_values(self):
        months = {
            'pt': 'jan fev mar abr mai jun jul ago set out nov dez'.split(),
            'en': 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(),
        }
        for lang, labels in months.items():
            set_language(lang)
            for number, label in enumerate(labels, 1):
                with self.subTest(lang=lang, month=number):
                    self.assertEqual(components.data_editorial('2024-{:02d}-01'.format(number)), '1 {} 2024'.format(label))
            self.assertEqual(components.data_editorial('not-a-date'), 'not-a-date')

    def test_each_driver_row_exposes_its_published_team_without_changing_values(self):
        snapshot = dict(disponivel=True, classificacao=[
            dict(posicao=9, piloto='Liam Lawson', piloto_id='lawson', equipe='RB F1 Team / Red Bull', equipe_ids=['rb', 'red_bull'], pontos=77, vitorias=0),
            dict(posicao=None, piloto='<driver>', piloto_id='unknown', equipe='A&B <Team>', equipe_id='unknown', pontos=0, vitorias=None),
        ])
        original = deepcopy(snapshot)
        for lang in ['pt', 'en']:
            set_language(lang)
            with patch('pitwall.dashboard.fan_views.portrait', return_value=''):
                rendered = components.standings_table(snapshot, season=2026)
            rows = re.findall(r'<tr>(.*?)</tr>', rendered, re.S)[1:]
            first, second = [re.findall(r'<td>(.*?)</td>', row, re.S) for row in rows]
            self.assertIn('<span class="pw-inline-team">RB F1 Team / Red Bull</span>', first[1])
            self.assertIn('RB F1 Team / Red Bull', first[2])
            self.assertEqual(first[3:], ['77', '0'])
            self.assertIn('piloto=lawson', first[1])
            self.assertIn('anos=2026', first[1])
            self.assertIn('lang=' + lang, first[1])
            self.assertIn('<span class="pw-inline-team">A&amp;B &lt;Team&gt;</span>', second[1])
            self.assertEqual(second[0], '—')
            self.assertEqual(second[3:], ['0', '—'])
        self.assertEqual(snapshot, original)

    def test_unknown_team_stays_unknown_and_constructor_rows_remain_complete(self):
        driver = dict(disponivel=True, classificacao=[dict(posicao=1, piloto='Unknown', piloto_id='unknown', equipe=None, pontos=0)])
        with patch('pitwall.dashboard.fan_views.portrait', return_value=''):
            rendered = components.standings_table(driver)
        self.assertIn('<span class="pw-inline-team">—</span>', rendered)
        teams = dict(disponivel=True, classificacao=[
            dict(posicao=1, equipe='First', equipe_id='first', pontos=10, vitorias=0),
            dict(posicao=2, equipe='Second', equipe_id='second', pontos=10, vitorias=0),
        ])
        rendered = components.standings_table(teams, teams=True)
        self.assertNotIn('pw-inline-team', rendered)
        self.assertEqual(rendered.count('<tr>'), 3)
        self.assertIn('First', rendered)
        self.assertIn('Second', rendered)
        self.assertNotIn('<table', components.standings_table(dict(disponivel=False, classificacao=teams['classificacao'])))

    def test_weather_display_localises_decimals_and_preserves_unknown_and_true_zero(self):
        for lang, decimal in [('pt', ','), ('en', '.')]:
            for track_eligible, expected_track in [(False, '—'), (True, '0{}0 °C'.format(decimal))]:
                with self.subTest(lang=lang, track_eligible=track_eligible):
                    set_language(lang)
                    state = dict(sessoes=[dict(nome='Race', clima_observado=dict(campos={
                        'air_temperature': dict(media_amostras=24.2, elegivel=True),
                        'track_temperature': dict(media_amostras=0.0, elegivel=track_eligible),
                    }))])
                    original = deepcopy(state)
                    view = Mock()
                    air, track = Mock(), Mock()
                    view.columns.return_value = [air, track]
                    with patch.object(weekend_views, 'st', view):
                        self.assertTrue(weekend_views.render_weather(state))
                    air.metric.assert_called_once_with('Temperatura do ar', '24{}2 °C'.format(decimal))
                    track.metric.assert_called_once_with('Temperatura da pista', expected_track)
                    self.assertEqual(state, original)

    def test_preexisting_documentary_review_and_canonical_session_ids_survive(self):
        state = dict(temporada=2026, rodada=19, circuito_id='rodriguez', sessoes=[
            dict(nome='Practice 1', session_key=7, cobertura=dict(laps=2), tempos=[dict(piloto='Example', duracao=65.2)]),
            dict(nome='Race', session_key=8, cobertura=dict(laps=10), tempos=[dict(piloto='Example', duracao=3600.0)], dados_descritivos=dict(voltas_por_piloto=[])),
        ])
        original = deepcopy(state)
        set_language('en')
        with patch.object(weekend_views, 'st', Mock()), patch('pitwall.dashboard.archive_views.renderizar_tempos') as render:
            self.assertTrue(weekend_views.render_times(state))
        actual = render.call_args.args[0]
        self.assertEqual([(s['session_key'], s['nome']) for s in actual['sessoes']], [(7, 'Practice 1'), (8, 'Race')])
        self.assertEqual(actual['identidade'], dict(temporada=2026, rodada=19, circuito_id='rodriguez'))
        self.assertEqual(state, original)
        quality = dict(codigo='zero_isolado_excluido', fontes=[dict(url='https://example.org/weather.pdf')])
        state = dict(sessoes=[dict(nome='Race', clima_observado=dict(campos={
            'air_temperature': dict(media_amostras=24.2, elegivel=True),
            'track_temperature': dict(media_amostras=40.3, elegivel=True, qualidade=quality),
        }))])
        view = Mock(); view.columns.return_value = [Mock(), Mock()]
        with patch.object(weekend_views, 'st', view):
            weekend_views.render_weather(state)
        self.assertTrue(any('sem interpolação' in call.args[0] for call in view.caption.call_args_list))
        view.markdown.assert_any_call('[Relatório oficial do clima da corrida](https://example.org/weather.pdf)')


if __name__ == '__main__':
    unittest.main()
