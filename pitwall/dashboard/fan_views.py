"""Visual composition C. Pure presentation of existing, validated records."""
import base64
from functools import lru_cache
from html import escape
from pathlib import Path
from urllib.parse import urlencode

from pitwall.paths import PROJECT_ROOT
from pitwall.i18n import language, translate
from pitwall.dashboard.hero_assets import HERO_IMAGES, PORTRAIT_OVERRIDES, portrait_asset, profile_asset
from pitwall.dashboard.journey import race_identity
from pitwall.dashboard.media import responsive_attributes

GP_CHAPTERS = (
    ("Visão geral", "Resumo"),
    ("Tempos", "Sessões e voltas"),
    ("Estratégias", "Pneus e paradas"),
    ("Clima", "Clima"),
    ("Histórico", "Histórico desta pista"),
    ("Comparativo de equipes", "Equipes neste GP"),
)


def text(value):
    return escape(translate(str(value)))


def chapter_header(title, description=''):
    """A single page title; a subtitle is useful only when it adds information."""
    subtitle = '<p>{}</p>'.format(text(description)) if description else ''
    return '<header class="pw-chapter"><h1>{}</h1>{}</header>'.format(text(title), subtitle)


def href(screen, **params):
    return '?' + urlencode(dict(tela=screen, lang=language(), **params))


@lru_cache(maxsize=96)
def _image(path, modified):
    file = Path(path)
    mime = {'.svg':'image/svg+xml','.jpg':'image/jpeg','.png':'image/png','.webp':'image/webp'}[file.suffix]
    return 'data:{};base64,{}'.format(mime, base64.b64encode(file.read_bytes()).decode('ascii'))


def asset(name):
    path = PROJECT_ROOT / 'dashboard_assets/fan' / name
    if not path.is_file() or path.resolve().parent not in ((PROJECT_ROOT/'dashboard_assets/fan').resolve(), (PROJECT_ROOT/'dashboard_assets/fan/portraits').resolve(), (PROJECT_ROOT/'dashboard_assets/fan/logos').resolve()):
        return ''
    return _image(str(path), path.stat().st_mtime_ns)


def portrait(driver, name='', css=''):
    valid = str(driver).replace('_','').isalnum()
    spec = PORTRAIT_OVERRIDES.get(driver,{}) if valid else {}
    filename = spec.get('path') or spec.get('file') or 'portraits/{}.png'.format(driver)
    if filename.startswith('dashboard_assets/fan/'):
        filename = filename[len('dashboard_assets/fan/'):]
    image = asset(filename) if valid else ''
    if image:
        position = escape(spec.get('object_position') or spec.get('position','center 28%'),quote=True)
        return '<img class="fan-portrait {}" data-driver-id="{}" style="object-position:{}" src="{}" alt="{}" loading="lazy" decoding="async">'.format(css,escape(driver,quote=True),position,image,escape(name,quote=True))
    initials = ''.join(word[0] for word in str(name).split()[:2]) or '—'
    return '<span class="fan-avatar-fallback {}" aria-label="{}">{}</span>'.format(css,escape(name,quote=True),escape(initials))


def team_mark(team, label=''):
    aliases = {'red_bull_racing':'red_bull','racing_bulls':'rb','haas_f1_team':'haas','alpine_f1_team':'alpine','rb_f1_team':'rb'}
    key = aliases.get(team, team)
    image = asset('logos/{}.svg'.format('mclaren-swoosh' if key=='mclaren' else key)) if str(key).replace('_','').isalnum() else ''
    if image:
        return '<img class="fan-team-mark" src="{}" alt="{}">'.format(image,escape(label or str(team),quote=True))
    return '<span class="fan-team-wordmark">{}</span>'.format(escape(label or str(team).replace('_',' ').title()))




