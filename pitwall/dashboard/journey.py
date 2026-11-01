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
    start = max(0,min(index-1,len(options)-7))
    window = options[start:start+7]
    flags={'bahrain':'🇧🇭','saudi':'🇸🇦','japan':'🇯🇵','chinese':'🇨🇳','australian':'🇦🇺','miami':'🇺🇸','emilia':'🇮🇹','monaco':'🇲🇨','spanish':'🇪🇸','canadian':'🇨🇦','austrian':'🇦🇹','british':'🇬🇧','belgian':'🇧🇪','hungarian':'🇭🇺','dutch':'🇳🇱','italian':'🇮🇹','azerbaijan':'🇦🇿','singapore':'🇸🇬','united states':'🇺🇸','mexico':'🇲🇽','são paulo':'🇧🇷','brazil':'🇧🇷','las vegas':'🇺🇸','qatar':'🇶🇦','abu dhabi':'🇦🇪','madrid':'🇪🇸'}
    links = []
    for offset,item in enumerate(window,start):
        current = item['valor'] == selected
        href = '?' + urlencode(dict(tela=screen,temporada=year,gp=item['rodada'],lang=lang))
        short = item['corrida'].replace('Grand Prix','').strip()
        localized={'United States':('EUA','USA'),'Mexico City':('México','Mexico'),'Brazilian':('Brasil','Brazil'),'São Paulo':('São Paulo','São Paulo'),'Singapore':('Singapura','Singapore'),'Qatar':('Catar','Qatar')}
        displayed=localized.get(short,(short,short))[1 if lang=='en' else 0]
        flag=next((value for key,value in flags.items() if key in short.lower()),'{:02d}'.format(item['rodada']))
        links.append('<a href="{}" target="_self" data-distance="{}" title="{}"{}><span>{}</span>{}</a>'.format(
            escape(href,quote=True),offset-index,escape(item['corrida'],quote=True),
            ' aria-current="true"' if current else '',flag,escape(displayed)))
    return '<nav class="journey-calendar" aria-label="{}">{}</nav>'.format('Grand Prix calendar' if lang=='en' else 'Calendário de GPs',''.join(links))


