"""TDD da etapa 5: usa somente registros sintéticos de 2025 em TMP."""
import csv
import hashlib
import importlib
import importlib.util
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def modulo():
    assert importlib.util.find_spec('avaliar_modelo_v1'), 'Falta implementar avaliar_modelo_v1.py'
    return importlib.import_module('avaliar_modelo_v1')


def esquema():
    return json.loads((RAIZ / 'data/preparado/colunas.json').read_text(encoding='utf-8'))


def linha(piloto_id='piloto_a', *, temporada='2025', divisao='teste_final_reservado', rodada='1',
          posicao='1', podio='1'):
    return {
        'temporada': temporada,
        'rodada': rodada,
        'piloto_id': piloto_id,
        'corrida': 'GP sintético {}'.format(rodada),
        'data_corrida': '2025-01-01',
        'circuito_id': 'sintetico',
        'piloto': piloto_id.upper(),
        'equipe_id': 'equipe_sintetica',
        'equipe_id_entrada': 'equipe_sintetica',
        'divisao': divisao,
        'sessao_referencia': 'Qualifying',
        'limite_inferior_referencia_utc': '2025-01-01T10:00:00Z',
        'fim_sessao_referencia_utc': '',
        'precisao_referencia': 'inicio_sessao',
        'classificacao_nao_define_grid_gp': '0',
        'podio': podio,
        'posicao_final': '99',
        'pontos': '99',
        'status': 'AUDITORIA_PROIBIDA',
        'grid_resultado': '99',
        'resultado_ausente': '0',
        'posicao_classificacao': posicao,
        'posicao_classificacao_repetida': '0',
        'classificacao_ausente': '0',
        'posicao_classificacao_ausente': '0',
        'media_posicao_final_5': '5.0',
        'taxa_podios_5': '0.2',
        'n_posicoes_5': '5',
        'n_podios_5': '5',
        'media_pontos_equipe_5': '8.0',
        'n_corridas_equipe_5': '5',
        'n_participacoes_equipe_5': '10',
        'historico_piloto_insuficiente': '0',
        'historico_equipe_insuficiente': '0',
        'equipe_pre_corrida_ausente': '0',
        'referencia_temporal_ausente': '0',
    }


class MapaSemAlvoOuAuditoria(dict):
    """Falha se a fase pré-corrida tentar acessar resultado, alvo ou auditoria."""

    PROIBIDAS = {'podio', 'posicao_final', 'pontos', 'status', 'grid_resultado', 'resultado_ausente'}

    def __getitem__(self, chave):
        if chave in self.PROIBIDAS:
            raise AssertionError('A fase de previsão acessou {}'.format(chave))
        return super().__getitem__(chave)

    def get(self, chave, *padrao):
        if chave in self.PROIBIDAS:
            raise AssertionError('A fase de previsão acessou {}'.format(chave))
        return super().get(chave, *padrao)


class PipelineSomentePrever:
    def predict_proba(self, matriz):
        assert matriz.shape[1] == 15
        return np.tile(np.array([[0.8, 0.2]]), (len(matriz), 1))


class TestValidacaoESeparacao(unittest.TestCase):
    def test_validador_e_exclusivo_para_teste_2025(self):
        m = modulo()
        aprovado = m.validar_linhas_teste([linha()], esquema())
        self.assertEqual(aprovado[0]['temporada'], '2025')
        for campo, valor in [('temporada', '2024'), ('temporada', '2026'),
                              ('divisao', 'validacao'), ('divisao', 'treino')]:
            registro = linha()
            registro[campo] = valor
            with self.assertRaisesRegex(ValueError, '2025|Divisão|divisão'):
                m.validar_linhas_teste([registro], esquema())

    def test_previsao_e_favoritos_nao_acessam_alvo_nem_auditoria(self):
        m = modulo()
        registros = m.validar_linhas_teste(
            [MapaSemAlvoOuAuditoria(linha('z', posicao='2')), MapaSemAlvoOuAuditoria(linha('a', posicao='1'))],
            esquema(),
        )
        previsoes = m.prever_teste(PipelineSomentePrever(), 0.15011372251705837, registros, esquema())
        self.assertEqual([registro['piloto_id'] for registro in previsoes], ['z', 'a'])
        self.assertTrue(all('podio' not in registro for registro in previsoes))
        self.assertTrue(all('status' not in registro for registro in previsoes))
        self.assertEqual([registro['piloto_id'] for registro in previsoes if registro['favorito_classificacao']], ['z', 'a'])
        self.assertTrue(all(math.isclose(registro['probabilidade_modelo'], 0.2) for registro in previsoes))


