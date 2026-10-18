"""Contraprovas temporais: dados SIMULADOS, nunca publicados como resultados reais."""
import copy
import importlib
import importlib.util
from datetime import date, timedelta
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def modulo():
    assert importlib.util.find_spec('preparar_historico'), 'Falta implementar preparar_historico'
    return importlib.import_module('preparar_historico')


class TestReferencia(unittest.TestCase):
    def test_referencia_posterior_a_corrida_bloqueia_em_vez_de_vazar(self):
        corrida = {'season': '2024', 'date': '2024-11-03', 'time': '15:30:00Z',
                   'Qualifying': {'date': '2024-11-10', 'time': '10:30:00Z'}}
        with self.assertRaisesRegex(ValueError, 'referência.*corrida'):
            modulo().definir_referencia(corrida)

    def test_sprint_2021_2022_define_referencia_mas_nao_e_resultado_de_gp(self):
        corrida = {'season': '2021', 'date': '2021-07-18', 'time': '14:00:00Z',
                   'Qualifying': {'date': '2021-07-16', 'time': '17:00:00Z'},
                   'Sprint': {'date': '2021-07-17', 'time': '15:30:00Z'}}
        ref = modulo().definir_referencia(corrida)
        self.assertEqual(ref['sessao_referencia'], 'Sprint_2021_2022')
        self.assertEqual(ref['limite_inferior_referencia_utc'], '2021-07-17T15:30:00Z')
        self.assertTrue(ref['classificacao_nao_define_grid_gp'])
        corrida['season'] = '2023'
        self.assertEqual(modulo().definir_referencia(corrida)['sessao_referencia'], 'Qualifying')

    def test_referencia_preserva_fim_desconhecido_sem_inventar_duracao(self):
        corrida = {'season': '2024', 'round': '21', 'date': '2024-11-03',
                   'time': '15:30:00Z', 'Qualifying': {'date': '2024-11-03', 'time': '10:30:00Z'}}
        ref = modulo().definir_referencia(corrida)
        self.assertEqual(ref['sessao_referencia'], 'Qualifying')
        self.assertEqual(ref['limite_inferior_referencia_utc'], '2024-11-03T10:30:00Z')
        self.assertIsNone(ref['fim_sessao_referencia_utc'])
        self.assertFalse(ref['referencia_temporal_ausente'])


def eventos_simulados(quantidade=7):
    """Mini campeonato artificial com quatro pilotos: apenas teste, sem arquivos de dados."""
    calendario, resultados, classificacao = [], [], []
    for rodada in range(1, quantidade + 1):
        dia = date(2021, 1, 3) + timedelta(days=7 * (rodada - 1))
        corrida = {'season': '2021', 'round': str(rodada), 'raceName': 'Corrida simulada',
                   'date': dia.isoformat(), 'time': '14:00:00Z',
                   'Circuit': {'circuitId': 'teste', 'circuitName': 'Circuito de teste'},
                   'Qualifying': {'date': (dia - timedelta(days=1)).isoformat(), 'time': '14:00:00Z'}}
        calendario.append(corrida)
        r, q = copy.deepcopy(corrida), copy.deepcopy(corrida)
        r['Results'], q['QualifyingResults'] = [], []
        for pos, piloto in enumerate(['a', 'b', 'c', 'd'], 1):
            item = {'Driver': {'driverId': piloto, 'givenName': 'Piloto', 'familyName': piloto},
                    'Constructor': {'constructorId': 'x' if pos < 3 else 'y', 'name': 'Equipe de teste'},
                    'position': str(pos)}
            q['QualifyingResults'].append(copy.deepcopy(item))
            item.update({'grid': str(5 - pos), 'points': str(rodada * pos), 'status': 'Finished'})
            r['Results'].append(item)
        resultados.append(r)
        classificacao.append(q)
    return calendario, resultados, classificacao


