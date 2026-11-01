"""Visual composition C. Pure presentation of existing, validated records."""
import base64
from functools import lru_cache
from html import escape
from pathlib import Path
from urllib.parse import urlencode

from pitwall.paths import PROJECT_ROOT
from pitwall.i18n import language, translate


def text(value):
    return escape(translate(str(value)))


def href(screen, **params):
    return '?' + urlencode(dict(tela=screen, lang=language(), **params))


@lru_cache(maxsize=96)
def _image(path, modified):
    file = Path(path)
    mime = {'.svg':'image/svg+xml','.jpg':'image/jpeg','.png':'image/png'}[file.suffix]
    return 'data:{};base64,{}'.format(mime, base64.b64encode(file.read_bytes()).decode('ascii'))


def asset(name):
    path = PROJECT_ROOT / 'dashboard_assets/fan' / name
    if not path.is_file() or path.resolve().parent not in ((PROJECT_ROOT/'dashboard_assets/fan').resolve(), (PROJECT_ROOT/'dashboard_assets/fan/portraits').resolve(), (PROJECT_ROOT/'dashboard_assets/fan/logos').resolve()):
        return ''
    return _image(str(path), path.stat().st_mtime_ns)


def portrait(driver, name='', css=''):
    image = asset('portraits/{}.png'.format(driver)) if str(driver).replace('_','').isalnum() else ''
    if image:
        return '<img class="fan-portrait {}" src="{}" alt="{}" loading="lazy">'.format(css, image, escape(name, quote=True))
    initials = ''.join(word[0] for word in str(name).split()[:2]) or '—'
    return '<span class="fan-avatar-fallback {}" aria-label="{}">{}</span>'.format(css,escape(name,quote=True),escape(initials))


def team_mark(team, label=''):
    aliases = {'red_bull_racing':'red_bull','racing_bulls':'rb','haas_f1_team':'haas','alpine_f1_team':'alpine','rb_f1_team':'rb'}
    key = aliases.get(team, team)
    image = asset('logos/{}.svg'.format(key)) if str(key).replace('_','').isalnum() else ''
    if image:
        return '<img class="fan-team-mark" src="{}" alt="{}">'.format(image,escape(label or str(team),quote=True))
    return '<span class="fan-team-wordmark">{}</span>'.format(escape(label or str(team).replace('_',' ').title()))


# Only identified real drivers may illustrate a driver banner. No generic fallback.
HERO_IMAGES = {
    'rain': dict(path='dashboard_assets/fan/banner-norris.png',driver_id='norris',
                 name='Lando Norris',credit='Lando Norris · Formula 1',portrait=True,
                 source='https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/L/LANNOR01_Lando_Norris/lannor01.png.transform/12col/image.png'),
    'helmet': dict(path='dashboard_assets/fan/banner-verstappen.png',driver_id='max_verstappen',
                   name='Max Verstappen',credit='Max Verstappen · Formula 1',portrait=True,
                   source='https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/M/MAXVER01_Max_Verstappen/maxver01.png.transform/12col/image.png'),
    'car': dict(path='dashboard_assets/circuit/miami-hero.jpg',driver_id='perez',
                name='Sergio Pérez',credit='Sergio Pérez · Miami 2022 · David Castro · CC BY-SA 4.0',portrait=False,
                source='https://commons.wikimedia.org/wiki/File:2022_Miami_GP_-_Red_Bull_RB18_of_Sergio_P%C3%A9rez.jpg'),
}


def hero(title, subtitle='', image='helmet', extra='', dark=False, photo=None, alt='', photo_left=False):
    spec = HERO_IMAGES[image] if photo is None else None
    css = ['fan-hero', 'fan-hero-dark' if dark else '']
    driver = ''
    if spec:
        path = PROJECT_ROOT / spec['path']
        source = _image(str(path),path.stat().st_mtime_ns)
        alt = translate('Fotografia de {}').format(spec['name'])
        driver = ' data-driver-id="{}"'.format(escape(spec['driver_id'],quote=True))
        css.append('fan-hero-portrait' if spec['portrait'] else 'fan-hero-action')
        if spec['portrait']:css.append('fan-hero-person-'+spec['driver_id'])
        credit = '<a class="fan-art-label" href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(escape(spec['source'],quote=True),escape(spec['credit']))
    else:
        source = photo
        credit = '<small class="fan-art-label">{}</small>'.format(text('Ilustração IA')) if 'gerada por IA' in alt else ''
    image_css = 'fan-hero-image' + (' fan-photo-left' if photo_left else '')
    if spec and spec['portrait']:image_css += ' fan-hero-real-portrait'
    image_html = '<img class="{}" src="{}" alt="{}">'.format(image_css,source,escape(alt,quote=True)) if source else ''
    return '<section class="{}"{}>{}<div class="fan-hero-copy"><h1>{}</h1><p>{}</p>{}</div>{}</section>'.format(' '.join(css),driver,image_html,text(title),text(subtitle),extra,credit)


