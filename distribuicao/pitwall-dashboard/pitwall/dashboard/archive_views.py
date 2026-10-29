"""Vistas descritivas do acervo portátil; sem coleta, treino ou inferência."""

import math

import pandas as pd
import plotly.graph_objects as go
from pitwall.i18n.streamlit import st


ROTULOS_SESSAO = {
    "Practice 1": "TL1",
    "Practice 2": "TL2",
    "Practice 3": "TL3",
    "Qualifying": "Classificação",
    "Sprint Qualifying": "Classificação Sprint",
    "Sprint Shootout": "Classificação Sprint",
    "Sprint": "Sprint",
    "Race": "Corrida",
}
CORES_PNEU = {
    "SOFT": "#D3071D",
    "MEDIUM": "#E7B914",
    "HARD": "#C5CDD7",
    "INTERMEDIATE": "#168A55",
    "WET": "#2475EF",
}


def _chave(gp, sufixo):
    identidade = gp["identidade"]
    return "acervo_{}_{}_{}".format(
        identidade["temporada"], identidade["rodada"], sufixo
    )


def _valor(valor, unidade=""):
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, (float, int)) and not isinstance(valor, bool):
        if not math.isfinite(valor):
            return "—"
        return ("{:g}".format(valor) + unidade).replace(".", ",")
    return str(valor) + unidade


def _tempo(valor):
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, (list, tuple)):
        return " / ".join(
            "Q{}: {}".format(i + 1, _tempo(v)) for i, v in enumerate(valor)
        )
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if not math.isfinite(valor):
            return "—"
        minutos, segundos = divmod(float(valor), 60)
        horas, minutos = divmod(int(minutos), 60)
        return (
            "{}:{:02d}:{:06.3f}".format(horas, minutos, segundos)
            if horas
            else "{}:{:06.3f}".format(minutos, segundos)
        )
    return str(valor)


def _tabela(linhas, chave, nome):
    frame = pd.DataFrame(linhas)
    if frame.empty:
        st.info("Não há registros disponíveis para esta seleção.")
        return
    st.dataframe(frame, width="stretch", hide_index=True)
    from pitwall.i18n.streamlit import dataframe as display_dataframe

    st.download_button(
        "Baixar tabela CSV",
        display_dataframe(frame).to_csv(index=False).encode("utf-8-sig"),
        file_name=nome + ".csv",
        mime="text/csv",
        key=chave,
    )


def _figura_base(figura, altura=340):
    figura.update_layout(
        height=altura,
        margin={"l": 8, "r": 8, "t": 22, "b": 30},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"color": "#061226"},
        hovermode="closest",
    )
    return figura


