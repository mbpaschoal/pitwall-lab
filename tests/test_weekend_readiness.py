"""A future calendar or a different GP must never unlock forecast preparation."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import unittest

from operacao2026 import readiness, weekend, cloud

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'operacao2026/eventos/saopaulo2026.json'


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.event=weekend.load_event(CONFIG)
        self.now=datetime(2026,11,7,20,tzinfo=timezone.utc)
        self.public=dict(temporada=2026,rodada=20,circuito_id='interlagos',sessoes=[dict(
            session_key=11408,estado='dados_recebidos',encerramento_observado_utc='2026-11-07T19:01:00Z')])

    def test_qualifying_receipt_does_not_claim_forecast_readiness(self):
        self.assertEqual(readiness.qualification_status(self.event,self.public,self.now),
                         'classificacao_recebida_snapshot_preditivo_pendente')

    def test_mexico_and_other_sessions_do_not_unlock_sao_paulo(self):
        for row in [dict(self.public,rodada=19,circuito_id='rodriguez'),
                    dict(self.public,sessoes=[dict(self.public['sessoes'][0],session_key=11407)]),
                    dict(self.public,sessoes=[dict(self.public['sessoes'][0],estado='parcial')])]:
            with self.subTest(row=row):
                self.assertEqual(readiness.qualification_status(self.event,row,self.now),'aguardando_classificacao')

    def test_schedule_is_not_an_observed_finish_and_future_receipts_fail(self):
        row=deepcopy(self.public);row['sessoes'][0].pop('encerramento_observado_utc')
        self.assertEqual(readiness.qualification_status(self.event,row,self.now),'aguardando_encerramento_observado')
        for end in ['2026-11-07T21:00:00Z','2026-11-07T17:59:00Z']:
            row['sessoes'][0]['encerramento_observado_utc']=end
            with self.assertRaisesRegex(ValueError,'inconsistent'):
                readiness.qualification_status(self.event,row,self.now)

    def test_race_start_closes_prospective_window(self):
        self.assertEqual(readiness.qualification_status(self.event,self.public,cloud.instant(self.event['largada_utc'])),
                         'janela_prospectiva_encerrada')

    def test_offline_inventory_is_honest_and_uses_three_different_team_cards(self):
        result=readiness.inspect(CONFIG,ROOT,datetime(2026,11,3,18,tzinfo=timezone.utc))
        self.assertEqual(result['identity'],[2026,20,'interlagos'])
        self.assertEqual(result['qualification_status'],'aguardando_classificacao')
        self.assertFalse(result['forecast_emission_attempted']);self.assertFalse(result['forecast_emitted_by_this_check'])
        self.assertGreaterEqual(result['verified_team_pairs'],22)
        for pair in result['cards']:
            self.assertEqual(len({p['sha256'] for p in pair['poses']}),3)

    def test_sao_paulo_free_window_and_preserved_mexico_archive(self):
        self.assertFalse(cloud.in_window(self.event,datetime(2026,11,3,18,tzinfo=timezone.utc)))
        self.assertTrue(cloud.in_window(self.event,datetime(2026,11,5,15,30,tzinfo=timezone.utc)))
        self.assertIsNotNone(cloud.historical_access_after(self.event,datetime(2026,11,7,19,29,tzinfo=timezone.utc)))
        self.assertIsNone(cloud.historical_access_after(self.event,datetime(2026,11,7,19,31,tzinfo=timezone.utc)))
        mexico=dict(temporada=2026,rodada=19,circuito_id='rodriguez',sessoes=[])
        merged=cloud.merge_archive(mexico,self.public)
        self.assertEqual(merged['arquivo_eventos'],[mexico])
        self.assertEqual(mexico['sessoes'],[])


if __name__=='__main__':unittest.main()
