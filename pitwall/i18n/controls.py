"""Upper-right BR/GB controls retain language, GP and tab without iframe navigation."""

from . import language, set_language
from pitwall.version import version
from html import escape
from urllib.parse import urlencode


def _language_params(st, active_tab=None):
    """The native callback and its link alternative use identical context."""
    keys = ("temporada", "gp", "tela", "documento", "aba", "visao", "secao", "piloto", "rival",
            "duelo_condicao", "faixas", "anos", "metrica", "minimo", "condicao", "cartas",
            "origem_tela", "origem_temporada", "origem_gp", "painel", "equipe", "campanha", "campeao",
            "rival_campeao")
    params = {}
    for key in keys:
        if key in st.query_params:
            values = st.query_params.get_all(key)
            params[key] = values if len(values) > 1 else values[0]
    for key in ("temporada", "tela"):
        if st.session_state.get(key) is not None:
            params[key] = st.session_state[key]
    gp = st.session_state.get("gp") or st.session_state.get("_gp_context")
    if gp:
        params["gp"] = str(gp).split(":")[-1]
    if active_tab is not None:
        params["aba"] = active_tab
    return params


def language_link(params, code, selected):
    """A normal same-frame link works without the native Button JS module."""
    if code not in ("pt", "en") or selected not in ("pt", "en"):
        raise ValueError("Unsupported language")
    flag, label = ("🇧🇷", "Português") if code == "pt" else ("🇬🇧", "English")
    return '<a class="pw-language-fallback" href="?{}" target="_self" data-language="{}" lang="{}" aria-label="{} {}"{}>{}</a>'.format(
        escape(urlencode(dict(params, lang=code), doseq=True), quote=True), code, code,
        flag, label, ' aria-current="true"' if selected == code else '', flag)


def _browser_accessibility(st, selected):
    """Bridge the native Streamlit document, without changing widget callbacks.

    Only the validated locale is interpolated. The iframe has same-origin access
    to its immediate app parent, including inside the Cloud hosting iframe.
    """
    script = r'''<script>
    (() => {
      const doc = window.parent.document, host = window.parent;
      const locale = "LOCALE";
      if (host.pitwallAccessibility) host.pitwallAccessibility();
      let pending = false;
      function update() {
        pending = false;
        doc.documentElement.lang = locale;
        doc.querySelectorAll('[class*="st-key-pw_language_button_"] button').forEach(button => {
          const selected = button.closest('[class*="st-key-pw_language_button_"]').className;
          const pt = /_pt(?:\s|$)/.test(selected);
          button.setAttribute('aria-label', pt ? '🇧🇷 Português' : '🇬🇧 English');
          button.setAttribute('lang', pt ? 'pt' : 'en');
          button.setAttribute('aria-pressed', String((pt ? 'pt' : 'en') === locale));
        });
      }
      function schedule() { if (!pending) { pending = true; host.requestAnimationFrame(update); } }
      const observer = new MutationObserver(schedule);
      observer.observe(doc.body, {childList:true, subtree:true});
      host.pitwallAccessibility = () => {
        observer.disconnect();
      };
      update();
    })();
    </script>'''.replace('LOCALE', selected)
    with st.container(key='pw-a11y-bridge'):
        st.iframe(script, height=1, tab_index=-1)


def initialize(st):
    requested = st.query_params.get("lang", st.session_state.get("_language", "pt"))
    selected = set_language(requested)
    previous = st.session_state.get("_rendered_language", selected)
    st.session_state["_preserve_language_widgets"] = previous != selected
    st.session_state["_rendered_language"] = selected
    st.session_state["_language"] = selected
    _browser_accessibility(st, selected)


def render(st, active_tab=None):
    def choose(selected):
        # Read the latest URL at click time: profile filters can update it later
        # in the same run, after this header has been rendered.
        params = _language_params(st, active_tab)
        st.session_state["_language"]=selected
        st.query_params.update(dict(params,lang=selected))

    # One header control retains the active chapter and current view context.
    suffix = (active_tab or "page").encode("utf-8").hex()
    key = "pw_language_switch_" + suffix
    with st.container(key=key):
        label, brazil, britain = st.columns([1.4, 1, 1], gap="small")
        label.caption("v" + version())
        for column, code, flag, title in [
            (brazil, "pt", "🇧🇷", "Português"),
            (britain, "en", "🇬🇧", "English"),
        ]:
            with column.container(key="pw_language_cell_" + suffix + "_" + code):
                st.button(
                    flag,
                    help=title,
                    key="pw_language_button_" + suffix + "_" + code,
                    on_click=choose,
                    args=(code,),
                    type="primary" if language() == code else "secondary",
                )
                st.markdown(language_link(_language_params(st, active_tab), code, language()),
                            unsafe_allow_html=True)