def renderizar_tempos(gp):
    st.subheader("Tempos de sessão")
    sessoes = gp.get("sessoes", [])
    if not sessoes:
        st.info("Tempos de sessão ainda não disponíveis para este GP.")
        return
    por_id = {s["session_key"]: s for s in sessoes}
    selecionada = st.selectbox(
        "Sessão com tempos publicados",
        list(por_id),
        format_func=lambda key: ROTULOS_SESSAO.get(
            por_id[key]["nome"], por_id[key]["nome"]
        ),
        key=_chave(gp, "sessao_tempos"),
    )
    sessao = por_id[selecionada]
    nome = sessao["nome"]
    if nome in ("Race", "Sprint"):
        st.caption("Tempo total publicado para a prova. Não é o tempo de uma volta.")
    elif "Qualifying" in nome or "Shootout" in nome:
        st.caption(
            "Q1, Q2 e Q3 conservam as fases publicadas; ausência de tempo não é zero."
        )
    else:
        st.caption("Melhor volta publicada de cada piloto nesta sessão de treino.")
    if sessao.get("n_voltas") in (None, 0):
        st.info(
            "Voltas detalhadas desta sessão indisponíveis na OpenF1. Os tempos agregados disponíveis permanecem abaixo."
        )
    linhas = []
    for item in sessao.get("tempos", []):
        linha = {
            "Pos.": _valor(
                item.get("posicao")
                if item.get("posicao") is not None
                else item.get("posicao_original")
            ),
            "Piloto": item.get("piloto"),
            "Equipe": item.get("equipe"),
            "Tempo publicado": _tempo(item.get("duracao")),
            "Diferença publicada": _valor(item.get("gap")),
            "Voltas na sessão": item.get("voltas"),
        }
        if "Qualifying" in nome or "Shootout" in nome:
            linha.update(
                {
                    "Q1": _tempo(item.get("q1")),
                    "Q2": _tempo(item.get("q2")),
                    "Q3": _tempo(item.get("q3")),
                }
            )
        linhas.append(linha)
    _tabela(
        linhas,
        _chave(gp, "csv_tempos"),
        "tempos_{}_{}".format(gp["identidade"]["temporada"], selecionada),
    )
    for url in sorted(
        {
            item["fonte_validacao"]
            for item in sessao.get("tempos", [])
            if item.get("fonte_validacao")
        }
    ):
        st.markdown(
            "[Classificação oficial usada na conferência documental]({})".format(url)
        )

    alternativas = gp.get("voltas_fia") if nome == "Qualifying" else None
    if alternativas:
        st.subheader("Tempos de volta — complemento oficial FIA")
        st.caption(
            "223 durações publicadas e 20 horários de referência. Os horários iniciais não são durações; voltas de boxes e tempos afetados por interrupções estão preservados, sem classificar todas como voltas rápidas válidas."
        )
        st.markdown("[Documento oficial FIA]({})".format(alternativas[0]["fonte"]))
        _tabela(
            [
                {
                    "Número": v["numero"],
                    "Passagem FIA": v["volta_fia"],
                    "Tempo publicado": v["tempo_publicado"],
                    "Duração (s)": v["duracao_s"],
                    "Natureza": v["natureza"],
                    "Marcador de boxes": v["pit"],
                }
                for v in alternativas
            ],
            _chave(gp, "csv_voltas_fia"),
            "voltas_classificacao_fia",
        )
    with st.expander("Resultados e voltas da corrida selecionada"):
        renderizar_observado(gp)


def renderizar_estrategias(gp):
    st.subheader("Pneus e paradas observados")
    st.caption("Compostos e limites de voltas publicados por piloto.")
    estrategias = gp.get("estrategias", [])
    modalidades = list(dict.fromkeys(e.get("modalidade", "Race") for e in estrategias))
    if modalidades:
        modalidade = st.selectbox(
            "Prova para analisar os pneus",
            modalidades,
            format_func=lambda x: ROTULOS_SESSAO.get(x, x),
            key=_chave(gp, "prova_pneus"),
        )
        estrategias = [
            e for e in estrategias if e.get("modalidade", "Race") == modalidade
        ]
    if not estrategias:
        st.info("Stints de pneus não disponíveis para esta prova.")
    figura = go.Figure()
    legenda = set()
    linhas = []
    sinalizadas = 0
    for item in estrategias:
        piloto = item.get("piloto") or "Piloto {}".format(item.get("numero"))
        qualidade = item.get("qualidade")
        if qualidade:
            sinalizadas += 1
        for indice, stint in enumerate(item.get("sequencia_stints", []), 1):
            composto = stint.get("composto") or "Não informado"
            inicio, fim = stint.get("inicio"), stint.get("fim")
            linhas.append(
                {
                    "Piloto": piloto,
                    "Equipe": item.get("equipe"),
                    "Stint": indice,
                    "Composto": composto,
                    "Volta inicial publicada": inicio,
                    "Volta final publicada": fim,
                    "Idade inicial do pneu": stint.get("idade"),
                    "Limites comparáveis": item.get("comparavel"),
                    "Observações de qualidade": _qualidade_texto(qualidade),
                }
            )
            conhecidos = (
                isinstance(inicio, (int, float))
                and isinstance(fim, (int, float))
                and inicio > 0
                and fim >= inicio
            )
            if not conhecidos:
                continue
            cor = CORES_PNEU.get(str(composto).upper(), "#7A8CA5")
            if fim == inicio:
                figura.add_trace(
                    go.Scatter(
                        x=[inicio],
                        y=[piloto],
                        mode="markers",
                        marker={"color": cor, "size": 8, "symbol": "diamond"},
                        name=composto,
                        legendgroup=composto,
                        showlegend=composto not in legenda,
                        hovertemplate="%{y}<br>Volta %{x}<extra>"
                        + str(composto)
                        + "</extra>",
                    )
                )
            else:
                # São limites publicados, sem converter a largura em número de
                # voltas ou resolver fronteiras compartilhadas por suposição.
                figura.add_trace(
                    go.Bar(
                        x=[fim - inicio],
                        y=[piloto],
                        base=[inicio],
                        orientation="h",
                        name=composto,
                        legendgroup=composto,
                        showlegend=composto not in legenda,
                        marker={
                            "color": cor,
                            "line": {"color": "#546477", "width": 0.5},
                        },
                        customdata=[[inicio, fim]],
                        hovertemplate="%{y}<br>Limites: %{customdata[0]}–%{customdata[1]}<extra>"
                        + str(composto)
                        + "</extra>",
                    )
                )
            legenda.add(composto)
    if figura.data:
        _figura_base(figura, max(350, min(850, len(estrategias) * 27 + 95)))
        figura.update_layout(
            barmode="overlay",
            legend={"orientation": "h", "y": 1.15},
            xaxis_title="Limites de volta publicados",
            yaxis={"autorange": "reversed"},
        )
        st.plotly_chart(
            figura,
            use_container_width=True,
            config={"displayModeBar": False},
            key=_chave(gp, "pneus_grafico"),
        )
    if sinalizadas:
        st.info(
            "{} piloto(s) têm observações de qualidade nos limites dos stints. Valores ausentes ou inconsistentes permanecem na tabela.".format(
                sinalizadas
            )
        )
    if linhas:
        with st.expander("Detalhes dos stints e qualidade dos dados"):
            _tabela(
                linhas,
                _chave(gp, "csv_stints"),
                "stints_{}".format(_chave(gp, "pneus")),
            )
    st.subheader("Pit stops da corrida principal")
    paradas = gp.get("paradas", [])
    if paradas:
        st.caption(
            "Duração conforme a fonte de paradas. Não equivale automaticamente ao tempo parado para trocar pneus."
        )
        _tabela(
            [
                {
                    "Piloto": p.get("piloto"),
                    "Equipe": p.get("equipe"),
                    "Parada": p.get("parada"),
                    "Volta": p.get("volta"),
                    "Duração publicada (s)": p.get("duracao_s"),
                    "Fonte": p.get("fonte"),
                }
                for p in paradas
            ],
            _chave(gp, "csv_paradas"),
            "paradas_{}".format(_chave(gp, "gp")),
        )
    else:
        st.info(
            "Registros de pit stop não disponíveis. Ausência de registro não comprova zero paradas."
        )


