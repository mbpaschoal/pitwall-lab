"""Historical driver views. No collection, training or prediction occurs here."""

from datetime import date
from html import escape
from urllib.parse import urlencode

import pandas as pd
import plotly.graph_objects as go

from pitwall.data.driver_conditions import DriverConditionsError, load
from pitwall.i18n import language, translate
from pitwall.i18n.streamlit import dataframe, st
from pitwall.research.driver_conditions import (
    BY_KEY, CONDITIONS, HIGHLIGHTS, METRICS, driver_names, leaders, profile,
    ranking, select_rows, summarize,
)


INK = "#102b50"
BLUE = "#7fa4ca"
SYMBOLS = {"rain": "☂", "track_hot": "☀", "ccw": "↶", "many_corners": "⌁",
           "high_altitude": "△", "track_cold": "❄"}
QUICK_CONDITIONS = (("rain", "☂ Chuva"), ("track_hot", "☀ Calor"),
                    ("ccw", "↶ Sentido anti-horário"))
COMPARISON_CONDITIONS = ("rain", "no_rain", "track_hot", "ccw")
CRITERION_DEFAULTS = {"pilot_years": [2024, 2025, 2026],
                      "pilot_metric": "win_rate", "pilot_minimum": 5}
TEAM_NAMES = {
    "mercedes": "Mercedes", "ferrari": "Ferrari", "red_bull": "Red Bull",
    "red_bull_racing": "Red Bull", "mclaren": "McLaren",
    "aston_martin": "Aston Martin", "alpine": "Alpine",
    "alpine_f1_team": "Alpine", "williams": "Williams", "haas": "Haas",
    "haas_f1_team": "Haas", "rb": "RB", "rb_f1_team": "RB",
    "racing_bulls": "Racing Bulls", "sauber": "Sauber", "audi": "Audi",
    "cadillac": "Cadillac",
}


def _race_context_params(query):
    """Keep a canonical GP independently of historical profile criteria."""
    year, round_ = query.get("temporada"), query.get("gp")
    if (year in ("2024", "2025", "2026") and isinstance(round_, str)
            and round_.isdigit() and str(int(round_)) == round_
            and 1 <= int(round_) <= 24):
        return dict(temporada=year, gp=round_)
    return {}


def _navigation_context_params(query):
    return dict(_race_context_params(query), **_forecast_origin_params(query))


def _forecast_origin_params(query):
    """Keep a matching GP origin separate from the profile's historical years."""
    year, round_ = query.get("origem_temporada"), query.get("origem_gp")
    if (query.get("origem_tela") == "Previsões" and year in ("2024", "2025", "2026")
            and isinstance(round_, str) and 1 <= len(round_) <= 2 and round_.isdigit()
            and str(int(round_)) == round_ and 1 <= int(round_) <= 24
            and query.get("temporada") == year and query.get("gp") == round_):
        return dict(temporada=year, gp=round_, origem_tela="Previsões",
                    origem_temporada=year, origem_gp=round_)
    return {}


def _condition_chips(years, metric, minimum, condition):
    """Quick conditions keep the comparison scope; Clear restores valid defaults."""
    chips = []
    for key, label in QUICK_CONDITIONS:
        query = dict(tela="Pilotos", visao="geral", condicao=key,
                     anos=",".join(map(str, years)), metrica=metric,
                     minimo=minimum, lang=language())
        query.update(_navigation_context_params(st.query_params))
        chips.append('<a href="?{}" target="_self"{}>{}</a>'.format(
            escape(urlencode(query), quote=True),
            ' aria-current="true"' if key == condition else "",
            escape(translate(label))))
    reset = dict(tela="Pilotos", visao="geral", condicao="rain",
                 anos="2024,2025,2026", metrica="win_rate", minimo=5,
                 faixas=",".join(HIGHLIGHTS), lang=language())
    reset.update(_navigation_context_params(st.query_params))
    chips.append('<a class="fan-condition-reset" href="?{}" target="_self" title="{}">{}</a>'.format(
        escape(urlencode(reset), quote=True),
        escape(translate("Restaurar período e critérios padrão"), quote=True),
        escape(translate("Limpar"))))
    return '<nav class="fan-condition-chips" aria-label="{}">{}</nav>'.format(
        escape(translate("Condições de corrida")), "".join(chips))


def _comparison_toolbar(years, metric, minimum):
    scope = translate("Histórico: {} · {} · mínimo {} corridas por condição.").format(
        ", ".join(map(str, years)) or "—", translate(METRICS[metric]), minimum)
    return '<div class="fan-pilot-toolbar"><span>{}</span></div>'.format(escape(scope))


