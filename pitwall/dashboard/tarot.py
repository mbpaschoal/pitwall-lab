"""Optional visual reading of stored probabilities. No draw, inference or ranking."""
import base64
from html import escape
import math
from urllib.parse import urlencode

from pitwall.i18n import translate, language
from pitwall.dashboard.tarot_catalog import (
    TarotCatalogError, select_cards, team_id,
)

def cards_html(rows, root, year=None, round_=None):
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
    return '<div class="tarot-cards">{}</div>'.format(''.join(cards))


def render(st, root, rows, year, round_, registered):
    if not rows:return

    def open_cards():
        st.query_params['cartas']='1'

    def dismiss():
        st.query_params.pop('cartas',None)

    st.button('Abrir as cartas do GP',key='open_tarot',on_click=open_cards)
    if st.query_params.get('cartas')!='1':return

    @st.dialog(translate('As cartas do GP'),width='large',on_dismiss=dismiss)
    def show():
        st.caption('Previsão registrada antes da corrida.' if registered else 'Estudo retrospectivo; não é previsão emitida antes da corrida.')
        st.markdown(cards_html(rows,root,year,round_),unsafe_allow_html=True)
        st.caption('Arte gerada por IA. As cartas não indicam a ordem de chegada. Consulte os percentuais na tabela de previsões.')
        href='?'+urlencode(dict(tela='Previsões',temporada=year,gp=round_,lang=language()))
        st.markdown('<a class="tarot-back" href="{}" target="_self">{}</a>'.format(escape(href,quote=True),escape(translate('Ver todos os pilotos e como calculamos'))),unsafe_allow_html=True)
    show()
