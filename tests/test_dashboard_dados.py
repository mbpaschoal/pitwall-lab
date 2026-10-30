"""TDD da etapa 6: fixtures temporárias derivadas apenas de reports/.

Estes testes não abrem data/ nem modelos. Eles copiam os artefatos de apresentação
verificados para um diretório temporário e alteram somente as cópias inválidas.
"""
import csv
import importlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def modulo():
    assert importlib.util.find_spec('dashboard_dados'), 'Falta implementar dashboard_dados.py'
    return importlib.import_module('dashboard_dados')


def copiar_artefatos(raiz):
    for origem_relativa in ('reports/modelo_v1', 'reports/avaliacao_final_v1'):
        origem = RAIZ / origem_relativa
        destino = raiz / origem_relativa
        destino.mkdir(parents=True, exist_ok=True)
        for nome in ('previsoes_validacao.csv', 'avaliacao_corridas.csv', 'metricas.json', 'calibracao.csv'):
            arquivo = origem / nome
            if arquivo.exists():
                shutil.copy2(arquivo, destino / nome)
        for nome in ('previsoes_pre_corrida.csv', 'avaliacao_por_piloto.csv'):
            arquivo = origem / nome
            if arquivo.exists():
                shutil.copy2(arquivo, destino / nome)
    return raiz


def ler_csv(caminho):
    with caminho.open(encoding='utf-8', newline='') as arquivo:
        return list(csv.DictReader(arquivo))


def escrever_csv(caminho, linhas, campos=None):
    campos = campos or list(linhas[0])
    with caminho.open('w', encoding='utf-8', newline='') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos, lineterminator='\n')
        escritor.writeheader()
        escritor.writerows(linhas)


class TestCarregamentoEDadosDoGp(unittest.TestCase):
    def test_carrega_2025_e_filtra_espanha_e_sao_paulo_sem_usar_alvos_para_favoritos(self):
        dados = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            pacote = dados.carregar_temporada(Path(copiar_artefatos(Path(tmp))), 2025)
        self.assertEqual(pacote['temporada'], 2025)
        self.assertEqual(len(pacote['corridas']), 24)
        espanha = dados.dados_do_gp(pacote, 9)
        sao_paulo = dados.dados_do_gp(pacote, 21)
        self.assertFalse(espanha['corrida']['avaliavel_ranking'])
        self.assertEqual(espanha['corrida']['motivos_nao_avaliavel'], 'alvo_desconhecido')
        self.assertEqual(next(l for l in espanha['participantes'] if l['piloto_id'] == 'stroll')['podio'], None)
        self.assertFalse(sao_paulo['corrida']['avaliavel_ranking'])
        self.assertEqual(sao_paulo['corrida']['motivos_nao_avaliavel'], 'participante_inelegivel')
        bortoleto = next(l for l in sao_paulo['participantes'] if l['piloto_id'] == 'bortoleto')
        self.assertFalse(bortoleto['elegivel_previsao'])
        self.assertIsNone(bortoleto['probabilidade_modelo'])
        favoritos_antes = [l['piloto_id'] for l in espanha['favoritos_modelo']]
        for linha in pacote['previsoes']:
            if linha['rodada'] == 9:
                linha['podio'] = 1 - linha['podio'] if linha['podio'] is not None else None
        self.assertEqual(favoritos_antes, [l['piloto_id'] for l in dados.dados_do_gp(pacote, 9)['favoritos_modelo']])

    def test_opcoes_de_gp_sao_ordenadas_por_rodada_e_temporadas_sao_ints(self):
        dados = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(copiar_artefatos(Path(tmp)))
            vinte_quatro = dados.carregar_temporada(raiz, 2024)
            vinte_cinco = dados.carregar_temporada(raiz, 2025)
        self.assertEqual(dados.temporadas_disponiveis(), [2024, 2025])
        self.assertEqual([item['rodada'] for item in dados.opcoes_gps(vinte_quatro)], list(range(1, 25)))
        self.assertEqual([item['rodada'] for item in dados.opcoes_gps(vinte_cinco)], list(range(1, 25)))


