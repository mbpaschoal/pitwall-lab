"""Optional visual reading of stored probabilities. No draw, inference or ranking."""
import base64
from html import escape
import math
from pathlib import Path
from urllib.parse import urlencode

from pitwall.i18n import translate, language

ART = {'max_verstappen':'verstappen.png','hamilton':'hamilton.png','russell':'russell.png'}
ART_TEAMS = {'max_verstappen': {'Red Bull', 'Red Bull Racing', 'Oracle Red Bull Racing'},
             'hamilton': {'Ferrari'}, 'russell': {'Mercedes'}}
HELMET = '<svg viewBox="0 0 28 28" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" d="M24 15a10 10 0 0 0-20 0v6l8 3h10l2-5H13l-2-6h12M5 15h5M7 21v-3"/></svg>'


def cards_html(rows, root):
    cards = []
    for row in rows:
        value = row.get('probability')
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1:
            continue
        # Artwork includes team colours and labels: never borrow a later team.
        filename = ART.get(row['driver_id']) if row['team'] in ART_TEAMS.get(row['driver_id'], set()) else None
        path = Path(root)/'dashboard_assets/tarot'/filename if filename else None
        if path and path.is_file():
            image = '<img src="data:image/png;base64,{}" alt="{}">'.format(
                base64.b64encode(path.read_bytes()).decode('ascii'),
                escape('{} · {}'.format(row['name'], row['team']), quote=True))
        else:
            image = '<div class="tarot-symbol">{}</div>'.format(HELMET)
            image += '<figcaption><h3>{}</h3><span>{}</span></figcaption>'.format(
                escape(row['name']), escape(row['team']))
        cards.append('<article class="tarot-card"><figure>{}</figure></article>'.format(image))
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
        st.markdown(cards_html(rows,root),unsafe_allow_html=True)
        st.caption('Arte gerada por IA. As cartas não indicam a ordem de chegada. Consulte os percentuais na tabela de previsões.')
        href='?'+urlencode(dict(tela='Previsões',temporada=year,gp=round_,lang=language()))
        st.markdown('<a class="tarot-back" href="{}" target="_self">{}</a>'.format(escape(href,quote=True),escape(translate('Ver todos os pilotos e como calculamos'))),unsafe_allow_html=True)
    show()
