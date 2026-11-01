"""Fan journey presentation: canonical links, never new data or inference."""
from html import escape
from urllib.parse import urlencode


def masthead(lang='pt'):
    href='?'+urlencode(dict(tela='Corridas',lang=lang))
    return '<header class="journey-masthead"><a href="{}" target="_self" aria-label="Pitwall Lab">Pitwall Lab</a><p>Dados · contexto · mais F1</p></header>'.format(escape(href,quote=True))


def calendar(options, year, selected, screen='Corridas', lang='pt'):
    """Show nearby events; the native GP selector retains the entire calendar."""
    indices = [i for i, item in enumerate(options) if item['valor'] == selected]
    index = indices[0] if indices else 0
    start = max(0,min(index-3,len(options)-7))
    window = options[start:start+7]
    links = []
    for offset,item in enumerate(window,start):
        current = item['valor'] == selected
        href = '?' + urlencode(dict(tela=screen,temporada=year,gp=item['rodada'],lang=lang))
        short = item['corrida'].replace('Grand Prix','').strip()
        links.append('<a href="{}" target="_self" data-distance="{}" title="{}"{}><span>{:02d}</span>{}</a>'.format(
            escape(href,quote=True),offset-index,escape(item['corrida'],quote=True),
            ' aria-current="true"' if current else '',item['rodada'],escape(short)))
    return '<nav class="journey-calendar" aria-label="Calendário de GPs">{}</nav>'.format(''.join(links))


