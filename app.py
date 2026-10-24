"""Dashboard local, somente leitura, do estudo retrospectivo Pitwall Lab."""
import os
import base64
from html import escape
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
from race_weekend_dados import (
    RaceWeekendDadosErro,
    carregar_asset,
    dados_do_gp_2026,
    identidade,
    pacote_2026,
)

RAIZ_PADRAO = Path(__file__).resolve().parent
CORES = {
    'fundo': '#F2F6FA', 'superficie': '#FFFFFF', 'texto': '#132B4F',
    'acento': '#D62732', 'modelo': '#2475EF', 'classificacao': '#132B4F', 'neutro': '#B7BEC8',
}
CORES_EQUIPE = {
    'ferrari': '#E53935', 'red_bull': '#183153', 'mercedes': '#00A19B',
    'mclaren': '#F58020', 'aston_martin': '#006F62', 'alpine': '#2475EF',
    'williams': '#2475EF', 'haas': '#FFFFFF', 'sauber': '#168A4A', 'audi': '#B7BEC8',
    'rb': '#2475EF', 'racing_bulls': '#2475EF',
}


def raiz_artefatos():
    """Gancho interno de teste; no uso normal, a raiz é a do projeto."""
    return Path(os.environ.get('PITWALL_DASHBOARD_ROOT', str(RAIZ_PADRAO)))


@st.cache_data(show_spinner=False)
def carregar_cacheado(temporada, conteudos):
    """Cache somente em memória: bytes participam diretamente da chave."""
    return carregar_temporada_de_conteudos(temporada, conteudos)


def carregar(temporada):
    if temporada == 2026:
        asset = carregar_asset(raiz_artefatos())
        pacote = pacote_2026(asset)
        pacote['asset_race_weekend'] = asset
        return pacote
    conteudos = conteudos_temporada(raiz_artefatos(), temporada)
    pacote = carregar_cacheado(temporada, conteudos)
    try:
        pacote['asset_race_weekend'] = carregar_asset(raiz_artefatos())
    except RaceWeekendDadosErro:
        pacote['asset_race_weekend'] = None
    return pacote


def percentual(valor):
    return '—' if valor is None else '{:.1f}%'.format(valor * 100)


def numero(valor):
    return 'N/A' if valor is None else str(valor)


def nome_temporada(temporada):
    if temporada == 2024:
        return '2024 — validação já explorada'
    if temporada == 2025:
        return '2025 — avaliação final retrospectiva já realizada'
    return '2026 — snapshots locais, cobertura parcial'


def nome_piloto(pacote, item):
    asset = pacote.get('asset_race_weekend')
    if asset:
        return identidade(asset, pacote['temporada'], item['rodada'], item['piloto_id'])['piloto']
    return 'Nome indisponível ({})'.format(item['piloto_id'])


def identidade_piloto(pacote, item):
    """Nome e equipe contextualizados pela temporada e rodada do GP."""
    asset = pacote.get('asset_race_weekend')
    if asset:
        return identidade(asset, pacote['temporada'], item['rodada'], item['piloto_id'])
    return {'piloto': nome_piloto(pacote, item), 'equipe_id': item.get('equipe_id'), 'equipe': item.get('equipe')}


def nome_equipe(pacote, item):
    dados = identidade_piloto(pacote, item)
    return dados['equipe'] or 'Equipe indisponível'


def conteudo_markdown(atual):
    return '<div class="nota-retrospectiva">Estudo retrospectivo com dados históricos.</div>'


def ativo_data_uri(caminho_relativo, mime):
    """Carrega um ativo local para o HTML sem depender de rede em produção."""
    try:
        bruto = (raiz_artefatos() / caminho_relativo).read_bytes()
    except OSError:
        return ''
    return 'data:{};base64,{}'.format(mime, base64.b64encode(bruto).decode('ascii'))


