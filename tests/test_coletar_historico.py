"""Integridade histórica; fixtures sintéticas identificadas, nunca dados reais."""
import copy
import hashlib
import importlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))



def pagina(endpoint='classificacao', offset=0, limite=2, total=3):
    """Resposta artificial mínima para exercitar paginação, não resultado esportivo."""
    chave = {'classificacao': 'QualifyingResults', 'resultados': 'Results'}.get(endpoint)
    corrida = {'season': '2023', 'round': '1', 'raceName': 'Teste simulado',
               'date': '2023-01-01', 'Circuit': {'circuitId': 'teste', 'circuitName': 'Teste'}}
    if chave:
        corrida[chave] = []
        for n in range(offset, min(offset + limite, total)):
            r = {'Driver': {'driverId': 'teste' + str(n), 'givenName': 'Teste', 'familyName': str(n)},
                 'Constructor': {'constructorId': 'teste', 'name': 'Teste'}, 'position': str(n+1),
                 'number': str(n+1)}
            if endpoint == 'resultados':
                r.update(grid=str(n+1), points='0', status='Finished')
            corrida[chave].append(r)
    return {'MRData': {'total': str(total), 'limit': str(limite), 'offset': str(offset),
                       'RaceTable': {'season': '2023', 'Races': [corrida]}}}


