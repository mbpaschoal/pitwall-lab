"""Fan journey presentation: canonical links, never new data or inference."""
from html import escape
from urllib.parse import urlencode


def race_identity(name, lang='pt'):
    """Shared country cue and short label; unknown events keep their own name."""
    short = name.replace('Grand Prix','').strip()
    flags={'Bahrain':'🇧🇭','Saudi Arabian':'🇸🇦','Japanese':'🇯🇵','Chinese':'🇨🇳','Australian':'🇦🇺','Miami':'🇺🇸','Emilia Romagna':'🇮🇹','Monaco':'🇲🇨','Spanish':'🇪🇸','Canadian':'🇨🇦','Austrian':'🇦🇹','British':'🇬🇧','Belgian':'🇧🇪','Hungarian':'🇭🇺','Dutch':'🇳🇱','Italian':'🇮🇹','Azerbaijan':'🇦🇿','Singapore':'🇸🇬','United States':'🇺🇸','Mexico City':'🇲🇽','São Paulo':'🇧🇷','Brazilian':'🇧🇷','Las Vegas':'🇺🇸','Qatar':'🇶🇦','Abu Dhabi':'🇦🇪','Madrid':'🇪🇸'}
    localized={'Bahrain':('Bahrein','Bahrain'),'Saudi Arabian':('Arábia Saudita','Saudi Arabia'),'Japanese':('Japão','Japan'),'Chinese':('China','China'),'Australian':('Austrália','Australia'),'Emilia Romagna':('Emília-Romanha','Emilia Romagna'),'Spanish':('Espanha','Spain'),'Canadian':('Canadá','Canada'),'Austrian':('Áustria','Austria'),'British':('Grã-Bretanha','Britain'),'Belgian':('Bélgica','Belgium'),'Hungarian':('Hungria','Hungary'),'Dutch':('Países Baixos','Netherlands'),'Italian':('Itália','Italy'),'Azerbaijan':('Azerbaijão','Azerbaijan'),'United States':('EUA','USA'),'Mexico City':('México','Mexico'),'Brazilian':('Brasil','Brazil'),'Singapore':('Singapura','Singapore'),'Qatar':('Catar','Qatar')}
    return flags.get(short,''),localized.get(short,(short,short))[1 if lang=='en' else 0]


def masthead(lang='pt'):
    href='?'+urlencode(dict(tela='Corridas',lang=lang))
    return '<header class="journey-masthead"><a href="{}" target="_self" aria-label="Pitwall Lab">Pitwall Lab</a><p>Dados · contexto · mais F1</p></header>'.format(escape(href,quote=True))


def calendar(options, year, selected, screen='Corridas', lang='pt'):
    """Show nearby events; the native GP selector retains the entire calendar."""
    indices = [i for i, item in enumerate(options) if item['valor'] == selected]
    index = indices[0] if indices else 0
    start = max(0,min(index-1,len(options)-7))
    window = options[start:start+7]
    links = []
    for offset,item in enumerate(window,start):
        current = item['valor'] == selected
        href = '?' + urlencode(dict(tela=screen,temporada=year,gp=item['rodada'],lang=lang))
        flag,displayed=race_identity(item['corrida'],lang)
        flag=flag or '{:02d}'.format(item['rodada'])
        links.append('<a href="{}" target="_self" data-distance="{}" title="{}"{}><span>{}</span>{}</a>'.format(
            escape(href,quote=True),offset-index,escape(item['corrida'],quote=True),
            ' aria-current="true"' if current else '',flag,escape(displayed)))
    return '<nav class="journey-calendar" aria-label="{}">{}</nav>'.format('Grand Prix calendar' if lang=='en' else 'Calendário de GPs',''.join(links))