def estilo_dashboard():
    fontes = raiz_artefatos() / 'dashboard_assets' / 'fonts'
    def fonte(nome, formato):
        try:
            return 'data:{};base64,{}'.format(formato, base64.b64encode((fontes / nome).read_bytes()).decode('ascii'))
        except OSError:
            return ''
    return '''
        <style>
        @font-face { font-family: AbrilFatfaceLocal; src: url("%s") format("truetype"); }
        @font-face { font-family: LatoLocal; src: url("%s") format("truetype"); font-weight: 400; }
        @font-face { font-family: LatoLocal; src: url("%s") format("truetype"); font-weight: 700; }
        .stApp { background: #F2F6FA; color: #132B4F; font-family: LatoLocal, Arial, sans-serif; }
        header[data-testid="stHeader"] { display: none; }
        .stApp *, [data-testid="stSidebar"] * { font-family: LatoLocal, Arial, sans-serif; }
        [data-testid="stIconMaterial"] { font-family: "Material Symbols Rounded" !important; }
        [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #D8E0E9; min-width: 15.25rem; max-width: 15.25rem; }
        [data-testid="stSidebar"] > div { padding-top: 1.2rem; }
        .main .block-container { max-width: 78rem; padding-top: 1.7rem; padding-bottom: 3rem; }
        h1 { border-left: 4px solid #D62732; font-family: AbrilFatfaceLocal, Georgia, serif !important; color: #132B4F; font-size: 3.45rem !important; font-weight: 400; letter-spacing: .01em; line-height: 1.02; padding-left: 1rem; }
        h2, h3 { color: #132B4F; font-weight: 700; letter-spacing: -.01em; }
        .sidebar-title { font-family: AbrilFatfaceLocal, Georgia, serif !important; color: #132B4F; font-size: 1.7rem; line-height: 1; margin: 0 0 .35rem; }
        .sidebar-caption { color: #526983; font-size: .84rem; line-height: 1.45; margin-bottom: 1.5rem; }
        .nota-retrospectiva { border-left: 3px solid #D62732; background: transparent; padding: .2rem 0 .2rem .75rem; margin: .15rem 0 1.4rem; color: #36516F; font-weight: 700; }
        .secao-rotulo { color: #D62732; font-size: .78rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
        .gp-meta { color: #526983; font-size: .96rem; margin: -.35rem 0 1.1rem; }
        .estado-operacao { color: #132B4F; font-weight: 700; }
        .gp-cabecalho { align-items: flex-start; border-bottom: 1px solid #D8E0E9; display: flex; gap: 1.2rem; justify-content: space-between; margin: .45rem 0 1.1rem; padding-bottom: 1.1rem; }
        .gp-cabecalho h1 { margin: 0; }
        .gp-status { background: #E9EEF4; color: #132B4F; font-size: .78rem; font-weight: 700; margin-top: .5rem; padding: .38rem .68rem; white-space: nowrap; }
        .gp-status::before { background: #D62732; border-radius: 50%%; content: ""; display: inline-block; height: .38rem; margin-right: .4rem; width: .38rem; }
        .contexto-circuito { border-top: 1px solid #D8E0E9; border-bottom: 1px solid #D8E0E9; margin: .35rem 0 1.35rem; padding: 1.35rem 0; }
        .circuito-rotulo { color: #D62732; font-size: .72rem; font-weight: 700; letter-spacing: .1em; margin: 0 0 .25rem; text-transform: uppercase; }
        .circuito-nome { color: #132B4F; font-size: 1.45rem; font-weight: 700; margin: 0; }
        .tracado-indisponivel { color: #526983; font-size: .86rem; margin: .45rem 0 0; }
        .ficha-gp { border-left: 3px solid #D62732; padding-left: .85rem; }
        .ficha-gp p { margin: .16rem 0; }
        .ficha-gp strong { color: #132B4F; }
        .circuito-linha { display: block; height: 118px; max-width: 100%%; width: 100%%; }
        .condicoes-disponiveis { border-top: 1px solid #D8E0E9; margin-top: .4rem; padding-top: .85rem; }
        .condicoes-disponiveis p { color: #526983; margin: .25rem 0; }
        .tabela-editorial { overflow-x: auto; }
        .tabela-editorial table { border-collapse: collapse; font-size: .84rem; width: 100%%; }
        .tabela-editorial th { border-bottom: 1px solid #AFC0D2; color: #526983; font-size: .68rem; letter-spacing: .06em; padding: .35rem .25rem; text-align: left; text-transform: uppercase; }
        .tabela-editorial td { border-bottom: 1px solid #D8E0E9; padding: .44rem .25rem; vertical-align: middle; }
        .tabela-editorial .numero { text-align: right; white-space: nowrap; }
        .barra-equipe { display: inline-block; height: 1.05rem; margin-right: .38rem; vertical-align: middle; width: .22rem; }
        .tabela-legenda { color: #526983; font-size: .78rem; margin: .25rem 0 .6rem; }
        .breadcrumb-editorial { color: #667A9A; font-size: .66rem; font-weight: 700; letter-spacing: .12em; margin: .1rem 0 1.6rem; text-transform: uppercase; }
        .breadcrumb-editorial span { color: #132B4F; margin: 0 .7rem; }
        .area-visao-geral { display: grid; gap: .85rem; grid-template-columns: minmax(0, 1.95fr) minmax(175px, .64fr) minmax(235px, .9fr); margin-top: 1rem; }
        .hero-circuito { background: #17304F; color: #FFFFFF; margin: 0; min-height: 23.4rem; overflow: hidden; position: relative; }
        .hero-circuito img { height: 23.4rem; object-fit: cover; object-position: center; width: 100%%; }
        .hero-sobreposicao { background: rgba(11,27,48,.88); bottom: 0; left: 0; padding: 1rem 1.45rem 1.1rem; position: absolute; right: 0; }
        .hero-sobreposicao .circuito-rotulo { color: #FFFFFF; margin-bottom: .4rem; }
        .hero-sobreposicao h2 { color: #FFFFFF; font-family: AbrilFatfaceLocal, Georgia, serif !important; font-size: 2rem; font-weight: 400; margin: 0 0 .3rem; }
        .hero-sobreposicao p { color: #E3EBF5; font-size: .82rem; margin: 0; }
        .hero-atribuicao { bottom: .45rem; color: rgba(255,255,255,.78); font-size: .62rem; position: absolute; right: .65rem; }
        .mapa-circuito, .painel-editorial { background: rgba(255,255,255,.72); border: 1px solid #DFE8F0; }
        .mapa-circuito { align-items: center; display: flex; flex-direction: column; justify-content: center; min-height: 23.4rem; padding: 1.2rem; }
        .mapa-circuito img { max-height: 13.8rem; max-width: 100%%; object-fit: contain; width: 100%%; }
        .mapa-circuito p { color: #526983; font-size: .74rem; margin: .35rem 0 0; }
        .coluna-circuito { display: grid; gap: .85rem; grid-template-rows: .82fr 1.18fr; }
        .painel-editorial { padding: 1.1rem 1.2rem; }
        .painel-editorial h3 { font-size: .7rem; letter-spacing: .1em; margin: 0 0 .7rem; text-transform: uppercase; }
        .painel-editorial p { color: #526983; font-size: .85rem; line-height: 1.45; margin: .35rem 0; }
        .painel-editorial strong { color: #132B4F; }
        .painel-vazio { align-items: center; display: flex; min-height: 100%%; }
        .secao-campeonato { margin-top: .85rem; }
        .secao-campeonato [data-testid="stColumn"] { background: rgba(255,255,255,.72); border: 1px solid #DFE8F0; padding: 1rem 1.2rem; }
        [data-testid="stSidebar"] { min-width: 16.8125rem; max-width: 16.8125rem; }
        [data-testid="stSidebar"] > div { padding: 1.85rem .9rem; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label { border-left: 3px solid transparent; min-height: 3.2rem; padding: .55rem .65rem; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] { background: #EAF4FC; border-left-color: #D62732; color: #132B4F; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label::before { color: #526983; font-family: "Material Symbols Rounded"; font-size: 1.25rem; margin-right: .6rem; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-of-type(1)::before { content: "flag"; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-of-type(2)::before { content: "query_stats"; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-of-type(3)::before { content: "monitoring"; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-of-type(4)::before { content: "fact_check"; }
        .main .block-container { max-width: 83.6rem; padding: .5rem 2.35rem 3rem; }
        .gp-cabecalho { margin-bottom: 1.45rem; }
        .gp-cabecalho h1 { font-size: 5rem !important; letter-spacing: -.035em; line-height: .96; max-width: 58rem; }
        .gp-meta { font-size: 1.15rem; letter-spacing: .18em; margin: .55rem 0 0 1.28rem; }
        .gp-status { border-radius: 999px; font-size: .88rem; margin-top: 1rem; padding: .72rem 1.1rem; }
        [data-baseweb="tab-list"] { gap: 2rem; margin-bottom: .1rem; }
        button[data-baseweb="tab"] { font-size: .94rem !important; padding: .7rem .1rem !important; }
        .contexto-circuito, .ficha-gp, .condicoes-disponiveis { border: 0; margin: 0; padding: 0; }
        @media (max-width: 1000px) { .area-visao-geral { grid-template-columns: minmax(0, 1fr) minmax(200px, .55fr); } .coluna-circuito { grid-column: 1 / -1; grid-template-columns: 1fr 1fr; grid-template-rows: none; } .gp-cabecalho h1 { font-size: 4rem !important; } }
        [data-baseweb="tab-list"] { border-bottom: 1px solid #D8E0E9; gap: 2rem; margin-bottom: .1rem; }
        button[data-baseweb="tab"] { background: transparent !important; color: #526983 !important; font-size: .94rem !important; font-weight: 700 !important; padding: .7rem .1rem !important; }
        button[data-baseweb="tab"][aria-selected="true"] { border-bottom: 3px solid #D62732 !important; color: #132B4F !important; }
        .stMetric { background: #FFFFFF; border: 1px solid #D8E0E9; border-radius: 0; padding: .55rem .75rem; }
        .stDataFrame { border: 1px solid #D8E0E9; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] { color: #D62732; font-weight: 700; }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] > div { border-radius: 0; }
        *:focus-visible { outline: 3px solid #D62732 !important; outline-offset: 2px; }
        @media (max-width: 700px) {
          [data-testid="stMetric"] { min-width: 0; padding: .45rem .55rem; }
          .main .block-container { padding-left: .9rem; padding-right: .9rem; }
          h1 { font-size: 2.2rem !important; line-height: 1.04; }
          .gp-cabecalho { gap: .7rem; }
          .gp-status { font-size: .72rem; padding: .3rem .5rem; }
          .breadcrumb-editorial { margin-bottom: 1rem; }
          .area-visao-geral { display: block; }
          .hero-circuito, .hero-circuito img { min-height: 15rem; height: 15rem; }
          .mapa-circuito, .painel-editorial { margin-top: .8rem; min-height: auto; }
          .coluna-circuito { display: block; }
          .gp-cabecalho h1 { font-size: 2.75rem !important; }
          .gp-meta { font-size: .83rem; letter-spacing: .08em; margin-left: 1rem; }
          [data-testid="stSidebar"] { min-width: auto; max-width: none; }
          [data-baseweb="tab-list"] { gap: .7rem; overflow-x: auto; }
        }
        </style>
        ''' % (fonte('abrilfatface.ttf', 'font/ttf'), fonte('lato.ttf', 'font/ttf'), fonte('lato-bold.ttf', 'font/ttf'))