class TestVariaveis(unittest.TestCase):
    def entradas_por_chave(self, saida):
        m = modulo()
        return {tuple(l[c] for c in m.CHAVES): {c: l[c] for c in m.ENTRADAS} for l in saida['linhas']}

    def test_alterar_resultado_atual_nao_altera_entradas_da_corrida(self):
        c, r, q = eventos_simulados()
        antes = modulo().preparar(c, r, q)
        atual = r[3]['Results']
        atual[0]['position'], atual[3]['position'] = atual[3]['position'], atual[0]['position']
        atual[0]['points'], atual[0]['status'], atual[0]['grid'] = '0', 'Disqualified', '0'
        depois = modulo().preparar(c, r, q)
        x, y = self.entradas_por_chave(antes), self.entradas_por_chave(depois)
        for k in x:
            if k[1] == '4':
                self.assertEqual(x[k], y[k])
        self.assertNotEqual([l['podio'] for l in antes['linhas'] if l['rodada'] == '4'],
                            [l['podio'] for l in depois['linhas'] if l['rodada'] == '4'])

    def test_alterar_futuro_nao_altera_entradas_anteriores(self):
        c, r, q = eventos_simulados()
        antes = self.entradas_por_chave(modulo().preparar(c, r, q))
        for corrida in r[4:]:
            corrida['Results'][0]['position'], corrida['Results'][3]['position'] = '4', '1'
            corrida['Results'][0]['points'] = '0'
        depois = self.entradas_por_chave(modulo().preparar(c, r, q))
        for k in antes:
            if int(k[1]) <= 4:
                self.assertEqual(antes[k], depois[k])

    def test_todos_pilotos_mesma_divisao_e_historico_cruza_anos(self):
        c, r, q = eventos_simulados(3)
        for ano, i in zip(['2023', '2024', '2025'], range(3)):
            for objetos in [c, r, q]:
                objetos[i]['season'] = ano
                objetos[i]['date'] = objetos[i]['date'].replace('2021', ano)
                objetos[i]['Qualifying']['date'] = objetos[i]['Qualifying']['date'].replace('2021', ano)
        saida = modulo().preparar(list(reversed(c)), list(reversed(r)), list(reversed(q)))
        for ano, esperado in [('2023', 'treino'), ('2024', 'validacao'), ('2025', 'teste_final_reservado')]:
            grupo = [l for l in saida['linhas'] if l['temporada'] == ano]
            self.assertEqual({l['divisao'] for l in grupo}, {esperado})
        self.assertEqual(next(l for l in saida['linhas'] if l['temporada'] == '2025')['n_posicoes_5'], 2)

    def test_ausentes_juncao_externa_sem_excluir_ou_usar_equipe_do_resultado(self):
        c, r, q = eventos_simulados(2)
        del q[1]['QualifyingResults'][0]  # a: só no resultado.
        del r[1]['Results'][3]  # d: só na classificação; preserva pódio 1,2,3.
        del q[1]['QualifyingResults'][0]['position']  # b: presente, sem posição.
        saida = modulo().preparar(c, r, q)
        atuais = {l['piloto_id']: l for l in saida['linhas'] if l['rodada'] == '2'}
        self.assertEqual(set(atuais), {'a', 'b', 'c', 'd'})
        self.assertIsNone(atuais['a']['posicao_classificacao'])
        self.assertEqual(atuais['a']['classificacao_ausente'], 1)
        self.assertIsNone(atuais['a']['media_pontos_equipe_5'])
        self.assertEqual(atuais['a']['n_participacoes_equipe_5'], 0)
        self.assertEqual(atuais['b']['classificacao_ausente'], 0)
        self.assertEqual(atuais['b']['posicao_classificacao_ausente'], 1)
        self.assertIsNone(atuais['d']['podio'])
        self.assertEqual(atuais['d']['resultado_ausente'], 1)
        self.assertEqual(saida['qualidade']['2021']['diferencas_participantes'][0]['so_classificacao'], ['d'])

    def test_sem_referencia_mantem_linhas_mas_nao_inventa_historico(self):
        c, r, q = eventos_simulados(2)
        del c[1]['Qualifying']
        grupo = [l for l in modulo().preparar(c, r, q)['linhas'] if l['rodada'] == '2']
        self.assertEqual(len(grupo), 4)
        for l in grupo:
            self.assertEqual(l['referencia_temporal_ausente'], True)
            self.assertEqual(l['n_posicoes_5'], 0)
            self.assertIsNone(l['media_posicao_final_5'])

    def test_janelas_excluem_mesmo_dia_e_sao_auditaveis(self):
        c, r, q = eventos_simulados(3)
        # Histórico anterior na ordem de início, mas no mesmo dia da sessão: bloqueado.
        c[2]['Qualifying'] = {'date': c[1]['date'], 'time': '23:00:00Z'}
        saida = modulo().preparar(c, r, q)
        atual = next(l for l in saida['linhas'] if l['rodada'] == '3' and l['piloto_id'] == 'a')
        self.assertEqual(atual['n_posicoes_5'], 1)
        for janela in saida['auditoria_janelas']:
            for item in janela['piloto'] + janela['equipe']:
                self.assertLessEqual(item['liberado_pelo_protocolo_utc'], janela['limite_inferior_referencia_utc'])
                self.assertNotEqual((item['temporada'], item['rodada']), (janela['temporada'], janela['rodada']))

    def test_janela_e_por_participacoes_dns_dsq_e_equipes_por_id(self):
        c, r, q = eventos_simulados()
        del r[3]['Results'][3]  # d perde uma participação (e não é pódio).
        r[0]['Results'][0]['status'] = 'Did not start'
        r[1]['Results'][0]['status'] = 'Disqualified'
        saida = modulo().preparar(c, r, q)
        ultimo = {l['piloto_id']: l for l in saida['linhas'] if l['rodada'] == '7'}
        janela_d = next(j for j in saida['auditoria_janelas'] if j['rodada'] == '7' and j['piloto_id'] == 'd')
        self.assertEqual([j['rodada'] for j in janela_d['piloto']], ['1', '2', '3', '5', '6'])
        self.assertEqual(ultimo['d']['n_participacoes_equipe_5'], 9)
        terceiro_a = next(l for l in saida['linhas'] if l['rodada'] == '3' and l['piloto_id'] == 'a')
        self.assertEqual(terceiro_a['n_posicoes_5'], 2)  # Não exclui DNS/DSQ.
        # Mudança de ID de equipe não herda a história pelo nome igual.
        for fonte, campo in [(r, 'Results'), (q, 'QualifyingResults')]:
            for item in fonte[-1][campo][:2]:
                item['Constructor']['constructorId'] = 'x_nova'
        novo = next(l for l in modulo().preparar(c, r, q)['linhas'] if l['rodada'] == '7' and l['piloto_id'] == 'a')
        self.assertEqual(novo['n_corridas_equipe_5'], 0)
        self.assertEqual(novo['n_posicoes_5'], 5)

    def test_duplicacoes_e_juncoes_incoerentes_falham(self):
        for caso in ['calendario', 'piloto', 'equipe', 'circuito', 'rodada']:
            c, r, q = eventos_simulados(1)
            if caso == 'calendario': c.append(copy.deepcopy(c[0]))
            elif caso == 'piloto': q[0]['QualifyingResults'].append(copy.deepcopy(q[0]['QualifyingResults'][0]))
            elif caso == 'equipe': q[0]['QualifyingResults'][0]['Constructor']['constructorId'] = 'outra'
            elif caso == 'circuito': q[0]['Circuit']['circuitId'] = 'outro'
            else: q[0]['round'] = '99'
            with self.subTest(caso=caso), self.assertRaises(ValueError):
                modulo().preparar(c, r, q)

    def test_juncao_preserva_e_sinaliza_posicoes_classificacao_repetidas(self):
        c, r, q = eventos_simulados(1)
        q[0]['QualifyingResults'][1]['position'] = '1'
        saida = modulo().preparar(c, r, q)
        atuais = {linha['piloto_id']: linha for linha in saida['linhas']}
        self.assertEqual(len(atuais), 4)
        self.assertEqual(atuais['a']['posicao_classificacao'], 1)
        self.assertEqual(atuais['b']['posicao_classificacao'], 1)
        self.assertEqual(atuais['a']['posicao_classificacao_repetida'], 1)
        self.assertEqual(atuais['b']['posicao_classificacao_repetida'], 1)
        self.assertEqual(atuais['c']['posicao_classificacao_repetida'], 0)
        self.assertEqual(saida['qualidade']['2021']['posicoes_classificacao_repetidas'], [
            {'rodada': '1', 'posicao': 1, 'pilotos': ['a', 'b']},
        ])

    def test_juncao_recusa_posicao_classificacao_nao_positiva(self):
        c, r, q = eventos_simulados(1)
        q[0]['QualifyingResults'][1]['position'] = '0'
        with self.assertRaisesRegex(ValueError, 'Posição da classificação inválida'):
            modulo().preparar(c, r, q)

    def test_prepara_janela_cinco_exclui_corrida_atual_e_separa_funcoes(self):
        c, r, q = eventos_simulados()
        self.assertTrue(hasattr(modulo(), 'preparar'), 'Falta transformação histórica')
        saida = modulo().preparar(c, r, q)
        linha = next(x for x in saida['linhas'] if x['rodada'] == '7' and x['piloto_id'] == 'a')
        self.assertEqual(len(saida['linhas']), 28)
        self.assertEqual(linha['posicao_classificacao'], 1)  # Não é grid=4.
        self.assertEqual(linha['media_posicao_final_5'], 1)
        self.assertEqual(linha['taxa_podios_5'], 1)
        self.assertEqual(linha['n_posicoes_5'], 5)
        self.assertEqual(linha['n_podios_5'], 5)
        self.assertEqual(linha['n_corridas_equipe_5'], 5)
        self.assertEqual(linha['n_participacoes_equipe_5'], 10)
        self.assertEqual(linha['media_pontos_equipe_5'], sum(3 * i for i in range(2, 7)) / 10)
        primeiro = next(x for x in saida['linhas'] if x['rodada'] == '1')
        self.assertIsNone(primeiro['media_posicao_final_5'])
        self.assertIsNone(primeiro['media_pontos_equipe_5'])
        self.assertEqual(primeiro['n_posicoes_5'], 0)
        self.assertEqual(linha['divisao'], 'treino')
        self.assertFalse({'posicao_final', 'pontos', 'status', 'podio'} & set(modulo().ENTRADAS))
        self.assertEqual(set(modulo().ALVOS), {'podio'})


