"""Controlled hosted-publication failures; no real prediction or network writes."""
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from pitwall.operations import prospective as auto

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/auto.FROZEN))
import test_pair_predictions as fixtures
import pair_predictions as comparison


class FakeGitHub:
    def __init__(self,clock):
        self.clock=clock;self.value=None;self.rows=[];self.raw={};self.writes=[]
    def release(self,tag):return self.value
    def create(self,tag,commit):
        self.value=dict(id=123,draft=False,published_at=self.clock.isoformat(),tag_name=tag)
        self.writes.append(('release',tag));return self.value
    def assets(self,release):return list(self.rows)
    def upload(self,release,name,raw):
        if any(r['name']==name for r in self.rows):raise ValueError('No replacement')
        asset=dict(id=len(self.rows)+1,name=name,state='uploaded',size=len(raw),
                   digest='sha256:'+auto.digest(raw),created_at=self.clock.isoformat(),updated_at=self.clock.isoformat(),
                   browser_download_url='https://github.com/mbpaschoal/pitwall-lab/releases/download/'+release['tag_name']+'/'+name)
        self.rows.append(asset);self.raw[asset['id']]=raw;self.writes.append(('asset',name));return asset
    def download(self,asset):return self.raw[asset['id']]


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.PairTests('test_complete_pair_is_prepared_and_never_claims_publication')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.clock=self.fixture.now;self.api=FakeGitHub(self.clock)
        (self.root/'VERSION').write_text('0.0.0\n')
        verifier=self.root/'tests/browser/verificar_p1.cjs';verifier.parent.mkdir(parents=True)
        verifier.write_bytes((ROOT/'tests/browser/verificar_p1.cjs').read_bytes())
        self.entry=next(iter(self.fixture.registry.values()))
        self.event=dict(temporada=2026,rodada=20,circuito_id='interlagos',largada_utc='2026-11-08T17:00:00Z',data='2026-11-08')
        self.output=self.root/'automatic';self.output.mkdir()
        self.helpers=runpy.run_path(str(ROOT/auto.FROZEN/'pair_predictions.py'))
        self.helpers['prepare'].__globals__['utc_now']=lambda:self.clock
        self.receipt_module=runpy.run_path(str(ROOT/auto.FROZEN/'verify_published_pair.py'))
        self.receipt_module['validate'].__globals__['utc_now']=lambda:self.clock
        for obj,name,value in [(auto,'now',lambda:self.clock),(auto,'frozen',lambda root:self.helpers),
                               (auto,'host_spec',lambda root,pair:dict(identity=[2026,20,'interlagos'],rows=pair['pairs'],source_asset_sha256='a'*64)),
                               (auto.subprocess,'check_output',lambda *a,**k:'a'*40)]:
            context=patch.object(obj,name,value);context.start();self.addCleanup(context.stop)
        self.registry_patch=patch('registro_emissoes.carregar',return_value=self.fixture.registry)
        self.registry_patch.start();self.addCleanup(self.registry_patch.stop)
        context=patch.object(auto.subprocess,'run',side_effect=self.verify_cli);context.start();self.addCleanup(context.stop)

    def verify_cli(self,args,**kwargs):
        file=Path(args[args.index('--pair-file')+1]);asset_id=int(args[args.index('--asset-id')+1])
        asset=next(a for a in self.api.rows if a['id']==asset_id)
        receipt=self.receipt_module['validate'](file,asset)
        Path(args[args.index('--destination')+1]).write_bytes(auto.json_bytes({'receipt':receipt,'server_asset_metadata':asset}))

    def execute(self,entry=True):
        return auto.run_event(self.root,self.event,self.entry if entry else None,self.output,self.api)

    def host(self,pair_sha):
        observed=(self.clock-timedelta(seconds=1)).isoformat()
        return dict(schema='pitwall-p1-served-forecast-v1',base='https://pitwall-lab.streamlit.app',
                    source_asset_sha256='a'*64,version='0.0.0',
                    automation_commit='a'*40,verifier_sha256=auto.digest((ROOT/'tests/browser/verificar_p1.cjs').read_bytes()),
                    pair_sha256=pair_sha,identity=[2026,20,'interlagos'],status='passed',completed_at_utc=self.clock.isoformat(),
                    cases=[dict(engine=e,width=w,lang=l,status='passed',rows_checked=22,observed_at_utc=observed)
                           for e in ('chromium','webkit') for w in (390,1440) for l in ('pt','en')])

    def test_first_pair_uses_real_frozen_helpers_and_never_claims_host_acceptance(self):
        before={p.name:auto.digest(p.read_bytes()) for p in self.fixture.folder.iterdir()}
        result=self.execute()
        self.assertTrue(result['publication_verified']);self.assertFalse(result['admissible'])
        self.assertTrue((self.output/'host-input.json').exists())
        self.assertEqual(before,{p.name:auto.digest(p.read_bytes()) for p in self.fixture.folder.iterdir()})
        self.assertEqual(sum(name==auto.PAIR_NAME for kind,name in self.api.writes),1)

    def test_recovery_reuses_original_public_pair_without_recomputing_or_replacing(self):
        self.execute();original=auto.unique_asset(self.api.rows,auto.PAIR_NAME)
        original_raw=self.api.download(original);self.clock+=timedelta(hours=3);self.api.clock=self.clock
        self.output=self.root/'retry';self.output.mkdir()
        self.helpers['prepare']=lambda *a:(_ for _ in ()).throw(AssertionError('No new pair allowed'))
        result=self.execute();self.assertTrue(result['publication_verified'])
        self.assertEqual((self.output/auto.PAIR_NAME).read_bytes(),original_raw)
        self.assertEqual(sum(name==auto.PAIR_NAME for kind,name in self.api.writes),1)

    def test_existing_pair_is_rebound_to_native_probabilities_not_just_self_reported_hashes(self):
        self.execute();asset=auto.unique_asset(self.api.rows,auto.PAIR_NAME)
        raw=json.loads(self.api.raw[asset['id']]);raw['pairs'][0]['probabilidade_q']=.99
        self.api.raw[asset['id']]=auto.json_bytes(raw)
        self.output=self.root/'tampered';self.output.mkdir()
        with self.assertRaisesRegex(ValueError,'differs from the native'):self.execute()

    def test_no_native_forecast_never_publishes_a_pair(self):
        result=self.execute(False);self.assertEqual(result['status'],'waiting_for_native_forecast')
        self.assertEqual(self.api.writes,[])

    def test_deadline_records_missing_coverage_once_and_never_backfills(self):
        self.clock=auto.utc('2026-11-08T16:00:00Z');self.api.clock=self.clock
        result=self.execute();self.assertFalse(result['admissible'])
        self.assertIsNone(auto.unique_asset(self.api.rows,auto.PAIR_NAME))
        self.assertIsNotNone(auto.unique_asset(self.api.rows,'coverage-missing-pair.json'))
        before=list(self.api.writes);self.execute();self.assertEqual(self.api.writes,before)

    def test_pair_attempt_cooldown_and_four_attempt_cap_are_durable(self):
        release=self.api.create('p1-2026-20-interlagos','a'*40)
        self.api.upload(release,'attempt-1.json',b'{}')
        self.assertEqual(self.execute()['status'],'retry_deferred')
        self.clock+=timedelta(hours=3);self.api.clock=self.clock
        for n in (2,3,4):self.api.upload(release,'attempt-'+str(n)+'.json',b'{}')
        with self.assertRaisesRegex(RuntimeError,'attempts exhausted'):self.execute()

    def test_late_server_upload_is_not_admitted(self):
        self.api.clock=auto.utc('2026-11-08T16:00:00Z')
        with self.assertRaises(ValueError):self.execute()
        self.assertFalse((self.output/'public-receipt.json').exists())

    def test_calendar_change_cannot_silently_expand_publication_window(self):
        self.event['largada_utc']='2026-11-08T18:00:00Z'
        with self.assertRaisesRegex(ValueError,'schedule changed'):self.execute()
        self.assertIsNone(auto.unique_asset(self.api.rows,auto.PAIR_NAME))

    def test_public_draft_release_cannot_prove_public_pair(self):
        self.api.create('p1-2026-20-interlagos','a'*40);self.api.value['draft']=True
        with self.assertRaisesRegex(ValueError,'not publicly available'):self.execute()

    def test_host_gate_requires_all_eight_cases_full_roster_and_real_public_origin(self):
        start=auto.utc(self.event['largada_utc']);receipt=self.host('a'*64)
        auto.validate_host(receipt,'a'*64,[2026,20,'interlagos'],start)
        for alteration in [lambda d:d['cases'].pop(),lambda d:d['cases'][0].update(rows_checked=21),
                           lambda d:d.update(base='http://localhost:8501'),lambda d:d['cases'][1].update(status='failed')]:
            changed=deepcopy(receipt);alteration(changed)
            with self.assertRaises(ValueError):auto.validate_host(changed,'a'*64,[2026,20,'interlagos'],start)
        self.clock=start
        with self.assertRaises(ValueError):auto.validate_host(receipt,'a'*64,[2026,20,'interlagos'],start)
        auto.prior_host(receipt,'a'*64,[2026,20,'interlagos'],start)

    def test_existing_host_evidence_avoids_new_browser_attempts_and_keeps_posterior_separate(self):
        result=self.execute();receipt=self.host(result['pair_sha256'])
        self.api.upload(self.api.value,'host-acceptance.json',auto.json_bytes(receipt))
        self.output=self.root/'accepted-recovery';self.output.mkdir()
        result=self.execute();self.assertTrue(result['admissible'])
        self.assertEqual(result['posterior']['status'],'waiting_for_race')
        self.assertFalse((self.output/'host-input.json').exists())

    def test_native_model_tampering_rejected_on_recovery(self):
        self.execute();self.output=self.root/'changed-model';self.output.mkdir()
        (self.root/'models/modelo_v1/modelo.joblib').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Original v1 artifacts changed'):self.execute()

    def test_finish_host_binds_live_pair_calendar_projection_and_server_upload_time(self):
        result=self.execute();receipt=self.host(result['pair_sha256'])
        folder=self.root/'operacao2026/eventos';folder.mkdir(parents=True)
        (folder/'fixture.json').write_bytes(auto.json_bytes(dict(schema='pitwall-weekend-event-v1',**self.event)))
        saved=self.output/'host-result.json';saved.write_bytes(auto.json_bytes(receipt))
        spec=self.output/'host-input.json'
        with patch('operacao2026.post_qualifying.policy',return_value={'events':[[2026,20,'interlagos']]}):
            done=auto.finish_host(self.root,spec,saved,self.api)
            self.assertTrue(done['admissible'])
            self.assertIsNotNone(auto.unique_asset(self.api.rows,'host-acceptance.json'))
            altered=json.loads(spec.read_text());altered['race_start_utc']='2026-11-09T17:00:00Z'
            spec.write_bytes(auto.json_bytes(altered))
            with self.assertRaisesRegex(ValueError,'calendar differs'):auto.finish_host(self.root,spec,saved,self.api)

    def test_duplicate_incomplete_assets_and_byte_replacements_rejected(self):
        release=self.api.create('p1-2026-20-interlagos','a'*40)
        asset=self.api.upload(release,'fixture.json',b'original')
        with self.assertRaisesRegex(ValueError,'replace immutable'):auto.persist_asset(self.api,release,self.api.rows,'fixture.json',b'new')
        with self.assertRaises(ValueError):auto.unique_asset([asset,asset],'fixture.json')
        asset['state']='starter'
        with self.assertRaises(ValueError):auto.unique_asset([asset],'fixture.json')

    def test_gp_scores_preserve_unknown_targets_and_use_frozen_clipping(self):
        pairs=[dict(piloto_id='a',probabilidade_v1=.2,probabilidade_q=.4),
               dict(piloto_id='b',probabilidade_v1=1.,probabilidade_q=0.)]
        result=auto.score_rows(pairs,{'a':1,'b':None})
        self.assertEqual(result['known_targets'],1);self.assertEqual(result['unknown_targets'],1)
        self.assertAlmostEqual(result['scores']['v1']['brier'],.64)
        self.assertAlmostEqual(result['scores']['q']['log_loss'],-__import__('math').log(.4))
        self.assertIsNone(auto.score_rows(pairs,{})['scores']['v1']['brier'])
        self.assertFalse(result['model_selection_performed'])


