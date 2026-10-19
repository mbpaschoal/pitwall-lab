"""Dashboard local, somente leitura, do estudo retrospectivo Pitwall Lab."""
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard_dados import (
    DashboardDadosErro,
    carregar_temporada_de_conteudos,
    conteudos_temporada,
    dados_do_gp,
    opcoes_gps,
)

from documentacao_local import renderizar_documentacao_local

RAIZ_PADRAO = Path(__file__).resolve().parent
CORES = {
    'fundo': '#0D1117',
    'superficie': '#171E27',
    'texto': '#EDF0F4',
    'acento': '#E64B44',
    'modelo': '#59CDD1',
    'classificacao': '#F1AE55',
    'neutro': '#AAB5C4',
}


def raiz_artefatos():
    """Gancho interno de teste; no uso normal, a raiz é a do projeto."""
    return Path(os.environ.get('PITWALL_DASHBOARD_ROOT', str(RAIZ_PADRAO)))


@st.cache_data(show_spinner=False)
def carregar_cacheado(temporada, conteudos):
    """Cache somente em memória: bytes participam diretamente da chave."""
    return carregar_temporada_de_conteudos(temporada, conteudos)


def carregar(temporada):
    conteudos = conteudos_temporada(raiz_artefatos(), temporada)
    return carregar_cacheado(temporada, conteudos)


def percentual(valor):
    return '—' if valor is None else '{:.1f}%'.format(valor * 100)


def numero(valor):
    return 'N/A' if valor is None else str(valor)


def nome_temporada(temporada):
    if temporada == 2024:
        return '2024 — validação já explorada'
    return '2025 — avaliação final retrospectiva já realizada'


def conteudo_markdown(atual):
    return '<div class="nota-retrospectiva">Estudo retrospectivo com dados históricos.</div>'


def aplicar_estilo():
    st.markdown(
        '''
        <style>
        :root { color-scheme: dark; }
        .stApp { background: #0D1117; color: #EDF0F4; }
        [data-testid="stSidebar"] { background: #171E27; border-right: 1px solid #273241; }
        [data-testid="stSidebar"] > div { padding-top: 1rem; }
        .pitwall-wordmark { font-size: 1.45rem; font-weight: 800; letter-spacing: .02em; margin: 0 0 .15rem; }
        .pitwall-wordmark span { color: #E64B44; }
        .sidebar-caption { color: #AAB5C4; font-size: .78rem; margin-bottom: 1.25rem; }
        .nota-retrospectiva { border-left: 4px solid #E64B44; background: #171E27; padding: .7rem .9rem; margin: .1rem 0 1.2rem; font-weight: 650; }
        .secao-rotulo { color: #59CDD1; font-size: .8rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
        .stMetric { background: #171E27; border: 1px solid #273241; padding: .55rem .75rem; border-radius: .25rem; }
        .stDataFrame { border: 1px solid #273241; }
        h1, h2, h3 { letter-spacing: -.02em; }
        @media (max-width: 700px) {
          [data-testid="stMetric"] { min-width: 0; }
          .main .block-container { padding-left: .8rem; padding-right: .8rem; }
        }
        </style>
        ''',
        unsafe_allow_html=True,
    )


def tabela_participantes(participantes):
    linhas = []
    for item in participantes:
        situacao = 'Elegível' if item['elegivel_previsao'] else 'Inelegível: {}'.format(item['motivos_inelegibilidade'])
        if item['elegivel_previsao'] and item['podio'] is None:
            situacao += ' · alvo desconhecido'
        linhas.append({
            'Piloto (ID)': item['piloto_id'],
            'Situação': situacao,
            'Probabilidade de pódio': percentual(item['probabilidade_modelo']),
            'Rank do modelo': numero(item['ranking_modelo']),
            'Rank da classificação': numero(item['ranking_classificacao']),
            'Alvo posterior conhecido': 'sim' if item['alvo_conhecido'] else 'não',
        })
    return pd.DataFrame(linhas)


def aviso_favoritos_insuficientes(quantidade):
    if quantidade < 3:
        return 'Aviso: há menos de três favoritos disponíveis neste ranking ({} de 3).'.format(quantidade)
    return ''


