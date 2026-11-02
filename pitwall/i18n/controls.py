"""Upper-right BR/GB controls retain language, GP and tab without iframe navigation."""

from . import language, set_language
from pitwall.version import version


def _browser_accessibility(st, selected):
    """Bridge the native Streamlit document, without changing widget callbacks.

    Only the validated locale is interpolated. The iframe has same-origin access
    to its immediate app parent, including inside the Cloud hosting iframe.
    """
    import streamlit.components.v1 as components

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
        scroll();
      }
      function schedule() { if (!pending) { pending = true; host.requestAnimationFrame(update); } }
      function scroll() {
        // The header controls travel with the page instead of obscuring rows.
        const y = doc.querySelector('.stMain')?.scrollTop || 0;
        doc.querySelectorAll('[class*="st-key-pw_language_switch_"]').forEach(el => {
          el.style.transform = `translateY(${-y}px)`;
        });
      }
      function focus(event) {
        if (event.target.closest('[class*="st-key-pw_language_switch_"]')) {
          const main = doc.querySelector('.stMain');
          if (main) main.scrollTop = 0;
          scroll();
        }
      }
      function skip(event) {
        if (!event.target.closest('.pw-skip-link')) return;
        const target = doc.querySelector('#pw-main-content');
        if (target) { event.preventDefault(); target.focus(); target.scrollIntoView({block:'start'}); }
      }
      const observer = new MutationObserver(schedule);
      observer.observe(doc.body, {childList:true, subtree:true});
      doc.addEventListener('scroll', scroll, true);
      doc.addEventListener('focusin', focus);
      doc.addEventListener('click', skip);
      host.pitwallAccessibility = () => {
        observer.disconnect();
        doc.removeEventListener('scroll', scroll, true);
        doc.removeEventListener('focusin', focus);
        doc.removeEventListener('click', skip);
      };
      update();
    })();
    </script>'''.replace('LOCALE', selected)
    with st.container(key='pw-a11y-bridge'):
        components.html(script, height=0, tab_index=-1)


def initialize(st):
    requested = st.query_params.get("lang", st.session_state.get("_language", "pt"))
    selected = set_language(requested)
    previous = st.session_state.get("_rendered_language", selected)
    st.session_state["_preserve_language_widgets"] = previous != selected
    st.session_state["_rendered_language"] = selected
    st.session_state["_language"] = selected
    _browser_accessibility(st, selected)


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
