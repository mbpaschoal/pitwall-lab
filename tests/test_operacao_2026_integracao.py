"""Contraprovas de integração offline da operação 2026."""
import argparse
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import operar_2026
from operacao2026 import fontes, previsao


SCRATCH = Path(os.environ.get('TMPDIR', '/Users/MBPaschoal/.hermes/cache/scratch'))


def corrida(round_, data, circuito, qualifying=True, results=None):
    race = {'season': '2026', 'round': str(round_), 'raceName': 'GP {}'.format(round_),
            'date': data, 'time': '20:00:00Z', 'Circuit': {'circuitId': circuito}}
    if qualifying:
        race['Qualifying'] = {'date': data, 'time': '12:00:00Z'}
    if results is not None:
        race['Results'] = results
    return race


def quali(driver='a', team='t', position=1):
    return {'Driver': {'driverId': driver, 'givenName': driver, 'familyName': 'F'},
            'Constructor': {'constructorId': team}, 'position': None if position is None else str(position)}


def resultado(driver='a', team='t', position=1, points=25):
    return {'Driver': {'driverId': driver}, 'Constructor': {'constructorId': team},
            'position': str(position), 'points': str(points), 'status': 'Finished'}


def page(races):
    return json.dumps({'MRData': {'limit': '100', 'offset': '0', 'total': str(len(races)),
                                  'RaceTable': {'season': '2026', 'Races': races}}}).encode('utf-8')


def source(raw, round_=None):
    value = {'bytes': raw, 'parametros': {'offset': 0}, 'status': 200,
             'url_solicitada': 'https://fixture.test', 'url_real': 'https://fixture.test',
             'obtido_em_utc': '2026-10-10T13:00:00Z', 'origem': 'fixture'}
    if round_ is not None:
        value['rodada'] = str(round_)
    return value


