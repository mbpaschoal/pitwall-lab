"""Hosted scheduling, idempotence and archive isolation without HTTP."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from operacao2026 import cloud, weekend

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'operacao2026/eventos/mexico2026.json'


class CloudTests(unittest.TestCase):
    def test_calendar_network_failure_keeps_discovery_pending_with_original_error(self):
        def unavailable(request, timeout):
            raise URLError('offline synthetic failure')
        def factory(directory, interval):
            return cloud.CaptureClient(directory, interval, opener=unavailable)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'Calendar unavailable'):
                cloud.discover(root, datetime(2026,11,6,tzinfo=timezone.utc), factory)
            base = root/cloud.STATE/'descoberta'
            self.assertFalse((base/'ultima_consulta.json').exists())
            receipt = json.loads(next(base.glob('*/coleta_online.json')).read_text())
            self.assertEqual(receipt['fontes'], [])
            self.assertEqual(receipt['falhas'][0]['endpoint'], 'calendar')

    def test_session_catalogue_network_failure_does_not_cache_a_discovery(self):
        calendar = {'MRData': dict(total='1', offset='0', RaceTable=dict(season='2026', Races=[
            dict(round='20', date='2026-11-08', raceName='São Paulo Grand Prix',
                 Circuit=dict(circuitId='interlagos', Location=dict(locality='São Paulo', lat='-23.7', long='-46.7')))
        ]))}
        class Response(io.BytesIO):
            status = 200
            def geturl(self):
                return 'https://api.jolpi.ca/ergast/f1/2026/?limit=100&offset=0'
        def opener(request, timeout):
            if request.full_url.startswith('https://api.jolpi.ca/'):
                return Response(json.dumps(calendar).encode())
            raise URLError('offline synthetic failure')
        def factory(directory, interval):
            return cloud.CaptureClient(directory, interval, opener=opener,
                                       sleeper=lambda seconds: None, clock=lambda: 0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'Session catalogue unavailable'):
                cloud.discover(root, datetime(2026,11,6,tzinfo=timezone.utc), factory)
            base = root/cloud.STATE/'descoberta'
            self.assertFalse((base/'ultima_consulta.json').exists())
            self.assertFalse((root/cloud.STATE/'configuracoes').exists())
            capture = next(base.glob('*/coleta_online.json'))
            receipt = json.loads(capture.read_text())
            self.assertEqual(receipt['fontes'][0]['endpoint'], 'calendar')
            self.assertEqual(json.loads((capture.parent/'calendar.json').read_text()), calendar)
            self.assertEqual(receipt['falhas'][0]['endpoint'], 'sessions')

    def test_forecast_validates_new_receipts_against_a_post_collection_clock(self):
        start=datetime(2026,11,1,23,31,tzinfo=timezone.utc);end=start+timedelta(minutes=2)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'operacao2026').mkdir();(root/'frontend_assets').mkdir()
            (root/'operacao2026/forecast_policy.json').write_text('{}')
            with patch.object(cloud,'datetime') as clock,patch.object(cloud,'discover',return_value=CONFIG), \
                 patch.object(weekend,'collect',return_value=self.state()), \
                 patch('operacao2026.post_qualifying.prepare',return_value=dict(status='event_not_admitted')) as prepare:
                clock.now.side_effect=[start,end]
                cloud.collect(root)
            self.assertEqual(prepare.call_args.args[-1],end)

    def test_real_discovery_client_preserves_first_response_in_a_new_directory(self):
        payload=json.dumps(dict(MRData=dict(offset='0',total='0',RaceTable=dict(season='2026',Races=[])))).encode()
        class Response(io.BytesIO):
            status=200
            def geturl(self):return 'https://api.jolpi.ca/ergast/f1/2026/?limit=100&offset=0'
        def factory(directory,interval):return cloud.CaptureClient(directory,interval,opener=lambda *a,**kw:Response(payload))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertIsNone(cloud.discover(root,datetime(2026,11,3,tzinfo=timezone.utc),factory))
            raws=list((root/cloud.STATE/'descoberta').rglob('calendar.json'))
            self.assertEqual(len(raws),1);self.assertEqual(raws[0].read_bytes(),payload)
            self.assertTrue(raws[0].with_name('coleta_online.json').exists())

    def test_blocked_forecast_does_not_block_valid_descriptive_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'operacao2026').mkdir()
            (root/'frontend_assets').mkdir()
            (root/'operacao2026/forecast_policy.json').write_text('{}')
            with patch.object(cloud,'discover',return_value=CONFIG),patch.object(weekend,'collect',return_value=self.state()), \
                 patch('operacao2026.post_qualifying.prepare',side_effect=ValueError('Prior result unavailable')):
                result=cloud.collect(root,datetime(2026,11,1,23,31,tzinfo=timezone.utc))
            self.assertTrue(result['changed'])
            self.assertEqual(result['forecast']['status'],'blocked')
            self.assertEqual(json.loads((root/cloud.PUBLIC).read_text())['rodada'],19)

    def test_free_access_waits_through_the_live_window_without_any_collection(self):
        event=weekend.load_event(CONFIG)
        race=next(s for s in event['sessions'] if s['session_name']=='Race')
        expected=cloud.instant(race['consulta_publica_apos_utc'])
        for now in [datetime(2026,11,1,19,30,tzinfo=timezone.utc),
                    datetime(2026,11,1,23,9,tzinfo=timezone.utc),expected]:
            with self.subTest(now=now), tempfile.TemporaryDirectory() as tmp:
                with patch.object(cloud,'discover',return_value=CONFIG), patch.object(weekend,'collect',side_effect=AssertionError('No live HTTP')):
                    result=cloud.collect(Path(tmp),now)
                self.assertFalse(result['changed'])
                self.assertEqual(result['reason'],'provider_live_window')
                self.assertEqual(cloud.instant(result['retry_after_utc']),expected)
                self.assertFalse((Path(tmp)/cloud.PUBLIC).exists())

    def test_catalogue_time_and_conservative_public_access_are_separate(self):
        event=weekend.load_event(CONFIG)
        race=next(s for s in event['sessions'] if s['session_name']=='Race')
        self.assertEqual(cloud.instant(race['date_end']),datetime(2026,11,1,22,tzinfo=timezone.utc))
        self.assertEqual(cloud.historical_access_after(event,datetime(2026,11,1,23,9,tzinfo=timezone.utc)),
                         datetime(2026,11,1,23,30,tzinfo=timezone.utc))
        race.pop('consulta_publica_apos_utc')
        self.assertEqual(cloud.historical_access_after(event,datetime(2026,11,1,22,29,tzinfo=timezone.utc)),
                         datetime(2026,11,1,22,30,tzinfo=timezone.utc))

    def test_optional_public_access_deferral_cannot_shorten_the_free_tier_wait(self):
        event=weekend.load_event(CONFIG)
        race=next(s for s in event['sessions'] if s['session_name']=='Race')
        race['consulta_publica_apos_utc']='2026-11-01T22:29:00Z'
        with self.assertRaisesRegex(ValueError,'cannot shorten'):
            cloud.historical_access_after(event,datetime(2026,11,1,21,tzinfo=timezone.utc))

    def test_free_access_resumes_after_the_window_and_preserves_finish_validation(self):
        event=weekend.load_event(CONFIG)
        self.assertIsNone(cloud.historical_access_after(event,datetime(2026,11,1,23,31,tzinfo=timezone.utc)))
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(cloud,'discover',return_value=CONFIG), patch.object(weekend,'collect',side_effect=ValueError('Session catalogue changed; review configuration')):
                with self.assertRaisesRegex(ValueError,'catalogue changed'):
                    cloud.collect(Path(tmp),datetime(2026,11,1,23,31,tzinfo=timezone.utc))

    def test_restricted_access_keeps_last_public_data_and_reports_a_pending_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);public=root/cloud.PUBLIC;public.parent.mkdir(parents=True)
            public.write_text(json.dumps(self.state()));before=public.read_bytes()
            with patch.object(cloud,'discover',return_value=CONFIG),patch.object(weekend,'collect',side_effect=weekend.ProviderAccessUnavailable(401)):
                result=cloud.collect(root,datetime(2026,11,1,23,31,tzinfo=timezone.utc))
            self.assertEqual(result,dict(changed=False,reason='provider_access_restricted',http_status=401))
            self.assertEqual(public.read_bytes(),before)

    def test_original_capture_archive_preserves_bytes_and_rejects_symlinks(self):
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=root/cloud.STATE/'mexico/raw.json';raw.parent.mkdir(parents=True)
            raw.write_bytes(b'{"source":"original"}\n')
            output=root/'captures.tar.gz';cloud.archive_captures(root,output)
            with tarfile.open(output) as archive:
                self.assertEqual(archive.extractfile(str(raw.relative_to(root))).read(),raw.read_bytes())
            self.assertEqual(cloud.collection_files(root), ([raw], len(raw.read_bytes())))
            with patch.object(cloud, 'MAX_STATE_MIB', 0):
                with self.assertRaisesRegex(ValueError, 'exceeds 0 MiB'):
                    cloud.archive_captures(root,output)
            (raw.parent/'link').symlink_to(raw)
            with self.assertRaises(ValueError):cloud.archive_captures(root,output)
    def state(self,round_=19):
        return dict(schema='pitwall-weekend-public-v1',temporada=2026,rodada=round_,circuito_id='rodriguez',atualizado_em_utc='2026-10-30T10:00:00Z',automacao=cloud.AUTOMATION,sessoes=[dict(session_key=11397,nome='Practice 1',estado='aguardando_sessao',fontes=[])])

    def test_timestamp_and_forecast_only_do_not_create_versions(self):
        first=self.state();second=deepcopy(first)
        second['atualizado_em_utc']='2026-10-30T11:00:00Z'
        second['previsao_meteorologica']={'horas':[{'temperature_2m':25}]}
        second['sessoes'][0]['fontes']=[dict(obtido_em_utc='later',sha256='different')]
        self.assertEqual(cloud.semantic(first),cloud.semantic(second))
        second['sessoes'][0]['estado']='dados_recebidos'
        self.assertNotEqual(cloud.semantic(first),cloud.semantic(second))

    def test_next_weekend_preserves_previous_gp(self):
        old=self.state();new=self.state(20)
        merged=cloud.merge_archive(old,new)
        self.assertEqual(merged['rodada'],20)
        self.assertEqual(merged['arquivo_eventos'],[old])
        self.assertEqual(cloud.merge_archive(merged,new)['arquivo_eventos'],[old])

    def test_known_configuration_requires_no_discovery_http(self):
        now=datetime(2026,10,30,12,tzinfo=timezone.utc)
        def no_http(*args):raise AssertionError('No HTTP')
        self.assertEqual(cloud.discover(ROOT,now,client_factory=no_http),CONFIG)

    def test_next_gp_is_discovered_from_canonical_date_and_meeting(self):
        from datetime import timedelta
        calendar={'MRData':dict(total='1',offset='0',RaceTable=dict(season='2026',Races=[dict(round='20',date='2026-11-08',raceName='São Paulo Grand Prix',Circuit=dict(circuitId='interlagos',Location=dict(locality='São Paulo',lat='-23.7',long='-46.7')))]))}
        catalog=deepcopy(json.loads(CONFIG.read_text())['sessions'])
        for session in catalog:
            session.update(meeting_key=1299,session_key=session['session_key']+100,location='São Paulo',country_name='Brazil')
            for field in ('date_start','date_end'):
                session[field]=(cloud.instant(session[field])+timedelta(days=7)).isoformat()
        class Source:
            def __init__(self,*args):self.manifest={'fontes':[]}
            def capture(self,provider,endpoint,*args):
                self.manifest['fontes'].append(dict(provider=provider,endpoint=endpoint,obtido_em_utc='2026-11-06T19:00:00Z'))
                return calendar if provider=='jolpica' else catalog
        with tempfile.TemporaryDirectory() as tmp:
            path=cloud.discover(Path(tmp),datetime(2026,11,6,19,tzinfo=timezone.utc),Source)
            event=weekend.load_event(path)
            self.assertEqual(cloud.identity(event),(2026,20,'interlagos'))
            self.assertEqual(event['sessions'][-1]['meeting_key'],1299)
            calendar['MRData']['RaceTable']['season']='2025'
            with tempfile.TemporaryDirectory() as other:
                with self.assertRaises(ValueError):cloud.discover(Path(other),datetime(2026,11,6,19,tzinfo=timezone.utc),Source)

    def test_cooldown_survives_runner_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);base=root/cloud.STATE/'rodriguez-2026';base.mkdir(parents=True)
            (base/'estado.json').write_text(json.dumps(dict(retry_after_utc='2026-10-30T14:00:00Z')))
            with patch.object(cloud,'discover',side_effect=AssertionError('No HTTP')):
                result=cloud.collect(root,datetime(2026,10,30,12,tzinfo=timezone.utc))
            self.assertFalse(result['changed'])
            self.assertEqual(result['reason'],'provider_cooldown')

    def test_driver_update_publishes_even_when_native_weekend_is_unchanged(self):
        event=weekend.load_event(CONFIG)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/cloud.PUBLIC;path.parent.mkdir(parents=True)
            path.write_text(json.dumps(self.state()));before=path.read_bytes()
            (root/'frontend_assets/pilotos_condicoes.json').write_text('{}')
            state=self.state();state['nome']=event['nome']
            with patch.object(cloud,'discover',return_value=CONFIG), \
                 patch.object(weekend,'collect',return_value=state), \
                 patch.object(weekend,'public_status',return_value=self.state()), \
                 patch('operacao2026.driver_archive.update',return_value=dict(changed=True,status='updated',races=67)):
                result=cloud.collect(root,datetime(2026,11,3,21,tzinfo=timezone.utc))
            self.assertTrue(result['changed'])
            self.assertEqual(result['pilotos']['races'],67)
            self.assertEqual(path.read_bytes(),before)

    def test_release_requires_data_and_updates_both_languages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'publicacao/templates').mkdir(parents=True)
            (root/'VERSION').write_text('0.4.1\n')
            (root/'publicacao/templates/requirements.txt').write_text('# Pitwall Lab 0.4.1: presentation\n')
            for name in ('CHANGELOG.md','CHANGELOG.en.md'):
                (root/name).write_text('# Changes\n\n## 0.4.1 — 2026-10-30\n\nPrevious release\n')
            with self.assertRaises(ValueError):cloud.prepare_release(dict(changed=False),root)
            result=dict(changed=True,evento='Mexico',sessoes_completas=1,sessoes=5)
            self.assertEqual(cloud.prepare_release(result,root),'0.4.2')
            self.assertIn('0.4.2',(root/'CHANGELOG.en.md').read_text())
            self.assertIn('0.4.2',(root/'CHANGELOG.md').read_text())

    def test_sprint_weekend_is_not_replaced_by_normal_format(self):
        event=json.loads(CONFIG.read_text());event['sessions']=[s for s in event['sessions'] if s['session_name'] not in ('Practice 2','Practice 3')]
        sprint=deepcopy(event['sessions'][0]);sprint.update(session_key=9991,session_name='Sprint',session_type='Race')
        sprint_q=deepcopy(event['sessions'][0]);sprint_q.update(session_key=9992,session_name='Sprint Qualifying',session_type='Qualifying')
        event['sessions'].extend([sprint,sprint_q])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'event.json';path.write_text(json.dumps(event))
            self.assertEqual(len(weekend.load_event(path)['sessions']),5)
        self.assertIsNone(weekend.finished([dict(session_key=9992,meeting_key=sprint_q['meeting_key'],date=sprint_q['date_end'],message='SESSION FINISHED',qualifying_phase=1)],sprint_q))

    def test_ui_archive_does_not_borrow_latest_gp(self):
        from pitwall.dashboard.weekend_views import load_status
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'frontend_assets').mkdir()
            (root/cloud.PUBLIC).write_text(json.dumps(cloud.merge_archive(self.state(),self.state(20))))
            self.assertEqual(load_status(root,2026,19,'rodriguez')['rodada'],19)
            self.assertIsNone(load_status(root,2026,18,'americas'))


if __name__=='__main__':unittest.main()