def hero(title, subtitle='', image='method', extra='', dark=False, photo=None, alt='', photo_left=False, person=None, photo_meta=None):
    spec = dict(HERO_IMAGES[image]) if photo is None else None
    css = ['fan-hero', 'fan-hero-dark' if dark else '']
    attrs = ' data-hero-kind="{}"'.format(escape(image,quote=True))
    backdrop_html=''
    responsive_attrs=None
    if person:
        editorial = profile_asset(person['id'])
        if editorial:
            caption = editorial['caption'][language() == 'en']
            return ('<section class="fan-hero fan-hero-profile-editorial" data-hero-kind="{}" data-driver-id="{}">'
                    '<div class="fan-hero-copy"><h1>{}</h1><p>{}</p>{}</div>'
                    '<figure class="pw-profile-photograph"><img class="fan-hero-image fan-hero-candid" src="{}" '
                    'width="{}" height="{}" style="object-position:{}" alt="{}" decoding="async">'
                    '<figcaption>{} <a href="{}" target="_blank" rel="noopener noreferrer">{}</a> · '
                    '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a></figcaption></figure></section>').format(
                        'profile',escape(person['id'],quote=True),text(title),text(subtitle),extra,
                        escape(editorial['src'],quote=True),editorial['width'],editorial['height'],
                        escape(editorial['object_position'],quote=True),escape(caption,quote=True),escape(caption),
                        escape(editorial['source'],quote=True),escape(editorial['author']),
                        escape(editorial['license_url'],quote=True),escape(editorial['license']))
        spec=portrait_asset(person['id'],person['name'])
        if spec and not (PROJECT_ROOT/spec['path']).is_file():
            spec=None
        if not spec:
            # Keep newly observed drivers usable without borrowing another face.
            photo=''
            extra+='<small>{}</small>'.format(text('Retrato ainda não disponível.'))
    if spec:
        path = PROJECT_ROOT / spec['path']
        responsive_attrs=responsive_attributes(spec)
        source = '' if responsive_attrs else _image(str(path),path.stat().st_mtime_ns)
        alt = spec.get('alt_'+language()) or translate('Fotografia de {}').format(spec['name'])
        attrs+=' data-driver-id="{}"'.format(escape(spec['driver_id'],quote=True))
        css.append('fan-hero-portrait' if spec['portrait'] else 'fan-hero-action')
        if spec.get('layout')=='right_panel':
            css.append('fan-hero-photo-panel')
        credit = '<a class="fan-art-label" href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(escape(spec['source'],quote=True),escape(spec['credit']))
        position=spec.get('position','center')
        backdrop=spec.get('backdrop')
        if backdrop:
            backdrop_path=PROJECT_ROOT/backdrop['path']
            backdrop_source=_image(str(backdrop_path),backdrop_path.stat().st_mtime_ns)
            backdrop_html='<img class="fan-hero-backdrop" src="{}" alt="" aria-hidden="true" decoding="async">'.format(backdrop_source)
            backdrop_credit='<a class="fan-art-label" href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(escape(backdrop['source'],quote=True),escape(backdrop['credit']))
            credit='<details class="fan-photo-credits"><summary>{}</summary><div><small>{}</small>{}{}</div></details>'.format(text('Créditos das fotos'),text(spec.get('composition_'+language(),'')),credit,backdrop_credit)

    else:
        source=photo
        photo_meta=photo_meta or {}
        position=photo_meta.get('object_position') or ('20% center' if photo_left else 'center')
        credit='<small class="fan-art-label">{}</small>'.format(text('Ilustração IA')) if 'gerada por IA' in alt else ''
        if photo_meta.get('credito_curto') and photo_meta.get('pagina'):
            credit='<a class="fan-art-label" href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(escape(photo_meta['pagina'],quote=True),escape(photo_meta['credito_curto']))
    image_css='fan-hero-image'+(' fan-photo-left' if photo_left else '')+(' fan-hero-real-portrait' if spec and spec['portrait'] else '')
    source_attrs=responsive_attrs or 'src="{}"'.format(source)
    image_html='<img class="{}" style="object-position:{}" {} alt="{}" decoding="async">'.format(image_css,escape(position,quote=True),source_attrs,escape(alt,quote=True)) if source or responsive_attrs else ''
    return '<section class="{}"{}>{}<div class="fan-hero-copy"><h1>{}</h1><p>{}</p>{}</div>{}</section>'.format(' '.join(css),attrs,backdrop_html+image_html,text(title),text(subtitle),extra,credit)


