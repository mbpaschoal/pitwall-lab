"""TDD sintético da coleta 2026; nunca abre rede real."""
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError

from operacao2026 import fontes

SCRATCH = Path(os.environ.get('TMPDIR') or tempfile.gettempdir()).resolve()


def pagina(races, total=None, offset=0, limit=100):
    return json.dumps({'MRData': {'limit': str(limit), 'offset': str(offset),
                                  'total': str(len(races) if total is None else total),
                                  'RaceTable': {'season': '2026', 'Races': races}}}).encode('utf-8')


def corrida(round_='1', circuit='americas', date='2026-01-01', results=None):
    row = {'season': '2026', 'round': str(round_), 'date': date,
           'time': '12:00:00Z', 'Circuit': {'circuitId': circuit}}
    if results is not None:
        row['Results'] = results
    return row


def resultado(driver='a', position='1', points='25'):
    return {'Driver': {'driverId': driver}, 'Constructor': {'constructorId': 'team'},
            'position': position, 'points': points}


class FontesEtapa8Test(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=str(SCRATCH))
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_rate_limit_e_retry_http_date_sao_deterministicos(self):
        sleeps, calls = [], []
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date = 'Thu, 01 Jan 2026 00:00:10 GMT'
        class Response:
            status = 200
            url = 'https://real.example/page'
            def read(self): return pagina([])
            def close(self): pass
        def opener(request, timeout=30):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise HTTPError(request.full_url, 429, 'busy', {'Retry-After': date}, io.BytesIO(b'busy'))
            return Response()
        client = fontes.ClienteHTTP(opener=opener, sleeper=sleeps.append,
                                    clock=lambda: 0.0, utc_clock=lambda: now)
        client.buscar('https://example/a', 0)
        client.buscar('https://example/b', 0)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [10.0, 8.0])

    def test_ler_snapshot_filtra_antes_de_abrir_raw_nao_selecionado(self):
        snap = self.root / 's1'; (snap / 'raw').mkdir(parents=True)
        good = pagina([]); explosive = snap / 'raw/resultados_offset_0000.json'
        explosive.write_bytes(b'not-json-must-never-be-read')
        (snap / 'raw/calendario_offset_0000.json').write_bytes(good)
        index = {'versao': 1, 'snapshot_id': 's1', 'criado_em_utc': '2026-01-01T00:00:00Z', 'fontes': [
            {'arquivo': 'raw/calendario_offset_0000.json', 'endpoint': 'calendario', 'sha256': sha256(good).hexdigest(), 'parametros': {'offset': 0}, 'status': 200, 'url_solicitada': 'u', 'url_real': 'u', 'obtido_em_utc': '2026-01-01T00:00:00Z', 'origem': 'rede'},
            {'arquivo': 'raw/resultados_offset_0000.json', 'endpoint': 'resultados', 'sha256': '0' * 64, 'parametros': {'offset': 0}, 'status': 200, 'url_solicitada': 'u', 'url_real': 'u', 'obtido_em_utc': '2026-01-01T00:00:00Z', 'origem': 'rede'}]}
        (snap / 'indice.json').write_text(json.dumps(index), encoding='utf-8')
        loaded, pages = fontes.ler_snapshot(self.root, 's1', endpoints={'calendario'})
        self.assertEqual(loaded['snapshot_id'], 's1')
        self.assertEqual(set(pages), {'calendario'})
        self.assertEqual(pages['calendario'][0][1]['MRData']['RaceTable']['Races'], [])
        _, paths = fontes.ler_snapshot(self.root, 's1', carregar=False, endpoints={'calendario'})
        self.assertEqual(paths['calendario'][0][1].name, 'calendario_offset_0000.json')
        with self.assertRaises(ValueError):
            fontes.ler_snapshot(self.root, '../s1')

    def test_paginas_recusa_incompletude_ids_e_tipos(self):
        one = {'bytes': pagina([corrida(results=[resultado('a')])], total=2), 'parametros': {'offset': 0}}
        with self.assertRaisesRegex(ValueError, 'incompleta'):
            fontes.paginas_completas(lambda offset: one, 'resultados', '1')
        bad_id = {'bytes': pagina([corrida(results=[resultado('a'), resultado('a', '2')])]), 'parametros': {'offset': 0}}
        with self.assertRaisesRegex(ValueError, 'duplicado'):
            fontes.paginas_completas(lambda offset: bad_id, 'resultados', '1')
        bad_type = {'bytes': pagina([corrida(results=[resultado(position=True)])]), 'parametros': {'offset': 0}}
        with self.assertRaisesRegex(ValueError, 'Posição'):
            fontes.paginas_completas(lambda offset: bad_type, 'resultados', '1')

    def test_cache_original_e_refresh_e_falha_parcial(self):
        original = pagina([corrida('1', date='2026-01-01', results=[resultado()])])
        fontes.gravar_snapshot(self.root, 'old', {'resultados': [
            {'bytes': original, 'parametros': {'offset': 0}, 'status': 200, 'url_solicitada': 'u', 'url_real': 'u',
             'obtido_em_utc': '2026-01-03T00:00:00Z', 'origem': 'rede'}]})
        calendario = pagina([corrida('1', date='2026-01-01')])
        calls = []
        def fresh(url, offset):
            calls.append(url)
            if url == fontes.BASE:
                return {'bytes': calendario, 'parametros': {'offset': offset}, 'status': 200,
                        'url_solicitada': url, 'url_real': url, 'obtido_em_utc': '2026-02-01T00:00:00Z', 'origem': 'rede'}
            raise AssertionError('resultado deveria vir do cache: {}'.format(url))
        saved = fontes.coletar_snapshot(self.root, 'reuse', circuitos=(), agora=datetime(2026, 2, 1, tzinfo=timezone.utc), fetch=fresh)
        index = fontes.ler_indice(self.root, saved.name)
        cached = next(item for item in index['fontes'] if item['endpoint'] == 'resultados')
        self.assertEqual(cached['origem'], 'cache')
        self.assertEqual(cached['obtido_em_utc'], '2026-01-03T00:00:00Z')
        self.assertEqual(calls, [fontes.BASE])
        with self.assertRaisesRegex(RuntimeError, 'rede'):
            fontes.coletar_snapshot(self.root, 'broken', circuitos=(), agora=datetime(2026, 2, 1, tzinfo=timezone.utc),
                                    fetch=lambda url, offset: (_ for _ in ()).throw(RuntimeError('rede')))
        self.assertTrue((self.root / 'broken').is_dir())
        self.assertFalse((self.root / 'broken/indice.json').exists())


if __name__ == '__main__':
    unittest.main()
