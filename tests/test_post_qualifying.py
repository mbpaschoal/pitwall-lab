"""Hosted forecasts must keep temporal gates, immutable evidence and bounded retry."""
from copy import deepcopy
import csv
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
        for review in pq.policy(self.root).get('roster_reviews', []):
            name = review['source']['file']
            (self.root/name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, self.root/name)
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

    def test_projection_failure_preserves_registry_and_previous_public_asset(self):
        registry = self.root/pq.REGISTRY
        original_registry = b' [ ]\n'
        registry.write_bytes(original_registry)
        asset = self.root/'frontend_assets/race_weekend.json'
        asset.parent.mkdir()
        original_asset = b'{"previous":"published"}\n'
        asset.write_bytes(original_asset)
        output = []
        def rejected(root, args):
            destination = root/args[args.index('--saida')+1]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b'{"incomplete":')
            output.append(destination)
            raise RuntimeError('Synthetic projection failure')
        with patch('registro_emissoes.validar_declaracoes') as validate:
            with self.assertRaisesRegex(RuntimeError, 'Synthetic projection failure'):
                pq.register_and_project(self.root, self.prepared(), rejected)
        validate.assert_called_once()
        self.assertEqual(registry.read_bytes(), original_registry)
        self.assertEqual(asset.read_bytes(), original_asset)
        self.assertNotEqual(output[0], asset)
        self.assertEqual(output[0].read_bytes(), b'{"incomplete":')

    def test_failed_first_projection_creates_no_registry_or_public_asset(self):
        output = []
        def rejected(root, args):
            destination = root/args[args.index('--saida')+1]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b'{"incomplete":')
            output.append(destination)
            raise RuntimeError('Synthetic projection failure')
        with patch('registro_emissoes.validar_declaracoes'):
            with self.assertRaisesRegex(RuntimeError, 'Synthetic projection failure'):
                pq.register_and_project(self.root, self.prepared(), rejected)
        self.assertFalse((self.root/pq.REGISTRY).exists())
        self.assertFalse((self.root/'frontend_assets/race_weekend.json').exists())
        self.assertEqual(output[0].read_bytes(), b'{"incomplete":')

    def test_registered_emission_reprojection_is_staged_and_keeps_registry_bytes(self):
        item = self.prepared()
        registry = self.root/pq.REGISTRY
        registry.write_text(' '+json.dumps([item['declaration']])+'\n')
        original = registry.read_bytes()
        asset = self.root/'frontend_assets/race_weekend.json'
        asset.parent.mkdir();asset.write_bytes(b'{"previous":true}\n')
        projected = b'{"next":"complete"}\n'
        def project(root, args):
            destination = root/args[args.index('--saida')+1]
            self.assertNotEqual(destination, asset)
            self.assertEqual(asset.read_bytes(), b'{"previous":true}\n')
            destination.write_bytes(projected)
        with patch('registro_emissoes.validar_declaracoes') as validate:
            pq.register_and_project(self.root, item, project)
        validate.assert_not_called()
        self.assertEqual(registry.read_bytes(), original)
        self.assertEqual(asset.read_bytes(), projected)

    def test_empty_or_invalid_projection_cannot_commit_a_registration(self):
        for payload in (None, b'{"incomplete":', b'[]'):
            with self.subTest(payload=payload):
                def incomplete(root, args):
                    if payload is not None:
                        destination = root/args[args.index('--saida')+1]
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(payload)
                with patch('registro_emissoes.validar_declaracoes'):
                    with self.assertRaises((FileNotFoundError, ValueError)):
                        pq.register_and_project(self.root, self.prepared(), incomplete)
                self.assertFalse((self.root/pq.REGISTRY).exists())
                self.assertFalse((self.root/'frontend_assets/race_weekend.json').exists())

    def test_projection_failure_recovers_retained_forecast_without_new_emission(self):
        self.observed();calls=[];projection_attempts=[]
        def snapshot(root, snapshot_id, **kwargs):
            path = root/snapshot_id/'indice.json'
            path.parent.mkdir(parents=True);path.write_text('{}')
        def run(root, args):
            calls.append(args)
            if args[0] == 'preparar_dashboard_race_weekend.py':
                destination = root/args[args.index('--saida')+1]
                destination.parent.mkdir(parents=True, exist_ok=True)
                projection_attempts.append(destination)
                if len(projection_attempts) == 1:
                    destination.write_bytes(b'{"incomplete":')
                    raise RuntimeError('Synthetic projection failure')
                destination.write_bytes(b'{"recovered":true}\n')
            elif args[1] == 'estado':
                return json.dumps(dict(estado='pronto', registros_classificacao=22))
            else:
                emission = args[args.index('--id')+1]
                path = root/'reports/operacao_2026/emissoes'/emission/'manifesto.json'
                path.parent.mkdir(parents=True);path.write_bytes(b'immutable synthetic emission')
                shutil.copyfile(self.probabilities()/'probabilidades.csv', path.parent/'probabilidades.csv')
            return ''
        def registered(root):
            path = root/pq.REGISTRY
            return {cloud.identity(d): d for d in json.loads(path.read_text())} if path.exists() else {}
        with patch('registro_emissoes.carregar', side_effect=registered), \
             patch('registro_emissoes.validar_declaracoes'), \
             patch.object(pq, 'source_control', return_value={}), \
             patch.object(pq.fontes, 'coletar_snapshot', side_effect=snapshot) as capture, \
             patch.object(pq, 'utc_now', return_value=self.now), \
             patch.object(pq, 'review_forecast_roster', return_value={'status':'fixture'}):
            with self.assertRaisesRegex(RuntimeError, 'Synthetic projection failure'):
                pq.prepare(self.root, self.config, self.state, self.now, run)
            self.assertFalse((self.root/pq.REGISTRY).exists())
            prepared = json.loads((self.base/'prepared.json').read_text())
            before = {name: hashlib.sha256((self.root/name).read_bytes()).hexdigest()
                      for name in prepared['files']}
            recovered = pq.prepare(self.root, self.config, self.state, self.now+timedelta(minutes=10), run)
            capture.assert_called_once()
        self.assertEqual(recovered['status'], 'prepared')
        self.assertEqual(sum(len(args)>1 and args[1]=='emitir' for args in calls), 1)
        self.assertEqual(before, {name: hashlib.sha256((self.root/name).read_bytes()).hexdigest()
                                 for name in prepared['files']})
        self.assertEqual((self.root/'frontend_assets/race_weekend.json').read_bytes(), b'{"recovered":true}\n')
        self.assertEqual(projection_attempts[0].read_bytes(), b'{"incomplete":')

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
            shutil.copyfile(self.probabilities()/'probabilidades.csv',path.parent/'probabilidades.csv')
            return ''
        with patch.object(pq,'source_control',return_value={}), patch.object(pq.fontes,'coletar_snapshot',side_effect=snapshot), patch.object(pq,'utc_now',return_value=self.now), \
             patch.object(pq,'review_forecast_roster',return_value={'status':'fixture'}), \
             patch.object(pq,'register_and_project') as register:
            result=pq.prepare(self.root,self.config,self.state,self.now,run)
            self.assertEqual(result['status'],'prepared');self.assertEqual(len(calls),2)
            self.assertNotIn('--openf1-diretorio',calls[1]);register.assert_called_once()
            self.assertEqual(result['artwork_coverage']['status'],'partial')
            self.assertFalse(result['artwork_coverage']['required_for_forecast'])
            calls.clear();register.reset_mock()
            recovered=pq.prepare(self.root,self.config,self.state,self.now+timedelta(minutes=10),run)
            self.assertEqual(recovered['files'],result['files']);self.assertEqual(calls,[])
            register.assert_called_once()

    def test_team_artworks_match_actual_emission_participants(self):
        result = pq.verify_cards(ROOT,ROOT/'reports/operacao_2026/emissoes/mexico-prospectivo-20261101T0435Z',2026)
        self.assertEqual((result['status'],result['verified_driver_pairs']),('complete',22))
        self.assertFalse(result['required_for_forecast'])

    def probabilities(self, duplicate=False):
        """Synthetic unknown IDs deliberately do not claim Camara's canonical ID."""
        path=self.root/'emission';path.mkdir(exist_ok=True)
        with (path/'probabilidades.csv').open('w') as stream:
            writer=csv.DictWriter(stream,fieldnames=['piloto_id','equipe_id_entrada'])
            writer.writeheader()
            writer.writerows(dict(piloto_id='synthetic_'+str(0 if duplicate else i),equipe_id_entrada='haas')
                             for i in range(22))
        return path

    def test_optional_artwork_absence_is_reported_without_forecast_rejection(self):
        result=pq.verify_cards(self.root,self.probabilities(),2026)
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['catalog_status'],'unavailable')
        self.assertEqual(len(result['missing']),22)
        self.assertFalse(result['required_for_forecast'])
        self.assertEqual(result['missing'][0]['poses'],[0,1,2])

    def test_missing_optional_art_never_weakens_the_population_guard(self):
        with self.assertRaisesRegex(ValueError,'complete 2026 population'):
            pq.verify_cards(self.root,self.probabilities(duplicate=True),2026)

    def test_new_driver_has_no_borrowed_history_and_frozen_v1_stays_eligible(self):
        from operacao2026 import previsao
        from treinar_modelo_v1 import motivos_inelegibilidade
        from tests.test_operacao_2026_r1 import corrida,resultado
        previous=corrida(19,'2026-11-01','rodriguez','2026-10-31')
        target=corrida(20,'2026-11-08','interlagos','2026-11-07')
        target['time']='17:00:00Z'
        q=[self.roster_rows()[-1]]
        state=previsao.preparar_alvo(target,q,prospectivo=True)
        old=dict(resultado('ocon'),Constructor=dict(constructorId='haas'))
        rows,audit=previsao.gerar_entradas(state,[previous,target],{('2026','19'):[old]})
        self.assertEqual(rows[0]['piloto_id'],'synthetic_rookie_id')
        self.assertEqual(rows[0]['n_posicoes_5'],0)
        self.assertIsNone(rows[0]['media_posicao_final_5'])
        self.assertIsNone(rows[0]['taxa_podios_5'])
        self.assertEqual(rows[0]['historico_piloto_insuficiente'],1)
        self.assertEqual(rows[0]['n_participacoes_equipe_5'],1)
        self.assertEqual(audit['janelas'][0]['piloto'],[])
        self.assertEqual(motivos_inelegibilidade(rows[0]),[])

    def roster_rows(self):
        rows=[dict(position=str(i+1),Driver=dict(driverId='synthetic_'+str(i),givenName='Fixture',familyName=str(i)),
                   Constructor=dict(constructorId='fixture')) for i in range(21)]
        rows.append(dict(position='22',Driver=dict(driverId='synthetic_rookie_id',givenName='Rafael',familyName='Camara'),
                         Constructor=dict(constructorId='haas')))
        return rows

    def roster_snapshot(self, records, snapshot='fixture', circuit='interlagos'):
        from tests.test_operacao_2026_r1 import raw_page,source
        race=dict(season='2026',round='20',date=self.event['data'],time='17:00:00Z',
                  Circuit=dict(circuitId=circuit),QualifyingResults=records)
        raw=raw_page([race],'classificacao')
        pq.fontes.gravar_snapshot(self.root/'data/operacao_2026/snapshots',snapshot,
                                 {'classificacao':[source(raw,'classificacao',20,got=self.now.isoformat())]})

    def test_review_accepts_canonical_id_unchanged_and_only_literal_names_and_team(self):
        rows=self.roster_rows();self.roster_snapshot(rows)
        result=pq.review_forecast_roster(self.root,self.event,'fixture')
        self.assertEqual(result['admitted_entries'],[dict(driver_id='synthetic_rookie_id',team_id='haas')])
        self.assertEqual(result['id_origin'],'unchanged_qualifying_record')
        rows[-1]['Driver']['familyName']='Câmara';self.roster_snapshot(rows,'accent')
        self.assertEqual(pq.review_forecast_roster(self.root,self.event,'accent')['status'],'verified')

    def test_stale_replaced_driver_wrong_team_similar_name_and_foreign_gp_block(self):
        for field,value in [('id','ocon'),('team','ferrari'),('name','Camara Junior')]:
            rows=self.roster_rows()
            if field=='id':rows[-1]['Driver']['driverId']=value
            elif field=='team':rows[-1]['Constructor']['constructorId']=value
            else:rows[-1]['Driver']['familyName']=value
            self.roster_snapshot(rows,field)
            with self.assertRaises(ValueError):pq.review_forecast_roster(self.root,self.event,field)
        self.roster_snapshot(self.roster_rows(),'foreign',circuit='americas')
        with self.assertRaisesRegex(ValueError,'another event'):
            pq.review_forecast_roster(self.root,self.event,'foreign')

    def test_review_source_tampering_is_rejected_before_opening_q(self):
        source=pq.policy(self.root)['roster_reviews'][0]['source']
        (self.root/source['file']).write_text('modified announcement')
        with patch.object(pq.fontes,'ler_snapshot') as read:
            with self.assertRaisesRegex(ValueError,'source changed'):
                pq.review_forecast_roster(self.root,self.event,'unused')
            read.assert_not_called()

    def test_stale_roster_stops_before_inference_or_registry(self):
        self.observed();rows=self.roster_rows();rows[-1]['Driver']['driverId']='ocon'
        def snapshot(root,snapshot_id,**kwargs):self.roster_snapshot(rows,snapshot_id)
        calls=[]
        def run(root,args):
            calls.append(args)
            if args[1]!='estado':self.fail('Stale roster reached inference')
            return json.dumps(dict(estado='pronto',registros_classificacao=22))
        with patch.object(pq,'source_control',return_value={}),patch.object(pq.fontes,'coletar_snapshot',side_effect=snapshot):
            with self.assertRaisesRegex(ValueError,'replaced driver'):
                pq.prepare(self.root,self.config,self.state,self.now,run)
        self.assertEqual(len(calls),1)
        self.assertFalse((self.root/pq.REGISTRY).exists())
        self.assertFalse((self.base/'prepared.json').exists())

    def test_complete_historical_registry_and_restored_sources_are_available(self):
        from registro_emissoes import DECLARACOES,validar_declaracoes
        additional=json.loads((ROOT/pq.REGISTRY).read_text())
        registry=validar_declaracoes(ROOT,(*DECLARACOES,*additional))
        self.assertGreaterEqual(len(registry),19)
        receipt=json.loads((ROOT/'reports/automacao_saopaulo_20261103/restoration-plan.json').read_text())
        self.assertTrue(receipt['original_utc_fields_unchanged'])
        for row in receipt['files']:
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])

    def test_frozen_model_loads_with_its_original_fingerprint_without_inference(self):
        from operacao2026.previsao import carregar_modelo
        model=carregar_modelo(str(ROOT/'models/modelo_v1/modelo.joblib'),
            str(ROOT/'models/modelo_v1/metadados.json'),str(ROOT/'data/preparado/colunas.json'))
        self.assertEqual(model['hashes']['modelo'],'16718ea5c4a7f662e72f09d38b073e545df1bba5c64c87b2cc1a0973ad9116e3')

    def test_openf1_fallback_passes_the_explicit_target_config_to_the_frozen_cli(self):
        self.observed();calls=[]
        def snapshot(root,snapshot_id,**kwargs):
            path=root/snapshot_id/'indice.json';path.parent.mkdir(parents=True);path.write_text('{}')
        bundle=(self.root/'data/operacao_2026/fontes_alternativas/q-2026-interlagos-test').resolve()
        bundle.mkdir(parents=True);(bundle/'inventario.json').write_text('{}')
        def run(root,args):
            calls.append(args)
            if args[1]=='estado':return json.dumps(dict(estado='aguardando_classificacao',registros_classificacao=0))
            path=root/'reports/operacao_2026/emissoes'/args[args.index('--id')+1]/'manifesto.json'
            path.parent.mkdir(parents=True);path.write_text('immutable fixture');return ''
        with patch.object(pq,'source_control',return_value={}),patch.object(pq.fontes,'coletar_snapshot',side_effect=snapshot), \
             patch.object(pq.weekend,'qualification_bundle',return_value=bundle),patch.object(pq,'utc_now',return_value=self.now), \
             patch.object(pq,'review_forecast_roster',return_value={'status':'fixture'}), \
             patch.object(pq,'verify_cards',return_value={'status':'complete'}),patch.object(pq,'register_and_project'):
            result=pq.prepare(self.root,self.config,self.state,self.now,run)
        emission=calls[1]
        self.assertEqual(emission[emission.index('--openf1-evento')+1],str(self.config.resolve()))
        self.assertEqual(emission[emission.index('--circuito')+1],'interlagos')
        self.assertEqual(result['identity'],[2026,20,'interlagos'])

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
