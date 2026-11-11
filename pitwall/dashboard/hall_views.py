"""World Drivers' Champions and career milestones from the portable archive."""

import json
from datetime import date
from html import escape
from pathlib import Path

from dateutil.relativedelta import relativedelta

from pitwall.dashboard import photo_archive
from pitwall.dashboard.components import data_editorial
from pitwall.dashboard.fan_views import chapter_header, href, text
from pitwall.dashboard.journey import race_identity
from pitwall.dashboard.team_views import profile_url
from pitwall.i18n import language, translate
from pitwall.i18n.streamlit import st


ASSET = "frontend_assets/hall_da_fama.json"
F1_RESULTS = "https://www.formula1.com/en/results"
LOCAL_FINAL_ROUNDS = {2024: 24, 2025: 24}
DEFAULT_DUEL = ("ayrton-senna", "alain-prost")


def hall_url(year, round_, champion=None):
    params = dict(visao="hall", temporada=year, gp=round_)
    if champion:
        params["campeao"] = champion
    return href("Pilotos", **params)


def duel_url(year, round_, champion=None):
    first = champion or DEFAULT_DUEL[0]
    second = DEFAULT_DUEL[0] if first == DEFAULT_DUEL[1] else DEFAULT_DUEL[1]
    return href("Pilotos", visao="duelo-campeoes", temporada=year, gp=round_,
                campeao=first, rival_campeao=second)


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


def _title_cells(title, year, round_):
    season = title["ano"]
    decision = title["decisao"]
    reference = LOCAL_FINAL_ROUNDS.get(season, decision["rodada"])
    championship = (href("Campeonato", painel="pilotos", temporada=season, gp=reference)
                    if season in (2024, 2025, 2026) else "{}/{}/drivers".format(F1_RESULTS, season))
    constructors = []
    for entry in title["construtores"]:
        url = profile_url(entry["id"].replace("-", "_"), year, round_)
        constructors.append(_link(entry["nome"], url) if url else escape(entry["nome"]))
    return _link(season, championship), " → ".join(constructors), _race_link(decision)


def _titles(profile, year, round_):
    rows = [
        '<tr><th scope="row">{}</th><td>{}</td><td>{}</td></tr>'.format(*_title_cells(title, year, round_))
        for title in profile["titulos"]
    ]
    st.markdown(_table("Títulos mundiais de pilotos", ("Temporada", "Construtor", "GP decisivo"), rows),
                unsafe_allow_html=True)
    for title in profile["titulos"]:
        if "fonte" in title:
            st.markdown(_link(translate("Confirmação do título pela FIA"), title["fonte"]),
                        unsafe_allow_html=True)


def _profile(root, driver, profile, year, round_, cutoff):
    covers, cars, moments = photo_archive.driver_photos(root, driver, profile)
    if covers:
        intro, photograph = st.columns([1.1, 1], vertical_alignment="center")
    else:
        intro = st.container()
    with intro:
        st.markdown(chapter_header(profile["nome"], profile["bio"][language()]), unsafe_allow_html=True)
        st.caption("{} · {}".format(profile["pais"][language()], "–".join(map(str, profile["anos_atividade"]))))
    if covers:
        with photograph:
            photo_archive.gallery(covers, cover=True)
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
    photo_archive.gallery(cars, "Carros campeões")
    st.subheader("Marcos da carreira")
    st.markdown('<dl class="pw-hall-milestones"><div><dt>{}</dt><dd>{}</dd></div>'
                '<div><dt>{}</dt><dd>{}</dd></div></dl>'.format(
                    text("Estreia no Mundial"), _race_link(profile["estreia"]),
                    text("Primeira vitória"), _race_link(profile["primeira_vitoria"]),
                ), unsafe_allow_html=True)
    photo_archive.gallery(moments, "Momentos históricos")
    if profile.get("perfil_pitwall"):
        url = href("Pilotos", visao="perfil", piloto=profile["perfil_pitwall"], temporada=year, gp=round_)
        st.markdown(_link(translate("Ver análise por condições no Pitwall Lab"), url), unsafe_allow_html=True)


def _first_title_age(profile):
    first_title = profile.get("primeiro_titulo")
    if first_title is None:
        return "—"
    birth = date.fromisoformat(first_title["nascimento"])
    decision = date.fromisoformat(first_title["data"])
    age = relativedelta(decision, birth)
    anniversary = birth + relativedelta(years=age.years)
    days = (decision - anniversary).days
    years_label = translate("{} ano" if age.years == 1 else "{} anos").format(age.years)
    if not days:
        return years_label
    days_label = translate("{} dia" if days == 1 else "{} dias").format(days)
    return translate("{} e {}").format(years_label, days_label)


