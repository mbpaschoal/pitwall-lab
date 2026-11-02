"""Tyre display contract: missing values, zero, chart, translated table and CSV."""
import copy
import csv
import io
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from pitwall.dashboard import archive_views as views
from pitwall.i18n import set_language
from pitwall.i18n.streamlit import Presentation
from pitwall.data.archive import carregar

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'frontend_assets').is_dir())


def render(gp, lang):
    set_language(lang)
    ui = MagicMock()
    ui.selectbox.side_effect = lambda label, options, **kwargs: 'Race' if 'Race' in options else options[0]
    with patch.object(views, 'st', Presentation(ui)):
        views.renderizar_estrategias(gp)
    frame = ui.dataframe.call_args_list[0].args[0]
    payload = ui.download_button.call_args_list[0].args[1]
    rows = list(csv.DictReader(io.StringIO(payload.decode('utf-8-sig'))))
    fig = ui.plotly_chart.call_args.args[0] if ui.plotly_chart.called else None
    return ui, frame, rows, fig


class TestTyrePresentation(unittest.TestCase):
    def tearDown(self):
        set_language('pt')

    def test_unknown_null_zero_and_quality_agree_across_chart_table_and_csv(self):
        gp = {'identidade': {'temporada': 2024, 'rodada': 1}, 'estrategias': [
            {'piloto': 'Driver A', 'comparavel': False,
             'qualidade': [{'stint_number': 4, 'flags': ['lap_start_ausente']}],
             'sequencia_stints': [
                 {'composto': 'SOFT', 'idade': 0, 'inicio': 1, 'fim': 2},
                 {'composto': 'UNKNOWN', 'idade': None, 'inicio': 3, 'fim': 5},
                 {'composto': None, 'idade': None, 'inicio': 6, 'fim': 6},
                 {'composto': 'HARD', 'idade': 4, 'inicio': None, 'fim': None}]},
            {'piloto': 'Driver B', 'comparavel': None,
             'sequencia_stints': [{'composto': 'MEDIUM', 'idade': 2, 'inicio': 1, 'fim': 7}]}]}
        original = copy.deepcopy(gp)
        for lang in ('pt', 'en'):
            with self.subTest(lang=lang):
                ui, frame, rows, fig = render(gp, lang)
                compound, age, quality = ('Composto', 'Idade inicial do pneu', 'Limites comparáveis') if lang == 'pt' else ('Compound', 'Initial tyre age', 'Comparable boundaries')
                unknown, no = ('Não informado', 'Não') if lang == 'pt' else ('Not reported', 'No')
                self.assertEqual(frame[compound].tolist(), ['SOFT', unknown, unknown, 'HARD', 'MEDIUM'])
                self.assertEqual([r[quality] for r in rows], [no]*4 + [unknown])
                self.assertEqual([r[age] for r in rows], ['0.0', '', '', '4.0', '2.0'])
                self.assertEqual(len(fig.data), 4)  # no fabricated missing-boundary bar
                self.assertEqual([t.name for t in fig.data], ['SOFT', unknown, unknown, 'MEDIUM'])
                self.assertEqual(fig.data[0].customdata[0][2], '0 voltas' if lang == 'pt' else '0 laps')
                self.assertEqual(fig.data[1].customdata[0][2], unknown)
                self.assertEqual(fig.data[2].customdata[0][2], unknown)
                self.assertEqual(list(fig.data[0].x), [1])  # boundary width is not tyre age
                self.assertEqual(fig.data[2].mode, 'markers')
                self.assertIn('Idade inicial:' if lang == 'pt' else 'Initial age:', fig.data[2].hovertemplate)
                captions = ' '.join(c.args[0] for c in ui.caption.call_args_list)
                self.assertIn('sem comprovar pneu novo' if lang == 'pt' else 'without proving the tyres were new', captions)
                self.assertNotIn('UNKNOWN', frame.to_csv(index=False))
                self.assertNotIn('False', frame.to_csv(index=False))
                self.assertEqual(gp, original)

    def test_real_corrected_control_unknown_and_missing_age_in_both_languages(self):
        archive = carregar(ROOT)
        for lang in ('pt', 'en'):
            with self.subTest(lang=lang):
                driver, age, compound = ('Piloto', 'Idade inicial do pneu', 'Composto') if lang == 'pt' else ('Driver', 'Initial tyre age', 'Compound')
                _, _, rows, fig = render(archive['gps']['2024:1'], lang)
                nico = [r for r in rows if r[driver] == 'Nico Hülkenberg']
                self.assertEqual(float(next(r[age] for r in nico if r['Stint'] == '4')), 1)
                self.assertEqual(float(next(r[age] for r in nico if r['Stint'] == '1')), 0)
                _, _, rows, _ = render(archive['gps']['2024:23'], lang)
                ocon = [r for r in rows if r[driver] == 'Esteban Ocon']
                self.assertTrue(any(r[compound] == ('Não informado' if lang == 'pt' else 'Not reported') for r in ocon))
                _, frame, rows, fig = render(archive['gps']['2025:1'], lang)
                self.assertTrue(any(r[age] == '' for r in rows))
                self.assertTrue(frame[age].isna().any())
                self.assertTrue(any(t.customdata[0][2] == ('Não informado' if lang == 'pt' else 'Not reported') for t in fig.data))

    def test_invalid_boundaries_are_retained_in_table_but_not_drawn(self):
        gp = {'identidade': {'temporada': 2024, 'rodada': 1}, 'estrategias': [{
            'piloto': 'Driver', 'comparavel': False, 'sequencia_stints': [
                {'composto': 'SOFT', 'idade': 0, 'inicio': a, 'fim': b}
                for a, b in [(None, None), (0, 2), (3, 2), (True, 5), (1, float('inf')), (float('nan'), 5)]
            ]}]}
        _, frame, rows, fig = render(gp, 'pt')
        self.assertEqual(len(frame), 6)
        self.assertEqual(len(rows), 6)
        self.assertIsNone(fig)


if __name__ == '__main__':
    unittest.main()
