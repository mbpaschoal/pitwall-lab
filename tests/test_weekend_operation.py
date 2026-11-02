"""Synthetic operational checks; no network, fitting or frozen-data edits."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from operacao2026 import weekend
from operacao2026.openf1_qualificacao import carregar, MAPEAMENTO_2026
ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'operacao2026/eventos/mexico2026.json'

class FakeClient:
    calls = []

    def __init__(self, destination, interval):
        self.destination = Path(destination)
        self.manifest = {'fontes': []}

    def capture(self, provider, endpoint, relative, url):
        self.calls.append(endpoint)
        payload = weekend.load_event(CONFIG)['sessions'] if endpoint == 'sessions' else {'hourly': {'time': [], 'temperature_2m': [], 'precipitation': [], 'wind_speed_10m': []}}
        raw = json.dumps(payload).encode()
        path = self.destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        self.manifest['fontes'].append(dict(endpoint=endpoint, provider=provider, arquivo=relative, url=url, status=200, sha256=hashlib.sha256(raw).hexdigest(), obtido_em_utc='2026-10-30T04:00:00Z'))
        return payload

class WeekendTests(unittest.TestCase):
    def test_isolated_track_zero_is_retained_but_its_mean_is_withheld(self):
        from tests.test_race_weather import event, observation
        data=dict(race_control=[event('10:00:00','SESSION STARTED'),event('10:04:00','SESSION FINISHED')],
                  weather=[observation('10:00:30',air_temperature=25,track_temperature=40),
                           observation('10:01:30',air_temperature=25,track_temperature=0),
                           observation('10:02:30',air_temperature=25,track_temperature=41),
                           observation('10:03:30',air_temperature=25,track_temperature=42)])
        original=deepcopy(data)
        result=weekend.observed_weather(data,dict(session_key=7,date_start='2024-01-01T10:00:00Z'))
        track=result['campos']['track_temperature']
        self.assertFalse(track['elegivel'])
        self.assertEqual(track['media_amostras'],30.75)
        self.assertEqual(track['qualidade']['registros'][0]['indice_fonte'],1)
        self.assertTrue(result['campos']['air_temperature']['elegivel'])
        self.assertEqual(data,original)
        for row in data['weather']:
            row['track_temperature']=0
        result=weekend.observed_weather(data,dict(session_key=7,date_start='2024-01-01T10:00:00Z'))
        self.assertTrue(result['campos']['track_temperature']['elegivel'])
        self.assertNotIn('qualidade',result['campos']['track_temperature'])

    def test_restricted_catalogue_keeps_its_receipt_without_overwriting_state(self):
        from io import BytesIO
        from urllib.error import HTTPError
        from pitwall.data.archive_collection import CaptureClient
        def restricted(request, timeout):
            raise HTTPError(request.full_url,401,'Restricted',{},BytesIO(b'{"detail":"restricted"}'))
        def client(destination, interval):
            return CaptureClient(destination,interval,opener=restricted)

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / 'data/operacao_2026/fins_de_semana/rodriguez-2026'
            base.mkdir(parents=True)
            checkpoint = base / 'estado.json'
            checkpoint.write_text('{"previous":true}')
            with self.assertRaises(weekend.ProviderAccessUnavailable) as caught:
                weekend.collect(CONFIG, tmp, datetime(2026,11,2,1,tzinfo=timezone.utc), client)
            self.assertEqual(caught.exception.status, 401)
            self.assertEqual(checkpoint.read_text(), '{"previous":true}')
            receipts = list(base.glob('*/coleta_online.json'))
            self.assertEqual(len(receipts), 1)
            self.assertEqual(json.loads(receipts[0].read_text())['fontes'][0]['status'], 401)

    def test_canonical_portrait_identity_requires_the_literal_profile(self):
        profile=dict(driver_number=44,first_name='Lewis',last_name='Hamilton',team_name='Ferrari',full_name='Lewis HAMILTON')
        data=dict(drivers=[profile],session_result=[dict(driver_number=44,position=2)])
        self.assertEqual(weekend.session_times(data,dict(session_name='Race'))[0]['piloto_id'],'hamilton')
        data['drivers'][0]['last_name']='Another Driver'
        self.assertIsNone(weekend.session_times(data,dict(session_name='Race'))[0]['piloto_id'])

    def test_qualifying_phases_preserve_source_values_and_missing_times(self):
        data=dict(drivers=[dict(driver_number=7)],session_result=[dict(driver_number=7,duration=[78.3,77.1,None])])
        row=weekend.session_times(data,dict(session_name='Qualifying'))[0]
        self.assertEqual([row['q1'],row['q2'],row['q3']],[78.3,77.1,None])
        self.assertEqual(row['duracao'],[78.3,77.1,None])

    def test_missing_practice_profile_withholds_projection_but_collects_qualifying(self):
        class MissingProfile(FakeClient):
            def capture(self, provider, endpoint, relative, url):
                self.calls.append(endpoint)
                event = weekend.load_event(CONFIG)
                if endpoint == 'sessions':
                    payload = event['sessions']
                elif endpoint == 'forecast':
                    payload = {'hourly': {'time': [], 'temperature_2m': [], 'precipitation': [], 'wind_speed_10m': []}}
                else:
                    session = next(s for s in event['sessions'] if str(s['session_key']) == relative.split('/')[0])
                    ids = dict(session_key=session['session_key'], meeting_key=session['meeting_key'])
                    result_number = 30 if session['session_name'] == 'Practice 3' else 7
                    payload = {
                        'race_control': [dict(ids, message='SESSION FINISHED', qualifying_phase=3, date=session['date_end'])],
                        'drivers': [dict(ids, driver_number=7, full_name='Synthetic Driver', team_name='Synthetic')],
                        'session_result': [dict(ids, driver_number=result_number, position=1)],
                        'weather': [dict(ids, air_temperature=20)],
                        'laps': [], 'stints': [], 'pit': [],
                    }[endpoint]
                raw = json.dumps(payload).encode()
                path = self.destination / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                self.manifest['fontes'].append(dict(endpoint=endpoint, provider=provider, arquivo=relative, url=url, status=200, sha256=hashlib.sha256(raw).hexdigest(), obtido_em_utc='2026-11-01T05:00:00Z'))
                return payload

        with tempfile.TemporaryDirectory() as tmp:
            state = weekend.collect(CONFIG, tmp, datetime(2026, 11, 1, 5, tzinfo=timezone.utc), MissingProfile)
            sessions = {s['nome']: s for s in state['sessoes']}
            partial = sessions['Practice 3']
            self.assertEqual(partial['estado'], 'parcial')
            self.assertEqual(partial['qualidade_identidade']['numero'], 30)
            self.assertNotIn('tempos', partial)
            self.assertEqual(partial['dados_descritivos'],dict(voltas_por_piloto=[],estrategias=[],paradas=[]))
            self.assertTrue(partial['fontes'])
            self.assertFalse(weekend.cached_session(partial, Path(tmp)))
            self.assertEqual(sessions['Qualifying']['estado'], 'dados_recebidos')
            self.assertEqual(sessions['Race']['estado'], 'aguardando_sessao')
            self.assertTrue((Path(tmp)/'data/operacao_2026/fins_de_semana/rodriguez-2026/estado.json').exists())

    def test_missing_profile_cannot_hide_conflicting_results(self):
        data = dict(drivers=[dict(driver_number=7)], session_result=[dict(driver_number=30), dict(driver_number=7), dict(driver_number=7)])
        with self.assertRaisesRegex(ValueError, 'duplicated'):
            weekend.session_times(data, {})

    def test_unlinked_pit_does_not_block_valid_qualifying_times_or_laps(self):
        entry=dict(estado='dados_recebidos')
        data=dict(drivers=[dict(driver_number=7,full_name='Synthetic')],
                  session_result=[dict(driver_number=7,position=1)],
                  laps=[dict(driver_number=7,lap_number=1,lap_duration=80)],
                  stints=[],pit=[dict(driver_number=236)])
        weekend.project_session(entry,data,dict(session_name='Qualifying',session_key=11400))
        self.assertEqual(entry['estado'],'parcial')
        self.assertEqual(entry['tempos'][0]['numero'],7)
        self.assertEqual(len(entry['dados_descritivos']['voltas_por_piloto']),1)
        self.assertNotIn('paradas',entry['dados_descritivos'])
        self.assertEqual(entry['qualidade_identidade']['grupos_bloqueados'],[dict(grupo='paradas',numeros=[236])])

    def test_missing_profile_cannot_hide_conflicting_laps(self):
        data = dict(drivers=[dict(driver_number=7)], session_result=[dict(driver_number=30)],
                    laps=[dict(driver_number=7,lap_number=1,lap_duration=90),dict(driver_number=7,lap_number=1,lap_duration=80)])
        with self.assertRaisesRegex(ValueError, 'Conflicting duplicate lap'):
            weekend.session_times(data, {})

    def test_completed_practice_projects_times_laps_and_pneus(self):

        class Completed(FakeClient):

            def capture(self, provider, endpoint, relative, url):
                if endpoint in ('sessions', 'forecast'):
                    value = super().capture(provider, endpoint, relative, url)
                else:
                    s = weekend.load_event(CONFIG)['sessions'][0]
                    ids = dict(session_key=s['session_key'], meeting_key=s['meeting_key'])
                    payload = {'race_control': [dict(ids, message='SESSION FINISHED', date='2026-10-30T19:30:00Z')], 'drivers': [dict(ids, driver_number=7, full_name='Synthetic Driver', team_name='Synthetic')], 'session_result': [dict(ids, driver_number=7, position=1, duration=88.7, number_of_laps=1)], 'weather': [dict(ids, air_temperature=20)], 'laps': [dict(ids, driver_number=7, lap_number=1, lap_duration=88.7)], 'stints': [dict(ids, driver_number=7, lap_start=1, lap_end=1, compound='SOFT')], 'pit': []}[endpoint]
                    raw = json.dumps(payload).encode()
                    p = self.destination / relative
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(raw)
                    self.calls.append(endpoint)
                    self.manifest['fontes'].append(dict(provider=provider, endpoint=endpoint, arquivo=relative, url=url, status=200, sha256=hashlib.sha256(raw).hexdigest(), obtido_em_utc='2026-10-30T20:00:00Z'))
                    value = payload
                self.manifest['fontes'][-1]['obtido_em_utc'] = '2026-10-30T20:00:00Z'
                return value
        with tempfile.TemporaryDirectory() as tmp:
            state = weekend.collect(CONFIG, tmp, datetime(2026, 10, 30, 20, tzinfo=timezone.utc), Completed)
            first = state['sessoes'][0]
            self.assertEqual(first['estado'], 'dados_recebidos')
            self.assertEqual(first['tempos'][0]['piloto'], 'Synthetic Driver')
            self.assertEqual(first['dados_descritivos']['voltas_por_piloto'][0]['voltas'], [[1, 88.7]])
            self.assertEqual(first['dados_descritivos']['estrategias'][0]['sequencia_stints'][0]['composto'], 'SOFT')
            self.assertTrue(all((s['estado'] == 'aguardando_sessao' for s in state['sessoes'][1:])))

    def test_future_sessions_do_not_query_results_or_telemetry(self):
        FakeClient.calls = []
        with tempfile.TemporaryDirectory() as tmp:
            state = weekend.collect(CONFIG, tmp, datetime(2026, 10, 30, 4, tzinfo=timezone.utc), FakeClient)
            self.assertEqual(FakeClient.calls, ['sessions', 'forecast'])
            self.assertTrue(all((s['estado'] == 'aguardando_sessao' for s in state['sessoes'])))
            self.assertIsNone(weekend.qualification_bundle(CONFIG, state, tmp))

    def test_qualifying_requires_q3_finish_and_matching_session(self):
        q = next((s for s in weekend.load_event(CONFIG)['sessions'] if s['session_name'] == 'Qualifying'))
        row = dict(session_key=q['session_key'], meeting_key=q['meeting_key'], message='SESSION FINISHED', qualifying_phase=1, date='2026-10-31T22:00:00Z')
        self.assertIsNone(weekend.finished([row], q))
        row['qualifying_phase'] = 3
        self.assertIsNotNone(weekend.finished([row], q))
        row['session_key'] -= 1
        with self.assertRaises(ValueError):
            weekend.finished([row], q)

    def test_calendar_configuration_rejects_duplicate_and_foreign_sessions(self):
        for change in ('duplicate', 'foreign'):
            event = weekend.load_event(CONFIG)
            if change == 'duplicate':
                event['sessions'][1]['session_key'] = event['sessions'][0]['session_key']
            else:
                event['sessions'][1]['location'] = 'Austin'
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / 'event.json'
                p.write_text(json.dumps(event))
                with self.assertRaises(ValueError):
                    weekend.load_event(p)

    def test_public_projection_does_not_publish_local_raw_paths(self):
        state = dict(temporada=2026, rodada=19, circuito_id='rodriguez', atualizado_em_utc='2026-10-30T04:00:00Z', sessoes=[dict(session_key=11400, nome='Qualifying', fontes=[dict(arquivo_local='/private/source', url='https://api.openf1.org/v1/drivers', sha256='abc')])])
        value = json.dumps(weekend.public_status(state))
        self.assertNotIn('/private/source', value)
        self.assertIn('https://api.openf1.org', value)

    def test_cache_validates_original_bytes_before_skipping_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'raw.json'
            p.write_bytes(b'[]')
            entry = dict(estado='dados_recebidos', fontes=[dict(arquivo_local='raw.json', sha256=hashlib.sha256(b'[]').hexdigest())])
            self.assertTrue(weekend.cached_session(entry, Path(tmp)))
            p.write_bytes(b'[1]')
            with self.assertRaises(ValueError):
                weekend.cached_session(entry, Path(tmp))

    def test_mexico_qualifying_can_be_admitted_without_borrowing_austin_identity(self):
        event = weekend.load_event(CONFIG)
        session = next((s for s in event['sessions'] if s['session_name'] == 'Qualifying'))
        identity = dict(session_key=session['session_key'], meeting_key=session['meeting_key'])
        drivers = [dict(identity, driver_number=n, first_name=v[2], last_name=v[3], team_name=v[4]) for (n, v) in MAPEAMENTO_2026.items()]
        results = [dict(identity, driver_number=d['driver_number'], position=i + 1) for (i, d) in enumerate(drivers)]
        data = dict(sessions=[session], drivers=drivers, session_result=results, race_control=[dict(identity, message='SESSION FINISHED', qualifying_phase=3, date='2026-10-31T22:00:00Z')])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = dict(schema='pitwall-source-availability-evidence-v1', sha256_arquivos={}, fontes=[])
            for (endpoint, payload) in data.items():
                name = 'openf1-q-' + endpoint + '.json'
                raw = json.dumps(payload).encode()
                (root / name).write_bytes(raw)
                sha = hashlib.sha256(raw).hexdigest()
                manifest['sha256_arquivos'][name] = sha
                manifest['fontes'].append(dict(arquivo=name, sha256=sha, status=200, url_solicitada='https://api.openf1.org/v1/' + endpoint, url_real='https://api.openf1.org/v1/' + endpoint, obtido_em_utc='2026-10-31T22:05:00Z'))
            (root / 'inventario.json').write_text(json.dumps(manifest))
            q = carregar(root, sessao_esperada=session, prefixo='openf1-q', mapeamento=MAPEAMENTO_2026)
            self.assertEqual(q['sessao']['session_key'], 11400)
            self.assertEqual(len(q['registros']), 22)
            with self.assertRaises(ValueError):
                carregar(root, sessao_esperada=dict(session, meeting_key=1297), prefixo='openf1-q')

    def test_provider_cooldown_is_not_lost_between_runs(self):
        value = weekend.retry_deadline({'fontes': [dict(status=429, retry_after='7200', obtido_em_utc='2026-10-30T04:00:00Z')]})
        self.assertEqual(value.hour, 6)

    def test_evaluation_excludes_retrospective_and_unvalidated_outcomes(self):
        from pitwall.research.prospective_evaluation import prospective_races
        row = dict(rodada=18, corrida='Synthetic', estado_previsao='previsao_registrada', resultado_posterior_validado=True, avaliavel_ranking=True, acertos_modelo=2, acertos_classificacao=1)
        self.assertEqual(len(prospective_races(dict(temporada=2026, corridas=[row]))), 1)
        for changed in (dict(row, estado_previsao='ensaio_retrospectivo'), dict(row, resultado_posterior_validado=False)):
            self.assertEqual(prospective_races(dict(temporada=2026, corridas=[changed])), [])

    def test_active_weekend_expires_and_never_overrides_another_event(self):
        from pitwall.dashboard.weekend_views import current_gp, load_status
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'frontend_assets').mkdir()
            state = dict(schema='pitwall-weekend-public-v1', temporada=2026, rodada=19, circuito_id='rodriguez', atualizado_em_utc='2026-10-30T04:00:00Z', sessoes=[dict(session_key=s['session_key'], nome=s['session_name'], inicio_utc=s['date_start'], fim_programado_utc=s['date_end'], estado='aguardando_sessao') for s in weekend.load_event(CONFIG)['sessions']])
            (root / 'frontend_assets/operacao_fim_semana.json').write_text(json.dumps(state))
            self.assertEqual(current_gp(root, datetime(2026, 10, 30, 16, tzinfo=timezone.utc)), '2026:19')
            self.assertIsNone(current_gp(root, datetime(2026, 11, 5, tzinfo=timezone.utc)))
            self.assertIsNone(load_status(root, 2026, 18, 'americas'))
if __name__ == '__main__':
    unittest.main()