def aplicar_estilo():
    st.markdown(estilo_dashboard(), unsafe_allow_html=True)


def rotulo_resultado(posicao, status):
    status_normalizado = str(status or '').strip().lower()
    if status_normalizado in ('disqualified', 'disqualificado', 'desclassificado'):
        return 'Desclassificação'
    if status_normalizado in ('retired', 'abandoned', 'abandonou'):
        return 'Abandono'
    if status_normalizado in ('did not start', 'dns', 'não largou'):
        return 'Não largou'
    if posicao in (1, 2, 3):
        return 'Pódio'
    if isinstance(posicao, int) and 4 <= posicao <= 10:
        return 'Pontuou fora do pódio'
    return 'Resultado registrado'


def tabela_participantes(pacote, participantes):
    linhas = []
    for item in participantes:
        situacao = 'Elegível' if item['elegivel_previsao'] else 'Inelegível: {}'.format(item['motivos_inelegibilidade'])
        if item['elegivel_previsao'] and item['podio'] is None:
            situacao += ' · alvo desconhecido'
        linhas.append({
            'Piloto': nome_piloto(pacote, item),
            'Equipe': nome_equipe(pacote, item),
            'ID': item['piloto_id'],
            'Situação': situacao,
            'Probabilidade de pódio': percentual(item['probabilidade_modelo']),
            'Rank do modelo': numero(item['ranking_modelo']),
            'Rank da classificação': numero(item['ranking_classificacao']),
            'Alvo posterior conhecido': 'sim' if item['alvo_conhecido'] else 'não',
        })
    return pd.DataFrame(linhas)


