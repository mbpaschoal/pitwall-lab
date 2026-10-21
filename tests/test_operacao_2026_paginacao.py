"""Paginação sintética: fragmentos de GP, integridade e admissão offline."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import operar_2026 as cli
from operacao2026 import fontes
from tests.test_operacao_2026_r3 import corrida, fonte, pagina, quali, resultado


class PaginacaoGPTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
        self.root = Path(self.temp.name)
        self.counter = 0

    def tearDown(self):
        self.temp.cleanup()

    def _fragmentos(self, endpoint, quantidades=(100, 1)):
        field = fontes._field(endpoint)
        make = resultado if endpoint == 'resultados' else quali
        registros = [make('d{:03d}'.format(n), position=n + 1) for n in range(sum(quantidades))]
        event = corrida(1, '2026-03-01', 'circuit')
        payloads = []
        start = 0
        for offset, size in zip((0, 100), quantidades):
            fragment = dict(event, **{field: registros[start:start + size]})
            payloads.append(json.loads(pagina([fragment], endpoint, total=101, offset=offset)))
            start += size
        return event, registros, payloads

    def _itens(self, payloads):
        items = [fonte(json.dumps(p).encode('utf-8'), 'fixture') for p in payloads]
        for offset, item in zip((0, 100), items):
            item['parametros']['offset'] = offset
        return items

    def _coletor(self, endpoint, payloads):
        items = self._itens(payloads)
        return fontes.paginas_completas(lambda offset: items[offset // 100], endpoint,
                                       None if endpoint == 'calendario' else '1')

    def _snapshot(self, endpoint, payloads):
        self.counter += 1
        sid = 's{}'.format(self.counter)
        items = self._itens(payloads)
        for offset, item in zip((0, 100), items):
            item['parametros']['offset'] = offset
            if endpoint != 'calendario':
                item['rodada'] = '1'
        fontes.gravar_snapshot(self.root, sid, {endpoint: items})
        return sid

    def _recusa_ambos(self, endpoint, payloads):
        with self.assertRaises(ValueError):
            self._coletor(endpoint, payloads)
        sid = self._snapshot(endpoint, payloads)
        with self.assertRaises(ValueError):
            fontes.ler_snapshot(self.root, sid, endpoints={endpoint})

    def test_gp_fragmentado_reune_todos_os_registros_sem_perda_ou_duplicacao(self):
        for endpoint in ('resultados', 'classificacao'):
            with self.subTest(endpoint=endpoint):
                event, expected, payloads = self._fragmentos(endpoint)
                pages = self._coletor(endpoint, payloads)
                self.assertEqual(len(pages), 2)
                sid = self._snapshot(endpoint, payloads)
                _, selected = fontes.ler_snapshot(self.root, sid, endpoints={endpoint})
                records = [r for race in cli._races(selected[endpoint]) for r in race[fontes._field(endpoint)]]
                self.assertEqual(records, expected)
                self.assertEqual(len(records), len({r['Driver']['driverId'] for r in records}))
                with patch.object(cli, 'SNAPSHOTS', self.root):
                    if endpoint == 'classificacao':
                        state = cli._event_with_q(sid, [event], 'circuit')[2]
                        self.assertEqual([r['piloto_id'] for r in state['registros']],
                                         [r['Driver']['driverId'] for r in expected])
                    else:
                        alvo = corrida(2, '2026-04-02', 'target')
                        state = cli.previsao.preparar_alvo(alvo, [quali('synthetic')])
                        results, _ = cli._resultados_2026(sid, [event, alvo], state)
                        self.assertEqual(results[('2026', '1')], expected)

    def test_piloto_duplicado_no_gp_e_recusado(self):
        for endpoint in ('resultados', 'classificacao'):
            _, _, payloads = self._fragmentos(endpoint)
            field = fontes._field(endpoint)
            payloads[1]['MRData']['RaceTable']['Races'][0][field][0]['Driver']['driverId'] = 'd000'
            with self.subTest(endpoint=endpoint):
                self._recusa_ambos(endpoint, payloads)

    def test_metadados_dos_fragmentos_devem_coincidir(self):
        for endpoint in ('resultados', 'classificacao'):
            _, _, base = self._fragmentos(endpoint)
            for change in ('date', 'time', 'raceName', 'Circuit', 'Qualifying'):
                payloads = copy.deepcopy(base)
                race = payloads[1]['MRData']['RaceTable']['Races'][0]
                race[change] = {'date': '2026-03-02', 'time': '21:00:00Z',
                                'raceName': 'OTHER SYNTHETIC',
                                'Circuit': {'circuitId': 'other'},
                                'Qualifying': {'date': '2026-03-01', 'time': '11:00:00Z'}}[change]
                with self.subTest(endpoint=endpoint, campo=change):
                    self._recusa_ambos(endpoint, payloads)

    def test_offset_divergente_e_recusado(self):
        for endpoint in ('resultados', 'classificacao'):
            _, _, payloads = self._fragmentos(endpoint)
            payloads[1]['MRData']['offset'] = '99'
            with self.subTest(endpoint=endpoint):
                self._recusa_ambos(endpoint, payloads)

    def test_total_divergente_e_recusado(self):
        for endpoint in ('resultados', 'classificacao'):
            _, _, payloads = self._fragmentos(endpoint)
            payloads[1]['MRData']['total'] = '102'
            with self.subTest(endpoint=endpoint):
                self._recusa_ambos(endpoint, payloads)

    def test_quantidades_por_pagina_devem_respeitar_limit_offset_total(self):
        for endpoint in ('resultados', 'classificacao'):
            for sizes in ((99, 2), (101, 0), (0, 101), (100, 0)):
                _, _, payloads = self._fragmentos(endpoint, sizes)
                with self.subTest(endpoint=endpoint, quantidades=sizes):
                    self._recusa_ambos(endpoint, payloads)

    def test_calendario_paginado_valido_preserva_todas_as_corridas(self):
        events = [corrida(n, '2026-03-01', 'circuit{}'.format(n)) for n in range(1, 102)]
        payloads = [json.loads(pagina(events[:100], 'calendario', total=101, offset=0)),
                    json.loads(pagina(events[100:], 'calendario', total=101, offset=100))]
        self.assertEqual(len(self._coletor('calendario', payloads)), 2)
        sid = self._snapshot('calendario', payloads)
        _, selected = fontes.ler_snapshot(self.root, sid, endpoints={'calendario'})
        self.assertEqual(cli._races(selected['calendario']), events)

    def test_corrida_duplicada_no_calendario_e_recusada(self):
        events = [corrida(n, '2026-03-01', 'circuit{}'.format(n)) for n in range(1, 101)]
        payloads = [json.loads(pagina(events, 'calendario', total=101, offset=0)),
                    json.loads(pagina([events[0]], 'calendario', total=101, offset=100))]
        self._recusa_ambos('calendario', payloads)

    def test_quantidades_do_calendario_tambem_devem_ser_coerentes(self):
        events = [corrida(n, '2026-03-01', 'circuit{}'.format(n)) for n in range(1, 102)]
        payloads = [json.loads(pagina(events[:99], 'calendario', total=101, offset=0)),
                    json.loads(pagina(events[99:], 'calendario', total=101, offset=100))]
        self._recusa_ambos('calendario', payloads)
