"""Documentação allowlistada, renderizada dentro do dashboard offline."""

import re
from html import escape
from urllib.parse import urlencode
from pathlib import Path
from pitwall.paths import PROJECT_ROOT


RAIZ = PROJECT_ROOT
DOCUMENTOS = (
    ("fontes-atuais", "Fontes e cobertura atuais", "FONTES_E_DADOS.md"),
    ("metodo-v1", "Método do modelo v1", "docs/experimento_modelo_v1.md"),
    (
        "relatorio-2024",
        "Relatório de 2024",
        (
            "docs/relatorio_2024.md"
            if (RAIZ / "docs/relatorio_2024.md").is_file()
            else "reports/modelo_v1/relatorio.md"
        ),
    ),
    ("avaliacao-2025", "Avaliação de 2025", "reports/avaliacao_final_v1/relatorio.md"),
    (
        "plano-avaliacao-2025",
        "Plano da avaliação de 2025",
        "docs/avaliacao_final_v1.md",
    ),
    ("protocolo-temporal", "Protocolo temporal", "docs/protocolo_temporal.md"),
    ("dicionario-variaveis", "Dicionário de variáveis", "docs/dicionario_variaveis.md"),
)
DOWNLOADS = {
    "relatorio-2024": (
        (
            "Baixar previsões de 2024 (CSV)",
            "previsoes_validacao.csv",
            "reports/modelo_v1/previsoes_validacao.csv",
        ),
    ),
}
ENGLISH_DOCUMENTS = {
    "fontes-atuais": "FONTES_E_DADOS.md",
    "metodo-v1": "docs/en/experimento_modelo_v1.md",
    "relatorio-2024": "docs/en/relatorio_2024.md",
    "avaliacao-2025": "docs/en/relatorio_2025.md",
    "plano-avaliacao-2025": "docs/en/avaliacao_final_v1.md",
    "protocolo-temporal": "docs/en/protocolo_temporal.md",
    "dicionario-variaveis": "docs/en/dicionario_variaveis.md",
}


_IDS_POR_TITULO = {titulo: identificador for identificador, titulo, _ in DOCUMENTOS}
_MAPA_DOCUMENTOS = {
    identificador: (titulo, caminho) for identificador, titulo, caminho in DOCUMENTOS
}
_MAPA_CAMINHOS = {caminho: titulo for _, titulo, caminho in DOCUMENTOS}
_MAPA_RELATIVOS = {
    "protocolo_temporal.md": "Protocolo temporal",
    "dicionario_variaveis.md": "Dicionário de variáveis",
    "experimento_modelo_v1.md": "Método do modelo v1",
    "avaliacao_final_v1.md": "Plano da avaliação de 2025",
}


def _arquivo_allowlistado(caminho_relativo):
    permitidos = (
        set(_MAPA_CAMINHOS)
        | set(ENGLISH_DOCUMENTS.values())
        | {item[2] for itens in DOWNLOADS.values() for item in itens}
        | {"publicacao/templates/FONTES_E_DADOS.md"}
    )
    if caminho_relativo not in permitidos:
        raise ValueError(
            "Arquivo fora da allowlist de documentação: {}".format(caminho_relativo)
        )
    caminho = RAIZ / caminho_relativo
    raiz_resolvida = RAIZ.resolve()
    try:
        caminho.resolve().relative_to(raiz_resolvida)
    except ValueError:
        raise ValueError("Documento local fora da raiz: {}".format(caminho_relativo))
    ancestral = RAIZ
    for parte in Path(caminho_relativo).parts[:-1]:
        ancestral = ancestral / parte
        if ancestral.is_symlink():
            try:
                ancestral.resolve().relative_to(raiz_resolvida)
            except ValueError:
                raise ValueError(
                    "Documento local fora da raiz: {}".format(caminho_relativo)
                )
    if caminho.is_symlink() or not caminho.is_file():
        raise ValueError("Documento local indisponível: {}".format(caminho_relativo))
    return caminho


def documentos_disponiveis():
    return [
        {"id": identificador, "titulo": titulo,
         "caminho": _caminho_fontes_atuais() if identificador == "fontes-atuais" else caminho}
        for identificador, titulo, caminho in DOCUMENTOS
    ]


def documento_disponivel(identificador):
    """Validate a document identity, never a user-supplied filesystem path."""
    return identificador in _MAPA_DOCUMENTOS


def _caminho_fontes_atuais():
    # The portable package already includes this bilingual source document.
    if (RAIZ / "FONTES_E_DADOS.md").is_file():
        return "FONTES_E_DADOS.md"
    return "publicacao/templates/FONTES_E_DADOS.md"


def conteudo_documento(identificador, temporada=None, rodada=None):
    try:
        _, caminho = _MAPA_DOCUMENTOS[identificador]
    except KeyError:
        raise ValueError("Documento fora da allowlist: {}".format(identificador))
    from pitwall.i18n import language

    if identificador == "fontes-atuais":
        texto = _arquivo_allowlistado(_caminho_fontes_atuais()).read_text(encoding="utf-8")
        if language() == "en":
            corpo = texto.split("## English", 1)[1].split("\n## ", 1)[0].strip()
            return reescrever_links("# Current sources and coverage\n\n" + corpo, temporada, rodada)
        corpo = texto.split("## Português", 1)[1].split("## English", 1)[0].strip()
        return reescrever_links("# Fontes e cobertura atuais\n\n" + corpo, temporada, rodada)
    if language() == "en":
        caminho = ENGLISH_DOCUMENTS[identificador]
    return reescrever_links(_arquivo_allowlistado(caminho).read_text(encoding="utf-8"), temporada, rodada)


