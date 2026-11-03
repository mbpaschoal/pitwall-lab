"""Hosted forecasts must keep temporal gates, immutable evidence and bounded retry."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from operacao2026 import post_qualifying as pq, weekend, cloud

ROOT = Path(__file__).resolve().parents[1]


class PostQualifyingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root/'operacao2026/eventos/saopaulo2026.json'
        self.config.parent.mkdir(parents=True)
        shutil.copyfile(ROOT/'operacao2026/eventos/saopaulo2026.json', self.config)
        shutil.copyfile(ROOT/pq.POLICY, self.root/pq.POLICY)
        self.event = weekend.load_event(self.config)
        self.now = datetime(2026, 11, 7, 20, tzinfo=timezone.utc)
        self.state = dict(temporada=2026, rodada=20, circuito_id='interlagos', sessoes=[])
        self.base = self.root/cloud.STATE/'forecasts/2026-interlagos'
        self.registered = patch('registro_emissoes.carregar', return_value={})
        self.registered.start(); self.addCleanup(self.registered.stop)

    def observed(self):
        raw = json.dumps([dict(session_key=11408, meeting_key=1299, qualifying_phase=3,
            message='SESSION FINISHED', date='2026-11-07T19:01:00Z')]).encode()
        path = self.root/cloud.STATE/'interlagos-2026/control.json'
        path.parent.mkdir(parents=True); path.write_bytes(raw)
        source = dict(endpoint='race_control', status=200, arquivo_local=str(path.relative_to(self.root)),
            sha256=hashlib.sha256(raw).hexdigest(), obtido_em_utc='2026-11-07T19:40:00Z',
            url='https://api.openf1.org/v1/race_control?session_key=11408')
        self.state['sessoes'] = [dict(session_key=11408, estado='dados_recebidos',
            encerramento_observado_utc='2026-11-07T19:01:00Z', fontes=[source])]

    def prepared(self):
        return dict(status='prepared', identity=[2026,20,'interlagos'], race_start_utc=self.event['largada_utc'],
            declaration=dict(temporada=2026, rodada=20, circuito_id='interlagos', snapshot='auto-interlagos-test',
                diretorio='reports/operacao_2026/emissoes/auto-prospectivo-interlagos-test', modo='PROSPECTIVO'),
            directories=['data/operacao_2026/snapshots/auto-interlagos-test',
                         'reports/operacao_2026/emissoes/auto-prospectivo-interlagos-test'])

    def test_future_q_performs_no_collection_or_inference(self):
        with patch.object(pq.fontes, 'coletar_snapshot', side_effect=AssertionError('No future HTTP')):
            result = pq.prepare(self.root, self.config, self.state, datetime(2026,11,3,tzinfo=timezone.utc))
        self.assertEqual(result['status'], 'waiting_for_observed_qualifying')
        self.assertFalse(self.base.exists())

    def test_other_gp_and_already_registered_never_create_another_forecast(self):
        wrong = dict(self.state, rodada=19)
        with self.assertRaisesRegex(ValueError, 'another event'):
            pq.prepare(self.root, self.config, wrong, self.now)
        with patch('registro_emissoes.carregar', return_value={(2026,20,'interlagos'): {}}):
            self.assertEqual(pq.prepare(self.root,self.config,self.state,self.now)['status'], 'already_registered')

    def test_schedule_or_other_session_does_not_unlock_q(self):
        self.observed()
        for field, value in [('session_key',11407), ('estado','aguardando_publicacao'),
                             ('encerramento_observado_utc',None)]:
            state = deepcopy(self.state); state['sessoes'][0][field] = value
            self.assertEqual(pq.prepare(self.root,self.config,state,self.now)['status'], 'waiting_for_observed_qualifying')

    def test_q3_raw_sha_and_actual_chronology_are_required(self):
        self.observed(); entry = self.state['sessoes'][0]; q=self.event['sessions'][3]
        self.assertEqual(pq.finish_evidence(self.root,entry,q,self.now)[0], '2026-11-07T19:01:00Z')
        entry['fontes'][0]['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'changed'):pq.finish_evidence(self.root,entry,q,self.now)

    def test_publication_buffer_and_forged_calendar_are_rejected(self):
        item = self.prepared()
        pq.publication_guard(self.root,item,self.now)
        at = cloud.instant(self.event['largada_utc'])-timedelta(hours=1)
        with self.assertRaisesRegex(ValueError,'window closed'):pq.publication_guard(self.root,item,at)
        item['race_start_utc'] = '2026-11-09T17:00:00Z'
        with self.assertRaisesRegex(ValueError,'calendar differs'):pq.publication_guard(self.root,item,self.now)

    def test_q1_q2_foreign_and_ambiguous_finish_do_not_unlock_forecast(self):
        self.observed();entry=self.state['sessoes'][0];q=self.event['sessions'][3];source=entry['fontes'][0]
        rawpath=self.root/source['arquivo_local'];original=json.loads(rawpath.read_text())[0]
        for records in ([dict(original,qualifying_phase=1)],[dict(original,qualifying_phase=2)],
                        [dict(original,meeting_key=1298)],[original,original],
                        [dict(original,date='2026-11-07T21:00:00Z')]):
            raw=json.dumps(records).encode();rawpath.write_bytes(raw);source['sha256']=hashlib.sha256(raw).hexdigest()
            with self.assertRaises(ValueError):pq.finish_evidence(self.root,entry,q,self.now)

    def test_uncommitted_or_untracked_automation_never_collects(self):
        self.observed()
        with patch.object(pq,'source_control',side_effect=ValueError('Uncommitted automation')), \
             patch.object(pq.fontes,'coletar_snapshot') as collect:
            with self.assertRaisesRegex(ValueError,'Uncommitted'):pq.prepare(self.root,self.config,self.state,self.now)
            collect.assert_not_called()

    def test_missing_descriptive_tyres_do_not_replace_predictive_q_gates(self):
        self.observed();self.state['sessoes'][0]['estado']='parcial'
        with patch.object(pq,'source_control',return_value={}), \
             patch.object(pq.fontes,'coletar_snapshot',side_effect=ValueError('Predictive snapshot still required')) as collect:
            with self.assertRaisesRegex(ValueError,'Predictive snapshot'):pq.prepare(self.root,self.config,self.state,self.now)
            collect.assert_called_once()

    def test_lookahead_checks_references_without_acquisition(self):
        from operacao2026.readiness import check_upcoming
        self.assertEqual(check_upcoming(ROOT,datetime(2026,11,3,tzinfo=timezone.utc))['verified_events'],1)
        self.assertFalse(check_upcoming(ROOT,datetime(2026,11,3,tzinfo=timezone.utc))['new_acquisition'])
        path=self.root/'frontend_assets/race_weekend.json';path.parent.mkdir()
        shutil.copyfile(ROOT/'frontend_assets/race_weekend.json',path)
        (self.root/'operacao2026/driver_circuit_reviews.json').write_text('{}')
        with self.assertRaisesRegex(RuntimeError,'interlagos'):check_upcoming(self.root,datetime(2026,11,3,tzinfo=timezone.utc))

    def test_attempts_are_spaced_and_bounded_without_network(self):
        self.observed(); self.base.mkdir(parents=True)
        receipt=self.base/'attempts.json'
        receipt.write_text(json.dumps([dict(utc=(self.now-timedelta(minutes=30)).isoformat())]))
        with patch.object(pq.fontes,'coletar_snapshot',side_effect=AssertionError('No early retry')):
            self.assertEqual(pq.prepare(self.root,self.config,self.state,self.now)['status'],'retry_deferred')
        receipt.write_text(json.dumps([dict(utc=(self.now-timedelta(hours=3)).isoformat())]*4))
        with self.assertRaisesRegex(RuntimeError,'exhausted'):pq.prepare(self.root,self.config,self.state,self.now)

    def test_scientific_rejection_is_preserved_without_registration(self):
        self.observed()
        with patch.object(pq,'source_control',return_value={}), patch.object(pq.fontes,'coletar_snapshot',side_effect=ValueError('Incomplete prior race')):
            with self.assertRaisesRegex(ValueError,'Incomplete'):pq.prepare(self.root,self.config,self.state,self.now)
        self.assertEqual(json.loads((self.base/'attempts.json').read_text())[0]['status'],'blocked')
        self.assertFalse((self.root/pq.REGISTRY).exists())

    def test_retained_emission_recovers_exact_bytes_and_rejects_changes(self):
        item = self.prepared(); self.base.mkdir(parents=True)
        for directory in item['directories']:
            path=self.root/directory/'raw.json'; path.parent.mkdir(parents=True);path.write_text('immutable original\n')
        pq.retain(self.root,self.base,item)
        for directory in item['directories']:shutil.rmtree(self.root/directory)
        pq.restore(self.root,self.base,item)
        for directory in item['directories']:self.assertEqual((self.root/directory/'raw.json').read_text(),'immutable original\n')
        target=self.root/item['directories'][0]/'raw.json';target.write_text('different')
        with self.assertRaisesRegex(ValueError,'differs'):pq.restore(self.root,self.base,item)

    def test_path_traversal_and_symlinks_are_rejected(self):
        with self.assertRaises(ValueError):pq.relative_file(self.root,'../outside')
        (self.root/'link').symlink_to(ROOT/'VERSION')
        with self.assertRaises(ValueError):pq.relative_file(self.root,'link')

    def test_canonical_preparation_invokes_existing_producer_and_retains_once(self):
        self.observed(); calls=[]
        def snapshot(root,snapshot_id,**kwargs):
            path=root/snapshot_id/'indice.json';path.parent.mkdir(parents=True);path.write_text('{}')
        def run(root,args):
            calls.append(args)
            if args[1]=='estado':return json.dumps(dict(estado='pronto',registros_classificacao=22))
            emission=args[args.index('--id')+1]
            path=root/'reports/operacao_2026/emissoes'/emission/'manifesto.json'
            path.parent.mkdir(parents=True);path.write_text('immutable emitted bytes')
            return ''
        with patch.object(pq,'source_control',return_value={}), patch.object(pq.fontes,'coletar_snapshot',side_effect=snapshot), patch.object(pq,'utc_now',return_value=self.now), \
             patch.object(pq,'verify_cards'),patch.object(pq,'register_and_project') as register:
            result=pq.prepare(self.root,self.config,self.state,self.now,run)
            self.assertEqual(result['status'],'prepared');self.assertEqual(len(calls),2)
            self.assertNotIn('--openf1-diretorio',calls[1]);register.assert_called_once()
            calls.clear();register.reset_mock()
            recovered=pq.prepare(self.root,self.config,self.state,self.now+timedelta(minutes=10),run)
            self.assertEqual(recovered['files'],result['files']);self.assertEqual(calls,[])
            register.assert_called_once()

    def test_team_artworks_match_actual_emission_participants(self):
        pq.verify_cards(ROOT,ROOT/'reports/operacao_2026/emissoes/mexico-prospectivo-20261101T0435Z',2026)

    def test_complete_historical_registry_and_restored_sources_are_available(self):
        from registro_emissoes import DECLARACOES,validar_declaracoes
        additional=json.loads((ROOT/pq.REGISTRY).read_text())
        registry=validar_declaracoes(ROOT,(*DECLARACOES,*additional))
        self.assertGreaterEqual(len(registry),19)
        receipt=json.loads((ROOT/'reports/automacao_saopaulo_20261103/restoration-plan.json').read_text())
        self.assertTrue(receipt['original_utc_fields_unchanged'])
        for row in receipt['files']:
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])

    def test_blocked_retry_stays_actionable_but_future_q_does_not_alert(self):
        for status in ('blocked','blocked_retry_deferred','publication_window_closed'):
            with self.assertRaisesRegex(RuntimeError,'review'):pq.check_health(dict(forecast=dict(status=status)))
        self.assertEqual(pq.check_health(dict(forecast=dict(status='waiting_for_observed_qualifying')))['status'],
                         'waiting_for_observed_qualifying')

    def test_sao_paulo_reference_is_current_and_sources_are_byte_verified(self):
        reference=json.loads((ROOT/'operacao2026/driver_circuit_reviews.json').read_text())['2026:interlagos']
        self.assertEqual((reference['corners'],reference['direction'],reference['length_km']),(15,'anti_horario',4.309))
        for field in ('source','altitude_source'):
            receipt=reference[field]
            raw=(ROOT/'reports/automacao_saopaulo_20261103/sources'/receipt['arquivo']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),receipt['sha256'])


if __name__=='__main__':unittest.main()
