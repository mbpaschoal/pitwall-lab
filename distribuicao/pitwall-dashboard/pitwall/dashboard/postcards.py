"""Place-specific covers composed from original linework and approved photos."""
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from pitwall.paths import PROJECT_ROOT
from pitwall.i18n import language, translate
from pitwall.dashboard.destination_art import DESTINATIONS, artwork_svg
from pitwall.dashboard.journey import race_identity
from pitwall.dashboard.media import circuit_photo_source


def _link(label, url):
    if not isinstance(url, str) or urlsplit(url).scheme not in ('https', 'http'):
        return escape(str(label))
    return '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(
        escape(url, quote=True), escape(str(label)))


def _credits(photo, destination, has_photo):
    parts = []
    if has_photo:
        author = photo.get('autor') or photo.get('credito') or translate('Fonte')
        parts.append('<p>{}: {}. {}</p>'.format(
            escape(translate('Imagem')), _link(author, photo.get('pagina')),
            _link(photo.get('licenca', translate('Fonte')), photo.get('url_licenca') or photo.get('pagina'))))
        parts.append('<p>{}</p>'.format(escape(translate('Imagem ilustrativa; não documenta o GP selecionado.'))))
    if destination:
        motif = destination.motif[language() == 'en']
        parts.append('<p>{}: {}.</p>'.format(escape(translate('Arte editorial original do Pitwall Lab')), escape(motif)))
        if destination.reference:
            parts.append('<p>{}</p>'.format(_link(translate('Referência visual'), destination.reference)))
    return '<details class="pc-credits"><summary>{}</summary><div>{}</div></details>'.format(
        escape(translate('Imagem e referências')), ''.join(parts))


def cover(race, year, forecast=False, note='', assets=None, root=PROJECT_ROOT):
    """Render an identified place without changing any event or forecast record."""
    from pitwall.dashboard.components import data_editorial

    circuit_id = race.get('circuito_id', '')
    destination = DESTINATIONS.get(circuit_id)
    _, event_name = race_identity(race['corrida'], language())
    place = destination.name[language() == 'en'] if destination else race.get('cidade') or event_name
    heading = translate('Previsões') if forecast else place
    subtitle = (translate('A leitura de {} começa com três cartas fechadas.').format(place)
                if forecast else race.get('circuito_nome', ''))
    palette = destination.palette if destination else ('#e7f3fc','#08172d','#c11b27','#b8cbd9')
    paper, ink, accent, second = palette
    frame = destination.frame if destination else 'plain'
    position = destination.photo_position if destination else 'center'
    photo = (assets or {}).get('foto') or {}
    source = circuit_photo_source(Path(root), circuit_id, photo) if photo else ''

    # A circuit illustration does not identify one of the sealed predictions.
    # Full photo provenance remains in the explicit credit disclosure.
    alt = translate('Imagem ilustrativa do circuito de {}.').format(place)
    if not forecast:
        original_alt = (photo.get('alt_en') if language() == 'en' else (assets or {}).get('alt_foto'))
        alt = original_alt or alt
    image = ('<img class="pc-photo" src="{}" alt="{}" style="object-position:{}" decoding="async">'.format(
        escape(source, quote=True), escape(alt, quote=True), escape(position, quote=True))) if source else ''
    image_note = translate('Imagem ilustrativa do circuito' if source else 'Imagem indisponível')
    style = '--pc-paper:{};--pc-ink:{};--pc-accent:{};--pc-second:{}'.format(paper, ink, accent, second)
    date = str(race.get('data') or '')
    date_label = translate(data_editorial(date)) if date else ''
    description = '<p class="pc-note">{}</p>'.format(escape(translate(note))) if note else ''
    return (
        '<section class="pw-postcard fan-hero pc-{}" data-place="{}" data-hero-kind="{}" style="{}" aria-label="{}">'
        '<div class="pc-copy fan-hero-copy"><h1>{}</h1><p class="pc-intro">{}</p>{}</div>'
        '<div class="pc-scene">{}<div class="pc-art-plane" aria-hidden="true"></div>{}'
        '<span class="pc-photo-note">{}</span></div>'
        '<footer class="pc-footer"><time datetime="{}">{}</time>{}</footer></section>'
    ).format(
        frame, escape(circuit_id, quote=True), 'forecast' if forecast else 'race', style,
        escape(race['corrida'], quote=True), escape(heading), escape(subtitle), description,
        image, artwork_svg(circuit_id), escape(image_note), escape(date, quote=True), escape(date_label),
        _credits(photo, destination, bool(source)))
