"""Read-only view of post-session collection; never calls data providers."""
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime
import pandas as pd
from pitwall.i18n.streamlit import st
STATES = {'aguardando_sessao': 'Sessão ainda não encerrada', 'aguardando_publicacao': 'Aguardando publicação da fonte', 'encerramento_ou_resultado_pendente': 'Encerramento ou resultado ainda não confirmado', 'parcial': 'Dados parciais; nova consulta necessária', 'dados_recebidos': 'Dados recebidos após a sessão'}


def _read_status_asset(root):
    """Check the event envelope before any reader follows archived identities."""
    path = Path(root) / 'frontend_assets/operacao_fim_semana.json'
    if not path.is_file():
        return None
    if path.stat().st_size > 10 * 1024 ** 2:
        raise ValueError('Weekend asset too large')
    state = json.loads(path.read_text())
    required = ('temporada', 'rodada', 'circuito_id', 'sessoes', 'atualizado_em_utc')
    if not isinstance(state, dict) or state.get('schema') != 'pitwall-weekend-public-v1' or any(k not in state for k in required):
        raise ValueError('Unknown weekend schema')
    archive = state.get('arquivo_eventos', [])
    if not isinstance(archive, list) or any(
        not isinstance(event, dict) or any(k not in event for k in required)
        for event in archive
    ):
        raise ValueError('Invalid archived event list')
    return state


def observed_rounds(root, year):
    """Observed results are context, not automatic admission to model scoring."""
    raw = _read_status_asset(root)
    if raw is None:
        return set()
    rounds=set()
    for record in [raw]+raw.get('arquivo_eventos',[]):
        if record.get('temporada')!=year:
            continue
        state=load_status(root,year,record['rodada'],record['circuito_id'])
        race=next((s for s in state['sessoes'] if s['nome']=='Race'),{})
        if race.get('encerramento_observado_utc') and race.get('tempos'):
            rounds.add(record['rodada'])
    return rounds


def load_status(root, year, round_, circuit):
    state = _read_status_asset(root)
    if state is None:
        return None
    if (state['temporada'], state['rodada'], state['circuito_id']) != (year, round_, circuit):
        matches = [s for s in state.get('arquivo_eventos', []) if (s.get('temporada'),s.get('rodada'),s.get('circuito_id')) == (year,round_,circuit)]
        if not matches:
            return None
        if len(matches) != 1:
            raise ValueError('Ambiguous archived event')
        state = matches[0]
    if not isinstance(state.get('sessoes'), list) or any((not isinstance(s, dict) or type(s.get('session_key')) is not int for s in state['sessoes'])):
        raise ValueError('Invalid session list')
    if len({s['session_key'] for s in state['sessoes']}) != len(state['sessoes']):
        raise ValueError('Duplicate session')
    for s in state['sessoes']:
        if s.get('estado') not in STATES:
            raise ValueError('Unknown session state')
    from pitwall.data.standings_state import admit_weekend_standings
    return admit_weekend_standings(state)

