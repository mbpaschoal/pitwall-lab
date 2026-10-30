"""Dashboard local, somente leitura, do estudo retrospectivo Pitwall Lab."""

import os
import base64
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from pitwall.paths import PROJECT_ROOT

import pandas as pd
import plotly.graph_objects as go
from pitwall.i18n.streamlit import st
from pitwall.i18n.controls import render as render_language

from pitwall.data.dashboard import (
    DashboardDadosErro,
    carregar_temporada_de_conteudos,
    conteudos_temporada,
    dados_do_gp,
    opcoes_gps,
)
from pitwall.data.race_weekend import (
    RaceWeekendDadosErro,
    carregar_asset,
    dados_do_gp_2026,
    identidade,
    nome_exibicao_piloto,
    pacote_2026,
)
from pitwall.data.editorial import (
    ContextoEditorialErro,
    carregar as carregar_contextos_editoriais,
    para_gp,
)
from pitwall.data.visual_catalog import (
    CatalogoVisualErro,
    carregar as carregar_catalogo_visual,
    para_circuito,
)
from pitwall.data.editorial_panels import carregar_paineis, complementar_paineis
from pitwall.data.archive import (
    AcervoDashboardErro,
    carregar as carregar_acervo_dashboard,
    para_gp as acervo_para_gp,
)
import pitwall.dashboard.archive_views as acervo_dashboard_ui
from pitwall.data.circuit_history import para_corrida_planejada
import pitwall.dashboard.components as pitwall_ui
from pitwall.publishing.documentation import renderizar_documentacao_local

from pitwall.dashboard.model_views import (tabela_distribuicao, grafico_calibracao, tabela_calibracao, tela_desempenho, numero, nome_temporada)

RAIZ_PADRAO = PROJECT_ROOT
from pitwall.dashboard.tokens import CORES
CORES_EQUIPE = {
    "ferrari": "#E53935",
    "red_bull": "#183153",
    "mercedes": "#00A19B",
    "mclaren": "#F58020",
    "aston_martin": "#006F62",
    "alpine": "#2475EF",
    "williams": "#2475EF",
    "haas": "#FFFFFF",
    "sauber": "#168A4A",
    "audi": "#B7BEC8",
    "rb": "#2475EF",
    "racing_bulls": "#2475EF",
}


def raiz_artefatos():
    """Gancho interno de teste; no uso normal, a raiz é a do projeto."""
    return Path(os.environ.get("PITWALL_DASHBOARD_ROOT", str(RAIZ_PADRAO)))


@st.cache_data(show_spinner=False)
def carregar_cacheado(temporada, conteudos):
    """Cache somente em memória: bytes participam diretamente da chave."""
    return carregar_temporada_de_conteudos(temporada, conteudos)


def carregar(temporada):
    try:
        contextos_editoriais = carregar_contextos_editoriais(raiz_artefatos())
    except ContextoEditorialErro as erro:
        raise RaceWeekendDadosErro(str(erro)) from erro
    if temporada == 2026:
        asset = carregar_asset(raiz_artefatos())
        pacote = pacote_2026(asset)
        pacote["asset_race_weekend"] = asset
        pacote["contextos_editoriais"] = contextos_editoriais
        try:
            pacote["catalogo_visual"] = carregar_catalogo_visual(raiz_artefatos())
        except CatalogoVisualErro:
            pacote["catalogo_visual"] = {}
        return pacote
    conteudos = conteudos_temporada(raiz_artefatos(), temporada)
    pacote = carregar_cacheado(temporada, conteudos)
    try:
        pacote["asset_race_weekend"] = carregar_asset(raiz_artefatos())
    except RaceWeekendDadosErro:
        pacote["asset_race_weekend"] = None
    pacote["contextos_editoriais"] = contextos_editoriais
    try:
        pacote["catalogo_visual"] = carregar_catalogo_visual(raiz_artefatos())
    except CatalogoVisualErro:
        pacote["catalogo_visual"] = {}
    return pacote


def percentual(valor):
    return "—" if valor is None else "{:.1f}%".format(valor * 100)






def corrida_editorial(pacote, corrida):
    """Acrescenta somente contexto factual de apresentação ao artefato do GP."""
    contexto = para_gp(
        pacote["contextos_editoriais"], pacote["temporada"], corrida["rodada"]
    )
    resultado = dict(corrida)
    resultado.update(contexto)
    return resultado


def nome_piloto(pacote, item):
    asset = pacote.get("asset_race_weekend")
    if asset:
        return identidade(
            asset, pacote["temporada"], item["rodada"], item["piloto_id"]
        )["piloto"]
    return "Nome indisponível ({})".format(item["piloto_id"])


def identidade_piloto(pacote, item):
    """Nome e equipe contextualizados pela temporada e rodada do GP."""
    asset = pacote.get("asset_race_weekend")
    if asset:
        return identidade(asset, pacote["temporada"], item["rodada"], item["piloto_id"])
    return {
        "piloto": nome_piloto(pacote, item),
        "equipe_id": item.get("equipe_id"),
        "equipe": item.get("equipe"),
    }


def nome_equipe(pacote, item):
    dados = identidade_piloto(pacote, item)
    return dados["equipe"] or "Equipe indisponível"


@st.cache_data(show_spinner=False)
def _asset_uri_cached(path, mime, modified_ns, size):
    return "data:{};base64,{}".format(mime, base64.b64encode(Path(path).read_bytes()).decode("ascii"))


def ativo_data_uri(caminho_relativo, mime):
    """Serve a small presentation derivative when available; preserve originals."""
    path = raiz_artefatos() / caminho_relativo
    derivative = raiz_artefatos() / "dashboard_assets/presentation" / (path.stem + ".webp")
    if mime.startswith("image/") and derivative.is_file():
        path, mime = derivative, "image/webp"
    try:
        stat = path.stat()
        return _asset_uri_cached(str(path), mime, stat.st_mtime_ns, stat.st_size)
    except OSError:
        return ""


def estilo_dashboard():
    return pitwall_ui.stylesheet(raiz_artefatos())


def aplicar_estilo():
    st.markdown(estilo_dashboard(), unsafe_allow_html=True)


