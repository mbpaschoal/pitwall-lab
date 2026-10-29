"""Documentação allowlistada, renderizada dentro do dashboard offline."""
import re
from html import escape
from urllib.parse import urlencode
from pathlib import Path


RAIZ = Path(__file__).resolve().parent
DOCUMENTOS = (
    ('metodo-v1', 'Método do modelo v1', 'docs/experimento_modelo_v1.md'),
    ('relatorio-2024', 'Relatório de 2024', 'docs/relatorio_2024.md'),
    ('avaliacao-2025', 'Avaliação de 2025', 'reports/avaliacao_final_v1/relatorio.md'),
    ('plano-avaliacao-2025', 'Plano da avaliação de 2025', 'docs/avaliacao_final_v1.md'),
    ('protocolo-temporal', 'Protocolo temporal', 'docs/protocolo_temporal.md'),
    ('dicionario-variaveis', 'Dicionário de variáveis', 'docs/dicionario_variaveis.md'),
)
DOWNLOADS = {
    'relatorio-2024': (
        ('Baixar previsões de 2024 (CSV)', 'previsoes_validacao.csv', 'reports/modelo_v1/previsoes_validacao.csv'),
    ),
}
_IDS_POR_TITULO = {titulo: identificador for identificador, titulo, _ in DOCUMENTOS}
_MAPA_DOCUMENTOS = {identificador: (titulo, caminho) for identificador, titulo, caminho in DOCUMENTOS}
_MAPA_CAMINHOS = {caminho: titulo for _, titulo, caminho in DOCUMENTOS}
_MAPA_RELATIVOS = {
    'protocolo_temporal.md': 'Protocolo temporal',
    'dicionario_variaveis.md': 'Dicionário de variáveis',
    'experimento_modelo_v1.md': 'Método do modelo v1',
    'avaliacao_final_v1.md': 'Plano da avaliação de 2025',
}


def _arquivo_allowlistado(caminho_relativo):
    permitidos = set(_MAPA_CAMINHOS) | {item[2] for itens in DOWNLOADS.values() for item in itens}
    if caminho_relativo not in permitidos:
        raise ValueError('Arquivo fora da allowlist de documentação: {}'.format(caminho_relativo))
    caminho = RAIZ / caminho_relativo
    raiz_resolvida = RAIZ.resolve()
    try:
        caminho.resolve().relative_to(raiz_resolvida)
    except ValueError:
        raise ValueError('Documento local fora da raiz: {}'.format(caminho_relativo))
    ancestral = RAIZ
    for parte in Path(caminho_relativo).parts[:-1]:
        ancestral = ancestral / parte
        if ancestral.is_symlink():
            try:
                ancestral.resolve().relative_to(raiz_resolvida)
            except ValueError:
                raise ValueError('Documento local fora da raiz: {}'.format(caminho_relativo))
    if caminho.is_symlink() or not caminho.is_file():
        raise ValueError('Documento local indisponível: {}'.format(caminho_relativo))
    return caminho


def documentos_disponiveis():
    return [
        {'id': identificador, 'titulo': titulo, 'caminho': caminho}
        for identificador, titulo, caminho in DOCUMENTOS
    ]


def conteudo_documento(identificador):
    try:
        _, caminho = _MAPA_DOCUMENTOS[identificador]
    except KeyError:
        raise ValueError('Documento fora da allowlist: {}'.format(identificador))
    return reescrever_links(_arquivo_allowlistado(caminho).read_text(encoding='utf-8'))


def downloads_documento(identificador):
    itens = []
    for rotulo, nome, caminho in DOWNLOADS.get(identificador, ()):
        itens.append({'rotulo': rotulo, 'nome': nome, 'dados': _arquivo_allowlistado(caminho).read_bytes()})
    return itens


def url_documento(identificador, download=False):
    if identificador not in _MAPA_DOCUMENTOS:
        raise ValueError('Documento fora da allowlist: {}'.format(identificador))
    parametros = {'tela': 'Metodologia', 'documento': identificador}
    if download:
        parametros['download'] = 'csv'
    return '/?' + urlencode(parametros)


def reescrever_links(texto):
    """Mantém referências allowlistadas navegáveis; não abre caminhos arbitrários."""
    def substituir(encontro):
        rotulo, destino = encontro.group(1), encontro.group(2)
        normalizado = destino.lstrip('./')
        titulo = _MAPA_CAMINHOS.get(normalizado) or _MAPA_RELATIVOS.get(normalizado)
        if titulo:
            return '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(escape(url_documento(_IDS_POR_TITULO[titulo]), quote=True), escape(rotulo))
        if normalizado.endswith('previsoes_validacao.csv'):
            return '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(escape(url_documento('relatorio-2024', download=True), quote=True), escape(rotulo))
        if destino.startswith(('https://', 'http://', '#')):
            return encontro.group(0)
        return '{} (artefato de auditoria fora desta demonstração)'.format(rotulo)

    return re.sub(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)', substituir, texto)


def renderizar_documentacao_local(st):
    st.markdown('<div id="documentacao"></div>', unsafe_allow_html=True)
    st.subheader('Documentação e relatórios')
    por_id = {item['id']: item['titulo'] for item in documentos_disponiveis()}
    links = ['<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format(escape(url_documento(identificador), quote=True), escape(titulo)) for identificador, titulo in por_id.items()]
    st.markdown('<nav aria-label="Documentação">{}</nav>'.format(' · '.join(links)), unsafe_allow_html=True)
    identificador = st.query_params.get('documento')
    if identificador not in por_id:
        return
    st.caption('Registros históricos do projeto. Comandos nos documentos não são executados pelo aplicativo.')
    downloads = downloads_documento(identificador)
    if downloads:
        st.markdown('<div id="download-documento"></div>', unsafe_allow_html=True)
    for item in downloads:
        st.download_button(item['rotulo'], data=item['dados'], file_name=item['nome'],
                           mime='text/csv', key='download-{}'.format(item['nome']))
    st.markdown(conteudo_documento(identificador), unsafe_allow_html=True)
