"""Dashboard local, somente leitura, do estudo retrospectivo Pitwall Lab."""

import os
import base64
import re
from datetime import time
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from pitwall.paths import PROJECT_ROOT

import pandas as pd
import plotly.graph_objects as go
from pitwall.i18n.streamlit import st
from pitwall.i18n import translate, language
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
    para_gp as acervo_para_gp,
)
from pitwall.dashboard.archive_cache import carregar as carregar_acervo_dashboard
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
    """Serve the full-resolution source; never silently select a small derivative."""
    path = raiz_artefatos() / caminho_relativo
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
    if status_normalizado in ("retired", "abandoned", "abandonou", "dnf", "nc"):
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
        from pitwall.data.standings_state import publication_message
        st.info("Classificação de pilotos indisponível.")
        st.caption(publication_message(campeonato))
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
    status = nome_estado_operacao(corrida.get("estado_operacao", "aguardando_dados"))
    if status == "Aguardando dados":
        from datetime import date
        try:
            if date.fromisoformat(corrida["data"][:10]) > date.today():
                return "Etapa futura"
        except (ValueError, KeyError, TypeError):
            pass
    return status


def renderizar_programacao(corrida):
    st.subheader("Programação do fim de semana")
    programacao = corrida.get("programacao")
    if not isinstance(programacao, list) or not programacao:
        st.caption("Programação não disponível no artefato local desta temporada.")
        return
    rows = []
    for item in programacao:
        hour = item['hora']
        try:
            parsed = time.fromisoformat(hour)
            # Preserve unusual seconds and offsets instead of silently changing them.
            if not parsed.second and not parsed.microsecond and (parsed.utcoffset() is None or parsed.utcoffset().total_seconds() == 0):
                hour = parsed.strftime('%H:%M')
        except (TypeError, ValueError):
            pass
        rows.append('<tr><th scope="row">{}</th><td>{}</td><td>{}</td></tr>'.format(
            escape(translate(item['sessao'])), escape(pitwall_ui.data_editorial(item['data'])), escape(hour)))
    rows = ''.join(rows)
    st.markdown('<table class="pw-weekend-schedule"><caption>{}</caption><thead><tr><th scope="col">{}</th><th scope="col">{}</th><th scope="col">{}</th></tr></thead><tbody>{}</tbody></table>'.format(
        escape(translate('Programação em UTC')), escape(translate('Sessão')),
        escape(translate('Data')), escape(translate('Hora (UTC)')), rows
    ), unsafe_allow_html=True)


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