def tabela_campeonato_pilotos(campeonato):
    return pd.DataFrame([
        {
            'Posição': item['posicao'],
            'Piloto': item['piloto'],
            'Equipe': item['equipe'] or 'Equipe indisponível',
            'Pontos': item['pontos'],
            'Vitórias': item['vitorias'],
        }
        for item in campeonato['classificacao']
    ])


def cor_equipe(equipe):
    nome = str(equipe or '').lower()
    for identificador, cor in CORES_EQUIPE.items():
        if identificador.replace('_', ' ') in nome:
            return cor
    return CORES['neutro']


def tabela_campeonato_editorial(campeonato, limite=5):
    """Tabela visual curta; a tabela completa continua disponível no expander."""
    linhas = []
    for item in campeonato['classificacao'][:limite]:
        equipe = item['equipe'] or 'Equipe indisponível'
        linhas.append(
            '<tr><td class="numero">{}</td><td>{}</td><td><span class="barra-equipe" style="background:{}"></span>{}</td><td class="numero">{}</td></tr>'.format(
                escape(str(item['posicao'])), escape(str(item['piloto'])), cor_equipe(equipe),
                escape(equipe), escape(str(item['pontos'])),
            )
        )
    return '''
    <div class="tabela-editorial">
      <table aria-label="Campeonato de pilotos 2026">
        <thead><tr><th>Pos.</th><th>Piloto</th><th>Equipe</th><th class="numero">Pontos</th></tr></thead>
        <tbody>{}</tbody>
      </table>
    </div>
    '''.format(''.join(linhas))


def renderizar_campeonato_pilotos(pacote):
    campeonato = pacote.get('campeonato_pilotos')
    st.subheader('Classificação de pilotos 2026')
    if not isinstance(campeonato, dict) or not isinstance(campeonato.get('disponivel'), bool):
        st.info('Classificação de pilotos indisponível.')
        st.caption('Snapshot DriverStandings ausente ou com schema inválido. Probabilidades por GP permanecem separadas.')
        return
    if not campeonato['disponivel']:
        st.info('Classificação de pilotos indisponível.')
        st.caption(campeonato.get('motivo') or 'Snapshot DriverStandings incompleto.')
        return
    campos = ('snapshot_id', 'rodada_referencia', 'obtido_em_utc', 'paginas_validadas', 'escopo', 'classificacao')
    if not all(campo in campeonato for campo in campos) or not isinstance(campeonato['classificacao'], list):
        st.info('Classificação de pilotos indisponível.')
        st.caption('Snapshot DriverStandings incompleto. Probabilidades por GP permanecem separadas.')
        return
    st.caption('DriverStandings Jolpica-F1, separado das probabilidades por GP.')
    st.caption('Rodada de referência: {} · Obtido em UTC: {} · Snapshot: {} · {} página(s) paginada(s) validada(s).'.format(
        campeonato['rodada_referencia'], campeonato['obtido_em_utc'], campeonato['snapshot_id'],
        campeonato['paginas_validadas'],
    ))
    st.caption(campeonato['escopo'])
    st.markdown('<p class="tabela-legenda">Top 5 do snapshot oficial local. Barras finas identificam a equipe.</p>', unsafe_allow_html=True)
    st.markdown(tabela_campeonato_editorial(campeonato), unsafe_allow_html=True)
    with st.expander('Classificação completa'):
        st.dataframe(tabela_campeonato_pilotos(campeonato), width='stretch', hide_index=True)


def tabela_calendario_2026(pacote, rodada_selecionada):
    return pd.DataFrame([
        {
            'Rodada': corrida['rodada'],
            'Data': corrida['data_corrida'],
            'GP': corrida['corrida'],
            'Selecionado': 'sim' if corrida['rodada'] == rodada_selecionada else '',
        }
        for corrida in sorted(pacote['corridas'], key=lambda item: item['rodada'])
    ])


def renderizar_calendario_2026(pacote, rodada_selecionada):
    st.subheader('Calendário 2026')
    st.caption('Calendário local do mesmo asset 2026; “Selecionado” acompanha o seletor de Grande Prêmio.')
    st.dataframe(tabela_calendario_2026(pacote, rodada_selecionada), width='stretch', hide_index=True)


def nome_estado_operacao(estado):
    return {
        'aguardando_dados': 'Aguardando dados',
        'classificacao_disponivel': 'Classificação disponível',
        'previsao_registrada': 'Previsão registrada',
    }.get(estado, str(estado).replace('_', ' ').capitalize())


def renderizar_programacao(corrida):
    st.subheader('Programação do fim de semana')
    programacao = corrida.get('programacao')
    if not isinstance(programacao, list) or not programacao:
        st.caption('Programação não disponível no artefato local desta temporada.')
        return
    cabecalho = st.columns((2, 1, 1))
    cabecalho[0].markdown('**Sessão**')
    cabecalho[1].markdown('**Data**')
    cabecalho[2].markdown('**Hora**')
    for item in programacao:
        linha = st.columns((2, 1, 1))
        linha[0].write(item['sessao'])
        linha[1].write(item['data'])
        linha[2].write(item['hora'])


