"""Regressões R1 sintéticas da operação 2026; sem rede ou dados reais."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import cast
from unittest.mock import patch

import operar_2026
from operacao2026 import fontes, previsao


SCRATCH = Path(os.environ.get('TMPDIR') or tempfile.gettempdir()).resolve()


def corrida(round_, date_, circuit='americas', qdate=None):
    return {'season': '2026', 'round': str(round_), 'raceName': 'SYNTHETIC', 'date': date_,
            'time': '20:00:00Z', 'Circuit': {'circuitId': circuit},
            'Qualifying': {'date': qdate or date_, 'time': '12:00:00Z'}}


def quali(driver='synthetic_a', team='synthetic_team', position='1'):
    return {'Driver': {'driverId': driver}, 'Constructor': {'constructorId': team}, 'position': position}


def resultado(driver='synthetic_a'):
    return {'Driver': {'driverId': driver}, 'Constructor': {'constructorId': 'synthetic_team'},
            'position': '1', 'points': '25'}


def raw_page(races, endpoint, total=None, offset=0):
    field = {'classificacao': 'QualifyingResults', 'resultados': 'Results'}.get(endpoint)
    count = sum(len(row[field]) for row in races) if field else len(races)
    return json.dumps({'MRData': {'limit': '100', 'offset': str(offset), 'total': str(count if total is None else total),
                                  'RaceTable': {'season': '2026', 'Races': races}}}).encode()


def source(raw, endpoint, round_=None, got='2026-10-24T22:01:00Z', offset=0):
    item = {'bytes': raw, 'parametros': {'offset': offset, 'limit': 100}, 'status': 200,
            'url_solicitada': 'https://fixture.invalid', 'url_real': 'https://fixture.invalid',
            'obtido_em_utc': got, 'origem': 'fixture'}
    if round_ is not None:
        item['rodada'] = str(round_)
    return item


class R1Operacao2026Test(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=str(SCRATCH))
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_referencia_posterior_bloqueia_antes_de_admitir_gp_futuro(self):
        alvo = corrida(1, '2026-03-01', 'marina_bay', '2026-05-01')
        futuro = corrida(2, '2026-04-01', 'future', '2026-03-31')
        with self.assertRaisesRegex(ValueError, 'referência posterior'):
            previsao.preparar_alvo(alvo, [quali()])
        valido = corrida(1, '2026-03-01', 'marina_bay', '2026-02-28')
        state = previsao.preparar_alvo(valido, [quali()])
        self.assertNotIn(('2026', '2'), previsao.chaves_historicas_admitidas(state, [valido, futuro]))

    def test_snapshot_com_hash_integro_mas_paginacao_q_incompleta_bloqueia(self):
        target = corrida(18, '2026-10-25')
        raw = raw_page([dict(target, QualifyingResults=[quali()])], 'classificacao', total=2)
        fontes.gravar_snapshot(self.root, 'incompleto', {'classificacao': [source(raw, 'classificacao', 18)]})
        with self.assertRaisesRegex(ValueError, 'incompleta'):
            fontes.ler_snapshot(self.root, 'incompleto', endpoints={'classificacao'}, rodadas={'18'})

    def test_ids_literais_malformados_sao_rejeitados_sem_normalizar(self):
        event = corrida(18, '2026-10-25')
        for driver, team in (('   ', 'synthetic_team'), (' synthetic_a', 'synthetic_team'),
                             ('synthetic_a ', 'synthetic_team'), ('synthetic_a', 'wrong team')):
            raw = raw_page([dict(event, QualifyingResults=[quali(driver, team)])], 'classificacao')
            with self.assertRaisesRegex(ValueError, 'ID'):
                fontes.validar_pagina(raw, 'classificacao', '18', event)
            with self.assertRaisesRegex(ValueError, 'ID'):
                previsao.preparar_alvo(event, [quali(driver, team)], prospectivo=True)
        previsao.preparar_alvo(event, [quali('driver_2026', 'team_2026')], prospectivo=True)

    def test_cache_resultado_vazio_tenta_atualizacao_limitada_e_preserva_origem(self):
        event = corrida(1, '2026-01-01', 'cache')
        fontes.gravar_snapshot(self.root, 'old', {'resultados': [source(raw_page([], 'resultados', total=0), 'resultados', 1)]})
        calendar = raw_page([event], 'calendario')
        calls = []
        def fetch(url, offset):
            calls.append((url, offset))
            if url == fontes.BASE:
                return source(calendar, 'calendario', offset=offset)
            return source(raw_page([dict(event, Results=[resultado()])], 'resultados'), 'resultados', 1, offset=offset)
        saved = fontes.coletar_snapshot(self.root, 'novo', circuitos=(), agora=datetime(2026, 2, 1, tzinfo=timezone.utc), fetch=fetch)
        index = fontes.ler_indice(self.root, saved.name)
        result = next(item for item in index['fontes'] if item['endpoint'] == 'resultados')
        self.assertEqual(result['origem'], 'rede')
        self.assertIn((fontes.BASE + '1/results/', 0), calls)

    def test_prospectivo_exige_timestamps_de_todas_fontes_admitidas(self):
        cutoff = '2026-10-24T22:30:00Z'
        pages = {'calendario': [(dict(source(raw_page([], 'calendario'), 'calendario', got='2026-10-26T00:00:00Z'), arquivo='raw/c.json'), {})],
                 'classificacao': [(dict(source(raw_page([], 'classificacao'), 'classificacao', 18, got='2026-10-24T22:01:00Z'), arquivo='raw/q.json'), {})],
                 'resultados': [(dict(source(raw_page([], 'resultados'), 'resultados', 1, got='2026-10-26T00:00:00Z'), arquivo='raw/r.json'), {})]}
        with self.assertRaisesRegex(ValueError, 'corte'):
            operar_2026._validar_fontes_prospectivas(pages, [], '2026-10-24T22:00:00Z', cutoff)
        pages['calendario'][0][0]['obtido_em_utc'] = '2026-10-24T22:02:00Z'
        pages['resultados'][0][0]['obtido_em_utc'] = '2026-10-24T22:02:00Z'
        pages['classificacao'][0][0]['obtido_em_utc'] = '2026-10-24T20:00:00Z'
        with self.assertRaisesRegex(ValueError, 'encerramento'):
            operar_2026._validar_fontes_prospectivas(pages, [], '2026-10-24T22:00:00Z', cutoff)
        pages['classificacao'][0][0]['obtido_em_utc'] = '2026-10-24T22:01:00Z'
        with self.assertRaisesRegex(ValueError, 'histórica'):
            operar_2026._validar_fontes_prospectivas(
                pages, [{'arquivo': '2025/raw/r.json', 'sha256': '0' * 64}],
                '2026-10-24T22:00:00Z', cutoff)

    def test_historico_auditavel_retorna_proveniencia_com_hash(self):
        historical = self.root / 'historico'
        for year in range(2021, 2026):
            event = dict(corrida(1, '{}-03-01'.format(year)), season=str(year))
            calendar = raw_page([event], 'calendario')
            results = raw_page([dict(event, Results=[resultado('driver_{}'.format(year))])], 'resultados')
            folder = historical / str(year)
            raw = folder / 'raw'
            raw.mkdir(parents=True)
            (raw / 'calendar.json').write_bytes(calendar)
            (raw / 'results.json').write_bytes(results)
            provenance = []
            for endpoint, name, payload in (('calendario', 'raw/calendar.json', calendar),
                                            ('resultados', 'raw/results.json', results)):
                provenance.append({'endpoint': endpoint, 'arquivo': name,
                                   'sha256': sha256(payload).hexdigest(),
                                   'obtido_em_utc': '2026-10-24T22:01:00Z'})
            (folder / 'manifesto.json').write_text(json.dumps({'proveniencia': provenance}))
        calendar, results, sources = cast(
            tuple[list, dict, list], previsao.carregar_historico_bruto(str(historical), auditoria=True))
        self.assertEqual(len(calendar), 5)
        self.assertEqual(len(results), 5)
        self.assertEqual(len(sources), 10)
        self.assertTrue(all(item['origem'] == 'historico_congelado' and len(item['sha256']) == 64
                            for item in sources))

    def test_publicacao_prospectiva_revalida_durante_escrita_sem_pasta_final(self):
        clock = [datetime(2026, 10, 25, 19, 59, 59, tzinfo=timezone.utc)]
        def guard():
            now = clock[0]
            previsao.validar_prospectivo('2026-10-25T20:00:00Z', '2026-10-24T21:00:00Z',
                                          '2026-10-24T22:00:00Z', '2026-10-24T22:01:00Z',
                                          '2026-10-24T22:02:00Z', now)
            return now
        original_open = Path.open
        advanced = [False]
        def advances(path, *args, **kwargs):
            handle = original_open(path, *args, **kwargs)
            if not advanced[0] and path.name == 'probabilidades.csv':
                advanced[0] = True
                clock[0] = datetime(2026, 10, 25, 20, 0, 1, tzinfo=timezone.utc)
            return handle
        data = {'modo': 'PROSPECTIVO', 'emitido_em_utc': '2026-10-25T19:59:59Z',
                'evento': {'temporada': '2026', 'rodada': '18', 'circuito_id': 'americas'}, 'linhas': [],
                'fontes': [], 'historicos_usados': {}, 'limites': ['fixture']}
        with patch.object(Path, 'open', advances):
            with self.assertRaisesRegex(ValueError, 'largada'):
                previsao.gravar_emissao(self.root, 'prospectivo-write-r1', data, validar_publicacao=guard)
        self.assertTrue(advanced[0])
        self.assertFalse((self.root / 'prospectivo-write-r1').exists())

    def test_publicacao_prospectiva_revalida_depois_da_serializacao_sem_pasta_final(self):
        clock = [datetime(2026, 10, 25, 19, 59, 59, tzinfo=timezone.utc)]
        def guard():
            now = clock[0]
            previsao.validar_prospectivo('2026-10-25T20:00:00Z', '2026-10-24T21:00:00Z',
                                          '2026-10-24T22:00:00Z', '2026-10-24T22:01:00Z',
                                          '2026-10-24T22:02:00Z', now)
            return now
        original = previsao._bytes_json
        def advances(value):
            clock[0] = datetime(2026, 10, 25, 20, 0, 1, tzinfo=timezone.utc)
            return original(value)
        data = {'modo': 'PROSPECTIVO', 'emitido_em_utc': '2026-10-25T19:59:59Z',
                'evento': {'temporada': '2026', 'rodada': '18', 'circuito_id': 'americas'}, 'linhas': [],
                'fontes': [], 'historicos_usados': {}, 'limites': ['fixture']}
        with patch.object(previsao, '_bytes_json', advances):
            with self.assertRaisesRegex(ValueError, 'largada'):
                previsao.gravar_emissao(self.root, 'prospectivo-r1', data, validar_publicacao=guard)
        self.assertFalse((self.root / 'prospectivo-r1').exists())
        self.assertTrue(any(path.name.startswith('.parcial-prospectivo-r1-') for path in self.root.iterdir()))

    def test_publicacao_prospectiva_que_cruza_largada_no_replace_vira_parcial_invalida(self):
        race = datetime(2026, 10, 25, 20, 0, 0, tzinfo=timezone.utc)
        clock = [datetime(2026, 10, 25, 19, 59, 59, tzinfo=timezone.utc)]
        def guard():
            now = clock[0]
            previsao.validar_prospectivo(race, '2026-10-24T21:00:00Z',
                                          '2026-10-24T22:00:00Z', '2026-10-24T22:01:00Z',
                                          '2026-10-24T22:02:00Z', now)
            return now
        real_replace = os.replace
        def crosses_start(source, destination):
            real_replace(source, destination)
            clock[0] = datetime(2026, 10, 25, 20, 0, 1, tzinfo=timezone.utc)
        data = {'modo': 'PROSPECTIVO', 'linhas': [], 'fontes': [], 'historicos_usados': {}, 'limites': ['fixture']}
        with patch.object(previsao.os, 'replace', crosses_start):
            with self.assertRaisesRegex(ValueError, 'largada'):
                previsao.gravar_emissao(self.root, 'prospectivo-replace-r1', data, validar_publicacao=guard)
        self.assertFalse((self.root / 'prospectivo-replace-r1').exists())
        invalidas = [path for path in self.root.iterdir()
                     if path.name.startswith('.parcial-invalida-prospectivo-replace-r1-')]
        self.assertEqual(len(invalidas), 1)
        self.assertTrue((invalidas[0] / 'probabilidades.csv').is_file())


if __name__ == '__main__':
    unittest.main()