def _qualidade_texto(valor):
    if not valor:
        return ""
    if isinstance(valor, str):
        return valor
    rotulos = {
        "lap_start_ausente": "volta inicial ausente",
        "lap_end_ausente": "volta final ausente",
        "lap_start_zero": "volta inicial zero na fonte",
        "lap_end_zero": "volta final zero na fonte",
        "limites_invertidos_na_fonte": "limites invertidos na fonte",
        "ordem_limites_diverge_stint_number": "ordem dos limites difere da sequência dos stints",
        "intervalos_sobrepostos_na_fonte": "intervalos sobrepostos na fonte",
        "fronteira_compartilhada_na_fonte": "fronteira compartilhada entre stints",
    }
    notas = []
    for item in valor:
        if isinstance(item, dict):
            flags = [
                rotulos.get(flag, str(flag).replace("_", " "))
                for flag in item.get("flags", [])
            ]
            notas.append(
                "Stint {}: {}".format(item.get("stint_number", "—"), "; ".join(flags))
            )
        else:
            notas.append(str(item).replace("_", " "))
    return " | ".join(notas)


def renderizar_clima(gp):
    actual = gp.get("clima_corrida_efetiva")
    if actual:
        st.subheader("Durante a corrida")
        columns = st.columns(3)
        columns[0].metric("Temperatura média do ar", _valor(actual["air_temperature"], " °C"))
        columns[1].metric("Temperatura média da pista", _valor(actual["track_temperature"], " °C"))
        columns[2].metric("Chuva registrada", "Sim" if actual["rain_condition"] == "recorded" else "Não")
        st.caption("Sensores OpenF1 nos intervalos ativos da corrida; pausas por bandeira vermelha são excluídas. Ausência de chuva registrada não comprova pista seca.")
        with st.expander("Janela efetiva e contexto atmosférico"):
            st.dataframe(pd.DataFrame(actual["active_intervals_utc"], columns=["Início (UTC)", "Fim (UTC)"]), hide_index=True, width="stretch")
            st.caption("Open-Meteo: reconstrução em grade, com amostras horárias dentro desses intervalos; não representa observação contínua na pista.")
            st.dataframe(pd.DataFrame(actual["atmospheric_context"]["amostras"]).rename(columns={"time_utc": "Hora (UTC)", "cloud_cover": "Cobertura de nuvens (%)", "weather_code": "Código meteorológico WMO"}), hide_index=True, width="stretch")
    st.subheader("Clima do fim de semana")
    clima = gp.get("clima") or {}
    horas = clima.get("horas") or []
    if not horas:
        st.info("Série meteorológica não disponível para este GP.")
        return
    st.caption(
        "Modelo atmosférico histórico próximo ao circuito; não é uma medição do asfalto."
    )
    if clima.get("origem") == "archived_forecast":
        st.info(
            "Esta série é uma previsão meteorológica arquivada, identificada pela fonte; não é uma medição realizada na pista."
        )
    st.markdown(
        "Dados meteorológicos por [Open-Meteo.com](https://open-meteo.com/) · [CC BY 4.0](https://open-meteo.com/en/licence)."
    )
    st.caption(
        "Horários em UTC. Modelo: {}. A precipitação corresponde ao acumulado de cada hora.".format(
            clima.get("modelo") or "informado pela fonte"
        )
    )
    st.caption(
        "Janela de {} a {} ({} horas). As estatísticas abaixo abrangem essa janela inteira.".format(
            horas[0]["data_utc"][:10], horas[-1]["data_utc"][:10], len(horas)
        )
    )
    resumo = clima.get("resumo") or {}
    colunas = st.columns(3)
    faixa = "{} a {} °C".format(
        _valor(resumo.get("temperatura_min_c")), _valor(resumo.get("temperatura_max_c"))
    )
    colunas[0].metric("Temperatura na janela", faixa)
    colunas[1].metric(
        "Precipitação na janela", _valor(resumo.get("precipitacao_total_mm"), " mm")
    )
    colunas[2].metric("Vento máximo", _valor(resumo.get("vento_max_ms"), " m/s"))
    frame = pd.DataFrame(horas)
    instante = pd.to_datetime(frame["data_utc"], errors="coerce", utc=True)
    temperatura = go.Figure(
        go.Scatter(
            x=instante,
            y=frame["temperatura_c"],
            mode="lines",
            name="Temperatura a 2 m",
            line={"color": "#D3071D", "width": 2},
            connectgaps=False,
        )
    )
    _figura_base(temperatura, 285)
    temperatura.update_layout(
        yaxis_title="Temperatura do ar (°C)", xaxis_title="Fim de semana (UTC)"
    )
    st.plotly_chart(
        temperatura,
        use_container_width=True,
        config={"displayModeBar": False},
        key=_chave(gp, "temperatura"),
    )
    chuva = go.Figure(
        go.Bar(
            x=instante,
            y=frame["precipitacao_mm"],
            name="Precipitação",
            marker_color="#2475EF",
        )
    )
    _figura_base(chuva, 245)
    chuva.update_layout(
        yaxis_title="Precipitação na hora (mm)", xaxis_title="Fim de semana (UTC)"
    )
    st.plotly_chart(
        chuva,
        use_container_width=True,
        config={"displayModeBar": False},
        key=_chave(gp, "precipitacao"),
    )
    with st.expander("Série horária e unidades"):
        _tabela(
            [
                {
                    "Data e hora (UTC)": h.get("data_utc"),
                    "Temperatura a 2 m (°C)": h.get("temperatura_c"),
                    "Umidade relativa (%)": h.get("umidade"),
                    "Precipitação (mm)": h.get("precipitacao_mm"),
                    "Vento a 10 m (m/s)": h.get("vento_ms"),
                    "Pressão (hPa)": h.get("pressao_hpa"),
                }
                for h in horas
            ],
            _chave(gp, "csv_clima"),
            "clima_{}".format(_chave(gp, "gp")),
        )
    sensores = clima.get("pista_sessoes") or []
    if sensores:
        st.subheader("Medições meteorológicas da pista")
        st.caption(
            "Fonte OpenF1. Resumo das medições por sessão, separado do modelo atmosférico Open-Meteo."
        )
        _tabela(
            [
                {
                    "Sessão": ROTULOS_SESSAO.get(s.get("nome"), s.get("nome")),
                    "Medições": s.get("n_medicoes"),
                    "Ar mínimo (°C)": s.get("temperatura_ar_min_c"),
                    "Ar máximo (°C)": s.get("temperatura_ar_max_c"),
                    "Pista mínima (°C)": s.get("temperatura_pista_min_c"),
                    "Pista máxima (°C)": s.get("temperatura_pista_max_c"),
                    "Chuva observada": s.get("chuva_observada"),
                }
                for s in sensores
            ],
            _chave(gp, "csv_pista"),
            "clima_pista_{}".format(_chave(gp, "gp")),
        )