def _overview_details(asset, rows, years, metric, minimum):
    """Read four comparable cohorts and each driver's last team in this period."""
    comparisons, teams = {}, {}
    for row in rows:
        driver = row["driver_id"]
        comparisons[driver] = []
        for condition in COMPARISON_CONDITIONS:
            stats = summarize(select_rows(asset, years, condition, driver))
            comparisons[driver].append({
                "label": "Sem chuva registrada" if condition == "no_rain" else BY_KEY[condition].short,
                "condition": condition,
                "score": stats[metric] if stats["starts"] >= minimum else None,
                "starts": stats["starts"], "wins": stats["wins"],
                "podiums": stats["podiums"],
            })
        observations = select_rows(asset, years, driver=driver)
        if observations:
            latest = max(observations, key=lambda item: (
                asset["gps"][item["race_id"]]["temporada"],
                asset["gps"][item["race_id"]]["rodada"]))
            team = latest["team_id"]
            teams[driver] = {"id": team, "name": TEAM_NAMES.get(team, team.replace("_", " ").title())}
    maximum = 1 if metric.endswith("rate") else max(
        (item["score"] for items in comparisons.values() for item in items
         if item["score"] is not None), default=0)
    for items in comparisons.values():
        for item in items:
            item["maximum"] = maximum
    return comparisons, teams


def _link(driver, condition="rain"):
    params = {"tela": "Pilotos", "piloto": driver, "visao": "perfil",
                             "condicao": condition, "lang": language(),
        "anos": ",".join(map(str, st.session_state.get("pilot_years", [2024, 2025, 2026]))),
        "metrica": st.session_state.get("pilot_metric", "win_rate"),
        "minimo": st.session_state.get("pilot_minimum", 5),
        "faixas": ",".join(st.session_state.get("profile_conditions", HIGHLIGHTS))}
    params.update(_navigation_context_params(st.query_params))
    return "?" + urlencode(params)


def _value(value, metric):
    if value is None:
        return "—"
    if metric.endswith("rate"):
        text = "{:.1f}%".format(100 * value)
        return text.replace(".", ",") if language() == "pt" else text
    return str(value)


def _figure(figure, height=350):
    figure.update_layout(height=height, margin=dict(l=8, r=16, t=10, b=36),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Lato, Arial, sans-serif", color=INK),
        legend=dict(orientation="h", y=-.22), hovermode="closest", separators=",." if language() == "pt" else ".,")
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def _condition_values_html(comparisons, series, metric, minimum):
    """Expose exactly the plotted aggregates and denominators as native text."""
    headings = ("Condição", "Grupo", METRICS[metric], "Largadas (N)")
    header = "".join('<th scope="col">{}</th>'.format(escape(translate(label)))
                     for label in headings)
    rows = []
    for item in comparisons:
        for field, label, _ in series:
            stats = item[field]
            value = stats[metric] if stats["starts"] >= minimum else None
            rows.append('<tr><th scope="row">{}</th><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
                escape(translate(BY_KEY[item["condition"]].short)),
                escape(translate(label)), escape(_value(value, metric)), stats["starts"]))
    return '<table class="pilot-condition-values"><caption>{}</caption><thead><tr>{}</tr></thead><tbody>{}</tbody></table>'.format(
        escape(translate("Valores e amostras por condição")), header, "".join(rows))


def _appearance_date_label(value):
    """Label the published UTC date without browser-locale or timezone changes."""
    try:
        published = date.fromisoformat(str(value)[:10])
    except ValueError:
        return str(value)
    months = ("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec" if language() == "en"
              else "jan fev mar abr mai jun jul ago set out nov dez").split()
    return "{} {} {}".format(published.day, months[published.month - 1], published.year)


def _evidence(asset, rows, key):
    records = []
    for row in sorted(rows, key=lambda x: (asset["gps"][x["race_id"]]["temporada"],
                                         asset["gps"][x["race_id"]]["rodada"]), reverse=True):
        gp = asset["gps"][row["race_id"]]
        status = ("Não largou" if not row["started"] else
                  "Desclassificado" if row["disqualified"] else
                  "Abandono" if row["retired"] else "Classificado")
        records.append({"Temporada": gp["temporada"], "GP": gp["name"],
            "Piloto": row["driver_name"], "Equipe": row["team_id"].replace("_", " ").title(),
            "Posição": row["position"], "Situação": status,
            "Chuva": "Registrada" if gp["rain_condition"] == "recorded" else "Não registrada",
            "Pista (°C)": round(gp["track_temperature"], 1), "Curvas": gp["corners"],
            "Corrida": "?" + urlencode({"tela": "Corridas", "temporada": gp["temporada"],
                "gp": gp["rodada"], "lang": language()}), "Fonte do circuito": gp["circuit_source_url"]})
    frame = pd.DataFrame(records)
    if frame.empty:
        st.info("Nenhuma corrida neste recorte.")
        return
    st.dataframe(frame, hide_index=True, width="stretch", column_config={
        "Corrida": st.column_config.LinkColumn(translate("Corrida"), display_text=translate("Abrir GP")),
        "Fonte do circuito": st.column_config.LinkColumn(translate("Fonte do circuito"), display_text=translate("Fonte"))})
    st.download_button("Baixar evidências (CSV)", dataframe(frame).to_csv(index=False).encode("utf-8-sig"),
                       file_name="pitwall-pilotos-{}.csv".format(key), mime="text/csv", key="csv_" + key, on_click="ignore")


