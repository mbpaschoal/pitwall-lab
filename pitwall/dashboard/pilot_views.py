"""Historical driver views. No collection, training or prediction occurs here."""

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


def _link(driver, condition="rain"):
    return "?" + urlencode({"tela": "Pilotos", "piloto": driver, "visao": "perfil",
                             "condicao": condition, "lang": language(),
        "anos": ",".join(map(str, st.session_state.get("pilot_years", [2024, 2025, 2026]))),
        "metrica": st.session_state.get("pilot_metric", "win_rate"),
        "minimo": st.session_state.get("pilot_minimum", 5),
        "faixas": ",".join(st.session_state.get("profile_conditions", HIGHLIGHTS))})


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
        "Fonte do circuito": st.column_config.LinkColumn(translate("Fonte do circuito"), display_text="FIA")})
    st.download_button("Baixar evidências (CSV)", dataframe(frame).to_csv(index=False).encode("utf-8-sig"),
                       file_name="pitwall-pilotos-{}.csv".format(key), mime="text/csv", key="csv_" + key)


def _overview(asset, years, metric, minimum):
    cards = []
    for key in HIGHLIGHTS:
        ranked_card = ranking(asset, key, metric, minimum, years)
        best = leaders(ranked_card)
        title = "Chuva registrada" if key == "rain" else BY_KEY[key].short
        if best:
            winners = []
            for leader in best:
                count = leader["podiums" if "podium" in metric else "wins"]
                evidence = translate("{} {} em {} corrida" if leader["starts"] == 1 else "{} {} em {} corridas").format(count, translate(("pódio" if count == 1 else "pódios") if "podium" in metric else ("vitória" if count == 1 else "vitórias")), leader["starts"])
                winners.append('<div class="pilot-leader"><h3><a href="{}" target="_self">{} →</a></h3><p>{}</p></div>'.format(escape(_link(leader["driver_id"], key)), escape(leader["driver_name"]), escape(evidence)))
            label = translate(METRICS[metric]) + (" · " + translate("Empate") if len(best) > 1 else "")
            cards.append('<article class="pilot-card"><div class="pilot-card-heading"><span>{}</span>{}</div><small>{}</small><strong>{}</strong>{}</article>'.format(SYMBOLS[key], escape(translate(title)), label, _value(best[0]["score"], metric), "".join(winners)))
        else:
            cards.append('<article class="pilot-card"><div class="pilot-card-heading">{} {}</div><h3>{}</h3><p>{}</p></article>'.format(
                SYMBOLS[key], escape(translate(title)), translate("Sem destaque neste recorte"),
                translate("Nenhum piloto alcança o mínimo de largadas." if not ranked_card else "Nenhuma vitória ou pódio nesta métrica e neste recorte.")))
    st.markdown('<div class="pilot-cards">' + "".join(cards) + "</div>", unsafe_allow_html=True)
    condition = st.selectbox("Condição para comparar", list(BY_KEY), format_func=lambda x: BY_KEY[x].label,
                             key="pilot_condition")
    ranked = ranking(asset, condition, metric, minimum, years)
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Classificação por condição")
        if ranked:
            ordered = list(reversed(ranked))
            figure = go.Figure(go.Bar(x=[x["score"] for x in ordered], y=[x["driver_name"] for x in ordered],
                orientation="h", marker_color=["#d3071d" if x["driver_id"] == st.session_state.get("favorite_driver") else INK for x in ordered], customdata=[[x["starts"], x["wins"], x["podiums"]] for x in ordered],
                hovertemplate=("%{y}<br>%{x:.1%}<br>N=%{customdata[0]}<extra></extra>" if metric.endswith("rate") else "%{y}<br>%{x}<br>N=%{customdata[0]}<extra></extra>")))
            figure.update_xaxes(tickformat=".0%" if metric.endswith("rate") else "d", title_text=METRICS[metric])
            _figure(figure, max(340, 27 * len(ordered)))
        else:
            st.info("Amostra insuficiente para esta condição.")
    with right:
        with st.expander("Mapa de condições"):
            # Alphabetical inclusion is explicit; the complete matrix is available below.
            names = driver_names(asset, years)
            if "matrix_drivers" in st.session_state:
                st.session_state["matrix_drivers"] = [x for x in st.session_state["matrix_drivers"] if x in names]
            ids = st.multiselect("Pilotos no mapa", sorted(names, key=names.get), default=sorted(names, key=names.get), format_func=names.get, key="matrix_drivers")
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
    driver = st.selectbox("Piloto", ids, format_func=names.get, key="pilot_driver")
    conditions = st.multiselect("Condições para explorar", list(BY_KEY), default=list(HIGHLIGHTS), format_func=lambda x: BY_KEY[x].label, key="profile_conditions")
    details = profile(asset, driver, years, conditions=conditions)
    back = _link(driver, st.session_state.get("pilot_condition", "rain")).replace("visao=perfil", "visao=geral")
    st.markdown('<a href="{}" target="_self">← {}</a>'.format(escape(back), escape(translate("Voltar à visão geral"))), unsafe_allow_html=True)
    st.markdown('<div class="pilot-profile"><h2>{}</h2><p>{}</p></div>'.format(
        escape(names[driver]), translate("Desempenho histórico por condição")), unsafe_allow_html=True)
    for column, label, field in zip(st.columns(3), ("Largadas", "Vitórias", "Pódios"), ("starts", "wins", "podiums")):
        column.metric(label, details["summary"][field])
    left, right = st.columns([1.3, 1])
    with left:
        st.subheader("Desempenho por condição")
        comparisons = details["conditions"]
        figure = go.Figure()
        reference_label = "Demais pilotos (taxa conjunta)" if metric.endswith("rate") else "Demais pilotos (total)"
        series = [("driver", details["driver_name"], INK)]
        if metric.endswith("rate"):
            series.append(("reference", reference_label, BLUE))
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