def rotulo_resultado(posicao, status):
    status_normalizado = str(status or "").strip().lower()
    if status_normalizado in ("disqualified", "disqualificado", "desclassificado"):
        return "Desclassificação"
    if status_normalizado in ("retired", "abandoned", "abandonou"):
        return "Abandono"
    if status_normalizado in ("did not start", "dns", "não largou"):
        return "Não largou"
    if posicao in (1, 2, 3):
        return "Pódio"
    if isinstance(posicao, int) and 4 <= posicao <= 10:
        return "Pontuou fora do pódio"
    return "Resultado registrado"


def tabela_participantes(pacote, participantes):
    linhas = []
    for item in participantes:
        situacao = (
            "Elegível"
            if item["elegivel_previsao"]
            else "Inelegível: {}".format(item["motivos_inelegibilidade"])
        )
        if item["elegivel_previsao"] and item["podio"] is None:
            situacao += " · alvo desconhecido"
        linhas.append(
            {
                "Piloto": nome_piloto(pacote, item),
                "Equipe": nome_equipe(pacote, item),
                "ID": item["piloto_id"],
                "Situação": situacao,
                "Probabilidade de pódio": percentual(item["probabilidade_modelo"]),
                "Rank do modelo": numero(item["ranking_modelo"]),
                "Rank da classificação": numero(item["ranking_classificacao"]),
                "Alvo posterior conhecido": "sim" if item["alvo_conhecido"] else "não",
            }
        )
    return pd.DataFrame(linhas)


def tabela_campeonato_pilotos(campeonato):
    return pd.DataFrame(
        [
            {
                "Posição": item["posicao"],
                "Piloto": item["piloto"],
                "Equipe": item["equipe"] or "Equipe indisponível",
                "Pontos": item["pontos"],
                "Vitórias": item["vitorias"],
            }
            for item in campeonato["classificacao"]
        ]
    )


def cor_equipe(equipe):
    nome = str(equipe or "").lower()
    for identificador, cor in CORES_EQUIPE.items():
        if identificador.replace("_", " ") in nome:
            return cor
    return CORES["neutro"]


def tabela_campeonato_editorial(campeonato, limite=None):
    """Tabela completa da fotografia de campeonato."""
    linhas = []
    for item in (
        campeonato["classificacao"]
        if limite is None
        else campeonato["classificacao"][:limite]
    ):
        equipe = item["equipe"] or "Equipe indisponível"
        linhas.append(
            '<tr><td class="numero">{}</td><td>{}</td><td><span class="barra-equipe" style="background:{}"></span>{}</td><td class="numero">{}</td></tr>'.format(
                escape(str(item["posicao"])),
                escape(str(item["piloto"])),
                cor_equipe(equipe),
                escape(equipe),
                escape(str(item["pontos"])),
            )
        )
    return """
    <div class="tabela-editorial">
      <table aria-label="Campeonato de pilotos 2026">
        <thead><tr><th>Pos.</th><th>Piloto</th><th>Equipe</th><th class="numero">Pontos</th></tr></thead>
        <tbody>{}</tbody>
      </table>
    </div>
    """.format(
        "".join(linhas)
    )


def renderizar_campeonato_pilotos(pacote):
    campeonato = pacote.get("campeonato_pilotos")
    st.subheader(
        "Classificação de pilotos {}".format(pacote.get("temporada", "")).strip()
    )
    if not isinstance(campeonato, dict) or not isinstance(
        campeonato.get("disponivel"), bool
    ):
        st.info("Classificação de pilotos indisponível.")
        st.caption(
            "Snapshot DriverStandings ausente ou com schema inválido. Probabilidades por GP permanecem separadas."
        )
        return
    if not campeonato["disponivel"]:
        st.info("Classificação de pilotos indisponível.")
        st.caption(campeonato.get("motivo") or "Snapshot DriverStandings incompleto.")
        return
    campos = (
        "snapshot_id",
        "rodada_referencia",
        "obtido_em_utc",
        "paginas_validadas",
        "escopo",
        "classificacao",
    )
    if not all(campo in campeonato for campo in campos) or not isinstance(
        campeonato["classificacao"], list
    ):
        st.info("Classificação de pilotos indisponível.")
        st.caption(
            "Snapshot DriverStandings incompleto. Probabilidades por GP permanecem separadas."
        )
        return
    st.caption("DriverStandings Jolpica-F1, separado das probabilidades por GP.")
    st.caption(
        "Rodada de referência: {} · Obtido em UTC: {} · Snapshot: {} · {} página(s) paginada(s) validada(s).".format(
            campeonato["rodada_referencia"],
            campeonato["obtido_em_utc"],
            campeonato["snapshot_id"],
            campeonato["paginas_validadas"],
        )
    )
    st.caption(campeonato["escopo"])
    st.dataframe(
        tabela_campeonato_pilotos(campeonato), width="stretch", hide_index=True
    )


def tabela_calendario_2026(pacote, rodada_selecionada):
    return pd.DataFrame(
        [
            {
                "Rodada": corrida["rodada"],
                "Data": corrida["data_corrida"],
                "GP": corrida["corrida"],
                "Selecionado": "sim" if corrida["rodada"] == rodada_selecionada else "",
            }
            for corrida in sorted(pacote["corridas"], key=lambda item: item["rodada"])
        ]
    )


def renderizar_calendario_2026(pacote, rodada_selecionada):
    st.subheader("Calendário 2026")
    st.caption("Calendário da temporada; o GP selecionado está marcado.")
    st.dataframe(
        tabela_calendario_2026(pacote, rodada_selecionada),
        width="stretch",
        hide_index=True,
    )


def nome_estado_operacao(estado):
    return {
        "aguardando_dados": "Aguardando dados",
        "classificacao_disponivel": "Classificação disponível",
        "previsao_registrada": "Previsão registrada",
        "resultado_observado": "Resultado observado",
    }.get(estado, str(estado).replace("_", " ").capitalize())