class ActualRuntimeTests(unittest.TestCase):
    def posterior_fixture(self):
        # Existing Mexico data are only a reader/target fixture, never a new P1 pair.
        import csv
        from registro_emissoes import carregar
        entry=carregar(ROOT)[(2026,19,'rodriguez')]
        directory=ROOT/entry['diretorio'];manifest=json.loads((directory/'manifesto.json').read_text())
        with (directory/'probabilidades.csv').open() as stream:rows=list(csv.DictReader(stream))
        return dict(event=manifest['evento'],v1_manifest_sha256=auto.digest((directory/'manifesto.json').read_bytes()),
                    pairs=[dict(piloto_id=r['piloto_id'],probabilidade_v1=float(r['probabilidade_modelo']),
                                probabilidade_q=.25,equipe_id_entrada=r['equipe_id_entrada']) for r in rows])

    def test_native_projection_reads_all_22_rows_with_canonical_integer_identity(self):
        spec=auto.host_spec(ROOT,self.posterior_fixture())
        self.assertEqual(spec['identity'],[2026,19,'rodriguez']);self.assertEqual(len(spec['rows']),22)
        self.assertEqual(len(spec['favorites']),3)

    def test_posterior_reader_scores_known_DNF_targets_separately_and_never_changes_pair(self):
        pair=self.posterior_fixture();original=deepcopy(pair)
        clock=auto.utc('2026-11-05T12:00:00Z');api=FakeGitHub(clock);release=api.create('p1-fixture-only','a'*40)
        event=dict(temporada=2026,rodada=19,circuito_id='rodriguez',data='2026-11-01',largada_utc='2026-11-01T20:00:00Z',
                   sessions=[dict(session_name='Race',session_key=11404)])
        with tempfile.TemporaryDirectory() as tmp,patch.object(auto,'now',return_value=clock):
            result=auto.post_race(ROOT,pair,'a'*64,Path(tmp),api,release,api.rows,event)
        self.assertEqual(result['known_targets'],22);self.assertEqual(pair,original)
        record=json.loads(api.raw[1]);self.assertEqual(record['posterior']['targets']['stroll'],0)
        self.assertFalse(record['model_selection_performed']);self.assertEqual(record['pair_sha256'],'a'*64)

    def test_posterior_source_timing_roster_team_and_session_fail_closed(self):
        from pitwall.data.driver_conditions import ASSET as BASELINE
        from pitwall.data.driver_updates import ASSET as UPDATES,seal
        pair=self.posterior_fixture();clock=auto.utc('2026-11-05T12:00:00Z')
        event=dict(temporada=2026,rodada=19,circuito_id='rodriguez',data='2026-11-01',largada_utc='2026-11-01T20:00:00Z',
                   sessions=[dict(session_name='Race',session_key=11404)])
        for kind in ['early_capture','foreign_team','missing_driver','foreign_session']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'frontend_assets').mkdir();api=FakeGitHub(clock);release=api.create('p1-fixture-only','a'*40)
                for name in [BASELINE,UPDATES,'frontend_assets/operacao_fim_semana.json']:(root/name).write_bytes((ROOT/name).read_bytes())
                updates=json.loads((root/UPDATES).read_text());candidate=updates['events']['2026:19'];config=deepcopy(event)
                if kind=='early_capture':candidate['sources'][0]['obtido_em_utc']='2026-11-01T20:01:00Z'
                elif kind=='foreign_team':candidate['results'][0]['team_id']='haas'
                elif kind=='missing_driver':candidate['results'].pop()
                else:config['sessions'][0]['session_key']=11408
                (root/UPDATES).write_bytes(auto.json_bytes(seal(updates)))
                with patch.object(auto,'now',return_value=clock),patch.object(auto,'host_spec',return_value={}):
                    with self.assertRaises(ValueError):auto.post_race(root,pair,'a'*64,root,api,release,api.rows,config)
                self.assertEqual(len(api.rows),0)

    def test_missing_observed_race_finish_prevents_scores_even_with_validated_results(self):
        from pitwall.data.driver_conditions import ASSET as BASELINE
        from pitwall.data.driver_updates import ASSET as UPDATES
        pair=self.posterior_fixture();clock=auto.utc('2026-11-05T12:00:00Z')
        event=dict(temporada=2026,rodada=19,circuito_id='rodriguez',data='2026-11-01',largada_utc='2026-11-01T20:00:00Z',
                   sessions=[dict(session_name='Race',session_key=11404)])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'frontend_assets').mkdir();api=FakeGitHub(clock);release=api.create('p1-fixture-only','a'*40)
            for name in [BASELINE,UPDATES,'frontend_assets/operacao_fim_semana.json']:(root/name).write_bytes((ROOT/name).read_bytes())
            path=root/'frontend_assets/operacao_fim_semana.json';state=json.loads(path.read_text())
            matches=[s for s in [state]+state.get('arquivo_eventos',[])
                     if [s.get(k) for k in ('temporada','rodada','circuito_id')]==[2026,19,'rodriguez']]
            self.assertEqual(len(matches),1)
            next(s for s in matches[0]['sessoes'] if s['nome']=='Race')['encerramento_observado_utc']=None
            path.write_bytes(auto.json_bytes(state))
            with patch.object(auto,'now',return_value=clock),patch.object(auto,'host_spec',side_effect=AssertionError('No forecast binding before observed Race finish')):
                result=auto.post_race(root,pair,'a'*64,root,api,release,api.rows,event)
            self.assertEqual(result['status'],'waiting_for_observed_race_finish');self.assertEqual(api.rows,[])

    def test_real_pre_Q_path_does_not_collect_infer_or_publish(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(auto,'now',return_value=auto.utc('2026-11-05T12:00:00Z')), \
                patch.object(auto.GitHub,'request',side_effect=AssertionError('No network allowed before Q')):
            result=auto.run(ROOT,Path(tmp)/'new')
        self.assertEqual([r['status'] for r in result],['waiting_for_observed_qualifying'])

    def test_final_coverage_gap_is_reported_without_failing_the_workflow(self):
        clock = auto.utc('2026-11-09T12:00:00Z')
        for status in ('missing_pair_deadline_closed', 'missing_host_before_race', 'blocked'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'p1'
                event = dict(status=status, identity=[2026, 20, 'interlagos'], admissible=False)
                with patch.object(auto, 'now', return_value=clock), patch.object(auto, 'run_event', return_value=event):
                    if status == 'blocked':
                        with self.assertRaisesRegex(RuntimeError, 'P1 needs attention'):
                            auto.run(ROOT, output)
                    else:
                        self.assertEqual(auto.run(ROOT, output), [event])
                self.assertEqual(json.loads((output / 'status.json').read_text())['events'], [event])

    def test_frozen_public_manifest_is_verified(self):
        self.assertEqual(auto.frozen(ROOT)['Q_SHA'],comparison.Q_SHA)

    def test_HTTP_404_is_only_missing_case_and_writes_require_actions_token(self):
        api=auto.GitHub();error=HTTPError(auto.BASE+'/test',404,'fixture',{},io.BytesIO())
        with patch.object(auto,'urlopen',side_effect=error):self.assertIsNone(api.release('p1-fixture'))
        error=HTTPError(auto.BASE+'/test',403,'fixture',{},io.BytesIO())
        with patch.object(auto,'urlopen',side_effect=error):
            with self.assertRaisesRegex(RuntimeError,'403'):api.release('p1-fixture')
        with patch.dict(auto.os.environ,{},clear=True):
            with self.assertRaisesRegex(ValueError,'token required'):api.create('p1-fixture','a'*40)

    def test_control_plane_reads_use_existing_actions_token_while_public_verifier_stays_original(self):
        captured=[]
        def opening(request,timeout):
            captured.append(request);return io.StringIO('{}')
        with patch.dict(auto.os.environ,{'GITHUB_TOKEN':'fixture-only-not-a-credential'}),patch.object(auto,'urlopen',side_effect=opening):
            auto.GitHub().release('p1-fixture')
        self.assertEqual(captured[0].get_header('Authorization'),'Bearer fixture-only-not-a-credential')
        self.assertNotIn('GITHUB_TOKEN',(ROOT/auto.FROZEN/'verify_published_pair.py').read_text())


if __name__=='__main__':unittest.main()