def renderizar_observado(gp):
    st.subheader("Histórico observado deste GP")
    historico = gp.get("historico") or {}
    resumo = historico.get("resumo") or {}
    st.caption(
        "{} resultados, {} voltas com tempo e {} pilotos com voltas disponíveis. ".format(
            resumo.get("n_resultados", 0),
            resumo.get("n_voltas", 0),
            resumo.get("n_pilotos_com_voltas", 0),
        )
    )
    resultados = historico.get("resultados") or []
    if resultados:
        _tabela(
            [
                {
                    "Pos.": r.get("posicao"),
                    "Piloto": r.get("piloto"),
                    "Equipe": r.get("equipe"),
                    "Pontos": r.get("pontos"),
                    "Voltas publicadas": r.get("voltas"),
                    "Status": r.get("status"),
                    "Tempo publicado": r.get("tempo"),
                }
                for r in resultados
            ],
            _chave(gp, "csv_resultados"),
            "resultados_{}".format(_chave(gp, "gp")),
        )
    pilotos = historico.get("voltas_por_piloto") or []
    if not pilotos:
        st.info("Voltas da corrida principal ainda não disponíveis neste acervo.")
        return
    por_id = {str(p.get("piloto_id") or i): p for i, p in enumerate(pilotos)}
    selecionado = st.selectbox(
        "Piloto para consultar as voltas",
        list(por_id),
        format_func=lambda pid: por_id[pid].get("piloto") or pid,
        key=_chave(gp, "piloto_voltas"),
    )
    piloto = por_id[selecionado]
    voltas = piloto.get("voltas") or []
    if voltas:
        figura = go.Figure(
            go.Scatter(
                x=[v[0] for v in voltas],
                y=[v[1] for v in voltas],
                mode="lines+markers",
                name="Tempo observado",
                line={"color": "#2475EF"},
                marker={"size": 4},
                connectgaps=False,
            )
        )
        _figura_base(figura)
        figura.update_layout(xaxis_title="Volta", yaxis_title="Tempo observado (s)")
        st.plotly_chart(
            figura,
            use_container_width=True,
            config={"displayModeBar": False},
            key=_chave(gp, "voltas_grafico"),
        )
        st.caption(
            "Voltas de entrada/saída dos boxes, neutralizações e tráfego podem afetar estes tempos. O gráfico não isola ritmo ou degradação."
        )
        linhas = [{"Volta": v[0], "Tempo observado (s)": v[1]} for v in voltas]
        if any(len(v) > 2 and v[2] is not None for v in voltas):
            for linha, volta in zip(linhas, voltas):
                linha["Posição publicada"] = volta[2]
        _tabela(linhas, _chave(gp, "csv_voltas"), "voltas_{}".format(selecionado))