class TestValidacao(unittest.TestCase):
    def test_arquivo_ausente_informa_nome_e_restauracao(self):
        dados = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(copiar_artefatos(Path(tmp)))
            (raiz / 'reports/modelo_v1/metricas.json').unlink()
            with self.assertRaisesRegex(dados.DashboardDadosErro, 'metricas.json.*restaur'):
                dados.carregar_temporada(raiz, 2024)

    def test_csv_com_cabecalho_duplicado_e_recusado(self):
        dados = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(copiar_artefatos(Path(tmp)))
            caminho = raiz / 'reports/modelo_v1/previsoes_validacao.csv'
            conteudo = caminho.read_text(encoding='utf-8')
            primeira_linha, restante = conteudo.split('\n', 1)
            campos = primeira_linha.split(',')
            campos[2] = campos[1]
            caminho.write_text(','.join(campos) + '\n' + restante, encoding='utf-8')
            with self.assertRaisesRegex(dados.DashboardDadosErro, 'duplicad'):
                dados.carregar_temporada(raiz, 2024)

    def test_chave_duplicada_probabilidade_infinita_e_fora_da_faixa_sao_recusadas(self):
        dados = modulo()
        casos = [('duplicada', None), ('infinita', 'inf'), ('fora', '1.1')]
        for nome, probabilidade in casos:
            with self.subTest(nome=nome), tempfile.TemporaryDirectory() as tmp:
                raiz = Path(copiar_artefatos(Path(tmp)))
                caminho = raiz / 'reports/avaliacao_final_v1/previsoes_pre_corrida.csv'
                linhas = ler_csv(caminho)
                if nome == 'duplicada':
                    linhas[1]['piloto_id'] = linhas[0]['piloto_id']
                else:
                    linhas[0]['probabilidade_modelo'] = probabilidade
                escrever_csv(caminho, linhas)
                with self.assertRaisesRegex(dados.DashboardDadosErro, 'chave|finit|intervalo'):
                    dados.carregar_temporada(raiz, 2025)

    def test_cobertura_json_incoerente_e_recusada(self):
        dados = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(copiar_artefatos(Path(tmp)))
            caminho = raiz / 'reports/avaliacao_final_v1/metricas.json'
            metricas = json.loads(caminho.read_text(encoding='utf-8'))
            metricas['cobertura']['gps_total'] = 99
            caminho.write_text(json.dumps(metricas), encoding='utf-8')
            with self.assertRaisesRegex(dados.DashboardDadosErro, 'metricas.json.*cobertura'):
                dados.carregar_temporada(raiz, 2025)

    def test_metricas_de_ranking_rejeitam_media_ou_distribuicao_que_nao_batem_com_acertos_publicados(self):
        dados = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(copiar_artefatos(Path(tmp)))
            conteudos = dict(dados.conteudos_temporada(raiz, 2025))
            nome = 'reports/avaliacao_final_v1/metricas.json'
            metricas = json.loads(conteudos[nome].decode('utf-8'))
            metricas['ranking_modelo']['media_integrantes_corretos'] = 0.0
            conteudos[nome] = json.dumps(metricas).encode('utf-8')
            with self.assertRaisesRegex(dados.DashboardDadosErro, 'metricas.json.*média.*acertos'):
                dados.carregar_temporada_de_conteudos(2025, tuple(conteudos.items()))

            metricas['ranking_modelo']['media_integrantes_corretos'] = 2.3181818181818183
            metricas['ranking_modelo']['distribuicao_0_1_2_3'] = {'0': 1, '1': 0, '2': 13, '3': 8}
            conteudos[nome] = json.dumps(metricas).encode('utf-8')
            with self.assertRaisesRegex(dados.DashboardDadosErro, 'metricas.json.*distribuição.*acertos'):
                dados.carregar_temporada_de_conteudos(2025, tuple(conteudos.items()))

    def test_ranks_favoritos_e_gp_nao_avaliavel_exigem_coerencia(self):
        dados = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(copiar_artefatos(Path(tmp)))
            caminho = raiz / 'reports/avaliacao_final_v1/previsoes_pre_corrida.csv'
            linhas = ler_csv(caminho)
            linha = next(item for item in linhas if item['rodada'] == '1' and item['ranking_modelo'] == '1')
            linha['favorito_modelo'] = '0'
            escrever_csv(caminho, linhas)
            with self.assertRaisesRegex(dados.DashboardDadosErro, 'favorito'):
                dados.carregar_temporada(raiz, 2025)
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(copiar_artefatos(Path(tmp)))
            caminho = raiz / 'reports/avaliacao_final_v1/avaliacao_corridas.csv'
            linhas = ler_csv(caminho)
            linha = next(item for item in linhas if item['rodada'] == '9')
            linha['motivos_nao_avaliavel'] = ''
            escrever_csv(caminho, linhas)
            with self.assertRaisesRegex(dados.DashboardDadosErro, 'não avaliável'):
                dados.carregar_temporada(raiz, 2025)

    def test_ranking_modelo_rejeita_probabilidade_invertida_sem_substituir_o_rank_publicado(self):
        dados = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(copiar_artefatos(Path(tmp)))
            for nome in ('previsoes_pre_corrida.csv', 'avaliacao_por_piloto.csv'):
                caminho = raiz / 'reports/avaliacao_final_v1' / nome
                linhas = ler_csv(caminho)
                russell = next(item for item in linhas if item['rodada'] == '1' and item['piloto_id'] == 'russell')
                self.assertEqual(russell['ranking_modelo'], '4')
                russell['probabilidade_modelo'] = '0.9999'
                escrever_csv(caminho, linhas)
            with self.assertRaisesRegex(dados.DashboardDadosErro, 'ranking_modelo.*probabilidade'):
                dados.carregar_temporada(raiz, 2025)

    def test_ranking_modelo_rejeita_empate_que_nao_desempata_por_piloto_id(self):
        dados = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(copiar_artefatos(Path(tmp)))
            for nome in ('previsoes_pre_corrida.csv', 'avaliacao_por_piloto.csv'):
                caminho = raiz / 'reports/avaliacao_final_v1' / nome
                linhas = ler_csv(caminho)
                ordenadas = sorted(
                    (item for item in linhas if item['rodada'] == '1'),
                    key=lambda item: int(item['ranking_modelo']),
                )
                primeiro, segundo = next(
                    (anterior, posterior)
                    for anterior, posterior in zip(ordenadas, ordenadas[1:])
                    if anterior['piloto_id'] > posterior['piloto_id']
                )
                segundo['probabilidade_modelo'] = primeiro['probabilidade_modelo']
                escrever_csv(caminho, linhas)
            with self.assertRaisesRegex(dados.DashboardDadosErro, 'ranking_modelo.*probabilidade'):
                dados.carregar_temporada(raiz, 2025)

    def test_metricas_json_rejeitam_numeros_em_texto_e_booleanos(self):
        dados = modulo()
        casos = (
            ('probabilisticas', 'modelo', 'log_loss', '0.2033'),
            ('probabilisticas', 'linhas_avaliaveis', None, '478'),
            ('cobertura', 'gps_total', None, True),
            ('ranking_modelo', 'media_integrantes_corretos', None, True),
            ('ranking_classificacao', 'distribuicao_0_1_2_3', '3', True),
        )
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(copiar_artefatos(Path(tmp)))
            caminho = raiz / 'reports/avaliacao_final_v1/metricas.json'
            original = caminho.read_text(encoding='utf-8')
            for bloco, campo, subcampo, valor in casos:
                with self.subTest(bloco=bloco, campo=campo, subcampo=subcampo):
                    metricas = json.loads(original)
                    destino = metricas[bloco][campo]
                    if subcampo is None:
                        metricas[bloco][campo] = valor
                    else:
                        destino[subcampo] = valor
                    caminho.write_text(json.dumps(metricas), encoding='utf-8')
                    with self.assertRaisesRegex(dados.DashboardDadosErro, 'metricas.json.*tipo numérico'):
                        dados.carregar_temporada(raiz, 2025)

    def test_calibracao_tem_vinte_linhas_e_faixas_vazias_sem_ponto(self):
        dados = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            pacote = dados.carregar_temporada(Path(copiar_artefatos(Path(tmp))), 2025)
        self.assertEqual(len(pacote['calibracao']), 20)
        vazias = [linha for linha in pacote['calibracao'] if linha['contagem'] == 0]
        self.assertTrue(vazias)
        self.assertTrue(all(linha['media_prevista'] is None and linha['frequencia_observada'] is None for linha in vazias))

    def test_calibracao_rejeita_rotulo_invalido_ou_duplicado(self):
        dados = modulo()
        for caso in ('invalido', 'duplicado'):
            with self.subTest(caso=caso), tempfile.TemporaryDirectory() as tmp:
                raiz = Path(copiar_artefatos(Path(tmp)))
                caminho = raiz / 'reports/avaliacao_final_v1/calibracao.csv'
                linhas = ler_csv(caminho)
                if caso == 'invalido':
                    linhas[1]['faixa'] = 'invalida'
                else:
                    linhas[1]['faixa'] = linhas[0]['faixa']
                    linhas[1]['limite_inferior'] = linhas[0]['limite_inferior']
                    linhas[1]['limite_superior'] = linhas[0]['limite_superior']
                escrever_csv(caminho, linhas)
                with self.assertRaisesRegex(dados.DashboardDadosErro, 'faixa.*calibração|calibração.*duplicada'):
                    dados.carregar_temporada(raiz, 2025)


class TestCacheEIsolamento(unittest.TestCase):
    def test_assinatura_por_bytes_muda_com_mtime_preservado(self):
        dados = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(copiar_artefatos(Path(tmp)))
            antes = dados.conteudos_temporada(raiz, 2025)
            caminho = raiz / 'reports/avaliacao_final_v1/calibracao.csv'
            estat = caminho.stat()
            caminho.write_bytes(caminho.read_bytes() + b'\n')
            os.utime(caminho, ns=(estat.st_atime_ns, estat.st_mtime_ns))
            depois = dados.conteudos_temporada(raiz, 2025)
        self.assertNotEqual(dados.assinatura_conteudos(antes), dados.assinatura_conteudos(depois))

    def test_modulos_do_dashboard_nao_abrem_data_nem_importam_modelo_ou_rede(self):
        fontes = '\n'.join((RAIZ / nome).read_text(encoding='utf-8') for nome in ('pitwall/data/dashboard.py', 'pitwall/dashboard/app.py'))
        for proibido in ('joblib', 'sklearn', 'treinar_modelo', 'avaliar_modelo', 'data/', 'urllib.request', 'requests', 'socket'):
            self.assertNotIn(proibido, fontes.lower())


if __name__ == '__main__':
    unittest.main()
