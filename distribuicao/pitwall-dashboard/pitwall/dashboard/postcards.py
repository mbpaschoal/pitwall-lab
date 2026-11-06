"""Original abstract destination covers. Geography is presentation, never a feature."""
from html import escape
from pitwall.i18n import translate, language
from pitwall.dashboard.journey import race_identity

# paper, text, architecture, sun, secondary plane, illustration family
THEMES = {
    'Australia': ('#b6d7e8', '#193f45', '#247b7a', '#f4c654', '#c36147', 'waves'),
    'Austria': ('#d8e4dd', '#263d35', '#527666', '#be4b47', '#90a4aa', 'mountains'),
    'Azerbaijan': ('#f1d0a0', '#183d4b', '#245b70', '#be523c', '#73a7ac', 'city'),
    'Bahrain': ('#ead1b2', '#4b333a', '#92584d', '#c44b44', '#75526c', 'arches'),
    'Belgium': ('#d9dfaa', '#223e37', '#48735a', '#d4a82f', '#7f9e79', 'mountains'),
    'Brazil': ('#154a3f', '#fff0b8', '#95cce7', '#f4cf58', '#367761', 'paulista'),
    'Canada': ('#e1dfc8', '#293e3d', '#326451', '#bf4846', '#7c9b92', 'mountains'),
    'China': ('#e7c2a3', '#492b31', '#9e4541', '#e9b645', '#35556d', 'arches'),
    'Hungary': ('#ddd1b6', '#3d444b', '#a36551', '#d0a04a', '#5b7d7a', 'arches'),
    'Italy': ('#c8d9bd', '#254b3b', '#55765b', '#c65042', '#d4ac52', 'arches'),
    'Japan': ('#f1ece2', '#25354b', '#243e6a', '#c43b3e', '#738baa', 'mountains'),
    'Malaysia': ('#d4e0bd', '#1d4c45', '#3b7964', '#e6ae48', '#5288a0', 'waves'),
    'Mexico': ('#edb6cb', '#123e36', '#075744', '#f7c74d', '#2649a6', 'arches'),
    'Monaco': ('#e1c9b7', '#2d404c', '#658da0', '#c65a4f', '#a07e69', 'city'),
    'Netherlands': ('#e6c9a5', '#30465a', '#657f99', '#d77534', '#4f7290', 'waves'),
    'Qatar': ('#e9d5b8', '#522c3c', '#803c53', '#d29f4c', '#ac7c68', 'arches'),
    'Saudi Arabia': ('#d4dec6', '#244337', '#53705a', '#d7ac50', '#8eaaa4', 'city'),
    'Singapore': ('#243f4b', '#f5e7c7', '#71a397', '#de7757', '#487b86', 'city'),
    'Spain': ('#edc985', '#56392e', '#a65a43', '#dca22b', '#3d7790', 'arches'),
    'UAE': ('#ead8b6', '#364e4b', '#68817a', '#d29d40', '#b57f62', 'city'),
    'UK': ('#ccd6d3', '#2e4052', '#547562', '#b6534e', '#718f9f', 'waves'),
    'USA': ('#c9d4e4', '#283a58', '#4f6c9b', '#d16e48', '#a1b8c8', 'city'),
}


def cover(race, year, forecast=False, note=''):
    theme = THEMES.get(race.get('pais'), ('#d4e0e6', '#233d4c', '#547887', '#d5ac55', '#91aeb9', 'waves'))
    paper, ink, plane, sun, second, family = theme
    _, title = race_identity(race['corrida'], language())
    # Multiple events in one country keep their own city/circuit identity.
    heading = race.get('cidade') if race.get('pais') in ('USA', 'Italy', 'Spain') else title
    if race.get('circuito_id') == 'interlagos':
        heading = 'São Paulo'
    heading = heading or title
    label = translate('Previsões') if forecast else translate('Corridas')
    subtitle = translate('Três cartas guardam a leitura deste GP. Revele uma de cada vez.') if forecast else '{} {} · {} · {}'.format(translate('Temporada'), year, race.get('cidade', ''), race.get('data', ''))
    style = '--pc-paper:{};--pc-ink:{};--pc-plane:{};--pc-sun:{};--pc-second:{}'.format(paper, ink, plane, sun, second)
    return '<section class="pw-postcard fan-hero pc-{}" data-hero-kind="{}" style="{}" aria-label="{}"><div class="pc-copy"><p class="pc-area">{} / {}</p><h1>{}</h1><p>{}</p><small>{}</small></div><div class="pc-scene" aria-hidden="true"><div class="pc-sun"></div><div class="pc-building"></div><div class="pc-arch"></div><div class="pc-road"></div></div><div class="pc-strip"><span>{}</span><span>{}</span></div></section>'.format(
        family, 'forecast' if forecast else 'race', style, escape(race['corrida'], quote=True), escape(label), escape(title), escape(heading), escape(subtitle), escape(translate(note)),
        escape(race.get('circuito_nome', '')), escape(str(race.get('data', ''))))