def gp_chapters(year, round_, active='Visão geral'):
    links=[]
    for key,label in GP_CHAPTERS:
        url=href('Corridas',temporada=year,gp=round_,aba=key)
        links.append('<a href="{}" target="_self"{}>{}</a>'.format(escape(url,quote=True),' aria-current="page"' if key==active else '',text(label)))
    return '<nav class="fan-gp-tabs" aria-label="{}">{}</nav>'.format(text('Explorar este GP'),''.join(links))


def podium(rows, year, title='Pódio da corrida', compact=False, round_=None):
    """Positions only from observed results. Never use probability ranks."""
    positions = {r.get('position'): r for r in rows if r.get('position') in (1,2,3)}
    cards = []
    for pos in (2,1,3):
        row = positions.get(pos)
        if row is None:
            continue
        context = dict(piloto=row.get('id'), visao='perfil', anos=year)
        if year in (2024, 2025, 2026) and type(round_) is int and 1 <= round_ <= 24:
            context.update(temporada=year, gp=round_)
            if compact:
                context.update(origem_tela='Previsões', origem_temporada=year, origem_gp=round_)
        url = href('Pilotos', **context) if row.get('id') else None
        display_name = row['name'].rsplit(' ',1)[-1] if compact else row['name']
        cards.append('<a class="fan-podium-place fan-place-{}" href="{}" target="_self"><b>{}º</b>{}<strong title="{}">{}</strong><small>{}</small></a>'.format(pos,escape(url or '#',quote=True),pos,portrait(row.get('id') or '',row['name']),escape(row['name'],quote=True),escape(display_name),escape(row.get('team') or '—')))
    cards=[c.replace('<a ','<article ').replace(' href="#"','').replace('</a>','</article>') if 'href="#"' in c else c for c in cards]
    body = '<div class="fan-podium">{}</div>'.format(''.join(cards)) if cards else '<div class="fan-awaiting"><p>{}</p>{}</div>'.format(
        text('Resultado ainda indisponível para este GP.'),
        '<a class="fan-context-link" href="{}" target="_self">{}</a>'.format(
            escape(href('Corridas', temporada=year, gp=round_, aba='Tempos'), quote=True),
            text('Consultar sessões e voltas')) if round_ is not None else '')
    heading = '' if compact else '<h2>{}</h2>'.format(text(title))
    return '<section class="fan-podium-panel{}" aria-label="{}">{}{}</section>'.format(
        ' fan-podium-compact' if compact else '', text(title), heading, body)


def forecast_context(race, year):
    """Explain the stored prediction state without deriving any racing data."""
    state = race.get('estado_previsao')
    unavailable = year == 2026 and state == 'indisponivel'
    if unavailable:
        title = 'Sem previsão registrada para este GP.'
        description = 'As chances de pódio dependem da classificação concluída e de uma emissão prospectiva registrada.'
    elif state == 'previsao_registrada':
        title = 'Previsão registrada antes da corrida.'
        description = 'Probabilidade individual de pódio neste GP; não indica uma posição de chegada.'
    else:
        title = 'Estudo retrospectivo com dados históricos.'
        description = 'Estudo retrospectivo; não é previsão emitida antes da corrida.'
    return ('<section class="fan-forecast-context" data-forecast-state="{}" aria-label="{}">'
            '<div><h2>{}</h2><p>{}</p></div></section>').format(
                'unavailable' if unavailable else 'recorded' if state == 'previsao_registrada' else 'retrospective',
                text('Probabilidades de pódio'), text(title), text(description))