def renderizar_estado_dados(corrida):
    st.subheader('Estado dos dados')
    for nome, estado in (
        ('Classificação', corrida.get('estado_qualificacao', 'histórico disponível')),
        ('Previsão', corrida.get('estado_previsao', 'avaliação retrospectiva')),
        ('Resultado', corrida.get('estado_resultado', 'observado')),
    ):
        linha = st.columns((1, 2))
        linha[0].markdown('**{}**'.format(nome))
        linha[1].write(estado.replace('_', ' '))


def renderizar_contexto_circuito(corrida):
    circuito = corrida.get('circuito_nome') or 'Circuito indisponível'
    eh_austin = corrida.get('circuito_id') == 'americas'
    foto = ativo_data_uri('dashboard_assets/circuit/cota-hero.jpg', 'image/jpeg') if eh_austin else ''
    mapa = ativo_data_uri('dashboard_assets/circuit/cota-f1-layout.svg', 'image/svg+xml') if eh_austin else ''
    hero = '<img src="{}" alt="Foto do circuito Circuit of the Americas">'.format(foto) if foto else '<p>Foto do circuito indisponível no pacote local.</p>'
    mapa_html = '<img src="{}" alt="Mapa do circuito Circuit of the Americas">'.format(mapa) if mapa else '<p>Mapa do circuito indisponível no pacote local.</p>'
    st.markdown('''
    <section class="area-visao-geral" aria-label="Visão geral do circuito">
      <figure class="hero-circuito">
        {}
        <figcaption class="hero-sobreposicao">
          <p class="circuito-rotulo">Foto do circuito · Contexto do circuito</p>
          <h2>{}</h2>
          <p>Dados do circuito indisponíveis no snapshot local.</p>
        </figcaption>
        <span class="hero-atribuicao">Foto: Pedro Mendes · CC BY 2.0</span>
      </figure>
      <section class="mapa-circuito" aria-label="Mapa do circuito">
        <p class="circuito-rotulo">Mapa do circuito</p>
        {}
        <p>Layout F1 · CC BY-SA 4.0</p>
      </section>
      <div class="coluna-circuito">
        <section class="painel-editorial painel-vazio">
          <div>
            <h3>Condições disponíveis</h3>
            <p><strong>Dados meteorológicos indisponíveis no snapshot local.</strong></p>
            <p>Não há clima, tempos ou estratégias publicados nesta visualização.</p>
          </div>
        </section>
        <section class="painel-editorial">
          <h3>Informações do circuito</h3>
          <p><strong>Circuito</strong><br>{}</p>
          <p><strong>Local</strong><br>{}, {}</p>
          <p><strong>Data</strong><br>{}</p>
          <p><strong>Estado operacional</strong><br>{}</p>
        </section>
      </div>
    </section>
    '''.format(
        hero, escape(circuito), mapa_html, escape(circuito), escape(corrida.get('cidade', 'Cidade indisponível')),
        escape(corrida.get('pais', 'País indisponível')), escape(corrida.get('data', 'Data indisponível')),
        escape(nome_estado_operacao(corrida.get('estado_operacao', 'aguardando_dados'))),
    ), unsafe_allow_html=True)


def renderizar_condicoes_disponiveis(corrida):
    st.markdown('''
    <section class="condicoes-disponiveis">
      <p class="circuito-rotulo">Condições disponíveis</p>
      <p><strong>Dados meteorológicos indisponíveis no snapshot local.</strong></p>
      <p>O dashboard não estima clima, tempos de sessão ou estratégias antes de uma fonte pública canônica.</p>
    </section>
    ''', unsafe_allow_html=True)


def renderizar_desempenho_equipes_indisponivel():
    st.subheader('Desempenho das equipes')
    st.info('Dados de desempenho por equipe indisponíveis no snapshot local.')
    st.caption('A tabela não é reconstruída a partir de resultados de corrida porque não há um snapshot canônico de campeonato de construtores neste pacote.')


def aviso_favoritos_insuficientes(quantidade):
    if quantidade < 3:
        return 'Aviso: há menos de três favoritos disponíveis neste ranking ({} de 3).'.format(quantidade)
    return ''


def grafico_probabilidades(pacote, participantes=None):
    if participantes is None:
        participantes = pacote
        pacote = {'temporada': 0, 'asset_race_weekend': None}
    elegiveis = [item for item in participantes if item['elegivel_previsao']]
    elegiveis.sort(key=lambda item: (item.get('ranking_modelo') is None, item.get('ranking_modelo') or 9999, item['piloto_id']))
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

    maior_percentual = max(item['probabilidade_modelo'] * 100 for item in elegiveis)
    figura = go.Figure(go.Bar(
        x=[item['probabilidade_modelo'] * 100 for item in elegiveis],
        y=[nome_piloto(pacote, item) for item in elegiveis],
        orientation='h',
        marker={'color': [CORES_EQUIPE.get(identidade_piloto(pacote, item).get('equipe_id') or '', CORES['neutro']) for item in elegiveis],
                'line': {'color': ['#183153' if identidade_piloto(pacote, item).get('equipe_id') == 'haas' else 'rgba(0,0,0,0)' for item in elegiveis], 'width': 1}},
        customdata=[nome_equipe(pacote, item) for item in elegiveis],
        hovertemplate='%{y}<br>Equipe: %{customdata}<br>Probabilidade: %{x:.1f}%<extra>pódio individual</extra>',
        name='Probabilidade do modelo',
    ))
    figura.update_layout(
        height=max(360, min(620, 28 * len(elegiveis) + 120)),
        margin={'l': 10, 'r': 20, 't': 25, 'b': 40},
        paper_bgcolor=CORES['fundo'], plot_bgcolor=CORES['fundo'], font={'color': CORES['texto']},
        xaxis={'title': 'Probabilidade individual de pódio (%)', 'range': [0, min(100, max(10, maior_percentual * 1.15))]},
        yaxis={'title': 'Piloto', 'autorange': 'reversed'},
        showlegend=False,
    )
    return figura