def _overview(asset, years, metric, minimum):
    from pitwall.dashboard.fan_views import condition_rows
    condition=st.session_state.get('pilot_condition','rain')
    if condition not in BY_KEY:condition='rain'
    ranked=ranking(asset,condition,metric,minimum,years)
    if ranked:
        # Four people initially; never cut the tie containing the fourth person.
        cutoff_rank = ranked[min(3, len(ranked) - 1)]["rank"]
        visible = [row for row in ranked if row["rank"] <= cutoff_rank]
        comparisons, teams = _overview_details(asset, visible, years, metric, minimum)
        st.markdown(condition_rows(visible, metric,
            {r['driver_id']:_link(r['driver_id'],condition) for r in ranked},
            comparisons=comparisons, teams=teams), unsafe_allow_html=True)
        with st.expander('Classificação completa por condição'):
            st.dataframe(pd.DataFrame([{'Pos.':r['rank'],'Piloto':r['driver_name'],'Largadas':r['starts'],METRICS[metric]:r['score']} for r in ranked]),hide_index=True,width='stretch')
    else:
        st.info("Amostra insuficiente para esta condição.")
    # Alternative circumstances are discoveries, not another copy of the ranking.
    cards=[]
    for key in HIGHLIGHTS:
        if key==condition:continue
        best=leaders(ranking(asset,key,metric,minimum,years))
        if not best:continue
        cards.append('<a class="fan-discovery" href="{}" target="_self"><span>{}</span><div><strong>{}</strong><small>{}</small></div></a>'.format(escape(_link(best[0]['driver_id'],key),quote=True),SYMBOLS[key],escape(translate(BY_KEY[key].short)),escape(' / '.join(r['driver_name'] for r in best))))
    st.markdown('<div class="fan-discoveries">{}</div>'.format(''.join(cards)),unsafe_allow_html=True)
    with st.expander('Mais condições'):
        st.selectbox('Condição para comparar',list(BY_KEY),index=list(BY_KEY).index(condition),format_func=lambda x:BY_KEY[x].label,key='pilot_condition')
    right=st.container()
    with right:
        with st.expander("Mapa de condições"):
            # Alphabetical inclusion is explicit; the complete matrix is available below.
            names = driver_names(asset, years)
            if "matrix_drivers" in st.session_state:
                st.session_state["matrix_drivers"] = [x for x in st.session_state["matrix_drivers"] if x in names]
            ids = st.multiselect("Pilotos no mapa", sorted(names, key=names.get), default=st.session_state.get("matrix_drivers", sorted(names, key=names.get)), format_func=names.get, key="matrix_drivers")
            matrix = {}
            for key in HIGHLIGHTS:
                matrix[key] = {x["driver_id"]: x["score"] for x in ranking(asset, key, metric, minimum, years)}
            figure = go.Figure(go.Heatmap(z=[[matrix[key].get(driver) for key in HIGHLIGHTS] for driver in ids],
                x=[BY_KEY[key].short for key in HIGHLIGHTS], y=[names[x] for x in ids],
                colorscale=[[0, "#eef4f9"], [1, "#102b50"]], hoverongaps=False,
                hovertemplate=("%{y}<br>%{x}<br>%{z:.1%}<extra></extra>" if metric.endswith("rate") else "%{y}<br>%{x}<br>%{z}<extra></extra>"),
                colorbar=dict(tickformat=".0%" if metric.endswith("rate") else "d")))
            figure.update_yaxes(autorange="reversed")
            _figure(figure, max(340, 27 * len(ids)))
            st.caption("Células vazias indicam amostra insuficiente. Todos os pilotos do período estão incluídos.")
            with st.expander("Valores do mapa em tabela"):
                records = [{"Piloto": names[driver], **{BY_KEY[key].short: _value(matrix[key].get(driver), metric) for key in HIGHLIGHTS}} for driver in ids]
                st.dataframe(pd.DataFrame(records), hide_index=True, width="stretch")
    with st.expander("Corridas que sustentam a comparação"):
        _evidence(asset, select_rows(asset, years, condition), "condicao")


