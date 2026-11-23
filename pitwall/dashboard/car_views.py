"""All-car comparisons: presentation of public declarations and observed times."""
import json
import pandas as pd
import plotly.graph_objects as go
from pitwall.data.car_comparison import CarDataError, load, for_event, team_rows
from pitwall.dashboard.fan_views import chapter_header
from pitwall.dashboard.journey import race_identity
from pitwall.i18n import language, translate
from pitwall.i18n.streamlit import st

COLOURS={'mclaren':'#a14d00','mercedes':'#007c77','red_bull':'#183153','ferrari':'#c51c31',
         'williams':'#2475ef','racing_bulls':'#7067aa','aston_martin':'#006f62','haas':'#536173',
         'audi':'#78483d','alpine':'#a1377d','cadillac':'#655522'}
CATEGORIES={'floor':'Assoalho e difusor','front_wing':'Asa dianteira e nariz','rear_wing':'Asa traseira',
            'suspension':'Suspensão','wheels_brakes':'Rodas e freios','body_cooling':'Carroceria e refrigeração','other':'Outros componentes'}
STATES={'updates_declared':'Alterações declaradas','no_updates_declared':'Sem novas alterações declaradas',
        'event_identity_review':'Identidade da seção a revisar'}
REASONS={'no_legal_q1_time':'Sem tempo válido em Q1','no_legal_reference':'Referência indisponível',
         'wet_or_mixed_session':'Sessão com chuva ou condição mista',
         'no_matching_dry_laps_same_compound':'Voltas ou pneus sem comparação válida'}


def remember(key):
    st.session_state['_cars_saved_'+key]=st.session_state[key]


def saved(key,default):
    return st.session_state.get('_cars_saved_'+key,default)


def pct(value):
    if value is None:return translate('Indisponível')
    text=f'{value:+.3f}%'
    return text.replace('.',',') if language()=='pt' else text


def source_link(label,url):
    return '[{}]({})'.format(translate(label),url)


def comparison(event,no_flags):
    variant='q1_no_flags' if no_flags else 'q1'
    rows=[]
    for team in team_rows(event,no_flags):
        metric=team[variant]
        nonclassified=sorted({d['qualifying_status'] for d in team['drivers'] if not d['qualifying_status'].isdigit()})
        rows.append({'Equipe':team['name'],'Diferença em Q1':pct(metric['gap_percent']),
                     'Pilotos comparáveis':f"{metric['eligible_drivers']}/2"+(' · '+', '.join(nonclassified) if nonclassified else ''),
                     'Declaração técnica':STATES[team['declaration']['status']]})
    st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch',height=430)
    st.caption('Média dos dois pilotos contra o menor tempo válido de Q1, na mesma sessão. Positivo significa mais lento. Uma equipe com apenas um piloto elegível fica sem média.')
    if any(not d['qualifying_status'].isdigit() for t in event['teams'] for d in t['drivers']):
        st.caption('NC indica piloto não classificado. Seu tempo observado é preservado quando comparável; consulte o estado oficial e a cobertura nos detalhes dos pilotos.')
    if event['wet_or_mixed_qualifying']:
        st.info('A classificação foi disputada com chuva ou condição mista. Os tempos permanecem nas fontes; este comparativo de pista seca fica indisponível.')
    reference=event['reference']
    if reference:
        st.caption(translate('Referência deste GP: {}.').format(reference['name']))
    st.markdown(source_link('Classificação oficial',event['source']['qualifying_url']))
    with st.expander('Ver os dois pilotos de cada equipe'):
        drivers=[]
        for team in team_rows(event,no_flags):
            for driver in team['drivers']:
                q=driver['q1'];eligible=q['eligible_no_flags' if no_flags else 'eligible']
                reason='; '.join(translate(REASONS[r]) for r in q['exclusion_reasons'])
                if no_flags and q['eligible'] and not eligible:reason=translate('Alerta potencial durante a volta')
                drivers.append({'Equipe':team['name'],'Piloto':driver['name'],
                                'Diferença em Q1':pct(q['gap_percent'] if eligible else None),
                                'Classificação oficial':driver['qualifying_status'],
                                'Cobertura':translate('Comparável') if eligible else reason})
        st.dataframe(pd.DataFrame(drivers),hide_index=True,width='stretch')
    with st.expander('Resultados da corrida'):
        st.caption('Posição, pontos e abandono são resultados observados; não representam uma medida de ritmo ou de ganho do carro. Sprints não entram nesta tabela.')
        rows=[{'Equipe':t['name'],'Piloto':d['name'],'Posição':d['race_position'],
               'Resultado':d['race_status'],'Pontos':d['race_points']} for t in event['teams'] for d in t['drivers']]
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        st.markdown(source_link('Resultado oficial da corrida',event['source']['race_url']))


