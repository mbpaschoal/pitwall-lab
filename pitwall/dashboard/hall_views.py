"""World Drivers' Champions and career milestones from the portable archive."""

import json
from html import escape
from pathlib import Path

from pitwall.dashboard.components import data_editorial
from pitwall.dashboard.fan_views import chapter_header, href, text
from pitwall.dashboard.journey import race_identity
from pitwall.dashboard.team_views import profile_url
from pitwall.i18n import language, translate
from pitwall.i18n.streamlit import st


ASSET = "frontend_assets/hall_da_fama.json"
F1_RESULTS = "https://www.formula1.com/en/results"
LOCAL_FINAL_ROUNDS = {2024: 24, 2025: 24}


def hall_url(year, round_, champion=None):
    params = dict(visao="hall", temporada=year, gp=round_)
    if champion:
        params["campeao"] = champion
    return href("Pilotos", **params)


def load(root):
    snapshot = json.loads((Path(root) / ASSET).read_text(encoding="utf-8"))
    if (not isinstance(snapshot, dict)
            or snapshot.get("schema") != "pitwall-hall-da-fama-v1"
            or not isinstance(snapshot.get("pilotos"), dict)
            or not snapshot["pilotos"]):
        raise ValueError("Invalid Hall of Fame archive")
    return snapshot


def _link(label, url):
    external = ' target="_blank" rel="noopener noreferrer"' if url.startswith("https://") else ' target="_self"'
    return '<a href="{}"{}>{}</a>'.format(escape(url, quote=True), external, escape(str(label)))


def _table(label, headings, rows):
    return (
        '<div class="tabela-editorial pw-hall-table"><table aria-label="{}">'
        '<thead><tr>{}</tr></thead><tbody>{}</tbody></table></div>'
    ).format(
        text(label),
        "".join('<th scope="col">{}</th>'.format(text(heading)) for heading in headings),
        "".join(rows),
    )


def _directory(champions, year, round_):
    ordering = st.selectbox("Ordenar campeões", ("Primeiro título mais recente", "Mais títulos", "Nome"),
                            key="hall_sort", width=380)
    orders = {
        "Primeiro título mais recente": lambda item: -item[1]["titulos"][0]["ano"],
        "Mais títulos": lambda item: (-len(item[1]["titulos"]), item[1]["nome"].casefold()),
        "Nome": lambda item: item[1]["nome"].casefold(),
    }
    rows = []
    for pid, profile in sorted(champions.items(), key=orders[ordering]):
        title_years = ", ".join(str(title["ano"]) for title in profile["titulos"])
        rows.append('<tr><th scope="row">{}</th><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
            _link(profile["nome"], hall_url(year, round_, pid)), escape(profile["pais"][language()]),
            len(profile["titulos"]), title_years,
        ))
    st.markdown(_table("Campeões mundiais de Fórmula 1", ("Piloto", "País", "Títulos", "Temporadas"), rows),
                unsafe_allow_html=True)


def _race_link(event):
    year, round_ = event["ano"], event["rodada"]
    _, race = race_identity(event["gp"], language())
    label = "{} · {}".format(year, race)
    if year in (2024, 2025, 2026):
        return _link(label, href("Corridas", aba="Visão geral", temporada=year, gp=round_))
    return escape(label)


def _titles(profile, year, round_):
    rows = []
    for title in profile["titulos"]:
        season = title["ano"]
        decision = title["decisao"]
        reference = LOCAL_FINAL_ROUNDS.get(season, decision["rodada"])
        championship = (href("Campeonato", painel="pilotos", temporada=season, gp=reference)
                        if season in (2024, 2025, 2026) else "{}/{}/drivers".format(F1_RESULTS, season))
        constructors = []
        for entry in title["construtores"]:
            url = profile_url(entry["id"].replace("-", "_"), year, round_)
            constructors.append(_link(entry["nome"], url) if url else escape(entry["nome"]))
        rows.append('<tr><th scope="row">{}</th><td>{}</td><td>{}</td></tr>'.format(
            _link(season, championship), " → ".join(constructors), _race_link(decision),
        ))
    st.markdown(_table("Títulos mundiais de pilotos", ("Temporada", "Construtor", "GP decisivo"), rows),
                unsafe_allow_html=True)
    for title in profile["titulos"]:
        if "fonte" in title:
            st.markdown(_link(translate("Confirmação do título pela FIA"), title["fonte"]),
                        unsafe_allow_html=True)


