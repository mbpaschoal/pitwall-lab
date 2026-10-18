"""AppTest da etapa 6: usa uma cópia temporária de reports/, sem data/ ou modelos."""
import os
import shutil
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
# O terminal do agente injeta um site-packages Python 3.14 antes do .venv 3.9.
# AppTest deve usar a cópia compatível de click instalada no ambiente do projeto.
sys.path[:] = [p for p in sys.path if '/.hermes/installs/' not in p]
SITE_LOCAL = str(RAIZ / '.venv/lib/python3.9/site-packages')
if SITE_LOCAL in sys.path:
    sys.path.remove(SITE_LOCAL)
sys.path.insert(0, SITE_LOCAL)
sys.path.insert(0, str(RAIZ))

from streamlit.testing.v1 import AppTest
import app


def copiar_artefatos(raiz):
    for origem_relativa in ('reports/modelo_v1', 'reports/avaliacao_final_v1'):
        origem = RAIZ / origem_relativa
        destino = raiz / origem_relativa
        destino.mkdir(parents=True, exist_ok=True)
        for arquivo in origem.iterdir():
            if arquivo.name in {
                'previsoes_validacao.csv', 'avaliacao_corridas.csv', 'metricas.json', 'calibracao.csv',
                'previsoes_pre_corrida.csv', 'avaliacao_por_piloto.csv',
            }:
                shutil.copy2(arquivo, destino / arquivo.name)
    return raiz


def por_chave(elementos, chave):
    return next(elemento for elemento in elementos if elemento.key == chave)


def texto_renderizado(at):
    partes = []
    for tipo in ('markdown', 'text', 'caption', 'title', 'header', 'subheader', 'info', 'warning', 'error'):
        for elemento in at.get(tipo):
            partes.append(str(getattr(elemento, 'value', elemento)))
    return '\n'.join(partes)


