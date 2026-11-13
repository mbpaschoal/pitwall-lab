"""Archival photographs for champions, teams, cars and championship events."""

import json
from html import escape
from pathlib import Path
import re

from pitwall.dashboard.fan_views import chapter_header, href, text
from pitwall.i18n import language, translate
from pitwall.i18n.streamlit import st


CATALOG = "frontend_assets/acervo_fotografico.json"
INVENTORY = "frontend_assets/inventario_campeoes.json"
PHOTO_PATH = re.compile(r"static/pitwall-archive/[a-z0-9-]+-[a-f0-9]{12}-[0-9]+\.webp")
ARCHIVE_MODES = ("Carros campeões", "Equipes", "Momentos históricos")
EVENT_GROUPS = {None: "Todos os marcos", "pilotos": "Marcos de pilotos", "equipes": "Títulos de construtores"}


def archive_url(year, round_):
    return href("Pilotos", visao="acervo", temporada=year, gp=round_)


def _catalog(root):
    try:
        data = json.loads((Path(root) / CATALOG).read_text(encoding="utf-8"))
        if data.get("schema") == 1 and isinstance(data.get("fotos"), dict):
            return data
    except (OSError, ValueError, AttributeError):
        pass
    return {}


def load(root):
    return _catalog(root).get("fotos", {})


def _link(url, label):
    return '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(
        escape(url, quote=True), escape(label),
    )


def _figure(key, photo):
    small, large = photo["variantes"]
    if not all(PHOTO_PATH.fullmatch(item["arquivo"]) for item in (small, large)):
        return ""
    variants = ", ".join("app/{} {}w".format(item["arquivo"], item["largura"]) for item in (small, large))
    caption = photo["legenda"][language()]
    return (
        '<figure data-archive-photo="{}"><img src="app/{}" srcset="{}" '
        'sizes="auto, (max-width: 640px) 92vw, (max-width: 1000px) 45vw, 600px" '
        'width="{}" height="{}" alt="{}" loading="lazy" decoding="async">'
        '<figcaption><span>{}</span><small>{} · {} · {} · {} · {}</small></figcaption></figure>'
    ).format(
        escape(key, quote=True), small["arquivo"], escape(variants, quote=True),
        small["largura"], small["altura"], escape(caption, quote=True), escape(caption),
        escape(photo["autor"]), _link(photo["licenca_url"], photo["licenca"]),
        text("Versão redimensionada"),
        _link(f'app/{large["arquivo"]}', translate("Ampliar foto")),
        _link(photo["fonte"], "Original · {} × {}".format(photo["largura"], photo["altura"])),
    )


def gallery(photos, heading=None, cover=False):
    figures = "".join(_figure(key, photo) for key, photo in photos)
    if figures:
        if heading:
            st.subheader(heading)
        css = "pw-archive-gallery pw-archive-cover" if cover else "pw-archive-gallery"
        st.markdown(f'<div class="{css}">{figures}</div>', unsafe_allow_html=True)
    return bool(figures)


def _references(catalog, group, keys):
    return [
        row for key, row in catalog.get("referencias_fotograficas", {}).get(group, {}).items()
        if key in keys and row["url"].startswith("https://")
    ]


def reference_links(references, expanded=False):
    if not references:
        return
    items = "".join(
        "<li>{}</li>".format(_link(row["url"], f'{row["legenda"][language()]} · {row["acervo"]}'))
        for row in references
    )
    with st.expander("Fotografias nos arquivos de origem", expanded=expanded):
        st.markdown(f"<ul>{items}</ul>", unsafe_allow_html=True)


def driver_photos(root, driver, profile):
    catalog = _catalog(root)
    photos = list(catalog.get("fotos", {}).items())
    titles = {(title["ano"], entry["id"]) for title in profile["titulos"] for entry in title["construtores"]}
    events = [profile["estreia"], profile["primeira_vitoria"], *(title["decisao"] for title in profile["titulos"])]
    race_ids = {"{}:{}".format(event["ano"], event["rodada"]) for event in events}
    cars = [
        (key, photo) for key, photo in photos
        if driver not in photo.get("pilotos", [])
        and any((season, photo.get("construtor")) in titles for season in photo.get("temporadas", []))
    ]
    portraits = [(key, photo) for key, photo in photos if driver in photo.get("pilotos", [])]
    if not portraits and cars:
        portraits, cars = cars[:1], cars[1:]
    shown = {key for key, _ in portraits[:1]}
    moments = [(key, photo) for key, photo in photos
               if key not in shown and race_ids.intersection(photo.get("gps", []))]
    shown.update(key for key, _ in moments)
    artifacts = [(key, photo) for key, photo in photos
                 if key not in shown and race_ids.intersection(photo.get("artefatos_gps", []))]
    shown.update(key for key, _ in artifacts)
    cars = [(key, photo) for key, photo in cars if key not in shown]
    portraits = portraits[:1] + [(key, photo) for key, photo in portraits[1:] if key not in shown]
    return portraits, cars, moments, artifacts, _references(catalog, "gps", race_ids)


