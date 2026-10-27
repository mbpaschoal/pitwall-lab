"""Dashboard local, somente leitura, do estudo retrospectivo Pitwall Lab."""
import os
import base64
import re
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
    nome_exibicao_piloto,
    pacote_2026,
)
from contexto_editorial import ContextoEditorialErro, carregar as carregar_contextos_editoriais, para_gp
from catalogo_visual import CatalogoVisualErro, carregar as carregar_catalogo_visual, para_circuito
from pitwall_ui_dados import carregar_paineis
import pitwall_ui

RAIZ_PADRAO = Path(__file__).resolve().parent
CORES = {
    'fundo': '#E8F3FC', 'superficie': '#FFFFFF', 'texto': '#061226',
    'acento': '#D3071D', 'modelo': '#2475EF', 'classificacao': '#061226', 'neutro': '#B7BEC8',
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
    try:
        contextos_editoriais = carregar_contextos_editoriais(raiz_artefatos())
    except ContextoEditorialErro as erro:
        raise RaceWeekendDadosErro(str(erro)) from erro
    if temporada == 2026:
        asset = carregar_asset(raiz_artefatos())
        pacote = pacote_2026(asset)
        pacote['asset_race_weekend'] = asset
        pacote['contextos_editoriais'] = contextos_editoriais
        try:
            pacote['catalogo_visual'] = carregar_catalogo_visual(raiz_artefatos())
        except CatalogoVisualErro:
            pacote['catalogo_visual'] = {}
        return pacote
    conteudos = conteudos_temporada(raiz_artefatos(), temporada)
    pacote = carregar_cacheado(temporada, conteudos)
    try:
        pacote['asset_race_weekend'] = carregar_asset(raiz_artefatos())
    except RaceWeekendDadosErro:
        pacote['asset_race_weekend'] = None
    pacote['contextos_editoriais'] = contextos_editoriais
    try:
        pacote['catalogo_visual'] = carregar_catalogo_visual(raiz_artefatos())
    except CatalogoVisualErro:
        pacote['catalogo_visual'] = {}
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


def corrida_editorial(pacote, corrida):
    """Acrescenta somente contexto factual de apresentação ao artefato do GP."""
    contexto = para_gp(pacote['contextos_editoriais'], pacote['temporada'], corrida['rodada'])
    resultado = dict(corrida)
    resultado.update(contexto)
    return resultado


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


def conteudo_markdown(atual, rodada=None):
    aviso = 'Estudo retrospectivo com dados históricos.'
    if atual['temporada'] == 2026:
        corrida = next((item for item in atual['corridas'] if item['rodada'] == rodada), None)
        if corrida and corrida.get('estado_previsao') == 'previsao_registrada':
            aviso = 'Previsão registrada antes da corrida.'
        elif corrida is None:
            aviso = 'Análise de pódios com dados históricos e previsões registradas.'
        elif corrida.get('estado_previsao') != 'ensaio_retrospectivo':
            aviso = 'Previsão deste GP indisponível.'
    return '<div class="nota-retrospectiva">{}</div>'.format(aviso)


def ativo_data_uri(caminho_relativo, mime):
    """Carrega um ativo local para o HTML sem depender de rede em produção."""
    try:
        bruto = (raiz_artefatos() / caminho_relativo).read_bytes()
    except OSError:
        return ''
    return 'data:{};base64,{}'.format(mime, base64.b64encode(bruto).decode('ascii'))


def estilo_dashboard():
    return pitwall_ui.stylesheet(raiz_artefatos())


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
    st.subheader('Classificação de pilotos {}'.format(pacote.get('temporada', '')).strip())
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
        'resultado_observado': 'Resultado observado',
    }.get(estado, str(estado).replace('_', ' ').capitalize())


def situacao_corrida(corrida):
    if corrida.get('estado_resultado') == 'observado_local' or (corrida.get('estado_resultado') is None and corrida.get('alvos_conhecidos', 0) > 0):
        return 'Resultado observado'
    if corrida.get('estado_previsao') == 'ensaio_retrospectivo':
        return 'Ensaio retrospectivo'
    if corrida.get('estado_previsao') == 'previsao_registrada':
        return 'Previsão registrada'
    if corrida.get('estado_qualificacao') == 'local_disponivel':
        return 'Classificação disponível'
    return nome_estado_operacao(corrida.get('estado_operacao', 'aguardando_dados'))


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


