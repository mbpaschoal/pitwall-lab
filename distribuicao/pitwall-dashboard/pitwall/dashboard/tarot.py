"""Optional visual reading of stored probabilities. No draw, inference or ranking."""
import base64
from html import escape
import math
import hashlib
import json

from pitwall.i18n import translate, language
from pitwall.dashboard.tarot_catalog import (
    TarotCatalogError, select_cards, team_id,
)

def _cards(rows, root, year=None, round_=None):
    """Illustrate the given favorites without calculating or changing their order."""
    eligible = []
    for row in rows:
        value = row.get('probability')
        if (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value) and 0 <= value <= 1):
            eligible.append(row)
    try:
        selected = select_cards(eligible, root, year, round_)
    except TarotCatalogError:
        selected = [dict(row=row, pose_id=None, entry=None, content=None) for row in eligible]
    cards = []
    for item in selected:
        row = item['row']
        entry = item['entry']
        team = team_id(row) or 'unknown'
        pose = '' if item['pose_id'] is None else str(item['pose_id'])
        kind = 'team' if entry else 'missing'
        if item['content'] is not None:
            image = '<img src="data:image/png;base64,{}" alt="{}">'.format(
                base64.b64encode(item['content']).decode('ascii'),
                escape('{} · {}'.format(row['name'], row['team']), quote=True))
        else:
            kind = 'missing'
            missing = ('Illustration unavailable for this team' if language() == 'en'
                       else 'Ilustração indisponível para esta equipe')
            image = '<div class="tarot-art-unavailable">{}</div>'.format(missing)
        # Team labels and framing belong to this GP, not to a driver's current team.
        image += '<figcaption class="tarot-card-label"><h3>{}</h3><span>{}</span></figcaption>'.format(
            escape(row['name']), escape(row['team']))
        cards.append('<article class="tarot-card tarot-team-{} tarot-pose-{}" data-driver-id="{}" data-team-id="{}" data-pose-id="{}" data-artwork-kind="{}"><figure>{}</figure></article>'.format(
            escape(team, quote=True), pose, escape(row['driver_id'], quote=True),
            escape(team, quote=True), pose, kind, image))
    return cards



def cards_html(rows, root, year=None, round_=None):
    return '<div class="tarot-cards">{}</div>'.format(''.join(_cards(rows, root, year, round_)))


def deck_key(rows, year, round_, emission=None):
    payload = dict(year=year, round=round_, emission=emission, rows=rows)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def sealed_cards_html(rows, root, year, round_, emission=None, country=None):
    eligible = [row for row in rows if not isinstance(row.get('probability'), bool)
                and isinstance(row.get('probability'), (int, float))
                and math.isfinite(row['probability']) and 0 <= row['probability'] <= 1]
    faces = _cards(eligible, root, year, round_)
    cards = []
    phrase = translate('Probabilidade individual de pódio neste GP; não indica uma posição de chegada.')
    for index, (row, face) in enumerate(zip(eligible, faces)):
        label = chr(65 + index)
        probability = '{:.1%}'.format(row['probability'])
        if language() == 'pt':
            probability = probability.replace('.', ',')
        payload = '{}<p class="pw-tarot-prob">{} {}</p><p class="pw-tarot-phrase">{}</p><button type="button" data-tarot-hide>{}</button>'.format(face, probability, escape(translate('de chance de pódio')), escape(phrase), escape(translate('Virar para baixo')))
        cards.append('<article class="pw-sealed-card" data-card-index="{i}"><button type="button" class="pw-card-back" data-tarot-reveal aria-label="{reveal}"><span>{card} {label}</span><b aria-hidden="true">PL</b><span>{tap}</span></button><template class="pw-tarot-face" data-pw-face="{payload}"></template><div class="pw-revealed-face" hidden></div></article>'.format(
            i=index, label=label, reveal=escape(translate('Revelar carta') + ' ' + label, quote=True),
            card=escape(translate('Carta')), tap=escape(translate('Toque para revelar')), payload=escape(payload, quote=True),
            prob=probability, chance=escape(translate('de chance de pódio')), phrase=escape(phrase),
            hide=escape(translate('Virar para baixo'))))
    key = deck_key(rows, year, round_, emission)
    back, ink = {'Brazil': ('#154a3f', '#f4cf58'), 'Japan': ('#243e6a', '#f4dfb3'),
                 'Mexico': ('#075744', '#f7d576')}.get(country, ('#192e39', '#dbc893'))
    return '<section class="pw-tarot-reading" data-deck-key="{}" style="--deck-back:{};--deck-ink:{}"><p class="pw-reveal-count" aria-live="polite" data-total="{}" data-label="{}">0 / {}</p><div class="pw-sealed-deck">{}</div></section>'.format(
        key, back, ink, len(cards), escape(translate('cartas reveladas'), quote=True), len(cards), ''.join(cards))


def render(st, root, rows, year, round_, registered, emission=None, country=None):
    if not rows:
        return
    key = deck_key(rows, year, round_, emission)
    opened = st.session_state.setdefault('_tarot_opened', {})

    def open_cards():
        opened[key] = True
        st.query_params['cartas'] = '1'

    if not opened.get(key) and st.query_params.get('cartas') != '1':
        st.button('Ver as cartas deste GP', key='open_tarot', on_click=open_cards, type='primary')
        return
    opened[key] = True
    st.caption('Previsão registrada antes da corrida.' if registered else 'Estudo retrospectivo; não é previsão emitida antes da corrida.')
    st.markdown(sealed_cards_html(rows, root, year, round_, emission, country), unsafe_allow_html=True)
    st.caption('Arte gerada por IA. As cartas não indicam a ordem de chegada.')
