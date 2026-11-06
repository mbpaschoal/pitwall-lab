"""Local motion and same-document navigation; no data or URL mutations."""
from pathlib import Path
from html import escape
from pitwall.i18n import translate


def render():
    from pitwall.i18n.streamlit import st
    st.markdown('<nav class="pw-page-tools" aria-label="{}"><a data-pw-scroll href="#pw-main-content">{}</a><a data-pw-scroll href="#pw-page-top">{}</a><button type="button" data-pw-motion data-reduce="{}" data-enable="{}" data-system="{}">{}</button></nav>'.format(*[escape(translate(s),quote=True) for s in ('Navegação da página','Ir para o conteúdo','Voltar ao topo','Reduzir movimento','Ativar movimento','Movimento reduzido pelo sistema','Reduzir movimento')]),unsafe_allow_html=True)


def install():
    from pitwall.i18n.streamlit import st
    script = (Path(__file__).resolve().parents[2]/'frontend_assets/motion.js').read_text()
    with st.container(key='pw-motion-bridge'):
        st.iframe('<script>'+script+'</script>',height=1,tab_index=-1)