def _individual(asset, years, metric, minimum):
    names = driver_names(asset)
    ids = sorted(names, key=names.get)
    if st.session_state.get("pilot_driver") not in names:
        st.session_state["pilot_driver"] = ids[0]
    driver = st.selectbox("Piloto", ids, index=ids.index(st.session_state["pilot_driver"]), format_func=names.get, key="pilot_driver")
    conditions = st.multiselect("Condições para explorar", list(BY_KEY), default=st.session_state.get("profile_conditions", list(HIGHLIGHTS)), format_func=lambda x: BY_KEY[x].label, key="profile_conditions")
    details = profile(asset, driver, years, conditions=conditions)
    back = _link(driver, st.session_state.get("pilot_condition", "rain")).replace("visao=perfil", "visao=geral")
    st.markdown('<a href="{}" target="_self">← {}</a>'.format(escape(back), escape(translate("Voltar à visão geral"))), unsafe_allow_html=True)
    st.markdown('<div class="pilot-profile"><h2>{}</h2><p>{}</p></div>'.format(
        escape(names[driver]), translate("Desempenho histórico por condição")), unsafe_allow_html=True)
    for column, label, field in zip(st.columns(3), ("Largadas", "Vitórias", "Pódios"), ("starts", "wins", "podiums")):
        column.metric(label, details["summary"][field])
    if not details["races"]:
        st.info("Nenhuma corrida neste recorte.")
        return
    left, right = st.columns([1.3, 1])
    with left:
        st.subheader("Desempenho por condição")
        comparisons = details["conditions"]
        reference_label = "Demais pilotos (taxa conjunta)" if metric.endswith("rate") else "Demais pilotos (total)"
        series = [("driver", details["driver_name"], INK)]
        if metric.endswith("rate"):
            series.append(("reference", reference_label, BLUE))
        if not comparisons:
            st.info("Selecione pelo menos uma condição.")
        elif not any(item[field]["starts"] >= minimum for item in comparisons
                     for field, _, _ in series):
            st.info("Amostra insuficiente para esta condição.")
        else:
            figure = go.Figure()
            for field, label, color in series:
                values = [x[field][metric] if x[field]["starts"] >= minimum else None for x in comparisons]
                figure.add_bar(name=label, y=[BY_KEY[x["condition"]].short for x in comparisons], x=values,
                    orientation="h", marker_color=color, customdata=[x[field]["starts"] for x in comparisons],
                    hovertemplate=("%{y}<br>%{x:.1%}<br>N=%{customdata}<extra>%{fullData.name}</extra>" if metric.endswith("rate") else "%{y}<br>%{x}<br>N=%{customdata}<extra>%{fullData.name}</extra>"))
            figure.update_layout(barmode="group")
            figure.update_xaxes(tickformat=".0%" if metric.endswith("rate") else "d", title_text=METRICS[metric])
            figure.update_yaxes(autorange="reversed")
            _figure(figure, 390)
            st.caption("A referência usa os outros pilotos nos mesmos GPs em que este piloto largou. Contagens mostram apenas o piloto; taxas permitem comparação.")
        if comparisons:
            with st.expander("Ver valores e amostras"):
                st.caption("Os valores e as amostras são os mesmos do gráfico. — indica amostra abaixo do mínimo escolhido.")
                st.markdown(_condition_values_html(comparisons, series, metric, minimum),
                            unsafe_allow_html=True)
    with right:
        st.subheader("Contra o companheiro de equipe")
        st.caption("Todas as condições no período selecionado.")
        mate = details["teammates"]
        if mate["comparable"]:
            figure = go.Figure()
            for label, field, color in (("À frente", "ahead", INK), ("Atrás", "behind", BLUE), ("Empates", "ties", "#cedce9")):
                figure.add_bar(name=label, x=[mate[field]], y=[translate("Corridas comparáveis")], orientation="h", marker_color=color)
            figure.update_layout(barmode="stack")
            _figure(figure, 180)
            st.caption("{} corridas comparáveis; {} à frente do companheiro.".format(mate["comparable"], mate["ahead"]))
        else:
            st.info("Sem corridas comparáveis com companheiro neste recorte.")
        st.info("Os resultados mostram associações históricas. Equipe, carro e época também influenciam o desempenho; este painel não estima habilidade isolada nem prevê a próxima corrida.")
        eligible = [x for x in details["conditions"] if x["driver"]["starts"] >= minimum]
        if eligible:
            best = max(eligible, key=lambda x: x["driver"][metric])
            tied = [x for x in eligible if abs(x["driver"][metric] - best["driver"][metric]) < 1e-12]
            if best["driver"][metric] > 0:
                evidence = " · ".join("{}: {} (N={})".format(translate(BY_KEY[x["condition"]].short),
                    _value(x["driver"][metric], metric), x["driver"]["starts"]) for x in tied)
                st.markdown("**{}:** {}.".format(translate("Destaque neste conjunto de condições"), evidence))
    _form(asset, details["races"])
    st.subheader("Evidências do piloto")
    _evidence(asset, details["races"], driver)
    with st.expander("Comparações com o companheiro, corrida a corrida"):
        if mate["evidence"]:
            st.dataframe(pd.DataFrame([{"GP": asset["gps"][x["race_id"]]["name"],
                "Temporada": asset["gps"][x["race_id"]]["temporada"], "Companheiro": x["teammate_name"],
                "Posição do piloto": x["own_position"], "Posição do companheiro": x["teammate_position"]}
                for x in mate["evidence"]]), hide_index=True, width="stretch")


def _remember_criterion(key):
    """Only an explicit criteria change commits a widget value to the scope."""
    filters = dict(st.session_state.get("_pilot_filters", {}))
    value = st.session_state[key]
    filters[key] = list(value) if isinstance(value, list) else value
    st.session_state["_pilot_filters"] = filters


