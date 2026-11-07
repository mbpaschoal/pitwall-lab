"""Complete gouache scenes, readable copy and explicit image provenance."""
from html import escape
from urllib.parse import urlsplit

from pitwall.paths import PROJECT_ROOT
from pitwall.i18n import language, translate
from pitwall.dashboard.destination_art import DESTINATIONS
from pitwall.dashboard.illustrations import illustration
from pitwall.dashboard.journey import race_identity


def _link(label, url):
    if not isinstance(url, str) or urlsplit(url).scheme not in ('https', 'http'):
        return escape(str(label))
    return '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(
        escape(url, quote=True), escape(str(label)))


def _credits(art, destination):
    parts = ['<p>{}</p>'.format(escape(translate('Ilustração em guache gerada com IA para o Pitwall Lab.'))),
             '<p>{}</p>'.format(escape(translate('Interpretação artística; não documenta o GP selecionado.')))]
    if destination:
        parts.append('<p>{}.</p>'.format(escape(destination.motif[language() == 'en'])))
    references = art.get('reference_urls', []) if art else []
    links = [_link(urlsplit(url).netloc.removeprefix('www.'), url) for url in references
             if isinstance(url, str) and urlsplit(url).scheme in ('http', 'https')]
    if links:
        parts.append('<p>{}: {}.</p>'.format(escape(translate('Referências visuais')), ', '.join(links)))
    return '<details class="pc-credits"><summary>{}</summary><div>{}</div></details>'.format(
        escape(translate('Imagem e referências')), ''.join(parts))


def cover(race, year, forecast=False, note='', assets=None, root=PROJECT_ROOT):
    """Artwork is separate from event data, original photos and sealed cards."""
    from pitwall.dashboard.components import data_editorial

    circuit_id = race.get('circuito_id', '')
    destination = DESTINATIONS.get(circuit_id)
    _, event_name = race_identity(race['corrida'], language())
    place = destination.name[language() == 'en'] if destination else race.get('cidade') or event_name
    heading = translate('Previsões') if forecast else place
    subtitle = place if forecast else race.get('circuito_nome', '')
    art = illustration(root, circuit_id)
    copy = '<div class="pc-copy fan-hero-copy"><h1>{}</h1><p class="pc-intro">{}</p></div>'.format(
        escape(heading), escape(subtitle))
    if art:
        scene = ('<figure class="pc-scene"><div class="pc-image-frame">'
                 '<img class="pc-illustration" src="{}" alt="{}" width="{}" height="{}" '
                 'decoding="async" fetchpriority="high">{}'
                 '</div><figcaption>{}</figcaption></figure>').format(
            escape(art['src'], quote=True), escape(art['alt'][language() == 'en'], quote=True),
            art['width'], art['height'], copy, escape(translate('Ilustração editorial')))
    else:
        scene = '<div class="pc-art-unavailable">{}<p>{}</p></div>'.format(
            copy, escape(translate('Ilustração indisponível')))
    description = '<p class="pc-note">{}</p>'.format(escape(translate(note))) if note else ''
    date = str(race.get('data') or '')
    date_label = translate(data_editorial(date)) if date else ''
    return (
        '<section class="pw-postcard fan-hero" data-place="{}" data-hero-kind="{}" aria-label="{}">{}'
        '<footer class="pc-footer"><div class="pc-event-meta"><time datetime="{}">{}</time>{}</div>{}</footer></section>'
    ).format(escape(circuit_id, quote=True), 'forecast' if forecast else 'race',
             escape(race['corrida'], quote=True), scene, escape(date, quote=True),
             escape(date_label), description, _credits(art, destination))
