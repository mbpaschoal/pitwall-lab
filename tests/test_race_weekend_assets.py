"""Contrato focal das etapas 1 e 2: asset offline Race Weekend."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import preparar_dashboard_race_weekend as preparar
import registro_emissoes
from operacao2026 import fontes
import app
import race_weekend_dados
from dashboard_dados import carregar_temporada, dados_do_gp
from streamlit.testing.v1 import AppTest


RAIZ = Path(__file__).resolve().parents[1]


class TestAssetsRaceWeekend(unittest.TestCase):
    def test_tempos_formula1dashboard_austin_entram_no_asset_com_herta_excluido_da_previsao(self):
        dados, arquivos = preparar._tempos_formula1dashboard(RAIZ, 18, {
            'antonelli': {'ranking_modelo': 1, 'probabilidade_modelo': 0.8353690998809116},
        })
        self.assertEqual(set(dados['sessoes']), {'TL1', 'TL2', 'TL3', 'Q'})
        self.assertEqual([dados['sessoes'][chave]['cobertura'] for chave in ('TL1', 'TL2', 'TL3', 'Q')], [22, 22, 22, 22])
        herta = next(item for item in dados['sessoes']['TL1']['linhas'] if item['numero_carro'] == 25)
        self.assertEqual(herta['motivo_exclusao_comparacao'], 'substituto de treino sem identidade canônica na previsão do GP')
        antonelli = next(item for item in dados['sessoes']['Q']['linhas'] if item['piloto_id'] == 'antonelli')
        self.assertEqual(antonelli['ranking_modelo'], 1)
        self.assertTrue(arquivos)

    def test_emissao_vencem_q_base_divergente_com_paginas_completas(self):
        hashes_q_base = set()

        def pagina(evento, resultados, offset, total):
            return json.dumps({'MRData': {'limit': '100', 'offset': str(offset), 'total': str(total),
                                          'RaceTable': {'season': '2026', 'Races': [dict(
                                              evento, QualifyingResults=resultados,
                                          )]}}}).encode('utf-8')

        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            base = raiz / 'data' / 'operacao_2026' / 'snapshots'
            evento = {
                'season': '2026', 'round': '18', 'raceName': 'GP Sintético', 'date': '2026-10-25',
                'time': '20:00:00Z', 'Circuit': {'circuitId': 'americas', 'Location': {}},
            }
            def fonte(raw, rodada=None, offset=0, obtido='2026-10-24T22:01:00Z'):
                item = {'bytes': raw, 'parametros': {'offset': offset, 'limit': 100}, 'status': 200,
                        'url_solicitada': 'https://fixture.invalid/q', 'url_real': 'https://fixture.invalid/q',
                        'obtido_em_utc': obtido, 'origem': 'fixture'}
                if rodada is not None:
                    item['rodada'] = str(rodada)
                return item
            q_base = [
                {'Driver': {'driverId': 'base{}'.format(i), 'givenName': 'Base', 'familyName': str(i)},
                 'Constructor': {'constructorId': 'base_obsoleta_{}'.format(i)}, 'position': str(i + 1)}
                for i in range(101)
            ]
            fontes.gravar_snapshot(base, 'base', {
                'calendario': [fonte(json.dumps({'MRData': {'limit': '100', 'offset': '0', 'total': '1',
                                                   'RaceTable': {'season': '2026', 'Races': [evento]}}}).encode())],
                # A ordem no índice é intencionalmente inversa; o consumidor deve ordenar por offset.
                'classificacao': [
                    fonte(pagina(evento, q_base[100:], 100, 101), 18, 100),
                    fonte(pagina(evento, q_base[:100], 0, 101), 18, 0),
                ],
            })
            hashes_q_base = {
                source['sha256'] for source in fontes.ler_indice(base, 'base')['fontes']
                if source['endpoint'] == 'classificacao'
            }
            q_canonica = [
                {'Driver': {'driverId': 'p{}'.format(i), 'givenName': 'Canon', 'familyName': str(i)},
                 'Constructor': {'constructorId': 'canonica_{}'.format(i)}, 'position': str(i + 1)}
                for i in range(101)
            ]
            fontes.gravar_snapshot(base, 'emissao-q', {
                'classificacao': [
                    fonte(pagina(evento, q_canonica[:100], 0, 101), 18, 0, '2026-10-24T22:01:00Z'),
                    fonte(pagina(evento, q_canonica[100:], 100, 101), 18, 100, '2026-10-24T22:02:00Z'),
                ],
            })
            indice_q = fontes.ler_indice(base, 'emissao-q')
            emissao = raiz / 'reports' / 'emissao'
            emissao.mkdir(parents=True)
            csv = ('piloto_id,elegivel_previsao,probabilidade_modelo,ranking_modelo,ranking_classificacao\n'
                   'p0,True,0.4,1,1\n').encode('utf-8')
            (emissao / 'probabilidades.csv').write_bytes(csv)
            manifesto = {
                'modo': 'ENSAIO_RETROSPECTIVO',
                'evento': {'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas'},
                'source_snapshots': ['emissao-q'], 'fontes': indice_q['fontes'],
                'emitido_em_utc': '2026-10-24T22:30:00Z',
                'modelos': {'modelo': 'm', 'metadados': 'm', 'esquema': 'm'},
                'hashes_saidas': {'probabilidades.csv': __import__('hashlib').sha256(csv).hexdigest()},
            }
            (emissao / 'manifesto.json').write_text(json.dumps(manifesto), encoding='utf-8')
            declaracoes = ({'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas', 'snapshot': 'emissao-q',
                            'diretorio': 'reports/emissao', 'modo': 'ENSAIO_RETROSPECTIVO'},)
            leitor_fontes = preparar._fontes_snapshot
            with patch.object(preparar, 'SNAPSHOT_2026', 'base'), \
                 patch.object(preparar, '_fontes_snapshot', side_effect=lambda root, nome=preparar.SNAPSHOT_2026:
                              leitor_fontes(root, 'base' if nome == preparar.SNAPSHOT_2026 else nome)), \
                 patch.object(registro_emissoes, 'DECLARACOES', declaracoes):
                dados, _, _, proveniencia = preparar._dados_2026(raiz)
        piloto = next(item for item in dados['previsoes'] if item['rodada'] == 18 and item['piloto_id'] == 'p0')
        corrida = next(item for item in dados['corridas'] if item['rodada'] == 18)
        self.assertEqual(piloto['equipe_id'], 'canonica_0')
        self.assertEqual(len(corrida['fontes_qualificacao_sha256']), 2)
        proveniencia_q = proveniencia['emissoes']['2026:18:americas']
        self.assertEqual(proveniencia_q['fonte_qualificacao_sha256'], corrida['fontes_qualificacao_sha256'][0])
        self.assertEqual(proveniencia_q['fontes_qualificacao_sha256'], corrida['fontes_qualificacao_sha256'])
        self.assertTrue(set(proveniencia_q['fontes_qualificacao_sha256']).isdisjoint(hashes_q_base))

    def test_c_q_base_paginada_sem_emissao_usa_offsets_ordenados(self):
        evento = {'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas', 'data': '2026-10-25'}
        corridas = []
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            for offset, pilotos in ((100, range(100, 101)), (0, range(100))):
                resultados = [
                    {'Driver': {'driverId': 'base{}'.format(item)}, 'Constructor': {'constructorId': 'team'},
                     'position': str(item + 1)} for item in pilotos
                ]
                raw = json.dumps({'MRData': {'limit': '100', 'offset': str(offset), 'total': '101',
                    'RaceTable': {'season': '2026', 'Races': [{
                        'season': '2026', 'round': '18', 'date': '2026-10-25', 'time': '20:00:00Z',
                        'Circuit': {'circuitId': 'americas'}, 'QualifyingResults': resultados,
                    }]}}}).encode('utf-8')
                path = pasta / 'q-{}.json'.format(offset)
                path.write_bytes(raw)
                corridas.append(({'endpoint': 'classificacao', 'parametros': {'offset': offset, 'limit': 100},
                                  'sha256': hashlib.sha256(raw).hexdigest()}, path))
            ordenadas, resultados = preparar._paginas_qualificacao_comprovadas(corridas, evento)
        self.assertEqual([source['parametros']['offset'] for source, _ in ordenadas], [0, 100])
        self.assertEqual([item['Driver']['driverId'] for item in resultados],
                         ['base{}'.format(item) for item in range(101)])

    def test_c_q_base_paginada_sem_emissao_entra_no_asset(self):
        hashes_esperados = []
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            snapshots = raiz / 'data' / 'operacao_2026' / 'snapshots'
            evento = {
                'season': '2026', 'round': '18', 'raceName': 'GP Sintético', 'date': '2026-10-25',
                'time': '20:00:00Z', 'Circuit': {'circuitId': 'americas', 'Location': {}},
            }
            pilotos = [
                {'Driver': {'driverId': 'base{}'.format(item), 'givenName': 'Base', 'familyName': str(item)},
                 'Constructor': {'constructorId': 'team'}, 'position': str(item + 1)}
                for item in range(101)
            ]
            def pagina(offset, itens):
                return json.dumps({'MRData': {'limit': '100', 'offset': str(offset), 'total': '101',
                    'RaceTable': {'season': '2026', 'Races': [dict(evento, QualifyingResults=itens)]}}}).encode()
            def fonte(raw, offset):
                return {'bytes': raw, 'parametros': {'offset': offset, 'limit': 100}, 'status': 200,
                        'url_solicitada': 'https://fixture.invalid/q', 'url_real': 'https://fixture.invalid/q',
                        'obtido_em_utc': '2026-10-24T22:01:00Z', 'origem': 'fixture', 'rodada': '18'}
            calendario = json.dumps({'MRData': {'limit': '100', 'offset': '0', 'total': '1',
                'RaceTable': {'season': '2026', 'Races': [evento]}}}).encode()
            fontes.gravar_snapshot(snapshots, 'base-paginada', {
                'calendario': [dict(fonte(calendario, 0), rodada=None)],
                'classificacao': [fonte(pagina(100, pilotos[100:]), 100), fonte(pagina(0, pilotos[:100]), 0)],
            })
            hashes_esperados = [
                source['sha256'] for source in sorted(fontes.ler_indice(snapshots, 'base-paginada')['fontes'],
                                                       key=lambda source: source['parametros']['offset'])
                if source['endpoint'] == 'classificacao'
            ]
            leitor_fontes = preparar._fontes_snapshot
            with patch.object(preparar, 'SNAPSHOT_2026', 'base-paginada'), \
                 patch.object(preparar, '_fontes_snapshot', side_effect=lambda root, nome='base-paginada': leitor_fontes(root, nome)), \
                 patch.object(registro_emissoes, 'DECLARACOES', ()):
                dados, _, _, _ = preparar._dados_2026(raiz)
        corrida = next(item for item in dados['corridas'] if item['rodada'] == 18)
        self.assertEqual(corrida['estado_qualificacao'], 'local_disponivel')
        self.assertEqual(corrida['fontes_qualificacao_sha256'], hashes_esperados)
        self.assertEqual(dados['previsoes'], [])

    def test_q_paginada_recusa_lacuna_duplicidade_total_ids_e_evento(self):
        evento = {'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas', 'data': '2026-10-25'}

        def construir(paginas):
            with tempfile.TemporaryDirectory() as tmp:
                pasta = Path(tmp)
                fontes_paginas = []
                for indice, (offset, total, pilotos, circuito) in enumerate(paginas):
                    resultados = [
                        {'Driver': {'driverId': piloto}, 'Constructor': {'constructorId': 'team'},
                         'position': str(posicao + 1)}
                        for posicao, piloto in enumerate(pilotos)
                    ]
                    raw = json.dumps({'MRData': {'limit': '100', 'offset': str(offset), 'total': str(total),
                        'RaceTable': {'season': '2026', 'Races': [{
                            'season': '2026', 'round': '18', 'date': '2026-10-25', 'time': '20:00:00Z',
                            'Circuit': {'circuitId': circuito}, 'QualifyingResults': resultados,
                        }]}}}).encode('utf-8')
                    path = pasta / 'q-{}.json'.format(indice)
                    path.write_bytes(raw)
                    fontes_paginas.append(({
                        'endpoint': 'classificacao', 'parametros': {'offset': offset, 'limit': 100},
                        'sha256': hashlib.sha256(raw).hexdigest(),
                    }, path))
                with self.assertRaises(ValueError):
                    preparar._paginas_qualificacao_comprovadas(fontes_paginas, evento)

        primeiros = ['p{:03d}'.format(item) for item in range(100)]
        ultimo = ['p100']
        with self.subTest('offset ausente'):
            construir([(0, 101, primeiros, 'americas')])
        with self.subTest('offset duplicado'):
            construir([(0, 101, primeiros, 'americas'), (0, 101, ultimo, 'americas')])
        with self.subTest('total divergente'):
            construir([(0, 101, primeiros, 'americas'), (100, 100, ultimo, 'americas')])
        with self.subTest('id duplicado'):
            construir([(0, 101, primeiros, 'americas'), (100, 101, ['p000'], 'americas')])
        with self.subTest('evento divergente'):
            construir([(0, 101, primeiros, 'americas'), (100, 101, ultimo, 'outro')])

    def test_q_paginada_recusa_hash_adulterado_antes_de_gerar_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            base = raiz / 'data' / 'operacao_2026' / 'snapshots'
            evento = {'season': '2026', 'round': '18', 'date': '2026-10-25', 'time': '20:00:00Z',
                      'Circuit': {'circuitId': 'americas'}, 'QualifyingResults': []}
            raw = json.dumps({'MRData': {'limit': '100', 'offset': '0', 'total': '0',
                                         'RaceTable': {'season': '2026', 'Races': [evento]}}}).encode('utf-8')
            fontes.gravar_snapshot(base, 'adulterado', {'classificacao': [{
                'bytes': raw, 'parametros': {'offset': 0, 'limit': 100}, 'status': 200,
                'url_solicitada': 'https://fixture.invalid/q', 'url_real': 'https://fixture.invalid/q',
                'obtido_em_utc': '2026-10-24T22:01:00Z', 'origem': 'fixture', 'rodada': '18',
            }]})
            raw_path = next((base / 'adulterado' / 'raw').glob('*.json'))
            raw_path.write_bytes(raw + b' ')
            with self.assertRaisesRegex(ValueError, 'Hash divergente'):
                preparar._fontes_snapshot(raiz, 'adulterado')

    def test_participante_prospectivo_e_classificado_sem_resultado_observado(self):
        participante = preparar._participante_da_emissao(
            18, 'piloto_teste',
            {'piloto': 'Piloto Teste', 'equipe_id': 'equipe_teste', 'equipe': 'Equipe Teste'},
            {'elegivel_previsao': 'True', 'probabilidade_modelo': '0.25', 'ranking_modelo': '1',
             'ranking_classificacao': '2'},
        )
        self.assertEqual(participante['rodada'], 18)
        self.assertIsNone(participante['resultado_observado'])
        self.assertIsNone(participante['status_resultado'])
        self.assertEqual(participante['probabilidade_modelo'], 0.25)
        self.assertTrue(participante['elegivel_previsao'])

    def test_participante_prospectivo_descarta_resultado_local_do_mesmo_gp(self):
        participante = preparar._participante_da_emissao(
            18, 'piloto_teste',
            {'piloto': 'Piloto Teste', 'equipe_id': 'equipe_teste', 'equipe': 'Equipe Teste'},
            {'elegivel_previsao': 'True', 'probabilidade_modelo': '0.25', 'ranking_modelo': '1',
             'ranking_classificacao': '2'},
            existente={'resultado_observado': 1, 'status_resultado': 'Finished', 'podio': True},
            prospectivo=True,
        )
        self.assertIsNone(participante['resultado_observado'])
        self.assertIsNone(participante['status_resultado'])
        self.assertIsNone(participante['podio'])

    def test_projecao_prospectiva_limpa_toda_populacao_e_estado_resultado(self):
        def pagina(races, campo=None):
            total = sum(len(race.get(campo, [])) for race in races) if campo else len(races)
            return json.dumps({'MRData': {'limit': '100', 'offset': '0', 'total': str(total),
                                          'RaceTable': {'season': '2026', 'Races': races}}}).encode('utf-8')

        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            snapshot = 'sintetico-prospectivo'
            base = raiz / 'data' / 'operacao_2026' / 'snapshots'
            evento = {
                'season': '2026', 'round': '18', 'raceName': 'GP Sintético', 'date': '2026-10-25',
                'time': '20:00:00Z', 'Circuit': {'circuitId': 'americas', 'Location': {}},
            }
            resultados = [
                {'Driver': {'driverId': piloto, 'givenName': piloto, 'familyName': 'F'},
                 'Constructor': {'constructorId': 'equipe'}, 'position': str(posicao), 'points': '25', 'status': 'Finished'}
                for piloto, posicao in (('a', 1), ('b', 2), ('c', 3))
            ]
            classificacao = [
                {'Driver': {'driverId': piloto, 'givenName': piloto, 'familyName': 'F'},
                 'Constructor': {'constructorId': 'equipe'}, 'position': str(posicao)}
                for piloto, posicao in (('a', 1), ('b', 2))
            ]
            def fonte(raw, rodada=None):
                item = {'bytes': raw, 'parametros': {'offset': 0, 'limit': 100}, 'status': 200,
                        'url_solicitada': 'https://fixture.invalid', 'url_real': 'https://fixture.invalid',
                        'obtido_em_utc': '2026-10-24T22:01:00Z', 'origem': 'fixture'}
                if rodada is not None:
                    item['rodada'] = str(rodada)
                return item
            fontes.gravar_snapshot(base, snapshot, {
                'calendario': [fonte(pagina([evento]))],
                'resultados': [fonte(pagina([dict(evento, Results=resultados)], 'Results'), 18)],
                'classificacao': [fonte(pagina([dict(evento, QualifyingResults=classificacao)], 'QualifyingResults'), 18)],
            })
            indice = fontes.ler_indice(base, snapshot)
            fontes_manifesto = indice['fontes']
            q = next(item for item in fontes_manifesto if item['endpoint'] == 'classificacao')
            emissao = raiz / 'reports' / 'emissao'
            emissao.mkdir(parents=True)
            csv = ('piloto_id,elegivel_previsao,probabilidade_modelo,ranking_modelo,ranking_classificacao\n'
                   'a,True,0.4,1,1\n').encode('utf-8')
            (emissao / 'probabilidades.csv').write_bytes(csv)
            manifesto = {
                'modo': 'PROSPECTIVO', 'evento': {'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas'},
                'source_snapshots': [snapshot], 'fontes': fontes_manifesto,
                'emitido_em_utc': '2026-10-24T22:30:00Z',
                'corte_temporal': {'qualificacao_inicio_utc': '2026-10-24T00:00:00Z',
                                   'qualificacao_encerrada_em_utc': '2026-10-24T22:00:00Z',
                                   'qualificacao_disponivel_em_utc': '2026-10-24T22:01:00Z',
                                   'corte_utc': '2026-10-24T22:20:00Z',
                                   'corrida_programada_em_utc': '2026-10-25T20:00:00Z',
                                   'resultado_alvo_incluido': False},
                'modelos': {'modelo': 'm', 'metadados': 'm', 'esquema': 'm'},
                'hashes_saidas': {'probabilidades.csv': __import__('hashlib').sha256(csv).hexdigest()},
            }
            (emissao / 'manifesto.json').write_text(json.dumps(manifesto), encoding='utf-8')
            declaracoes = ({'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas', 'snapshot': snapshot,
                            'diretorio': 'reports/emissao', 'modo': 'PROSPECTIVO'},)
            fontes_snapshot_original = preparar._fontes_snapshot
            with patch.object(preparar, 'SNAPSHOT_2026', snapshot), \
                 patch.object(preparar, '_fontes_snapshot', side_effect=lambda root, nome=snapshot: fontes_snapshot_original(root, snapshot if nome == preparar.SNAPSHOT_2026 else nome)), \
                 patch.object(registro_emissoes, 'DECLARACOES', declaracoes):
                dados, _, _, _ = preparar._dados_2026(raiz)
        corrida = next(item for item in dados['corridas'] if item['rodada'] == 18)
        participantes = {item['piloto_id']: item for item in dados['previsoes'] if item['rodada'] == 18}
        self.assertEqual(corrida['estado_resultado'], 'indisponivel')
        self.assertEqual(corrida['motivo_resultado'], preparar.MOTIVO_SEM_RESULTADO)
        self.assertEqual(set(participantes), {'a', 'b', 'c'})
        self.assertTrue(all(item['resultado_observado'] is None for item in participantes.values()))
        self.assertTrue(all(item['status_resultado'] is None for item in participantes.values()))

    def test_leitor_aceita_previsao_registrada_sem_alvo(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            destino = raiz / 'frontend_assets' / 'race_weekend.json'
            destino.parent.mkdir()
            asset = preparar.gerar(RAIZ, destino)
            corrida = next(item for item in asset['dados_2026']['corridas'] if item['rodada'] == 18)
            corrida.update({'estado_previsao': 'previsao_registrada', 'estado_operacao': 'previsao_registrada'})
            asset['dados_2026']['previsoes'].append(preparar._participante_da_emissao(
                18, 'piloto_teste',
                {'piloto': 'Piloto Teste', 'equipe_id': 'equipe_teste', 'equipe': 'Equipe Teste'},
                {'elegivel_previsao': 'True', 'probabilidade_modelo': '0.25', 'ranking_modelo': '1',
                 'ranking_classificacao': '2'},
            ))
            destino.write_text(json.dumps(asset), encoding='utf-8')
            carregado = race_weekend_dados.carregar_asset(raiz)
        pacote = race_weekend_dados.pacote_2026(carregado)
        piloto = next(item for item in pacote['participantes_por_rodada'][18] if item['piloto_id'] == 'piloto_teste')
        self.assertFalse(piloto['alvo_conhecido'])
        self.assertIsNone(piloto['podio'])

    def test_gera_asset_local_com_nomes_historicos_e_cobertura_2026(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / 'race_weekend.json'
            asset = preparar.gerar(RAIZ, destino)
            self.assertEqual(json.loads(destino.read_text(encoding='utf-8')), asset)
        self.assertEqual(asset['versao'], 2)
        self.assertEqual(asset['temporadas'], [2024, 2025, 2026])
        self.assertEqual(asset['identidades']['2024:1:hamilton']['equipe_id'], 'mercedes')
        self.assertEqual(asset['identidades']['2025:1:hamilton']['equipe_id'], 'ferrari')
        self.assertEqual(asset['identidades']['2024:1:max_verstappen']['piloto'], 'Max Verstappen')
        corrida_2026 = {item['rodada']: item for item in asset['dados_2026']['corridas']}
        self.assertEqual(len(corrida_2026), 23)
        self.assertEqual(corrida_2026[1]['estado_resultado'], 'observado_local')
        self.assertEqual(corrida_2026[17]['estado_resultado'], 'observado_local')
        self.assertEqual(corrida_2026[17]['estado_previsao'], 'ensaio_retrospectivo')
        self.assertEqual(corrida_2026[17]['estado_operacao'], 'ensaio_retrospectivo')
        self.assertEqual(corrida_2026[1]['estado_operacao'], 'ensaio_retrospectivo')
        self.assertEqual(corrida_2026[18]['estado_qualificacao'], 'local_disponivel')
        self.assertEqual(corrida_2026[18]['estado_previsao'], 'previsao_registrada')
        self.assertEqual(corrida_2026[18]['estado_resultado'], 'indisponivel')
        self.assertEqual(corrida_2026[18]['cidade'], 'Austin')
        self.assertEqual(corrida_2026[18]['pais'], 'USA')
        self.assertEqual(corrida_2026[18]['data'], '2026-10-25')
        self.assertEqual(corrida_2026[18]['circuito_nome'], 'Circuit of the Americas')
        self.assertEqual(corrida_2026[18]['estado_operacao'], 'previsao_registrada')
        self.assertEqual(corrida_2026[18]['motivo_resultado'], 'snapshot local de resultados ausente; o calendário não prova que a corrida não foi concluída')
        singapura = [item for item in asset['dados_2026']['previsoes'] if item['rodada'] == 17]
        self.assertEqual(len(singapura), 22)
        self.assertEqual(singapura[0]['piloto'], 'Max Verstappen')
        self.assertEqual(singapura[0]['equipe_id'], 'red_bull')
        observados = [item for item in asset['dados_2026']['previsoes'] if item['resultado_observado'] is not None]
        self.assertEqual(len(observados), 374)
        self.assertEqual(len({(item['temporada'], item['rodada'], item['piloto_id']) for item in observados}), 374)
        ausentes_classificacao = {(item['rodada'], item['piloto_id']) for item in asset['dados_2026']['previsoes']
                                  if item['probabilidade_modelo'] is None}
        self.assertEqual(ausentes_classificacao, {(1, 'max_verstappen'), (1, 'sainz'), (1, 'stroll'),
                                                  (14, 'bearman'), (14, 'stroll')})
        for item in asset['dados_2026']['previsoes']:
            if (item['rodada'], item['piloto_id']) in ausentes_classificacao:
                self.assertIn('classificação capturada', item['motivos_inelegibilidade'])
        self.assertEqual(sum(item['probabilidade_modelo'] is not None for item in singapura), 22)
        self.assertTrue(all(item['resultado_observado'] is not None for item in singapura))
        self.assertEqual(asset['proveniencia']['emissao']['modo'], 'ENSAIO_RETROSPECTIVO')
        self.assertEqual(
            asset['proveniencia']['emissao']['hashes_saidas']['probabilidades.csv'],
            '54bcac2526c326820533f0b4d96e3b9bb354cdd24a77496d634cd70d04932e2e',
        )
        registro = asset['proveniencia']['emissoes']['2026:17:marina_bay']
        self.assertEqual(registro['modo'], 'ENSAIO_RETROSPECTIVO')
        self.assertEqual(registro['evento']['rodada'], 17)

    def test_campeonato_2026_usa_driverstandings_jolpica_paginado_e_max_em_p4(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset = preparar.gerar(RAIZ, Path(tmp) / 'race_weekend.json')
        campeonato = asset['dados_2026']['campeonato_pilotos']
        self.assertTrue(campeonato['disponivel'])
        self.assertEqual(campeonato['snapshot_id'], 'classificacao-pilotos-20261023T143930Z')
        self.assertEqual(campeonato['rodada_referencia'], 17)
        self.assertEqual(campeonato['paginas_validadas'], 1)
        self.assertIn('driverstandings.json', campeonato['url_base'])
        max_verstappen = next(item for item in campeonato['classificacao'] if item['piloto_id'] == 'max_verstappen')
        self.assertEqual(max_verstappen['posicao'], 4)
        self.assertEqual(max_verstappen['pontos'], 221.0)
        self.assertEqual(max_verstappen['vitorias'], 2)
        self.assertIsInstance(campeonato['classificacao'][0]['pontos'], float)

    def test_campeonato_incompleto_fica_indisponivel_sem_somar_resultados(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / 'data/operacao_2026/snapshots' / preparar.SNAPSHOT_CLASSIFICACAO_PILOTOS_2026
            base.mkdir(parents=True)
            (base / 'indice.json').write_text('{"paginacao": {"completa": false}}', encoding='utf-8')
            campeonato, _ = preparar._campeonato_pilotos_2026(Path(tmp))
        self.assertFalse(campeonato['disponivel'])
        self.assertEqual(campeonato['classificacao'], [])

    def test_figura_historica_usa_nomes_e_cores_contextuais_de_equipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset = preparar.gerar(RAIZ, Path(tmp) / 'race_weekend.json')
        casos = ((2024, 'norris', 'McLaren', '#F58020'), (2024, 'hamilton', 'Mercedes', '#00A19B'),
                 (2025, 'norris', 'McLaren', '#F58020'), (2025, 'hamilton', 'Ferrari', '#E53935'))
        for temporada, piloto_id, equipe, cor in casos:
            pacote = carregar_temporada(RAIZ, temporada)
            pacote['asset_race_weekend'] = asset
            participantes = dados_do_gp(pacote, 1)['participantes']
            piloto = next(item for item in participantes if item['piloto_id'] == piloto_id)
            self.assertEqual(app.nome_equipe(pacote, piloto), equipe)
            figura = app.grafico_probabilidades(pacote, participantes)
            indice = list(figura.data[0].y).index(app.nome_piloto(pacote, piloto))
            self.assertEqual(figura.data[0].marker.color[indice], cor)

    def test_nao_chama_rede_nem_carrega_modelo(self):
        fonte = (RAIZ / 'preparar_dashboard_race_weekend.py').read_text(encoding='utf-8').lower()
        for proibido in ('urlopen', 'requests', 'socket', 'joblib', 'sklearn', 'predict', 'fit('):
            self.assertNotIn(proibido, fonte)

    def test_apptest_troca_temporada_e_gp_sem_reter_chave_invalida(self):
        with patch.dict(os.environ, {'PITWALL_DASHBOARD_ROOT': str(RAIZ)}, clear=False):
            at = AppTest.from_file(RAIZ / 'app.py', default_timeout=15)
            at.run(timeout=15)
            temporada = next(item for item in at.get('selectbox') if item.key == 'temporada')
            temporada.set_value(2026)
            at.run(timeout=15)
            self.assertFalse(at.exception, [str(item.value) for item in at.exception])
            gp = next(item for item in at.get('selectbox') if item.key == 'gp')
            self.assertEqual(len(gp.options), 23)
            gp.set_value('2026:17')
            at.run(timeout=15)
            texto = '\n'.join(str(item.value) for item in at.get('markdown') + at.get('text') + at.get('caption') + at.get('title'))
            self.assertIn('Max Verstappen', texto)
            temporada = next(item for item in at.get('selectbox') if item.key == 'temporada')
            temporada.set_value(2024)
            at.run(timeout=15)
            gp = next(item for item in at.get('selectbox') if item.key == 'gp')
            self.assertEqual(gp.value, '2024:1')


if __name__ == '__main__':
    unittest.main()
