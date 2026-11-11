"""Profiles and championship campaigns from the portable team catalogue."""

import json
from html import escape
from pathlib import Path

from pitwall.dashboard.components import data_editorial
from pitwall.dashboard.fan_views import href, team_mark, text
from pitwall.dashboard.journey import race_identity
from pitwall.i18n import language, translate
from pitwall.i18n.streamlit import st


PROFILE_IDS = frozenset({
    "alpine", "aston_martin", "audi", "cadillac", "ferrari", "haas",
    "mclaren", "mercedes", "rb", "red_bull", "williams",
})
ALIASES = {
    "haas_f1_team": "haas",
    "kick_sauber": "audi",
    "racing_bulls": "rb",
    "rb_f1_team": "rb",
    "red_bull_racing": "red_bull",
    "sauber": "audi",
}
ASSET = "frontend_assets/perfis_equipes.json"
F1_RESULTS = "https://www.formula1.com/en/results"
TITLE_KINDS = ("construtores", "pilotos")


def profile_id(team):
    canonical = ALIASES.get(team, team)
    return canonical if canonical in PROFILE_IDS else None


def profile_url(team, year, round_):
    canonical = profile_id(team)
    if canonical and year in (2024, 2025, 2026) and type(round_) is int and 1 <= round_ <= 24:
        return href("Campeonato", painel="equipes", equipe=canonical, temporada=year, gp=round_)
    return None


def link(label, url, css=""):
    return '<a class="{}" href="{}" target="_self">{}</a>'.format(
        css, escape(url, quote=True), escape(str(label)),
    )


def directory_url(year, round_):
    return href("Campeonato", painel="equipes", equipe="perfis", temporada=year, gp=round_)


def render_links(teams, identity):
    entries = []
    for row in teams:
        team = row.get("equipe_id")
        url = profile_url(team, identity["temporada"], identity["rodada"])
        if url:
            label = row["equipe"]
            if team in ("sauber", "kick_sauber"):
                label = "{} → Audi".format(label)
            entries.append(link(label, url))
    if entries:
        st.markdown('<nav class="pw-team-links" aria-label="{}"><strong>{}</strong><div>{}</div></nav>'.format(
            text("Perfis de equipes"), text("Perfis de equipes"), "".join(entries),
        ), unsafe_allow_html=True)


def load(root):
    path = Path(root) / ASSET
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict) or set(snapshot.get("equipes", {})) != PROFILE_IDS:
        raise ValueError("Incomplete team profiles catalogue")
    return snapshot


def _source(label, url):
    return '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(
        escape(url, quote=True), text(label),
    )


def _title_url(team, profile, title, kind, year, round_):
    season = title["ano"]
    if str(season) in profile.get("campanhas", {}):
        return href("Campeonato", painel="equipes", equipe=team, temporada=year, gp=round_,
                    campanha="{}-{}".format(season, kind))
    return "{}/{}/{}".format(F1_RESULTS, season, "team" if kind == "construtores" else "drivers")


def _title_list(team, profile, kind, year, round_):
    titles = profile["titulos_" + kind]
    if not titles:
        return ""
    entries = []
    for title in reversed(titles):
        label = "{} · {}".format(title["ano"], title["piloto"]) if kind == "pilotos" else str(title["ano"])
        url = _title_url(team, profile, title, kind, year, round_)
        anchor = link(label, url) if url.startswith("?") else _source(label, url)
        entries.append("<li>{}</li>".format(anchor))
    return '<ul class="pw-team-title-years">{}</ul>'.format("".join(entries))


def _render_campaign(profile, requested):
    for kind in TITLE_KINDS:
        for title in profile["titulos_" + kind]:
            season = title["ano"]
            if requested != "{}-{}".format(season, kind):
                continue
            rows = profile.get("campanhas", {}).get(str(season), [])
            if rows:
                _campaign_table(profile["nome"], title, kind, rows)
            return


def _campaign_table(name, title, kind, rows):
    year = title["ano"]
    end_round = title.get("rodada", rows[-1]["rodada"])
    heading = translate("Campanha de {}").format(year)
    if kind == "pilotos":
        heading += " · " + title["piloto"]
    st.subheader(heading)
    st.caption("Posição e pontos acumulados no Campeonato de Construtores.")
    if year == 2026:
        st.caption(translate("Classificação até a rodada em que o título foi confirmado."))
    panel = "equipes" if kind == "construtores" else "pilotos"
    table_rows = []
    for row in rows:
        round_ = row["rodada"]
        if round_ > end_round:
            break
        _, race = race_identity(row["gp"], language())
        race_url = href("Corridas", aba="Comparativo de equipes", temporada=year, gp=round_)
        table_rows.append("<tr><td>{}</td><th scope=\"row\">{}</th><td>{}</td><td>{:g}</td></tr>".format(
            round_, link(race, race_url), row["posicao"], row["pontos"],
        ))
    columns = ("Rodada", "Grande Prêmio", "Pos.", "Pontos")
    table = '<div class="tabela-editorial pw-team-campaign"><table aria-label="{}"><thead><tr>{}</tr></thead><tbody>{}</tbody></table></div>'.format(
        escape("{} · {}".format(name, year), quote=True),
        "".join('<th scope="col">{}</th>'.format(text(column)) for column in columns),
        "".join(table_rows),
    )
    standings = href("Campeonato", painel=panel, temporada=year, gp=end_round)
    standings_label = "Ver classificação de equipes" if kind == "construtores" else "Ver classificação de pilotos"
    st.markdown(link(translate(standings_label), standings) + table, unsafe_allow_html=True)
    if title.get("fonte"):
        st.markdown(_source("Confirmação do título pela FIA", title["fonte"]), unsafe_allow_html=True)