def renderizar_historico(gp):
    st.subheader("Desempenho dos pilotos nesta pista")
    historico = gp.get("historico_circuito") or {}
    st.caption(
        historico.get("escopo")
        or "Edições anteriores ainda não disponíveis no acervo portátil."
    )
    edicoes = historico.get("edicoes") or []
    if not edicoes:
        st.info("Não há corrida anterior nesta pista no acervo local disponível.")
        return
    st.caption(
        "{} edições anteriores, de {} a {}. A corrida selecionada está excluída.".format(
            len(edicoes),
            min(e["temporada"] for e in edicoes),
            max(e["temporada"] for e in edicoes),
        )
    )
    pilotos = historico.get("pilotos") or []
    atuais = {r["piloto_id"] for r in (gp.get("historico") or {}).get("resultados", [])}
    so_atuais = st.checkbox(
        "Mostrar apenas pilotos deste GP",
        value=bool(atuais),
        disabled=not atuais,
        key=_chave(gp, "historico_atuais"),
    )
    selecionados = [p for p in pilotos if not so_atuais or p["piloto_id"] in atuais]
    _tabela(
        [
            {
                "Piloto": p["piloto"],
                "Participações": p["participacoes"],
                "Vitórias": p["vitorias"],
                "Pódios": p["podios"],
                "Melhor posição": p["melhor_posicao"],
                "Posição média publicada": p["posicao_media"],
                "Pontos observados": p["pontos_observados"],
            }
            for p in selecionados
        ],
        _chave(gp, "csv_historico_pista"),
        "historico_pista",
    )
    if any("Archive" in e.get("fonte", "") for e in edicoes):
        st.caption(
            "Edições antigas: archive jtrotman/formula-1-race-data, identificado pelo ZIP local. UTC original de aquisição desconhecido. Valores não substituem fontes canônicas ou entradas do modelo."
        )
    st.caption(
        "Participações contam registros de resultado, inclusive DNS/DSQ. Médias usam somente posições publicadas, inclusive classificados que abandonaram; os estados de cada resultado estão abaixo. Pontuação e traçado podem mudar entre edições."
    )
    if not selecionados:
        st.info(
            "Os pilotos deste GP não têm participações anteriores no recorte. Desmarque o filtro para ver outros pilotos."
        )
        return
    por_id = {p["piloto_id"]: p for p in selecionados}
    pid = st.selectbox(
        "Piloto nas edições anteriores",
        list(por_id),
        format_func=lambda p: por_id[p]["piloto"],
        key=_chave(gp, "historico_piloto"),
    )
    _tabela(
        [
            {
                "Temporada": r["temporada"],
                "Rodada": r["rodada"],
                "Data": r["data"],
                "Equipe": r["equipe"],
                "Posição final": r["posicao"],
                "Pontos": r.get("pontos"),
                "Voltas": r.get("voltas"),
                "Status": r.get("status"),
            }
            for r in por_id[pid]["resultados"]
        ],
        _chave(gp, "csv_historico_piloto"),
        "historico_" + pid,
    )