def previsao(piloto_id, rodada, probabilidade, alvo, *, elegivel=True, posicao=1):
    return {
        'temporada': '2025', 'rodada': str(rodada), 'piloto_id': piloto_id,
        'corrida': 'GP sintético {}'.format(rodada),
        'posicao_classificacao': float(posicao),
        'posicao_classificacao_repetida': False,
        'elegivel_previsao': elegivel,
        'alvo_conhecido': alvo is not None,
        'podio': alvo,
        'probabilidade_modelo': probabilidade if elegivel else None,
        'probabilidade_constante': 0.15011372251705837 if elegivel else None,
        'favorito_modelo': elegivel and piloto_id in ('a', 'b', 'c'),
        'favorito_classificacao': elegivel and piloto_id in ('a', 'b', 'c'),
    }


def escrever_csv(caminho, linhas):
    with caminho.open('w', encoding='utf-8', newline='') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]), lineterminator='\n')
        escritor.writeheader()
        escritor.writerows(linhas)


def fontes_sinteticas(raiz, linhas=None):
    dados = raiz / 'dados_sinteticos'
    dados.mkdir(parents=True, exist_ok=True)
    linhas = linhas or [linha('a', posicao='1', podio='1'), linha('b', posicao='2', podio='1'),
                        linha('c', posicao='3', podio='1'), linha('d', posicao='4', podio='0')]
    teste = dados / 'teste_final_reservado.csv'
    escrever_csv(teste, linhas)
    esquema_tmp = dados / 'colunas.json'
    esquema_tmp.write_bytes((RAIZ / 'data/preparado/colunas.json').read_bytes())
    return teste, esquema_tmp


class TestMetricasECalibracao(unittest.TestCase):
    def test_metricas_tem_oraculo_aritmetico_e_cobertura_de_teste(self):
        m = modulo()
        registros = [
            previsao('a', 1, 0.9, 1, posicao=1), previsao('b', 1, 0.8, 1, posicao=2),
            previsao('c', 1, 0.7, 1, posicao=3), previsao('d', 1, 0.1, 0, posicao=4),
        ]
        metricas, corridas, calibracao = m.avaliar_teste(registros)
        esperado_brier = sum((registro['probabilidade_modelo'] - registro['podio']) ** 2
                             for registro in registros) / 4
        esperado_log_loss = -sum(
            registro['podio'] * math.log(registro['probabilidade_modelo']) +
            (1 - registro['podio']) * math.log(1 - registro['probabilidade_modelo'])
            for registro in registros
        ) / 4
        self.assertAlmostEqual(metricas['probabilisticas']['modelo']['brier'], esperado_brier)
        self.assertAlmostEqual(metricas['probabilisticas']['modelo']['log_loss'], esperado_log_loss)
        self.assertEqual(metricas['cobertura']['linhas_teste'], 4)
        self.assertNotIn('linhas_validacao', metricas['cobertura'])
        self.assertEqual(corridas[0]['acertos_modelo'], 3)
        self.assertEqual(len(calibracao), 20)

    def test_gps_incompletos_ficam_indefinidos_e_faixas_incluem_limites(self):
        m = modulo()
        registros = [
            previsao('a', 1, 0.0, 1), previsao('b', 1, 0.1, 1),
            previsao('c', 1, 1.0, 1), previsao('d', 1, 0.5, 0),
            previsao('a', 2, 0.5, 1), previsao('b', 2, 0.5, 1),
            previsao('a', 3, 0.5, 1), previsao('b', 3, 0.5, 1),
            previsao('c', 3, 0.5, 1), previsao('d', 3, 0.5, 0, elegivel=False),
            previsao('a', 4, 0.5, 1), previsao('b', 4, 0.5, 1),
            previsao('c', 4, 0.5, None), previsao('d', 4, 0.5, 0),
            previsao('a', 5, 0.5, 1), previsao('b', 5, 0.5, 1),
            previsao('c', 5, 0.5, 0), previsao('d', 5, 0.5, 0),
        ]
        metricas, corridas, calibracao = m.avaliar_teste(registros)
        por_rodada = {linha['rodada']: linha for linha in corridas}
        self.assertIsNone(por_rodada['2']['acertos_modelo'])
        self.assertIn('menos_de_3_elegiveis', por_rodada['2']['motivos_nao_avaliavel'])
        self.assertIn('participante_inelegivel', por_rodada['3']['motivos_nao_avaliavel'])
        self.assertIn('alvo_desconhecido', por_rodada['4']['motivos_nao_avaliavel'])
        self.assertIn('quantidade_de_podios_diferente_de_3', por_rodada['5']['motivos_nao_avaliavel'])
        modelo = [linha for linha in calibracao if linha['metodo'] == 'modelo']
        self.assertEqual([linha['contagem'] for linha in modelo][0], 1)
        self.assertEqual([linha['contagem'] for linha in modelo][1], 1)
        self.assertEqual([linha['contagem'] for linha in modelo][9], 1)
        self.assertTrue(any(linha['contagem'] == 0 and linha['media_prevista'] is None for linha in modelo))
        svg = m._svg_calibracao_2025(calibracao)
        self.assertIn('Calibração descritiva (2025)', svg)
        self.assertNotIn('Calibração descritiva (2024)', svg)