class TestDashboardApp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = copiar_artefatos(Path(self.tmp.name))
        self.ambiente = patch.dict(os.environ, {'PITWALL_DASHBOARD_ROOT': str(self.raiz)}, clear=False)
        self.ambiente.start()
        self.addCleanup(self.ambiente.stop)
        self.addCleanup(self.tmp.cleanup)
        self.at = AppTest.from_file(RAIZ / 'app.py', default_timeout=15)

    def executar(self):
        self.at.run(timeout=15)
        self.assertFalse(self.at.exception, [str(e.value) for e in self.at.exception])
        return self.at

    def escolher(self, chave, valor):
        por_chave(self.at.get('selectbox'), chave).set_value(valor)
        return self.executar()

    def test_navega_tres_telas_com_campos_e_nota_retrospectiva(self):
        self.executar()
        radio = por_chave(self.at.get('radio'), 'tela')
        self.assertEqual(radio.value, 'Explorar um GP')
        self.assertIn('Estudo retrospectivo com dados históricos.', texto_renderizado(self.at))
        self.assertEqual(por_chave(self.at.get('selectbox'), 'temporada').value, 2025)
        self.assertEqual(por_chave(self.at.get('selectbox'), 'gp').value, '2025:1')

        radio.set_value('Desempenho')
        self.executar()
        texto = texto_renderizado(self.at)
        self.assertIn('Modelo versus constante', texto)
        self.assertIn('478', texto)

        radio = por_chave(self.at.get('radio'), 'tela')
        radio.set_value('Como funciona')
        self.executar()
        texto = texto_renderizado(self.at)
        self.assertIn('15 entradas', texto)
        self.assertIn('CC BY-NC-SA 4.0', texto)

    def test_gp_fica_desabilitado_fora_da_exploracao_sem_desabilitar_temporada(self):
        self.executar()
        gp_inicial = por_chave(self.at.get('selectbox'), 'gp').value
        radio = por_chave(self.at.get('radio'), 'tela')

        for tela in ('Desempenho', 'Como funciona'):
            radio.set_value(tela)
            self.executar()
            seletor_gp = por_chave(self.at.get('selectbox'), 'gp')
            seletor_temporada = por_chave(self.at.get('selectbox'), 'temporada')
            self.assertTrue(seletor_gp.disabled)
            self.assertEqual(seletor_gp.value, gp_inicial)
            self.assertFalse(seletor_temporada.disabled)
            self.assertIn('aplica-se apenas em Explorar um GP', texto_renderizado(self.at))

    def test_grafico_vazio_e_probabilidade_maxima_nao_criam_dado_falso_nem_eixo_acima_de_100(self):
        vazio = app.grafico_probabilidades([])
        self.assertEqual(len(vazio.data), 0)
        self.assertIn('Nenhum participante elegível', vazio.layout.annotations[0].text)
        figura = app.grafico_probabilidades([{
            'elegivel_previsao': True,
            'probabilidade_modelo': 1.0,
            'piloto_id': 'piloto_teste',
            'favorito_modelo': True,
        }])
        self.assertLessEqual(figura.layout.xaxis.range[1], 100)

    def test_calibracao_reserva_topo_para_legenda_sem_encobrir_titulo_do_eixo(self):
        figura = app.grafico_calibracao([
            {'metodo': 'modelo', 'contagem': 2, 'media_prevista': 0.2, 'frequencia_observada': 0.1, 'faixa': '[0.1, 0.2)'},
            {'metodo': 'constante', 'contagem': 2, 'media_prevista': 0.3, 'frequencia_observada': 0.2, 'faixa': '[0.2, 0.3)'},
        ])
        self.assertEqual(figura.layout.height, 460)
        self.assertEqual(figura.layout.margin.t, 70)
        self.assertEqual(figura.layout.margin.b, 60)
        self.assertEqual(figura.layout.legend.orientation, 'h')
        self.assertEqual(figura.layout.legend.x, 0)
        self.assertEqual(figura.layout.legend.y, 1.04)
        self.assertEqual(figura.layout.legend.yanchor, 'bottom')
        self.assertEqual(figura.layout.xaxis.title.text, 'Média prevista')
        self.assertEqual(figura.layout.yaxis.title.text, 'Frequência observada')
        self.assertEqual([traco.marker.symbol for traco in figura.data[:2]], ['circle', 'diamond'])

    def test_explorar_exibe_temporada_cobertura_na_e_aviso_de_favoritos_antes_da_avaliacao(self):
        self.executar()
        self.escolher('temporada', 2025)
        self.escolher('gp', '2025:9')
        texto = texto_renderizado(self.at)
        self.assertIn('2025 — avaliação final retrospectiva já realizada', texto)
        self.assertIn('Cobertura desta corrida', texto)
        self.assertIn('Participantes preparados', texto)
        self.assertIn('Elegíveis', texto)
        self.assertIn('Alvos conhecidos', texto)
        self.assertIn('N/A — não avaliável', texto)
        self.assertLess(texto.index('Cobertura desta corrida'), texto.index('Probabilidades de pódio'))
        self.assertIn('menos de três favoritos', app.aviso_favoritos_insuficientes(2).lower())

    def test_como_funciona_expoe_regras_congeladas_e_links_dos_dois_relatorios(self):
        self.executar()
        radio = por_chave(self.at.get('radio'), 'tela')
        radio.set_value('Como funciona')
        self.executar()
        texto = texto_renderizado(self.at)
        texto_minusculo = texto.lower()
        self.assertIn('classificação presente e referência temporal', texto)
        self.assertIn('posição de classificação ausente e histórico insuficiente não excluem', texto_minusculo)
        self.assertIn('medianas aprendidas somente no treino', texto_minusculo)
        self.assertIn('escala também foi aprendida somente nesse treino', texto_minusculo)
        self.assertIn('relatório de 2024', texto_minusculo)
        self.assertIn('avaliação de 2025', texto_minusculo)

    def test_todas_as_24_corridas_de_cada_temporada_renderizam_e_preservam_filtros(self):
        self.executar()
        for temporada in (2024, 2025):
            self.escolher('temporada', temporada)
            seletor_gp = por_chave(self.at.get('selectbox'), 'gp')
            valores = list(seletor_gp.options)
            self.assertEqual(len(valores), 24)
            for valor in valores:
                seletor_gp.set_value(valor)
                self.executar()
                self.assertIn('Modelo e referências — calculados sem o alvo atual', texto_renderizado(self.at))
                seletor_gp = por_chave(self.at.get('selectbox'), 'gp')

    def test_espanha_e_sao_paulo_2025_exibem_na_motivo_unknown_e_inelegivel(self):
        self.executar()
        self.escolher('temporada', 2025)
        self.escolher('gp', '2025:9')
        texto = texto_renderizado(self.at).lower()
        self.assertIn('n/a', texto)
        self.assertIn('alvo_desconhecido', texto)
        self.assertIn('stroll', texto)
        self.escolher('gp', '2025:21')
        texto = texto_renderizado(self.at).lower()
        self.assertIn('n/a', texto)
        self.assertIn('participante_inelegivel', texto)
        self.assertIn('bortoleto', texto)

    def test_execucao_app_nao_chama_socket_e_nao_importa_joblib(self):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('rede externa proibida')):
            self.executar()
        fontes = (RAIZ / 'app.py').read_text(encoding='utf-8').lower()
        self.assertNotIn('joblib', fontes)
        self.assertNotIn('sklearn', fontes)

    def test_metricas_json_com_numero_em_texto_exibe_erro_util_sem_traceback(self):
        caminho = self.raiz / 'reports/avaliacao_final_v1/metricas.json'
        import json
        metricas = json.loads(caminho.read_text(encoding='utf-8'))
        metricas['probabilisticas']['modelo']['log_loss'] = '0.2033'
        caminho.write_text(json.dumps(metricas), encoding='utf-8')
        self.executar()
        por_chave(self.at.get('radio'), 'tela').set_value('Desempenho')
        self.executar()
        texto = texto_renderizado(self.at).lower()
        self.assertIn('metricas.json', texto)
        self.assertIn('restaure', texto)

    def test_calibracao_com_rotulo_invalido_exibe_erro_util_sem_traceback(self):
        caminho = self.raiz / 'reports/avaliacao_final_v1/calibracao.csv'
        linhas = caminho.read_text(encoding='utf-8').splitlines()
        campos = linhas[1].split(',')
        campos[1] = 'invalida'
        linhas[1] = ','.join(campos)
        caminho.write_text('\n'.join(linhas) + '\n', encoding='utf-8')
        app.carregar_cacheado.clear()
        self.executar()
        por_chave(self.at.get('radio'), 'tela').set_value('Desempenho')
        self.executar()
        texto = texto_renderizado(self.at).lower()
        self.assertIn('calibracao.csv', texto)
        self.assertIn('restaure', texto)


if __name__ == '__main__':
    unittest.main()