class TestHistorico(unittest.TestCase):
    def modulo(self):
        self.assertIsNotNone(importlib.util.find_spec('coletar_historico'), 'Falta coletor histórico')
        return importlib.import_module('coletar_historico')

    def test_pagina_classificacao_preserva_posicao_e_tempos_opcionais(self):
        m = self.modulo()
        p = pagina()
        r = p['MRData']['RaceTable']['Races'][0]['QualifyingResults'][0]
        del r['position']
        r['Q1'] = '1:20.123'
        antes = copy.deepcopy(p)
        self.assertEqual(m.validar_pagina(p, 'classificacao', '2023', 0), (3, 2))
        self.assertEqual(p, antes)
        for campo in ('Q1', 'Q2', 'Q3'):
            ruim = copy.deepcopy(p)
            ruim['MRData']['RaceTable']['Races'][0]['QualifyingResults'][0][campo] = 123
            with self.assertRaises(ValueError):
                m.validar_pagina(ruim, 'classificacao', '2023', 0)

    def test_uniao_detecta_duplicatas_e_reporta_classificacao_ausente(self):
        m = self.modulo()
        cal = pagina('calendario', limite=1, total=1)['MRData']['RaceTable']['Races']
        frag = [pagina('resultados', offset=n)['MRData']['RaceTable']['Races'][0] for n in (0, 2)]
        base = m.montar_temporada(cal, frag, [], {'calendario': 1, 'resultados': 3, 'classificacao': 0})
        self.assertEqual(len(base['resultados'][0]['Results']), 3)
        self.assertEqual(base['qualidade']['rodadas_sem_classificacao'], ['1'])
        self.assertTrue(base['qualidade']['completa'])
        for erro in ('piloto', 'posicao', 'metadados', 'corrida_ausente'):
            ruim = copy.deepcopy(frag)
            if erro == 'piloto': ruim[1]['Results'][0]['Driver']['driverId'] = 'teste0'
            elif erro == 'posicao': ruim[1]['Results'][0]['position'] = '1'
            elif erro == 'metadados': ruim[1]['raceName'] = 'Diferente'
            else: ruim = []
            with self.subTest(erro=erro), self.assertRaises(ValueError):
                m.montar_temporada(cal, ruim, [], {'calendario': 1, 'resultados': 3, 'classificacao': 0})
        q = pagina()['MRData']['RaceTable']['Races']
        del q[0]['QualifyingResults'][0]['position']
        q[0]['QualifyingResults'].append(copy.deepcopy(q[0]['QualifyingResults'][0]))
        with self.assertRaises(ValueError):
            m.montar_temporada(cal, frag, q, {'calendario': 1, 'resultados': 3, 'classificacao': 3})

    def test_pagina_rede_salva_bytes_originais_proveniencia_e_intervalo(self):
        m = self.modulo()
        original = (json.dumps(pagina(), indent=2) + '\r\n').encode()
        with tempfile.TemporaryDirectory() as t, patch.object(m, 'ULTIMA_REQUISICAO', 100), patch.object(m.time, 'monotonic', side_effect=[102, 108]), patch.object(m.time, 'sleep') as espera, patch.object(m, 'urlopen', return_value=io.BytesIO(original)) as abrir:
            dados, prov = m.obter_pagina('classificacao', '2023', 0, Path(t))
            self.assertEqual((Path(t) / prov['arquivo']).read_bytes(), original)
            self.assertEqual(prov['sha256'], hashlib.sha256(original).hexdigest())
            self.assertTrue(prov['obtido_em_utc'].endswith('Z'))
            self.assertIn('qualifying/?limit=100&offset=0', prov['url_consultada'])
            self.assertIn('PitwallLab/0.3.0 Python/', abrir.call_args.args[0].get_header('User-agent'))
            espera.assert_called_once_with(6.0)
            self.assertEqual(abrir.call_args.kwargs['timeout'], 30)
            with patch.object(m, 'urlopen', side_effect=AssertionError('Rede proibida')):
                self.assertEqual(m.obter_pagina('classificacao', '2023', 0, Path(t)), (dados, prov))

    def test_coleta_completa_offline_prova_hash_lista_arquivos_e_idempotencia(self):
        m = self.modulo()
        respostas = [pagina('calendario', limite=100, total=1)] + [pagina(e, offset=n) for e in ('resultados', 'classificacao') for n in (0, 2)]
        with tempfile.TemporaryDirectory() as t, patch.object(m.time, 'sleep'), patch.object(m, 'urlopen', side_effect=[io.BytesIO(json.dumps(p).encode()) for p in respostas]) as abrir:
            raiz = Path(t)
            base = m.coletar_temporada('2023', raiz)
            self.assertEqual(abrir.call_count, 5)
            self.assertEqual(len(base['resultados'][0]['Results']), 3)
            self.assertEqual(len(base['proveniencia']), 5)
            antes = {str(p.relative_to(raiz)): p.read_bytes() for p in raiz.rglob('*') if p.is_file()}
            with patch.object(m, 'urlopen', side_effect=AssertionError('Rede proibida')):
                self.assertEqual(m.carregar_temporada(2023, raiz), base)
                self.assertEqual(m.coletar_temporada(2023, raiz, somente_cache=True), base)
            self.assertEqual(antes, {str(p.relative_to(raiz)): p.read_bytes() for p in raiz.rglob('*') if p.is_file()})
            meta = raiz / '2023/proveniencia/resultados_offset_0000.json'
            meta_original = meta.read_bytes()
            meta.write_bytes(meta_original + b' ')
            with self.assertRaises(ValueError):
                m.carregar_temporada('2023', raiz)
            meta.write_bytes(meta_original)
            alvo = raiz / '2023/raw/resultados_offset_0000.json'
            original = alvo.read_bytes()
            for corrupcao in ('alterado', 'removido', 'extra'):
                if corrupcao == 'alterado': alvo.write_bytes(original + b' ')
                elif corrupcao == 'removido': alvo.unlink()
                else: (alvo.parent / 'extra.json').write_bytes(b'{}')
                with self.subTest(corrupcao=corrupcao), self.assertRaises(ValueError):
                    m.carregar_temporada('2023', raiz)
                alvo.write_bytes(original)

    def test_duplicata_na_pagina_falha_antes_de_gravar(self):
        m = self.modulo()
        p = pagina('resultados')
        p['MRData']['RaceTable']['Races'][0]['Results'][1]['position'] = '1'
        with tempfile.TemporaryDirectory() as t, patch.object(m, 'ULTIMA_REQUISICAO', None), patch.object(m, 'urlopen', return_value=io.BytesIO(json.dumps(p).encode())):
            with self.assertRaisesRegex(ValueError, 'duplicada.*2023/1.*1.*teste0.*teste1'):
                m.obter_pagina('resultados', '2023', 0, Path(t))
            self.assertEqual(list(Path(t).rglob('*')), [])

    def test_cli_temporadas_cache_e_pasta(self):
        m = self.modulo()
        resumo = {'qualidade': {'corridas_esperadas': 1, 'registros_resultados': 3,
                              'registros_classificacao': 3, 'rodadas_sem_classificacao': []}}
        with patch.object(m, 'coletar_temporada', return_value=resumo) as coleta:
            self.assertEqual(m.main(['--temporadas', '2021', '2025', '--somente-cache', '--pasta-dados', '/dados/teste']), 0)
            self.assertEqual([c.args for c in coleta.call_args_list], [('2021', Path('/dados/teste')), ('2025', Path('/dados/teste'))])
            self.assertTrue(all(c.kwargs == {'somente_cache': True} for c in coleta.call_args_list))

    def test_proveniencia_incompleta_e_recusada_sem_rede(self):
        m = self.modulo()
        with tempfile.TemporaryDirectory() as t, patch.object(m, 'ULTIMA_REQUISICAO', None), patch.object(m, 'urlopen', return_value=io.BytesIO(json.dumps(pagina()).encode())):
            _, prov = m.obter_pagina('classificacao', '2023', 0, Path(t))
            metapath = Path(t) / 'proveniencia' / Path(prov['arquivo']).name
            del prov['obtido_em_utc']
            metapath.write_text(json.dumps(prov))
            with patch.object(m, 'urlopen', side_effect=AssertionError('Rede proibida')):
                with self.assertRaisesRegex(ValueError, 'proveniência|Proveniência'):
                    m.obter_pagina('classificacao', '2023', 0, Path(t))

    def test_classificacao_tempo_vazio_e_preservado_como_na_fonte(self):
        m = self.modulo()
        p = pagina()
        p['MRData']['RaceTable']['Races'][0]['QualifyingResults'][0]['Q1'] = ''
        self.assertEqual(m.validar_pagina(p, 'classificacao', '2023', 0), (3, 2))
        self.assertEqual(p['MRData']['RaceTable']['Races'][0]['QualifyingResults'][0]['Q1'], '')

    def test_falhas_de_transporte_simuladas_sem_retry_nem_arquivos(self):
        m = self.modulo()
        erros = [HTTPError(m.BASE_API, 429, 'simulado', {'Retry-After': '60'}, None),
                 HTTPError(m.BASE_API, 503, 'simulado', {}, None), URLError('timeout simulado')]
        for erro in erros:
            with self.subTest(erro=str(erro)), tempfile.TemporaryDirectory() as t, patch.object(m, 'ULTIMA_REQUISICAO', None), patch.object(m, 'urlopen', side_effect=erro) as abrir:
                with self.assertRaises((ValueError, OSError)) as capturada:
                    m.obter_pagina('classificacao', '2023', 0, Path(t))
                abrir.assert_called_once()
                if isinstance(erro, HTTPError) and erro.code == 429:
                    self.assertIn('Retry-After: 60', str(capturada.exception))
                self.assertEqual(list(Path(t).rglob('*')), [])

    def test_resposta_e_cache_invalidos_preservados_sem_outputs(self):
        m = self.modulo()
        casos = [b'[]', b'{', b'\xff']
        for alteracao in ('total', 'offset', 'temporada', 'limit'):
            p = pagina()
            if alteracao == 'total': p['MRData']['total'] = '5'
            elif alteracao == 'offset': p['MRData']['offset'] = '1'
            elif alteracao == 'temporada': p['MRData']['RaceTable']['season'] = '2022'
            else: p['MRData']['limit'] = '101'
            casos.append(json.dumps(p).encode())
        # total=5 sozinho não altera o tamanho válido da primeira página; para esse
        # caso verificamos também o total conhecido da página anterior (3).
        for conteudo in casos:
            for cache in (False, True):
                with self.subTest(conteudo=conteudo[:40], cache=cache), tempfile.TemporaryDirectory() as t:
                    pasta = Path(t)
                    alvo = pasta / 'raw/classificacao_offset_0000.json'
                    if cache:
                        alvo.parent.mkdir()
                        alvo.write_bytes(conteudo)
                    with patch.object(m, 'ULTIMA_REQUISICAO', None), patch.object(m, 'urlopen', side_effect=AssertionError('Rede proibida') if cache else [io.BytesIO(conteudo)]) as abrir:
                        with self.assertRaises(ValueError):
                            m.obter_pagina('classificacao', '2023', 0, pasta, total_esperado=3)
                        if cache:
                            abrir.assert_not_called()
                            self.assertEqual(alvo.read_bytes(), conteudo)
                        else:
                            self.assertFalse(alvo.exists())
                        self.assertFalse((pasta / 'proveniencia').exists())

    def test_falha_intermediaria_simulada_nao_cria_comprovante(self):
        m = self.modulo()
        respostas = [io.BytesIO(json.dumps(pagina('calendario', limite=100, total=1)).encode()),
                     io.BytesIO(json.dumps(pagina('resultados')).encode()), URLError('falha intermediária simulada')]
        with tempfile.TemporaryDirectory() as t, patch.object(m, 'ULTIMA_REQUISICAO', None), patch.object(m.time, 'sleep'), patch.object(m, 'urlopen', side_effect=respostas):
            with self.assertRaises(OSError):
                m.coletar_temporada('2023', Path(t))
            self.assertTrue((Path(t) / '2023/raw/resultados_offset_0000.json').exists())
            self.assertFalse((Path(t) / '2023/manifesto.json').exists())
            self.assertFalse((Path(t) / '2023/verificacao.json').exists())

    def test_reutiliza_legado_2024_byte_a_byte_com_data_desconhecida(self):
        m = self.modulo()
        caminhos = sorted((RAIZ / 'data/temporada_2024/raw').glob('*.json'))
        self.assertTrue(caminhos)
        with tempfile.TemporaryDirectory() as t, patch.object(m, 'urlopen', side_effect=AssertionError('Rede proibida')):
            for origem in caminhos:
                endpoint, offset = origem.stem.split('_offset_')
                _, prov = m.obter_pagina(endpoint, '2024', int(offset), Path(t), somente_cache=True)
                self.assertEqual((Path(t) / prov['arquivo']).read_bytes(), origem.read_bytes())
                self.assertEqual(prov['obtido_em_utc'], 'desconhecida')
                self.assertTrue(prov['url_reconstruida'])
                self.assertEqual(prov['origem_arquivo_legado'], str(origem.relative_to(RAIZ)))

    def test_cache_sem_metadados_nao_fabrica_data_por_mtime(self):
        m = self.modulo()
        with tempfile.TemporaryDirectory() as t, patch.object(m, 'urlopen', side_effect=AssertionError('Rede proibida')):
            alvo = Path(t) / 'raw/classificacao_offset_0000.json'
            alvo.parent.mkdir()
            alvo.write_bytes(json.dumps(pagina()).encode())
            _, prov = m.obter_pagina('classificacao', '2023', 0, Path(t), somente_cache=True)
            self.assertEqual(prov['obtido_em_utc'], 'desconhecida')
            self.assertEqual(prov['sha256'], hashlib.sha256(alvo.read_bytes()).hexdigest())

    def test_preflight_lote_preserva_todos_destinos(self):
        m = self.modulo()
        with tempfile.TemporaryDirectory() as t:
            novo, existente = Path(t) / 'novo.json', Path(t) / 'existente.json'
            existente.write_bytes(b'antigo')
            with self.assertRaises(FileExistsError):
                m.salvar_lote([(novo, b'novo'), (existente, b'diferente')])
            self.assertFalse(novo.exists())
            self.assertEqual(existente.read_bytes(), b'antigo')

    def test_qualifying_total_zero_reportado_sem_esconder_corrida(self):
        m = self.modulo()
        vazio = pagina(total=0)
        vazio['MRData']['RaceTable']['Races'] = []
        respostas = [pagina('calendario', limite=100, total=1), pagina('resultados', limite=100), vazio]
        with tempfile.TemporaryDirectory() as t, patch.object(m, 'ULTIMA_REQUISICAO', None), patch.object(m.time, 'sleep'), patch.object(m, 'urlopen', side_effect=[io.BytesIO(json.dumps(p).encode()) for p in respostas]):
            base = m.coletar_temporada('2023', Path(t))
            self.assertEqual(base['qualidade']['rodadas_sem_classificacao'], ['1'])
            self.assertEqual(len(base['resultados']), 1)
            self.assertEqual(base['classificacao'], [])

    def test_horarios_opcionais_vazios_sao_preservados(self):
        m = self.modulo()
        p = pagina('calendario', total=1)
        corrida = p['MRData']['RaceTable']['Races'][0]
        corrida['time'] = ''
        corrida['Qualifying'] = {'date': '', 'time': ''}
        antes = copy.deepcopy(p)
        self.assertEqual(m.validar_pagina(p, 'calendario', '2023', 0), (1, 1))
        self.assertEqual(p, antes)

    def test_sessoes_opcionais_validam_tipos_sem_mutar(self):
        m = self.modulo()
        p = pagina('calendario', total=1)
        corrida = p['MRData']['RaceTable']['Races'][0]
        corrida['Qualifying'] = {'date': '2023-01-01'}
        antes = copy.deepcopy(p)
        m.validar_pagina(p, 'calendario', '2023', 0)
        self.assertEqual(p, antes)
        for valor in ([], {'date': 123}, {'time': None}):
            corrida['Qualifying'] = valor
            with self.assertRaises(ValueError):
                m.validar_pagina(p, 'calendario', '2023', 0)

    def test_cli_avisa_posicoes_classificacao_repetidas_sem_remover_dados(self):
        m = self.modulo()
        resumo = {'qualidade': {'corridas_esperadas': 1, 'registros_resultados': 3,
                              'registros_classificacao': 3, 'rodadas_sem_classificacao': [],
                              'posicoes_classificacao_repetidas': [{'temporada': '2023', 'rodada': '1',
                                                                  'posicao': '1', 'pilotos': ['a', 'b']}]}}
        with patch.object(m, 'coletar_temporada', return_value=resumo), patch('sys.stdout', new_callable=io.StringIO) as saida:
            self.assertEqual(m.main(['--temporadas', '2023', '--somente-cache']), 0)
            self.assertIn('AVISO', saida.getvalue())
            self.assertIn('posições de classificação repetidas preservadas', saida.getvalue())

    def test_posicoes_classificacao_repetidas_preservadas_e_sinalizadas(self):
        m = self.modulo()
        q = pagina(limite=100)
        qualificacao = q['MRData']['RaceTable']['Races']
        qualificacao[0]['QualifyingResults'][1]['position'] = '1'
        original = copy.deepcopy(q)
        self.assertEqual(m.validar_pagina(q, 'classificacao', '2023', 0), (3, 3))
        calendario = pagina('calendario', limite=100, total=1)['MRData']['RaceTable']['Races']
        resultados = pagina('resultados', limite=100)['MRData']['RaceTable']['Races']
        base = m.montar_temporada(calendario, resultados, qualificacao,
                                 {'calendario': 1, 'resultados': 3, 'classificacao': 3})
        self.assertEqual(q, original)
        self.assertEqual(base['classificacao'], qualificacao)
        self.assertEqual(base['qualidade']['posicoes_classificacao_repetidas'],
                         [{'temporada': '2023', 'rodada': '1', 'posicao': '1', 'pilotos': ['teste0', 'teste1']}])
        self.assertTrue(base['qualidade']['completa'])


if __name__ == '__main__':
    unittest.main()
