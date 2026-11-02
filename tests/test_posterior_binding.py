"""Posterior admission must survive a portable copy and reject altered evidence."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from pitwall.data import post_race_evaluation as posterior
from pitwall.data.race_weekend import pacote_2026

ROOT = Path(__file__).resolve().parents[1]


class PosteriorBindingTests(unittest.TestCase):
    def setUp(self):
        self.asset = json.loads((ROOT / 'frontend_assets/race_weekend.json').read_text())

    def test_portable_annex_needs_no_private_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'frontend_assets').mkdir()
            shutil.copyfile(ROOT / posterior.ANNEX, root / posterior.ANNEX)
            posterior.validate_projected_asset(root, self.asset)
            self.assertFalse((root / 'reports').exists())
        package = pacote_2026(self.asset)
        race = next(r for r in package['corridas'] if r['rodada'] == 19)
        self.assertTrue(race['avaliavel_ranking'])
        self.assertEqual((race['acertos_modelo'], race['acertos_classificacao']), (2, 1))
        self.assertEqual(race['alvos_conhecidos'], 22)
        rows = package['participantes_por_rodada'][19]
        self.assertEqual(sum(r['resultado_observado'] is None for r in rows), 5)
        self.assertTrue(all(r['podio'] == 0 for r in rows if r['resultado_observado'] is None))

    def test_targets_forecasts_and_provenance_cannot_be_changed(self):
        mutations = [
            lambda a, r, rows: rows[0].update(probabilidade_modelo=0.1),
            lambda a, r, rows: rows[0].update(ranking_modelo=22),
            lambda a, r, rows: rows[0].update(ranking_classificacao=22),
            lambda a, r, rows: rows[0].update(elegivel_previsao=False),
            lambda a, r, rows: rows[0].update(equipe_id='other'),
            lambda a, r, rows: rows[0].update(resultado_observado=22),
            lambda a, r, rows: rows[0].update(podio_resultado_confirmado=False),
            lambda a, r, rows: rows.pop(),
            lambda a, r, rows: r.update(emissao_sha256='0' * 64),
            lambda a, r, rows: r.update(resultado_obtido_em_utc='2026-11-01T21:00:00Z'),
            lambda a, r, rows: a['proveniencia']['avaliacoes_posteriores'].clear(),
            lambda a, r, rows: a['proveniencia']['avaliacoes_posteriores'][posterior.KEY]['avaliacao'].update(acertos_modelo=3),
            lambda a, r, rows: r.update(resultado_circuito_id='americas'),
            lambda a, r, rows: r.update(resultado_data_fonte='2026-10-25'),
            lambda a, r, rows: a['proveniencia']['emissoes'][posterior.KEY].update(evento=dict(temporada=2026, rodada=18, circuito_id='americas')),
            lambda a, r, rows: rows[0].update(modo_previsao='ensaio_retrospectivo'),
            lambda a, r, rows: r['participantes_esperados_previsao'].append(r['participantes_esperados_previsao'][0]),
            lambda a, r, rows: a['proveniencia']['fontes_sha256'].update({posterior.ANNEX: '0' * 64}),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                asset = deepcopy(self.asset)
                race, rows = posterior._race_rows(asset['dados_2026'])
                mutate(asset, race, rows)
                # _race_rows returns a filtered list: removing one must also be
                # reflected in the parent asset to exercise the population gate.
                if index == 7:
                    removed = {r['piloto_id'] for r in rows}
                    asset['dados_2026']['previsoes'] = [r for r in asset['dados_2026']['previsoes']
                        if r['rodada'] != 19 or r['piloto_id'] in removed]
                with self.assertRaises((ValueError, KeyError)):
                    posterior.validate_projected_asset(ROOT, asset)

    def test_tampered_annex_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'frontend_assets').mkdir()
            (root / posterior.ANNEX).write_bytes((ROOT / posterior.ANNEX).read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'annex hash'):
                posterior.validate_projected_asset(root, self.asset)

    def test_offline_admission_preserves_forecast_and_other_rounds(self):
        before = deepcopy(self.asset)
        race, rows = posterior._race_rows(self.asset['dados_2026'])
        frozen = posterior.forecast_digest(rows)
        others = [r for r in before['dados_2026']['previsoes'] if r['rodada'] != 19]
        posterior.apply_posterior(ROOT, self.asset)
        self.assertEqual(posterior.forecast_digest(rows), frozen)
        self.assertEqual([r for r in self.asset['dados_2026']['previsoes'] if r['rodada'] != 19], others)
        self.assertEqual(self.asset, before)

    def test_reproduction_without_private_pdf_rejects_a_conflicting_capture(self):
        annex = json.loads((ROOT / posterior.ANNEX).read_text())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            names = [posterior.ANNEX, annex['normalizacao']['arquivo']]
            names.extend(annex['emissao']['diretorio'] + '/' + name
                         for name in ('manifesto.json', 'probabilidades.csv'))
            for name in names:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, root / name)
            posterior.apply_posterior(root, self.asset)
            pdf = root / 'reports/avaliacao_mexico_20261102/fia_final_race_classification.pdf'
            self.assertFalse(pdf.exists())
            pdf.write_bytes(b'conflicting capture')
            with self.assertRaisesRegex(ValueError, 'source hash'):
                posterior.apply_posterior(root, self.asset)


if __name__ == '__main__':
    unittest.main()
