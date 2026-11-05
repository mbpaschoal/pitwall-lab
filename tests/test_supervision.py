"""Read-only supervision, temporal counterexamples, durable deduplication."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from pitwall.operations import supervision as s

ROOT=Path(__file__).resolve().parents[1]


class SupervisionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name); self.clock=datetime(2026,11,5,15,tzinfo=timezone.utc)
        context=patch.object(s,'utc_now',side_effect=lambda:self.clock); context.start(); self.addCleanup(context.stop)
        self.conclusion='success'; self.fail_release=False; self.calls=[]; self.html=b'<html><p>Schedule 17:00</p></html>'
        self.supervisor=s.Supervisor(ROOT,self.base/'state',self.base/'archive',self.fetch)

    def fetch(self,url,missing=False):
        self.calls.append(url)
        if '/actions/workflows/' in url:
            return s.raw_json({'workflow_runs':[dict(id=1,head_branch='main',event='schedule',conclusion=self.conclusion,
                                                   updated_at=self.clock.isoformat(),html_url='https://github.com/example',head_sha='a'*40)]})
        if '/releases/' in url:
            if self.fail_release: raise RuntimeError('Public source HTTP 403')
            return None
        if '/frontend_assets/' in url: return b'{"pending":{}}'
        return self.html

    def test_workflow_success_is_not_forecast_or_observed_qualifying(self):
        result=self.supervisor.run()
        self.assertEqual(result['p1']['status'],'pre_q_no_public_pair')
        self.assertFalse(result['p1']['admissible']); self.assertFalse(result['scientific_execution'])
        self.assertFalse(result['changed']); self.assertFalse(result['post_race'])
        self.assertTrue(all('/dispatches' not in url for url in self.calls))

    def test_repeated_failures_are_deduplicated_and_recovery_is_reported(self):
        self.conclusion='failure'; first=self.supervisor.run(); self.assertTrue(first['changed'])
        second=self.supervisor.run(force=True); self.assertFalse(second['changed'])
        self.conclusion='success'; third=self.supervisor.run(force=True); self.assertTrue(third['changed'])
        self.assertFalse(third['queue'])
        self.assertEqual(len(list((self.base/'archive/runs').glob('*.json'))),3)

    def test_restart_retains_cursor_and_twenty_minute_cooldown(self):
        self.supervisor.run(); self.calls=[]
        fresh=s.Supervisor(ROOT,self.base/'state',self.base/'archive',self.fetch)
        self.assertEqual(fresh.run()['status'],'cooldown'); self.assertFalse(self.calls)
        self.assertFalse(fresh.run(force=True)['changed'])

    def test_rate_limit_is_indeterminate_and_never_missing_release(self):
        self.fail_release=True
        result=self.supervisor.run()
        self.assertEqual(result['p1']['status'],'indeterminate')
        self.assertTrue(any(row['kind']=='P1_validation' for row in result['queue']))
        self.assertFalse(result['p1']['admissible'])

    def test_deadline_does_not_create_late_probabilities(self):
        self.clock=datetime(2026,11,8,16,tzinfo=timezone.utc)
        result=self.supervisor.run()
        self.assertEqual(result['p1']['status'],'missing_public_pair_deadline')
        self.assertFalse(any(p.name=='paired-probabilities.json' for p in self.base.rglob('*')))

    def test_official_document_change_is_review_only_and_stays_queued(self):
        self.supervisor.run(); self.clock+=timedelta(hours=25)
        self.html=b'<html><p>Schedule 18:00</p></html>'
        result=self.supervisor.run()
        reviews=[r for r in result['queue'] if r['kind']=='official_document_changed']
        self.assertEqual(len(reviews),2); self.assertTrue(result['changed'])
        next_result=self.supervisor.run(force=True)
        self.assertFalse(next_result['changed'])
        self.assertEqual(len([r for r in next_result['queue'] if r['kind']=='official_document_changed']),2)

    def test_dynamic_script_changes_do_not_create_document_review(self):
        self.assertEqual(s.semantic(b'<p>17:00</p><script>random1</script>'),s.semantic(b'<p>17:00</p><script>random2</script>'))
        self.assertNotEqual(s.semantic(b'<p>17:00</p>'),s.semantic(b'<p>18:00</p>'))

    def test_documents_have_one_daily_check_and_immutable_hash_checked_copies(self):
        first=self.supervisor.run(); self.calls=[]
        self.supervisor.run(force=True)
        self.assertFalse(any(url in s.OFFICIAL for url in self.calls))
        for row in first['sources']:
            if row['sha256']:
                raw=(self.base/'archive/objects'/row['sha256']).read_bytes()
                self.assertEqual(s.sha(raw),row['sha256'])
        self.assertTrue((self.base/'archive/latest.pt.md').exists())
        self.assertTrue((self.base/'archive/latest.en.md').exists())

    def test_existing_object_is_not_overwritten_on_conflicting_bytes(self):
        path=self.base/'evidence'; s.immutable(path,b'first')
        with self.assertRaisesRegex(ValueError,'collision'): s.immutable(path,b'changed')
        self.assertEqual(path.read_bytes(),b'first')

    def test_bad_asset_digest_and_size_are_rejected(self):
        asset=dict(digest='sha256:'+'a'*64,state='uploaded',size=5,browser_download_url=s.OFFICIAL[0])
        with self.assertRaisesRegex(ValueError,'digest/size'): self.supervisor.asset(asset,[])
        asset['size']=s.MAX_BYTES+1
        with self.assertRaisesRegex(ValueError,'metadata'): self.supervisor.asset(asset,[])

    def test_open_dependency_finding_and_stale_audit_remain_visible_once(self):
        gate={'checked_at_utc':(self.clock-timedelta(days=8)).isoformat(),'decision':{
            'accepted_for_restricted_local_profile':True,'counts':{'critical':0,'high':1},
            'residual_high':[{'package':'zod','version':'3.25.76','advisory':'GHSA-mrhx-c7xc-m3w5'}]}}
        (self.base/'dependency-gate.json').write_bytes(s.raw_json(gate))
        first=self.supervisor.run(); self.assertTrue(first['changed'])
        self.assertEqual(first['dependency_audit']['counts']['high'],1)
        self.assertTrue({'dependency_security','dependency_audit_due'} <= {r['kind'] for r in first['queue']})
        self.assertFalse(self.supervisor.run(force=True)['changed'])

    def test_post_race_scores_keep_unknown_targets_and_reject_future_finish(self):
        pairs=[dict(piloto_id='a',probabilidade_v1=.8,probabilidade_q=.5),
               dict(piloto_id='b',probabilidade_v1=.1,probabilidade_q=.5)]
        posterior=dict(identity=s.IDENTITY,targets={'a':1,'b':None},observed_race_finish_utc='2026-11-08T19:00:00Z',
                       sources=[dict(sha256='b'*64,obtido_em_utc='2026-11-08T19:02:00Z')])
        record=dict(schema='pitwall-p1-post-race-descriptive-v1',pair_sha256='a'*64,posterior=posterior,
                    **s.p1.score_rows(pairs,posterior['targets']))
        event={'largada_utc':'2026-11-08T17:00:00Z'}; asset={'created_at':'2026-11-08T19:03:00Z'}
        with self.assertRaisesRegex(ValueError,'chronology'): s.posterior_checks(record,{'pairs':pairs},'a'*64,event,asset)
        self.clock=datetime(2026,11,9,tzinfo=timezone.utc)
        s.posterior_checks(record,{'pairs':pairs},'a'*64,event,asset)
        self.assertEqual(record['known_targets'],1); self.assertEqual(record['unknown_targets'],1)
        self.assertAlmostEqual(record['scores']['v1']['brier'],.04)
        changed=deepcopy(record); changed['scores']['v1']['brier']=0
        with self.assertRaisesRegex(ValueError,'score'): s.posterior_checks(changed,{'pairs':pairs},'a'*64,event,asset)
        changed=deepcopy(record); changed['posterior']['targets']['foreign']=0
        with self.assertRaisesRegex(ValueError,'population'): s.posterior_checks(changed,{'pairs':pairs},'a'*64,event,asset)

    def test_n8n_export_has_no_credentials_shell_model_or_external_message(self):
        workflow=json.loads((ROOT/'automation/n8n/supervisor.json').read_text())
        self.assertEqual({n['type'] for n in workflow['nodes']},{'n8n-nodes-base.manualTrigger','n8n-nodes-base.scheduleTrigger','n8n-nodes-base.httpRequest'})
        http=next(n for n in workflow['nodes'] if n['type'].endswith('httpRequest'))
        self.assertEqual(http['parameters']['url'],'http://127.0.0.1:5681/run')
        self.assertFalse(any(n.get('credentials') for n in workflow['nodes']))
        self.assertEqual(workflow['settings']['timezone'],'America/Sao_Paulo')

    def test_runtime_does_not_inherit_tokens_and_binds_only_loopback(self):
        spec=importlib.util.spec_from_file_location('pitwall_n8n_local',ROOT/'automation/n8n/local.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with patch.dict('os.environ',{'GITHUB_TOKEN':'test-never-export','DROPBOX_TOKEN':'test-never-export'}):
            environment=module.environment()
        self.assertNotIn('GITHUB_TOKEN',environment); self.assertNotIn('DROPBOX_TOKEN',environment)
        self.assertEqual(environment['N8N_LISTEN_ADDRESS'],'127.0.0.1')
        self.assertEqual(environment['N8N_COMMUNITY_PACKAGES_ENABLED'],'false')
        self.assertEqual(environment['N8N_PAYLOAD_SIZE_MAX'],'1')
        self.assertEqual(set(json.loads(environment['NODES_INCLUDE'])),{'n8n-nodes-base.manualTrigger','n8n-nodes-base.scheduleTrigger','n8n-nodes-base.httpRequest'})

    def test_audit_gate_rejects_critical_unknown_high_and_expanded_runtime(self):
        spec=importlib.util.spec_from_file_location('pitwall_n8n_audit',ROOT/'automation/n8n/audit_result.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        report={'metadata':{'vulnerabilities':{'critical':0,'high':1,'moderate':18,'low':5}},'advisories':{
            '1':dict(severity='high',module_name='zod',url='https://github.com/advisories/'+module.RESIDUAL,findings=[{'version':'3.25.76'}])}}
        result=module.evaluate(report,module.runtime_profile())
        self.assertTrue(result['accepted_for_restricted_local_profile']); self.assertFalse(result['zero_vulnerabilities_claimed'])
        for change in [('severity','critical'),('module_name','foreign'),('url','https://github.com/advisories/GHSA-other')]:
            changed=deepcopy(report); changed['advisories']['1'][change[0]]=change[1]
            self.assertFalse(module.evaluate(changed,module.runtime_profile())['accepted_for_restricted_local_profile'])
        env=module.runtime_profile(); env['N8N_LISTEN_ADDRESS']='0.0.0.0'
        with self.assertRaises(ValueError): module.evaluate(report,env)
        with self.assertRaises(ValueError): module.evaluate({'error':'HTTP 403'},module.runtime_profile())

    def test_url_allowlist_rejects_foreign_repo_credentials_and_insecure_transport(self):
        for url in ('http://api.github.com/repos/'+s.p1.REPO+'/releases',
                    'https://github.com/foreign/repo/releases/download/x/y',
                    'https://api.github.com.evil.test/repos/'+s.p1.REPO+'/releases',
                    'https://user:pass@www.formula1.com/en/racing/2026/brazil'):
            self.assertFalse(s.allowed(url))
        self.assertTrue(s.allowed(s.p1.BASE+'/releases/tags/'+s.TAG))

    def test_real_frozen_pair_validator_handles_native_string_identity_and_rejects_late_metadata(self):
        folder=ROOT/'reports/prospectivo_p1_20261105'
        sys.path.insert(0,str(folder)); self.addCleanup(lambda:sys.path.remove(str(folder)))
        import test_pair_predictions as fixtures
        import pair_predictions
        fixture=fixtures.PairTests('test_complete_pair_is_prepared_and_never_claims_publication')
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        pair=fixture.pair(); raw=s.p1.json_bytes(pair)
        path=self.base/'pair.json'; path.write_bytes(raw)
        asset=dict(state='uploaded',digest='sha256:'+s.sha(raw),size=len(raw),id=1,
                   created_at='2026-11-07T20:02:00Z',updated_at='2026-11-07T20:02:00Z',
                   browser_download_url='https://github.com/'+s.p1.REPO+'/releases/download/'+s.TAG+'/paired-probabilities.json')
        event={'largada_utc':'2026-11-08T17:00:00Z'}
        with patch.object(pair_predictions,'utc_now',return_value=s.p1.utc('2026-11-07T21:00:00Z')):
            accepted,receipt=s.pair_checks(ROOT,path,asset,event)
            self.assertEqual(len(accepted['pairs']),22); self.assertTrue(receipt['publication_verified'])
            late=dict(asset,updated_at='2026-11-08T16:00:00Z')
            with self.assertRaises(ValueError): s.pair_checks(ROOT,path,late,event)
            foreign=deepcopy(pair); foreign['event']['circuito_id']='foreign'
            for row in foreign['pairs']: row['circuito_id']='foreign'
            path.write_bytes(s.p1.json_bytes(foreign)); wrong=dict(asset,digest='sha256:'+s.sha(path.read_bytes()),size=path.stat().st_size)
            with self.assertRaisesRegex(ValueError,'event/calendar'): s.pair_checks(ROOT,path,wrong,event)


if __name__=='__main__': unittest.main()
