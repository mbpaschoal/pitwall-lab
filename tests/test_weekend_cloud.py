"""Hosted scheduling, idempotence and archive isolation without HTTP."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from operacao2026 import cloud, weekend

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'operacao2026/eventos/mexico2026.json'


class CloudTests(unittest.TestCase):
    def test_original_capture_archive_preserves_bytes_and_rejects_symlinks(self):
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=root/cloud.STATE/'mexico/raw.json';raw.parent.mkdir(parents=True)
            raw.write_bytes(b'{"source":"original"}\n')
            output=root/'captures.tar.gz';cloud.archive_captures(root,output)
            with tarfile.open(output) as archive:
                self.assertEqual(archive.extractfile(str(raw.relative_to(root))).read(),raw.read_bytes())
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