def renderizar_equipes(gp):
    st.subheader("Comparativo de equipes no GP")
    equipes = gp.get("equipes") or []
    modalidades = list(dict.fromkeys(e.get("modalidade", "Race") for e in equipes))
    if not modalidades:
        st.info("Resultados por equipe ainda não disponíveis para este GP.")
        return
    modalidade = st.selectbox(
        "Modalidade do comparativo",
        modalidades,
        format_func=lambda x: ROTULOS_SESSAO.get(x, x),
        key=_chave(gp, "prova_equipes"),
    )
    selecionadas = [e for e in equipes if e.get("modalidade", "Race") == modalidade]
    st.caption("Resultados das equipes nesta prova. O campeonato está na visão geral.")
    _tabela(
        [
            {
                "Equipe": e.get("equipe"),
                "Resultados": e.get("n_resultados"),
                "Pontos observados": e.get("pontos"),
                "Pontos completos": e.get("pontos_completos"),
                "Posição média observada": e.get("posicao_media"),
                "Melhor posição": e.get("melhor_posicao"),
                "Pilotos": ", ".join(e.get("pilotos") or []),
            }
            for e in selecionadas
        ],
        _chave(gp, "csv_equipes"),
        "equipes_{}".format(_chave(gp, "gp")),
    )


def renderizar_fontes(gp, asset):
    st.caption("Versão do acervo: {}".format(asset.get("versao", "não informada")))
    st.markdown(
        "Fontes: [OpenF1](https://openf1.org/docs/), [Jolpica-F1](https://github.com/jolpica/jolpica-f1) e [Open-Meteo](https://open-meteo.com/)."
    )
    cobertura = gp.get("cobertura") or []
    parciais = [r for r in cobertura if r.get("estado") in ("parcial", "indisponivel")]
    if parciais:
        rotulos = {
            "laps_sessoes": "Voltas das sessões",
            "stints": "Limites dos stints",
            "estrategias_pneus": "Sequências de pneus",
            "clima_open_meteo": "Clima Open-Meteo",
            "clima_pista": "Medições meteorológicas da pista",
            "tempos_sessoes": "Tempos de sessão",
        }
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Conjunto": rotulos.get(
                            r.get("tipo"), str(r.get("tipo", "")).replace("_", " ")
                        ),
                        "Estado": r.get("estado"),
                        "Observação": r.get("motivo"),
                    }
                    for r in parciais
                ]
            ),
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption(
            "Conjuntos disponíveis; campos ausentes permanecem sinalizados nas tabelas."
        )