def situacao_corrida(corrida):
    if corrida.get("estado_resultado") == "observado_local" or (
        corrida.get("estado_resultado") is None
        and corrida.get("alvos_conhecidos", 0) > 0
    ):
        return "Resultado observado"
    if corrida.get("estado_previsao") == "ensaio_retrospectivo":
        return "Ensaio retrospectivo"
    if corrida.get("estado_previsao") == "previsao_registrada":
        return "Previsão registrada"
    if corrida.get("estado_qualificacao") == "local_disponivel":
        return "Classificação disponível"
    return nome_estado_operacao(corrida.get("estado_operacao", "aguardando_dados"))


def renderizar_programacao(corrida):
    st.subheader("Programação do fim de semana")
    programacao = corrida.get("programacao")
    if not isinstance(programacao, list) or not programacao:
        st.caption("Programação não disponível no artefato local desta temporada.")
        return
    cabecalho = st.columns((2, 1, 1))
    cabecalho[0].markdown("**Sessão**")
    cabecalho[1].markdown("**Data**")
    cabecalho[2].markdown("**Hora**")
    for item in programacao:
        linha = st.columns((2, 1, 1))
        linha[0].write(item["sessao"])
        linha[1].write(item["data"])
        linha[2].write(item["hora"])


def renderizar_tempos_sessoes(bloco):
    tempos = bloco.get("tempos_sessoes")
    st.subheader("Tempos de sessão")
    if not tempos or not tempos.get("disponivel"):
        st.info(
            (tempos or {}).get(
                "motivo", "Tempos de sessão não disponíveis no pacote local."
            )
        )
        return
    st.caption(
        "Fonte: Formula1Dashboard · snapshot {} · {}".format(
            tempos["snapshot_id"], tempos["aviso_modelo"]
        )
    )
    rotulos = {"TL1": "TL1", "TL2": "TL2", "TL3": "TL3", "Q": "Qualifying"}
    chave = st.selectbox(
        "Sessão com tempos publicados",
        list(rotulos),
        format_func=lambda item: rotulos[item],
        key="sessao_tempos",
    )
    sessao = tempos["sessoes"][chave]
    linhas = []
    for item in sessao["linhas"]:
        linhas.append(
            {
                "Pos.": item["posicao"],
                "Piloto": nome_exibicao_piloto(item.get("piloto_id"), item["piloto"]),
                "Equipe": item["equipe"],
                "Tempo": item["tempo"] or "Sem tempo",
                "Gap ao líder (%)": (
                    None
                    if item["gap_percentual_lider"] is None
                    else round(item["gap_percentual_lider"], 3)
                ),
                "Q1": item["q1"] or "—",
                "Q2": item["q2"] or "—",
                "Q3": item["q3"] or "—",
            }
        )
    st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)


def renderizar_estado_dados(corrida):
    st.subheader("Estado dos dados")
    for nome, estado in (
        ("Classificação", corrida.get("estado_qualificacao", "histórico disponível")),
        ("Previsão", corrida.get("estado_previsao", "avaliação retrospectiva")),
        ("Resultado", corrida.get("estado_resultado", "observado")),
    ):
        linha = st.columns((1, 2))
        linha[0].markdown("**{}**".format(nome))
        linha[1].write(estado.replace("_", " "))


def renderizar_contexto_circuito(pacote, corrida, acervo_gp=None):
    ativos = (
        para_circuito(pacote.get("catalogo_visual", {}), corrida.get("circuito_id"))
        or {}
    )
    foto_meta, mapa_meta = ativos.get("foto"), ativos.get("mapa")
    foto = ativo_data_uri(foto_meta["caminho"], foto_meta["mime"]) if foto_meta else ""
    mapa = ativo_data_uri(mapa_meta["caminho"], mapa_meta["mime"]) if mapa_meta else ""
    paineis = carregar_paineis(
        raiz_artefatos(), pacote["temporada"], corrida["rodada"], corrida["circuito_id"]
    )
    if acervo_gp:
        paineis = complementar_paineis(paineis, acervo_gp)
        visao = pitwall_ui.visao_geral(
            corrida,
            paineis,
            foto,
            mapa,
            ativos.get("alt_foto", "Imagem ilustrativa do circuito"),
            clima=dict(acervo_gp.get("clima") or {}, corrida_efetiva=acervo_gp.get("clima_corrida_efetiva")),
            enquadramento_foto=foto_meta.get("enquadramento") if foto_meta else None,
        )
    else:
        visao = pitwall_ui.visao_geral(
            corrida,
            paineis,
            foto,
            mapa,
            ativos.get("alt_foto", "Imagem ilustrativa do circuito"),
            enquadramento_foto=foto_meta.get("enquadramento") if foto_meta else None,
        )
    st.markdown(
        visao,
        unsafe_allow_html=True,
    )


class TextoCredito(HTMLParser):
    def __init__(self):
        super().__init__()
        self.partes = []

    def handle_data(self, texto):
        self.partes.append(texto)


def credito_texto(valor):
    parser = TextoCredito()
    parser.feed(str(valor or "Fonte"))
    return "".join(parser.partes)


def renderizar_fontes_circuito(pacote, corrida, acervo_gp):
    ativos = (
        para_circuito(pacote.get("catalogo_visual", {}), corrida.get("circuito_id"))
        or {}
    )
    st.caption("Foto do circuito e mapa: ativos ilustrativos.")
    for label in ("foto", "mapa"):
        meta = ativos.get(label)
        if meta:
            st.markdown(
                '{}: <a href="{}" target="_blank" rel="noopener noreferrer">{}</a> · {}'.format(
                    "Imagem" if label == "foto" else "Mapa",
                    escape(meta["pagina"], quote=True),
                    escape(credito_texto(meta["autor"])),
                    escape(meta["licenca"]),
                ),
                unsafe_allow_html=True,
            )
    paineis = carregar_paineis(
        raiz_artefatos(), pacote["temporada"], corrida["rodada"], corrida["circuito_id"]
    )
    if acervo_gp:
        paineis = complementar_paineis(paineis, acervo_gp)
    st.caption(paineis["circuit_info"]["motivo_metricas"])
    for fonte in paineis["circuit_info"].get("fontes", []):
        st.markdown("[{}]({})".format(fonte["titulo"], fonte["url"]))
    for campo, titulo in [
        ("driver_standings", "Pilotos"),
        ("constructor_standings", "Construtores"),
    ]:
        snapshot = paineis[campo]
        if snapshot["disponivel"]:
            st.caption(
                "{}: rodada {} · captura UTC {}. {}".format(
                    titulo,
                    snapshot["rodada_referencia"],
                    snapshot.get("obtido_em_utc") or "desconhecida",
                    snapshot.get("escopo", ""),
                )
            )