class Operacao2026IntegracaoTest(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=str(SCRATCH))
        self.root = Path(self.temp.name)
        self.snapshots = self.root / 'snapshots'

    def tearDown(self):
        self.temp.cleanup()

    def test_cli_coletar_delega_snapshot_id_e_circuito_explicito_sem_duplicar_padrao(self):
        called = []
        def collect(root, snapshot_id=None, atualizar=False, circuitos=None):
            called.append((root, snapshot_id, atualizar, tuple(circuitos)))
            return Path(root) / snapshot_id
        with patch.object(operar_2026, 'SNAPSHOTS', self.snapshots), \
             patch.object(fontes, 'coletar_snapshot', collect):
            self.assertEqual(operar_2026.main(['coletar', '--id', 's1', '--classificacao-circuito', 'foo']), 0)
        self.assertEqual(called, [(self.snapshots, 's1', False, ('foo',))])

    def test_leitura_agrupada_filtra_metadata_antes_de_raw_alvo_ou_futuro(self):
        prior = corrida(1, '2026-03-01', 'prior')
        target = corrida(2, '2026-03-15', 'marina_bay')
        future = corrida(3, '2026-04-01', 'future')
        fontes.gravar_snapshot(self.snapshots, 's1', {
            'calendario': [source(page([prior, target, future]))],
            'classificacao': [source(page([dict(target, QualifyingResults=[quali()])]), 2)],
            'resultados': [source(page([dict(prior, Results=[resultado()])]), 1),
                            source(page([dict(target, Results=[resultado(points=999)])]), 2),
                            source(page([dict(future, Results=[resultado(points=999)])]), 3)],
        })
        original = Path.read_bytes
        blocked = ('resultados_2_', 'resultados_3_')
        def guarded(path):
            if any(part in path.name for part in blocked):
                raise AssertionError('raw do alvo/futuro foi aberto: {}'.format(path.name))
            return original(path)
        with patch.object(operar_2026, 'SNAPSHOTS', self.snapshots), \
             patch.object(previsao, 'carregar_historico_bruto', return_value=([], {})), \
             patch.object(Path, 'read_bytes', guarded):
            index, calendar, event, state, pages, results, rows, audit = operar_2026._preparar_fluxo('s1', 'marina_bay')
        self.assertEqual(index['snapshot_id'], 's1')
        self.assertEqual(event['round'], '2')
        self.assertEqual(state['estado'], 'pronto')
        self.assertEqual(audit['resultados_lidos'], [('2026', '1')])
        self.assertEqual(rows[0]['media_pontos_equipe_5'], 25.0)
        self.assertEqual(set(pages), {'calendario', 'classificacao', 'resultados'})
        self.assertEqual(set(results), {('2026', '1')})

    def test_estado_q_vazio_nao_indexa_e_calendario_entra_nos_raw_admitidos(self):
        austin = corrida(18, '2026-10-25', 'americas')
        fontes.gravar_snapshot(self.snapshots, 'q0', {
            'calendario': [source(page([austin]))],
            'classificacao': [source(page([]), 18)],
        })
        with patch.object(operar_2026, 'SNAPSHOTS', self.snapshots):
            text = io.StringIO()
            with redirect_stdout(text):
                operar_2026.cmd_estado(argparse.Namespace(snapshot='q0'))
            index, calendar, calendar_pages = operar_2026._calendar('q0')
            raw = operar_2026._raw_admitidos('q0', calendar_pages)
        self.assertIn('aguardando_classificacao', text.getvalue())
        self.assertEqual(index['snapshot_id'], 'q0')
        self.assertEqual(len(calendar), 1)
        self.assertEqual(len(raw), 1)

    def test_inferir_normaliza_none_so_para_rank_e_preserva_entrada_json(self):
        model = previsao.carregar_modelo()
        row = {'temporada': '2026', 'rodada': '1', 'piloto_id': 'sem-q', 'corrida': 'Teste',
               'data_corrida': '2026-01-01', 'circuito_id': 'test', 'equipe_id': 't', 'equipe_id_entrada': 't',
               'limite_inferior_referencia_utc': '2026-01-01T12:00:00Z', 'posicao_classificacao': None,
               'posicao_classificacao_repetida': 0, 'classificacao_ausente': 0,
               'posicao_classificacao_ausente': 1, 'media_posicao_final_5': None,
               'taxa_podios_5': None, 'n_posicoes_5': 0, 'n_podios_5': 0,
               'media_pontos_equipe_5': None, 'n_corridas_equipe_5': 0,
               'n_participacoes_equipe_5': 0, 'historico_piloto_insuficiente': 1,
               'historico_equipe_insuficiente': 1, 'equipe_pre_corrida_ausente': 0,
               'referencia_temporal_ausente': 0}
        output = previsao.inferir(model, [row])
        self.assertIsNone(row['posicao_classificacao'])
        self.assertTrue(output[0]['elegivel_previsao'])
        self.assertIsNone(output[0]['posicao_classificacao'])
        self.assertIsInstance(output[0]['probabilidade_modelo'], float)
        json.dumps(output, allow_nan=False)

    def test_retry_after_503_respeita_hint_sem_sleep_real(self):
        sleeps, calls = [], []
        class Response:
            status = 200
            url = 'https://fixture.test/ok'
            def read(self): return page([])
            def close(self): pass
        def opener(request, timeout=30):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise HTTPError(request.full_url, 503, 'busy', {'Retry-After': '7'}, io.BytesIO(b'busy'))
            return Response()
        client = fontes.ClienteHTTP(opener=opener, sleeper=sleeps.append, clock=lambda: 0.0,
                                    utc_clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
        client.buscar('https://fixture.test', 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [7.0, 1.0])

    def test_fontes_prospectivas_exigem_janela_de_encerramento_e_corte(self):
        item = source(page([]))
        pages = {'calendario': [(dict(item, obtido_em_utc='2026-10-24T22:02:00Z'), {})],
                 'classificacao': [(dict(item, obtido_em_utc='2026-10-24T22:01:00Z'), {})]}
        operar_2026._validar_fontes_prospectivas(
            pages, [], '2026-10-24T22:00:00Z', '2026-10-24T22:30:00Z')
        pages['classificacao'][0][0]['obtido_em_utc'] = '2026-10-24T20:00:00Z'
        with self.assertRaisesRegex(ValueError, 'encerramento'):
            operar_2026._validar_fontes_prospectivas(
                pages, [], '2026-10-24T22:00:00Z', '2026-10-24T22:30:00Z')


if __name__ == '__main__':
    unittest.main()