def podium(rows, year, title='Pódio da corrida'):
    """Positions only from observed results. Never use probability ranks."""
    positions = {r.get('position'): r for r in rows if r.get('position') in (1,2,3)}
    cards = []
    for pos in (2,1,3):
        row = positions.get(pos)
        if row is None:
            continue
        url = href('Pilotos',piloto=row['id'],visao='perfil',anos=year) if row.get('id') else None
        cards.append('<a class="fan-podium-place fan-place-{}" href="{}" target="_self"><b>{}º</b>{}<strong>{}</strong><small>{}</small></a>'.format(pos,escape(url or '#',quote=True),pos,portrait(row.get('id') or '',row['name']),escape(row['name']),escape(row.get('team') or '—')))
    cards=[c.replace('<a ','<article ').replace(' href="#"','').replace('</a>','</article>') if 'href="#"' in c else c for c in cards]
    body = '<div class="fan-podium">{}</div>'.format(''.join(cards)) if cards else '<div class="fan-awaiting">{}</div>'.format(text('Resultado ainda indisponível para este GP.'))
    return '<section class="fan-podium-panel"><h2>{}</h2>{}</section>'.format(text(title),body)


def forecast_rows(rows, year):
    result=[]
    for row in rows:
        value = row.get('probability')
        if value is None:
            continue
        percent = '{:.1f}%'.format(value*100)
        if language() == 'pt': percent=percent.replace('.',',')
        result.append('<a class="fan-probability-row" href="{}" target="_self">{}<span class="fan-driver-name"><strong>{}</strong><small>{}</small></span><span class="fan-probability-track"><i style="width:{:.4f}%"></i></span><b>{}</b><span aria-hidden="true">›</span></a>'.format(escape(href('Pilotos',piloto=row['id'],visao='perfil',anos=year),quote=True),portrait(row['id'],row['name']),escape(row['name']),escape(row.get('team') or '—'),max(0,min(100,value*100)),percent))
    return '<div class="fan-probability-list">{}</div>'.format(''.join(result))


def circuit_details(info, climate=None, weather_href=None):
    values=[('Comprimento',str(info.get('comprimento_km','—')).replace('.',',' if language()=='pt' else '.')+' km'),('Curvas',info.get('curvas')),('Voltas',info.get('voltas')),('Primeiro GP',info.get('primeiro_gp')),('Sentido',info.get('sentido')),('Altitude aprox.','{:g} m'.format(info['altitude_m']) if info.get('altitude_m') is not None else None),('Zonas de DRS','Não se aplica em 2026' if not info.get('drs_aplicavel',True) else info.get('zonas_drs')),('Recorde de corrida',info.get('recorde_volta'))]
    details=''.join('<div><dt>{}</dt><dd>{}</dd></div>'.format(text(k),text(v if v is not None else 'Não documentado')) for k,v in values)
    actual=(climate or {}).get('corrida_efetiva')
    value=actual.get('air_temperature') if actual else (climate or {}).get('resumo',{}).get('temperatura_media_c')
    temperature=('{:.1f} °C'.format(value).replace('.',',') if language()=='pt' else '{:.1f} °C'.format(value)) if isinstance(value,(int,float)) and not isinstance(value,bool) else '—'
    note='Ar durante a corrida · OpenF1' if actual else 'Fim de semana · Open-Meteo' if value is not None else 'Clima não disponível'
    weather_title='<a href="{}" target="_self">{}</a>'.format(escape(weather_href,quote=True),text('Clima e medições')) if weather_href else text('Clima e medições')
    return '<aside class="fan-circuit-details"><h2>{}</h2><dl>{}</dl><div class="fan-weather"><span aria-hidden="true">🌡</span><div><h3>{}</h3><strong>{}</strong><small>{}</small></div></div></aside>'.format(text('Sobre o circuito'),details,weather_title,temperature,text(note))


ICONS = {'database': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6c0-4 18-4 18 0s-18 4-18 0m0 0v12c0 4 18 4 18 0V6M3 12c0 4 18 4 18 0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>', 'settings': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M9 2h6v4l4 2 3 4-3 4-4 2v4H9v-4l-4-2-3-4 3-4 4-2V2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>', 'bar_chart': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V12h4v8m3 0V4h4v16m3 0V8h4v12" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>', 'description': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 2h10l5 5v15H5V2m10 0v6h5M8 12h9M8 16h9" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>', 'sports_score': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 21V3m0 1c5-4 9 4 16 0v10c-7 4-11-4-16 0M9 3v10m4-9v10m4-10v10M5 8h16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>'}

