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
    ranking, select_rows,
)


INK = "#102b50"
BLUE = "#7fa4ca"
SYMBOLS = {"rain": "☂", "track_hot": "☀", "ccw": "↶", "many_corners": "⌁",
           "high_altitude": "△", "track_cold": "❄"}


def _link(driver, condition="rain"):
    return "?" + urlencode({"tela": "Pilotos", "piloto": driver, "visao": "perfil",
                             "condicao": condition, "lang": language()})


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
        legend=dict(orientation="h", y=-.22), hovermode="closest")
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
        best = leaders(ranking(asset, key, metric, minimum, years))
        title = "Chuva registrada" if key == "rain" else BY_KEY[key].short
        if best:
            names = " · ".join('<a href="{}" target="_self">{}</a>'.format(
                escape(_link(x["driver_id"], key)), escape(x["driver_name"])) for x in best)
            details = "<br>".join("{}: {} / {} {}".format(escape(x["driver_name"]),
                x["podiums" if "podium" in metric else "wins"], x["starts"], translate("largadas")) for x in best)
            href = _link(best[0]["driver_id"], key)
            value = _value(best[0]["score"], metric)
            tie = translate("Empate") if len(best) > 1 else translate("Maior desempenho observado")
            cards.append('<article class="pilot-card"><div class="pilot-card-heading"><span>{}</span>{}</div>'
                '<small>{}</small><h3>{}</h3><strong>{}</strong><p>{}</p><a href="{}" target="_self">{} →</a></article>'.format(
                    SYMBOLS[key], escape(translate(title)), tie, names, value, details, escape(href), translate("Ver perfil")))
        else:
            cards.append('<article class="pilot-card"><div class="pilot-card-heading">{} {}</div><h3>{}</h3><p>{}</p></article>'.format(
                SYMBOLS[key], escape(translate(title)), translate("Sem destaque neste recorte"),
                translate("Amostra insuficiente ou nenhum sucesso registrado.")))
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
                orientation="h", marker_color=INK, customdata=[[x["starts"], x["wins"], x["podiums"]] for x in ordered],
                hovertemplate="%{y}<br>%{x}<br>N=%{customdata[0]}<extra></extra>"))
            figure.update_xaxes(tickformat=".0%" if metric.endswith("rate") else "d", title_text=METRICS[metric])
            _figure(figure, max(340, 27 * len(ordered)))
        else:
            st.info("Amostra insuficiente para esta condição.")
    with right:
        st.subheader("Mapa de condições")
        # Alphabetical inclusion is explicit; the complete matrix is available below.
        names = driver_names(asset, years)
        ids = sorted(names, key=names.get)
        matrix = {}
        for key in HIGHLIGHTS:
            matrix[key] = {x["driver_id"]: x["score"] for x in ranking(asset, key, metric, minimum, years)}
        figure = go.Figure(go.Heatmap(z=[[matrix[key].get(driver) for key in HIGHLIGHTS] for driver in ids],
            x=[BY_KEY[key].short for key in HIGHLIGHTS], y=[names[x] for x in ids],
            colorscale=[[0, "#eef4f9"], [1, "#102b50"]], hoverongaps=False,
            colorbar=dict(tickformat=".0%" if metric.endswith("rate") else "d")))
        figure.update_yaxes(autorange="reversed")
        _figure(figure, max(340, 27 * len(ids)))
        st.caption("Células vazias indicam amostra insuficiente. Todos os pilotos do período estão incluídos.")
    with st.expander("Corridas que sustentam a comparação"):
        _evidence(asset, select_rows(asset, years, condition), "condicao")