def render(root):
    try:
        asset = load(root)
    except DriverConditionsError as error:
        st.error(str(error))
        return
    for key, value in st.session_state.get("_pilot_filters", {}).items():
        if key not in st.session_state:
            st.session_state[key] = value
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
            if parsed_years and all(x in (2024, 2025, 2026) for x in parsed_years):
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
    st.markdown('<div class="pilot-header"><h1>Pilotos</h1><p>Quem se destaca em cada condição?</p></div>', unsafe_allow_html=True)
    from pitwall.dashboard.favorites import render as favorite_control
    favorite_slot = st.empty()
    names = driver_names(asset)
    favorite = st.session_state.get("browser_favorite", st.session_state.get("favorite_driver"))
    favorite = favorite if isinstance(favorite, str) and favorite in names else None
    st.session_state["favorite_driver"] = favorite
    if favorite and st.button("Ver meu favorito"):
        st.session_state["pilot_view"] = "Perfil individual"
        st.session_state["pilot_driver"] = favorite
    view = st.radio("Visualização de pilotos", ["Visão geral", "Perfil individual", "Duelo"], horizontal=True, key="pilot_view", label_visibility="collapsed")
    period = measure = sample = st.sidebar
    years = period.multiselect("Período", [2024, 2025, 2026], default=[2024, 2025, 2026], key="pilot_years")
    metric = measure.selectbox("Comparar por", list(METRICS), format_func=METRICS.get, key="pilot_metric")
    minimum = sample.selectbox("Corridas mínimas por condição", [5, 3, 10, 15, 1], key="pilot_minimum")
    st.caption("Corridas principais · 2026 até Austin · análises descritivas")
    if not years:
        st.info("Selecione pelo menos uma temporada.")
        return
    races = [gp for gp in asset["gps"].values() if gp["temporada"] in years]
    st.caption("{} corridas no período; {} com registro de chuva. Carro e época também influenciam os resultados.".format(len(races), sum(gp["rain_condition"] == "recorded" for gp in races)))
    if view == "Visão geral":
        _overview(asset, years, metric, minimum)
    elif view == "Perfil individual":
        _individual(asset, years, metric, minimum)
    else:
        _duel(asset, years, metric, minimum)
    _share(asset, years, metric, minimum, view)
    with st.expander("Como os números são calculados"):
        st.markdown("**Taxa de vitórias = vitórias ÷ largadas.** A taxa de pódios usa o mesmo denominador. Não largadas são excluídas; abandonos e desclassificações contam como oportunidades. Empates entre líderes são preservados.")
        st.markdown("Chuva significa registro do sensor durante os intervalos ativos da corrida, sem a pausa por bandeira vermelha. Ausência de chuva registrada não comprova pista seca. Temperaturas são médias das amostras nesses intervalos; as faixas são escolhas de análise, não limites universais.")
        st.markdown("Altitude é uma aproximação pontual do terreno. Suzuka fica no grupo de traçado em oito. Curvas, sentido e comprimento correspondem ao mapa FIA de cada edição.")
        st.caption("Também disponíveis como contexto auditado: umidade, pressão, velocidade e direção do vento, comprimento do circuito, nuvens e código WMO. As condições podem se sobrepor; suas largadas não devem ser somadas entre grupos.")
        st.markdown("O confronto exige dois pilotos da mesma equipe na mesma corrida, ambos com largada e posição válidas, sem desclassificação. Não mede ritmo isolado do carro.")
        st.markdown("17 compostos de pneus de treinos ou classificação seguem indisponíveis nas fontes consultadas. Eles permanecem ausentes e não participam destes rankings.")
        st.dataframe(pd.DataFrame([{"Condição": x.label, "Variável": x.variable} for x in CONDITIONS]), hide_index=True, width="stretch")
        st.markdown("[OpenF1](https://openf1.org/docs/) · [Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) · [Mapas FIA por edição](https://github.com/TracingInsights/DDocs/tree/9f647f7c62a838405c85219e5eb2feb5c3575027) · [Auditoria dos dados](https://github.com/mbpaschoal/pitwall-lab/tree/main/reports/pilotos_condicoes_20261029)")

    with favorite_slot.container():
        favorite_control(names, favorite)