def forecast_rows(rows, year, origin_round=None):
    result=[]
    for row in rows:
        value = row.get('probability')
        if value is None:
            continue
        percent = '{:.1f}%'.format(value*100)
        if language() == 'pt': percent=percent.replace('.',',')
        context = dict(piloto=row['id'],visao='perfil',anos=year)
        if origin_round is not None:
            context.update(temporada=year,gp=origin_round,origem_tela='Previsões',origem_temporada=year,origem_gp=origin_round)
        result.append('<a class="fan-probability-row" href="{}" target="_self">{}<span class="fan-driver-name"><strong>{}</strong><small>{}</small></span><span class="fan-probability-track"><i style="width:{:.4f}%"></i></span><b>{}</b><span aria-hidden="true">›</span></a>'.format(escape(href('Pilotos',**context),quote=True),portrait(row['id'],row['name']),escape(row['name']),escape(row.get('team') or '—'),max(0,min(100,value*100)),percent))
    return '<div class="fan-probability-list">{}</div>'.format(''.join(result))


def circuit_details(info, climate=None, weather_href=None):
    def rows(values):
        return ''.join('<div><dt>{}</dt><dd>{}</dd></div>'.format(text(k),text(v if v is not None else 'Não documentado')) for k,v in values)
    length = info.get('comprimento_km')
    if length is not None:
        length = str(length).replace('.', ',' if language() == 'pt' else '.') + ' km'
    primary=rows([('Comprimento',length),('Curvas',info.get('curvas')),('Voltas',info.get('voltas')),
                  ('Distância da corrida',str(info.get('distancia_corrida_km','—')).replace('.',',' if language()=='pt' else '.')+' km' if info.get('distancia_corrida_km') is not None else 'Não documentado')])
    secondary=rows([('Primeiro GP',info.get('primeiro_gp')),('Sentido',info.get('sentido')),
                    ('Altitude aprox.','{:g} m'.format(info['altitude_m']) if info.get('altitude_m') is not None else None),
                    ('Zonas de DRS','Não se aplica em 2026' if not info.get('drs_aplicavel',True) else info.get('zonas_drs')),
                    ('Recorde de corrida',info.get('recorde_volta'))])
    actual=(climate or {}).get('corrida_efetiva')
    value=actual.get('air_temperature') if actual else (climate or {}).get('resumo',{}).get('temperatura_media_c')
    temperature=('{:.1f} °C'.format(value).replace('.',',') if language()=='pt' else '{:.1f} °C'.format(value)) if isinstance(value,(int,float)) and not isinstance(value,bool) else '—'
    note='Ar durante a corrida · OpenF1' if actual else 'Fim de semana · Open-Meteo' if value is not None else 'Clima não disponível'
    weather_title='<a href="{}" target="_self">{}</a>'.format(escape(weather_href,quote=True),text('Clima e medições')) if weather_href else text('Clima e medições')
    return '<aside class="fan-circuit-details"><h2>{}</h2><dl>{}</dl><div class="fan-weather"><span aria-hidden="true">🌡</span><div><h3>{}</h3><strong>{}</strong><small>{}</small></div></div><details class="fan-circuit-more"><summary>{}</summary><dl>{}</dl></details></aside>'.format(text('Sobre o circuito'),primary,weather_title,temperature,text(note),text('Mais sobre a pista'),secondary)