def _milestone_year(team, profile, season, year, round_):
    title = next((item for item in profile["titulos_construtores"] if item["ano"] == season), None)
    if title and str(season) in profile.get("campanhas", {}):
        return link(season, _title_url(team, profile, title, "construtores", year, round_))
    if season in (2024, 2025) and team != "cadillac":
        return link(season, href("Campeonato", painel="equipes", temporada=season, gp=24))
    return str(season)


def render(root, year, round_):
    try:
        snapshot = load(root)
    except (OSError, ValueError, TypeError):
        st.info("Perfis de equipes indisponíveis neste pacote.")
        return
    profiles = snapshot["equipes"]
    requested = st.query_params.get("equipe")
    team = profile_id(requested)
    options = sorted(profiles, key=lambda key: profiles[key]["nome"])

    def choose():
        st.query_params["equipe"] = st.session_state["team_profile"] or "perfis"
        st.query_params.pop("campanha", None)

    overview = href("Campeonato", painel="equipes", temporada=year, gp=round_)
    gp_teams = href("Corridas", aba="Comparativo de equipes", temporada=year, gp=round_)
    st.markdown('<nav class="pw-team-links" aria-label="{}"><div>{}{}</div></nav>'.format(
        text("Navegação do perfil"), link(translate("Campeonato de equipes"), overview),
        link(translate("Equipes neste GP"), gp_teams),
    ), unsafe_allow_html=True)
    st.selectbox("Escolha uma equipe", options, index=options.index(team) if team else None,
                 key="team_profile", format_func=lambda key: profiles[key]["nome"], on_change=choose, width=380)
    if team is None:
        st.title("Perfis de equipes")
        if requested != "perfis":
            st.info("Perfil indisponível para esta equipe. Escolha uma equipe do grid de 2026.")
        return

    profile = profiles[team]
    st.markdown('<header class="pw-chapter pw-team-profile-head"><div aria-hidden="true">{}</div><h1>{}</h1></header>'.format(
        team_mark(team, profile["nome"]), escape(profile["nome"]),
    ), unsafe_allow_html=True)

    _render_campaign(profile, st.query_params.get("campanha"))

    st.subheader("Títulos mundiais")
    championships = []
    for kind, label in (("construtores", "Construtores"), ("pilotos", "Pilotos")):
        championships.append('<section><h3>{} · {}</h3>{}</section>'.format(
            text(label), len(profile["titulos_" + kind]), _title_list(team, profile, kind, year, round_),
        ))
    st.markdown('<div class="pw-team-championships">{}</div>'.format("".join(championships)), unsafe_allow_html=True)
    if profile["titulos_anteriores"]:
        previous = [
            _source("{} · {}".format(title["ano"], title["construtor"]), "{}/{}/team".format(F1_RESULTS, title["ano"]))
            for title in profile["titulos_anteriores"]
        ]
        st.markdown('<p>{} {}</p>'.format(text("Títulos de construtores na linhagem da operação"), " · ".join(previous)),
                    unsafe_allow_html=True)
    if team == "mercedes":
        st.caption("Fangio assegurou o título de 1954 pela Mercedes após disputar provas daquela temporada pela Maserati.")

    st.subheader(translate("Equipe técnica em {}").format(snapshot["temporada"]))
    st.caption(translate("Informações conferidas em {}.").format(data_editorial(snapshot["conferido_em"])))
    facts = [
        ("Base", profile["base"][language()]),
        ("Unidade de potência", profile["unidade_potencia"]),
        *((role["cargo"], role["nome"]) for role in profile["lideranca"]),
    ]
    st.markdown('<dl class="pw-team-facts">{}</dl>'.format("".join(
        "<div><dt>{}</dt><dd>{}</dd></div>".format(text(label), escape(value)) for label, value in facts
    )), unsafe_allow_html=True)

    st.subheader("História da equipe")
    st.markdown('<ol class="pw-team-timeline">{}</ol>'.format("".join(
        "<li><strong>{}</strong><p>{}</p></li>".format(
            _milestone_year(team, profile, mark["ano"], year, round_), escape(mark[language()]),
        ) for mark in profile["marcos"]
    )), unsafe_allow_html=True)

    with st.expander("Fontes do perfil"):
        sources = [
            _source("Ficha da equipe na Fórmula 1", profile["fonte"]),
            _source("História das equipes na Fórmula 1", snapshot["fonte_historia"]),
            _source("Arquivo histórico F1DB · CC BY 4.0", snapshot["fonte_titulos"]),
        ]
        sources.extend(_source(translate("Documento complementar {}").format(i), url)
                       for i, url in enumerate(profile["fontes_complementares"], 1))
        st.markdown("<ul>{}</ul>".format("".join("<li>{}</li>".format(source) for source in sources)),
                    unsafe_allow_html=True)