def _duel(champions, options, year, round_):
    st.markdown(chapter_header("Duelo de Campeões"), unsafe_allow_html=True)
    first = st.query_params.get("campeao", DEFAULT_DUEL[0])
    second = st.query_params.get("rival_campeao", DEFAULT_DUEL[1])
    if first not in champions:
        first = DEFAULT_DUEL[0]
    if second not in champions:
        second = DEFAULT_DUEL[1]

    def choose():
        st.query_params.update(campeao=st.session_state["hall_duel_first"],
                               rival_campeao=st.session_state["hall_duel_second"])

    left, right = st.columns(2)
    with left:
        first = st.selectbox("Primeiro campeão", options, index=options.index(first),
                             format_func=lambda key: champions[key]["nome"],
                             key="hall_duel_first", on_change=choose)
    with right:
        second = st.selectbox("Segundo campeão", options, index=options.index(second),
                              format_func=lambda key: champions[key]["nome"],
                              key="hall_duel_second", on_change=choose)
    if first == second:
        st.info("Escolha dois campeões diferentes para comparar.")
        return

    pairs = [(key, champions[key]) for key in (first, second)]
    profile_headings = [_link(profile["nome"], hall_url(year, round_, key)) for key, profile in pairs]
    metrics = [
        ("Títulos mundiais", [len(profile["titulos"]) for _, profile in pairs]),
        ("Idade no primeiro título", [_first_title_age(profile) for _, profile in pairs]),
        ("Temporadas até o primeiro título", [
            profile.get("primeiro_titulo", {}).get("temporadas_disputadas", "—") for _, profile in pairs
        ]),
    ]
    rows = [
        '<tr><th scope="row">{}</th><td>{}</td><td>{}</td></tr>'.format(
            text(metric), escape(str(values[0])), escape(str(values[1])),
        )
        for metric, values in metrics
    ]
    st.markdown(_table("Comparação de campeões", ("Métrica", *(profile["nome"] for _, profile in pairs)), rows),
                unsafe_allow_html=True)
    st.caption("A contagem inclui a temporada do título e considera as temporadas em que o piloto largou em pelo menos um GP.")

    st.subheader("Títulos em ordem cronológica")
    titles = sorted(((title, profile["nome"]) for _, profile in pairs for title in profile["titulos"]),
                    key=lambda item: item[0]["ano"])
    rows = []
    for title, name in titles:
        season, teams, decision = _title_cells(title, year, round_)
        rows.append('<tr><th scope="row">{}</th><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
            season, escape(name), teams, decision,
        ))
    st.markdown(_table("Títulos do duelo", ("Temporada", "Piloto", "Construtor", "GP decisivo"), rows),
                unsafe_allow_html=True)
    st.markdown('<nav class="pw-hall-links" aria-label="{}">{}</nav>'.format(
        text("Perfis dos campeões do duelo"), "".join(profile_headings),
    ), unsafe_allow_html=True)


def render(root, year, round_, duel=False):
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
    if champion or duel:
        links.insert(0, _link(translate("Todos os campeões"), hall_url(year, round_)))
    if not duel:
        links.append(_link(translate("Duelo de Campeões"), duel_url(year, round_, requested if champion else None)))
    links.append(_link(translate("Acervo fotográfico"), photo_archive.archive_url(year, round_)))
    st.markdown('<nav class="pw-hall-links" aria-label="{}">{}</nav>'.format(
        text("Navegação do Hall da Fama"), "".join(links),
    ), unsafe_allow_html=True)

    if duel:
        _duel(champions, options, year, round_)
    else:
        if not champion:
            title = translate("{} campeões mundiais de Fórmula 1.").format(len(champions))
            st.markdown(chapter_header("Hall da Fama", title), unsafe_allow_html=True)
            if requested:
                st.info("Perfil de campeão indisponível. Escolha um piloto na lista.")
        st.selectbox("Buscar um campeão", options, index=options.index(requested) if champion else None,
                     format_func=lambda key: champions[key]["nome"], key="hall_champion", on_change=choose, width=380)
        if champion:
            _profile(root, requested, champion, year, round_, snapshot["corte"])
        else:
            _directory(champions, year, round_)

    with st.expander("Fontes do Hall da Fama"):
        sources = []
        if champion and not duel:
            sources.append(_link(translate("Biografia oficial na Fórmula 1"), champion["fonte"]))
        sources += [
            _link(translate("Hall da Fama da Fórmula 1"), snapshot["fonte_f1"]),
            _link(translate("Arquivo histórico F1DB · CC BY 4.0"), snapshot["fonte_dados"]),
        ]
        st.markdown("<ul>{}</ul>".format("".join("<li>{}</li>".format(source) for source in sources)),
                    unsafe_allow_html=True)