def _form(asset, rows):
    recent = sorted(rows, key=lambda x: (asset["gps"][x["race_id"]]["temporada"], asset["gps"][x["race_id"]]["rodada"]))[-10:]
    st.subheader("Últimas participações no recorte")
    if not recent:
        st.info("Nenhuma corrida neste recorte.")
        return
    figure = go.Figure(go.Scatter(x=[asset["gps"][x["race_id"]]["date_utc"] for x in recent],
        y=[x["position"] if x["started"] and not x["disqualified"] else None for x in recent],
        text=[asset["gps"][x["race_id"]]["name"] for x in recent], mode="lines+markers", connectgaps=False,
        marker_color=INK, hovertemplate="%{text}<br>%{y}<extra></extra>"))
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
    left = st.selectbox("Primeiro piloto", ids, format_func=names.get, key="pilot_driver")
    rivals = [x for x in ids if x != left]
    if st.session_state.get("duel_right") not in rivals:
        st.session_state["duel_right"] = rivals[0]
    right = st.selectbox("Segundo piloto", rivals, format_func=names.get, key="duel_right")
    condition = st.selectbox("Condição do duelo", ["all"] + list(BY_KEY), format_func=lambda x: "Todas as condições" if x == "all" else BY_KEY[x].label, key="duel_condition")
    result = duel(asset, left, right, years, None if condition == "all" else condition)
    st.caption("{} largadas em comum; {} resultados comparáveis. Só entram GPs em que ambos largaram.".format(result["common_starts"], result["comparable_results"]))
    if not result["common_starts"]:
        st.info("Sem largadas em comum nesta condição. Experimente outro período ou condição.")
        return
    a, b = st.columns(2)
    for column, pid, side, ahead in ((a, left, "left", "left_ahead"), (b, right, "right", "right_ahead")):
        with column:
            st.subheader(names[pid])
            st.metric("À frente do rival", result[ahead])
            st.metric(METRICS[metric], _value(result[side][metric], metric) if result["common_starts"] >= minimum else "—")
            st.caption("{} vitórias · {} pódios".format(result[side]["wins"], result[side]["podiums"]))
    if result["common_starts"] < minimum:
        st.info("Poucas corridas em comum para o mínimo escolhido. Explore os resultados ou reduza o filtro.")
    st.caption("O confronto compara posições oficiais; abandonos contam. Resultados desclassificados ficam fora do placar de posições. Carro e época também contam.")
    _evidence(asset, [row for x in result["evidence"] for row in (x["left"], x["right"])], "duelo")


def _share(asset, years, metric, minimum, view):
    from pitwall.dashboard.share_cards import card_svg
    mapping = {"Visão geral": "geral", "Perfil individual": "perfil", "Duelo": "duelo"}
    params = dict(tela="Pilotos", visao=mapping[view], anos=",".join(map(str, years)), metrica=metric,
        minimo=minimum, lang=language(), condicao=st.session_state.get("pilot_condition", "rain"),
        faixas=",".join(st.session_state.get("profile_conditions", HIGHLIGHTS)))
    driver = st.session_state.get("pilot_driver")
    if driver:
        params["piloto"] = driver
    if view == "Duelo":
        params["rival"] = st.session_state.get("duel_right", "")
        params["duelo_condicao"] = st.session_state.get("duel_condition", "all")
    st.session_state["_pilot_filters"] = {key: st.session_state[key] for key in ("pilot_years", "pilot_metric", "pilot_minimum", "pilot_condition", "pilot_driver", "pilot_view", "profile_conditions", "matrix_drivers", "duel_right", "duel_condition") if key in st.session_state}
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
        svg = card_svg(title, ", ".join(map(str, years)) + " · " + translate("Dados até Austin 2026"), facts,
            "OpenF1 · Jolpica-F1 · Open-Meteo · pitwall-lab.streamlit.app", language() == "en")
        st.download_button("Baixar cartão (SVG)", svg, file_name="pitwall-comparacao.svg", mime="image/svg+xml", key="share_svg")
