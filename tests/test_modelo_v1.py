"""Regressões TDD da etapa 4; todas as bases deste arquivo são simuladas."""
import csv
import importlib
import importlib.util
import json
import socket
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def modulo():
    assert importlib.util.find_spec('treinar_modelo_v1'), 'Falta implementar treinar_modelo_v1.py'
    return importlib.import_module('treinar_modelo_v1')


def esquema():
    return {
        'entradas': list(modulo().ENTRADAS_AUTORIZADAS),
        'chaves': ['temporada', 'rodada', 'piloto_id'],
        'alvos': ['podio'],
        'identificacao': ['corrida', 'data_corrida', 'divisao',
                           'limite_inferior_referencia_utc'],
        'auditoria_proibida_como_entrada': ['posicao_final', 'pontos', 'status',
                                             'grid_resultado', 'resultado_ausente'],
    }


def linha(temporada, rodada, piloto, posicao, podio, *, classificacao_ausente='0',
          posicao_ausente='0', referencia_ausente='0', referencia='2024-01-01T10:00:00Z',
          repetida='0', auditoria='0'):
    valores = {
        'temporada': str(temporada), 'rodada': str(rodada), 'piloto_id': piloto,
        'corrida': 'GP simulado ' + str(rodada), 'data_corrida': f'{temporada}-01-01',
        'divisao': 'treino' if int(temporada) < 2024 else 'validacao',
        'limite_inferior_referencia_utc': referencia,
        'podio': podio, 'posicao_final': '999', 'pontos': '999', 'status': 'Auditoria',
        'grid_resultado': auditoria, 'resultado_ausente': auditoria,
        'posicao_classificacao': posicao,
        'posicao_classificacao_repetida': repetida,
        'classificacao_ausente': classificacao_ausente,
        'posicao_classificacao_ausente': posicao_ausente,
        'media_posicao_final_5': '' if piloto == 'novo' else '5.0',
        'taxa_podios_5': '' if piloto == 'novo' else '0.2',
        'n_posicoes_5': '0' if piloto == 'novo' else '5',
        'n_podios_5': '0' if piloto == 'novo' else '5',
        'media_pontos_equipe_5': '8.0', 'n_corridas_equipe_5': '5',
        'n_participacoes_equipe_5': '10', 'historico_piloto_insuficiente': '0',
        'historico_equipe_insuficiente': '0', 'equipe_pre_corrida_ausente': '0',
        'referencia_temporal_ausente': referencia_ausente,
    }
    return valores


def base_simulada():
    treino = []
    for ano, rodada in [(2021, 1), (2022, 1), (2023, 1)]:
        for piloto, pos, alvo in [('a', '1', '1'), ('b', '2', '1'), ('c', '3', '1'), ('d', '4', '0')]:
            treino.append(linha(ano, rodada, piloto, pos, alvo,
                                referencia=f'{ano}-01-01T10:00:00Z'))
    validacao = [
        linha(2024, 1, 'a', '1', '1'), linha(2024, 1, 'b', '1', '1', repetida='1'),
        linha(2024, 1, 'c', '3', '1'), linha(2024, 1, 'd', '4', '0'),
        linha(2024, 2, 'a', '1', '1'),
        linha(2024, 2, 'b', '2', '0', classificacao_ausente='1'),
        linha(2024, 2, 'c', '3', '1'), linha(2024, 2, 'd', '4', '0'),
        linha(2024, 2, 'novo', '', '', posicao_ausente='1'),
    ]
    return treino, validacao


def gravar_csv(caminho, linhas):
    campos = list(linhas[0])
    with caminho.open('w', encoding='utf-8', newline='') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos, lineterminator='\n')
        escritor.writeheader()
        escritor.writerows(linhas)