def evolution(asset,event,no_flags):
    ids=list(asset['teams'])
    selected=st.multiselect('Filtrar equipes',ids,default=saved('car_teams',[]),format_func=lambda k:asset['teams'][k],
                           key='car_teams',on_change=remember,args=('car_teams',),placeholder='Todas as equipes',
                           help='Sem seleção, o gráfico mostra todas as equipes.')
    chosen=selected or ids
    detail=st.checkbox('Mostrar os dois pilotos',value=saved('car_driver_lines',False),key='car_driver_lines',on_change=remember,args=('car_driver_lines',))
    variant='q1_no_flags' if no_flags else 'q1'
    events=[e for e in asset['events'] if e['round']<=event['round']]
    fig=go.Figure()
    for team_id in chosen:
        teams=[next(t for t in e['teams'] if t['team_id']==team_id) for e in events]
        if detail:
            names=sorted({d['name'] for t in teams for d in t['drivers']})
            for index,name in enumerate(names):
                ys=[]
                for team in teams:
                    driver=next((d for d in team['drivers'] if d['name']==name),None)
                    ys.append(driver['q1']['gap_percent'] if driver and driver['q1']['eligible_no_flags' if no_flags else 'eligible'] else None)
                fig.add_trace(go.Scatter(x=[e['round'] for e in events],y=ys,name=name,
                    mode='lines+markers',connectgaps=False,line=dict(color=COLOURS[team_id],dash=('solid','dash','dot')[index%3]),
                    hovertemplate='%{x}: %{y:.3f}%<extra>%{fullData.name}</extra>'))
        else:
            fig.add_trace(go.Scatter(x=[e['round'] for e in events],y=[t[variant]['gap_percent'] for t in teams],
                name=asset['teams'][team_id],mode='lines+markers',connectgaps=False,
                line=dict(color=COLOURS[team_id],width=2),
                marker=dict(size=7,symbol=['diamond' if t['declaration']['status']=='updates_declared' else 'circle' for t in teams]),
                hovertemplate='%{x}: %{y:.3f}%<extra>%{fullData.name}</extra>'))
    last_round=events[-1]['round']
    tickvals=list(range(1,last_round+1)) if last_round<=8 else sorted({1,last_round,*range(3,last_round,3)})
    fig.update_layout(height=480,margin=dict(l=8,r=8,t=15,b=20),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                      font=dict(family='LatoLocal, Arial, sans-serif',color='#061226'),
                      legend=dict(orientation='h',y=-.25,x=0,font=dict(size=11)),
                      xaxis=dict(title=translate('Rodada'),range=[.5,last_round+.5],tickmode='array',tickvals=tickvals,tickangle=0),
                      yaxis=dict(title=translate('Diferença em Q1 (%)'),zeroline=True,zerolinecolor='#51617e'))
    st.plotly_chart(fig,width='stretch',config={'displayModeBar':False})
    st.caption('Losangos indicam alterações declaradas para o GP; não confirmam uso em cada carro. Lacunas ficam sem linha. A evolução inclui efeitos de piloto, carro, circuito, acerto e rivais.')
    st.caption('A troca de piloto é preservada: cada nome tem sua própria série. Os dados vão apenas até o GP selecionado.')
    rows=[]
    for team_id in chosen:
        values=[next(t for t in e['teams'] if t['team_id']==team_id)[variant]['gap_percent'] for e in events]
        rows.append({'Equipe':asset['teams'][team_id],'GPs comparáveis':sum(v is not None for v in values),
                     'GPs consultados':len(events)})
    st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')


def purpose(text):
    if language()=='en':return text
    s=text.lower();labels=[]
    if 'circuit' in s:labels.append('Adaptação ao circuito')
    if 'reliab' in s:labels.append('Confiabilidade')
    if 'flow' in s:labels.append('Condicionamento do fluxo')
    if 'local load' in s:labels.append('Carga aerodinâmica local')
    if 'cool' in s:labels.append('Refrigeração')
    if 'drag' in s:labels.append('Arrasto')
    if 'balance' in s:labels.append('Equilíbrio')
    if 'mechanical' in s:labels.append('Acerto mecânico')
    if 'structur' in s:labels.append('Estrutura')
    if 'correlation' in s:labels.append('Correlação')
    return ' · '.join(labels) if labels else 'Desempenho declarado'