def grafico_probabilidades(participantes):
    elegiveis = [item for item in participantes if item['elegivel_previsao']]
    elegiveis.sort(key=lambda item: (item['probabilidade_modelo'], item['piloto_id']))
    if not elegiveis:
        figura = go.Figure()
        figura.add_annotation(
            text='Nenhum participante elegível para exibir probabilidades neste GP.',
            x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False,
            font={'color': CORES['texto'], 'size': 15},
        )
        figura.update_layout(
            height=260, margin={'l': 10, 'r': 20, 't': 25, 'b': 40},
            paper_bgcolor=CORES['fundo'], plot_bgcolor=CORES['fundo'], font={'color': CORES['texto']},
            xaxis={'visible': False}, yaxis={'visible': False}, showlegend=False,
        )
        return figura
    padroes = ['/' if item['favorito_modelo'] else '' for item in elegiveis]
    maior_percentual = max(item['probabilidade_modelo'] * 100 for item in elegiveis)
    figura = go.Figure(go.Bar(
        x=[item['probabilidade_modelo'] * 100 for item in elegiveis],
        y=[item['piloto_id'] for item in elegiveis],
        orientation='h',
        marker={'color': CORES['modelo'], 'pattern': {'shape': padroes, 'fgcolor': CORES['fundo'], 'bgcolor': CORES['modelo'], 'fillmode': 'overlay'}},
        hovertemplate='%{y}: %{x:.1f}%<extra>probabilidade individual de pódio</extra>',
        name='Probabilidade do modelo',
    ))
    figura.update_layout(
        height=max(360, min(620, 28 * len(elegiveis) + 120)),
        margin={'l': 10, 'r': 20, 't': 25, 'b': 40},
        paper_bgcolor=CORES['fundo'], plot_bgcolor=CORES['fundo'], font={'color': CORES['texto']},
        xaxis={'title': 'Probabilidade individual de pódio (%)', 'range': [0, min(100, max(10, maior_percentual * 1.15))]},
        yaxis={'title': 'Piloto (ID)'},
        showlegend=False,
    )
    return figura


def tela_explorar(pacote, rodada):
    bloco = dados_do_gp(pacote, rodada)
    corrida = bloco['corrida']
    participantes = bloco['participantes']
    st.title('Explorar um GP')
    st.caption('{} · rodada {} · {} · {} participantes preparados'.format(
        nome_temporada(pacote['temporada']), corrida['rodada'], corrida['corrida'], corrida['participantes_preparados']
    ))
    st.markdown('<div class="secao-rotulo">Cobertura desta corrida — informação posterior usada só na avaliação</div>', unsafe_allow_html=True)
    cobertura = st.columns(3)
    cobertura[0].metric('Participantes preparados', corrida['participantes_preparados'])
    cobertura[1].metric('Elegíveis para previsão', corrida['elegiveis'])
    cobertura[2].metric('Alvos conhecidos depois', corrida['alvos_conhecidos'])
    st.caption('Participantes preparados: {} · Elegíveis: {} · Alvos conhecidos: {}.'.format(
        corrida['participantes_preparados'], corrida['elegiveis'], corrida['alvos_conhecidos']
    ))
    if corrida['avaliavel_ranking']:
        st.caption('Ranking avaliável: há cobertura completa para pontuar os favoritos depois da corrida.')
    else:
        st.warning('N/A — não avaliável para ranking. Motivo: `{}`. Não há placar zero artificial.'.format(corrida['motivos_nao_avaliavel']))
    st.markdown('<div class="secao-rotulo">Modelo e referências — calculados sem o alvo atual</div>', unsafe_allow_html=True)
    st.subheader('Favoritos por ranking publicado')
    esquerda, direita = st.columns(2)
    with esquerda:
        st.markdown('**Modelo — top 3 por probabilidade**')
        for item in bloco['favoritos_modelo']:
            st.write('#{} · Piloto ({}) · {}'.format(item['ranking_modelo'], item['piloto_id'], percentual(item['probabilidade_modelo'])))
    with direita:
        st.markdown('**Referência de classificação — top 3 por ranking**')
        for item in bloco['favoritos_classificacao']:
            st.write('#{} · Piloto ({})'.format(item['ranking_classificacao'], item['piloto_id']))
        st.caption('A referência é uma ordem por classificação; ela não recebe probabilidade.')
    for ranking, favoritos in (('modelo', bloco['favoritos_modelo']), ('referência de classificação', bloco['favoritos_classificacao'])):
        aviso = aviso_favoritos_insuficientes(len(favoritos))
        if aviso:
            st.warning('{} Ranking: {}.'.format(aviso, ranking))
    st.subheader('Probabilidades de pódio de todos os elegíveis')
    st.caption('Barras hachuradas indicam os três favoritos do modelo; a hachura complementa a cor. % arredondadas apenas para exibição; rank original mantido.')
    st.plotly_chart(grafico_probabilidades(participantes))
    st.subheader('Participantes do GP')
    st.dataframe(tabela_participantes(participantes), width='stretch', hide_index=True)

    st.markdown('<div class="secao-rotulo">Resultados observados — usados depois para avaliação</div>', unsafe_allow_html=True)
    if corrida['avaliavel_ranking']:
        st.markdown('**Integrantes do pódio observado (sem ordem):** {}'.format(', '.join(corrida['podio_observado'])))
        col1, col2 = st.columns(2)
        col1.metric('Acertos — modelo', '{} de 3'.format(corrida['acertos_modelo']))
        col2.metric('Acertos — classificação', '{} de 3'.format(corrida['acertos_classificacao']))
        st.caption('A pontuação ignora a ordem dos três integrantes e só é mostrada com cobertura oficial avaliável.')
    else:
        st.markdown('**N/A — não avaliável.** Motivo: `{}`.'.format(corrida['motivos_nao_avaliavel']))
        alvos_desconhecidos = [item['piloto_id'] for item in participantes if item['podio'] is None]
        inelegiveis = [item['piloto_id'] for item in participantes if not item['elegivel_previsao']]
        if alvos_desconhecidos:
            st.markdown('**Alvo(s) desconhecido(s) no GP:** {}'.format(', '.join(alvos_desconhecidos)))
        if inelegiveis:
            st.markdown('**Participante(s) inelegível(is):** {}'.format(', '.join(inelegiveis)))
        identificados = bloco['integrantes_identificados']
        if identificados:
            st.markdown('**Integrantes identificados na base, sem ordem:** {}'.format(', '.join(identificados)))
        st.caption('O campo de pódio por GP fica vazio nesta cobertura; não há placar zero nem acerto artificial. Os favoritos continuam visíveis acima.')


