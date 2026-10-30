"""Model evaluation views, isolated from GP navigation and collection."""
import pandas as pd
import plotly.graph_objects as go
from pitwall.i18n.streamlit import st

from pitwall.dashboard.tokens import CORES


def numero(valor):
    return "N/A" if valor is None else str(valor)


def nome_temporada(temporada):
    if temporada == 2024:
        return "2024 — validação já explorada"
    if temporada == 2025:
        return "2025 — avaliação final retrospectiva já realizada"
    return "2026 — snapshots locais, cobertura parcial"


def tabela_distribuicao(metricas):
    linhas = []
    for acertos in range(4):
        linhas.append(
            {
                "Integrantes corretos": acertos,
                "Modelo (GPs)": metricas["ranking_modelo"]["distribuicao_0_1_2_3"][
                    str(acertos)
                ],
                "Classificação (GPs)": metricas["ranking_classificacao"][
                    "distribuicao_0_1_2_3"
                ][str(acertos)],
            }
        )
    return pd.DataFrame(linhas)


def grafico_calibracao(calibracao):
    figura = go.Figure()
    configuracoes = {
        "modelo": {
            "nome": "Modelo · círculos",
            "cor": CORES["modelo"],
            "simbolo": "circle",
        },
        "constante": {
            "nome": "Constante · losangos",
            "cor": CORES["classificacao"],
            "simbolo": "diamond",
        },
    }
    for metodo, estilo in configuracoes.items():
        linhas = [
            linha
            for linha in calibracao
            if linha["metodo"] == metodo and linha["contagem"] > 0
        ]
        figura.add_trace(
            go.Scatter(
                x=[linha["media_prevista"] for linha in linhas],
                y=[linha["frequencia_observada"] for linha in linhas],
                mode="lines+markers",
                name=estilo["nome"],
                marker={
                    "color": estilo["cor"],
                    "symbol": estilo["simbolo"],
                    "size": 10,
                },
                line={"color": estilo["cor"]},
                customdata=[[linha["faixa"], linha["contagem"]] for linha in linhas],
                hovertemplate="Faixa %{customdata[0]} · n=%{customdata[1]}<br>Prevista: %{x:.3f}<br>Observada: %{y:.3f}<extra></extra>",
            )
        )
    figura.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            name="Referência perfeita",
            line={"color": CORES["neutro"], "dash": "dot"},
        )
    )
    figura.update_layout(
        height=460,
        paper_bgcolor=CORES["fundo"],
        plot_bgcolor=CORES["fundo"],
        font={"color": CORES["texto"]},
        margin={"l": 10, "r": 10, "t": 70, "b": 60},
        legend={"orientation": "h", "x": 0, "y": 1.04, "yanchor": "bottom"},
        xaxis={"title": "Média prevista", "range": [0, 1]},
        yaxis={"title": "Frequência observada", "range": [0, 1]},
    )
    return figura


def tabela_calibracao(calibracao):
    linhas = []
    faixas = sorted(
        {(linha["limite_inferior"], linha["limite_superior"]) for linha in calibracao}
    )
    for limites in faixas:
        atual = {
            linha["metodo"]: linha
            for linha in calibracao
            if (linha["limite_inferior"], linha["limite_superior"]) == limites
        }
        modelo, constante = atual["modelo"], atual["constante"]
        linhas.append(
            {
                "Faixa": modelo["faixa"],
                "Modelo n": modelo["contagem"],
                "Modelo: média / frequência": (
                    "—"
                    if modelo["contagem"] == 0
                    else "{:.3f} / {:.3f}".format(
                        modelo["media_prevista"], modelo["frequencia_observada"]
                    )
                ),
                "Constante n": constante["contagem"],
                "Constante: média / frequência": (
                    "—"
                    if constante["contagem"] == 0
                    else "{:.3f} / {:.3f}".format(
                        constante["media_prevista"], constante["frequencia_observada"]
                    )
                ),
            }
        )
    return pd.DataFrame(linhas)