def renderizar_tempos_sessoes(bloco):
    tempos = bloco.get('tempos_sessoes')
    st.subheader('Tempos de sessão')
    if not tempos or not tempos.get('disponivel'):
        st.info((tempos or {}).get('motivo', 'Tempos de sessão não disponíveis no pacote local.'))
        return
    st.caption('Fonte: Formula1Dashboard · snapshot {} · {}'.format(tempos['snapshot_id'], tempos['aviso_modelo']))
    rotulos = {'TL1': 'TL1', 'TL2': 'TL2', 'TL3': 'TL3', 'Q': 'Qualifying'}
    chave = st.selectbox('Sessão com tempos publicados', list(rotulos), format_func=lambda item: rotulos[item], key='sessao_tempos')
    sessao = tempos['sessoes'][chave]
    linhas = []
    for item in sessao['linhas']:
        linhas.append({
            'Pos.': item['posicao'], 'Piloto': nome_exibicao_piloto(item.get('piloto_id'), item['piloto']), 'Equipe': item['equipe'], 'Tempo': item['tempo'] or 'Sem tempo',
            'Gap ao líder (%)': None if item['gap_percentual_lider'] is None else round(item['gap_percentual_lider'], 3),
            'Q1': item['q1'] or '—', 'Q2': item['q2'] or '—', 'Q3': item['q3'] or '—',
            'Rank da previsão': numero(item['ranking_modelo']),
            'Prob. pódio publicada': percentual(item['probabilidade_modelo']),
            'Comparação': item['motivo_exclusao_comparacao'] or ('favorito/previsão registrada' if item['ranking_modelo'] else 'sem probabilidade publicada'),
        })
    st.dataframe(pd.DataFrame(linhas), width='stretch', hide_index=True)
    favoritos = [item for item in sessao['linhas'] if item['ranking_modelo'] in (1, 2, 3)]
    if favoritos:
        st.caption('Favoritos da emissão congelada comparados nesta sessão: ' + '; '.join(
            '#{} {} ({}, {})'.format(item['ranking_modelo'], nome_exibicao_piloto(item.get('piloto_id'), item['piloto']), item['tempo'] or 'sem tempo', percentual(item['probabilidade_modelo']))
            for item in sorted(favoritos, key=lambda valor: valor['ranking_modelo'])
        ))


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


def renderizar_contexto_circuito(pacote, corrida):
    ativos = para_circuito(pacote.get('catalogo_visual', {}), corrida.get('circuito_id')) or {}
    foto_meta, mapa_meta = ativos.get('foto'), ativos.get('mapa')
    foto = ativo_data_uri(foto_meta['caminho'], foto_meta['mime']) if foto_meta else ''
    mapa = ativo_data_uri(mapa_meta['caminho'], mapa_meta['mime']) if mapa_meta else ''
    paineis = carregar_paineis(raiz_artefatos(), pacote['temporada'], corrida['rodada'], corrida['circuito_id'])
    st.markdown(pitwall_ui.visao_geral(corrida, paineis, foto, mapa, ativos.get('alt_foto', 'Imagem ilustrativa do circuito')) + pitwall_ui.campeonatos(paineis, pacote['temporada']), unsafe_allow_html=True)
    with st.expander('Fontes, contexto do circuito e classificações completas', expanded=st.session_state.get('mostrar_fontes', False) or st.query_params.get('painel') in ('pilotos', 'equipes')):
        st.caption('Foto do circuito · Contexto do circuito. Ativos ilustrativos; não fornecem entradas ao modelo.')
        for label, meta in [('Imagem', foto_meta), ('Mapa', mapa_meta)]:
            if meta:
                st.markdown('{}: [{}]({}) · {}'.format(label, meta['autor'], meta['pagina'], meta['licenca']))
        st.caption(paineis['circuit_info']['motivo_metricas'])
        for campo, titulo, ancora in [('driver_standings', 'Campeonato de pilotos', 'campeonato-completo'), ('constructor_standings', 'Campeonato de construtores', 'equipes-completo')]:
            snapshot = paineis[campo]
            st.markdown('<h3 id="{}">{} {}</h3>'.format(ancora, titulo, pacote['temporada']), unsafe_allow_html=True)
            if snapshot['disponivel']:
                st.caption('Rodada de referência: {} · Snapshot: {} · Captura UTC: {} · {} página(s) validada(s).'.format(snapshot['rodada_referencia'], snapshot['snapshot_id'], snapshot['obtido_em_utc'], snapshot['paginas_validadas']))
                st.dataframe(pd.DataFrame(snapshot['classificacao']), width='stretch', hide_index=True)
            else:
                st.caption(snapshot['motivo'])


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
        if corrida.get('estado_previsao') == 'previsao_registrada':
            st.caption('Avaliação posterior desta previsão registrada: a pontuação ignora a ordem dos três integrantes; não é métrica anual nem altera a emissão original.')
        else:
            st.caption('Resultado apresentado em estudo retrospectivo; não é avaliação posterior de uma previsão registrada.')
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


