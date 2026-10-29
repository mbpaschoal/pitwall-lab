"""Native BR/GB controls retain language, GP and tab without iframe navigation."""

from . import language, set_language
from pitwall.version import version


def initialize(st):
    requested = st.query_params.get("lang", st.session_state.get("_language", "pt"))
    selected = set_language(requested)
    previous = st.session_state.get("_rendered_language", selected)
    st.session_state["_preserve_language_widgets"] = previous != selected
    st.session_state["_rendered_language"] = selected
    st.session_state["_language"] = selected


def render(st, active_tab=None):
    params = {
        key: st.query_params[key]
        for key in ("temporada", "gp", "tela", "documento")
        if key in st.query_params
    }
    for key in ("temporada", "tela"):
        if st.session_state.get(key) is not None:
            params[key] = st.session_state[key]
    if st.session_state.get("gp"):
        params["gp"] = str(st.session_state["gp"]).split(":")[-1]
    if active_tab is not None:
        params["aba"] = active_tab

    def choose(selected):
        st.session_state["_language"] = selected
        st.query_params.update(dict(params, lang=selected))

    # Each tab owns one control; only the active tab is visible. Stable keys keep
    # callbacks separate, including when a document is opened in its own session.
    suffix = (active_tab or "page").encode("utf-8").hex()
    key = "pw_language_switch_" + suffix
    with st.container(key=key):
        label, brazil, britain = st.columns([1.4, 1, 1], gap="small")
        label.caption("v" + version())
        for column, code, flag, title in [
            (brazil, "pt", "🇧🇷", "Português"),
            (britain, "en", "🇬🇧", "English"),
        ]:
            column.button(
                flag,
                help=title,
                key="pw_language_button_" + suffix + "_" + code,
                on_click=choose,
                args=(code,),
                type="primary" if language() == code else "secondary",
            )