def process_steps():
    steps=[('database','Dados históricos','Resultados e tempos de corridas passadas, condições da pista e características de cada circuito.'),('settings','Modelo de análise','O Lab usa essas informações para estimar a chance de cada piloto terminar entre os três primeiros.'),('bar_chart','Resultados no site','Explore chances de pódio, compare pilotos e veja o que o Lab acertou. As previsões registradas ficam preservadas.')]
    cards=''.join('<article class="fan-process-step"><b>{}</b><span class="fan-symbol" aria-hidden="true">{}</span><div><h2>{}</h2><p>{}</p></div></article>'.format(i,ICONS[icon],text(title),text(description)) for i,(icon,title,description) in enumerate(steps,1))
    links=[]
    for doc,title,description,icon in [('metodo-v1','Metodologia completa','Conheça as escolhas e os limites do modelo.','description'),('protocolo-temporal','Origem dos dados','Veja as fontes e os cuidados com cada informação.','database')]:
        links.append('<a href="{}" target="_self"><span class="fan-symbol" aria-hidden="true">{}</span><span><strong>{}</strong><small>{}</small></span><b>›</b></a>'.format(escape(href('Metodologia',documento=doc),quote=True),ICONS[icon],text(title),text(description)))
    return '<div class="fan-process">{}</div><div class="fan-document-links">{}</div>'.format(cards,''.join(links))


def condition_rows(rows, metric, links):
    result=[]
    maximum=max((r['score'] for r in rows if r['score'] is not None),default=0)
    for i,row in enumerate(rows):
        score=row['score']
        label=('{:.1f}%'.format(score*100) if metric.endswith('rate') else str(int(score))) if score is not None else '—'
        if language()=='pt':label=label.replace('.',',')
        value=max(0,min(100,score*100)) if metric.endswith('rate') and score is not None else (100*score/maximum if score is not None and maximum else 0)
        result.append('<a class="fan-condition-row {}" href="{}" target="_self"><b>{}º</b>{}<span><strong>{}</strong><small>{} · {} {}</small></span><span class="fan-condition-bar"><i style="width:{}%"></i></span><em>{}</em><span aria-hidden="true">›</span></a>'.format('fan-condition-leader' if row['rank']==1 else '',escape(links[row['driver_id']],quote=True),row['rank'],portrait(row['driver_id'],row['driver_name']),escape(row['driver_name']),text('Empate') if row['rank']==1 and sum(r['rank']==1 for r in rows)>1 else text('Histórico no recorte'),row['starts'],text('largadas'),value,label))
    return '<div class="pilot-cards fan-pilot-ranking">{}</div>'.format(''.join(result))


def performance_cards(rows, races, year):
    if not rows:
        return '<p class="fan-awaiting">{}</p>'.format(text('Ainda não há previsão registrada com resultado validado para avaliar em 2026.' if year==2026 else 'Nenhuma corrida avaliável neste recorte.'))
    by_round={r['rodada']:r for r in rows}
    issued=[r['rodada'] for r in races if r.get('estado_previsao')=='previsao_registrada']
    end=max(issued,default=max(by_round,default=0))
    window=[r for r in races if r['rodada']<=end][-6:]
    if not window:
        window=[dict(rodada=r['rodada'],corrida=r['corrida']) for r in rows[-6:]]
    cards=[]
    for race in window:
        row=by_round.get(race['rodada'])
        label=race['corrida'].replace('Grand Prix','').strip()
        if row:
            dots=''.join('<div class="fan-result-dots"><small>{}</small>{}</div>'.format(text(name),''.join('<i class="{}" aria-hidden="true"></i>'.format('fan-hit' if i<row[key] else 'fan-miss') for i in range(3))) for key,name in [('modelo','Lab'),('classificacao','Classificação')])
            content='<span class="fan-result-label">{}</span>{}'.format(text('{} de 3').format(row['modelo']),dots)
        else:
            content='<p>{}</p>'.format(text('Corrida aguardada' if race.get('estado_previsao')=='previsao_registrada' else 'Sem previsão registrada'))
        cards.append('<a class="fan-gp-result" href="{}" target="_self"><strong>{}</strong>{}</a>'.format(escape(href('Previsões',temporada=year,gp=race['rodada']),quote=True),escape(label),content))
    wins=sum(r['modelo']>r['classificacao'] for r in rows)
    ties=sum(r['modelo']==r['classificacao'] for r in rows)
    note=text('Em {} de {} corridas, o Lab acertou mais integrantes do pódio.').format(wins,len(rows))
    detail=text('{} corridas com o mesmo número de acertos.').format(ties)
    if len(rows)==1 and ties==1:
        note=text('Empate na corrida avaliada')
        detail=text('As duas seleções acertaram {} dos três integrantes do pódio.').format(rows[0]['modelo'])
    limit='Somente previsões registradas e resultados validados. Uma amostra pequena não demonstra superioridade.' if year==2026 else 'Estudo retrospectivo com dados históricos.'
    return '<section class="fan-results"><h2>{}</h2><p>{}</p><div class="fan-gp-results">{}</div><div class="fan-insights"><article><span class="fan-symbol"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 21V3m0 1c5-4 9 4 16 0v10c-7 4-11-4-16 0M9 3v10m4-9v10m4-10v10M5 8h16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg></span><div><strong>{}</strong><p>{}</p></div></article><article><span class="fan-symbol"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V12h4v8m3 0V4h4v16m3 0V8h4v12" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg></span><div><strong>{}</strong><p>{}</p></div></article></div></section>'.format(text('Comparação com a classificação'),text('As escolhas do Lab e da classificação são comparadas com o mesmo resultado.'),''.join(cards),note,detail,text('Amostra limitada'),text(limit))