def tabela_distribuicao(metricas):
    linhas = []
    for acertos in range(4):
        linhas.append({
            'Integrantes corretos': acertos,
            'Modelo (GPs)': metricas['ranking_modelo']['distribuicao_0_1_2_3'][str(acertos)],
            'Classificação (GPs)': metricas['ranking_classificacao']['distribuicao_0_1_2_3'][str(acertos)],
        })
    return pd.DataFrame(linhas)


def grafico_calibracao(calibracao):
    figura = go.Figure()
    configuracoes = {
        'modelo': {'nome': 'Modelo · círculos', 'cor': CORES['modelo'], 'simbolo': 'circle'},
        'constante': {'nome': 'Constante · losangos', 'cor': CORES['classificacao'], 'simbolo': 'diamond'},
    }
    for metodo, estilo in configuracoes.items():
        linhas = [linha for linha in calibracao if linha['metodo'] == metodo and linha['contagem'] > 0]
        figura.add_trace(go.Scatter(
            x=[linha['media_prevista'] for linha in linhas], y=[linha['frequencia_observada'] for linha in linhas],
            mode='lines+markers', name=estilo['nome'],
            marker={'color': estilo['cor'], 'symbol': estilo['simbolo'], 'size': 10},
            line={'color': estilo['cor']},
            customdata=[[linha['faixa'], linha['contagem']] for linha in linhas],
            hovertemplate='Faixa %{customdata[0]} · n=%{customdata[1]}<br>Prevista: %{x:.3f}<br>Observada: %{y:.3f}<extra></extra>',
        ))
    figura.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines', name='Referência perfeita', line={'color': CORES['neutro'], 'dash': 'dot'}))
    figura.update_layout(
        height=460, paper_bgcolor=CORES['fundo'], plot_bgcolor=CORES['fundo'], font={'color': CORES['texto']},
        margin={'l': 10, 'r': 10, 't': 70, 'b': 60},
        legend={'orientation': 'h', 'x': 0, 'y': 1.04, 'yanchor': 'bottom'},
        xaxis={'title': 'Média prevista', 'range': [0, 1]}, yaxis={'title': 'Frequência observada', 'range': [0, 1]},
    )
    return figura


def tabela_calibracao(calibracao):
    linhas = []
    faixas = sorted({(linha['limite_inferior'], linha['limite_superior']) for linha in calibracao})
    for limites in faixas:
        atual = {
            linha['metodo']: linha
            for linha in calibracao
            if (linha['limite_inferior'], linha['limite_superior']) == limites
        }
        modelo, constante = atual['modelo'], atual['constante']
        linhas.append({
            'Faixa': modelo['faixa'],
            'Modelo n': modelo['contagem'],
            'Modelo: média / frequência': '—' if modelo['contagem'] == 0 else '{:.3f} / {:.3f}'.format(modelo['media_prevista'], modelo['frequencia_observada']),
            'Constante n': constante['contagem'],
            'Constante: média / frequência': '—' if constante['contagem'] == 0 else '{:.3f} / {:.3f}'.format(constante['media_prevista'], constante['frequencia_observada']),
        })
    return pd.DataFrame(linhas)