def atalho_gp(pacote, corrida, tela, rotulo, aba=None):
    url = pitwall_ui.link_interno(
        pacote["temporada"], corrida["rodada"], tela=tela, aba=aba
    )
    st.markdown(
        '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(
            escape(url, quote=True), escape(rotulo)
        ),
        unsafe_allow_html=True,
    )


def renderizar_podio(pacote, corrida, participantes, acervo_gp=None):
    from urllib.parse import urlencode
    from pitwall.i18n import language
    official = ((acervo_gp or {}).get("historico") or {}).get("resultados", [])
    podium = sorted([r for r in official if r.get("posicao") in (1, 2, 3)], key=lambda r: r["posicao"])
    if podium:
        st.subheader("Pódio da corrida")
        for row in podium:
            link = "?" + urlencode(dict(tela="Pilotos", piloto=row["piloto_id"], visao="perfil", anos=pacote["temporada"], lang=language()))
            st.markdown("**{} · [{}]({})** · {}".format(row["posicao"], row["piloto"], link, row["equipe"]))
        return
    rows = [p for p in participantes if p.get("posicao_observada") in (1, 2, 3)]
    if rows:
        st.subheader("Pódio da corrida")
        for p in sorted(rows, key=lambda item: item["posicao_observada"]):
            st.markdown("**{} · {}**".format(p["posicao_observada"], nome_piloto(pacote, p)))
    elif corrida.get("podio_observado"):
        nomes = [nome_piloto(pacote, next(p for p in participantes if p["piloto_id"] == pid)) + " · " + nome_equipe(pacote, next(p for p in participantes if p["piloto_id"] == pid))
                 for pid in corrida["podio_observado"]]
        st.markdown("**Integrantes do pódio observado (sem ordem):** {}".format(", ".join(nomes)))
    else:
        st.info("Resultado ainda indisponível para este GP.")


def renderizar_condicoes_disponiveis(corrida):
    st.markdown(
        """
    <section class="condicoes-disponiveis">
      <p class="circuito-rotulo">Condições disponíveis</p>
      <p><strong>Dados meteorológicos indisponíveis no snapshot local.</strong></p>
      <p>O dashboard não estima clima, tempos de sessão ou estratégias antes de uma fonte pública canônica.</p>
    </section>
    """,
        unsafe_allow_html=True,
    )


def renderizar_desempenho_equipes_indisponivel():
    st.subheader("Comparativo de equipes")
    st.info("Comparativo indisponível para este GP.")


def aviso_favoritos_insuficientes(quantidade):
    if quantidade < 3:
        return "Aviso: há menos de três favoritos disponíveis neste ranking ({} de 3).".format(
            quantidade
        )
    return ""


def grafico_probabilidades(pacote, participantes=None):
    if participantes is None:
        participantes = pacote
        pacote = {"temporada": 0, "asset_race_weekend": None}
    elegiveis = [item for item in participantes if item["elegivel_previsao"]]
    elegiveis.sort(
        key=lambda item: (
            item.get("ranking_modelo") is None,
            item.get("ranking_modelo") or 9999,
            item["piloto_id"],
        )
    )
    if not elegiveis:
        figura = go.Figure()
        figura.add_annotation(
            text="Nenhum participante elegível para exibir probabilidades neste GP.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"color": CORES["texto"], "size": 15},
        )
        figura.update_layout(
            height=260,
            margin={"l": 10, "r": 20, "t": 25, "b": 40},
            paper_bgcolor=CORES["fundo"],
            plot_bgcolor=CORES["fundo"],
            font={"color": CORES["texto"]},
            xaxis={"visible": False},
            yaxis={"visible": False},
            showlegend=False,
        )
        return figura

    maior_percentual = max(item["probabilidade_modelo"] * 100 for item in elegiveis)
    figura = go.Figure(
        go.Bar(
            x=[item["probabilidade_modelo"] * 100 for item in elegiveis],
            y=[nome_piloto(pacote, item) for item in elegiveis],
            orientation="h",
            marker={
                "color": [
                    CORES_EQUIPE.get(
                        identidade_piloto(pacote, item).get("equipe_id") or "",
                        CORES["neutro"],
                    )
                    for item in elegiveis
                ],
                "line": {
                    "color": [
                        (
                            "#183153"
                            if identidade_piloto(pacote, item).get("equipe_id")
                            == "haas"
                            else "rgba(0,0,0,0)"
                        )
                        for item in elegiveis
                    ],
                    "width": 1,
                },
            },
            customdata=[nome_equipe(pacote, item) for item in elegiveis],
            hovertemplate="%{y}<br>Equipe: %{customdata}<br>Probabilidade: %{x:.1f}%<extra>pódio individual</extra>",
            name="Probabilidade do modelo",
        )
    )
    figura.update_layout(
        height=max(360, min(620, 28 * len(elegiveis) + 120)),
        margin={"l": 10, "r": 20, "t": 25, "b": 40},
        paper_bgcolor=CORES["fundo"],
        plot_bgcolor=CORES["fundo"],
        font={"color": CORES["texto"]},
        xaxis={
            "title": "Probabilidade individual de pódio (%)",
            "range": [0, min(100, max(10, maior_percentual * 1.15))],
        },
        yaxis={"title": "Piloto", "autorange": "reversed"},
        showlegend=False,
    )
    return figura


