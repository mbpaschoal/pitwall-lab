"""Controlled P1 fixtures. They create no real GP forecasts or public receipts."""
from copy import deepcopy
import csv
from datetime import timedelta
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import pair_predictions as p

ROOT = Path(os.environ.get('PITWALL_P1_SOURCE_ROOT', str(p.HERE.parents[1])))
if not (ROOT/'models/modelo_v1/modelo.joblib').is_file() or not (ROOT/'models/modelo_v1/modelo.joblib').stat().st_size:
    ROOT = Path(json.loads((p.HERE/'registration.json').read_text())['source_root'])
sys.path.insert(0, str(ROOT))


class PairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.folder = self.root/'reports/operacao_2026/emissoes/fixture-p1'
        self.folder.mkdir(parents=True); self.destination = self.root/'pair-new'
        for name in ['models/modelo_v1/modelo.joblib', 'models/modelo_v1/metadados.json', 'data/preparado/colunas.json']:
            q = self.root/name; q.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT/name, q)
        fields = p.load(self.root/'data/preparado/colunas.json')['entradas']; self.fields = fields
        self.event = {'temporada': '2026', 'rodada': '20', 'circuito_id': 'interlagos'}
        lines, matrix, csv_rows = [], [], []
        for i in range(22):
            numeric = {f: 0 for f in fields}; numeric['posicao_classificacao'] = i+1
            r = {**numeric, **self.event, 'piloto_id': 'fixture-driver-'+str(i), 'equipe_id_entrada': 'fixture-team',
                'elegivel_previsao': True, 'probabilidade_modelo': .15}
            lines.append(r); matrix.append(numeric)
            csv_rows.append({**{k: str(r[k]) for k in p.KEY}, 'circuito_id': 'interlagos', 'probabilidade_modelo': '.15'})
        self.inputs = {'linhas': lines, 'matriz': matrix, 'ordem': fields}; self.csv_rows = csv_rows
        (self.folder/'entradas.json').write_text(json.dumps(self.inputs))
        with (self.folder/'probabilidades.csv').open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(csv_rows[0])); w.writeheader(); w.writerows(csv_rows)
        for name in ['historicos.json', 'fontes.json', 'cobertura.json']: (self.folder/name).write_text('{}')
        self.manifest = {'modo': 'PROSPECTIVO', 'modelos': p.V1_HASHES, 'evento': self.event,
            'corte_utc': '2026-11-07T20:00:00Z', 'emitido_em_utc': '2026-11-07T20:00:01Z',
            'sessao_qualifying_inicio_utc': '2026-11-07T18:00:00Z',
            'sessao_qualifying_encerrada_utc': '2026-11-07T19:01:00Z', 'obtido_classificacao_utc': '2026-11-07T19:45:00Z',
            'corte_temporal': {'corrida_programada_em_utc': '2026-11-08T17:00:00Z', 'corte_utc': '2026-11-07T20:00:00Z', 'resultado_alvo_incluido': False},
            'cobertura': {'elegiveis': 22, 'registros_classificacao': 22},
            'hashes_saidas': {q.name: p.sha(q) for q in self.folder.iterdir()}}
        self.write_manifest(); self.now = p.utc('2026-11-07T20:01:00Z')
        self.registry = {(2026, 20, 'interlagos'): {'modo': 'PROSPECTIVO', 'evento': {'temporada': 2026, 'rodada': 20, 'circuito_id': 'interlagos'},
            'diretorio': 'reports/operacao_2026/emissoes/fixture-p1'}}

    def write_manifest(self): (self.folder/'manifesto.json').write_text(json.dumps(self.manifest))

    def pair(self, clock=None):
        with patch('registro_emissoes.carregar', return_value=self.registry), patch.object(p, 'utc_now', return_value=clock or self.now):
            return p.prepare(self.root, 'fixture-p1', self.destination)

    def test_complete_pair_is_prepared_and_never_claims_publication(self):
        r = self.pair(); self.assertEqual(len(r['pairs']), 22)
        self.assertEqual(r['status'], 'prepared_not_published'); self.assertFalse(r['publication_verified'])
        self.assertFalse(r['fitting_performed']); self.assertFalse(r['current_targets_read'])
        self.assertTrue(all(x['probabilidade_v1'] == .15 for x in r['pairs']))

    def test_race_boundary_and_freeze_after_cutoff_reject(self):
        with self.assertRaises(ValueError): self.pair(p.utc('2026-11-08T16:00:00Z'))
        model = p.frozen_q(); model['frozen_at_utc'] = '2026-11-07T21:00:00Z'
        with self.assertRaises(ValueError): p.inspect_manifest(self.folder, model, self.now)

    def test_clock_rechecked_after_computation_before_output(self):
        with patch('registro_emissoes.carregar', return_value=self.registry), patch.object(p, 'utc_now', side_effect=[self.now, p.utc('2026-11-08T16:00:00Z')]):
            with self.assertRaises(ValueError): p.prepare(self.root, 'fixture-p1', self.destination)
        self.assertFalse(self.destination.exists())

    def test_retrospective_or_current_target_admitted_is_rejected(self):
        self.manifest['modo'] = 'ENSAIO_RETROSPECTIVO'; self.write_manifest()
        with self.assertRaises(ValueError): self.pair()
        self.manifest['modo'] = 'PROSPECTIVO'; self.manifest['corte_temporal']['resultado_alvo_incluido'] = True; self.write_manifest()
        with self.assertRaises(ValueError): self.pair()

    def test_changed_hash_or_frozen_model_rejects(self):
        (self.folder/'entradas.json').write_text('{}')
        with self.assertRaises(ValueError): self.pair()
        (self.root/'models/modelo_v1/modelo.joblib').write_bytes(b'changed')
        with self.assertRaises(ValueError): self.pair()

    def test_duplicate_foreign_or_current_outcome_rows_reject(self):
        model = p.frozen_q(); inputs = deepcopy(self.inputs)
        inputs['linhas'][0]['podio'] = 1
        with self.assertRaises(ValueError): p.assemble_pairs(inputs, self.csv_rows, self.event, model)
        inputs = deepcopy(self.inputs); inputs['linhas'][0]['circuito_id'] = 'americas'
        with self.assertRaises(ValueError): p.assemble_pairs(inputs, self.csv_rows, self.event, model)
        rows = deepcopy(self.csv_rows); rows[0] = rows[1]
        with self.assertRaises(ValueError): p.assemble_pairs(self.inputs, rows, self.event, model)

    def test_incomplete_roster_and_matrix_mismatch_reject(self):
        model = p.frozen_q(); inputs = deepcopy(self.inputs)
        inputs['linhas'].pop(); inputs['matriz'].pop()
        with self.assertRaises(ValueError): p.assemble_pairs(inputs, self.csv_rows[:-1], self.event, model)
        inputs = deepcopy(self.inputs); inputs['matriz'][0]['posicao_classificacao'] = 99
        with self.assertRaises(ValueError): p.assemble_pairs(inputs, self.csv_rows, self.event, model)

    def test_naive_utc_and_scheduled_finish_do_not_suffice(self):
        self.manifest['sessao_qualifying_encerrada_utc'] = '2026-11-07T21:00:00Z'; self.write_manifest()
        with self.assertRaises(ValueError): self.pair()
        with self.assertRaises(ValueError): p.utc('2026-11-07T19:01:00')

    def test_output_refuses_replacement_or_unregistered_emission(self):
        self.destination.mkdir()
        with self.assertRaises(FileExistsError): self.pair()
        self.destination.rmdir(); self.registry = {}
        with self.assertRaises(ValueError): self.pair()

    def test_frozen_q_reconstructs_prior_reference_probabilities(self):
        model = p.frozen_q(); prior = p.load(p.HERE/'q-reconstruction-fixture.json')['records']
        count = 0
        for row in prior:
            raw = row['features']
            observed = p.q_probability({name: raw[name] for name in model['fields']}, model)
            self.assertAlmostEqual(observed, row['probability'], places=13); count += 1
        self.assertEqual(count, 479)

    def test_q_imputes_missing_position_and_refuses_extra_predictor(self):
        model = p.frozen_q(); raw = {k: None if k == 'posicao_classificacao' else 0 for k in model['fields']}
        p1 = p.q_probability(raw, model); raw['posicao_classificacao'] = model['medians'][0]
        self.assertEqual(p1, p.q_probability(raw, model)); raw['grid_resultado'] = 1
        with self.assertRaises(ValueError): p.q_probability(raw, model)


if __name__ == '__main__': unittest.main()
