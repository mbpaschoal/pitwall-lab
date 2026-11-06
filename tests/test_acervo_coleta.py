"""Contraprovas do coletor complementar, sem rede e sem dados científicos reais."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlsplit

from coletar_acervo_historico import CaptureClient, collect_online, map_sessions, weather_coverage, weather_window, WEATHER_FIELDS


class Response(io.BytesIO):
    status = 200

    def geturl(self):
        return 'https://example.test/data'


class TestAcervoColeta(unittest.TestCase):
    def test_cache_valido_nao_repete_rede_e_divergencia_bloqueia(self):
        calls = []

        def opener(request, timeout):
            calls.append(request.full_url)
            return Response(b'[{"session_key": 1}]')

        with tempfile.TemporaryDirectory() as folder:
            client = CaptureClient(folder, opener=opener)
            args = ('openf1', 'laps', 'openf1/laps.json', 'https://example.test/data')
            self.assertEqual(client.capture(*args), [{'session_key': 1}])
            self.assertEqual(client.capture(*args), [{'session_key': 1}])
            self.assertEqual(len(calls), 1)
            (Path(folder) / 'openf1/laps.json').write_bytes(b'[]')
            with self.assertRaisesRegex(ValueError, 'Cache divergente'):
                client.capture(*args)
            self.assertEqual(len(calls), 1)

    def test_rate_limit_preserva_resposta_e_para_sem_retry(self):
        calls = []

        def opener(request, timeout):
            calls.append(1)
            raise HTTPError(request.full_url, 429, 'Too Many Requests', {'Retry-After': '60'}, io.BytesIO(b'{"detail":"wait"}'))

        with tempfile.TemporaryDirectory() as folder:
            client = CaptureClient(folder, opener=opener)
            with self.assertRaisesRegex(RuntimeError, 'HTTP 429'):
                client.capture('openf1', 'laps', 'raw/error.json', 'https://example.test/data')
            manifest = json.loads((Path(folder) / 'coleta_online.json').read_text())
            self.assertEqual(manifest['estado'], 'limite_do_provedor')
            self.assertEqual(manifest['retry_after'], '60')
            self.assertEqual(manifest['fontes'][0]['sha256'], sha256((Path(folder) / 'raw/error.json').read_bytes()).hexdigest())
            self.assertEqual(len(calls), 1)

    def test_arquivo_sem_recibo_nao_e_sobrescrito(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'already.json'
            path.write_bytes(b'original')
            client = CaptureClient(folder, opener=lambda *a, **k: self.fail('Rede não permitida'))
            with self.assertRaises(FileExistsError):
                client.capture('openf1', 'laps', path.name, 'https://example.test/data')
            self.assertEqual(path.read_bytes(), b'original')

    def test_retomada_explicitamente_tenta_429_expirado_e_preserva_resposta_anterior(self):
        args = ('openf1', 'laps', 'raw/laps.json', 'https://example.test/data')

        def limited(request, timeout):
            raise HTTPError(request.full_url, 429, 'Too Many Requests', {'Retry-After': '0'}, io.BytesIO(b'{"detail":"wait"}'))

        with tempfile.TemporaryDirectory() as folder:
            original = CaptureClient(folder, opener=limited)
            with self.assertRaisesRegex(RuntimeError, 'HTTP 429'):
                original.capture(*args)
            old = dict(original.manifest['fontes'][0])
            calls = []

            def success(request, timeout):
                calls.append(request.full_url)
                return Response(b'[{"session_key": 1}]')

            resumed = CaptureClient(folder, opener=success, retry_errors=True)
            self.assertEqual(resumed.capture(*args), [{'session_key': 1}])
            self.assertEqual(resumed.capture(*args), [{'session_key': 1}])
            self.assertEqual(len(calls), 1)
            failed, completed = resumed.manifest['fontes']
            for field in ('arquivo', 'obtido_em_utc', 'sha256', 'status'):
                self.assertEqual(failed[field], old[field])
            self.assertEqual((Path(folder) / failed['arquivo']).read_bytes(), b'{"detail":"wait"}')
            self.assertNotEqual(completed['arquivo'], failed['arquivo'])
            self.assertEqual(completed['arquivo_requisicao'], args[2])
            self.assertFalse(failed['normalizar'])
            self.assertEqual(failed['substituido_por'], completed['arquivo'])
            resumed.source_usage(args[2], True)
            self.assertFalse(failed['normalizar'])
            self.assertTrue(completed['normalizar'])

    def test_retomada_respeita_retry_after_futuro_sem_rede_ou_espera(self):
        args = ('openf1', 'laps', 'raw/laps.json', 'https://example.test/data')
        future = datetime.now(timezone.utc) + timedelta(days=1)

        def limited(request, timeout):
            raise HTTPError(request.full_url, 429, 'Too Many Requests',
                            {'Retry-After': format_datetime(future, usegmt=True)}, io.BytesIO(b'{}'))

        with tempfile.TemporaryDirectory() as folder:
            original = CaptureClient(folder, opener=limited)
            with self.assertRaisesRegex(RuntimeError, 'HTTP 429'):
                original.capture(*args)
            sleeps = []
            resumed = CaptureClient(folder, opener=lambda *a, **k: self.fail('Prazo ainda não passou'),
                                    sleeper=sleeps.append, retry_errors=True)
            with self.assertRaisesRegex(RuntimeError, 'Retry-After ainda não expirou'):
                resumed.capture(*args)
            self.assertEqual(sleeps, [])
            self.assertEqual(len(resumed.manifest['fontes']), 1)
            self.assertEqual((Path(folder) / args[2]).read_bytes(), b'{}')

    def test_retomada_nao_repara_cache_divergente_nem_erro_permanente(self):
        args = ('openf1', 'laps', 'raw/laps.json', 'https://example.test/data')

        def missing(request, timeout):
            raise HTTPError(request.full_url, 404, 'Not Found', {}, io.BytesIO(b'{}'))

        with tempfile.TemporaryDirectory() as folder:
            CaptureClient(folder, opener=missing).capture(*args)
            resumed = CaptureClient(folder, opener=lambda *a, **k: self.fail('Não consultar'), retry_errors=True)
            self.assertIsNone(resumed.capture(*args))
            path = Path(folder) / args[2]
            path.write_bytes(b'modified')
            with self.assertRaisesRegex(ValueError, 'Cache divergente'):
                resumed.capture(*args)
            self.assertEqual(path.read_bytes(), b'modified')

    def test_retomada_faz_so_uma_tentativa_transitoria_por_invocacao(self):
        args = ('openf1', 'laps', 'raw/laps.json', 'https://example.test/data')
        calls = []

        def unavailable(request, timeout):
            calls.append(1)
            raise HTTPError(request.full_url, 503, 'Unavailable', {'Retry-After': '0'}, io.BytesIO(b'{}'))

        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(CaptureClient(folder, opener=unavailable).capture(*args))
            resumed = CaptureClient(folder, opener=unavailable, retry_errors=True)
            self.assertIsNone(resumed.capture(*args))
            self.assertIsNone(resumed.capture(*args))
            self.assertEqual(len(calls), 2)
            self.assertEqual(len(resumed.manifest['fontes']), 2)

    def test_mapeamento_usa_race_data_utc_e_exclui_sessao_futura(self):
        event = dict(temporada=2024, rodada=1, circuito_id='literal', data_corrida='2024-03-02')
        race = dict(session_key=10, meeting_key=20, year=2024, session_name='Race',
                    date_start='2024-03-02T15:00:00+00:00', date_end='2024-03-02T17:00:00+00:00')
        future = dict(race, session_key=11, session_name='Practice 1', date_end='2027-01-01T00:00:00Z')
        mappings, failures = map_sessions([event], {2024: [race, future]}, datetime(2026, 10, 27, tzinfo=timezone.utc))
        self.assertEqual([m['session_key'] for m in mappings], [10])
        self.assertEqual(failures, [])
        wrong = dict(event, data_corrida='2024-03-03')
        self.assertEqual(map_sessions([wrong], {2024: [race]}, datetime(2026, 10, 27, tzinfo=timezone.utc))[0], [])

    def test_race_ambiguo_nao_e_adivinhado(self):
        event = dict(temporada=2024, rodada=1, circuito_id='literal', data_corrida='2024-03-02')
        race = dict(session_key=10, meeting_key=20, year=2024, session_name='Race',
                    date_start='2024-03-02T15:00:00Z', date_end='2024-03-02T17:00:00Z')
        mappings, failures = map_sessions([event], {2024: [race, dict(race, session_key=12)]}, datetime(2026, 10, 27, tzinfo=timezone.utc))
        self.assertEqual(mappings, [])
        self.assertEqual(failures[0]['races_correspondentes'], 2)

    def test_data_local_so_e_admitida_com_localidade_literal_e_offset_da_fonte(self):
        event = dict(temporada=2024, rodada=22, circuito_id='vegas', data_corrida='2024-11-23', localidade='Las Vegas')
        race = dict(session_key=9644, meeting_key=1250, year=2024, session_name='Race', location='Las Vegas',
                    gmt_offset='-08:00:00', date_start='2024-11-24T06:00:00Z', date_end='2024-11-24T08:00:00Z')
        as_of = datetime(2026, 10, 27, tzinfo=timezone.utc)
        mappings, failures = map_sessions([event], {2024: [race]}, as_of)
        self.assertEqual(failures, [])
        self.assertEqual(mappings[0]['criterio_identidade'], 'data_local_e_localidade_literal')
        self.assertEqual(mappings[0]['data_calendario'], '2024-11-23')
        self.assertEqual(mappings[0]['data_race_utc'], '2024-11-24')
        self.assertEqual(event['data_corrida'], '2024-11-23')
        self.assertEqual(map_sessions([dict(event, localidade='Outra')], {2024: [race]}, as_of)[0], [])

    def test_clima_zero_e_valido_null_e_serie_incompleta_nao(self):
        data = {'utc_offset_seconds': 0, 'hourly': {'time': ['2024-01-01T%02d:00' % i for i in range(24)]}}
        data['hourly'].update({field: [0] * 24 for field in WEATHER_FIELDS})
        self.assertTrue(weather_coverage(data, '2024-01-01', '2024-01-01'))
        data['hourly']['rain'][0] = None
        self.assertFalse(weather_coverage(data, '2024-01-01', '2024-01-01'))
        data['hourly']['rain'][0] = 0
        data['utc_offset_seconds'] = 3600
        self.assertFalse(weather_coverage(data, '2024-01-01', '2024-01-01'))

    def test_janela_clima_inclui_data_utc_observada_sem_alterar_calendario(self):
        event = dict(data_corrida='2024-11-23', sessoes_calendario={'FirstPractice': {'date': '2024-11-21'}},
                     datas_sessoes_observadas_utc=['2024-11-22', '2024-11-24'])
        self.assertEqual(weather_window(event), ('2024-11-21', '2024-11-24'))
        self.assertEqual(event['data_corrida'], '2024-11-23')

    def test_fallback_clima_completo_desativa_serie_parcial_sem_apagar_raw(self):
        event = dict(temporada=2026, rodada=18, circuito_id='americas', data_corrida='2026-10-25',
                     latitude=30, longitude=-97, sessoes_calendario={'FirstPractice': {'date': '2026-10-25'}})
        race = dict(session_key=10, meeting_key=20, year=2026, session_name='Race',
                    date_start='2026-10-25T15:00:00Z', date_end='2026-10-25T17:00:00Z')
        weather = {'utc_offset_seconds': 0, 'hourly': {'time': ['2026-10-25T%02d:00' % i for i in range(24)]}}
        weather['hourly'].update({field: [0] * 24 for field in WEATHER_FIELDS})

        def opener(request, timeout):
            url = request.full_url
            host = urlsplit(url).hostname
            if '/sessions?' in url:
                value = [race]
            elif host in {'archive-api.open-meteo.com', 'api.open-meteo.com'}:
                value = json.loads(json.dumps(weather))
                if host == 'archive-api.open-meteo.com':
                    value['hourly']['rain'][0] = None
            else:
                value = []
            return Response(json.dumps(value).encode())

        with tempfile.TemporaryDirectory() as folder:
            client = CaptureClient(folder, opener=opener, sleeper=lambda seconds: None)
            with patch('coletar_acervo_historico.CaptureClient', return_value=client):
                manifest = collect_online(folder, [event], datetime(2026, 10, 27, tzinfo=timezone.utc))
            receipts = [r for r in manifest['fontes'] if r['provider'] == 'open-meteo']
            self.assertEqual(len(receipts), 2)
            self.assertEqual([r['endpoint'] for r in receipts if r['normalizar']], ['forecast'])
            self.assertTrue(all((Path(folder) / r['arquivo']).is_file() for r in receipts))


if __name__ == '__main__':
    unittest.main()