def preparar_fontes(raiz, treino=None, validacao=None):
    dados = raiz / 'dados'
    dados.mkdir(parents=True)
    treino_padrao, validacao_padrao = base_simulada()
    gravar_csv(dados / 'treino.csv', treino or treino_padrao)
    gravar_csv(dados / 'validacao.csv', validacao or validacao_padrao)
    (dados / 'colunas.json').write_text(json.dumps(esquema(), sort_keys=True), encoding='utf-8')
    plano = raiz / 'plano.md'
    plano.write_text('# Plano simulado já fixado\n', encoding='utf-8')
    return dados, plano


def ler_csv(caminho):
    with caminho.open(encoding='utf-8', newline='') as arquivo:
        return list(csv.DictReader(arquivo))


class TestSelecaoExplicita(unittest.TestCase):
    def test_entrada_proibida_e_lista_diferente_sao_recusadas(self):
        m = modulo()
        linha_teste = linha(2024, 1, 'a', '1', '1')
        with self.assertRaisesRegex(ValueError, 'permitidas|proibida'):
            m.selecionar_entradas([linha_teste], esquema(),
                                  features=list(m.ENTRADAS_AUTORIZADAS) + ['grid_resultado'])
        with self.assertRaisesRegex(ValueError, 'ordem|permitidas'):
            m.selecionar_entradas([linha_teste], esquema(),
                                  features=list(reversed(m.ENTRADAS_AUTORIZADAS)))

    def test_booleanos_alvos_e_infinitos_sao_validados(self):
        m = modulo()
        registro = linha(2024, 1, 'a', '1', '1', referencia_ausente='False')
        registro['classificacao_ausente'] = 'True'
        normalizada = m.validar_linhas([registro], esquema(), 'validacao')
        self.assertTrue(normalizada[0]['classificacao_ausente'])
        self.assertFalse(normalizada[0]['referencia_temporal_ausente'])
        registro_ruim = dict(registro, podio='2')
        with self.assertRaisesRegex(ValueError, 'podio'):
            m.validar_linhas([registro_ruim], esquema(), 'validacao')
        registro_inf = dict(registro, podio='1', media_posicao_final_5='inf')
        with self.assertRaisesRegex(ValueError, 'finito'):
            m.validar_linhas([registro_inf], esquema(), 'validacao')


class TestBarreiraNumerica(unittest.TestCase):
    def test_matmul_simulado_nao_emite_runtimewarning(self):
        rng = np.random.default_rng(42)
        matriz = rng.normal(size=(1319, 15))
        pesos = rng.normal(size=15)
        with warnings.catch_warnings():
            warnings.simplefilter('error', RuntimeWarning)
            for _ in range(10):
                resultado = matriz @ pesos
        self.assertTrue(np.isfinite(resultado).all())


class TestDefesasNumericasELeitura(unittest.TestCase):
    def test_runtimewarning_no_ajuste_e_na_previsao_interrompem_sem_artefatos(self):
        m = modulo()

        class PipelineComAvisoNoFit:
            def fit(self, matriz, alvos):
                warnings.warn('aviso numérico simulado no ajuste', RuntimeWarning)
                return self

        treino, _ = base_simulada()
        treino_normalizado = m.validar_linhas(treino, esquema(), 'treino')
        with patch.object(m, 'criar_pipeline', return_value=PipelineComAvisoNoFit()):
            with self.assertRaises(RuntimeWarning):
                m.ajustar(treino_normalizado, esquema())

        def aviso_na_previsao(self, matriz):
            warnings.warn('aviso numérico simulado na previsão', RuntimeWarning)
            return np.tile(np.array([[0.8, 0.2]]), (len(matriz), 1))

        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            dados, plano = preparar_fontes(raiz)
            with patch.object(m.Pipeline, 'predict_proba', aviso_na_previsao):
                with self.assertRaises(RuntimeWarning):
                    m.executar(dados, raiz / 'modelos', raiz / 'relatorios', plano=plano)
            self.assertFalse((raiz / 'modelos').exists())
            self.assertFalse((raiz / 'relatorios').exists())

    def test_carregamento_abre_somente_tres_fontes_permitidas_e_sem_rede(self):
        m = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            dados, _ = preparar_fontes(raiz)
            abertos = []
            original = Path.read_bytes

            def registrar_leitura(caminho):
                abertos.append(Path(caminho).resolve())
                return original(caminho)

            with patch.object(Path, 'read_bytes', registrar_leitura), \
                    patch.object(socket, 'create_connection', side_effect=AssertionError('rede proibida')):
                m.carregar_dados(dados)
            self.assertEqual(set(abertos), {
                (dados / 'treino.csv').resolve(),
                (dados / 'validacao.csv').resolve(),
                (dados / 'colunas.json').resolve(),
            })