def tela_desempenho(pacote):
    metricas = pacote['metricas']
    cobertura = metricas['cobertura']
    total_prob = metricas['probabilisticas']['linhas_avaliaveis']
    total_gp = metricas['ranking_modelo']['corridas_avaliaveis']
    st.title('Desempenho')
    st.caption('{} · métricas lidas dos artefatos publicados'.format(nome_temporada(pacote['temporada'])))
    st.subheader('Modelo versus constante — probabilidades')
    st.caption('Menor é melhor. As duas métricas usam {} casos elegíveis com alvo conhecido.'.format(total_prob))
    colunas = st.columns(4)
    colunas[0].metric('Log loss · modelo', '{:.4f}'.format(metricas['probabilisticas']['modelo']['log_loss']))
    colunas[1].metric('Log loss · constante', '{:.4f}'.format(metricas['probabilisticas']['constante']['log_loss']))
    colunas[2].metric('Brier · modelo', '{:.4f}'.format(metricas['probabilisticas']['modelo']['brier']))
    colunas[3].metric('Brier · constante', '{:.4f}'.format(metricas['probabilisticas']['constante']['brier']))
    st.caption('Erro menor é melhor, mas não demonstra causalidade nem garante desempenho futuro; Brier menor sozinho não prova calibração melhor.')

    st.subheader('Modelo versus classificação — ranking')
    st.caption('Os métodos usam os mesmos {} GPs avaliáveis de {} GPs presentes.'.format(total_gp, cobertura['gps_total']))
    colunas = st.columns(4)
    colunas[0].metric('Média · modelo', '{:.4f} de 3'.format(metricas['ranking_modelo']['media_integrantes_corretos']))
    colunas[1].metric('Média · classificação', '{:.4f} de 3'.format(metricas['ranking_classificacao']['media_integrantes_corretos']))
    completos_modelo = metricas['ranking_modelo']['distribuicao_0_1_2_3']['3']
    completos_classificacao = metricas['ranking_classificacao']['distribuicao_0_1_2_3']['3']
    colunas[2].metric('Pódios completos · modelo', '{} de {}'.format(completos_modelo, total_gp))
    colunas[3].metric('Pódios completos · classificação', '{} de {}'.format(completos_classificacao, total_gp))
    ganho = metricas['ranking_modelo']['media_integrantes_corretos'] - metricas['ranking_classificacao']['media_integrantes_corretos']
    texto_empate = 'Houve empate em pódios completos.' if completos_modelo == completos_classificacao else 'Os totais de pódios completos diferem.'
    st.caption('Ganho médio descritivo do modelo: {:+.4f} integrante por GP; é pequeno. {} A comparação não é uma garantia futura.'.format(ganho, texto_empate))
    st.dataframe(tabela_distribuicao(metricas), width='stretch', hide_index=True)

    st.subheader('Calibração descritiva')
    st.caption('Eixo x: média prevista. Eixo y: frequência observada. Faixas vazias não viram pontos; a tabela preserva n=0.')
    st.plotly_chart(grafico_calibracao(pacote['calibracao']))
    st.dataframe(tabela_calibracao(pacote['calibracao']), width='stretch', hide_index=True)

    st.subheader('Cobertura e avaliação por GP')
    linhas = []
    for corrida in pacote['corridas']:
        linhas.append({
            'Rodada': corrida['rodada'], 'GP': corrida['corrida'],
            'Participantes': corrida['participantes_preparados'], 'Elegíveis': corrida['elegiveis'],
            'Alvos conhecidos': corrida['alvos_conhecidos'],
            'Modelo': numero(corrida['acertos_modelo']), 'Classificação': numero(corrida['acertos_classificacao']),
            'Motivo de N/A': corrida['motivos_nao_avaliavel'] or '—',
        })
    st.dataframe(pd.DataFrame(linhas), width='stretch', hide_index=True)