ICONS = {'database': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6c0-4 18-4 18 0s-18 4-18 0m0 0v12c0 4 18 4 18 0V6M3 12c0 4 18 4 18 0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>', 'settings': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M9 2h6v4l4 2 3 4-3 4-4 2v4H9v-4l-4-2-3-4 3-4 4-2V2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>', 'bar_chart': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V12h4v8m3 0V4h4v16m3 0V8h4v12" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>', 'description': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 2h10l5 5v15H5V2m10 0v6h5M8 12h9M8 16h9" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>', 'sports_score': '<svg viewBox="0 0 28 28" aria-hidden="true" focusable="false"><path d="M4 26V3" stroke="#08172d" stroke-width="2"/><path d="M5 3h18v15H5z" fill="#fff" stroke="#08172d" stroke-width="1.4"/><path d="M5 3h6v5H5zm12 0h6v5h-6zm-6 5h6v5h-6zm-6 5h6v5H5zm12 0h6v5h-6z" fill="#08172d"/></svg>'}

def process_steps(year=None, round_=None):
    steps=[('database','Entradas do modelo v1','Classificação, histórico recente de pilotos e equipes e indicadores de ausência.'),('settings','Probabilidades de pódio','O v1 congelado estima chances individuais de integrar o pódio; não prevê a ordem de chegada.'),('bar_chart','Contexto do dashboard','Tempos, clima e características do circuito ajudam a explorar os dados; não alteram as entradas ou previsões registradas.')]
    cards=''.join('<article class="fan-process-step"><b>{}</b><span class="fan-symbol" aria-hidden="true">{}</span><div><h2>{}</h2><p>{}</p></div></article>'.format(i,ICONS[icon],text(title),text(description)) for i,(icon,title,description) in enumerate(steps,1))
    links=[]
    context = dict(temporada=year,gp=round_) if year is not None and round_ is not None else {}
    for doc,title,description,icon in [('metodo-v1','Metodologia completa','Conheça as escolhas e os limites do modelo.','description'),('fontes-atuais','Fontes e cobertura atuais','Veja as fontes, a cobertura e os limites do dashboard.','database')]:
        links.append('<a href="{}" target="_self"><span class="fan-symbol" aria-hidden="true">{}</span><span><strong>{}</strong><small>{}</small></span><b>›</b></a>'.format(escape(href('Metodologia',documento=doc,**context),quote=True),ICONS[icon],text(title),text(description)))
    return '<div class="fan-process">{}</div><div class="fan-document-links">{}</div>'.format(cards,''.join(links))


def condition_rows(rows, metric, links, comparisons=None, teams=None):
    """Measured historical comparisons; ties and unknown values stay visible."""
    comparisons=comparisons or {}
    teams=teams or {}
    maximum=max((r['score'] for r in rows if r['score'] is not None),default=0)
    def formatted(score):
        label=('{:.1f}%'.format(score*100) if metric.endswith('rate') else str(int(score))) if score is not None else '—'
        return label.replace('.',',') if language()=='pt' else label
    def bar(value,limit):
        return max(0,min(100,100*value/limit)) if value is not None and limit else 0
    result=[]
    tied=sum(r['rank']==1 for r in rows)>1
    for row in rows:
        score=row['score'];driver=row['driver_id'];leader=row['rank']==1
        info=teams.get(driver,{})
        team_name=info.get('name','') if isinstance(info,dict) else info
        team_id=info.get('id','') if isinstance(info,dict) else ''
        detail=(text('Empate na liderança')+' · ' if leader and tied else '')+text('{} largadas').format(row['starts'])
        identity='<span class="fan-ranking-identity"><strong>{}</strong><small>{}{}</small><small class="fan-ranking-sample">{}</small></span>'.format(escape(row['driver_name']),team_mark(team_id,team_name) if team_id else '',escape(team_name),detail)
        if leader and comparisons.get(driver):
            chart=[]
            for item in comparisons[driver]:
                value=item['score'];limit=1 if metric.endswith('rate') else item.get('maximum',maximum)
                title='{} · {}'.format(translate(item['label']),text('{} largadas').format(item['starts']))
                chart.append('<span class="fan-mini-comparison" title="{}"><span class="fan-mini-comparison-label">{} <small class="fan-mini-comparison-sample">{}</small></span><i class="fan-condition-bar" aria-hidden="true"><i style="width:{}%"></i></i><b>{}</b></span>'.format(escape(title,quote=True),text(item['label']),text('{} largadas').format(item['starts']),bar(value,limit),formatted(value)))
            ending='<span class="fan-mini-comparisons">{}</span>'.format(''.join(chart))
        else:
            ending='<span class="fan-condition-bar"><i style="width:{}%"></i></span><em>{}</em><span aria-hidden="true">›</span>'.format(bar(score,1 if metric.endswith('rate') else maximum),formatted(score))
        result.append('<a class="fan-condition-row {}" href="{}" target="_self"><b>{}º</b>{}{}{}</a>'.format('fan-condition-leader' if leader else '',escape(links[driver],quote=True),row['rank'],portrait(driver,row['driver_name']),identity,ending))
    return '<div class="pilot-cards fan-pilot-ranking" data-leaders="{}">{}</div>'.format(sum(r['rank']==1 for r in rows),''.join(result))


def _validated_exclusion(race):
    return (race.get('estado_previsao')=='previsao_registrada'
            and race.get('resultado_posterior_validado') is True
            and race.get('estado_resultado')=='observado_local'
            and race.get('avaliavel_ranking') is False)


def has_validated_exclusions(races):
    return any(_validated_exclusion(race) for race in races)


def evaluation_reason(codes):
    reasons = {
        'participante_inelegivel': 'Há participante inelegível para a avaliação.',
        'alvo_desconhecido': 'Resultado necessário à avaliação ausente.',
        'cobertura_elegivel_incompleta': 'Cobertura de participantes elegíveis incompleta.',
        'participantes_invalidos_ou_duplicados': 'Participantes inválidos ou repetidos.',
        'resultado_posterior_ausente': 'Alvo de pódio desconhecido para ao menos um participante.',
        'resultado_posterior_nao_validado': 'Resultado posterior ainda não validado.',
        'resultado_posterior_invalido': 'Posições posteriores inválidas ou repetidas.',
        'podio_posterior_incompleto': 'Pódio posterior incompleto.',
        'alvo_posterior_invalido': 'Alvo de pódio confirmado inválido.',
        'alvo_posterior_inconsistente': 'Alvo de pódio confirmado contradiz o resultado.',
        'probabilidade_publicada_invalida': 'Probabilidade registrada inválida.',
        'ranking_publicado_invalido': 'Ranking registrado inválido ou incompleto.',
        'ranking_publicado_incompleto': 'Ranking registrado inválido ou incompleto.',
    }
    detail=' '.join(reasons[code.strip()] for code in str(codes or '').split(';') if code.strip() in reasons)
    return detail or 'Critérios de avaliação não atendidos.'


def performance_cards(rows, races, year, observed_rounds=None, operation_available=True):
    if not rows and not (year==2026 and has_validated_exclusions(races)):
        return '<p class="fan-awaiting">{}</p>'.format(text('Ainda não há previsão registrada com resultado validado para avaliar em 2026.' if year==2026 else 'Nenhuma corrida avaliável neste recorte.'))
    by_round={r['rodada']:r for r in rows}
    issued=[r['rodada'] for r in races if r.get('estado_previsao')=='previsao_registrada']
    end=(max((r['rodada'] for r in races),default=max(by_round,default=0))
         if year < 2026 else max(issued,default=max(by_round,default=0)))
    window=[r for r in races if r['rodada']<=end][-6:]
    if not window:
        window=[dict(rodada=r['rodada'],corrida=r['corrida']) for r in rows[-6:]]
    cards=[]
    for race in window:
        row=by_round.get(race['rodada'])
        flag,label=race_identity(race['corrida'],language())
        if row:
            content=''.join('<div class="fan-result-dots"><span class="fan-result-label">{}: {}</span><span class="fan-result-symbols" aria-hidden="true">{}</span></div>'.format(text(name),text('{} de 3').format(row[key]),''.join('<i class="{}" aria-hidden="true"></i>'.format('fan-hit' if i<row[key] else 'fan-miss') for i in range(3))) for key,name in [('modelo','Lab'),('classificacao','Classificação')])
        else:
            if year < 2026 and race.get('elegiveis',0)>0:
                content='<p>{}</p><small class="fan-evaluation-reason">{}</small>'.format(text('Fora da avaliação'),text(evaluation_reason(race.get('motivos_nao_avaliavel'))))
            elif year < 2026:
                content='<p>{}</p>'.format(text('Sem probabilidades históricas disponíveis'))
            elif _validated_exclusion(race):
                content='<p>{}</p><small class="fan-evaluation-reason">{}</small>'.format(text('Fora da avaliação'),text(evaluation_reason(race.get('motivos_nao_avaliavel'))))
            else:
                pending = ('Estado do resultado indisponível' if not operation_available else
                           'Resultado em conferência' if race['rodada'] in (observed_rounds or set()) else
                           'Corrida aguardada')
                content='<p>{}</p>'.format(text(pending if race.get('estado_previsao')=='previsao_registrada' else 'Sem previsão registrada'))
        cards.append('<a class="fan-gp-result" data-evaluated="{}" href="{}" title="{}" target="_self"><strong><span aria-hidden="true">{}</span>{}</strong>{}</a>'.format('true' if row else 'false',escape(href('Previsões',temporada=year,gp=race['rodada']),quote=True),escape(race['corrida'],quote=True),flag,escape(label),content))
    wins=sum(r['modelo']>r['classificacao'] for r in rows)
    ties=sum(r['modelo']==r['classificacao'] for r in rows)
    note=text('Em {} de {} corridas, o Lab acertou mais integrantes do pódio.').format(wins,len(rows))
    detail=text('{} corridas com o mesmo número de acertos.').format(ties)
    if ties == 1:
        detail=text('Uma corrida com o mesmo número de acertos.')
    if not rows:
        note=text('Nenhuma corrida avaliável neste recorte.')
        detail=text('GPs fora da avaliação não entram no resumo de acertos.')
    if len(rows)==1 and ties==1:
        note=text('Empate na corrida avaliada')
        detail=text('As duas seleções acertaram {} dos três integrantes do pódio.').format(rows[0]['modelo'])
    limit='Somente previsões registradas e resultados validados. Uma amostra pequena não demonstra superioridade.' if year==2026 else 'Estudo retrospectivo com dados históricos.'
    status = '<p class="fan-results-status">{}</p>'.format(text('Estudo retrospectivo com dados históricos.')) if year < 2026 else ''
    header = '<header class="fan-results-header"><div><h2>{}</h2><p>{}</p>{}</div><div class="fan-results-legend"><span><i class="fan-legend-hit" aria-hidden="true"></i>{}</span><span><i class="fan-miss" aria-hidden="true"></i>{}</span></div></header>'.format(
        text('Comparação com a classificação'),
        text('Compare os três nomes escolhidos pelo Lab e pela classificação com o pódio real.'),
        status, text('Piloto no pódio'), text('Piloto fora do pódio'))
    window_label = text('Últimos {} GPs').format(len(window)) if len(window)>1 else text('Último GP')
    summary_description = text('Um GP avaliável nesta temporada.') if len(rows)==1 else text('{} GPs avaliáveis nesta temporada.').format(len(rows))
    summary = '<h3 class="fan-results-summary">{}</h3><p class="fan-results-scope">{}</p>'.format(text('Resumo da temporada'),summary_description)
    return '<section class="fan-results">{}<p class="fan-results-window">{}</p><div class="fan-gp-results">{}</div>{}<div class="fan-insights"><article><span class="fan-symbol">{}</span><div><strong>{}</strong><p>{}</p></div></article><article><span class="fan-symbol">{}</span><div><strong>{}</strong><p>{}</p></div></article></div></section>'.format(
        header, window_label, ''.join(cards), summary, ICONS['sports_score'], note, detail,
        ICONS['bar_chart'], text('Amostra limitada'), text(limit))
