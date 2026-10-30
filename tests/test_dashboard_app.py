"""AppTest da etapa 6: usa uma cópia temporária de reports/, sem data/ ou modelos."""
import os
import re
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
    destino_asset = raiz / 'frontend_assets'
    destino_asset.mkdir(parents=True, exist_ok=True)
    for nome in ('race_weekend.json', 'contexto_editorial.json', 'paineis_editoriais.json'):
        shutil.copy2(RAIZ / 'frontend_assets' / nome, destino_asset / nome)
    shutil.copytree(RAIZ / 'dashboard_assets' / 'circuit', raiz / 'dashboard_assets' / 'circuit')
    return raiz


def por_chave(elementos, chave):
    return next(elemento for elemento in elementos if elemento.key == chave)


def texto_renderizado(at):
    partes = []
    for tipo in ('markdown', 'text', 'caption', 'title', 'header', 'subheader', 'info', 'warning', 'error'):
        for elemento in at.get(tipo):
            valor = str(getattr(elemento, 'value', elemento))
            if not valor.startswith('<style>'):
                partes.append(re.sub(r'data:[^;]+;base64,[A-Za-z0-9+/=]+', 'ativo-local', valor))
    return '\n'.join(partes)


class TestDashboardApp(unittest.TestCase):
    def test_busca_local_navega_gp_e_preferencias_abrem_fontes(self):
        self.executar()
        busca = por_chave(self.at.get('text_input'), 'busca_local')
        busca.set_value('Austin')
        self.executar()
        botao = por_chave(self.at.get('button'), 'busca_gp_2025:19')
        botao.click()
        self.executar()
        self.assertEqual(por_chave(self.at.get('selectbox'), 'gp').value, '2025:19')
        self.assertIn('United States Grand Prix', texto_renderizado(self.at))
        por_chave(self.at.get('checkbox'), 'mostrar_fontes').check()
        self.executar()
        self.assertTrue(self.at.session_state['mostrar_fontes'])

    def test_link_de_campeonato_preserva_temporada_gp_e_abre_tabela(self):
        self.at.query_params.update({'temporada':'2026', 'gp':'18', 'painel':'equipes'})
        self.executar()
        self.assertEqual(por_chave(self.at.get('selectbox'), 'temporada').value, 2026)
        self.assertEqual(por_chave(self.at.get('selectbox'), 'gp').value, '2026:18')
        texto = texto_renderizado(self.at)
        self.assertIn('607', texto)
        self.assertIn('equipes-completo', texto)
        self.assertFalse(any('Session State API' in str(w.value) for w in self.at.warning))

    def test_query_invalida_e_limpeza_dos_filtros_nao_derrubam_app(self):
        self.at.query_params.update({'temporada':'2026', 'gp':'²'})
        self.executar()
        self.assertEqual(por_chave(self.at.get('selectbox'), 'temporada').value, 2025)
        self.escolher('temporada', None)
        self.assertEqual(por_chave(self.at.get('selectbox'), 'temporada').value, 2025)
        self.escolher('gp', None)
        self.assertEqual(por_chave(self.at.get('selectbox'), 'gp').value, '2025:1')

    def test_estado_prospectivo_prioriza_previsao_sem_resultado(self):
        corrida = {
            'estado_resultado': 'indisponivel', 'estado_previsao': 'previsao_registrada',
            'estado_qualificacao': 'local_disponivel', 'estado_operacao': 'previsao_registrada',
        }
        self.assertEqual(app.situacao_corrida(corrida), 'Previsão registrada')

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

    def test_corridas_compartilham_cabecalho_editorial_e_contexto_nas_tres_temporadas(self):
        self.executar()
        casos = (
            (2024, '2024:1', 'Bahrain Grand Prix', 'Sakhir, Bahrain · 2024-03-02'),
            (2025, '2025:1', 'Australian Grand Prix', 'Melbourne, Australia · 2025-03-16'),
            (2026, '2026:18', 'United States Grand Prix', 'Austin, USA · 2026-10-25'),
        )
        for temporada, gp, corrida, meta in casos:
            self.escolher('temporada', temporada)
            self.escolher('gp', gp)
            texto = texto_renderizado(self.at)
            self.assertIn(corrida, texto)
            self.assertIn(meta, texto)
            for rotulo in ('Foto do circuito', 'Mapa do circuito', 'Informações do circuito', 'Visão geral'):
                self.assertIn(rotulo, texto)

    def test_gp_filter_hidden_where_it_does_not_apply(self):
        self.executar()
        gp = por_chave(self.at.selectbox, 'gp').value
        for tela in ('Desempenho', 'Metodologia'):
            por_chave(self.at.radio, 'tela').set_value(tela)
            self.executar()
            self.assertFalse(any(x.key == 'gp' for x in self.at.selectbox))
            self.assertFalse(por_chave(self.at.selectbox, 'temporada').disabled)
        por_chave(self.at.radio, 'tela').set_value('Corridas')
        self.executar()
        self.assertEqual(por_chave(self.at.selectbox, 'gp').value, gp)

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
        por_chave(self.at.radio, 'tela').set_value('Previsões')
        self.executar()
        self.escolher('gp', '2025:9')
        texto = texto_renderizado(self.at)
        self.assertIn('Temporada 2025', texto)
        self.assertIn('Cobertura:', texto)
        self.assertIn('participantes preparados', texto)
        self.assertIn('elegíveis', texto)
        self.assertIn('alvos conhecidos', texto)
        self.assertIn('N/A — não avaliável', texto)
        self.assertLess(texto.index('Cobertura:'), texto.index('Chances de pódio'))
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
                self.assertIn('Ver previsões deste GP', texto_renderizado(self.at))
                self.assertNotIn('Quem tinha mais chance de pódio', texto_renderizado(self.at))
                seletor_gp = por_chave(self.at.get('selectbox'), 'gp')

    def test_espanha_e_sao_paulo_2025_exibem_na_motivo_unknown_e_inelegivel(self):
        self.executar()
        self.escolher('temporada', 2025)
        por_chave(self.at.radio, 'tela').set_value('Previsões')
        self.executar()
        self.escolher('gp', '2025:9')
        texto = texto_renderizado(self.at).lower()
        self.assertIn('n/a', texto)
        self.assertIn('alvo desconhecido', texto)
        self.assertIn('stroll', texto)
        self.escolher('gp', '2025:21')
        texto = texto_renderizado(self.at).lower()
        self.assertIn('n/a', texto)
        self.assertIn('participante inelegivel', texto)
        self.assertIn('bortoleto', texto)

    def test_execucao_app_nao_chama_socket_e_nao_importa_joblib(self):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('rede externa proibida')):
            self.executar()
        fontes = Path(app.__file__).read_text(encoding='utf-8').lower()
        self.assertNotIn('joblib', fontes)
        self.assertNotIn('sklearn', fontes)

    def test_2026_abre_no_ultimo_gp_observado_com_nomes_equipes_e_resultado(self):
        self.executar()
        self.escolher('temporada', 2026)
        self.assertEqual(por_chave(self.at.get('selectbox'), 'gp').value, '2026:18')
        texto = texto_renderizado(self.at)
        self.assertIn('Max Verstappen', texto)
        self.assertIn('Red Bull', texto)
        self.assertNotIn('Previsão e resultado observado', texto)
        self.assertIn('Integrantes do pódio observado', texto)
        self.assertNotIn('Max Verstappen (max_verstappen)', texto)

    def test_historico_sem_acervo_nao_reutiliza_podio_da_corrida_atual(self):
        self.executar()
        self.escolher('temporada', 2026)
        historico=next(tab for tab in self.at.tabs if tab.label=='Nesta pista')
        texto=texto_renderizado(historico)
        self.assertIn('Não há corrida anterior nesta pista', texto)
        self.assertNotIn('Integrantes do pódio observado', texto)
        tempos=next(tab for tab in self.at.tabs if tab.label=='Sessões e voltas')
        self.assertIn('Integrantes do pódio observado', texto_renderizado(tempos))

    def test_2026_com_resultado_observado_nao_afirma_que_o_podio_esta_vazio(self):
        self.executar()
        self.escolher('temporada', 2026)
        texto = texto_renderizado(self.at)
        self.assertIn('Integrantes do pódio observado (sem ordem):', texto)
        self.assertNotIn('Previsão registrada antes da corrida.', texto)
        self.assertNotIn('O campo de pódio por GP fica vazio nesta cobertura', texto)

    def test_2026_separa_campeonato_local_das_probabilidades_do_gp(self):
        self.executar()
        self.escolher('temporada', 2026)
        por_chave(self.at.get('radio'), 'tela').set_value('Previsões')
        self.executar()
        texto = texto_renderizado(self.at)
        self.assertNotIn('Campeonato de pilotos', texto)
        self.assertIn('Ver campeonato completo', texto)
        self.assertIn('Quem tinha mais chance de pódio', texto)
        campeonato = app.carregar(2026)['campeonato_pilotos']
        self.assertIn('Vitórias', app.tabela_campeonato_pilotos(campeonato).columns)
        self.assertIn('Max Verstappen', texto)

    def test_renderizar_campeonato_driverstandings_mostra_max_em_p4_sem_probabilidades(self):
        campeonato = app.carregar(2026)['campeonato_pilotos']
        with patch.object(app, 'st') as st_local:
            app.renderizar_campeonato_pilotos({'campeonato_pilotos': campeonato})
        tabela = st_local.dataframe.call_args.args[0]
        max_verstappen = tabela[tabela['Piloto'] == 'Max Verstappen'].iloc[0]
        self.assertEqual((max_verstappen['Posição'], max_verstappen['Pontos'], max_verstappen['Vitórias']), (4, 236.0, 2))
        self.assertNotIn('Probabilidade de pódio', tabela.columns)

    def test_renderizar_campeonato_schema_ausente_mostra_indisponibilidade_sem_traceback(self):
        with patch.object(app, 'st') as st_local:
            app.renderizar_campeonato_pilotos({'campeonato_pilotos': {}})
        st_local.info.assert_called_once_with('Classificação de pilotos indisponível.')
        st_local.dataframe.assert_not_called()

    def test_austin_com_emissao_openf1_mostra_favoritos_da_emissao(self):
        self.executar()
        self.escolher('temporada', 2026)
        por_chave(self.at.get('radio'), 'tela').set_value('Previsões')
        self.executar()
        self.escolher('gp', '2026:18')
        texto = texto_renderizado(self.at)
        self.assertIn('United States Grand Prix', texto)
        self.assertIn('Austin, USA · 2026-10-25', texto)
        self.assertIn('Previsão registrada', texto)
        self.assertIn('Quem tinha mais chance de pódio', texto)
        self.assertIn('Andrea Kimi Antonelli · Mercedes · 83.5%', texto)
        self.assertIn('Previsão registrada antes da corrida.', texto)
        self.assertNotIn('Estudo retrospectivo com dados históricos.', texto)
        self.assertNotIn('Max Verstappen · Red Bull · 76.0%', texto)

        pacote = app.carregar(2026)
        identidade_fonte = pacote['asset_race_weekend']['identidades']['2026:18:antonelli']
        self.assertEqual(identidade_fonte['piloto'], 'Kimi Antonelli')
        figura = app.grafico_probabilidades(pacote, app.dados_do_gp_2026(pacote, 18)['participantes'])
        self.assertIn('Andrea Kimi Antonelli', figura.data[0].y)

        self.escolher('gp', '2026:17')
        texto = texto_renderizado(self.at)
        self.assertIn('Estudo retrospectivo com dados históricos.', texto)
        self.assertNotIn('Previsão registrada antes da corrida.', texto)

    def test_visual_editorial_usa_fontes_locais_e_sobreposicao_legivel(self):
        css = app.estilo_dashboard()
        self.assertIn('AbrilFatfaceLocal', css)
        self.assertIn('LatoLocal', css)
        self.assertIn('stIconMaterial', css)
        self.assertIn('linear-gradient(transparent', css.lower())
        self.assertTrue((RAIZ / 'dashboard_assets/fonts/abrilfatface.ttf').is_file())
        self.assertTrue((RAIZ / 'dashboard_assets/fonts/lato.ttf').is_file())

    def test_menu_lateral_mantem_controle_nativo_e_adapta_ao_viewport(self):
        codigo = Path(app.__file__).read_text(encoding='utf-8')
        css = app.estilo_dashboard()
        self.assertRegex(codigo, "initial_sidebar_state=[\"']auto[\"']")
        self.assertNotIn('header[data-testid="stHeader"] { display: none; }', css)

    def test_corridas_austin_exibe_contexto_programacao_e_previsao_registrada(self):
        self.executar()
        self.escolher('temporada', 2026)
        self.escolher('gp', '2026:18')
        texto = texto_renderizado(self.at)
        self.assertEqual(list(por_chave(self.at.get('selectbox'), 'temporada').options), ['2024', '2025', '2026'])
        self.assertIn('United States Grand Prix', texto)
        self.assertIn('Austin, USA · 2026-10-25', texto)
        self.assertIn('Ver previsões deste GP', texto)
        self.assertIn('Mapa do circuito', texto)
        self.assertIn('Mapa:', texto)
        self.assertIn('CC BY-SA 4.0', texto)
        self.assertIn('Programação do fim de semana', texto)
        self.assertNotIn('Campeonato de pilotos', texto)
        self.assertNotIn('Campeonato de construtores', texto)
        self.assertNotIn('Campeonato de construtores', texto)
        self.assertNotIn('Estado dos dados', texto)
        self.assertIn('Resultado observado', texto)
        self.assertNotIn('83.5%', texto)

    def test_corridas_austin_tem_hierarquia_editorial_e_navegacao_secundaria_completa(self):
        self.executar()
        self.escolher('temporada', 2026)
        self.escolher('gp', '2026:18')
        texto = texto_renderizado(self.at)
        for rotulo in ('Foto do circuito', 'Informações do circuito', 'Clima'):
            self.assertIn(rotulo, texto)
        codigo = Path(app.__file__).read_text(encoding='utf-8')
        for aba in ('Resumo', 'Sessões e voltas', 'Pneus e paradas', 'Clima', 'Nesta pista', 'Equipes'):
            self.assertIn(aba, codigo)
        self.assertIn('Clima não disponível', texto)
        self.assertIn('Resultado observado', texto)
        self.assertNotIn('Andrea Kimi Antonelli · Mercedes · 83.5%', texto)
        self.assertNotIn('Previsão registrada antes da corrida.', texto)
        self.assertNotIn('Estudo retrospectivo com dados históricos.', texto)

        css = app.estilo_dashboard()
        self.assertIn('gp-cabecalho', css)
        self.assertIn('tabela-editorial', css)
        self.assertIn('barra-equipe', css)
        self.assertIn('.st-key-topbar', css)
        self.assertIn('max-width:none', css)
        self.assertIn('height:375px', css)

        campeonato = app.carregar(2026)['campeonato_pilotos']
        tabela = app.tabela_campeonato_editorial(campeonato)
        self.assertIn('Max Verstappen', tabela)
        self.assertIn('barra-equipe', tabela)
        self.assertIn('Pontos', tabela)

    def test_visao_geral_austin_usa_foto_e_mapa_locais_com_atribuicao(self):
        self.executar()
        self.escolher('temporada', 2026)
        self.escolher('gp', '2026:18')
        texto = texto_renderizado(self.at)
        self.assertIn('Foto do circuito', texto)
        self.assertIn('Mapa do circuito', texto)
        self.assertIn('5,513 km', texto)
        self.assertIn('Anti-horário', texto)
        css = app.estilo_dashboard()
        self.assertIn('hero-circuito', css)
        self.assertIn('mapa-circuito', css)
        self.assertTrue((RAIZ / 'dashboard_assets/circuit/americas-illustration-20261027.png').is_file())
        self.assertTrue((RAIZ / 'dashboard_assets/circuit/americas-outline.svg').is_file())
        catalogo = (RAIZ / 'dashboard_assets/circuit/catalogo_visual.json').read_text(encoding='utf-8')
        self.assertIn('americas-illustration-20261027.png', catalogo)
        self.assertIn('Ilustração gerada por IA', texto)
        self.assertIn('americas-outline.svg', catalogo)
        atribuicoes = (RAIZ / 'dashboard_assets/circuit/ATRIBUICOES.md').read_text(encoding='utf-8')
        self.assertIn('CC BY 2.0', atribuicoes)
        self.assertIn('CC BY-SA 4.0', atribuicoes)

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
        self.assertEqual(por_chave(self.at.selectbox, 'gp').value, '2026:18')
        corridas = texto_renderizado(self.at)
        self.assertNotIn('Campeonato de pilotos', corridas)
        self.assertIn('Integrantes do pódio observado', corridas)
        self.assertNotIn('Quem tinha mais chance de pódio', corridas)
        self.assertNotIn('Previsão e resultado observado', corridas)
        por_chave(self.at.radio, 'tela').set_value('Previsões')
        self.executar()
        previsoes = texto_renderizado(self.at)
        self.assertEqual(por_chave(self.at.selectbox, 'gp').value, '2026:18')
        self.assertIn('Quem tinha mais chance de pódio', previsoes)
        self.assertIn('Avaliação posterior desta previsão registrada', previsoes)
        self.assertNotIn('Campeonato de pilotos', previsoes)
        self.assertNotIn('Informações do circuito', previsoes)


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