def updates(asset,event):
    ids=list(asset['teams'])
    selected=st.selectbox('Equipe',ids,index=ids.index(saved('car_update_team',ids[0])),format_func=lambda k:asset['teams'][k],
                          key='car_update_team',on_change=remember,args=('car_update_team',))
    history=st.checkbox('Ver declarações anteriores ao GP selecionado',value=saved('car_update_history',False),
                        key='car_update_history',on_change=remember,args=('car_update_history',))
    entries=[e for e in asset['events'] if e['round']<=event['round']] if history else [event]
    for entry in reversed(entries):
        team=next(t for t in entry['teams'] if t['team_id']==selected)
        declaration=team['declaration']
        st.subheader(f"{entry['round']:02d} · {race_identity(entry['event'],language())[1]}")
        st.write(STATES[declaration['status']])
        if declaration['status']=='event_identity_review':
            st.warning('O título desta seção da equipe diverge do GP do documento. A associação dos componentes ao evento aguarda revisão.')
        elif declaration['no_updates_declared']:
            st.caption('A equipe não declarou novas alterações neste documento. Isso não significa ausência de diferenças de configuração ou acerto.')
        elif declaration['components']:
            rows=[{'Componente na fonte':c['component_original'],'Grupo':CATEGORIES[c['category']],
                   'Motivo declarado':purpose(c['declared_purpose_original'])} for c in declaration['components']]
            st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        else:
            st.info('Há uma declaração disponível, mas os componentes ainda não foram extraídos com segurança. Consulte a fonte original.')
        page=declaration['source_pages'][0]
        st.markdown(source_link('Ler declaração da FIA',declaration['source_url']+f'#page={page}'))
        st.caption(translate('Fonte capturada em {}.').format(declaration['captured_at_utc'][:10]))
        software=team.get('secu_software')
        if software:
            st.write(translate('Software SECU divulgado: {}.').format(software['version_as_published']))
            st.caption('Versão publicada para a equipe na classificação. Não revela código, mapas ou ganho de desempenho e não confirma cada carro em todas as sessões.')
            st.markdown(source_link('Relatório de escrutínio da FIA',software['source_url']+f"#page={software['source_page']}"))
    st.caption('Os nomes dos componentes preservam a terminologia original. O inventário completo de versões e uso por piloto e sessão não é público nesta base. Motivo declarado não é ganho medido.')


def render(root,year,round_,circuit_id=None):
    st.html(chapter_header('Carros','Compare todas as equipes e acompanhe desempenho, pilotos e alterações públicas.',anchor='carros-comparativo'))
    if year!=2026:
        st.info('O comparativo de carros cobre a temporada 2026. Selecione 2026 para consultar as onze equipes; os outros anos permanecem sem dados nesta seção.')
        return
    try:
        asset=load(root);event=for_event(asset,year,round_,circuit_id)
    except CarDataError as error:
        st.error(str(error));return
    if event is None:
        st.info('Ainda não há dados verificados dos carros para este GP. Selecione outro evento coberto.')
        return
    st.caption('Comparativo retrospectivo do conjunto carro-piloto. Estes dados não entram nas previsões registradas.')
    views=('Comparação','Evolução','Alterações')
    view=st.radio('Explorar carros',views,index=views.index(saved('car_view','Comparação')),key='car_view',horizontal=True,
                  on_change=remember,args=('car_view',))
    no_flags=False
    if view!='Alterações':
        no_flags=st.checkbox('Excluir voltas com alertas potenciais',key='car_no_flags',
                             value=saved('car_no_flags',False),on_change=remember,args=('car_no_flags',),
                             help='Sensibilidade conservadora: um alerta local na sessão não prova que o piloto encontrou a bandeira.')
    if view=='Comparação':comparison(event,no_flags)
    elif view=='Evolução':evolution(asset,event,no_flags)
    else:updates(asset,event)
    with st.expander('Método, fontes e download'):
        st.write('Q1 permite comparar a mesma fase em todo o grid. Exigimos sessão seca, tempos oficiais válidos, mesmo composto e vínculo com uma volta observada com setores e clima válidos. Combustível, programas de pneus e acerto não são conhecidos por completo.')
        st.write('A média exige os dois pilotos da equipe. Uma amostra incompleta aparece como indisponível, nunca zero. O número de componentes declarados não mede o tamanho do ganho e não é usado como nota do carro.')
        st.write('As fontes foram consultadas retrospectivamente. A data exata de captura é preservada quando disponível; uma verificação local posterior não substitui esse horário.')
        st.download_button('Baixar dados do comparativo',json.dumps(asset,ensure_ascii=False,indent=2),
                           file_name='pitwall-carros-2026.json',mime='application/json',key='car_download')