def renderizar_contexto_circuito(pacote, corrida, acervo_gp=None, mode="full", weekend=None, include_media=True):
    ativos = (
        para_circuito(pacote.get("catalogo_visual", {}), corrida.get("circuito_id"))
        or {}
    )
    foto_meta, mapa_meta = ativos.get("foto"), ativos.get("mapa")
    from pitwall.dashboard.media import circuit_photo_source
    foto = circuit_photo_source(raiz_artefatos(), corrida.get('circuito_id'), foto_meta) if foto_meta else ""
    mapa = ativo_data_uri(mapa_meta["caminho"], mapa_meta["mime"]) if mapa_meta else ""
    paineis = carregar_paineis(
        raiz_artefatos(), pacote["temporada"], corrida["rodada"], corrida["circuito_id"]
    )
    if mode in ('hero','details','media'):
        from pitwall.dashboard.fan_views import hero,circuit_details
        if acervo_gp:
            paineis=complementar_paineis(paineis,acervo_gp)
        if mode=='hero':
            map_html=('<div class="fan-hero-map"><img src="{}" alt="{}"><strong>{}</strong></div>'.format(mapa,escape('Mapa do circuito '+corrida['circuito_nome']),escape(corrida['circuito_nome']))) if mapa else ''
            date_label=pitwall_ui.data_editorial(corrida.get('data')).removesuffix(str(pacote['temporada'])).strip()
            meta='{} · {}\n{}'.format(corrida.get('cidade',''),pacote['temporada'],date_label)
            tooltip='Temporada {} · {}, {} · {}'.format(pacote['temporada'],corrida.get('cidade',''),corrida.get('pais',''),corrida.get('data',''))
            observed=next((s for s in (weekend or {}).get('sessoes',[]) if s['nome']=='Race'),{})
            status='Resultado publicado pela OpenF1' if observed.get('encerramento_observado_utc') and observed.get('tempos') else situacao_corrida(corrida)
            if corrida.get('resultado_posterior_validado') and any(
                    str(row.get('fonte_validacao', '')).endswith('_final_race_classification.pdf')
                    for row in observed.get('tempos', [])):
                status='Resultado final conferido com a FIA'
            map_html+='<span class="fan-gp-status" title="{}">{}</span>'.format(escape(tooltip,quote=True),escape(translate(status)))
            if corrida.get('estado_previsao')!='previsao_registrada' and (pacote['temporada']!=2026 or corrida.get('estado_previsao')=='ensaio_retrospectivo'):
                map_html+='<small class="fan-context-note">{}</small>'.format(escape(translate('Estudo retrospectivo com dados históricos.')))
            st.markdown(hero(corrida['corrida'],meta,image='race',photo=foto,alt=ativos.get('alt_foto_en' if language()=='en' else 'alt_foto',ativos.get('alt_foto','')),extra=map_html,photo_left=(foto_meta or {}).get('enquadramento')=='pista-esquerda',photo_meta=foto_meta),unsafe_allow_html=True)
        else:
            if mode == 'details':
                climate=dict((acervo_gp or {}).get('clima') or {},corrida_efetiva=(acervo_gp or {}).get('clima_corrida_efetiva'))
                observed=next((s for s in (weekend or {}).get('sessoes',[]) if s['nome']=='Race'),{}).get('clima_observado',{})
                air=observed.get('campos',{}).get('air_temperature',{})
                if air.get('elegivel'):
                    climate['corrida_efetiva']=dict(air_temperature=air['media_amostras'])
                st.markdown(circuit_details(paineis['circuit_info'],climate,pitwall_ui.link_interno(pacote['temporada'],corrida['rodada'],aba='Clima')),unsafe_allow_html=True)
            if (mode == 'media' or include_media) and (foto or mapa):
                with st.expander('Foto e mapa do circuito'):
                    for source, meta, label in ((foto, foto_meta, 'Foto do circuito'), (mapa, mapa_meta, 'Mapa do circuito')):
                        if source:
                            credit = credito_texto((meta or {}).get('credito') or (meta or {}).get('autor') or '')
                            url = (meta or {}).get('pagina', '')
                            st.markdown('<figure class="pw-circuit-media"><img src="{}" alt="{}" loading="lazy" decoding="async"><figcaption>{} · <a href="{}" target="_blank" rel="noopener noreferrer">{}</a></figcaption></figure>'.format(source, escape(translate(label), quote=True), escape(credit), escape(url, quote=True), escape(translate((meta or {}).get('licenca', 'Fonte')))), unsafe_allow_html=True)
        return
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


def atalho_gp(pacote, corrida, tela, rotulo, aba=None, full_width=False):
    st.button(
        rotulo,
        key="atalho_gp_{}_{}_{}_{}".format(pacote["temporada"], corrida["rodada"], tela, aba or "geral"),
        type="tertiary",
        width="stretch" if full_width else "content",
        on_click=selecionar_destino_gp,
        args=(pacote["temporada"], corrida["rodada"], tela, aba),
    )


def renderizar_podio(pacote, corrida, participantes, acervo_gp=None, weekend=None, compact=False):
    from pitwall.dashboard.fan_views import podium
    official=((acervo_gp or {}).get('historico') or {}).get('resultados',[])
    rows=[dict(id=r['piloto_id'],name=r['piloto'],team=r.get('equipe'),position=r.get('posicao')) for r in official if r.get('posicao') in (1,2,3)]
    if not rows:
        rows=[dict(id=p['piloto_id'],name=nome_piloto(pacote,p),team=nome_equipe(pacote,p),position=p.get('posicao_observada')) for p in participantes if p.get('posicao_observada') in (1,2,3)]
    if not rows and weekend:
        race=next((r for r in weekend.get('sessoes',[]) if r['nome']=='Race'),{})
        rows=[dict(id=r.get('piloto_id'),name=nome_exibicao_piloto(r.get('piloto_id'),r['piloto']),team=r.get('equipe'),position=r['posicao']) for r in race.get('tempos',[]) if r.get('posicao') in (1,2,3)]
    if rows or not corrida.get('podio_observado'):
        st.markdown(podium(rows,pacote['temporada'],compact=compact,round_=corrida['rodada']),unsafe_allow_html=True)
    if not rows and corrida.get('podio_observado'):
        st.caption("Integrantes do pódio observado (sem ordem):")
        for pid in corrida['podio_observado']:
            p=next((p for p in participantes if p['piloto_id']==pid),None)
            if p:st.write("{} · {}".format(nome_piloto(pacote,p),nome_equipe(pacote,p)))


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


