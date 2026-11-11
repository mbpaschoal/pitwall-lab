"""One navigation catalogue for the sidebar and search; routes keep GP context."""
from html import escape
from urllib.parse import urlencode

from pitwall.i18n import translate, in_language

# The IDs are presentation routes, never event identities or model inputs.
GROUPS = (
    ("Previsões", (("forecast", "Previsões deste GP", "Previsões", {}),
                   ("accuracy", "Acertos do Lab", "Desempenho", {}))),
    ("Corridas", (
        ("summary", "Visão geral do GP", "Corridas", {"aba": "Visão geral"}),
        ("sessions", "Sessões e voltas", "Corridas", {"aba": "Tempos"}),
        ("strategy", "Pneus e paradas", "Corridas", {"aba": "Estratégias"}),
        ("weather", "Clima", "Corridas", {"aba": "Clima"}),
        ("history", "Histórico desta pista", "Corridas", {"aba": "Histórico"}),
        ("teams", "Equipes neste GP", "Corridas", {"aba": "Comparativo de equipes"}))),
    ("Pilotos", (("profiles", "Perfis de pilotos", "Pilotos", {"visao": "perfil"}),
                 ("duel", "Duelo de pilotos", "Pilotos", {"visao": "duelo"}))),
    ("Campeonato", (("drivers-standing", "Campeonato de pilotos", "Campeonato", {"painel": "pilotos"}),
                    ("teams-standing", "Campeonato de equipes", "Campeonato", {"painel": "equipes"}))),
    ("Sobre o Lab", (("method", "Como funciona", "Metodologia", {}),
                     ("sources", "Fontes e limites", "Metodologia", {"secao": "fontes"}),
                     ("terms", "Termos da F1", "Metodologia", {"secao": "termos"}))),
)
ROUTES = {route[0]: route for _, routes in GROUPS for route in routes}
SYNONYMS = {
    "summary": "resultado resultados corrida visão geral overview result race",
    "forecast": "previsão previsões cartas tarot tarô chances pódio probabilidade palpites prediction forecast cards podium",
    "strategy": "estratégia estratégias pneus paradas stints pit stops tyres tires strategy",
    "sessions": "sessões voltas treinos horários classificação qualifying laps sessions times schedule",
    "history": "histórico edições anteriores circuito history circuit",
    "profiles": "perfil piloto pilotos profile driver",
    "duel": "comparar comparação duelo companheiro compare teammate duel",
    "drivers-standing": "pontos classificação pilotos standings drivers points",
    "teams-standing": "pontos classificação construtores equipes standings constructors teams",
    "sources": "fontes dados cobertura qualidade sources coverage data",
    "terms": "glossário termos dicionário significado glossary terms",
}


def selected_route(screen, params):
    for key, _, target, values in ROUTES.values():
        if screen == target and all(params.get(k) == v for k, v in values.items()):
            # Prefer a specific route over the general method entry.
            if key == "method" and params.get("secao") in ("fontes", "termos"):
                continue
            return key
    return {"Corridas": "summary", "Pilotos": "profiles", "Campeonato": "drivers-standing"}.get(screen, "method")


def route_params(key, year, round_, lang, params=None):
    _, _, screen, values = ROUTES[key]
    context = {k: (params.get_all(k) if hasattr(params, 'get_all') else v)
               for k, v in (params or {}).items()
               if k not in ('documento', 'painel', 'cartas', 'aba', 'visao', 'secao', 'equipe', 'campanha')}
    return dict(context, temporada=year, gp=round_, tela=screen, lang=lang, **values)


def render(st, slot, year, round_, screen, lang, params, choose):
    selected = selected_route(screen, params)
    with slot.container():
        with st.container(key="pw-sidebar-menu"):
            menu_label = '{} · {}'.format(translate('Explorar o Pitwall'), translate(ROUTES[selected][1]))
            with st.expander(menu_label, expanded=False):
                st.markdown('<h2 class="pw-explorer-title">{}</h2>'.format(escape(translate("Explorar"))), unsafe_allow_html=True)
                for title, routes in GROUPS:
                    st.markdown('<h3 class="pw-nav-group">{}</h3>'.format(escape(translate(title))), unsafe_allow_html=True)
                    for key, label, target, _ in routes:
                        with st.container(key="pw-nav-item-" + key):
                            st.button(label, key="pw_nav_" + key, on_click=choose, args=(key,),
                                      type="primary" if key == selected else "secondary", width="stretch")
                            href = "?" + urlencode(route_params(key, year, round_, lang, params), doseq=True)
                            st.markdown('<a class="pw-nav-fallback" data-pw-route="{}" data-screen="{}" href="{}" target="_self"{}>{}</a>'.format(
                                key, escape(target, quote=True), escape(href, quote=True), ' aria-current="page"' if key == selected else '',
                                escape(translate(label))), unsafe_allow_html=True)


def search(query, lang="pt"):
    from pitwall.dashboard.search import normalized
    needle = normalized(query)
    if len(needle) < 2:
        return []
    return [dict(kind="navigation", value=key, label=in_language(label, lang))
            for key, label, _, _ in ROUTES.values()
            if needle in normalized(" ".join((label, in_language(label, lang), SYNONYMS.get(key, ""))))]
