"""Regressões R3 sintéticas, offline e restritas ao scratch."""
import io
import json
import os
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import operar_2026 as cli
from operacao2026 import fontes, previsao


SCRATCH = Path(os.environ.get('TMPDIR', '/Users/MBPaschoal/.hermes/cache/scratch'))


def corrida(round_, data, circuito, qtime='12:00:00Z', results=None, qualifying=None):
    race = {'season': '2026', 'round': str(round_), 'raceName': 'SYNTHETIC {}'.format(round_),
            'date': data, 'time': '20:00:00Z', 'Circuit': {'circuitId': circuito},
            'Qualifying': {'date': data, 'time': qtime}}
    if results is not None:
        race['Results'] = results
    if qualifying is not None:
        race['QualifyingResults'] = qualifying
    return race


def resultado(driver, team='team', position=1, points=25):
    return {'Driver': {'driverId': driver}, 'Constructor': {'constructorId': team},
            'position': str(position), 'points': str(points), 'status': 'Finished'}


def quali(driver, team='team', position=1):
    return {'Driver': {'driverId': driver, 'givenName': driver, 'familyName': 'Synthetic'},
            'Constructor': {'constructorId': team}, 'position': str(position)}


def pagina(races, endpoint, total=None, offset=0):
    field = {'classificacao': 'QualifyingResults', 'resultados': 'Results'}.get(endpoint)
    count = sum(len(race.get(field, [])) for race in races) if field else len(races)
    return json.dumps({'MRData': {'limit': '100', 'offset': str(offset),
                                  'total': str(count if total is None else total),
                                  'RaceTable': {'season': '2026', 'Races': races}}}).encode('utf-8')


def fonte(raw, endpoint, round_=None):
    item = {'bytes': raw, 'parametros': {'offset': 0, 'limit': 100}, 'status': 200,
            'url_solicitada': 'https://fixture.invalid/{}'.format(endpoint),
            'url_real': 'https://fixture.invalid/{}'.format(endpoint),
            'obtido_em_utc': '2026-06-06T13:00:00Z', 'origem': 'fixture'}
    if round_ is not None:
        item['rodada'] = str(round_)
    return item