class TestExecucaoCongelada(unittest.TestCase):
    def executar(self, raiz, linhas=None, **substitutos):
        teste, esquema_tmp = fontes_sinteticas(raiz, linhas)
        argumentos = {
            'teste': teste,
            'esquema': esquema_tmp,
            'modelo': RAIZ / 'models/modelo_v1/modelo.joblib',
            'metadados': RAIZ / 'models/modelo_v1/metadados.json',
            'plano_avaliacao': RAIZ / 'docs/avaliacao_final_v1.md',
            'plano_original': RAIZ / 'docs/experimento_modelo_v1.md',
            'metricas_2024': RAIZ / 'reports/modelo_v1/metricas.json',
            'relatorios': raiz / 'relatorios',
        }
        argumentos.update(substitutos)
        return modulo().executar(**argumentos)

    def test_execucao_sem_fit_publica_saidas_deterministicas_e_preserva_v1(self):
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            artefatos_v1 = [RAIZ / 'models/modelo_v1/modelo.joblib',
                             RAIZ / 'models/modelo_v1/metadados.json',
                             RAIZ / 'reports/modelo_v1/metricas.json']
            antes = {caminho: hashlib.sha256(caminho.read_bytes()).hexdigest() for caminho in artefatos_v1}
            bloqueio = AssertionError('Avaliação não pode ajustar o pipeline congelado')
            with patch.object(Pipeline, 'fit', side_effect=bloqueio), \
                    patch.object(Pipeline, 'fit_transform', side_effect=bloqueio), \
                    patch.object(SimpleImputer, 'fit', side_effect=bloqueio), \
                    patch.object(SimpleImputer, 'fit_transform', side_effect=bloqueio), \
                    patch.object(StandardScaler, 'fit', side_effect=bloqueio), \
                    patch.object(StandardScaler, 'fit_transform', side_effect=bloqueio), \
                    patch.object(StandardScaler, 'partial_fit', side_effect=bloqueio), \
                    patch.object(LogisticRegression, 'fit', side_effect=bloqueio):
                self.executar(raiz)
            depois = {caminho: hashlib.sha256(caminho.read_bytes()).hexdigest() for caminho in artefatos_v1}
            self.assertEqual(antes, depois)
            esperadas = {
                'previsoes_pre_corrida.csv', 'avaliacao_por_piloto.csv', 'cobertura_pilotos.csv',
                'cobertura_gps.csv', 'avaliacao_corridas.csv', 'metricas.json', 'calibracao.csv', 'calibracao.svg',
                'comparacao_2024.json', 'relatorio.md', 'manifesto.json',
            }
            encontrados = {caminho.name for caminho in (raiz / 'relatorios').iterdir()}
            self.assertEqual(encontrados, esperadas)
            manifesto = json.loads((raiz / 'relatorios/manifesto.json').read_text(encoding='utf-8'))
            self.assertNotIn('manifesto.json', manifesto['hashes_saidas'])
            self.assertEqual(manifesto['constante_treino'], 0.15011372251705837)
            primeira = {p.name: p.read_bytes() for p in (raiz / 'relatorios').iterdir()}
            self.executar(raiz)
            segunda = {p.name: p.read_bytes() for p in (raiz / 'relatorios').iterdir()}
            self.assertEqual(primeira, segunda)

    def test_hash_adulterado_e_destino_divergente_sao_rejeitados_sem_publicacao_parcial(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            teste, esquema_tmp = fontes_sinteticas(raiz)
            modelo_adulterado = raiz / 'modelo_adulterado.joblib'
            modelo_adulterado.write_bytes((RAIZ / 'models/modelo_v1/modelo.joblib').read_bytes() + b'alterado')
            with self.assertRaisesRegex(ValueError, 'SHA-256|hash'):
                self.executar(raiz / 'hash', modelo=modelo_adulterado)
            self.assertFalse((raiz / 'hash/relatorios').exists())
            self.executar(raiz / 'normal')
            destino = raiz / 'normal/relatorios/calibracao.csv'
            destino.write_bytes(b'divergente')
            esperado = {p.name: p.read_bytes() for p in (raiz / 'normal/relatorios').iterdir()}
            with self.assertRaises(FileExistsError):
                self.executar(raiz / 'normal')
            depois = {p.name: p.read_bytes() for p in (raiz / 'normal/relatorios').iterdir()}
            self.assertEqual(esperado, depois)

    def test_previsoes_sao_invariantes_a_alvo_auditoria_e_desconhecido_nao_vira_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            original = [linha('a', posicao='1', podio='1'), linha('b', posicao='2', podio=''),
                        linha('c', posicao='3', podio='1'), linha('d', posicao='4', podio='0')]
            self.executar(raiz / 'a', linhas=original)
            alterado = [dict(registro) for registro in original]
            for registro in alterado:
                if registro['podio']:
                    registro['podio'] = '0' if registro['podio'] == '1' else '1'
                registro.update({'posicao_final': '1', 'pontos': '999999', 'status': 'ALTERADO',
                                 'grid_resultado': '0', 'resultado_ausente': '1'})
            self.executar(raiz / 'b', linhas=alterado)
            def pre(raiz_rel):
                with (raiz_rel / 'relatorios/previsoes_pre_corrida.csv').open(encoding='utf-8', newline='') as arquivo:
                    return list(csv.DictReader(arquivo))
            primeira, segunda = pre(raiz / 'a'), pre(raiz / 'b')
            campos = ['piloto_id', 'probabilidade_modelo', 'probabilidade_constante',
                      'favorito_modelo', 'favorito_classificacao']
            self.assertEqual([{c: r[c] for c in campos} for r in primeira],
                             [{c: r[c] for c in campos} for r in segunda])
            self.assertNotIn('podio', primeira[0])
            with (raiz / 'a/relatorios/avaliacao_por_piloto.csv').open(encoding='utf-8', newline='') as arquivo:
                final = list(csv.DictReader(arquivo))
            desconhecido = next(registro for registro in final if registro['piloto_id'] == 'b')
            self.assertEqual(desconhecido['podio'], '')
            self.assertEqual(desconhecido['alvo_conhecido'], '0')
            self.assertNotEqual(desconhecido['probabilidade_modelo'], '')

    def test_hash_falha_antes_de_abrir_o_teste_e_empate_modelo_e_lexicografico(self):
        m = modulo()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            teste, esquema_tmp = fontes_sinteticas(raiz)
            modelo_adulterado = raiz / 'modelo_adulterado.joblib'
            modelo_adulterado.write_bytes((RAIZ / 'models/modelo_v1/modelo.joblib').read_bytes() + b'alterado')
            original = Path.read_bytes
            def bloquear_teste(caminho):
                if Path(caminho) == teste:
                    raise AssertionError('teste não pode abrir antes da checagem de hash')
                return original(caminho)
            with patch.object(Path, 'read_bytes', bloquear_teste), self.assertRaises(ValueError):
                m.executar(teste=teste, esquema=esquema_tmp, modelo=modelo_adulterado,
                           metadados=RAIZ / 'models/modelo_v1/metadados.json',
                           plano_avaliacao=RAIZ / 'docs/avaliacao_final_v1.md',
                           plano_original=RAIZ / 'docs/experimento_modelo_v1.md',
                           metricas_2024=RAIZ / 'reports/modelo_v1/metricas.json', relatorios=raiz / 'relatorios')
        registros = m.validar_linhas_teste([linha('z'), linha('a'), linha('b'), linha('c')], esquema())
        saida = m.prever_teste(PipelineSomentePrever(), 0.15011372251705837, registros, esquema())
        por_id = {registro['piloto_id']: registro for registro in saida}
        self.assertEqual([registro['piloto_id'] for registro in saida if registro['favorito_modelo']], ['a', 'b', 'c'])
        self.assertIn('a,b,c,z', por_id['a']['empates_modelo'])
        self.assertIn('impacto_fronteira=sim', por_id['a']['empates_modelo'])

    def test_nome_da_fonte_e_entrada_proibida_sao_recusados(self):
        m = modulo()
        registro = linha()
        with self.assertRaisesRegex(ValueError, 'proibida|permitidas'):
            m.selecionar_entradas([registro], esquema(),
                                  features=list(m.ENTRADAS_AUTORIZADAS) + ['status'])
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            _, esquema_tmp = fontes_sinteticas(raiz)
            caminho_errado = raiz / 'validacao.csv'
            escrever_csv(caminho_errado, [linha()])
            with self.assertRaisesRegex(ValueError, 'única fonte'):
                m._ler_teste(caminho_errado, json.loads(esquema_tmp.read_text(encoding='utf-8')))


if __name__ == '__main__':
    unittest.main()
