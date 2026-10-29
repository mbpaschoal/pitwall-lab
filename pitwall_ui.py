"""Composição editorial compartilhada entre temporadas; sem inferência ou rede."""
import base64
import math
from datetime import date
from html import escape
from pathlib import Path


TEAM_COLORS = {'mercedes':'#18b7b0','ferrari':'#d30920','red_bull':'#2146a4','mclaren':'#ff8000','aston_martin':'#08765f','alpine':'#ec70bd','williams':'#3a8ee6','haas':'#929faa','audi':'#c90022','racing_bulls':'#4665db','rb':'#4665db'}
FLAGS = {'Italian':'🇮🇹','British':'🇬🇧','Dutch':'🇳🇱','Monegasque':'🇲🇨','Spanish':'🇪🇸','Australian':'🇦🇺','French':'🇫🇷','Canadian':'🇨🇦','Brazilian':'🇧🇷','German':'🇩🇪','Thai':'🇹🇭','Japanese':'🇯🇵','New Zealander':'🇳🇿','Argentine':'🇦🇷','Mexican':'🇲🇽','Finnish':'🇫🇮'}
COUNTRIES = {'USA':'Estados Unidos','Australia':'Austrália','Bahrain':'Bahrein','Japan':'Japão','Spain':'Espanha','China':'China','Italy':'Itália','Belgium':'Bélgica','Netherlands':'Países Baixos','Brazil':'Brasil','Mexico':'México','Austria':'Áustria','United Kingdom':'Reino Unido','Hungary':'Hungria','Singapore':'Singapura','Saudi Arabia':'Arábia Saudita','Canada':'Canadá','United Arab Emirates':'Emirados Árabes Unidos'}


def e(valor):
    return escape(str(valor if valor is not None else '—'))


def data_editorial(valor):
    try:
        d = date.fromisoformat(valor)
        return '{} {} {}'.format(d.day, ('jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez')[d.month-1], d.year)
    except (ValueError, TypeError):
        return str(valor or 'Data indisponível')


def stylesheet(root):
    root = Path(root)
    fontes = []
    for family, filename, weight in [('AbrilFatfaceLocal','abrilfatface.ttf',400),('LatoLocal','lato.ttf',400),('LatoLocal','lato-bold.ttf',700)]:
        try:
            uri = base64.b64encode((root/'dashboard_assets/fonts'/filename).read_bytes()).decode('ascii')
            fontes.append('@font-face{font-family:%s;src:url(data:font/ttf;base64,%s) format("truetype");font-weight:%s;font-display:swap;}' % (family, uri, weight))
        except OSError:
            pass
    # O CSS do aplicativo está num arquivo único; evita cascatas de patches.
    return '<style>{}{}</style>'.format(''.join(fontes), (Path(__file__).parent/'frontend_assets/pitwall.css').read_text(encoding='utf-8'))


def cabecalho(corrida, temporada, status):
    if status == 'Resultado observado' and corrida.get('estado_previsao') == 'previsao_registrada':
        detalhe = 'Resultado posterior à corrida. A previsão registrada permanece preservada.'
    elif status == 'Resultado observado':
        detalhe = 'Resultado histórico observado. Avaliação retrospectiva das probabilidades.'
    elif status == 'Aguardando dados':
        detalhe = 'Os dados oficiais serão exibidos quando houver um snapshot local validado.'
    else:
        detalhe = 'Dados históricos e probabilidades com sua origem e corte temporal preservados.'
    return '<section class="gp-cabecalho"><div class="gp-titulo"><h1>{}</h1><div class="gp-meta" title="{}"><span>{}</span><b aria-hidden="true">·</b><span>{}</span><b aria-hidden="true">·</b><span>{}</span></div></div><div class="gp-status-area"><div class="gp-status">{}</div><p>{}</p></div></section>'.format(
        e(corrida['corrida']),e('Temporada {} · {}, {} · {}'.format(temporada,corrida['cidade'],corrida['pais'],corrida['data'])),e(corrida['cidade']),e(COUNTRIES.get(corrida['pais'],corrida['pais'])),e(data_editorial(corrida['data'])),e(status),e(detalhe))


def _pontos(valor):
    return '{:g}'.format(float(valor))