def render_status(state):
    if not state:
        return
    stamp = datetime.fromisoformat(state['atualizado_em_utc'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M UTC')
    st.caption('Verificação das fontes: {}. Dados coletados após as sessões; sujeitos ao prazo de publicação.'.format(stamp))
    if state.get('automacao', {}).get('modo') == 'github_actions':
        st.markdown('[Atualização automática · acompanhar coleta no GitHub](https://github.com/mbpaschoal/pitwall-lab/actions/workflows/coletar-dados.yml)')
    with st.expander('Acompanhar chegada dos dados'):
        st.dataframe(pd.DataFrame([{'Sessão': {'Practice 1':'Treino livre 1','Practice 2':'Treino livre 2','Practice 3':'Treino livre 3','Qualifying':'Classificação','Race':'Corrida'}.get(s['nome'],s['nome']), 'Situação': STATES[s['estado']], 'Detalhes': s.get('motivo_parcial', '—')} for s in state['sessoes']]), hide_index=True, width='stretch')
        st.caption('A previsão meteorológica é uma estimativa arquivada. O clima observado da corrida só será consolidado depois da prova.')

def operational_race_results(root, state):
    """Join the observed main race to its verified, event-specific results."""
    from pitwall.data.driver_conditions import DriverConditionsError, load

    race = next((session for session in (state or {}).get('sessoes', []) if session['nome'] == 'Race'), {})
    if not race.get('encerramento_observado_utc') or not race.get('tempos'):
        return []
    key = '{}:{}'.format(state['temporada'], state['rodada'])
    try:
        asset = load(root)
    except DriverConditionsError:
        return []
    event = asset['gps'].get(key, {})
    if (key not in asset['atualizacao_operacional']['eventos']
            or (event.get('circuito_id'), event.get('session_key')) != (state['circuito_id'], race['session_key'])):
        return []
    rows = [row for row in asset['resultados'] if row['race_id'] == key]
    timing = {row['numero']: row for row in race['tempos']}
    if (len(timing) != len(race['tempos']) or len(rows) != len(timing)
            or {row['number'] for row in rows} != timing.keys()):
        return []
    if any(timing[row['number']].get('piloto_id') not in (None, row['driver_id'])
           or timing[row['number']].get('posicao') != row['position'] for row in rows):
        return []
    from pitwall.dashboard.archive_views import _tempo

    return [dict(piloto_id=row['driver_id'], piloto=row['driver_name'], equipe_id=row['team_id'],
                 equipe=timing[row['number']].get('equipe') or row['team_id'],
                 posicao=row['position'], pontos=row['points'], voltas=row['completed_laps'],
                 status=row['canonical_status'], tempo=_tempo(timing[row['number']].get('duracao')))
            for row in rows]


def render_teams(state, results):
    if not results:
        return False
    from pitwall.dashboard.archive_views import renderizar_equipes

    groups = defaultdict(list)
    for row in results:
        groups[row['equipe_id']].append(row)
    teams = []
    for team_id, rows in groups.items():
        positions = [row['posicao'] for row in rows if row['posicao'] is not None]
        points = [row['pontos'] for row in rows if row['pontos'] is not None]
        teams.append(dict(equipe_id=team_id, equipe=rows[0]['equipe'], modalidade='Race',
                          n_resultados=len(rows), pontos=sum(points) if points else None,
                          pontos_completos=len(points) == len(rows),
                          posicao_media=sum(positions) / len(positions) if positions else None,
                          melhor_posicao=min(positions, default=None),
                          pilotos=[row['piloto'] for row in rows]))
    teams.sort(key=lambda team: (not team['pontos_completos'], -(team['pontos'] or 0), team['equipe']))
    identity = {key: state[key] for key in ('temporada', 'rodada', 'circuito_id')}
    renderizar_equipes(dict(identidade=identity, equipes=teams))
    st.caption('Resultado da corrida conferido entre OpenF1 e Jolpica-F1.')
    return True


def render_times(state, results=()):
    if not state:
        return False
    sessions = [s for s in state['sessoes'] if s.get('tempos')]
    if not sessions:
        st.info('Ainda aguardamos os tempos publicados das sessões deste fim de semana.')
        return True
    from pitwall.dashboard.archive_views import renderizar_tempos
    identity = {k: state[k] for k in ('temporada', 'rodada', 'circuito_id')}
    gp = dict(identidade=identity, sessoes=[dict(s, n_voltas=s.get('cobertura', {}).get('laps'),
        voltas_por_piloto=s.get('dados_descritivos', {}).get('voltas_por_piloto', [])) for s in sessions])
    race = next((s for s in sessions if s['nome'] == 'Race'), {})
    laps = race.get('dados_descritivos', {}).get('voltas_por_piloto', [])
    gp['historico'] = {'resultados': results, 'voltas_por_piloto': laps, 'resumo': {
        'n_resultados': len(results),
        'n_voltas': sum(lap[1] is not None for pilot in laps for lap in pilot.get('voltas', [])),
        'n_pilotos_com_voltas': len(laps)}}
    renderizar_tempos(gp)
    st.caption('Tempos OpenF1 com conferências documentais identificadas quando disponíveis. Não alteram a previsão registrada.')
    final_sources = {row.get('fonte_validacao') for row in race.get('tempos', [])}
    if ('https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_final_race_classification.pdf' in final_sources):
        st.caption('México: classificação final da FIA, incluindo penalidades. Os cinco não classificados mantêm a posição ausente; o alvo de pódio é conhecido.')
        st.markdown('[Classificação final oficial · FIA]({})'.format(next(
            url for url in final_sources if url and url.endswith('_final_race_classification.pdf'))))
    return True

def render_strategies(state):
    if not state:
        return False
    sessions = [s for s in state['sessoes'] if s.get('dados_descritivos')]
    if not sessions:
        st.info('Pneus e paradas serão mostrados após a corrida, quando publicados pela fonte.')
        return True
    # Keep Race as the default; the existing selector also exposes practices/Q.
    sessions.sort(key=lambda s: s['nome'] != 'Race')
    data = {field: [dict(row, modalidade=s['nome']) for s in sessions
                   for row in s['dados_descritivos'].get(field, [])]
            for field in ('estrategias', 'paradas')}
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
    reviewed = any(r.get('fonte_validacao', '').endswith('_final_race_classification.pdf') for r in rows)
    st.subheader('Classificação final oficial · FIA' if reviewed else 'Resultado publicado pela OpenF1')
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
        from pitwall.i18n import language

        def format_field(field, unit):
            data = observed['campos'].get(field, {})
            value = data.get('media_amostras')
            if not data.get('elegivel') or value is None:
                return '—'
            formatted = '{:.1f} {}'.format(value, unit)
            return formatted.replace('.', ',') if language() == 'pt' else formatted

        st.subheader('Clima observado durante a corrida')
        cols = st.columns(2)
        for (column, field, label) in ((cols[0], 'air_temperature', 'Temperatura do ar'), (cols[1], 'track_temperature', 'Temperatura da pista')):
            column.metric(label, format_field(field, '°C'))
        st.caption('Medições OpenF1 nos intervalos ativos da corrida. Pausas por bandeira vermelha são excluídas.')
        rain = {'com_chuva_registrada': 'Chuva registrada durante a corrida',
                'sem_chuva_registrada': 'Sem chuva registrada durante a corrida'}
        st.caption(rain.get(observed.get('condicao_chuva'), 'Registro de chuva inconclusivo'))
        measurements = (('humidity', '%', 'Umidade média'), ('pressure', 'hPa', 'Pressão média'),
                        ('wind_speed', 'm/s', 'Velocidade média do vento'))
        if any(field in observed['campos'] for field, _, _ in measurements):
            with st.expander('Mais medições da corrida'):
                for column, (field, unit, label) in zip(st.columns(3), measurements):
                    column.metric(label, format_field(field, unit))
                direction = observed['campos'].get('wind_direction', {})
                angle = direction.get('media_circular_graus')
                if direction.get('elegivel') and angle is not None:
                    from pitwall.dashboard.archive_views import _valor
                    from pitwall.i18n import translate
                    st.caption("{} {}".format(translate("Direção média do vento"), _valor(round(angle, 1) % 360, "°")))
        if observed['campos']['track_temperature'].get('qualidade', {}).get('codigo') == 'zero_isolado_em_conferencia':
            st.caption('Temperatura do asfalto em conferência: leitura isolada de 0 °C entre medições acima de 20 °C. Média retida, sem substituir o registro original.')
        quality = observed['campos']['track_temperature'].get('qualidade', {})
        if quality.get('codigo') == 'zero_isolado_excluido':
            st.caption('Asfalto: média das leituras válidas. Uma leitura isolada de 0 °C foi excluída após conferência documental; sem interpolação, com cobertura recalculada e registro original preservado.')
            for source in quality.get('fontes',[]):
                st.markdown('[Relatório oficial do clima da corrida]({})'.format(source['url']))
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