class TestArquivos(unittest.TestCase):
    def test_falha_na_ultima_temporada_nao_publica_base_parcial(self):
        def carregar(temporada, raiz_dados):
            if str(temporada) == '2025':
                raise ValueError('Cache incompleto simulado')
            return {'calendario': [], 'resultados': [], 'classificacao': []}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {'coletar_historico': SimpleNamespace(carregar_temporada=carregar)}):
            with self.assertRaisesRegex(ValueError, 'incompleto'):
                modulo().executar(Path(tmp) / 'fontes', Path(tmp) / 'dados', Path(tmp) / 'relatorios')
            self.assertFalse((Path(tmp) / 'dados').exists())
            self.assertFalse((Path(tmp) / 'relatorios').exists())

    def test_execucao_carrega_cinco_temporadas_antes_de_gravar_sem_rede(self):
        chamadas = []
        def carregar(temporada, raiz_dados):
            chamadas.append(str(temporada))
            c, r, q = eventos_simulados(1)
            for fonte in [c, r, q]:
                for corrida in fonte:
                    corrida['season'] = str(temporada)
                    corrida['date'] = corrida['date'].replace('2021', str(temporada))
                    corrida['Qualifying']['date'] = corrida['Qualifying']['date'].replace('2021', str(temporada))
            return {'calendario': c, 'resultados': r, 'classificacao': q}
        m = modulo()
        self.assertTrue(hasattr(m, 'executar'), 'Falta executar preparação com dados locais')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {'coletar_historico': SimpleNamespace(carregar_temporada=carregar)}):
            saida = m.executar(Path(tmp) / 'fontes', Path(tmp) / 'dados', Path(tmp) / 'relatorios')
            self.assertEqual(chamadas, ['2021', '2022', '2023', '2024', '2025'])
            self.assertEqual(len(saida['linhas']), 20)
            self.assertTrue((Path(tmp) / 'dados/teste_final_reservado.csv').exists())

    def test_relatorios_markdown_tem_tabelas_contiguas_e_2025_so_qualidade(self):
        c, r, q = eventos_simulados(1)
        for fonte in [c, r, q]:
            fonte[0]['season'] = '2025'
            fonte[0]['date'] = fonte[0]['date'].replace('2021', '2025')
            fonte[0]['Qualifying']['date'] = fonte[0]['Qualifying']['date'].replace('2021', '2025')
        with tempfile.TemporaryDirectory() as tmp:
            modulo().gravar_preparacao(modulo().preparar(c, r, q), Path(tmp) / 'dados', Path(tmp) / 'relatorios')
            texto = (Path(tmp) / 'relatorios/qualidade_2025.md').read_text()
            self.assertNotIn('|\n\n|', texto)
            self.assertIn('teste final reservado', texto)
            self.assertIn('não mede desempenho', texto)
            self.assertNotIn('acurácia:', texto)
            self.assertNotIn('taxa de acertos:', texto)

    def test_relatorio_lista_posicoes_classificacao_repetidas_sem_inferir_ordem(self):
        c, r, q = eventos_simulados(1)
        q[0]['QualifyingResults'][1]['position'] = '1'
        with tempfile.TemporaryDirectory() as tmp:
            modulo().gravar_preparacao(modulo().preparar(c, r, q), Path(tmp) / 'dados', Path(tmp) / 'relatorios')
            texto = (Path(tmp) / 'relatorios/qualidade_2021.md').read_text()
        self.assertIn('Posições de classificação repetidas/ambíguas', texto)
        self.assertIn('posição 1: a, b', texto)
        self.assertIn('Não inferimos posição única nem substituímos pelo grid', texto)

    def test_gera_artefatos_separados_reproduziveis_e_preserva_diferentes(self):
        c, r, q = eventos_simulados(2)
        m = modulo()
        self.assertTrue(hasattr(m, 'gravar_preparacao'), 'Falta gravar os artefatos preparados')
        info = m.preparar(c, r, q)
        with tempfile.TemporaryDirectory() as tmp:
            dados, relatorios = Path(tmp) / 'dados', Path(tmp) / 'relatorios'
            m.gravar_preparacao(info, dados, relatorios)
            self.assertEqual((dados / 'entradas.csv').read_text().splitlines()[0].split(','), m.CHAVES + m.ENTRADAS)
            self.assertEqual((dados / 'alvos.csv').read_text().splitlines()[0].split(','), m.CHAVES + m.ALVOS)
            self.assertTrue(json.loads((dados / 'verificacao.json').read_text())['completa'])
            antes = {str(p.relative_to(tmp)): p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()}
            m.gravar_preparacao(info, dados, relatorios)
            self.assertEqual(antes, {str(p.relative_to(tmp)): p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()})
            (dados / 'entradas.csv').write_text('preservar arquivo diferente')
            alterados = {str(p.relative_to(tmp)): p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()}
            with self.assertRaises(FileExistsError):
                m.gravar_preparacao(info, dados, relatorios)
            self.assertEqual(alterados, {str(p.relative_to(tmp)): p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