def renderizar_previsoes(pacote, bloco, participantes):
    if pacote['temporada'] == 2026 and bloco['corrida']['estado_previsao'] == 'indisponivel':
        st.subheader('Probabilidades de pódio')
        st.info('Sem probabilidades publicadas para este GP.')
        st.caption('Faltam classificação concluída e emissão prospectiva registrada para este GP.')
        return
    st.markdown('<div class="secao-rotulo">Modelo e referências — calculados sem o alvo atual</div>', unsafe_allow_html=True)
    st.subheader('Favoritos por ranking publicado')
    esquerda, direita = st.columns(2)
    with esquerda:
        st.markdown('**Modelo — top 3 por probabilidade**')
        for item in bloco['favoritos_modelo']:
            st.write('#{} · {} · {} · {}'.format(item['ranking_modelo'], nome_piloto(pacote, item), nome_equipe(pacote, item), percentual(item['probabilidade_modelo'])))
    with direita:
        st.markdown('**Referência de classificação — top 3 por ranking**')
        for item in bloco['favoritos_classificacao']:
            st.write('#{} · {} · {}'.format(item['ranking_classificacao'], nome_piloto(pacote, item), nome_equipe(pacote, item)))
        st.caption('A referência é uma ordem por classificação; ela não recebe probabilidade.')
    for ranking, favoritos in (('modelo', bloco['favoritos_modelo']), ('referência de classificação', bloco['favoritos_classificacao'])):
        aviso = aviso_favoritos_insuficientes(len(favoritos))
        if aviso:
            st.warning('{} Ranking: {}.'.format(aviso, ranking))
    st.subheader('Probabilidades de pódio de todos os elegíveis')
    st.caption('Barras seguem o rank publicado e usam a cor da equipe junto do nome; % arredondadas apenas para exibição. Sem hachura e sem recálculo.')
    st.plotly_chart(grafico_probabilidades(pacote, participantes))
    st.subheader('Participantes do GP')
    st.dataframe(tabela_participantes(pacote, participantes), width='stretch', hide_index=True)


def renderizar_resultados_observados(pacote, corrida, bloco, participantes):
    st.markdown('<div class="secao-rotulo">Resultados observados — usados depois para avaliação</div>', unsafe_allow_html=True)
    if corrida['avaliavel_ranking']:
        podio = [nome_piloto(pacote, next(item for item in participantes if item['piloto_id'] == piloto_id)) for piloto_id in corrida['podio_observado']]
        st.markdown('**Integrantes do pódio observado (sem ordem):** {}'.format(', '.join(podio)))
        col1, col2 = st.columns(2)
        col1.metric('Acertos — modelo', '{} de 3'.format(corrida['acertos_modelo']))
        col2.metric('Acertos — classificação', '{} de 3'.format(corrida['acertos_classificacao']))
        st.caption('A pontuação ignora a ordem dos três integrantes e só é mostrada com cobertura oficial avaliável.')
    else:
        st.markdown('**N/A — não avaliável.** Motivo: `{}`.'.format(corrida['motivos_nao_avaliavel']))
        alvos_desconhecidos = [nome_piloto(pacote, item) for item in participantes if item['podio'] is None]
        inelegiveis = [nome_piloto(pacote, item) for item in participantes if not item['elegivel_previsao']]
        if alvos_desconhecidos:
            st.markdown('**Alvo(s) desconhecido(s) no GP:** {}'.format(', '.join(alvos_desconhecidos)))
        if inelegiveis:
            st.markdown('**Participante(s) inelegível(is):** {}'.format(', '.join(inelegiveis)))
        identificados = [nome_piloto(pacote, next(item for item in participantes if item['piloto_id'] == piloto_id)) for piloto_id in bloco['integrantes_identificados']]
        if identificados:
            st.markdown('**Integrantes identificados na base, sem ordem:** {}'.format(', '.join(identificados)))
        if pacote['temporada'] == 2026 and corrida['podio_observado']:
            st.caption('O resultado observado permanece visível. Não há avaliação prospectiva oficial ou anual: a comparação disponível é retrospectiva, sem placar zero nem reclassificação da emissão.')
        elif pacote['temporada'] == 2026 and corrida['estado_previsao'] == 'indisponivel':
            st.caption('Sem emissão deste GP, não há favoritos exibidos nem placar artificial.')
        else:
            st.caption('O campo de pódio por GP fica vazio nesta cobertura; não há placar zero nem acerto artificial. Os favoritos continuam visíveis acima.')
    if pacote['temporada'] == 2026:
        st.subheader('Previsão e resultado observado')
        linhas = []
        for item in participantes:
            if item['probabilidade_modelo'] is not None or item['resultado_observado'] is not None:
                linhas.append({
                    'Piloto': nome_piloto(pacote, item), 'Equipe': nome_equipe(pacote, item),
                    'Previsão disponível': percentual(item['probabilidade_modelo']),
                    'Rank previsto': numero(item['ranking_modelo']),
                    'Resultado observado': numero(item['resultado_observado']),
                    'Situação do resultado': rotulo_resultado(item['resultado_observado'], item.get('status_resultado')),
                })
        if linhas:
            st.dataframe(pd.DataFrame(linhas), width='stretch', hide_index=True)
        else:
            st.info('Não há previsão ou resultado local para este GP. As rodadas 1–16 não têm probabilidade local; a rodada 18 aguarda classificação local.')