def tela_desempenho(pacote):
    if pacote["temporada"] == 2026:
        st.title("Acertos do Lab")
        from pitwall.research.prospective_evaluation import prospective_races
        rows = prospective_races(pacote)
        if not rows:
            st.info("Ainda não há previsão registrada com resultado validado para avaliar em 2026.")
            return
        first, second, third = st.columns(3)
        first.metric("Corridas avaliadas",len(rows))
        second.metric("Integrantes do pódio acertados",'{} / {}'.format(sum(r['modelo'] for r in rows),3*len(rows)))
        third.metric("Pódios completos",'{} / {}'.format(sum(r['modelo']==3 for r in rows),len(rows)))
        st.caption("Somente previsões registradas antes da corrida e resultados posteriores validados. Poucas corridas não demonstram superioridade do modelo.")
        from urllib.parse import urlencode
        from pitwall.i18n import language
        frame = pd.DataFrame([{'GP':r['corrida'],'Acertos do Lab':r['modelo'],'Acertos da classificação':r['classificacao'],
            'Previsão registrada':'?'+urlencode(dict(tela='Previsões',temporada=2026,gp=r['rodada'],lang=language()))} for r in rows])
        st.dataframe(frame,hide_index=True,width='stretch',column_config={'Previsão registrada':st.column_config.LinkColumn(display_text='↗')})
        return
    metricas = pacote["metricas"]
    cobertura = metricas["cobertura"]
    total_prob = metricas["probabilisticas"]["linhas_avaliaveis"]
    total_gp = metricas["ranking_modelo"]["corridas_avaliaveis"]
    st.title("Acertos do Lab")
    st.caption(
        "{} · métricas lidas dos artefatos publicados".format(
            nome_temporada(pacote["temporada"])
        )
    )
    excluidos = cobertura["gps_total"] - total_gp
    st.subheader("Acertos entre os três escolhidos")
    st.caption(
        "Média de integrantes corretos entre três escolhas, em {} de {} GPs; {} excluído(s) por cobertura incompleta, sem transformar ausência em zero.".format(
            total_gp, cobertura["gps_total"], excluidos
        )
    )
    colunas = st.columns(2)
    colunas[0].metric(
        "Modelo",
        "{:.2f} de 3".format(metricas["ranking_modelo"]["media_integrantes_corretos"]),
    )
    colunas[1].metric(
        "Classificação",
        "{:.2f} de 3".format(
            metricas["ranking_classificacao"]["media_integrantes_corretos"]
        ),
    )

    completos_modelo = metricas["ranking_modelo"]["distribuicao_0_1_2_3"]["3"]
    completos_classificacao = metricas["ranking_classificacao"]["distribuicao_0_1_2_3"][
        "3"
    ]
    st.subheader("Pódios completos acertados")
    st.caption("Acerto dos três integrantes do pódio, independentemente da ordem")
    colunas = st.columns(2)
    colunas[0].metric("Modelo", "{} de {} GPs".format(completos_modelo, total_gp))
    colunas[1].metric(
        "Classificação", "{} de {} GPs".format(completos_classificacao, total_gp)
    )

    st.subheader("Comparação com a classificação")
    st.caption(
        "As duas listas são comparadas nos mesmos {} GPs avaliáveis. A tabela mostra quantos integrantes do pódio foram acertados; não promete ganho futuro.".format(
            total_gp
        )
    )
    st.dataframe(tabela_distribuicao(metricas), width="stretch", hide_index=True)

    with st.expander("Detalhes técnicos"):
        st.write(
            "Log loss penaliza especialmente probabilidades muito confiantes que erram; Brier mede a distância quadrática entre probabilidade e resultado. Em ambas, menor é melhor; nenhuma é porcentagem de acerto."
        )
        st.caption(
            "As métricas probabilísticas usam {} casos elegíveis com alvo conhecido.".format(
                total_prob
            )
        )
        tecnicas = pd.DataFrame(
            [
                {
                    "Métrica": "Log loss",
                    "Modelo": "{:.4f}".format(
                        metricas["probabilisticas"]["modelo"]["log_loss"]
                    ),
                    "Constante": "{:.4f}".format(
                        metricas["probabilisticas"]["constante"]["log_loss"]
                    ),
                },
                {
                    "Métrica": "Brier",
                    "Modelo": "{:.4f}".format(
                        metricas["probabilisticas"]["modelo"]["brier"]
                    ),
                    "Constante": "{:.4f}".format(
                        metricas["probabilisticas"]["constante"]["brier"]
                    ),
                },
            ]
        )
        st.dataframe(tecnicas, width="stretch", hide_index=True)
        st.subheader("Calibração descritiva")
        st.caption(
            "Eixo x: média prevista. Eixo y: frequência observada. Faixas vazias não viram pontos; a tabela preserva n=0."
        )
        st.plotly_chart(grafico_calibracao(pacote["calibracao"]))
        st.dataframe(
            tabela_calibracao(pacote["calibracao"]), width="stretch", hide_index=True
        )

    st.subheader("Cobertura e avaliação por GP")
    linhas = []
    for corrida in pacote["corridas"]:
        linhas.append(
            {
                "Rodada": corrida["rodada"],
                "GP": corrida["corrida"],
                "Participantes": corrida["participantes_preparados"],
                "Elegíveis": corrida["elegiveis"],
                "Alvos conhecidos": corrida["alvos_conhecidos"],
                "Modelo": numero(corrida["acertos_modelo"]),
                "Classificação": numero(corrida["acertos_classificacao"]),
                "Motivo de N/A": corrida["motivos_nao_avaliavel"] or "—",
            }
        )
    st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)