def coverage_label(asset):
    latest=max(asset['gps'].values(),key=lambda gp:(gp['date_utc'],gp['temporada'],gp['rodada']))
    label=translate('Dados até {gp} · {date}')
    return label.format(gp=translate(latest['name']),date=date.fromisoformat(latest['date_utc']).strftime('%d/%m/%Y'))


def render(root):
    try:
        asset = load(root)
    except DriverConditionsError as error:
        st.error(str(error))
        return
    st.caption(coverage_label(asset))
    pending=asset.get('atualizacao_operacional',{}).get('pendencias',{})
    if pending:
        st.info(translate('Há {n} GP(s) em conferência. As comparações mantêm os últimos dados validados.').format(n=len(pending)))
    names = driver_names(asset)
    requested_ids = ([st.query_params.get("piloto"), st.query_params.get("rival")]
                     if st.query_params.get("visao") == "duelo"
                     else [st.query_params.get("piloto")])
    requested = next((pid for pid in requested_ids if pid and pid not in names), None)
    if requested and st.query_params.get("visao") in ("perfil", "duelo"):
        # Never silently replace an uncovered/unknown identity with another driver.
        name = None
        try:
            from pitwall.data.race_weekend import carregar_asset
            identities = carregar_asset(root).get("identidades", {})
            name = next((value.get("piloto") for key, value in identities.items()
                         if key.rsplit(":", 1)[-1] == requested and value.get("piloto")), None)
        except (OSError, ValueError, KeyError):
            pass
        title = name or translate("Perfil histórico indisponível")
        st.markdown('<section class="fan-hero fan-hero-empty" data-hero-kind="drivers"><div class="fan-hero-copy"><h1>{}</h1><p>{}</p></div></section>'.format(
            escape(title), escape(translate("Perfil histórico indisponível"))), unsafe_allow_html=True)
        st.info("Ainda não há dados deste piloto no acervo histórico de condições. O piloto solicitado não foi substituído.")
        params = dict(tela="Pilotos", visao="geral", lang=language(), **_navigation_context_params(st.query_params))
        for key in ("anos", "metrica", "minimo", "condicao", "faixas"):
            if key in st.query_params:
                params[key] = st.query_params[key]
        st.markdown('<a href="?{}" target="_self">← {}</a>'.format(
            escape(urlencode(params), quote=True), escape(translate("Voltar à visão geral"))), unsafe_allow_html=True)
        return
    for key, value in st.session_state.get("_pilot_filters", {}).items():
        if key in CRITERION_DEFAULTS or key not in st.session_state:
            st.session_state[key] = list(value) if isinstance(value, list) else value
    query = tuple(st.query_params.get(x) for x in ("piloto", "visao", "condicao", "anos", "metrica", "minimo", "faixas", "rival", "duelo_condicao"))
    if query != st.session_state.get("_pilot_query"):
        driver, view, condition, year_query, metric_query, minimum_query, bands, rival, duel_query = query
        if bands is not None:
            st.session_state["profile_conditions"] = [x for x in bands.split(",") if x in BY_KEY]
        duel_condition = st.query_params.get("duelo_condicao", "all")
        if duel_condition == "all" or duel_condition in BY_KEY:
            st.session_state["duel_condition"] = duel_condition
        if rival in driver_names(asset):
            st.session_state["duel_right"] = rival
        if year_query is not None:
            try:
                parsed_years = list(dict.fromkeys(int(x) for x in year_query.split(",")))
            except ValueError:
                parsed_years = []
            if (parsed_years or year_query == "") and all(x in (2024, 2025, 2026) for x in parsed_years):
                st.session_state["pilot_years"] = parsed_years
        if metric_query in METRICS:
            st.session_state["pilot_metric"] = metric_query
        if minimum_query in ("1", "3", "5", "10", "15"):
            st.session_state["pilot_minimum"] = int(minimum_query)
        if driver in driver_names(asset):
            st.session_state["pilot_driver"] = driver
        if view in ("perfil", "geral", "duelo"):
            st.session_state["pilot_view"] = {"perfil": "Perfil individual", "geral": "Visão geral", "duelo": "Duelo"}[view]
        if condition in BY_KEY:
            st.session_state["pilot_condition"] = condition
        st.session_state["_pilot_query"] = query
    st.session_state.setdefault("pilot_metric", "win_rate")
    st.session_state.setdefault("pilot_minimum", 5)
    st.session_state.setdefault("pilot_condition", "rain")
    filters = dict(st.session_state.get("_pilot_filters", {}))
    for key, default in CRITERION_DEFAULTS.items():
        value = st.session_state.get(key, default)
        filters[key] = list(value) if isinstance(value, list) else value
    st.session_state["_pilot_filters"] = filters
    if st.session_state["pilot_condition"] not in BY_KEY:
        st.session_state["pilot_condition"] = "rain"
    with st.container(key="pilot-cover"):
        with st.container(key="pilot-view-navigation"):
            modes = ["Visão geral", "Perfil individual", "Duelo"]
            selected_mode = st.session_state.get("pilot_view", modes[0])
            with st.popover("Explorar pilotos", icon=":material/person_search:"):
                view = st.radio("Visualização de pilotos", modes,
                    index=modes.index(selected_mode) if selected_mode in modes else 0,
                    key="pilot_view", label_visibility="collapsed")
        years = st.session_state.get("pilot_years", [2024, 2025, 2026])
        metric = st.session_state["pilot_metric"]
        minimum = st.session_state["pilot_minimum"]
        condition = st.session_state["pilot_condition"]
        from pitwall.dashboard.fan_views import hero
        title = {
            "rain": "Quem se destaca na chuva?",
            "track_hot": "Quem se destaca no calor?",
            "ccw": "Quem se destaca no sentido anti-horário?",
        }.get(condition, "Quem se destaca em cada condição?") if view == "Visão geral" else "Pilotos"
        # Dry Miami photograph for heat; the wet scene belongs to rain only.
        image = "drivers" if condition == "rain" and view == "Visão geral" else "forecast"
        names = driver_names(asset)
        person = None
        if view == "Perfil individual" and names:
            driver = st.session_state.get("pilot_driver")
            if driver not in names:
                driver = sorted(names, key=names.get)[0]
                st.session_state["pilot_driver"] = driver
            person = {"id": driver, "name": names[driver]}
            title = names[driver]
            image = "method"
        elif view == "Duelo":
            title = "Duelo"
            image = "championship"
        st.markdown(hero(title,
            "Compare resultados históricos por condição, com o período e a amostra de cada piloto.",
            image=image, dark=image == "drivers",
            extra=_condition_chips(years, metric, minimum, condition), person=person), unsafe_allow_html=True)
        with st.container(key="pilot-comparison-toolbar"):
            metadata, criteria = st.columns([4, 1], vertical_alignment="center")
            with metadata:
                st.markdown(_comparison_toolbar(years, metric, minimum), unsafe_allow_html=True)
            with criteria:
                with st.popover("Filtros", icon=":material/tune:", help="Período e critérios da comparação"):
                    # Match browser defaults to the canonical scope: components
                    # can rerun before native widgets apply set_value.
                    st.multiselect("Período", [2024, 2025, 2026], default=years,
                        key="pilot_years", on_change=_remember_criterion, args=("pilot_years",))
                    st.selectbox("Comparar por", list(METRICS), index=list(METRICS).index(metric),
                        format_func=METRICS.get, key="pilot_metric",
                        on_change=_remember_criterion, args=("pilot_metric",))
                    st.selectbox("Corridas mínimas por condição", [5, 3, 10, 15, 1],
                        index=[5, 3, 10, 15, 1].index(minimum), key="pilot_minimum",
                        on_change=_remember_criterion, args=("pilot_minimum",))
    from pitwall.dashboard.favorites import render as favorite_control
    favorite = st.session_state.get("browser_favorite", st.session_state.get("favorite_driver"))
    favorite = favorite if isinstance(favorite, str) and favorite in names else None
    st.session_state["favorite_driver"] = favorite
    def show_favorite():
        st.session_state["pilot_view"] = "Perfil individual"
        st.session_state["pilot_driver"] = favorite
    with st.container(key="pilot-favorite-control"):
        favorite_control(names, favorite)
    if favorite:
        st.button("Ver meu favorito", on_click=show_favorite)
    if not years:
        st.info("Selecione pelo menos uma temporada.")
    if years and view == "Visão geral":
        _overview(asset, years, metric, minimum)
    elif years and view == "Perfil individual":
        _individual(asset, years, metric, minimum)
    elif years:
        _duel(asset, years, metric, minimum)
    if years:
        _share(asset, years, metric, minimum, view)

    with st.expander("Como os números são calculados"):
        st.markdown("**Taxa de vitórias = vitórias ÷ largadas.** A taxa de pódios usa o mesmo denominador. Não largadas são excluídas; abandonos e desclassificações contam como oportunidades. Empates entre líderes são preservados.")
        st.markdown("Chuva significa registro do sensor durante os intervalos ativos da corrida, sem a pausa por bandeira vermelha. Ausência de chuva registrada não comprova pista seca. Temperaturas são médias das amostras nesses intervalos; as faixas são escolhas de análise, não limites universais.")
        st.markdown("Altitude é uma aproximação pontual do terreno. Suzuka fica no grupo de traçado em oito. Curvas, sentido e comprimento correspondem ao mapa FIA de cada edição.")
        st.caption("Também disponíveis como contexto auditado: umidade, pressão, velocidade e direção do vento, comprimento do circuito, nuvens e código WMO. As condições podem se sobrepor; suas largadas não devem ser somadas entre grupos.")
        st.markdown("No Duelo, os dois pilotos podem pertencer a equipes diferentes. Entram apenas GPs em que ambos largaram; o placar de posições usa resultados válidos e sem desclassificação.")
        st.markdown("Na comparação com o companheiro, os pilotos precisam estar na mesma equipe no mesmo GP, ambos com largada e posição válidas, sem desclassificação. Nenhum dos confrontos isola o efeito do carro.")
        st.markdown("Na auditoria da base até Austin, 17 compostos de pneus de treinos ou classificação ficaram indisponíveis. Essas lacunas permanecem ausentes e não participam destes rankings.")
        st.dataframe(pd.DataFrame([{"Condição": x.label, "Variável": x.variable} for x in CONDITIONS]), hide_index=True, width="stretch")
        st.markdown("[OpenF1](https://openf1.org/docs/) · [Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) · [Mapas FIA por edição](https://github.com/TracingInsights/DDocs/tree/9f647f7c62a838405c85219e5eb2feb5c3575027) · [Auditoria dos dados](https://github.com/mbpaschoal/pitwall-lab/tree/main/reports/pilotos_condicoes_20261029)")