def tela_explorar(pacote, rodada, foco):
    bloco = dados_do_gp_2026(pacote, rodada) if pacote['temporada'] == 2026 else dados_do_gp(pacote, rodada)
    corrida = bloco['corrida']
    participantes = bloco['participantes']
    if pacote['temporada'] == 2026:
        st.markdown('<div class="breadcrumb-editorial">Corridas <span>›</span> {}</div>'.format(escape(corrida['corrida'])), unsafe_allow_html=True)
        st.markdown('''
        <section class="gp-cabecalho">
          <div>
            <h1>{}</h1>
            <div class="gp-meta">{}, {} · {}</div>
          </div>
          <div class="gp-status">{}</div>
        </section>
        '''.format(
            escape(corrida['corrida']), escape(corrida['cidade']), escape(corrida['pais']),
            escape(corrida['data']), escape(nome_estado_operacao(corrida['estado_operacao'])),
        ), unsafe_allow_html=True)
    else:
        st.title(corrida['corrida'])
        st.caption('Temporada {} · rodada {} · {} participantes preparados'.format(
            pacote['temporada'], corrida['rodada'], corrida['participantes_preparados']
        ))
    if pacote['temporada'] == 2026:
        if foco == 'Corridas':
            visao_geral, tempos, estrategias, clima, historico, comparativo_equipes = st.tabs((
                'Visão geral', 'Tempos', 'Estratégias', 'Clima', 'Histórico', 'Comparativo de equipes',
            ))
            with visao_geral:
                renderizar_contexto_circuito(corrida)
                classificacao, equipes = st.columns(2, gap='large')
                with classificacao:
                    renderizar_campeonato_pilotos(pacote)
                with equipes:
                    renderizar_desempenho_equipes_indisponivel()
            with tempos:
                renderizar_programacao(corrida)
                st.caption('Os horários programados não são tempos de volta. Não há tempos de sessão públicos no snapshot local.')
            with estrategias:
                st.info('Estratégias indisponíveis no snapshot local. O dashboard não estima paradas, pneus ou stints.')
            with clima:
                renderizar_condicoes_disponiveis(corrida)
            with historico:
                renderizar_estado_dados(corrida)
                with st.expander('Calendário 2026'):
                    renderizar_calendario_2026(pacote, rodada)
            with comparativo_equipes:
                renderizar_desempenho_equipes_indisponivel()
        else:
            renderizar_campeonato_pilotos(pacote)
            renderizar_estado_dados(corrida)
    else:
        estados = [
            ('Classificação', corrida.get('estado_qualificacao', 'histórico disponível')),
            ('Previsão', corrida.get('estado_previsao', 'avaliação retrospectiva')),
            ('Resultado factual', corrida.get('estado_resultado', 'observado')),
        ]
        linha_tempo = st.columns(3)
        for coluna, (nome, estado) in zip(linha_tempo, estados):
            coluna.markdown('**{}**  \n{}'.format(nome, estado.replace('_', ' ')))
        st.caption('A previsão retrospectiva é separada de previsão registrada antes da corrida; resultados não entram na previsão da própria corrida.')
    st.caption('Cobertura: {} participantes preparados · {} elegíveis · {} alvos conhecidos depois.'.format(
        corrida['participantes_preparados'], corrida['elegiveis'], corrida['alvos_conhecidos']))
    with st.expander('Cobertura e exclusões'):
        if corrida['avaliavel_ranking']:
            st.write('Ranking avaliável: há cobertura completa para pontuar os favoritos depois da corrida.')
        else:
            st.warning('N/A — não avaliável para ranking. Motivo: `{}`. Não há placar zero artificial.'.format(corrida['motivos_nao_avaliavel']))
    if foco == 'Corridas':
        st.markdown('<div class="secao-rotulo">Contexto do GP e resultado observado</div>', unsafe_allow_html=True)
        renderizar_resultados_observados(pacote, corrida, bloco, participantes)
        with st.expander('Previsões e probabilidades publicadas'):
            renderizar_previsoes(pacote, bloco, participantes)
    else:
        st.markdown('<div class="secao-rotulo">Probabilidades e estado da previsão</div>', unsafe_allow_html=True)
        renderizar_previsoes(pacote, bloco, participantes)
        with st.expander('Resultado observado — avaliação posterior'):
            renderizar_resultados_observados(pacote, corrida, bloco, participantes)


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
    if pacote['temporada'] == 2026:
        st.title('Desempenho')
        st.warning('N/A — não há métricas agregadas locais de 2026. Resultados observados e o ensaio retrospectivo permanecem separados; nenhuma probabilidade foi recalculada.')
        return
    metricas = pacote['metricas']
    cobertura = metricas['cobertura']
    total_prob = metricas['probabilisticas']['linhas_avaliaveis']
    total_gp = metricas['ranking_modelo']['corridas_avaliaveis']
    st.title('Desempenho')
    st.caption('{} · métricas lidas dos artefatos publicados'.format(nome_temporada(pacote['temporada'])))
    excluidos = cobertura['gps_total'] - total_gp
    st.subheader('Acertos entre os três escolhidos')
    st.caption('Média de integrantes corretos entre três escolhas, em {} de {} GPs; {} excluído(s) por cobertura incompleta, sem transformar ausência em zero.'.format(total_gp, cobertura['gps_total'], excluidos))
    colunas = st.columns(2)
    colunas[0].metric('Modelo', '{:.2f} de 3'.format(metricas['ranking_modelo']['media_integrantes_corretos']))
    colunas[1].metric('Classificação', '{:.2f} de 3'.format(metricas['ranking_classificacao']['media_integrantes_corretos']))

    completos_modelo = metricas['ranking_modelo']['distribuicao_0_1_2_3']['3']
    completos_classificacao = metricas['ranking_classificacao']['distribuicao_0_1_2_3']['3']
    st.subheader('Pódios completos acertados')
    st.caption('Acerto dos três integrantes do pódio, independentemente da ordem')
    colunas = st.columns(2)
    colunas[0].metric('Modelo', '{} de {} GPs'.format(completos_modelo, total_gp))
    colunas[1].metric('Classificação', '{} de {} GPs'.format(completos_classificacao, total_gp))
    st.caption('Houve empate em pódios completos.' if completos_modelo == completos_classificacao else 'Os totais de pódios completos diferem.')

    st.subheader('Comparação com a classificação')
    st.caption('As duas listas são comparadas nos mesmos {} GPs avaliáveis. A tabela mostra quantos integrantes do pódio foram acertados; não promete ganho futuro.'.format(total_gp))
    st.dataframe(tabela_distribuicao(metricas), width='stretch', hide_index=True)

    with st.expander('Detalhes técnicos'):
        st.write('Log loss penaliza especialmente probabilidades muito confiantes que erram; Brier mede a distância quadrática entre probabilidade e resultado. Em ambas, menor é melhor; nenhuma é porcentagem de acerto.')
        st.caption('As métricas probabilísticas usam {} casos elegíveis com alvo conhecido.'.format(total_prob))
        tecnicas = pd.DataFrame([
            {'Métrica': 'Log loss', 'Modelo': '{:.4f}'.format(metricas['probabilisticas']['modelo']['log_loss']), 'Constante': '{:.4f}'.format(metricas['probabilisticas']['constante']['log_loss'])},
            {'Métrica': 'Brier', 'Modelo': '{:.4f}'.format(metricas['probabilisticas']['modelo']['brier']), 'Constante': '{:.4f}'.format(metricas['probabilisticas']['constante']['brier'])},
        ])
        st.dataframe(tecnicas, width='stretch', hide_index=True)
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
    st.markdown(
        '[Método](https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/experimento_modelo_v1.md) · '
        '[Relatório de 2024](https://github.com/mbpaschoal/pitwall-lab/blob/main/reports/modelo_v1/relatorio.md) · '
        '[Avaliação de 2025](https://github.com/mbpaschoal/pitwall-lab/blob/main/reports/avaliacao_final_v1/relatorio.md) · '
        '[Repositório](https://github.com/mbpaschoal/pitwall-lab)'
    )