def renderizar_previsoes(pacote, bloco, participantes, acervo_gp=None, weekend=None, cards_slot=None):
    if (
        pacote["temporada"] == 2026
        and bloco["corrida"]["estado_previsao"] == "indisponivel"
    ):
        return
    from pitwall.dashboard.tarot import render as render_tarot
    with (cards_slot if cards_slot is not None else st.container()):
        render_tarot(st, raiz_artefatos(), [
            dict(driver_id=p['piloto_id'], name=nome_piloto(pacote, p),
                 team=nome_equipe(pacote, p), probability=p['probabilidade_modelo'])
            for p in bloco['favoritos_modelo']
        ], pacote['temporada'], bloco['corrida']['rodada'],
           bloco['corrida'].get('estado_previsao') == 'previsao_registrada',
           emission=bloco['corrida'].get('emissao_sha256'), country=bloco['corrida'].get('pais'))
    with st.container(key='forecast-details'):
        st.header('Antes da corrida')
        same={x['piloto_id'] for x in bloco['favoritos_modelo']}=={x['piloto_id'] for x in bloco['favoritos_classificacao']}
        if same:
            st.markdown('<p class="fan-forecast-baseline">{}</p>'.format(escape(translate('O Lab e a classificação escolheram os mesmos três pilotos.'))),unsafe_allow_html=True)
        else:
            with st.expander('Comparar com a classificação'):
                for item in bloco['favoritos_classificacao']:
                    st.write(nome_piloto(pacote,item))
        corrida=bloco['corrida']
        observed=next((s for s in (weekend or {}).get('sessoes',[]) if s['nome']=='Race'),{})
        observed_places={r.get('posicao') for r in observed.get('tempos',[]) if r.get('posicao') in (1,2,3)}
        if corrida.get('podio_observado') or any(p.get('posicao_observada') in (1,2,3) for p in participantes) or (observed.get('encerramento_observado_utc') and observed_places=={1,2,3}):
            with st.container(key='prediction-after'):
                phase,result=st.columns([1,2.3],vertical_alignment='center')
                with phase:
                    st.markdown('<div class="fan-timeline-stage"><h2>{}</h2></div>'.format(escape(translate('Depois da corrida'))),unsafe_allow_html=True)
                with result:
                    with st.container(key='prediction-result'):
                        renderizar_podio(pacote,corrida,participantes,acervo_gp,weekend,compact=True)
        for ranking, favoritos in (
            ("modelo", bloco["favoritos_modelo"]),
            ("referência de classificação", bloco["favoritos_classificacao"]),
        ):
            aviso = aviso_favoritos_insuficientes(len(favoritos))
            if aviso:
                st.warning("{} Ranking: {}.".format(aviso, ranking))
        with st.expander("Chances de pódio por piloto"):
            st.caption("Probabilidade individual de pódio; valores arredondados para exibição.")
            st.plotly_chart(grafico_probabilidades(pacote, participantes))
            st.dataframe(tabela_participantes(pacote,participantes),width="stretch",hide_index=True)

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
        motivo = corrida["motivos_nao_avaliavel"].replace("_", " ")
        if pacote["temporada"] == 2026 and corrida.get("estado_previsao") == "previsao_registrada":
            from pitwall.dashboard.fan_views import evaluation_reason
            motivo = translate(evaluation_reason(corrida["motivos_nao_avaliavel"]))
        st.markdown(
            "**N/A — não avaliável.** Motivo: {}.".format(
                motivo
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
        if pacote["temporada"] == 2026 and corrida.get("estado_previsao") == "previsao_registrada":
            st.caption(
                "Resultado posterior validado; este GP ficou fora da avaliação de ranking. A previsão registrada e suas probabilidades permanecem preservadas."
                if corrida.get("resultado_posterior_validado") is True and corrida.get("estado_resultado") == "observado_local" else
                "Resultado posterior ainda não validado; a previsão registrada permanece preservada, sem placar artificial."
            )
        elif pacote["temporada"] == 2026 and corrida["podio_observado"]:
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
    st.query_params.pop("cartas", None)
    st.query_params.pop("equipe", None)
    st.query_params.pop("campanha", None)
    st.query_params.pop("campeao", None)
    st.query_params.pop("rival_campeao", None)
    params = dict(tela=st.session_state["tela"])
    gp = st.session_state.get("_gp_context",st.session_state.get("gp"))
    if isinstance(gp,str) and re.fullmatch(r"202[456]:[0-9]{1,2}",gp):
        params.update(temporada=gp.split(':')[0],gp=gp.split(':')[1])
    st.query_params.update(params)
    st.session_state["_query_aplicada"] = tuple(st.query_params.get(key) for key in ("temporada", "gp", "painel", "tela", "aba", "documento", "lang"))


def selecionar_destino_gp(temporada, rodada, tela, aba=None):
    """Follow a GP shortcut through the existing session, without a new document."""
    gp = "{}:{}".format(temporada, rodada)
    st.session_state.update(tela=tela, temporada=temporada, gp=gp, _gp_context=gp)
    if aba:
        st.query_params["aba"] = aba
    else:
        st.query_params.pop("aba", None)
    sincronizar_navegacao()


def selecionar_gp_busca(valor):
    """Callback nativo: aplicado antes de o seletor lateral ser reconstruído."""
    st.session_state["gp"] = valor
    st.session_state["temporada"] = int(valor.split(":")[0])
    st.session_state["_query_gp_pendente"] = valor
    st.session_state["tela"] = "Corridas"
    st.query_params.update(temporada=valor.split(":")[0], gp=valor.split(":")[1])
    sincronizar_navegacao()


def selecionar_destino_menu(key):
    from pitwall.dashboard.navigation import ROUTES
    route = ROUTES.get(key)
    if route is None:
        return
    _, _, screen, values = route
    st.session_state['tela'] = screen
    sincronizar_navegacao()
    for field in ('aba', 'visao', 'secao'):
        st.query_params.pop(field, None)
    st.query_params.update(values)
    if screen == 'Pilotos':
        st.session_state['pilot_view'] = {'perfil': 'Perfil individual', 'duelo': 'Duelo'}[values['visao']]
    st.session_state['_query_aplicada'] = None


def renderizar_topo(pacote, corrida=None, participantes=None, slot=None):
    # Native search is placed in the single common header, not a second toolbar.
    # A DeltaGenerator belongs to one render/session; never share it in a global.
    if slot is None:
        slot = st.container()
    with slot:
        with st.container(key='topbar'):
            with st.popover("Buscar", key="global-search", width="stretch", help="Buscar corrida, piloto ou circuito…"):
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
                    from pitwall.dashboard.navigation import search as search_navigation
                    matches = search_navigation(consulta, language()) + search(raiz_artefatos(), consulta, language(),year=st.session_state.get("temporada"),round_=int(st.session_state.get("_gp_context",st.session_state.get("gp","0:0")).split(":")[-1]))
                    if not (raiz_artefatos() / "frontend_assets/pilotos_condicoes.json").is_file() and participantes:
                        identities = [{"Piloto": nome_piloto(pacote, p), "Equipe": nome_equipe(pacote, p)} for p in participantes if consulta in nome_piloto(pacote, p).casefold()]
                        if identities:
                            st.dataframe(pd.DataFrame(identities), hide_index=True, width="stretch")
                    all_results = st.checkbox("Mostrar todos os resultados", key="search_all") if len(matches) > 12 else True
                    for result in (matches if all_results else matches[:12]):
                        if result['kind'] == 'navigation':
                            st.button(result['label'], key='busca_destino_' + result['value'],
                                      on_click=selecionar_destino_menu, args=(result['value'],), width='stretch')
                        elif result["kind"] == "gp":
                            st.button(result["label"], key="busca_gp_" + result["value"],
                                      on_click=selecionar_gp_busca, args=(result["value"],), width="stretch")
                        else:
                            st.markdown('<a href="{}" target="_self">{}</a>'.format(escape(result["href"]), escape(result["label"])), unsafe_allow_html=True)
                    if not matches:
                        st.info("Nenhum resultado. Tente outro nome de piloto, pista ou corrida, com pelo menos duas letras.")
                st.checkbox("Abrir notas de fontes",key="mostrar_fontes")


def tela_explorar(pacote, rodada, foco, topbar_slot=None):
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
    renderizar_topo(pacote, corrida, participantes, slot=topbar_slot)
    from pitwall.dashboard.weekend_views import (
        load_status, operational_race_results, render_status, render_strategies,
        render_teams, render_times, render_weather,
    )
    try:
        weekend = load_status(raiz_artefatos(), pacote["temporada"], rodada, corrida["circuito_id"])
    except (ValueError, OSError):
        weekend = None
        st.warning("Não foi possível validar o estado da coleta deste GP.")
    display_status=situacao_corrida(corrida)
    observed_race=next((session for session in (weekend or {}).get('sessoes',[]) if session['nome']=='Race'),{})
    if observed_race.get('encerramento_observado_utc') and observed_race.get('tempos'):
        display_status='Resultado publicado pela OpenF1'
    # The real prediction state and next action precede the complete painting.
    cards_slot = None
    if foco != "Corridas":
        from pitwall.dashboard.fan_views import forecast_context
        with st.container(key='forecast-context'):
            st.markdown(forecast_context(corrida, pacote['temporada']), unsafe_allow_html=True)
            if pacote['temporada'] == 2026 and corrida.get('estado_previsao') == 'indisponivel':
                atalho_gp(pacote, corrida, 'Corridas', 'Consultar sessões e voltas', aba='Tempos', full_width=True)
            else:
                cards_slot = st.container(key='forecast-action')
    from pitwall.dashboard.fan_views import hero
    if foco == "Corridas":
        from pitwall.dashboard.fan_views import GP_CHAPTERS
        chapter = st.query_params.get('aba', 'Visão geral')
        if chapter not in dict(GP_CHAPTERS):
            chapter = 'Visão geral'
        if chapter == 'Visão geral':
            from pitwall.dashboard.postcards import cover
            context_note = translate(display_status)
            if pacote['temporada'] != 2026 or corrida.get('estado_previsao') == 'ensaio_retrospectivo':
                context_note += ' · ' + translate('Estudo retrospectivo com dados históricos.')
            elif corrida.get('estado_previsao') == 'previsao_registrada':
                context_note += ' · ' + translate('Previsão registrada antes da corrida.')
            st.markdown(cover(corrida, pacote['temporada'], note=context_note,
                              assets=para_circuito(pacote.get('catalogo_visual', {}), corrida['circuito_id']),
                              root=raiz_artefatos()), unsafe_allow_html=True)
        else:
            from pitwall.dashboard.fan_views import chapter_header
            st.markdown(chapter_header(dict(GP_CHAPTERS)[chapter]), unsafe_allow_html=True)
    else:
        from pitwall.dashboard.postcards import cover
        st.markdown(cover(corrida, pacote['temporada'], forecast=True,
                          assets=para_circuito(pacote.get('catalogo_visual', {}), corrida['circuito_id']),
                          root=raiz_artefatos()), unsafe_allow_html=True)
    if weekend:
        with st.expander('Atualização e cobertura'):
            render_status(weekend)
    if foco == "Corridas":
        if chapter == "Visão geral":
            with st.container(key='race-summary'):
                podium_column,context_column=st.columns([1.65,1],gap="small")
                with podium_column:
                    renderizar_podio(pacote,corrida,participantes,acervo_gp,weekend)
                with context_column:
                    renderizar_contexto_circuito(pacote,corrida,acervo_gp,mode='details',weekend=weekend,include_media=False)
            with st.container(key="race-summary-actions"):
                has_results = bool(acervo_gp or (observed_race.get('encerramento_observado_utc') and observed_race.get('tempos')))
                actions = st.columns(2 if has_results else 1, gap="small")
                if has_results:
                    with actions[0]:
                        atalho_gp(pacote, corrida, "Corridas", "Ver classificação completa da corrida", aba="Tempos", full_width=True)
                with actions[-1]:
                    atalho_gp(pacote, corrida, "Previsões", "Ver previsões deste GP", full_width=True)
            renderizar_contexto_circuito(pacote,corrida,acervo_gp,mode='media',weekend=weekend)
        elif chapter == 'Tempos':
            renderizar_programacao(corrida)
            if acervo_gp:
                acervo_dashboard_ui.renderizar_tempos(acervo_gp)
            elif not render_times(weekend, operational_race_results(raiz_artefatos(), weekend)):
                renderizar_tempos_sessoes(bloco)
                renderizar_podio(pacote, corrida, participantes)
        elif chapter == 'Estratégias':
            if acervo_gp:
                acervo_dashboard_ui.renderizar_estrategias(acervo_gp)
            elif not render_strategies(weekend):
                st.info("Estratégias indisponíveis no pacote local.")
        elif chapter == 'Clima':
            if acervo_gp:
                acervo_dashboard_ui.renderizar_clima(acervo_gp)
            elif not render_weather(weekend):
                renderizar_condicoes_disponiveis(corrida)
        elif chapter == 'Histórico':
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
                passado['historico']['resultados'] = operational_race_results(raiz_artefatos(), weekend)
                acervo_dashboard_ui.renderizar_historico(passado)
            if pacote["temporada"] == 2026:
                with st.expander("Calendário 2026"):
                    renderizar_calendario_2026(pacote, rodada)
        elif chapter == 'Comparativo de equipes':
            if (acervo_gp or {}).get('equipes'):
                acervo_dashboard_ui.renderizar_equipes(acervo_gp)
            elif not render_teams(weekend, operational_race_results(raiz_artefatos(), weekend)):
                renderizar_desempenho_equipes_indisponivel()
                atalho_gp(pacote, corrida, "Campeonato", "Ver campeonato completo")
        if chapter != 'Visão geral':
            atalho_gp(pacote, corrida, "Previsões", "Ver previsões deste GP")
        with st.expander(
            "Fontes e cobertura", expanded=st.session_state.get("mostrar_fontes", False)
        ):
            renderizar_fontes_circuito(pacote, corrida, acervo_gp)
            if acervo_gp:
                acervo_dashboard_ui.renderizar_fontes(acervo_gp, acervo_asset)
    else:
        renderizar_previsoes(pacote, bloco, participantes, acervo_gp, weekend, cards_slot=cards_slot)
        with st.container(key='forecast-audit'):
            with st.expander("Cobertura e exclusões"):
                st.caption(
                    "Cobertura: {} participantes preparados · {} elegíveis · {} alvos conhecidos depois.".format(
                        corrida["participantes_preparados"],
                        corrida["elegiveis"],
                        corrida["alvos_conhecidos"],
                    )
                )
                if not corrida["avaliavel_ranking"]:
                    motivo = corrida["motivos_nao_avaliavel"].replace("_", " ")
                    if pacote["temporada"] == 2026 and corrida.get("estado_previsao") == "previsao_registrada":
                        from pitwall.dashboard.fan_views import evaluation_reason
                        motivo = translate(evaluation_reason(corrida["motivos_nao_avaliavel"]))
                    st.write(
                        "Ranking não avaliável: {}.".format(
                            motivo
                        )
                    )
            if any(item["probabilidade_modelo"] is not None for item in participantes):
                with st.expander("Avaliação da previsão"):
                    renderizar_resultados_observados(pacote, corrida, bloco, participantes)
            if not (pacote['temporada'] == 2026 and corrida.get('estado_previsao') == 'indisponivel'):
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
    from pitwall.publishing.documentation import documento_disponivel
    if documento_disponivel(st.query_params.get('documento')):
        renderizar_documentacao_local(st, documento_primeiro=True)
        return
    from pitwall.dashboard.fan_views import hero, process_steps, chapter_header
    section = st.query_params.get('secao')
    if section == 'termos':
        st.markdown(chapter_header('Termos da F1', 'Entenda os termos usados nas análises.'), unsafe_allow_html=True)
        st.markdown("**Stint:** trecho entre trocas de pneus. **DNS:** não largou. **DSQ:** desclassificado. **Taxa de pódios:** pódios divididos pelas largadas.")
        return
    if section == 'fontes':
        st.markdown(chapter_header('Fontes e limites', 'Origem, cobertura e limites dos dados.'), unsafe_allow_html=True)
        st.markdown("Dados de [Jolpica-F1](https://github.com/jolpica/jolpica-f1), [OpenF1](https://openf1.org/docs/) e [Open-Meteo](https://open-meteo.com/). Consulte as licenças e a cobertura nas fontes de cada GP.")
        st.caption("Jolpica-F1 e OpenF1: CC BY-NC-SA 4.0; clima Open-Meteo: CC BY 4.0. Fontes históricas podem ter revisões posteriores.")
        st.info("Resultados retrospectivos não demonstram desempenho futuro e não são uma previsão ao vivo ou da próxima corrida.")
        renderizar_documentacao_local(st)
        return
    st.markdown(hero("Como funciona","Entenda como os dados viram chances de pódio e conheça os limites do Lab.",image="method"),unsafe_allow_html=True)
    st.markdown(process_steps(st.session_state.get('temporada'), str(st.session_state.get('_gp_context', '')).split(':')[-1]),unsafe_allow_html=True)
    with st.expander("Termos da corrida", expanded=st.query_params.get('secao') == 'termos'):
        st.markdown("**Stint:** trecho entre trocas de pneus. **DNS:** não largou. **DSQ:** desclassificado. **Taxa de pódios:** pódios divididos pelas largadas.")
    with st.expander("Para quem quer ir além",expanded=bool(st.query_params.get("documento")) or st.query_params.get('secao') == 'fontes'):
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
        page_title="Pitwall Lab", layout="wide", initial_sidebar_state="collapsed"
    )
    from pitwall.i18n.controls import initialize, render as render_language

    initialize(st)
    from pitwall.dashboard.journey import sync_host_query
    sync_host_query(st)
    aplicar_estilo()
    st.markdown('<a class="pw-skip-link" href="#pw-main-content">{}</a>'.format(escape(translate('Pular para o conteúdo'))), unsafe_allow_html=True)
    st.markdown('<span id="pw-page-top" tabindex="-1" aria-label="{}"></span>'.format(escape(translate("Topo da página"), quote=True)), unsafe_allow_html=True)
    from pitwall.dashboard.motion import install as install_motion, render as render_motion
    install_motion()
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
    from pitwall.dashboard.journey import masthead, race_identity
    from pitwall.i18n import language
    with st.container(key="journey-header"):
        with st.container(key="journey-brand-row"):
            logo_control,language_control = st.columns([2,1],vertical_alignment="center")
    with st.container(key="journey-navigation"):
        tela = st.radio(
            "Navegação", ("Corridas", "Pilotos", "Campeonato", "Previsões", "Desempenho", "Metodologia"),
            key="tela",on_change=sincronizar_navegacao,label_visibility="collapsed",horizontal=True,
            format_func=lambda value: {"Previsões":"Chances de pódio","Desempenho":"Acertos do Lab","Metodologia":"Como funciona"}.get(value,value),
        )

    with st.container(key="pw-shell"):
        navigation_column, content_column = st.columns([1, 3.7], gap="large")
    with navigation_column:
        sidebar_slot = st.empty()
    with content_column:
        with st.container(key="journey-context-row"):
            with st.container(key="pw-context-" + {"Pilotos": "drivers", "Metodologia": "method", "Desempenho": "accuracy"}.get(tela, "event")):
                year_control,gp_control,tool_control = st.columns([1,5,1.5],vertical_alignment="bottom")
        st.session_state.setdefault("temporada", st.session_state.get("_temporada_anterior_dashboard", 2026 if (raiz_artefatos() / "frontend_assets/pilotos_condicoes.json").is_file() else 2025))

        def manter_temporada():
            st.query_params.pop('cartas', None)
            if st.session_state.get("temporada") not in (2024, 2025, 2026):
                st.session_state["temporada"] = st.session_state.get(
                    "_temporada_anterior_dashboard", 2025
                )

        temporada = year_control.selectbox(
            "Temporada",
            (2024, 2025, 2026),
            index=None,
            key="temporada",
            on_change=manter_temporada,
            label_visibility="visible",
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
                from pitwall.dashboard.weekend_views import current_gp, observed_rounds
                root = raiz_artefatos()
                try:
                    operation_rounds = observed_rounds(root, temporada)
                except (ValueError, OSError, KeyError, TypeError):
                    operation_rounds = set()
                observadas = [
                    item["valor"]
                    for item in opcoes
                    if item["rodada"] in operation_rounds
                    or dados_do_gp_2026(pacote, item["rodada"])["corrida"]["alvos_conhecidos"]
                ]
                active = current_gp(root)
                st.session_state["gp"] = active if active in valores else (observadas[-1] if observadas else valores[0])
            else:
                st.session_state.pop("gp", None)
            st.session_state["_temporada_anterior_dashboard"] = temporada
        descricoes = {
            item["valor"]: "{:02d} — {}".format(item["rodada"], race_identity(item["corrida"], language())[1])
            for item in opcoes
        }
        gp_pendente = st.session_state.pop("_query_gp_pendente", None)
        if gp_pendente in valores:
            st.session_state["gp"] = gp_pendente

        def manter_gp():
            st.query_params.pop('cartas',None)
            if st.session_state.get("gp") not in valores:
                st.session_state["gp"] = valores[0]

        if "gp" not in st.session_state and st.session_state.get("_gp_context") in valores:
            st.session_state["gp"] = st.session_state["_gp_context"]
        if tela in ("Corridas", "Pilotos", "Previsões", "Campeonato", "Desempenho", "Metodologia"):
            gp = gp_control.selectbox(
                "Etapa de referência" if tela == "Campeonato" else "Grande Prêmio",
                valores,
                format_func=lambda valor: descricoes.get(valor, str(valor)),
                key="gp",
                index=None if "gp" in st.session_state else 0,
                on_change=manter_gp,
                label_visibility="visible",
            )
            st.session_state["_gp_context"] = gp
        else:
            gp = st.session_state.get("_gp_context", st.session_state.get("gp", valores[0]))

        if gp not in descricoes:
            # An existing session may still carry the old long option label.
            por_descricao = {"{:02d} — {}".format(item["rodada"], item["corrida"]): item["valor"] for item in opcoes}
            por_descricao.update({descricao: valor for valor, descricao in descricoes.items()})
            gp = por_descricao.get(gp, valores[0])
        rodada = int(gp.split(":", 1)[1])
        # Header selections are the canonical context for links and copied URLs.
        for key,value in (("temporada",str(temporada)),("gp",str(rodada))):
            if st.query_params.get(key) != value:
                st.query_params[key] = value
        st.session_state["_query_aplicada"] = tuple(st.query_params.get(key) for key in
            ("temporada","gp","painel","tela","aba","documento","lang"))
        from pitwall.dashboard.navigation import render as render_navigation
        render_navigation(st, sidebar_slot, temporada, rodada, tela, language(),
                          st.query_params, selecionar_destino_menu)
        with logo_control:
            st.markdown(masthead(language(),temporada,rodada),unsafe_allow_html=True)
        with language_control:
            render_language(st,st.query_params.get("aba") or ("Visão geral" if tela == "Corridas" else None))
        st.markdown('<span id="pw-main-content" tabindex="-1" aria-label="{}"></span>'.format(escape(translate('Conteúdo principal'), quote=True)), unsafe_allow_html=True)
        if tela == "Pilotos":
            from pitwall.dashboard.hall_views import hall_url, render as render_hall
            pilot_view = st.query_params.get("visao")
            if pilot_view in ("hall", "duelo-campeoes"):
                renderizar_topo(pacote, slot=tool_control)
                render_hall(raiz_artefatos(), temporada, rodada, duel=pilot_view == "duelo-campeoes")
                render_motion()
                return
            from pitwall.dashboard.pilot_views import render
            if (st.query_params.get('origem_tela') == 'Previsões'
                    and st.query_params.get('origem_temporada') == str(temporada)
                    and st.query_params.get('origem_gp') == str(rodada)):
                corrida_origem = next((item['corrida'] for item in opcoes if item['rodada'] == rodada), str(rodada))
                retorno = pitwall_ui.link_interno(temporada, rodada, tela='Previsões')
                st.markdown('<a class="fan-back-to-forecast" href="{}" target="_self">{}</a>'.format(
                    escape(retorno, quote=True), escape(translate('Voltar às chances de {} · {}').format(corrida_origem, temporada))
                ), unsafe_allow_html=True)
            st.markdown('<a class="pw-hall-entry" href="{}" target="_self">{}</a>'.format(
                escape(hall_url(temporada, rodada), quote=True), escape(translate("Hall da Fama")),
            ), unsafe_allow_html=True)
            render(raiz_artefatos(), search_renderer=lambda slot: renderizar_topo(
                {"temporada": "2024–2026"}, slot=slot))
            render_motion()
            return
        if tela in ("Corridas", "Previsões"):
            tela_explorar(pacote, rodada, tela, topbar_slot=tool_control)
        elif tela == "Campeonato":
            bloco = dados_do_gp_2026(pacote, rodada) if temporada == 2026 else dados_do_gp(pacote, rodada)
            corrida = corrida_editorial(pacote, bloco["corrida"])
            renderizar_topo(pacote, corrida, slot=tool_control)
            from pitwall.dashboard.team_views import directory_url, link, render as render_team_profile
            if st.query_params.get("painel") == "equipes" and "equipe" in st.query_params:
                render_team_profile(raiz_artefatos(), temporada, rodada)
                render_motion()
                return
            paineis = carregar_paineis(raiz_artefatos(), temporada, rodada, corrida["circuito_id"])
            try:
                arquivo = carregar_acervo_dashboard(raiz_artefatos())
                gp_acervo = acervo_para_gp(arquivo, temporada, rodada, corrida["circuito_id"])
                if gp_acervo:
                    paineis = complementar_paineis(paineis, gp_acervo)
            except AcervoDashboardErro:
                pass
            from pitwall.dashboard.weekend_views import load_status
            try:
                weekend = load_status(raiz_artefatos(), temporada, rodada, corrida["circuito_id"])
            except (ValueError, OSError):
                weekend = None
                st.warning("Não foi possível validar o estado da coleta deste GP.")
            from pitwall.data.standings_state import resolve_standings
            paineis = resolve_standings(paineis, weekend)
            from pitwall.dashboard.fan_views import hero
            st.markdown(hero("Campeonato de equipes" if st.query_params.get("painel") == "equipes" else "Campeonato de pilotos", "Pontuação acumulada e posição na temporada.", image="championship"), unsafe_allow_html=True)
            if st.query_params.get("painel") == "equipes":
                st.markdown(link(translate("Explorar perfis de equipes"), directory_url(temporada, rodada)),
                            unsafe_allow_html=True)
            st.markdown(pitwall_ui.campeonatos(paineis, temporada, rodada=rodada, painel=st.query_params.get('painel')), unsafe_allow_html=True)
        elif tela == "Desempenho":
            renderizar_topo(pacote, slot=tool_control)
            from pitwall.dashboard.fan_views import hero
            st.markdown(hero("Acertos do Lab","Nossas previsões buscam identificar quem tem mais chance de pódio. Veja a comparação com a classificação.",image="performance"),unsafe_allow_html=True)
            tela_desempenho(pacote,show_title=False,root=raiz_artefatos())
        else:
            renderizar_topo(pacote, slot=tool_control)
            tela_como_funciona()
        render_motion()


if __name__ == "__main__":
    executar_app()
