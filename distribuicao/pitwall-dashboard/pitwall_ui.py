"""Composição editorial compartilhada entre temporadas; sem inferência ou rede."""
import base64
import math
from datetime import date
from html import escape
from urllib.parse import urlencode
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


def link_interno(temporada=None, rodada=None, tela='Corridas', aba=None, documento=None):
    parametros = {'tela': tela}
    if temporada is not None:
        parametros['temporada'] = temporada
    if rodada is not None:
        parametros['gp'] = rodada
    if aba:
        parametros['aba'] = aba
    if documento:
        parametros['documento'] = documento
    return '/?' + urlencode(parametros)


def cabecalho(corrida, temporada, status):
    if corrida.get('estado_previsao') == 'previsao_registrada':
        detalhe = 'Previsão registrada antes da corrida.'
    elif status == 'Resultado observado' or corrida.get('estado_previsao') == 'ensaio_retrospectivo':
        detalhe = 'Estudo retrospectivo com dados históricos.'
    elif status == 'Aguardando dados':
        detalhe = 'Aguardando dados oficiais.'
    else:
        detalhe = ''
    return '<section class="gp-cabecalho"><div class="gp-titulo"><h1>{}</h1><div class="gp-meta" title="{}"><span>{}</span><b aria-hidden="true">·</b><span>{}</span><b aria-hidden="true">·</b><span>{}</span></div></div><div class="gp-status-area"><div class="gp-status">{}</div><p>{}</p></div></section>'.format(
        e(corrida['corrida']),e('Temporada {} · {}, {} · {}'.format(temporada,corrida['cidade'],corrida['pais'],corrida['data'])),e(corrida['cidade']),e(COUNTRIES.get(corrida['pais'],corrida['pais'])),e(data_editorial(corrida['data'])),e(status),e(detalhe))


def _pontos(valor):
    return '{:g}'.format(float(valor))


def standings_table(snapshot, teams=False):
    classificacao = snapshot.get('classificacao', []) if snapshot.get('disponivel') else []
    if not classificacao:
        return '<p class="pw-empty-note">Classificação desta rodada indisponível.</p>'
    vitorias = any(item.get('vitorias') is not None for item in classificacao)
    titulos = ['Pos.', 'Equipe' if teams else 'Piloto']
    if not teams:
        titulos.append('Equipe')
    titulos.append('Pontos')
    if vitorias:
        titulos.append('Vitórias')
    rows = []
    for item in classificacao:
        color = TEAM_COLORS.get(item.get('equipe_id') or (item.get('equipe_ids') or [''])[0], '#7a8ca5')
        label = ('<span class="barra-equipe" style="background:{}"></span>{}'.format(color,e(item['equipe'])) if teams
                 else '<span class="pw-flag" aria-hidden="true">{}</span>{}'.format(FLAGS.get(item.get('nacionalidade'),''),e(item['piloto'])))
        cells = [e(item.get('posicao')), label]
        if not teams:
            cells.append('<span class="barra-equipe" style="background:{}"></span>{}'.format(color,e(item.get('equipe'))))
        cells.append(e(_pontos(item['pontos'])))
        if vitorias:
            cells.append(e(item.get('vitorias')))
        rows.append('<tr>{}</tr>'.format(''.join('<td>{}</td>'.format(c) for c in cells)))
    return '<div class="tabela-editorial"><table class="{}" aria-label="{}"><thead><tr>{}</tr></thead><tbody>{}</tbody></table></div>'.format(
        'pw-team-table' if teams else 'pw-drivers-table', 'Campeonato de construtores' if teams else 'Campeonato de pilotos',
        ''.join('<th>{}</th>'.format(e(t)) for t in titulos), ''.join(rows))


def campeonatos(paineis, temporada):
    cards = []
    for teams,titulo,ancora in [(False,'Campeonato de pilotos','campeonato-completo'),(True,'Campeonato de construtores','equipes-completo')]:
        snapshot = paineis['constructor_standings' if teams else 'driver_standings']
        cards.append('<section class="painel-editorial" id="{}"><div class="pw-card-head"><h3>{} <span>{}</span></h3></div>{}</section>'.format(
            ancora, e(titulo), temporada, standings_table(snapshot, teams)))
    return '<p class="pw-standings-note">Classificação após a rodada {}.</p><div class="pw-standings">{}</div>'.format(paineis['rodada'], ''.join(cards))


def visao_geral(corrida, paineis, foto, mapa, alt, clima=None):
    info = paineis['circuit_info']
    metrics = [('Comprimento',info.get('comprimento_km'),' km'),('Curvas',info.get('curvas'),''),('Voltas',info.get('voltas'),''),('Distância da corrida',info.get('distancia_corrida_km'),' km')]
    metric_html = ''.join('<div><small>{}</small><strong>{}</strong></div>'.format(label,e((('{:.1f}'.format(value) if label == 'Distância da corrida' else str(value)).replace('.',','))+unit if value is not None else '—')) for label,value,unit in metrics if value is not None)
    technical = [('Primeiro GP',info.get('primeiro_gp')),('Sentido',info.get('sentido')),('Altitude',str(info['altitude_m'])+' m' if info.get('altitude_m') is not None else None),('Zonas de DRS',info.get('zonas_drs')),('Recorde de corrida',info.get('recorde_volta'))]
    details = ''.join('<div><dt>{}</dt><dd title="{}">{}</dd></div>'.format(label,e(value),e(value.split(' · ')[0]+' ('+value.rsplit('(',1)[-1] if label == 'Recorde de corrida' and value and ' · ' in value else value)) for label,value in technical if value is not None) or '<p>Informações técnicas indisponíveis.</p>'
    photo_html = '<img src="{}" alt="{}">'.format(foto,e(alt)) if foto else '<p>Imagem do circuito indisponível.</p>'
    if 'gerada por IA' in alt:
        photo_html += '<span class="pw-image-label">Ilustração IA</span>'
    map_html = '<img src="{}" alt="Mapa do circuito {}">'.format(mapa,e(corrida['circuito_nome'])) if mapa else '<p>Mapa do circuito indisponível.</p>'
    temperatura, nota_clima = '—', 'Clima não disponível'
    media = (clima or {}).get('resumo', {}).get('temperatura_media_c')
    if isinstance(media, (int, float)) and not isinstance(media, bool) and math.isfinite(media):
        temperatura = '{:.1f} °C'.format(media).replace('.', ',')
        nota_clima = 'Open-Meteo · média histórica'
    return '<section class="pw-overview" aria-label="Visão geral do circuito"><div class="pw-track"><figure class="hero-circuito">{}<figcaption class="hero-sobreposicao"><p class="circuito-rotulo">Circuito</p><h2>{}</h2><div class="pw-track-metrics">{}</div></figcaption></figure><section class="mapa-circuito" aria-label="Mapa do circuito"><div class="mapa-meta"><strong>Traçado do circuito</strong></div>{}</section></div><div class="coluna-circuito"><section class="painel-editorial"><h3><a href="{}" target="_top">Clima e medições</a></h3><div class="pw-weather"><span class="pw-weather-icon" aria-hidden="true">partly_cloudy_day</span><div><strong>{}</strong><p>{}</p></div></div></section><section class="painel-editorial"><h3>Informações do circuito</h3><dl class="pw-circuit-info">{}</dl></section></div></section>'.format(photo_html,e(corrida['circuito_nome']),metric_html,map_html,e(link_interno(paineis['temporada'], paineis['rodada'], aba='Clima')),e(temperatura),e(nota_clima),details)