def selecionar_gp_busca(valor):
    """Callback nativo: aplicado antes de o seletor lateral ser reconstruído."""
    st.session_state['gp'] = valor
    st.session_state['tela'] = 'Corridas'


def renderizar_topo(pacote, corrida=None, participantes=None):
    with st.container(key='topbar'):
        breadcrumb, busca, perfil = st.columns([.70, .24, .06], gap='small', vertical_alignment='center')
        with breadcrumb:
            st.markdown('<div class="breadcrumb-editorial">{} <span>› &nbsp; {}</span></div>'.format(
                escape(st.session_state.get('tela', 'Corridas')), escape(corrida['corrida'] if corrida else str(pacote['temporada']))), unsafe_allow_html=True)
        with busca:
            with st.popover('Buscar corrida, piloto ou circuito…', icon=':material/search:', width='stretch'):
                consulta = st.text_input('Buscar nesta temporada', key='busca_local', placeholder='Ex.: Austin, Leclerc, Monza').strip().casefold()
                st.caption('Busca local na temporada {}. Nenhuma consulta externa.'.format(pacote['temporada']))
                if consulta:
                    encontrados = []
                    for opcao in opcoes_gps(pacote):
                        contexto = para_gp(pacote['contextos_editoriais'], pacote['temporada'], opcao['rodada'])
                        if consulta in ' '.join(str(v) for v in contexto.values()).casefold():
                            encontrados.append(opcao)
                    for opcao in encontrados[:12]:
                        st.button('{:02d} · {}'.format(opcao['rodada'], opcao['corrida']), key='busca_gp_'+opcao['valor'], on_click=selecionar_gp_busca, args=(opcao['valor'],), width='stretch')
                    pilotos = [item for item in (participantes or []) if consulta in (nome_piloto(pacote, item)+' '+nome_equipe(pacote, item)).casefold()]
                    if pilotos:
                        st.dataframe(tabela_participantes(pacote, pilotos)[['Piloto','Equipe','Probabilidade de pódio','Rank do modelo']], hide_index=True, width='stretch')
                        st.caption('Pilotos do GP selecionado; probabilidades originais preservadas.')
                    if not encontrados and not pilotos:
                        st.info('Nenhum resultado nesta temporada ou no GP selecionado.')
        with perfil:
            with st.popover('Preferências locais', icon=':material/person:', help='Preferências desta sessão'):
                st.markdown('**Pitwall Lab · Preferências locais**')
                st.caption('Temporada {} · {}. Não há conta ou login nesta interface.'.format(pacote['temporada'], st.session_state.get('tela', 'Corridas')))
                st.checkbox('Abrir notas de fontes', key='mostrar_fontes')
                st.caption('A preferência vale somente para esta sessão e não altera dados nem previsões.')