def _form(asset, rows):
    recent = sorted(rows, key=lambda x: (asset["gps"][x["race_id"]]["temporada"], asset["gps"][x["race_id"]]["rodada"]))[-10:]
    st.subheader("Últimas participações no recorte")
    if not recent:
        st.info("Nenhuma corrida neste recorte.")
        return
    figure = go.Figure(go.Scatter(x=[asset["gps"][x["race_id"]]["date_utc"] for x in recent],
        y=[x["position"] if x["started"] and not x["disqualified"] else None for x in recent],
        text=[asset["gps"][x["race_id"]]["name"] + "<br>" + _appearance_date_label(
            asset["gps"][x["race_id"]]["date_utc"]) for x in recent], mode="lines+markers", connectgaps=False,
        marker_color=INK, hovertemplate="%{text}<br>%{y}<extra></extra>"))
    tick_rows = recent[::max(1, (len(recent) + 3) // 4)]
    if tick_rows[-1] is not recent[-1]:
        tick_rows.append(recent[-1])
    tick_dates = [asset["gps"][row["race_id"]]["date_utc"] for row in tick_rows]
    figure.update_xaxes(tickmode="array", tickvals=tick_dates,
                        ticktext=[_appearance_date_label(value) for value in tick_dates])
    figure.update_yaxes(autorange="reversed", title_text="Posição publicada", dtick=1)
    _figure(figure, 260)
    st.caption("Até dez participações. Não largadas e desclassificações ficam sem posição no gráfico; abandonos conservam a posição oficial.")


def _duel(asset, years, metric, minimum):
    from pitwall.research.driver_duel import duel
    names = driver_names(asset)
    ids = sorted(names, key=names.get)
    if len(ids) < 2:
        st.info("Escolha um período com pelo menos dois pilotos.")
        return
    if st.session_state.get("pilot_driver") not in ids:
        st.session_state["pilot_driver"] = ids[0]
    with st.container(key="duel-controls"):
        first, second = st.columns(2)
        with first:
            left = st.selectbox("Primeiro piloto", ids, index=ids.index(st.session_state["pilot_driver"]), format_func=names.get, key="pilot_driver")
        rivals = [x for x in ids if x != left]
        if st.session_state.get("duel_right") not in rivals:
            st.session_state["duel_right"] = rivals[0]
        with second:
            right = st.selectbox("Segundo piloto", rivals, index=rivals.index(st.session_state["duel_right"]), format_func=names.get, key="duel_right")
        conditions = ["all"] + list(BY_KEY)
        selected_condition = st.session_state.get("duel_condition", "all")
        condition = st.selectbox("Condição do duelo", conditions,
            index=conditions.index(selected_condition) if selected_condition in conditions else 0,
            format_func=lambda x: "Todas as condições" if x == "all" else BY_KEY[x].label, key="duel_condition")
    result = duel(asset, left, right, years, None if condition == "all" else condition)
    st.caption("{} largadas em comum; {} resultados comparáveis. Só entram GPs em que ambos largaram.".format(result["common_starts"], result["comparable_results"]))
    if not result["common_starts"]:
        st.info("Sem largadas em comum nesta condição. Experimente outro período ou condição.")
        return
    from pitwall.dashboard.fan_views import portrait
    with st.container(key="duel-stage"):
        a, b = st.columns(2)
        for column, pid, side, ahead in ((a, left, "left", "left_ahead"), (b, right, "right", "right_ahead")):
            with column:
                with st.container(key="duel-" + side):
                    st.markdown('<header class="fan-duel-driver" data-driver-id="{}">{}<h2>{}</h2></header>'.format(
                        escape(pid, quote=True), portrait(pid, names[pid]), escape(names[pid])), unsafe_allow_html=True)
                    st.metric("À frente do rival", result[ahead])
                    st.metric(METRICS[metric], _value(result[side][metric], metric) if result["common_starts"] >= minimum else "—")
                    st.caption("{} vitórias · {} pódios".format(result[side]["wins"], result[side]["podiums"]))
        st.markdown(_duel_difference_html(result, names[left], names[right], metric, minimum), unsafe_allow_html=True)
    if result["common_starts"] < minimum:
        st.info("Poucas corridas em comum para o mínimo escolhido. Explore os resultados ou reduza o filtro.")
    st.caption("Abandonos contam nas largadas. O placar compara posições oficiais conhecidas, sem desclassificações. Carro e época também contam.")
    _evidence(asset, [row for x in result["evidence"] for row in (x["left"], x["right"])], "duelo")


def _duel_difference_html(result, left_name, right_name, metric, minimum):
    """Describe the displayed metric, never the different finishing-order score."""
    title = translate("Diferença no recorte")
    a, b = result["left"][metric], result["right"][metric]
    if result["common_starts"] < minimum or a is None or b is None:
        detail = translate("Amostra abaixo do mínimo escolhido.")
        state = "insufficient"
    elif abs(a - b) < 1e-12:
        detail = translate("Empate nesta métrica.")
        state = "tied"
    else:
        difference = abs(a - b)
        if metric.endswith("rate"):
            amount = "{:.1f}".format(100 * difference)
            amount = amount.replace(".", ",") if language() == "pt" else amount
            amount += " " + translate("pontos percentuais")
        else:
            amount = str(int(difference))
        detail = translate("{} tem {} a mais nesta métrica.").format(
            left_name if a > b else right_name, amount)
        state = "left" if a > b else "right"
    return '<aside class="fan-duel-difference" data-state="{}" data-metric="{}" role="status"><span>{}</span><strong>{}</strong></aside>'.format(
        state, escape(metric, quote=True), escape(title), escape(detail))


def _share(asset, years, metric, minimum, view):
    from pitwall.dashboard.share_cards import card_svg
    mapping = {"Visão geral": "geral", "Perfil individual": "perfil", "Duelo": "duelo"}
    params = dict(tela="Pilotos", visao=mapping[view], anos=",".join(map(str, years)), metrica=metric,
        minimo=minimum, lang=language(), condicao=st.session_state.get("pilot_condition", "rain"),
        faixas=",".join(st.session_state.get("profile_conditions", HIGHLIGHTS)))
    params.update(_navigation_context_params(st.query_params))
    driver = st.session_state.get("pilot_driver")
    if driver:
        params["piloto"] = driver
    if view == "Duelo":
        params["rival"] = st.session_state.get("duel_right", "")
        params["duelo_condicao"] = st.session_state.get("duel_condition", "all")
    filters = dict(st.session_state.get("_pilot_filters", {}))
    filters.update({key: st.session_state[key] for key in ("pilot_condition", "pilot_driver", "pilot_view", "profile_conditions", "matrix_drivers", "duel_right", "duel_condition") if key in st.session_state})
    st.session_state["_pilot_filters"] = filters
    st.query_params.from_dict(params)
    st.session_state["_pilot_query"] = tuple(st.query_params.get(x) for x in ("piloto", "visao", "condicao", "anos", "metrica", "minimo", "faixas", "rival", "duelo_condicao"))
    title = translate("Pilotos")
    selected = select_rows(asset, years)
    facts = []
    if view == "Perfil individual" and driver:
        selected = select_rows(asset, years, driver=driver)
        title = driver_names(asset).get(driver, driver)
    if view == "Duelo" and driver and params.get("rival"):
        from pitwall.research.driver_duel import duel
        names = driver_names(asset)
        title = names[driver] + " × " + names[params["rival"]]
        cohort = params["duelo_condicao"]
        data = duel(asset, driver, params["rival"], years, None if cohort == "all" else cohort)
        facts = [translate("Largadas em comum") + ": " + str(data["common_starts"]),
                 names[driver] + ": " + str(data["left_ahead"]) + " / " + str(data["comparable_results"]) + " " + translate("À frente") + " · " + (_value(data["left"][metric], metric) if data["common_starts"] >= minimum else "—") + " " + translate(METRICS[metric]),
                 names[params["rival"]] + ": " + str(data["right_ahead"]) + " / " + str(data["comparable_results"]) + " " + translate("À frente") + " · " + (_value(data["right"][metric], metric) if data["common_starts"] >= minimum else "—") + " " + translate(METRICS[metric]),
                 translate("Todas as condições") if cohort == "all" else translate(BY_KEY[cohort].label)]
    else:
        stats = summarize(selected)
        facts = [translate(label) + ": " + str(stats[field]) for label, field in (("Largadas", "starts"), ("Vitórias", "wins"), ("Pódios", "podiums"))]
    with st.expander("Compartilhar esta análise"):
        url = "https://pitwall-lab.streamlit.app/?" + urlencode(params)
        st.session_state["share_current_url"] = url
        st.text_input("Link para compartilhar", key="share_current_url")
        st.caption("O link guarda período, métrica, condição e mínimo. O cartão resume resultados históricos no período selecionado.")
        svg = card_svg(title, ", ".join(map(str, years)) + " · " + coverage_label(asset), facts,
            "OpenF1 · Jolpica-F1 · Open-Meteo · pitwall-lab.streamlit.app", language() == "en")
        st.download_button("Baixar cartão (SVG)", svg, file_name="pitwall-comparacao.svg", mime="image/svg+xml", key="share_svg", on_click="ignore")
