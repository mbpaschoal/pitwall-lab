import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from operacao2026 import fontes, previsao


SCRATCH = Path(os.environ.get('TMPDIR', '/Users/MBPaschoal/.hermes/cache/scratch'))


def corrida(round_, date_, circuit='x', qualifying=None):
    item = {'season': '2026', 'round': str(round_), 'raceName': 'GP', 'date': date_,
            'time': '12:00:00Z', 'Circuit': {'circuitId': circuit}}
    if qualifying is not None:
        item['Qualifying'] = qualifying
    return item


def resultado(driver, team, position, points):
    return {'Driver': {'driverId': driver, 'givenName': driver, 'familyName': 'X'},
            'Constructor': {'constructorId': team}, 'position': str(position),
            'points': str(points), 'status': 'Finished'}


def quali(driver, team, position):
    return {'Driver': {'driverId': driver, 'givenName': driver, 'familyName': 'X'},
            'Constructor': {'constructorId': team}, 'position': None if position is None else str(position)}


class Operacao2026Test(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.work = tempfile.TemporaryDirectory(dir=str(SCRATCH))
        self.root = Path(self.work.name)

    def tearDown(self):
        self.work.cleanup()

    def test_qualifying_vazio_aguarda_sem_probabilidades(self):
        state = previsao.preparar_alvo(corrida(18, '2026-10-25', 'americas'), [])
        self.assertEqual(state['estado'], 'aguardando_classificacao')
        self.assertEqual(state['registros'], [])

    def test_qualifying_duplicado_bloqueia_e_posicao_repetida_e_preservada(self):
        event = corrida(17, '2026-10-11', 'marina_bay', {'date': '2026-10-10', 'time': '12:00:00Z'})
        with self.assertRaisesRegex(ValueError, 'piloto duplicado'):
            previsao.preparar_alvo(event, [quali('a', 't', 1), quali('a', 't', 2)])
        state = previsao.preparar_alvo(event, [quali('a', 't', 1), quali('b', 'u', 1)])
        self.assertTrue(all(x['posicao_classificacao_repetida'] == 1 for x in state['registros']))

    def test_matriz_nao_le_resultado_alvo_ou_futuro_e_janela_equipe_por_gp(self):
        target = corrida(3, '2026-03-15', 'marina_bay', {'date': '2026-03-14', 'time': '12:00:00Z'})
        calendar = [corrida(1, '2026-02-01'), corrida(2, '2026-03-01'), target, corrida(4, '2026-04-01')]
        results = {
            ('2026', '1'): [resultado('a', 'team', 1, '10'), resultado('b', 'team', 5, '2')],
            ('2026', '2'): [resultado('a', 'team', 2, '8')],
            ('2026', '3'): [resultado('a', 'team', 99, '999')],
            ('2026', '4'): [resultado('a', 'team', 88, '888')],
        }
        q = [quali('a', 'team', 1), quali('new', 'newteam', None)]
        state = previsao.preparar_alvo(target, q)
        rows, audit = previsao.gerar_entradas(state, calendar, results)
        a = next(x for x in rows if x['piloto_id'] == 'a')
        self.assertEqual(a['n_posicoes_5'], 2)
        self.assertEqual(a['n_corridas_equipe_5'], 2)
        self.assertEqual(a['n_participacoes_equipe_5'], 3)
        self.assertAlmostEqual(a['media_pontos_equipe_5'], float(Decimal('20') / Decimal(3)))
        self.assertEqual(audit['resultados_lidos'], [('2026', '1'), ('2026', '2')])
        self.assertEqual(next(x for x in rows if x['piloto_id'] == 'new')['n_posicoes_5'], 0)

    def test_futuros_nao_afetam_entradas(self):
        target = corrida(2, '2026-03-15', qualifying={'date': '2026-03-14', 'time': '12:00:00Z'})
        calendar = [corrida(1, '2026-03-01'), target, corrida(3, '2026-04-01')]
        q = [quali('a', 'team', 1)]
        state = previsao.preparar_alvo(target, q)
        base = {('2026', '1'): [resultado('a', 'team', 3, '4')], ('2026', '3'): [resultado('a', 'team', 1, '999')]}
        first, _ = previsao.gerar_entradas(state, calendar, base)
        base[('2026', '3')][0]['points'] = '0'
        second, _ = previsao.gerar_entradas(state, calendar, base)
        self.assertEqual(first, second)

    def test_paginacao_ua_retry_after_e_limite(self):
        calls, sleeps = [], []
        payload = {'MRData': {'limit': '100', 'offset': '0', 'total': '0', 'RaceTable': {'season': '2026', 'Races': []}}}
        class Response:
            status = 200
            headers = {}
            url = 'https://api.jolpi.ca/ergast/f1/2026/?limit=100&offset=0'
            def read(self): return json.dumps(payload).encode()
        class Fail429(Exception):
            code = 429
            headers = {'Retry-After': '121'}
        def open_(request, timeout=30):
            calls.append(request)
            if len(calls) == 1:
                raise Fail429()
            return Response()
        with self.assertRaisesRegex(RuntimeError, '120'):
            fontes.buscar_pagina('https://api.jolpi.ca/ergast/f1/2026/', 0,
                                 opener=open_, sleeper=sleeps.append)
        self.assertIn('PitwallLab/operacao-2026', calls[0].get_header('User-agent'))
        self.assertEqual(sleeps, [])

    def test_emissao_exclusiva_e_prospectivo_tem_guardas(self):
        dest = self.root / 'emissoes'
        data = {'evento': {'season': '2026'}, 'linhas': []}
        first = previsao.gravar_emissao(dest, 'x', data)
        self.assertTrue(first.is_dir())
        with self.assertRaises(FileExistsError):
            previsao.gravar_emissao(dest, 'x', data)
        now = datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, 'largada'):
            previsao.validar_prospectivo('2026-10-25T20:00:00Z', '2026-10-24T21:00:00Z',
                                          '2026-10-24T22:00:00Z', '2026-10-24T22:01:00Z', now)

    def test_modelo_congelado_carrega_e_inferencia_nao_ajusta(self):
        context = previsao.carregar_modelo()
        row = {'temporada': '2026', 'rodada': '1', 'piloto_id': 'double',
               'corrida': 'Teste', 'data_corrida': '2026-01-01', 'circuito_id': 'test',
               'equipe_id': 'double', 'equipe_id_entrada': 'double',
               'limite_inferior_referencia_utc': '2026-01-01T12:00:00Z',
               'posicao_classificacao': 1, 'posicao_classificacao_repetida': 0,
               'classificacao_ausente': 0, 'posicao_classificacao_ausente': 0,
               'media_posicao_final_5': None, 'taxa_podios_5': None, 'n_posicoes_5': 0,
               'n_podios_5': 0, 'media_pontos_equipe_5': None, 'n_corridas_equipe_5': 0,
               'n_participacoes_equipe_5': 0, 'historico_piloto_insuficiente': 1,
               'historico_equipe_insuficiente': 1, 'equipe_pre_corrida_ausente': 0,
               'referencia_temporal_ausente': 0}
        before = context['fingerprint']
        out = previsao.inferir(context, [row])
        self.assertEqual(len(out), 1)
        self.assertIsInstance(out[0]['probabilidade_modelo'], float)
        self.assertEqual(before, previsao._fingerprint_pipeline(context['pipeline']))

    def test_trava_fit_bloqueia_metodos_de_ajuste(self):
        context = previsao.carregar_modelo()
        with previsao._sem_fit():
            with self.assertRaisesRegex(RuntimeError, 'fit'):
                context['pipeline'].fit([[1.0] * 15], [0])


if __name__ == '__main__':
    unittest.main()