def tela_explorar(pacote, rodada, foco):
    bloco = dados_do_gp_2026(pacote, rodada) if pacote['temporada'] == 2026 else dados_do_gp(pacote, rodada)
    corrida = corrida_editorial(pacote, bloco['corrida'])
    bloco = dict(bloco)
    bloco['corrida'] = corrida
    participantes = bloco['participantes']
    renderizar_topo(pacote, corrida, participantes)
    st.markdown(pitwall_ui.cabecalho(corrida, pacote['temporada'], situacao_corrida(corrida)), unsafe_allow_html=True)
    if foco == 'Corridas':
        visao_geral, tempos, estrategias, clima, historico, comparativo_equipes = st.tabs((
            'Visão geral', 'Tempos', 'Estratégias', 'Clima', 'Histórico', 'Comparativo de equipes',
        ))
        with visao_geral:
            renderizar_contexto_circuito(pacote, corrida)
        with tempos:
            renderizar_programacao(corrida)
            renderizar_tempos_sessoes(bloco)
        with estrategias:
            st.info('Estratégias indisponíveis no pacote local.')
        with clima:
            renderizar_condicoes_disponiveis(corrida)
        with historico:
            renderizar_estado_dados(corrida)
            if pacote['temporada'] == 2026:
                with st.expander('Calendário 2026'):
                    renderizar_calendario_2026(pacote, rodada)
        with comparativo_equipes:
            paineis = carregar_paineis(raiz_artefatos(), pacote['temporada'], rodada, corrida['circuito_id'])
            equipes = paineis['constructor_standings']
            if equipes['disponivel']:
                st.subheader('Campeonato de construtores {}'.format(pacote['temporada']))
                st.caption('Classificação oficial pós-GP, rodada {}. Contexto descritivo separado das probabilidades individuais de pódio.'.format(rodada))
                st.dataframe(pd.DataFrame(equipes['classificacao']), width='stretch', hide_index=True)
            else:
                renderizar_desempenho_equipes_indisponivel()
    else:
        renderizar_campeonato_pilotos(pacote)
        renderizar_estado_dados(corrida)
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
    # Links dos painéis preservam temporada e GP; nenhum parâmetro altera dados.
    query_token = (st.query_params.get('temporada'), st.query_params.get('gp'), st.query_params.get('painel'))
    if query_token != st.session_state.get('_query_aplicada'):
        ano, gp_query, _ = query_token
        if ano in ('2024', '2025', '2026') and re.fullmatch(r'[0-9]{1,2}', str(gp_query)) and 1 <= int(gp_query) <= 24:
            st.session_state['temporada'] = int(ano)
            st.session_state['_query_gp_pendente'] = '{}:{}'.format(ano, int(gp_query))
        st.session_state['_query_aplicada'] = query_token
    st.sidebar.markdown('<div class="sidebar-title">Pitwall Lab</div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="sidebar-caption">DADOS · CONTEXTO · PERFORMANCE</div>', unsafe_allow_html=True)
    tela = st.sidebar.radio('Navegação', ('Corridas', 'Previsões', 'Desempenho', 'Metodologia'), key='tela')
    st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.session_state.setdefault('temporada', 2025)
    def manter_temporada():
        if st.session_state.get('temporada') not in (2024, 2025, 2026):
            st.session_state['temporada'] = st.session_state.get('_temporada_anterior_dashboard', 2025)
    temporada = st.sidebar.selectbox('Temporada', (2024, 2025, 2026), index=None, key='temporada', on_change=manter_temporada)
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
    gp_pendente = st.session_state.pop('_query_gp_pendente', None)
    if gp_pendente in valores:
        st.session_state['gp'] = gp_pendente
    def manter_gp():
        if st.session_state.get('gp') not in valores:
            st.session_state['gp'] = valores[0]
    gp = st.sidebar.selectbox(
        'Grande Prêmio', valores, format_func=lambda valor: descricoes.get(valor, str(valor)), key='gp',
        index=None if 'gp' in st.session_state else 0,
        on_change=manter_gp,
        disabled=tela in ('Desempenho', 'Metodologia'),
    )
    st.sidebar.markdown('<div class="sidebar-help">Desempenho agrega toda a temporada; o filtro de GP aplica-se em Corridas e Previsões.</div><div class="sidebar-motto">ANÁLISE<br>PARA UMA<br>FÓRMULA 1<br>MAIS INTELIGENTE.</div>', unsafe_allow_html=True)
    if gp not in descricoes:
        por_descricao = {descricao: valor for valor, descricao in descricoes.items()}
        gp = por_descricao.get(gp, valores[0])
    rodada = int(gp.split(':', 1)[1])
    rodada_aviso = rodada if tela in ('Corridas', 'Previsões') else None
    st.markdown(conteudo_markdown(pacote, rodada_aviso), unsafe_allow_html=True)
    if tela in ('Corridas', 'Previsões'):
        tela_explorar(pacote, rodada, tela)
    elif tela == 'Desempenho':
        renderizar_topo(pacote)
        tela_desempenho(pacote)
    else:
        renderizar_topo(pacote)
        tela_como_funciona()


if __name__ == '__main__':
    executar_app()