def renderizar_previsoes(pacote, bloco, participantes):
    if (
        pacote["temporada"] == 2026
        and bloco["corrida"]["estado_previsao"] == "indisponivel"
    ):
        st.subheader("Probabilidades de pódio")
        st.info("Sem probabilidades publicadas para este GP.")
        st.caption(
            "Faltam classificação concluída e emissão prospectiva registrada para este GP."
        )
        return
    st.subheader("Quem tinha mais chance de pódio")
    esquerda, direita = st.columns(2)
    with esquerda:
        st.markdown("**Modelo — top 3 por probabilidade**")
        for item in bloco["favoritos_modelo"]:
            st.write(
                "#{} · {} · {} · {}".format(
                    item["ranking_modelo"],
                    nome_piloto(pacote, item),
                    nome_equipe(pacote, item),
                    percentual(item["probabilidade_modelo"]),
                )
            )
    same = {x["piloto_id"] for x in bloco["favoritos_modelo"]} == {x["piloto_id"] for x in bloco["favoritos_classificacao"]}
    if same:
        direita.info("O Lab e a classificação escolheram os mesmos três pilotos.")
        direita.caption("A referência usa a ordem da classificação, sem atribuir probabilidades.")
    else:
        with direita:
            st.markdown("**Referência de classificação — top 3 por ranking**")
            only_reference = [item for item in bloco["favoritos_classificacao"] if item["piloto_id"] not in {x["piloto_id"] for x in bloco["favoritos_modelo"]}]
            st.caption("Diferentes da seleção do Lab")
            for item in only_reference:
                st.write(
                    "#{} · {} · {}".format(
                        item["ranking_classificacao"],
                        nome_piloto(pacote, item),
                        nome_equipe(pacote, item),
                    )
                )
            st.caption(
                "A referência é uma ordem por classificação; ela não recebe probabilidade."
            )
    for ranking, favoritos in (
        ("modelo", bloco["favoritos_modelo"]),
        ("referência de classificação", bloco["favoritos_classificacao"]),
    ):
        aviso = aviso_favoritos_insuficientes(len(favoritos))
        if aviso:
            st.warning("{} Ranking: {}.".format(aviso, ranking))
    st.subheader("Chances de pódio por piloto")
    st.caption("Probabilidade individual de pódio; valores arredondados para exibição.")
    st.plotly_chart(grafico_probabilidades(pacote, participantes))
    with st.expander("Detalhes por piloto"):
        st.dataframe(
            tabela_participantes(pacote, participantes),
            width="stretch",
            hide_index=True,
        )


def renderizar_resultados_observados(pacote, corrida, bloco, participantes):
    st.subheader("Avaliação após a corrida")
    if corrida["avaliavel_ranking"]:
        podio = [
            nome_piloto(
                pacote,
                next(item for item in participantes if item["piloto_id"] == piloto_id),
            )
            for piloto_id in corrida["podio_observado"]
        ]
        st.markdown(
            "**Integrantes do pódio observado (sem ordem):** {}".format(
                ", ".join(podio)
            )
        )
        col1, col2 = st.columns(2)
        col1.metric("Acertos — modelo", "{} de 3".format(corrida["acertos_modelo"]))
        col2.metric(
            "Acertos — classificação",
            "{} de 3".format(corrida["acertos_classificacao"]),
        )
        if corrida.get("estado_previsao") == "previsao_registrada":
            st.caption(
                "Avaliação posterior desta previsão registrada; conta os integrantes corretos, sem considerar a ordem."
            )
        else:
            st.caption(
                "Comparação retrospectiva; conta os integrantes corretos, sem considerar a ordem."
            )
    else:
        st.markdown(
            "**N/A — não avaliável.** Motivo: {}.".format(
                corrida["motivos_nao_avaliavel"].replace("_", " ")
            )
        )
        alvos_desconhecidos = [
            nome_piloto(pacote, item) for item in participantes if item["podio"] is None
        ]
        inelegiveis = [
            nome_piloto(pacote, item)
            for item in participantes
            if not item["elegivel_previsao"]
        ]
        if alvos_desconhecidos:
            st.markdown(
                "**Alvo(s) desconhecido(s) no GP:** {}".format(
                    ", ".join(alvos_desconhecidos)
                )
            )
        if inelegiveis:
            st.markdown(
                "**Participante(s) inelegível(is):** {}".format(", ".join(inelegiveis))
            )
        identificados = [
            nome_piloto(
                pacote,
                next(item for item in participantes if item["piloto_id"] == piloto_id),
            )
            for piloto_id in bloco["integrantes_identificados"]
        ]
        if identificados:
            st.markdown(
                "**Integrantes identificados na base, sem ordem:** {}".format(
                    ", ".join(identificados)
                )
            )
        if pacote["temporada"] == 2026 and corrida["podio_observado"]:
            st.caption(
                "O resultado observado permanece visível. Não há avaliação prospectiva oficial ou anual: a comparação disponível é retrospectiva, sem placar zero nem reclassificação da emissão."
            )
        elif (
            pacote["temporada"] == 2026 and corrida["estado_previsao"] == "indisponivel"
        ):
            st.caption(
                "Sem emissão deste GP, não há favoritos exibidos nem placar artificial."
            )
        else:
            st.caption(
                "O campo de pódio por GP fica vazio nesta cobertura; não há placar zero nem acerto artificial. Os favoritos continuam visíveis acima."
            )
    if pacote["temporada"] == 2026:
        st.subheader("Previsão e resultado observado")
        linhas = []
        for item in participantes:
            if (
                item["probabilidade_modelo"] is not None
                or item["resultado_observado"] is not None
            ):
                linhas.append(
                    {
                        "Piloto": nome_piloto(pacote, item),
                        "Equipe": nome_equipe(pacote, item),
                        "Previsão disponível": percentual(item["probabilidade_modelo"]),
                        "Rank previsto": numero(item["ranking_modelo"]),
                        "Resultado observado": numero(item["resultado_observado"]),
                        "Situação do resultado": rotulo_resultado(
                            item["resultado_observado"], item.get("status_resultado")
                        ),
                    }
                )
        if linhas:
            st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)
        else:
            st.info("Não há previsão ou resultado disponível para este GP.")


def sincronizar_navegacao():
    """Commit a native page change before query restoration runs."""
    st.query_params.pop("documento", None)
    st.query_params.pop("painel", None)
    st.query_params.update(tela=st.session_state["tela"])
    st.session_state["_query_aplicada"] = tuple(st.query_params.get(key) for key in ("temporada", "gp", "painel", "tela", "aba", "documento", "lang"))


