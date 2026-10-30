"""Read-only view of post-session collection; never calls data providers."""
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
from pitwall.i18n.streamlit import st
STATES = {'aguardando_sessao': 'Sessão ainda não encerrada', 'aguardando_publicacao': 'Aguardando publicação da fonte', 'encerramento_ou_resultado_pendente': 'Encerramento ou resultado ainda não confirmado', 'parcial': 'Dados parciais; nova consulta necessária', 'dados_recebidos': 'Dados recebidos após a sessão'}

def load_status(root, year, round_, circuit):
    path = Path(root) / 'frontend_assets/operacao_fim_semana.json'
    if not path.is_file():
        return None
    if path.stat().st_size > 10 * 1024 ** 2:
        raise ValueError('Weekend asset too large')
    state = json.loads(path.read_text())
    if not isinstance(state, dict) or any((k not in state for k in ('temporada', 'rodada', 'circuito_id', 'sessoes', 'atualizado_em_utc'))) or state.get('schema') != 'pitwall-weekend-public-v1':
        raise ValueError('Unknown weekend schema')
    if (state['temporada'], state['rodada'], state['circuito_id']) != (year, round_, circuit):
        return None
    if not isinstance(state.get('sessoes'), list) or any((not isinstance(s, dict) or type(s.get('session_key')) is not int for s in state['sessoes'])):
        raise ValueError('Invalid session list')
    if len({s['session_key'] for s in state['sessoes']}) != len(state['sessoes']):
        raise ValueError('Duplicate session')
    for s in state['sessoes']:
        if s['estado'] not in STATES:
            raise ValueError('Unknown session state')
    return state

def render_status(state):
    if not state:
        return
    stamp = datetime.fromisoformat(state['atualizado_em_utc'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M UTC')
    st.caption('Verificação das fontes: {}. Dados coletados após as sessões; sujeitos ao prazo de publicação.'.format(stamp))
    with st.expander('Acompanhar chegada dos dados'):
        st.dataframe(pd.DataFrame([{'Sessão': {'Practice 1':'Treino livre 1','Practice 2':'Treino livre 2','Practice 3':'Treino livre 3','Qualifying':'Classificação','Race':'Corrida'}.get(s['nome'],s['nome']), 'Situação': STATES[s['estado']]} for s in state['sessoes']]), hide_index=True, width='stretch')
        st.caption('A previsão meteorológica é uma estimativa arquivada. O clima observado da corrida só será consolidado depois da prova.')

def render_times(state):
    if not state:
        return False
    sessions = [s for s in state['sessoes'] if s.get('tempos')]
    if not sessions:
        st.info('Ainda aguardamos os tempos publicados das sessões deste fim de semana.')
        return True
    from pitwall.dashboard.archive_views import renderizar_tempos
    identity = {k: state[k] for k in ('temporada', 'rodada', 'circuito_id')}
    gp = dict(identidade=identity, sessoes=[dict(s, n_voltas=s.get('cobertura', {}).get('laps')) for s in sessions])
    race = next((s for s in sessions if s['nome'] == 'Race'), {})
    gp['historico'] = {'voltas_por_piloto': race.get('dados_descritivos', {}).get('voltas_por_piloto', [])}
    renderizar_tempos(gp)
    st.caption('Resultados nativos OpenF1. Não são probabilidades de pódio nem alteram uma previsão registrada.')
    return True

def render_strategies(state):
    if not state:
        return False
    race = next((s for s in state['sessoes'] if s['nome'] == 'Race'), {})
    data = race.get('dados_descritivos')
    if not data:
        st.info('Pneus e paradas serão mostrados após a corrida, quando publicados pela fonte.')
        return True
    from pitwall.dashboard.archive_views import renderizar_estrategias
    renderizar_estrategias(dict(data, identidade={k: state[k] for k in ('temporada', 'rodada', 'circuito_id')}))
    return True

def render_podium(state):
    if not state:
        return False
    race = next((s for s in state['sessoes'] if s['nome'] == 'Race'), {})
    rows = sorted([r for r in race.get('tempos', []) if r.get('posicao') in (1, 2, 3)], key=lambda r: r['posicao'])
    if not rows:
        return False
    st.subheader('Resultado publicado pela OpenF1')
    for row in rows:
        st.markdown('**{} · {}** · {}'.format(row['posicao'], row['piloto'], row['equipe']))
    st.caption('Resultado descritivo da fonte; sujeito à conferência e a revisões oficiais.')
    return True

def render_weather(state):
    if not state:
        return False
    race = next((s for s in state['sessoes'] if s['nome'] == 'Race'), {})
    observed = race.get('clima_observado')
    if observed:
        st.subheader('Clima observado durante a corrida')
        cols = st.columns(2)
        for (column, field, label) in ((cols[0], 'air_temperature', 'Temperatura do ar'), (cols[1], 'track_temperature', 'Temperatura da pista')):
            value = observed['campos'][field]
            column.metric(label, '{:.1f} °C'.format(value['media_amostras']) if value['elegivel'] else '—')
        st.caption('Medições OpenF1 nos intervalos ativos da corrida. Pausas por bandeira vermelha são excluídas.')
    forecast = state.get('previsao_meteorologica', {})
    hours = forecast.get('horas', [])
    if hours:
        st.subheader('Previsão meteorológica arquivada')
        st.caption('Estimativa Open-Meteo para as coordenadas do circuito; não é medição do asfalto nem clima observado.')
        st.markdown('[Open-Meteo · CC BY 4.0](https://open-meteo.com/en/licence)')
        with st.expander('Previsão por hora (UTC)'):
            st.dataframe(pd.DataFrame(hours).rename(columns={'hora_utc': 'Hora (UTC)', 'temperature_2m': 'Temperatura do ar (°C)', 'precipitation': 'Precipitação (mm)', 'wind_speed_10m': 'Vento (m/s)'}), hide_index=True, width='stretch')
    return bool(observed or hours)

def current_gp(root, now=None):
    """Select the active weekend only within its declared time window."""
    from datetime import timezone, timedelta
    p = Path(root) / 'frontend_assets/operacao_fim_semana.json'
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text())
        state = load_status(root, data['temporada'], data['rodada'], data['circuito_id'])
        sessions = state['sessoes']
        start = min((datetime.fromisoformat(s['inicio_utc'].replace('Z', '+00:00')) for s in sessions))
        end = max((datetime.fromisoformat(s['fim_programado_utc'].replace('Z', '+00:00')) for s in sessions))
        if start - timedelta(hours=24) <= (now or datetime.now(timezone.utc)) <= end + timedelta(hours=24):
            return '{}:{}'.format(state['temporada'], state['rodada'])
    except (ValueError, KeyError, TypeError):
        return None
    return None