def downloads_documento(identificador):
    itens = []
    for rotulo, nome, caminho in DOWNLOADS.get(identificador, ()):
        itens.append(
            {
                "rotulo": rotulo,
                "nome": nome,
                "dados": _arquivo_allowlistado(caminho).read_bytes(),
            }
        )
    return itens


def _contexto_gp(temporada, rodada):
    try:
        ano, gp = int(str(temporada)), int(str(rodada))
    except (TypeError, ValueError):
        return {}
    return {"temporada": ano, "gp": gp} if ano in (2024, 2025, 2026) and 1 <= gp <= 24 else {}


def url_documento(identificador, download=False, idioma=None, temporada=None, rodada=None):
    if identificador not in _MAPA_DOCUMENTOS:
        raise ValueError("Documento fora da allowlist: {}".format(identificador))
    parametros = {"tela": "Metodologia", "documento": identificador}
    parametros.update(_contexto_gp(temporada, rodada))
    from pitwall.i18n import language

    selected_language = idioma or language()
    if selected_language == "en" or idioma:
        parametros["lang"] = selected_language
    if download:
        parametros["download"] = "csv"
    return "/?" + urlencode(parametros)


def reescrever_links(texto, temporada=None, rodada=None):
    """Mantém referências allowlistadas navegáveis; não abre caminhos arbitrários."""

    def substituir(encontro):
        rotulo, destino = encontro.group(1), encontro.group(2)
        normalizado = destino.lstrip("./")
        titulo = _MAPA_CAMINHOS.get(normalizado) or _MAPA_RELATIVOS.get(normalizado)
        if titulo:
            return (
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(
                    escape(
                        url_documento(
                            _IDS_POR_TITULO[titulo],
                            idioma="pt" if rotulo == "Português" else None,
                            temporada=temporada, rodada=rodada,
                        ),
                        quote=True,
                    ),
                    escape(rotulo),
                )
            )
        if normalizado.endswith("previsoes_validacao.csv"):
            return (
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(
                    escape(url_documento("relatorio-2024", download=True, temporada=temporada, rodada=rodada), quote=True),
                    escape(rotulo),
                )
            )
        if destino.startswith(("https://", "http://", "#")):
            return encontro.group(0)
        from pitwall.i18n import translate
        return translate("{} (artefato de auditoria fora desta demonstração)").format(rotulo)

    return re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", substituir, texto)


def versao_interface():
    manifesto = RAIZ / "MANIFESTO.json"
    if not manifesto.is_file():
        return "ambiente local"
    import json

    build = json.loads(manifesto.read_text(encoding="utf8"))[
        "apresentacao_build_sha256"
    ]
    if len(build) != 64 or any(c not in "0123456789abcdef" for c in build):
        raise ValueError("Identificador de apresentação inválido no manifesto")
    return build


def _rotulo_documento(identificador, titulo):
    if identificador == "protocolo-temporal":
        return "Protocolo histórico (etapa 3)"
    return titulo


def _renderizar_indice_documentos(st):
    st.markdown('<div id="documentacao"></div>', unsafe_allow_html=True)
    st.subheader("Documentação e relatórios")
    st.caption("Versão da interface: {}".format(versao_interface()))
    por_id = {item["id"]: item["titulo"] for item in documentos_disponiveis()}
    links = [
        '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(
            escape(url_documento(identificador, temporada=st.query_params.get("temporada"), rodada=st.query_params.get("gp")), quote=True),
            escape(_rotulo_documento(identificador, titulo))
        )
        for identificador, titulo in por_id.items()
    ]
    st.markdown(
        '<nav aria-label="Documentação">{}</nav>'.format(" · ".join(links)),
        unsafe_allow_html=True,
    )
    return por_id


def _renderizar_documento(st, identificador):
    if identificador == "fontes-atuais":
        st.caption("Fontes e limites do produto atual. Dados descritivos não alteram as previsões registradas.")
    else:
        st.caption("Documento histórico preservado. O estado descrito pertence à etapa original; comandos não são executados pelo aplicativo.")
    downloads = downloads_documento(identificador)
    if downloads:
        st.markdown('<div id="download-documento"></div>', unsafe_allow_html=True)
    for item in downloads:
        st.download_button(
            item["rotulo"],
            data=item["dados"],
            file_name=item["nome"],
            mime="text/csv",
            key="download-{}".format(item["nome"]),
        )
    st.markdown(conteudo_documento(identificador, temporada=st.query_params.get("temporada"), rodada=st.query_params.get("gp")), unsafe_allow_html=True)


def renderizar_documentacao_local(st, documento_primeiro=False):
    """Render a requested document first without repeating the introduction."""
    identificador = st.query_params.get("documento")
    if documento_primeiro and documento_disponivel(identificador):
        from pitwall.i18n import language
        retorno = dict(tela="Metodologia", lang=language(),
                       **_contexto_gp(st.query_params.get("temporada"), st.query_params.get("gp")))

        def voltar_explicacao():
            st.session_state["tela"] = "Metodologia"
            st.query_params.from_dict(retorno)

        st.button("Voltar à explicação do Lab", key="fan-document-return",
                  on_click=voltar_explicacao)
        _renderizar_documento(st, identificador)
        with st.expander("Outros documentos e identificação da versão"):
            _renderizar_indice_documentos(st)
        return
    por_id = _renderizar_indice_documentos(st)
    if identificador in por_id:
        _renderizar_documento(st, identificador)