def _individual(asset, years, metric, minimum):
    names = driver_names(asset, years)
    ids = sorted(names, key=names.get)
    if st.session_state.get("pilot_driver") not in names:
        st.session_state["pilot_driver"] = ids[0]
    driver = st.selectbox("Piloto", ids, format_func=names.get, key="pilot_driver")
    details = profile(asset, driver, years)
    st.markdown('<div class="pilot-profile"><h2>{}</h2><p>{}</p></div>'.format(
        escape(details["driver_name"]), translate("Desempenho histórico por condição")), unsafe_allow_html=True)
    for column, label, field in zip(st.columns(3), ("Largadas", "Vitórias", "Pódios"), ("starts", "wins", "podiums")):
        column.metric(label, details["summary"][field])
    left, right = st.columns([1.3, 1])
    with left:
        st.subheader("Desempenho por condição")
        comparisons = details["conditions"]
        figure = go.Figure()
        reference_label = "Demais pilotos (taxa conjunta)" if metric.endswith("rate") else "Demais pilotos (total)"
        for field, label, color in (("driver", details["driver_name"], INK), ("reference", reference_label, BLUE)):
            values = [x[field][metric] if x[field]["starts"] >= minimum else None for x in comparisons]
            figure.add_bar(name=label, y=[BY_KEY[x["condition"]].short for x in comparisons], x=values,
                orientation="h", marker_color=color, customdata=[x[field]["starts"] for x in comparisons],
                hovertemplate="%{y}<br>%{x}<br>N=%{customdata}<extra>%{fullData.name}</extra>")
        figure.update_layout(barmode="group")
        figure.update_xaxes(tickformat=".0%" if metric.endswith("rate") else "d", title_text=METRICS[metric])
        figure.update_yaxes(autorange="reversed")
        _figure(figure, 390)
        st.caption("A referência reúne os demais pilotos nas mesmas condições. Barras exigem a amostra mínima selecionada.")
    with right:
        st.subheader("Contra o companheiro de equipe")
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
    query = tuple(st.query_params.get(x) for x in ("piloto", "visao", "condicao"))
    if query != st.session_state.get("_pilot_query"):
        driver, view, condition = query
        if driver in driver_names(asset):
            st.session_state["pilot_driver"] = driver
        if view in ("perfil", "geral"):
            st.session_state["pilot_view"] = "Perfil individual" if view == "perfil" else "Visão geral"
        if condition in BY_KEY:
            st.session_state["pilot_condition"] = condition
        st.session_state["_pilot_query"] = query
    st.markdown('<div class="pilot-header"><h1>Pilotos</h1><p>Quem se destaca em cada condição?</p></div>', unsafe_allow_html=True)
    view = st.radio("Visualização de pilotos", ["Visão geral", "Perfil individual"], horizontal=True, key="pilot_view", label_visibility="collapsed")
    period, measure, sample = st.columns([1.2, 1.3, 1])
    years = period.multiselect("Período", [2024, 2025, 2026], default=[2024, 2025, 2026], key="pilot_years")
    metric = measure.selectbox("Métrica", list(METRICS), format_func=METRICS.get, key="pilot_metric")
    minimum = sample.selectbox("Mínimo de largadas por condição", [5, 3, 10, 15, 1], key="pilot_minimum")
    st.caption("Corridas principais · 2026 até Austin · análises descritivas")
    if not years:
        st.info("Selecione pelo menos uma temporada.")
        return
    if view == "Visão geral":
        _overview(asset, years, metric, minimum)
    else:
        _individual(asset, years, metric, minimum)
    with st.expander("Como os números são calculados"):
        st.markdown("**Taxa de vitórias = vitórias ÷ largadas.** A taxa de pódios usa o mesmo denominador. Não largadas são excluídas; abandonos e desclassificações contam como oportunidades. Empates entre líderes são preservados.")
        st.markdown("Chuva significa registro do sensor durante os intervalos ativos da corrida, sem a pausa por bandeira vermelha. Ausência de chuva registrada não comprova pista seca. Temperaturas são médias das amostras nesses intervalos; as faixas são escolhas de análise, não limites universais.")
        st.markdown("Altitude é uma aproximação pontual do terreno. Suzuka fica no grupo de traçado em oito. Curvas, sentido e comprimento correspondem ao mapa FIA de cada edição.")
        st.caption("Também disponíveis como contexto auditado: umidade, pressão, velocidade e direção do vento, comprimento do circuito, nuvens e código WMO. As condições podem se sobrepor; suas largadas não devem ser somadas entre grupos.")
        st.markdown("O confronto exige dois pilotos da mesma equipe na mesma corrida, ambos com largada e posição válidas, sem desclassificação. Não mede ritmo isolado do carro.")
        st.markdown("17 compostos de pneus de treinos ou classificação seguem indisponíveis nas fontes consultadas. Eles permanecem ausentes e não participam destes rankings.")
        st.dataframe(pd.DataFrame([{"Condição": x.label, "Variável": x.variable} for x in CONDITIONS]), hide_index=True, width="stretch")
        st.markdown("[OpenF1](https://openf1.org/docs/) · [Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) · [Mapas FIA por edição](https://github.com/TracingInsights/DDocs/tree/9f647f7c62a838405c85219e5eb2feb5c3575027) · [Auditoria dos dados](https://github.com/mbpaschoal/pitwall-lab/tree/main/reports/pilotos_condicoes_20261029)")