def team_photos(root, team):
    constructor = team.replace("_", "-")
    photos = load(root)
    team_images = [(key, photo) for key, photo in photos.items() if team in photo.get("equipes", [])]
    cars = [(key, photo) for key, photo in photos.items()
            if photo.get("construtor") == constructor and team not in photo.get("equipes", [])]
    gallery(team_images[:1])
    return team_images[1:], cars


def render(root, year, round_):
    st.markdown('<nav class="pw-hall-links" aria-label="{}"><a href="{}" target="_self">{}</a></nav>'.format(
        text("Navegação do Hall da Fama"), escape(href("Pilotos", visao="hall", temporada=year, gp=round_), quote=True),
        text("Hall da Fama"),
    ), unsafe_allow_html=True)
    st.markdown(chapter_header("Acervo fotográfico"), unsafe_allow_html=True)
    catalog = _catalog(root)
    photos = list(catalog.get("fotos", {}).items())
    if not photos:
        st.info("Acervo fotográfico indisponível neste pacote.")
        return
    inventory = json.loads((Path(root) / INVENTORY).read_text(encoding="utf-8"))
    mode = st.radio("Coleção", ARCHIVE_MODES, horizontal=True, key="archive_mode")
    artifacts = []
    references = []
    if mode == "Carros campeões":
        seasons = sorted({row["ano"] for row in inventory["campanhas"]}, reverse=True)
        season = st.selectbox("Temporada do acervo", seasons, key="archive_season")
        selected = [(key, photo) for key, photo in photos if season in photo.get("temporadas", [])]
        models = {model for row in inventory["campanhas"] if row["ano"] == season
                  for model in row["modelos_candidatos"]}
        references = _references(catalog, "modelos", models)
    elif mode == "Equipes":
        teams = {key.replace("-", "_"): name for key, name in inventory["equipes_campeas"].items()}
        teams.update(inventory["equipes_atuais"])
        team = st.selectbox("Equipe no acervo", sorted(teams, key=teams.get), format_func=teams.get,
                            key="archive_team")
        selected = [(key, photo) for key, photo in photos
                    if team in {name.replace("-", "_") for name in photo.get("equipes", [])}
                    or photo.get("construtor") == team.replace("_", "-")]
    else:
        group_column, season_column = st.columns(2)
        with group_column:
            group = st.selectbox("Tipo de marco", tuple(EVENT_GROUPS), key="archive_event_group",
                                 format_func=lambda value: translate(EVENT_GROUPS[value]))
        events = [event for event in inventory["momentos"] if group is None or event.get(group)]
        seasons = sorted({event["ano"] for event in events}, reverse=True)
        with season_column:
            season = st.selectbox("Temporada do acervo", [None, *seasons], key="archive_event_season",
                                  format_func=lambda value: str(value) if value else translate("Todas as temporadas"))
        race_ids = {f'{event["ano"]}:{event["rodada"]}' for event in events
                    if season is None or event["ano"] == season}
        if group is None:
            race_ids.update(gp for _, photo in photos for gp in photo.get("gps", [])
                            if season is None or gp.split(":", 1)[0] == str(season))
        selected = [(key, photo) for key, photo in photos if race_ids.intersection(photo.get("gps", []))]
        selected_ids = {key for key, _ in selected}
        artifacts = [(key, photo) for key, photo in photos
                     if key not in selected_ids and race_ids.intersection(photo.get("artefatos_gps", []))]
        references = _references(catalog, "gps", race_ids)
    has_photos = gallery(selected)
    has_artifacts = gallery(artifacts, "Peças de acervo")
    reference_links(references, expanded=not (has_photos or has_artifacts))
    if not has_photos and not has_artifacts and not references:
        st.info("Fotografias desta seleção em pesquisa.")
