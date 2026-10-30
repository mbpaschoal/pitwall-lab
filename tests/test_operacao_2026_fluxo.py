import argparse
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import operar_2026
from operacao2026 import fontes, previsao
from treinar_modelo_v1 import ENTRADAS_AUTORIZADAS


SCRATCH = Path(os.environ.get('TMPDIR') or tempfile.gettempdir()).resolve()


def corrida(round_, data, circuito='x', qtime='12:00:00Z'):
    return {'season': '2026', 'round': str(round_), 'raceName': 'GP {}'.format(round_), 'date': data,
            'time': '20:00:00Z', 'Circuit': {'circuitId': circuito},
            'Qualifying': {'date': data, 'time': qtime}}


def quali(driver, team, pos):
    return {'Driver': {'driverId': driver, 'givenName': driver, 'familyName': 'F'},
            'Constructor': {'constructorId': team}, 'position': str(pos) if pos is not None else None}


def resultado(driver, team, pos, pontos):
    return {'Driver': {'driverId': driver}, 'Constructor': {'constructorId': team},
            'position': str(pos), 'points': str(pontos), 'status': 'Finished'}


class FluxoOperacao2026Test(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=str(SCRATCH))
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_leitor_nunca_recebe_chave_alvo_ou_futura(self):
        target = corrida(3, '2026-03-15', 'marina_bay')
        calendar = [corrida(1, '2026-02-01'), corrida(2, '2026-03-01'), target, corrida(4, '2026-04-01')]
        state = previsao.preparar_alvo(target, [quali('a', 't', 1)])
        opened = []
        def reader(key):
            opened.append(key)
            if key in (('2026', '3'), ('2026', '4')):
                raise AssertionError('resultado alvo/futuro foi aberto')
            return [resultado('a', 't', 2, 8)]
        rows, audit = previsao.gerar_entradas(state, calendar, reader)
        self.assertEqual(opened, [('2026', '1'), ('2026', '2')])
        self.assertEqual(audit['resultados_lidos'], opened)
        self.assertEqual(rows[0]['n_posicoes_5'], 2)

    def test_mutacoes_alvo_futuro_nao_alteram_entradas(self):
        target = corrida(2, '2026-03-15', 'marina_bay')
        calendar = [corrida(1, '2026-03-01'), target, corrida(3, '2026-04-01')]
        state = previsao.preparar_alvo(target, [quali('a', 't', 1)])
        base = {('2026', '1'): [resultado('a', 't', 3, 4)],
                ('2026', '2'): [resultado('a', 't', 1, 999)],
                ('2026', '3'): [resultado('a', 't', 1, 999)]}
        first, _ = previsao.gerar_entradas(state, calendar, base)
        base[('2026', '2')][0]['points'] = '0'
        base[('2026', '3')][0]['points'] = '0'
        second, _ = previsao.gerar_entradas(state, calendar, base)
        self.assertEqual(first, second)

    def test_janela_cinco_gp_cruza_ano_sem_unir_ids(self):
        target = corrida(6, '2026-01-20', 'marina_bay')
        calendar = [
            {'season': '2025', 'round': str(i), 'raceName': 'H', 'date': '2025-0{}-01'.format(i),
             'time': '20:00:00Z', 'Circuit': {'circuitId': 'h'}} for i in range(1, 6)
        ] + [target]
        state = previsao.preparar_alvo(target, [quali('novo', 'nova', None)])
        results = {('2025', str(i)): [resultado('novo', 'nova', i, i), resultado('outro', 'nova', 9, 0)]
                   for i in range(1, 6)}
        rows, _ = previsao.gerar_entradas(state, calendar, results)
        row = rows[0]
        self.assertEqual(row['n_posicoes_5'], 5)
        self.assertEqual(row['n_corridas_equipe_5'], 5)
        self.assertEqual(row['n_participacoes_equipe_5'], 10)
        self.assertEqual(set(ENTRADAS_AUTORIZADAS), set(row) & set(ENTRADAS_AUTORIZADAS))
        self.assertNotIn('podio', row)

    def test_prospectivo_exige_ordem_e_utc_explicito(self):
        now = datetime(2026, 10, 25, 19, 0, tzinfo=timezone.utc)
        previsao.validar_prospectivo('2026-10-25T20:00:00Z', '2026-10-24T21:00:00Z',
                                     '2026-10-24T22:00:00Z', '2026-10-24T22:01:00Z',
                                     '2026-10-24T22:02:00Z', now)
        with self.assertRaisesRegex(ValueError, 'UTC explícito'):
            previsao.validar_prospectivo('2026-10-25T20:00:00Z', '2026-10-24T21:00:00',
                                         '2026-10-24T22:00:00Z', '2026-10-24T22:01:00Z',
                                         '2026-10-24T22:02:00Z', now)
        with self.assertRaisesRegex(ValueError, 'largada'):
            previsao.validar_prospectivo('2026-10-25T20:00:00Z', '2026-10-24T21:00:00Z',
                                         '2026-10-24T22:00:00Z', '2026-10-24T22:01:00Z',
                                         '2026-10-24T22:02:00Z', datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc))

    def test_emissao_tem_lote_completo_e_rejeita_escape_e_correcao_incompleta(self):
        data = {'evento': {'temporada': '2026', 'rodada': '1', 'circuito_id': 'x'}, 'modo': 'ENSAIO_RETROSPECTIVO',
                'linhas': [], 'fontes': [], 'historicos_usados': {}, 'limites': ['fixture sintética']}
        dest = previsao.gravar_emissao(self.root, 'ensaio-1', data)
        self.assertEqual({p.name for p in dest.iterdir()}, {'probabilidades.csv', 'entradas.json', 'cobertura.json',
                         'historicos.json', 'fontes.json', 'relatorio.md', 'manifesto.json'})
        with self.assertRaises(ValueError):
            previsao.gravar_emissao(self.root, '../escape', data)
        with self.assertRaisesRegex(ValueError, 'Correção'):
            previsao.gravar_emissao(self.root, 'ensaio-2', dict(data, versao_anterior='ensaio-1'))

    def test_estado_le_calendario_depois_so_classificacao_e_nao_carrega_modelo(self):
        event = corrida(18, '2026-10-25', 'americas')
        payload = {'MRData': {'RaceTable': {'Races': [event]}}}
        calls = []
        def ler_indice(root, snapshot):
            return {'snapshot_id': snapshot, 'fontes': []}
        def ler_snapshot(root, snapshot, carregar=True, endpoints=None):
            calls.append(tuple(endpoints))
            return {'snapshot_id': snapshot}, {'calendario': [({'arquivo': 'raw/calendar.json'}, payload)]} if endpoints == ['calendario'] else {'classificacao_18': []}
        with patch.object(fontes, 'ler_indice', ler_indice, create=True), \
             patch.object(fontes, 'ler_snapshot', ler_snapshot), \
             patch.object(previsao, 'carregar_modelo', side_effect=AssertionError('modelo não deveria carregar')):
            text = io.StringIO()
            with redirect_stdout(text):
                operar_2026.cmd_estado(argparse.Namespace(snapshot='fixture', temporada='2026', rodada=18, circuito='americas'))
        self.assertEqual(calls, [('calendario',), ('classificacao_18',)])
        self.assertIn('aguardando_classificacao', text.getvalue())

    def test_ensaio_completo_nao_pede_resultado_do_alvo_ou_futuro(self):
        prior = corrida(1, '2026-03-01', 'anterior')
        target = corrida(2, '2026-03-15', 'marina_bay')
        future = corrida(3, '2026-04-01', 'futuro')
        calendar_payload = {'MRData': {'RaceTable': {'Races': [prior, target, future]}}}
        q_payload = {'MRData': {'RaceTable': {'Races': [dict(target, QualifyingResults=[quali('a', 't', 1)])]}}}
        r_payload = {'MRData': {'RaceTable': {'Races': [dict(prior, Results=[resultado('a', 't', 2, 8)])]}}}
        calls = []
        def ler_indice(root, snapshot):
            return {'snapshot_id': snapshot, 'fontes': []}
        def ler_snapshot(root, snapshot, carregar=True, endpoints=None):
            calls.append(tuple(endpoints))
            if endpoints == ['calendario']:
                return {}, {'calendario': [({'arquivo': 'raw/calendar.json'}, calendar_payload)]}
            if endpoints == ['classificacao_2']:
                return {}, {'classificacao_2': [({'arquivo': 'raw/q.json'}, q_payload)]}
            if endpoints == ['resultados_1']:
                return {}, {'resultados_1': [({'arquivo': 'raw/r1.json'}, r_payload)]}
            raise AssertionError('endpoint proibido: {}'.format(endpoints))
        with patch.object(fontes, 'ler_indice', ler_indice, create=True), \
             patch.object(fontes, 'ler_snapshot', ler_snapshot), \
             patch.object(previsao, 'carregar_historico_bruto', return_value=([], {})), \
             patch.object(previsao, 'carregar_modelo', return_value={'hashes': {}}), \
             patch.object(previsao, 'inferir', side_effect=lambda model, rows: rows), \
             patch.object(operar_2026, '_emissao_data', return_value={'linhas': []}), \
             patch.object(previsao, 'gravar_emissao', return_value=self.root / 'ensaio-2'):
            operar_2026.cmd_ensaio(argparse.Namespace(snapshot='fixture', id='ensaio-2'))
        self.assertEqual(calls, [('calendario',), ('classificacao_2',), ('resultados_1',)])


if __name__ == '__main__':
    unittest.main()
