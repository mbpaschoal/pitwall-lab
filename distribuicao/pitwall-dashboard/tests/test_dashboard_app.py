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
    asset = RAIZ / 'frontend_assets/race_weekend.json'
    destino_asset = raiz / 'frontend_assets/race_weekend.json'
    destino_asset.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(asset, destino_asset)
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
        self.assertEqual(radio.value, 'Corridas')
        self.assertIn('Estudo retrospectivo com dados históricos.', texto_renderizado(self.at))
        self.assertEqual(por_chave(self.at.get('selectbox'), 'temporada').value, 2025)
        self.assertEqual(por_chave(self.at.get('selectbox'), 'gp').value, '2025:1')

        radio.set_value('Desempenho')
        self.executar()
        texto = texto_renderizado(self.at)
        self.assertIn('Acertos entre os três escolhidos', texto)
        self.assertIn('478', texto)

        radio = por_chave(self.at.get('radio'), 'tela')
        radio.set_value('Metodologia')
        self.executar()
        texto = texto_renderizado(self.at)
        self.assertIn('15 entradas', texto)
        self.assertIn('CC BY-NC-SA 4.0', texto)

    def test_gp_fica_desabilitado_fora_da_exploracao_sem_desabilitar_temporada(self):
        self.executar()
        gp_inicial = por_chave(self.at.get('selectbox'), 'gp').value
        radio = por_chave(self.at.get('radio'), 'tela')

        for tela in ('Desempenho', 'Metodologia'):
            radio.set_value(tela)
            self.executar()
            seletor_gp = por_chave(self.at.get('selectbox'), 'gp')
            seletor_temporada = por_chave(self.at.get('selectbox'), 'temporada')
            self.assertTrue(seletor_gp.disabled)
            self.assertEqual(seletor_gp.value, gp_inicial)
            self.assertFalse(seletor_temporada.disabled)
            self.assertIn('aplica-se em Corridas e Previsões', texto_renderizado(self.at))

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
        self.assertIn('Temporada 2025', texto)
        self.assertIn('Cobertura:', texto)
        self.assertIn('participantes preparados', texto)
        self.assertIn('elegíveis', texto)
        self.assertIn('alvos conhecidos', texto)
        self.assertIn('N/A — não avaliável', texto)
        self.assertLess(texto.index('Cobertura:'), texto.index('Probabilidades de pódio'))
        self.assertIn('menos de três favoritos', app.aviso_favoritos_insuficientes(2).lower())

    def test_como_funciona_expoe_regras_congeladas_e_links_dos_dois_relatorios(self):
        self.executar()
        radio = por_chave(self.at.get('radio'), 'tela')
        radio.set_value('Metodologia')
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

    def test_2026_abre_no_ultimo_gp_observado_com_nomes_equipes_e_resultado(self):
        self.executar()
        self.escolher('temporada', 2026)
        self.assertEqual(por_chave(self.at.get('selectbox'), 'gp').value, '2026:17')
        texto = texto_renderizado(self.at)
        self.assertIn('Max Verstappen', texto)
        self.assertIn('Red Bull', texto)
        self.assertIn('Previsão e resultado observado', texto)
        self.assertNotIn('Max Verstappen (max_verstappen)', texto)

    def test_2026_com_resultado_observado_nao_afirma_que_o_podio_esta_vazio(self):
        self.executar()
        self.escolher('temporada', 2026)
        texto = texto_renderizado(self.at)
        self.assertIn('Integrantes identificados na base, sem ordem:', texto)
        self.assertIn('não há avaliação prospectiva oficial ou anual', texto.lower())
        self.assertNotIn('O campo de pódio por GP fica vazio nesta cobertura', texto)

    def test_2026_separa_campeonato_local_das_probabilidades_do_gp(self):
        self.executar()
        self.escolher('temporada', 2026)
        por_chave(self.at.get('radio'), 'tela').set_value('Previsões')
        self.executar()
        texto = texto_renderizado(self.at)
        self.assertIn('Classificação de pilotos 2026', texto)
        self.assertIn('Rodada de referência: 17', texto)
        self.assertIn('DriverStandings Jolpica-F1, separado das probabilidades por GP.', texto)
        campeonato = app.carregar(2026)['campeonato_pilotos']
        self.assertIn('Vitórias', app.tabela_campeonato_pilotos(campeonato).columns)
        self.assertIn('Max Verstappen', texto)

    def test_renderizar_campeonato_driverstandings_mostra_max_em_p4_sem_probabilidades(self):
        campeonato = app.carregar(2026)['campeonato_pilotos']
        with patch.object(app, 'st') as st_local:
            app.renderizar_campeonato_pilotos({'campeonato_pilotos': campeonato})
        tabela = st_local.dataframe.call_args.args[0]
        max_verstappen = tabela[tabela['Piloto'] == 'Max Verstappen'].iloc[0]
        self.assertEqual((max_verstappen['Posição'], max_verstappen['Pontos'], max_verstappen['Vitórias']), (4, 221.0, 2))
        self.assertNotIn('Probabilidade de pódio', tabela.columns)

    def test_renderizar_campeonato_schema_ausente_mostra_indisponibilidade_sem_traceback(self):
        with patch.object(app, 'st') as st_local:
            app.renderizar_campeonato_pilotos({'campeonato_pilotos': {}})
        st_local.info.assert_called_once_with('Classificação de pilotos indisponível.')
        st_local.dataframe.assert_not_called()

    def test_austin_sem_emissao_nao_reusa_ensaio_de_singapura_nem_mostra_favoritos(self):
        self.executar()
        self.escolher('temporada', 2026)
        por_chave(self.at.get('radio'), 'tela').set_value('Previsões')
        self.executar()
        self.escolher('gp', '2026:18')
        texto = texto_renderizado(self.at)
        self.assertIn('United States Grand Prix', texto)
        self.assertIn('Austin, USA · 2026-10-25', texto)
        self.assertIn('Aguardando dados', texto)
        self.assertIn('Faltam classificação concluída e emissão prospectiva registrada para este GP.', texto)
        self.assertNotIn('Favoritos por ranking publicado', texto)
        self.assertNotIn('76.0%', texto)
        self.assertNotIn('Max Verstappen · Red Bull · 76.0%', texto)

    def test_visual_editorial_usa_fontes_locais_abril_e_lato_sem_gradiente(self):
        css = app.estilo_dashboard()
        self.assertIn('AbrilFatfaceLocal', css)
        self.assertIn('LatoLocal', css)
        self.assertIn('stIconMaterial', css)
        self.assertNotIn('gradient', css.lower())
        self.assertTrue((RAIZ / 'dashboard_assets/fonts/abrilfatface.ttf').is_file())
        self.assertTrue((RAIZ / 'dashboard_assets/fonts/lato.ttf').is_file())

    def test_corridas_austin_exibe_contexto_programacao_e_estado_aguardando_dados(self):
        self.executar()
        self.escolher('temporada', 2026)
        self.escolher('gp', '2026:18')
        texto = texto_renderizado(self.at)
        self.assertEqual(list(por_chave(self.at.get('selectbox'), 'temporada').options), ['2024', '2025', '2026'])
        self.assertIn('United States Grand Prix', texto)
        self.assertIn('Austin, USA · 2026-10-25', texto)
        self.assertIn('Contexto do GP', texto)
        self.assertIn('Traçado do circuito indisponível no snapshot local.', texto)
        self.assertIn('Programação do fim de semana', texto)
        self.assertIn('Classificação de pilotos 2026', texto)
        self.assertIn('Desempenho das equipes', texto)
        self.assertIn('Dados de desempenho por equipe indisponíveis no snapshot local.', texto)
        self.assertIn('Estado dos dados', texto)
        self.assertIn('Aguardando dados', texto)
        self.assertNotIn('76.0%', texto)

    def test_corridas_austin_tem_hierarquia_editorial_e_navegacao_secundaria_completa(self):
        self.executar()
        self.escolher('temporada', 2026)
        self.escolher('gp', '2026:18')
        texto = texto_renderizado(self.at)
        for rotulo in ('Contexto do circuito', 'Informações do circuito', 'Condições disponíveis'):
            self.assertIn(rotulo, texto)
        codigo = (RAIZ / 'app.py').read_text(encoding='utf-8')
        for aba in ('Visão geral', 'Tempos', 'Estratégias', 'Clima', 'Histórico', 'Comparativo de equipes'):
            self.assertIn(aba, codigo)
        self.assertIn('Dados meteorológicos indisponíveis no snapshot local.', texto)
        self.assertIn('Aguardando dados', texto)
        self.assertNotIn('Previsão disponível: 76.0%', texto)

        css = app.estilo_dashboard()
        self.assertIn('gp-cabecalho', css)
        self.assertIn('tabela-editorial', css)
        self.assertIn('barra-equipe', css)

        campeonato = app.carregar(2026)['campeonato_pilotos']
        tabela = app.tabela_campeonato_editorial(campeonato)
        self.assertIn('Max Verstappen', tabela)
        self.assertIn('barra-equipe', tabela)
        self.assertIn('Pontos', tabela)

    def test_rotulo_resultado_distingue_podio_pontos_abandono_e_desclassificacao(self):
        self.assertEqual(app.rotulo_resultado(2, 'Finished'), 'Pódio')
        self.assertEqual(app.rotulo_resultado(8, 'Finished'), 'Pontuou fora do pódio')
        self.assertEqual(app.rotulo_resultado(14, 'Retired'), 'Abandono')
        self.assertEqual(app.rotulo_resultado(18, 'Disqualified'), 'Desclassificação')

    def test_calendario_2026_usa_corridas_locais_e_marca_gp_selecionado_sem_afetar_2025(self):
        self.executar()
        self.escolher('temporada', 2026)
        self.escolher('gp', '2026:18')
        texto = texto_renderizado(self.at)
        self.assertIn('Calendário 2026', texto)
        calendario = app.tabela_calendario_2026(app.carregar(2026), 18)
        austin = calendario[calendario['Rodada'] == 18].iloc[0]
        self.assertEqual(austin['GP'], 'United States Grand Prix')
        self.assertEqual(austin['Selecionado'], 'sim')

        self.escolher('temporada', 2025)
        self.assertNotIn('Calendário 2026', texto_renderizado(self.at))

    def test_desempenho_prioriza_acertos_e_mantem_metricas_tecnicas_no_expander(self):
        self.executar()
        por_chave(self.at.get('radio'), 'tela').set_value('Desempenho')
        self.executar()
        texto = texto_renderizado(self.at)
        self.assertIn('Acertos entre os três escolhidos', texto)
        self.assertIn('Pódios completos acertados', texto)
        self.assertIn('Acerto dos três integrantes do pódio, independentemente da ordem', texto)
        self.assertIn('Comparação com a classificação', texto)
        self.assertIn('22 de 24 GPs', texto)
        self.assertEqual(
            [(item.label, item.value) for item in self.at.get('metric')],
            [('Modelo', '2.32 de 3'), ('Classificação', '2.27 de 3'),
             ('Modelo', '8 de 22 GPs'), ('Classificação', '8 de 22 GPs')],
        )
        self.assertTrue(any('Detalhes técnicos' in str(item.label) for item in self.at.get('expander')))

    def test_corridas_e_previsoes_priorizam_blocos_distintos_sem_trocar_o_gp(self):
        self.executar()
        self.escolher('temporada', 2026)
        self.assertEqual(por_chave(self.at.get('selectbox'), 'gp').value, '2026:17')
        corridas = texto_renderizado(self.at)
        self.assertIn('Contexto do GP e resultado observado', corridas)
        self.assertLess(corridas.index('Resultados observados'), corridas.index('Modelo e referências'))
        self.assertIn('ensaio retrospectivo', corridas.lower())

        por_chave(self.at.get('radio'), 'tela').set_value('Previsões')
        self.executar()
        previsoes = texto_renderizado(self.at)
        self.assertEqual(por_chave(self.at.get('selectbox'), 'gp').value, '2026:17')
        self.assertIn('Probabilidades e estado da previsão', previsoes)
        self.assertLess(previsoes.index('Modelo e referências'), previsoes.index('Resultados observados'))
        self.assertIn('ensaio retrospectivo', previsoes.lower())

        self.escolher('gp', '2026:18')
        self.assertEqual(por_chave(self.at.get('selectbox'), 'gp').value, '2026:18')
        self.assertIn('N/A — não avaliável', texto_renderizado(self.at))

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