def selecionar_gp_busca(valor):
    """Callback nativo: aplicado antes de o seletor lateral ser reconstruído."""
    st.session_state["gp"] = valor
    st.session_state["temporada"] = int(valor.split(":")[0])
    st.session_state["_query_gp_pendente"] = valor
    st.session_state["tela"] = "Corridas"
    st.query_params.update(temporada=valor.split(":")[0], gp=valor.split(":")[1])
    sincronizar_navegacao()


def renderizar_topo(pacote, corrida=None, participantes=None):
    with st.container(key="topbar"):
        breadcrumb, busca, perfil = st.columns(
            [0.70, 0.24, 0.06], gap="small", vertical_alignment="center"
        )
        with breadcrumb:
            st.markdown(
                '<div class="breadcrumb-editorial">{} <span>› &nbsp; {}</span></div>'.format(
                    escape(st.session_state.get("tela", "Corridas")),
                    escape("{} · GP {}".format(pacote["temporada"], corrida.get("rodada", "")) if corrida else str(pacote["temporada"])),
                ),
                unsafe_allow_html=True,
            )
        with busca:
            with st.popover(
                "Buscar corrida, piloto ou circuito…",
                icon=":material/search:",
                width="stretch",
            ):
                consulta = (
                    st.text_input(
                        "Buscar no Pitwall Lab",
                        key="busca_local",
                        placeholder="Ex.: Austin, Leclerc, Monza",
                    )
                    .strip()
                    .casefold()
                )
                st.caption("Corridas, pistas, pilotos e equipes de todo o acervo.")
                if consulta:
                    from pitwall.dashboard.search import search
                    from pitwall.i18n import language
                    matches = search(raiz_artefatos(), consulta, language())
                    if not (raiz_artefatos() / "frontend_assets/pilotos_condicoes.json").is_file() and participantes:
                        identities = [{"Piloto": nome_piloto(pacote, p), "Equipe": nome_equipe(pacote, p)} for p in participantes if consulta in nome_piloto(pacote, p).casefold()]
                        if identities:
                            st.dataframe(pd.DataFrame(identities), hide_index=True, width="stretch")
                    all_results = st.checkbox("Mostrar todos os resultados", key="search_all") if len(matches) > 12 else True
                    for result in (matches if all_results else matches[:12]):
                        if result["kind"] == "gp":
                            st.button(result["label"], key="busca_gp_" + result["value"],
                                      on_click=selecionar_gp_busca, args=(result["value"],), width="stretch")
                        else:
                            st.markdown('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(escape(result["href"]), escape(result["label"])), unsafe_allow_html=True)
                    if not matches:
                        st.info("Nenhum resultado. Tente outro nome de piloto, pista ou corrida, com pelo menos duas letras.")
        with perfil:
            with st.popover(
                "Preferências locais",
                icon=":material/settings:",
                help="Preferências desta sessão",
            ):
                st.checkbox("Abrir notas de fontes", key="mostrar_fontes")
                st.caption("Válido nesta sessão.")


def tela_explorar(pacote, rodada, foco):
    bloco = (
        dados_do_gp_2026(pacote, rodada)
        if pacote["temporada"] == 2026
        else dados_do_gp(pacote, rodada)
    )
    corrida = corrida_editorial(pacote, bloco["corrida"])
    bloco = dict(bloco)
    bloco["corrida"] = corrida
    participantes = bloco["participantes"]
    acervo_asset, acervo_gp = None, None
    if (raiz_artefatos() / "frontend_assets/acervo_dashboard.json").exists():
        try:
            acervo_asset = carregar_acervo_dashboard(raiz_artefatos())
            acervo_gp = acervo_para_gp(
                acervo_asset, pacote["temporada"], rodada, corrida["circuito_id"]
            )
        except AcervoDashboardErro as erro:
            st.warning("O acervo complementar não pôde ser exibido: {}.".format(erro))
    renderizar_topo(pacote, corrida, participantes)
    st.markdown(
        pitwall_ui.cabecalho(corrida, pacote["temporada"], situacao_corrida(corrida), show_prediction_note=foco == "Previsões"),
        unsafe_allow_html=True,
    )
    if foco == "Corridas":
        abas = (
            "Visão geral",
            "Tempos",
            "Estratégias",
            "Clima",
            "Histórico",
            "Comparativo de equipes",
        )
        aba = st.query_params.get("aba")
        visao_geral, tempos, estrategias, clima, historico, comparativo_equipes = (
            st.tabs([{"Visão geral": "Resumo", "Tempos": "Sessões e voltas", "Estratégias": "Pneus e paradas", "Histórico": "Nesta pista", "Comparativo de equipes": "Equipes"}.get(a, a) for a in abas], default={"Visão geral": "Resumo", "Tempos": "Sessões e voltas", "Estratégias": "Pneus e paradas", "Histórico": "Nesta pista", "Comparativo de equipes": "Equipes"}.get(aba, aba) if aba in abas else "Resumo")
        )
        with visao_geral:
            render_language(st, "Visão geral")
            renderizar_podio(pacote, corrida, participantes, acervo_gp)
            if acervo_gp:
                atalho_gp(pacote, corrida, "Corridas", "Ver classificação completa da corrida", aba="Tempos")
            renderizar_contexto_circuito(pacote, corrida, acervo_gp)
        with tempos:
            render_language(st, "Tempos")
            renderizar_programacao(corrida)
            if acervo_gp:
                acervo_dashboard_ui.renderizar_tempos(acervo_gp)
            else:
                renderizar_tempos_sessoes(bloco)
                renderizar_podio(pacote, corrida, participantes)
        with estrategias:
            render_language(st, "Estratégias")
            if acervo_gp:
                acervo_dashboard_ui.renderizar_estrategias(acervo_gp)
            else:
                st.info("Estratégias indisponíveis no pacote local.")
        with clima:
            render_language(st, "Clima")
            if acervo_gp:
                acervo_dashboard_ui.renderizar_clima(acervo_gp)
            else:
                renderizar_condicoes_disponiveis(corrida)
        with historico:
            render_language(st, "Histórico")
            if acervo_gp:
                acervo_dashboard_ui.renderizar_historico(acervo_gp)
            else:
                passado = para_corrida_planejada(
                    acervo_asset or {},
                    pacote["temporada"],
                    corrida["rodada"],
                    corrida["circuito_id"],
                    corrida["data"],
                )
                acervo_dashboard_ui.renderizar_historico(passado)
            if pacote["temporada"] == 2026:
                with st.expander("Calendário 2026"):
                    renderizar_calendario_2026(pacote, rodada)
        with comparativo_equipes:
            render_language(st, "Comparativo de equipes")
            if acervo_gp:
                acervo_dashboard_ui.renderizar_equipes(acervo_gp)
            else:
                renderizar_desempenho_equipes_indisponivel()
        atalho_gp(pacote, corrida, "Previsões", "Ver previsões deste GP")
        with st.expander(
            "Fontes e cobertura", expanded=st.session_state.get("mostrar_fontes", False)
        ):
            renderizar_fontes_circuito(pacote, corrida, acervo_gp)
            if acervo_gp:
                acervo_dashboard_ui.renderizar_fontes(acervo_gp, acervo_asset)
    else:
        with st.expander("Cobertura e exclusões"):
            st.caption(
                "Cobertura: {} participantes preparados · {} elegíveis · {} alvos conhecidos depois.".format(
                    corrida["participantes_preparados"],
                    corrida["elegiveis"],
                    corrida["alvos_conhecidos"],
                )
            )
            if not corrida["avaliavel_ranking"]:
                st.write(
                    "Ranking não avaliável: {}.".format(
                        corrida["motivos_nao_avaliavel"].replace("_", " ")
                    )
                )
        renderizar_previsoes(pacote, bloco, participantes)
        if any(item["probabilidade_modelo"] is not None for item in participantes):
            with st.expander("Avaliação da previsão"):
                renderizar_resultados_observados(pacote, corrida, bloco, participantes)
        atalho_gp(pacote, corrida, "Corridas", "Ver resultado e voltas", aba="Tempos")
        atalho_gp(pacote, corrida, "Campeonato", "Ver campeonato completo")










def entradas_documentadas():
    caminho = RAIZ_PADRAO / "docs" / "experimento_modelo_v1.md"
    try:
        linhas = caminho.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    inicio = None
    for indice, linha in enumerate(linhas):
        if linha.strip() == "```text" and indice > 30:
            inicio = indice + 1
            break
    if inicio is None:
        return []
    saida = []
    for linha in linhas[inicio:]:
        if linha.strip() == "```":
            break
        if linha.strip():
            saida.append(linha.strip())
    return saida


def tela_como_funciona():
    st.title("Como funciona")
    st.subheader("De onde vêm os dados?")
    st.write("Resultados e tempos vêm de Jolpica-F1 e OpenF1. O clima combina medições da pista e estimativas Open-Meteo, sempre identificadas. Cada comparação informa o período e quantas corridas entram.")
    st.subheader("O que significa uma chance de pódio?")
    st.write("É uma estimativa de terminar entre os três primeiros, sem prever a ordem. Uma chance de 70% não garante um pódio. As estimativas registradas ficam preservadas para comparar depois da corrida.")
    st.subheader("Como ler os destaques dos pilotos?")
    st.write("São resultados históricos no período escolhido. Carro, equipe e época também contam. Poucas corridas podem produzir percentuais altos; confira sempre o número de largadas.")
    with st.expander("Termos da corrida"):
        st.markdown("**Stint:** trecho entre trocas de pneus. **DNS:** não largou. **DSQ:** desclassificado. **Taxa de pódios:** pódios divididos pelas largadas.")
    with st.expander("Para quem quer ir além"):
        entradas = entradas_documentadas()
        st.subheader("Detalhes do modelo")
        st.markdown(
            "**Pergunta do estudo:** estimar a probabilidade individual de um piloto integrar o pódio de um GP principal. Não estima a ordem entre os três integrantes."
        )
        st.subheader("Método histórico")
        st.write(
            "Regressão logística com treino em 2021–2023, validação de 2024 já explorada e avaliação retrospectiva de 2025 já realizada. A classificação é uma referência de ranking distinta do grid registrado depois; ela não é uma probabilidade."
        )
        st.write(
            "As 15 entradas cobrem classificação, histórico recente de pilotos e equipes e indicadores de ausência."
        )
        st.write(
            "Células numéricas ausentes foram preenchidas com medianas aprendidas somente no treino elegível e rotulado. Depois, a escala também foi aprendida somente nesse treino e ficou congelada para 2024 e 2025."
        )
        st.write(
            "Regra exata de elegibilidade: classificação presente e referência temporal disponível. Posição de classificação ausente e histórico insuficiente não excluem o piloto: os indicadores de ausência são preservados e o pipeline congelado trata essas lacunas. Alvo ausente continua desconhecido e não participa da avaliação."
        )
        st.write(
            "Probabilidades individuais não são forçadas a somar três dentro de um GP."
        )
        st.subheader("{} entradas documentadas".format(len(entradas)))
        st.code(
            "\n".join(entradas) if entradas else "Lista indisponível no documento local.",
            language=None,
        )
        st.caption(
            "São associações no recorte histórico, não relações causais. O estudo tem poucas temporadas, participantes dependentes dentro de cada GP."
        )
        st.subheader("Fonte e limites")
        st.markdown(
            "Dados de [Jolpica-F1](https://github.com/jolpica/jolpica-f1), [OpenF1](https://openf1.org/docs/) e [Open-Meteo](https://open-meteo.com/). Consulte as licenças e a cobertura nas fontes de cada GP."
        )
        st.caption(
            "Jolpica-F1 e OpenF1: CC BY-NC-SA 4.0; clima Open-Meteo: CC BY 4.0. Fontes históricas podem ter revisões posteriores."
        )
        st.info(
            "Resultados retrospectivos não demonstram desempenho futuro e não são uma previsão ao vivo ou da próxima corrida."
        )
        renderizar_documentacao_local(st)


def executar_app():
    st.set_page_config(
        page_title="Pitwall Lab", layout="wide", initial_sidebar_state="auto"
    )
    from pitwall.i18n.controls import initialize, render as render_language

    initialize(st)
    aplicar_estilo()
    # Links dos painéis preservam temporada e GP; nenhum parâmetro altera dados.
    query_token = tuple(
        st.query_params.get(chave)
        for chave in ("temporada", "gp", "painel", "tela", "aba", "documento", "lang")
    )
    if query_token != st.session_state.get("_query_aplicada"):
        ano, gp_query, painel, tela_query, _, documento, _ = query_token
        if tela_query in ("Corridas", "Pilotos", "Campeonato", "Previsões", "Desempenho", "Metodologia"):
            st.session_state["tela"] = tela_query
        elif painel in ("pilotos", "equipes"):
            st.session_state["tela"] = "Campeonato"
        if documento:
            st.session_state["tela"] = "Metodologia"
        if (
            ano in ("2024", "2025", "2026")
            and re.fullmatch(r"[0-9]{1,2}", str(gp_query))
            and 1 <= int(gp_query) <= 24
        ):
            st.session_state["temporada"] = int(ano)
            st.session_state["_query_gp_pendente"] = "{}:{}".format(ano, int(gp_query))
        st.session_state["_query_aplicada"] = query_token
    st.sidebar.markdown(
        '<div class="sidebar-title">Pitwall Lab</div>', unsafe_allow_html=True
    )
    st.sidebar.markdown(
        '<div class="sidebar-caption">DADOS · CONTEXTO · PERFORMANCE</div>',
        unsafe_allow_html=True,
    )
    tela = st.sidebar.radio(
        "Navegação", ("Corridas", "Pilotos", "Campeonato", "Previsões", "Desempenho", "Metodologia"), key="tela", on_change=sincronizar_navegacao, format_func=lambda value: {"Previsões": "Chances de pódio", "Desempenho": "Acertos do Lab", "Metodologia": "Como funciona"}.get(value, value)
    )
    st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    if tela == "Pilotos":
        from pitwall.dashboard.pilot_views import render
        renderizar_topo({"temporada": "2024–2026"})
        render_language(st)
        render(raiz_artefatos())
        return
    st.session_state.setdefault("temporada", st.session_state.get("_temporada_anterior_dashboard", 2026 if (raiz_artefatos() / "frontend_assets/pilotos_condicoes.json").is_file() else 2025))

    def manter_temporada():
        if st.session_state.get("temporada") not in (2024, 2025, 2026):
            st.session_state["temporada"] = st.session_state.get(
                "_temporada_anterior_dashboard", 2025
            )

    temporada = st.sidebar.selectbox(
        "Temporada",
        (2024, 2025, 2026),
        index=None,
        key="temporada",
        on_change=manter_temporada,
    )
    try:
        pacote = carregar(temporada)
    except (DashboardDadosErro, RaceWeekendDadosErro) as erro:
        st.error(str(erro))
        st.stop()
    anterior = st.session_state.get("_temporada_anterior_dashboard")
    opcoes = opcoes_gps(pacote)
    valores = [item["valor"] for item in opcoes]
    if anterior != temporada:
        if temporada == 2026:
            observadas = [
                item["valor"]
                for item in opcoes
                if dados_do_gp_2026(pacote, item["rodada"])["corrida"][
                    "alvos_conhecidos"
                ]
            ]
            st.session_state["gp"] = observadas[-1] if observadas else valores[0]
        else:
            st.session_state.pop("gp", None)
        st.session_state["_temporada_anterior_dashboard"] = temporada
    descricoes = {
        item["valor"]: "{:02d} — {}".format(item["rodada"], item["corrida"])
        for item in opcoes
    }
    gp_pendente = st.session_state.pop("_query_gp_pendente", None)
    if gp_pendente in valores:
        st.session_state["gp"] = gp_pendente

    def manter_gp():
        if st.session_state.get("gp") not in valores:
            st.session_state["gp"] = valores[0]

    if "gp" not in st.session_state and st.session_state.get("_gp_context") in valores:
        st.session_state["gp"] = st.session_state["_gp_context"]
    if tela in ("Corridas", "Previsões", "Campeonato"):
        gp = st.sidebar.selectbox(
            "Grande Prêmio",
            valores,
            format_func=lambda valor: descricoes.get(valor, str(valor)),
            key="gp",
            index=None if "gp" in st.session_state else 0,
            on_change=manter_gp,
        )
        st.session_state["_gp_context"] = gp
    else:
        gp = st.session_state.get("_gp_context", st.session_state.get("gp", valores[0]))
    st.sidebar.caption("Dados até Austin 2026")
    if tela != "Corridas":
        render_language(st)
    if gp not in descricoes:
        por_descricao = {descricao: valor for valor, descricao in descricoes.items()}
        gp = por_descricao.get(gp, valores[0])
    rodada = int(gp.split(":", 1)[1])
    if tela in ("Corridas", "Previsões"):
        tela_explorar(pacote, rodada, tela)
    elif tela == "Campeonato":
        bloco = dados_do_gp_2026(pacote, rodada) if temporada == 2026 else dados_do_gp(pacote, rodada)
        corrida = corrida_editorial(pacote, bloco["corrida"])
        renderizar_topo(pacote, corrida)
        paineis = carregar_paineis(raiz_artefatos(), temporada, rodada, corrida["circuito_id"])
        try:
            arquivo = carregar_acervo_dashboard(raiz_artefatos())
            gp_acervo = acervo_para_gp(arquivo, temporada, rodada, corrida["circuito_id"])
            if gp_acervo:
                paineis = complementar_paineis(paineis, gp_acervo)
        except AcervoDashboardErro:
            pass
        st.title("Campeonato")
        st.markdown(pitwall_ui.campeonatos(paineis, temporada), unsafe_allow_html=True)
    elif tela == "Desempenho":
        renderizar_topo(pacote)
        tela_desempenho(pacote)
    else:
        renderizar_topo(pacote)
        tela_como_funciona()


if __name__ == "__main__":
    executar_app()