def standings_table(snapshot, teams=False, limite=5):
    disponivel = snapshot.get('disponivel', False)
    head = '<tr><th>Pos</th><th>{}</th><th>{}</th><th>Pontos</th></tr>'.format('Equipe' if teams else 'Piloto','' if teams else 'Equipe')
    rows = []
    classificacao = snapshot.get('classificacao', []) if disponivel else []
    maximo = max([float(x['pontos']) for x in classificacao] or [1]) or 1
    for item in classificacao[:limite]:
        color = TEAM_COLORS.get(item.get('equipe_id') or (item.get('equipe_ids') or [''])[0], '#7a8ca5')
        if teams:
            label = '<span class="pw-team-label">{}</span>'.format(e(item['equipe']))
            third = '<span class="pw-bar-track"><span class="pw-bar-fill" style="width:{:.3f}%;background:{}"></span></span>'.format(100*float(item['pontos'])/maximo,color)
        else:
            label = '<span class="pw-flag" aria-hidden="true">{}</span>{}'.format(FLAGS.get(item.get('nacionalidade'),''),e(item['piloto']))
            third = '<span class="barra-equipe" style="background:{}"></span><span class="pw-team-label">{}</span>'.format(color,e(item['equipe']))
        rows.append('<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(e(item['posicao']),label,third,e(_pontos(item['pontos']))))
    if not rows:
        rows = ['<tr class="pw-empty-table"><td>—</td><td>—</td><td>—</td><td>—</td></tr>' for _ in range(4)]
    note = '' if disponivel else '<p class="pw-empty-note">Classificação oficial desta rodada indisponível no snapshot local.</p>'
    return '<div class="tabela-editorial"><table class="{}" aria-label="{}"><thead>{}</thead><tbody>{}</tbody></table></div>{}'.format('pw-team-table' if teams else 'pw-drivers-table','Campeonato de construtores' if teams else 'Campeonato de pilotos',head,''.join(rows),note)


def campeonatos(paineis, temporada):
    cards = []
    for teams,titulo,label,ancora in [(False,'Campeonato de pilotos','Ver campeonato','campeonato-completo'),(True,'Desempenho das equipes','Ver mais','equipes-completo')]:
        snapshot = paineis['constructor_standings' if teams else 'driver_standings']
        link = '?temporada={}&gp={}&painel={}#{}'.format(temporada, snapshot['rodada_referencia'], 'equipes' if teams else 'pilotos', ancora)
        cards.append('<section class="painel-editorial"><div class="pw-card-head"><h3>{}<span>{}</span></h3><a href="{}" target="_self">{} &nbsp;→</a></div>{}</section>'.format(e(titulo),temporada,e(link),label,standings_table(snapshot, teams)))
    return '<div class="pw-standings">{}</div>'.format(''.join(cards))


def visao_geral(corrida, paineis, foto, mapa, alt, clima=None):
    info = paineis['circuit_info']
    metrics = [('Comprimento',info.get('comprimento_km'),' km'),('Curvas',info.get('curvas'),''),('Voltas',info.get('voltas'),''),('Distância da corrida',info.get('distancia_corrida_km'),' km')]
    metric_html = ''.join('<div><small>{}</small><strong>{}</strong></div>'.format(label,e((('{:.1f}'.format(value) if label == 'Distância da corrida' else str(value)).replace('.',','))+unit if value is not None else '—')) for label,value,unit in metrics)
    technical = [('Primeiro GP',info.get('primeiro_gp')),('Sentido',info.get('sentido')),('Altitude',str(info['altitude_m'])+' m' if info.get('altitude_m') is not None else None),('Zonas de DRS',info.get('zonas_drs')),('Recorde de corrida',info.get('recorde_volta'))]
    details = ''.join('<div><dt>{}</dt><dd title="{}">{}</dd></div>'.format(label,e(value),e(value.split(' · ')[0]+' ('+value.rsplit('(',1)[-1] if label == 'Recorde de corrida' and value and ' · ' in value else value)) for label,value in technical)
    photo_html = '<img src="{}" alt="{}">'.format(foto,e(alt)) if foto else '<p>Imagem do circuito indisponível.</p>'
    if 'gerada por IA' in alt:
        photo_html += '<span class="pw-image-label">Ilustração IA</span>'
    map_html = '<img src="{}" alt="Mapa do circuito {}">'.format(mapa,e(corrida['circuito_nome'])) if mapa else '<p>Mapa do circuito indisponível.</p>'
    length = str(info.get('comprimento_km')).replace('.',',')+' km' if info.get('comprimento_km') is not None else 'Comprimento não documentado'
    temperatura, nota_clima = '—', 'Clima não disponível'
    media = (clima or {}).get('resumo', {}).get('temperatura_media_c')
    if isinstance(media, (int, float)) and not isinstance(media, bool) and math.isfinite(media):
        temperatura = '{:.1f} °C'.format(media).replace('.', ',')
        nota_clima = 'Open-Meteo · média do período histórico'
    return '<section class="pw-overview" aria-label="Visão geral do circuito"><div class="pw-track"><figure class="hero-circuito">{}<figcaption class="hero-sobreposicao"><p class="circuito-rotulo">Circuito</p><h2>{}</h2><div class="pw-track-metrics">{}</div></figcaption></figure><section class="mapa-circuito" aria-label="Mapa do circuito"><div class="mapa-meta"><strong>{}</strong>{}<span>{}</span></div>{}</section></div><div class="coluna-circuito"><section class="painel-editorial"><h3>Condições disponíveis</h3><p>{}</p><div class="pw-weather"><span class="pw-weather-icon" aria-hidden="true">partly_cloudy_day</span><div><strong>{}</strong><p>{}</p></div></div></section><section class="painel-editorial"><h3>Informações do circuito</h3><dl class="pw-circuit-info">{}</dl></section></div></section>'.format(photo_html,e(corrida['circuito_nome']),metric_html,e(corrida['cidade']),e(COUNTRIES.get(corrida['pais'],corrida['pais'])),e(length),map_html,e(data_editorial(corrida['data'])),e(temperatura),e(nota_clima),details)