def executar_app():
    st.set_page_config(page_title='Pitwall Lab', layout='wide', initial_sidebar_state='auto')
    aplicar_estilo()
    st.sidebar.markdown('<div class="sidebar-title">Pitwall Lab</div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="sidebar-caption">Estudo retrospectivo de pódios na Fórmula 1</div>', unsafe_allow_html=True)
    tela = st.sidebar.radio('Navegação', ('Corridas', 'Previsões', 'Desempenho', 'Metodologia'), key='tela')
    temporada = st.sidebar.selectbox('Temporada', (2024, 2025, 2026), index=1, key='temporada')
    try:
        pacote = carregar(temporada)
    except (DashboardDadosErro, RaceWeekendDadosErro) as erro:
        st.error(str(erro))
        st.stop()
    anterior = st.session_state.get('_temporada_anterior_dashboard')
    opcoes = opcoes_gps(pacote)
    valores = [item['valor'] for item in opcoes]
    if anterior != temporada:
        if temporada == 2026:
            observadas = [item['valor'] for item in opcoes if dados_do_gp_2026(pacote, item['rodada'])['corrida']['alvos_conhecidos']]
            st.session_state['gp'] = observadas[-1] if observadas else valores[0]
        else:
            st.session_state.pop('gp', None)
        st.session_state['_temporada_anterior_dashboard'] = temporada
    descricoes = {item['valor']: '{:02d} — {}'.format(item['rodada'], item['corrida']) for item in opcoes}
    st.sidebar.caption('Desempenho agrega toda a temporada; o filtro de GP aplica-se em Corridas e Previsões.')
    gp = st.sidebar.selectbox(
        'Grande Prêmio', valores, format_func=lambda valor: descricoes.get(valor, str(valor)), key='gp',
        disabled=tela in ('Desempenho', 'Metodologia'),
    )
    if gp not in descricoes:
        por_descricao = {descricao: valor for valor, descricao in descricoes.items()}
        gp = por_descricao.get(gp, valores[0])
    rodada = int(gp.split(':', 1)[1])
    if not (tela == 'Corridas' and temporada == 2026):
        st.markdown(conteudo_markdown(pacote), unsafe_allow_html=True)
    if tela in ('Corridas', 'Previsões'):
        tela_explorar(pacote, rodada, tela)
    elif tela == 'Desempenho':
        tela_desempenho(pacote)
    else:
        tela_como_funciona()


if __name__ == '__main__':
    executar_app()