class TestExperimentoIsolado(unittest.TestCase):
    def executar(self, raiz, treino=None, validacao=None):
        dados, plano = preparar_fontes(raiz, treino, validacao)
        return modulo().executar(dados, raiz / 'modelos', raiz / 'relatorios', plano=plano)

    def test_fit_usa_so_treino_e_rede_ou_2025_sao_bloqueados(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            dados, plano = preparar_fontes(raiz)
            (dados / 'teste_final_reservado.csv').write_text('NAO LER', encoding='utf-8')
            with patch.object(socket, 'create_connection', side_effect=AssertionError('rede proibida')):
                modulo().executar(dados, raiz / 'modelos_a', raiz / 'relatorios_a', plano=plano)
            meta_a = json.loads((raiz / 'modelos_a/metadados.json').read_text())
            treino, validacao = base_simulada()
            for registro in validacao:
                registro['posicao_classificacao'] = '999'
                registro['media_posicao_final_5'] = '999'
                registro['podio'] = '0' if registro['podio'] == '1' else '1'
            dados_b, plano_b = preparar_fontes(raiz / 'outra', treino, validacao)
            modulo().executar(dados_b, raiz / 'outra/modelos', raiz / 'outra/relatorios', plano=plano_b)
            meta_b = json.loads((raiz / 'outra/modelos/metadados.json').read_text())
            self.assertEqual(meta_a['parametros_aprendidos'], meta_b['parametros_aprendidos'])
            self.assertEqual((raiz / 'modelos_a/modelo.joblib').read_bytes(),
                             (raiz / 'outra/modelos/modelo.joblib').read_bytes())
            with self.assertRaisesRegex(ValueError, '2025|reservado'):
                modulo().carregar_dados(dados / '2025')

    def test_alvos_e_auditoria_nao_alteram_probabilidades_ou_favoritos(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            self.executar(raiz / 'a')
            treino, validacao = base_simulada()
            for registro in validacao:
                if registro['podio'] != '':
                    registro['podio'] = '0' if registro['podio'] == '1' else '1'
                registro['grid_resultado'] = '0'
                registro['pontos'] = '10000'
                registro['status'] = 'Resultado que não pode entrar'
                registro['resultado_ausente'] = '1'
            self.executar(raiz / 'b', treino, validacao)
            anterior = ler_csv(raiz / 'a/relatorios/previsoes_validacao.csv')
            posterior = ler_csv(raiz / 'b/relatorios/previsoes_validacao.csv')
            campos = ['temporada', 'rodada', 'piloto_id', 'probabilidade_modelo',
                      'probabilidade_constante', 'favorito_modelo', 'favorito_classificacao']
            self.assertEqual([{k: r[k] for k in campos} for r in anterior],
                             [{k: r[k] for k in campos} for r in posterior])

    def test_unknown_nao_vira_zero_posicao_ausente_e_empates_continuam(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            self.executar(raiz)
            previsoes = ler_csv(raiz / 'relatorios/previsoes_validacao.csv')
            novo = next(r for r in previsoes if r['piloto_id'] == 'novo' and r['rodada'] == '2')
            self.assertEqual(novo['elegivel_previsao'], '1')
            self.assertEqual(novo['alvo_conhecido'], '0')
            self.assertEqual(novo['podio'], '')
            self.assertNotEqual(novo['probabilidade_modelo'], '')
            grupo = [r for r in previsoes if r['rodada'] == '1']
            self.assertEqual([r['piloto_id'] for r in grupo if r['favorito_classificacao'] == '1'],
                             ['a', 'b', 'c'])
            self.assertIn('fronteira', next(r for r in grupo if r['piloto_id'] == 'c')['empates_classificacao'])

    def test_gp_parcial_nao_recebe_zero_falso_e_destino_divergente_preserva_tudo(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            self.executar(raiz)
            metricas = json.loads((raiz / 'relatorios/metricas.json').read_text())
            self.assertEqual(metricas['ranking_modelo']['corridas_avaliaveis'], 1)
            avaliacoes = ler_csv(raiz / 'relatorios/avaliacao_corridas.csv')
            parcial = next(r for r in avaliacoes if r['rodada'] == '2')
            self.assertEqual(parcial['avaliavel_ranking'], '0')
            self.assertEqual(parcial['acertos_modelo'], '')
            antes = {p.relative_to(raiz).as_posix(): p.read_bytes() for p in raiz.rglob('*') if p.is_file()}
            alvo = raiz / 'relatorios/calibracao.csv'
            alvo.write_bytes(b'destino divergente')
            esperado = {p.relative_to(raiz).as_posix(): p.read_bytes() for p in raiz.rglob('*') if p.is_file()}
            with self.assertRaises(FileExistsError):
                modulo().executar(raiz / 'dados', raiz / 'modelos', raiz / 'relatorios', plano=raiz / 'plano.md')
            depois = {p.relative_to(raiz).as_posix(): p.read_bytes() for p in raiz.rglob('*') if p.is_file()}
            self.assertNotEqual(antes, esperado)
            self.assertEqual(esperado, depois)

    def test_duas_execucoes_sao_reproduziveis(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            self.executar(raiz)
            antes = {p.relative_to(raiz).as_posix(): p.read_bytes() for p in raiz.rglob('*') if p.is_file()}
            modulo().executar(raiz / 'dados', raiz / 'modelos', raiz / 'relatorios', plano=raiz / 'plano.md')
            depois = {p.relative_to(raiz).as_posix(): p.read_bytes() for p in raiz.rglob('*') if p.is_file()}
            self.assertEqual(antes, depois)

    def test_artefatos_tem_calibracao_fixas_e_metadados_auditaveis(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            self.executar(raiz)
            esperados = {
                'modelos/modelo.joblib', 'modelos/metadados.json',
                'relatorios/previsoes_validacao.csv', 'relatorios/avaliacao_corridas.csv',
                'relatorios/calibracao.csv', 'relatorios/coeficientes.csv', 'relatorios/cobertura_treino.csv',
                'relatorios/metricas.json', 'relatorios/relatorio.md', 'relatorios/calibracao.svg',
            }
            encontrados = {p.relative_to(raiz).as_posix() for p in raiz.rglob('*') if p.is_file()}
            self.assertTrue(esperados.issubset(encontrados))
            calibracao = ler_csv(raiz / 'relatorios/calibracao.csv')
            self.assertEqual(len(calibracao), 20)
            self.assertEqual([r['faixa'] for r in calibracao[:10]],
                             ['[0.0,0.1)', '[0.1,0.2)', '[0.2,0.3)', '[0.3,0.4)', '[0.4,0.5)',
                              '[0.5,0.6)', '[0.6,0.7)', '[0.7,0.8)', '[0.8,0.9)', '[0.9,1.0]'])
            for registro in calibracao:
                if registro['contagem'] == '0':
                    self.assertEqual(registro['media_prevista'], '')
                    self.assertEqual(registro['frequencia_observada'], '')
            metadados = json.loads((raiz / 'modelos/metadados.json').read_text())
            self.assertIn('sha256_plano_fixado', metadados)
            self.assertEqual(metadados['entradas'], modulo().ENTRADAS_AUTORIZADAS)
            self.assertIn('Distribuição de GPs com 0 / 1 / 2 / 3',
                          (raiz / 'relatorios/relatorio.md').read_text())
            self.assertIn('cobertura_treino.csv', (raiz / 'relatorios/relatorio.md').read_text())


if __name__ == '__main__':
    unittest.main()
