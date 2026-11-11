"""Fan journey presentation: canonical links, never new data or inference."""
from html import escape
from urllib.parse import urlencode


def navigation_links(params, selected, lang='pt'):
    """Usable links while the native navigation module is still unavailable."""
    labels = (
        ('Corridas', 'Corridas', 'Races'),
        ('Pilotos', 'Pilotos', 'Drivers'),
        ('Campeonato', 'Campeonato', 'Championship'),
        ('Previsões', 'Chances de pódio', 'Podium chances'),
        ('Desempenho', 'Acertos do Lab', 'How the Lab did'),
        ('Metodologia', 'Como funciona', 'How it works'),
    )
    context = {key: value for key, value in params.items()
               if key not in ('documento', 'painel', 'cartas', 'equipe', 'campanha')}
    links = []
    for screen, pt, en in labels:
        query = urlencode(dict(context, tela=screen, lang=lang), doseq=True)
        links.append('<a href="?{}" target="_self" data-screen="{}"{}><span>{}</span></a>'.format(
            escape(query, quote=True), escape(screen, quote=True),
            ' aria-current="page"' if screen == selected else '', escape(en if lang == 'en' else pt)))
    return '<nav class="journey-navigation-fallback" aria-label="{}">{}</nav>'.format(
        'Main navigation' if lang == 'en' else 'Navegação principal', ''.join(links))


def sync_host_query(st):
    """Publish a new frame route through Streamlit's native hosting channel."""
    if not st.session_state.get('_public_query_synced'):
        # A relative HTML link reloads the app frame. Re-emitting its current
        # query also updates the Cloud wrapper, so refresh/share keep that route.
        # An empty update preserves repeated values and reserved embed options.
        st.query_params.update({})
        # HTML navigation starts a new WebSocket/session. Native widget reruns
        # retain this marker and already publish their own query changes.
        st.session_state['_public_query_synced'] = True


_RACE_IDENTITIES = {
    'Bahrain': ('🇧🇭', 'Bahrein', 'Bahrain'),
    'Bahrain in Malaysia': ('🇲🇾', 'Malásia · Sepang', 'Malaysia · Sepang'),
    'Saudi Arabian': ('🇸🇦', 'Arábia Saudita', 'Saudi Arabia'),
    'Japanese': ('🇯🇵', 'Japão', 'Japan'),
    'Chinese': ('🇨🇳', 'China', 'China'),
    'Australian': ('🇦🇺', 'Austrália', 'Australia'),
    'Miami': ('🇺🇸', 'Miami', 'Miami'),
    'Emilia Romagna': ('🇮🇹', 'Emília-Romanha', 'Emilia Romagna'),
    'Monaco': ('🇲🇨', 'Monaco', 'Monaco'),
    'Barcelona': ('🇪🇸', 'Barcelona', 'Barcelona'),
    'Spanish': ('🇪🇸', 'Espanha', 'Spain'),
    'Canadian': ('🇨🇦', 'Canadá', 'Canada'),
    'Austrian': ('🇦🇹', 'Áustria', 'Austria'),
    'British': ('🇬🇧', 'Grã-Bretanha', 'Britain'),
    'Belgian': ('🇧🇪', 'Bélgica', 'Belgium'),
    'Hungarian': ('🇭🇺', 'Hungria', 'Hungary'),
    'Dutch': ('🇳🇱', 'Países Baixos', 'Netherlands'),
    'Italian': ('🇮🇹', 'Itália', 'Italy'),
    'Azerbaijan': ('🇦🇿', 'Azerbaijão', 'Azerbaijan'),
    'Singapore': ('🇸🇬', 'Singapura', 'Singapore'),
    'United States': ('🇺🇸', 'EUA', 'USA'),
    'Mexico City': ('🇲🇽', 'México', 'Mexico'),
    'São Paulo': ('🇧🇷', 'São Paulo', 'São Paulo'),
    'Brazilian': ('🇧🇷', 'Brasil', 'Brazil'),
    'Las Vegas': ('🇺🇸', 'Las Vegas', 'Las Vegas'),
    'Qatar': ('🇶🇦', 'Catar', 'Qatar'),
    'Abu Dhabi': ('🇦🇪', 'Abu Dhabi', 'Abu Dhabi'),
    'Madrid': ('🇪🇸', 'Madrid', 'Madrid'),
}


def race_identity(name, lang='pt'):
    """Use exact event names, preserving a relocated GP's host country."""
    short = ' '.join(name.replace('Grand Prix', '').split())
    flag, pt, en = _RACE_IDENTITIES.get(short, ('', short, short))
    return flag, en if lang == 'en' else pt


def masthead(lang='pt', year=None, round_=None):
    params = dict(tela='Corridas', lang=lang)
    if year in (2024, 2025, 2026) and type(round_) is int and 1 <= round_ <= 24:
        params.update(temporada=year, gp=round_)
    href='?'+urlencode(params)
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


