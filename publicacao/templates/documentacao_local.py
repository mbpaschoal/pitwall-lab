"""Documentação allowlistada, renderizada dentro do dashboard offline."""
import re
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


def reescrever_links(texto):
    """Troca somente links relativos por instruções locais e controles allowlistados."""
    def substituir(encontro):
        rotulo, destino = encontro.group(1), encontro.group(2)
        normalizado = destino.lstrip('./')
        if normalizado in _MAPA_CAMINHOS:
            return '{} (documento disponível no seletor offline: {})'.format(rotulo, _MAPA_CAMINHOS[normalizado])
        if normalizado in _MAPA_RELATIVOS:
            return '{} (documento disponível no seletor offline: {})'.format(rotulo, _MAPA_RELATIVOS[normalizado])
        if normalizado.endswith('previsoes_validacao.csv'):
            return '{} (download disponível abaixo)'.format(rotulo)
        if not '://' in destino and not destino.startswith('#'):
            return '{} (artefato de auditoria fora desta demonstração)'.format(rotulo)
        return encontro.group(0)

    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', substituir, texto)


def renderizar_documentacao_local(st):
    st.subheader('Documentação e relatórios offline')
    opcoes = documentos_disponiveis()
    por_id = {item['id']: item['titulo'] for item in opcoes}
    st.markdown('**Documentos disponíveis offline:** {}.'.format(' · '.join(por_id.values())))
    identificador = st.selectbox(
        'Documento para consulta offline',
        list(por_id),
        format_func=lambda valor: por_id[valor],
        key='documentacao-local',
    )
    st.caption('São registros históricos; 2025 já foi avaliado; comandos de treino dos documentos NÃO são funções da distribuição. Links internos são resolvidos por esta allowlist; nenhum arquivo arbitrário é aberto.')
    st.markdown(conteudo_documento(identificador))
    for item in downloads_documento(identificador):
        st.download_button(
            item['rotulo'],
            data=item['dados'],
            file_name=item['nome'],
            mime='text/csv',
            key='download-{}'.format(item['nome']),
        )