def entradas_documentadas():
    caminho = RAIZ_PADRAO / 'docs' / 'experimento_modelo_v1.md'
    try:
        linhas = caminho.read_text(encoding='utf-8').splitlines()
    except OSError:
        return []
    inicio = None
    for indice, linha in enumerate(linhas):
        if linha.strip() == '```text' and indice > 30:
            inicio = indice + 1
            break
    if inicio is None:
        return []
    saida = []
    for linha in linhas[inicio:]:
        if linha.strip() == '```':
            break
        if linha.strip():
            saida.append(linha.strip())
    return saida


def tela_como_funciona():
    entradas = entradas_documentadas()
    st.title('Como funciona')
    st.markdown('**Pergunta do estudo:** estimar a probabilidade individual de um piloto integrar o pódio de um GP principal. Não estima a ordem entre os três integrantes.')
    st.subheader('Método histórico')
    st.write('Regressão logística com treino em 2021–2023, validação de 2024 já explorada e avaliação retrospectiva de 2025 já realizada. A classificação é uma referência de ranking distinta do grid registrado depois; ela não é uma probabilidade.')
    st.write('As 15 entradas documentadas cobrem a classificação, o histórico recente do piloto, o histórico recente da equipe e indicadores de ausência. A lista abaixo vem do documento do método; o app não inventa estatísticas novas.')
    st.write('Células numéricas ausentes foram preenchidas com medianas aprendidas somente no treino elegível e rotulado. Depois, a escala também foi aprendida somente nesse treino e ficou congelada para 2024 e 2025.')
    st.write('Regra exata de elegibilidade: classificação presente e referência temporal disponível. Posição de classificação ausente e histórico insuficiente não excluem o piloto: os indicadores de ausência são preservados e o pipeline congelado trata essas lacunas. Alvo ausente continua desconhecido e não participa da avaliação.')
    st.write('Probabilidades individuais não são forçadas a somar três dentro de um GP.')
    st.subheader('{} entradas documentadas'.format(len(entradas)))
    st.code('\n'.join(entradas) if entradas else 'Lista indisponível no documento local.', language=None)
    st.caption('São associações no recorte histórico, não relações causais. O estudo tem poucas temporadas, participantes dependentes dentro de cada GP e fontes que podem ter revisões posteriores.')
    st.subheader('Fonte e limites')
    st.write('Dados públicos Jolpica-F1, sob CC BY-NC-SA 4.0. O aplicativo não consulta essa fonte: mostra somente os artefatos locais já calculados.')
    st.info('Resultados retrospectivos não demonstram desempenho futuro e não são uma previsão ao vivo ou da próxima corrida.')
    renderizar_documentacao_local(st)


def executar_app():
    st.set_page_config(page_title='Pitwall Lab', page_icon='🏁', layout='wide', initial_sidebar_state='expanded')
    aplicar_estilo()
    st.sidebar.markdown('<div class="pitwall-wordmark">Pitwall<span>Lab</span></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="sidebar-caption">Estudo retrospectivo de pódios na Fórmula 1</div>', unsafe_allow_html=True)
    tela = st.sidebar.radio('Navegação', ('Explorar um GP', 'Desempenho', 'Como funciona'), key='tela')
    temporada = st.sidebar.selectbox('Temporada', (2024, 2025), index=1, format_func=nome_temporada, key='temporada')
    try:
        pacote = carregar(temporada)
    except DashboardDadosErro as erro:
        st.error(str(erro))
        st.stop()
    anterior = st.session_state.get('_temporada_anterior_dashboard')
    if anterior != temporada:
        st.session_state.pop('gp', None)
        st.session_state['_temporada_anterior_dashboard'] = temporada
    opcoes = opcoes_gps(pacote)
    valores = [item['valor'] for item in opcoes]
    descricoes = {item['valor']: '{:02d} — {}'.format(item['rodada'], item['corrida']) for item in opcoes}
    st.sidebar.caption('Desempenho agrega toda a temporada; o filtro de GP aplica-se apenas em Explorar um GP.')
    gp = st.sidebar.selectbox(
        'Grande Prêmio', valores, format_func=lambda valor: descricoes.get(valor, str(valor)), key='gp',
        disabled=tela != 'Explorar um GP',
    )
    if gp not in descricoes:
        por_descricao = {descricao: valor for valor, descricao in descricoes.items()}
        gp = por_descricao.get(gp, valores[0])
    rodada = int(gp.split(':', 1)[1])
    st.markdown(conteudo_markdown(pacote), unsafe_allow_html=True)
    if tela == 'Explorar um GP':
        tela_explorar(pacote, rodada)
    elif tela == 'Desempenho':
        tela_desempenho(pacote)
    else:
        tela_como_funciona()


if __name__ == '__main__':
    executar_app()