def _profile(profile, year, round_, cutoff):
    st.markdown(chapter_header(profile["nome"], profile["bio"][language()]), unsafe_allow_html=True)
    st.caption("{} · {}".format(profile["pais"][language()], "–".join(map(str, profile["anos_atividade"]))))
    stats = [
        ("Títulos mundiais", len(profile["titulos"])), ("Largadas", profile["largadas"]),
        ("Vitórias", profile["vitorias"]), ("Pódios", profile["podios"]), ("Poles", profile["poles"]),
    ]
    st.markdown('<dl class="pw-hall-facts">{}</dl>'.format("".join(
        "<div><dt>{}</dt><dd>{}</dd></div>".format(text(label), count) for label, count in stats
    )), unsafe_allow_html=True)
    st.caption(translate("Estatísticas do Mundial até {}.").format(data_editorial(cutoff)))
    st.subheader("Títulos mundiais de pilotos")
    _titles(profile, year, round_)
    st.subheader("Marcos da carreira")
    st.markdown('<dl class="pw-hall-milestones"><div><dt>{}</dt><dd>{}</dd></div>'
                '<div><dt>{}</dt><dd>{}</dd></div></dl>'.format(
                    text("Estreia no Mundial"), _race_link(profile["estreia"]),
                    text("Primeira vitória"), _race_link(profile["primeira_vitoria"]),
                ), unsafe_allow_html=True)
    if profile.get("perfil_pitwall"):
        url = href("Pilotos", visao="perfil", piloto=profile["perfil_pitwall"], temporada=year, gp=round_)
        st.markdown(_link(translate("Ver análise por condições no Pitwall Lab"), url), unsafe_allow_html=True)


def render(root, year, round_):
    try:
        snapshot = load(root)
    except (OSError, ValueError):
        st.info("Hall da Fama indisponível neste pacote.")
        return

    champions = snapshot["pilotos"]
    requested = st.query_params.get("campeao")
    champion = champions.get(requested)
    options = sorted(champions, key=lambda key: champions[key]["nome"].casefold())

    def choose():
        selected = st.session_state["hall_champion"]
        if selected:
            st.query_params["campeao"] = selected
        else:
            st.query_params.pop("campeao", None)

    profiles = href("Pilotos", visao="perfil", temporada=year, gp=round_)
    links = [_link(translate("Perfis de pilotos"), profiles)]
    if champion:
        links.insert(0, _link(translate("Todos os campeões"), hall_url(year, round_)))
    st.markdown('<nav class="pw-hall-links" aria-label="{}">{}</nav>'.format(
        text("Navegação do Hall da Fama"), "".join(links),
    ), unsafe_allow_html=True)

    if not champion:
        title = translate("{} campeões mundiais de Fórmula 1.").format(len(champions))
        st.markdown(chapter_header("Hall da Fama", title), unsafe_allow_html=True)
        if requested:
            st.info("Perfil de campeão indisponível. Escolha um piloto na lista.")

    st.selectbox("Buscar um campeão", options, index=options.index(requested) if champion else None,
                 format_func=lambda key: champions[key]["nome"], key="hall_champion", on_change=choose, width=380)

    if champion:
        _profile(champion, year, round_, snapshot["corte"])
    else:
        _directory(champions, year, round_)

    with st.expander("Fontes do Hall da Fama"):
        sources = []
        if champion:
            sources.append(_link(translate("Biografia oficial na Fórmula 1"), champion["fonte"]))
        sources += [
            _link(translate("Hall da Fama da Fórmula 1"), snapshot["fonte_f1"]),
            _link(translate("Arquivo histórico F1DB · CC BY 4.0"), snapshot["fonte_dados"]),
        ]
        st.markdown("<ul>{}</ul>".format("".join("<li>{}</li>".format(source) for source in sources)),
                    unsafe_allow_html=True)