class Operacao2026R3Test(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=str(SCRATCH))
        self.root = Path(self.temp.name)
        self.snapshots = self.root / 'snapshots'
        self.emissoes = self.root / 'emissoes'

    def tearDown(self):
        self.temp.cleanup()

    def _snapshot_ensaio(self, name, lacuna=False, resultado_alvo_futuro=False):
        anteriores = [corrida(number, '2026-0{}-0{}'.format(number, number), 'prior{}'.format(number),
                              results=[] if lacuna and number == 5 else [resultado('a'), resultado('b', position=2, points=18)])
                      for number in range(1, 6)]
        alvo = corrida(6, '2026-06-06', 'marina_bay', qualifying=[quali('a'), quali('b', position=2)])
        futuro = corrida(7, '2026-06-13', 'future', results=[])
        resultados = anteriores + ([corrida(6, '2026-06-06', 'marina_bay', results=[]), futuro]
                                    if resultado_alvo_futuro else [])
        calendario = anteriores + [alvo] + ([futuro] if resultado_alvo_futuro else [])
        pages = {'calendario': [fonte(pagina(calendario, 'calendario'), 'calendario')],
                 'classificacao': [fonte(pagina([alvo], 'classificacao'), 'classificacao', 6)],
                 'resultados': [fonte(pagina([event], 'resultados'), 'resultados', event['round'])
                                for event in resultados]}
        fontes.gravar_snapshot(self.snapshots, name, pages)
        if lacuna:
            index_path = self.snapshots / name / 'indice.json'
            index = json.loads(index_path.read_text())
            index['qualidade'] = {'resultados_disponiveis': ['1', '2', '3', '4'],
                                  'lacunas_resultados': ['5'], 'futuros': []}
            index_path.write_text(json.dumps(index), encoding='utf-8')

    def _run_ensaio(self, snapshot, emission_id, bloquear_raw=()):
        output = io.StringIO()
        def inferir(_, rows):
            return [dict(row, elegivel_previsao=True, motivos_inelegibilidade='',
                         probabilidade_modelo=0.5, probabilidade_constante=0.15,
                         ranking_modelo=1, favorito_modelo=True, ranking_classificacao=1,
                         favorito_classificacao=True, empates_modelo=1, empates_classificacao=1)
                    for row in rows]
        with ExitStack() as stack:
            stack.enter_context(patch.object(cli, 'SNAPSHOTS', self.snapshots))
            stack.enter_context(patch.object(cli, 'EMISSOES', self.emissoes))
            stack.enter_context(patch.object(previsao, 'carregar_historico_bruto', return_value=([], {})))
            stack.enter_context(patch.object(previsao, 'carregar_modelo', return_value={'hashes': {}}))
            stack.enter_context(patch.object(previsao, 'inferir', side_effect=inferir))
            stack.enter_context(patch.object(previsao, 'codigo_estado', return_value={'commit': None}))
            if bloquear_raw:
                original = Path.read_bytes
                def guarded(path):
                    if any(token in path.name for token in bloquear_raw):
                        raise AssertionError('raw alvo/futuro aberto: {}'.format(path.name))
                    return original(path)
                stack.enter_context(patch.object(Path, 'read_bytes', guarded))
            with redirect_stdout(output), redirect_stderr(output):
                code = cli.main(['ensaio', '--snapshot', snapshot, '--id', emission_id])
        return code, output.getvalue()

    def test_cli_ensaio_bloqueia_lacuna_anterior_e_emissao_completa_declara_lista_vazia(self):
        self._snapshot_ensaio('completo')
        code, output = self._run_ensaio('completo', 'ensaio-completo')
        self.assertEqual(code, 0, output)
        coverage = json.loads((self.emissoes / 'ensaio-completo/cobertura.json').read_text())
        report = (self.emissoes / 'ensaio-completo/relatorio.md').read_text()
        self.assertEqual(coverage['lacunas_resultados_relevantes'], [])
        self.assertIn('Política de lacunas', report)
        self.assertIn('[]', report)

        self._snapshot_ensaio('com-lacuna', lacuna=True)
        code, output = self._run_ensaio('com-lacuna', 'ensaio-bloqueado')
        self.assertEqual(code, 1)
        self.assertIn('rodada 5', output)
        self.assertIn('resultado indisponível', output)
        self.assertFalse((self.emissoes / 'ensaio-bloqueado').exists())

    def test_resultados_vazios_do_alvo_e_futuro_nao_abrem_nem_alteram_emissao(self):
        self._snapshot_ensaio('base')
        code, output = self._run_ensaio('base', 'base-emissao')
        self.assertEqual(code, 0, output)
        self._snapshot_ensaio('alvo-futuro-vazios', resultado_alvo_futuro=True)
        code, output = self._run_ensaio('alvo-futuro-vazios', 'vazios-emissao',
                                        bloquear_raw=('resultados_6_', 'resultados_7_'))
        self.assertEqual(code, 0, output)
        base = self.emissoes / 'base-emissao'
        vazios = self.emissoes / 'vazios-emissao'
        self.assertEqual((base / 'entradas.json').read_bytes(), (vazios / 'entradas.json').read_bytes())
        self.assertEqual((base / 'probabilidades.csv').read_bytes(), (vazios / 'probabilidades.csv').read_bytes())

    def test_piloto_ausente_em_gp_completo_preserva_janela_de_participacoes(self):
        # O GP 5 está completo: apenas 'b' participou. Isso não é lacuna da API.
        anteriores = [
            corrida(number, '2026-0{}-0{}'.format(number, number), 'prior{}'.format(number),
                    results=([resultado('b', position=2, points=18)] if number == 5 else
                             [resultado('a'), resultado('b', position=2, points=18)]))
            for number in range(1, 7)
        ]
        alvo = corrida(7, '2026-07-07', 'marina_bay',
                       qualifying=[quali('a'), quali('b', position=2)])
        fontes.gravar_snapshot(self.snapshots, 'participacao-ausente', {
            'calendario': [fonte(pagina(anteriores + [alvo], 'calendario'), 'calendario')],
            'classificacao': [fonte(pagina([alvo], 'classificacao'), 'classificacao', 7)],
            'resultados': [fonte(pagina([event], 'resultados'), 'resultados', event['round'])
                           for event in anteriores],
        })
        code, output = self._run_ensaio('participacao-ausente', 'ausencia-legitima')
        self.assertEqual(code, 0, output)
        dest = self.emissoes / 'ausencia-legitima'
        cobertura = json.loads((dest / 'cobertura.json').read_text())
        self.assertEqual(cobertura['lacunas_resultados_relevantes'], [])
        linhas = json.loads((dest / 'entradas.json').read_text())['linhas']
        piloto = next(row for row in linhas if row['piloto_id'] == 'a')
        self.assertEqual(piloto['n_posicoes_5'], 5)
        self.assertEqual(piloto['historico_piloto_insuficiente'], 0)
        self.assertEqual(piloto['n_corridas_equipe_5'], 5)
        self.assertEqual(piloto['n_participacoes_equipe_5'],
                         sum(len(event['Results']) for event in anteriores[-5:]))
        janelas = json.loads((dest / 'historicos.json').read_text())['janelas']
        janela_a = next(item for item in janelas if item['piloto_id'] == 'a')
        self.assertEqual(janela_a['piloto'], [['2026', str(n)] for n in (1, 2, 3, 4, 6)])

    def test_gp_anterior_vazio_bloqueia_mesmo_sem_declaracao_no_indice(self):
        self._snapshot_ensaio('lacuna-sem-marcador', lacuna=True)
        path = self.snapshots / 'lacuna-sem-marcador' / 'indice.json'
        index = json.loads(path.read_text())
        index['qualidade'].pop('lacunas_resultados')
        path.write_text(json.dumps(index), encoding='utf-8')
        code, output = self._run_ensaio('lacuna-sem-marcador', 'nao-publicar')
        self.assertEqual(code, 1)
        self.assertIn('rodada 5', output)
        self.assertIn('resultado indisponível', output)
        self.assertFalse((self.emissoes / 'nao-publicar').exists())

    def test_referencia_igual_largada_bloqueia_estado_e_ensaio_antes_de_resultados(self):
        austin = corrida(18, '2026-10-25', 'americas', qtime='20:00:00Z', qualifying=[quali('a')])
        singapura = corrida(17, '2026-10-18', 'marina_bay', qtime='20:00:00Z', qualifying=[quali('a')])
        anterior = corrida(16, '2026-10-11', 'prior', results=[resultado('a')])
        fontes.gravar_snapshot(self.snapshots, 'igual', {
            'calendario': [fonte(pagina([anterior, singapura, austin], 'calendario'), 'calendario')],
            'classificacao': [fonte(pagina([singapura], 'classificacao'), 'classificacao', 17),
                               fonte(pagina([austin], 'classificacao'), 'classificacao', 18)],
            'resultados': [fonte(pagina([anterior], 'resultados'), 'resultados', 16)],
        })
        output = io.StringIO()
        with patch.object(cli, 'SNAPSHOTS', self.snapshots), redirect_stdout(output), redirect_stderr(output):
            self.assertEqual(cli.main(['estado', '--snapshot', 'igual']), 1)
        self.assertIn('referência', output.getvalue())

        output = io.StringIO()
        with patch.object(cli, 'ROOT', self.root), patch.object(cli, 'SNAPSHOTS', self.snapshots), \
             patch.object(cli, 'EMISSOES', self.emissoes), \
             patch.object(cli, '_resultados_2026', side_effect=AssertionError('resultado não deveria abrir')), \
             redirect_stdout(output), redirect_stderr(output):
            self.assertEqual(cli.main(['ensaio', '--snapshot', 'igual', '--id', 'igual-ensaio']), 1)
        self.assertIn('referência', output.getvalue())
        self.assertFalse((self.emissoes / 'igual-ensaio').exists())

    def test_paginas_permite_101_participantes_do_mesmo_gp_em_resultados_e_classificacao(self):
        for endpoint, field in (('resultados', 'Results'), ('classificacao', 'QualifyingResults')):
            records = ([resultado('d{:03d}'.format(number), position=number + 1) for number in range(101)]
                       if endpoint == 'resultados' else
                       [quali('d{:03d}'.format(number), position=number + 1) for number in range(101)])
            event = corrida(1, '2026-03-01', 'circuit')
            first = dict(event, **{field: records[:100]})
            second = dict(event, **{field: records[100:]})
            pages = {0: {'bytes': pagina([first], endpoint, total=101, offset=0), 'parametros': {'offset': 0}},
                     100: {'bytes': pagina([second], endpoint, total=101, offset=100), 'parametros': {'offset': 100}}}
            received = fontes.paginas_completas(lambda offset: pages[offset], endpoint, '1', event)
            self.assertEqual(len(received), 2)

    def test_paginas_rejeita_id_duplicado_evento_divergente_e_calendario_duplicado(self):
        event = corrida(1, '2026-03-01', 'circuit')
        duplicate = dict(event, Results=[resultado('a', position=101)])
        first = dict(event, Results=[resultado('a')] +
                     [resultado('d{:03d}'.format(n), position=n + 1) for n in range(1, 100)])
        pages = {0: {'bytes': pagina([first], 'resultados', total=101, offset=0), 'parametros': {'offset': 0}},
                 100: {'bytes': pagina([duplicate], 'resultados', total=101, offset=100), 'parametros': {'offset': 100}}}
        with self.assertRaisesRegex(ValueError, 'piloto duplicado'):
            fontes.paginas_completas(lambda offset: pages[offset], 'resultados', '1', event)

        divergent = corrida(1, '2026-03-02', 'other', results=[resultado('b', position=2)])
        pages[100] = {'bytes': pagina([divergent], 'resultados', total=101, offset=100), 'parametros': {'offset': 100}}
        with self.assertRaisesRegex(ValueError, 'Envelope'):
            fontes.paginas_completas(lambda offset: pages[offset], 'resultados', '1', event)

        calendar_events = [event] + [corrida(n, '2026-03-01', 'circuit{}'.format(n)) for n in range(2, 101)]
        calendar = {0: {'bytes': pagina(calendar_events, 'calendario', total=101, offset=0), 'parametros': {'offset': 0}},
                    100: {'bytes': pagina([event], 'calendario', total=101, offset=100), 'parametros': {'offset': 100}}}
        with self.assertRaisesRegex(ValueError, 'Corrida duplicada'):
            fontes.paginas_completas(lambda offset: calendar[offset], 'calendario')


if __name__ == '__main__':
    unittest.main()
