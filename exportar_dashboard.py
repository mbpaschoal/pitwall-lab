"""Exporta uma demonstração mínima e reproduzível do dashboard Pitwall Lab."""
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path



COMMIT_BASE_PADRAO = '05eec0b70b24abf9a68dae45aac36730eefb5bc5'
FONTES_CIENTIFICAS = (
    'reports/modelo_v1/previsoes_validacao.csv',
    'reports/modelo_v1/avaliacao_corridas.csv',
    'reports/modelo_v1/metricas.json',
    'reports/modelo_v1/calibracao.csv',
    'reports/avaliacao_final_v1/previsoes_pre_corrida.csv',
    'reports/avaliacao_final_v1/avaliacao_por_piloto.csv',
    'reports/avaliacao_final_v1/avaliacao_corridas.csv',
    'reports/avaliacao_final_v1/metricas.json',
    'reports/avaliacao_final_v1/calibracao.csv',
)
DOCUMENTOS_COPIADOS = (
    'docs/experimento_modelo_v1.md',
    'docs/avaliacao_final_v1.md',
    'docs/protocolo_temporal.md',
    'docs/dicionario_variaveis.md',
    'reports/avaliacao_final_v1/relatorio.md',
)
FONTES_COPIADAS = (
    'app.py',
    'dashboard_dados.py',
    'tests/test_dashboard_app.py',
    'tests/test_dashboard_dados.py',
    'reports/dashboard_v1/desempenho_desktop.png',
    'reports/modelo_v1/relatorio.md',
) + FONTES_CIENTIFICAS + DOCUMENTOS_COPIADOS
TEMPLATES = (
    'publicacao/templates/README_PUBLICO.md.tpl',
    'publicacao/templates/FONTES_E_DADOS.md',
    'publicacao/templates/LICENCA_CODIGO.md',
    'publicacao/templates/GUIA_HOSPEDAGEM.md',
    'publicacao/templates/config.toml',
    'publicacao/templates/requirements.txt',
    'publicacao/templates/.python-version',
    'publicacao/templates/.gitignore',
    'publicacao/templates/documentacao_local.py',
    'publicacao/templates/test_distribuicao.py',
)


def _sha256(conteudo):
    return hashlib.sha256(conteudo).hexdigest()


def _contem(raiz, caminho):
    try:
        caminho.relative_to(raiz)
        return True
    except ValueError:
        return False


def _caminho_absoluto_sem_diretorio_pai(caminho, rotulo):
    caminho = Path(caminho).expanduser()
    if '..' in caminho.parts:
        raise ValueError('{} não pode conter diretório-pai; use um caminho canônico'.format(rotulo))
    return caminho.absolute()


def _validar_commit(commit):
    if len(commit) != 40 or any(caractere not in '0123456789abcdef' for caractere in commit):
        raise ValueError('commit de origem inválido')


def _recusar_symlink_no_caminho(caminho, rotulo, limite=None):
    atual = caminho.absolute()
    limite = limite.absolute() if limite is not None else None
    while True:
        if atual.is_symlink():
            raise ValueError('{} não pode usar symlink: {}'.format(rotulo, atual))
        if limite is not None and atual == limite:
            return
        if atual == atual.parent:
            return
        atual = atual.parent


def _ler_arquivo_regular(raiz, relativo):
    caminho = raiz / relativo
    if not _contem(raiz, caminho):
        raise ValueError('caminho de fonte fora da raiz: {}'.format(relativo))
    _recusar_symlink_no_caminho(caminho, 'fonte', raiz)
    if caminho.is_symlink() or not caminho.is_file():
        raise ValueError('fonte ausente, inválida ou symlink: {}'.format(relativo))
    return caminho.read_bytes()


def _git_show(raiz, commit, relativo):
    resultado = subprocess.run(
        ['git', '-C', str(raiz), 'show', '{}:{}'.format(commit, relativo)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if resultado.returncode:
        raise ValueError('não foi possível ler {} no commit de origem'.format(relativo))
    return resultado.stdout


def _data_do_commit(raiz, commit):
    resultado = subprocess.run(
        ['git', '-C', str(raiz), 'show', '-s', '--format=%cI', commit],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if resultado.returncode:
        raise ValueError('commit de origem indisponível')
    return datetime.fromisoformat(resultado.stdout.strip()).astimezone(timezone.utc).isoformat()


def validar_fontes_no_commit(raiz_projeto, commit_origem=COMMIT_BASE_PADRAO):
    """Confere cada fonte allowlistada contra o objeto Git fixado da etapa 6."""
    _validar_commit(commit_origem)
    raiz = _caminho_absoluto_sem_diretorio_pai(raiz_projeto, 'raiz do projeto')
    _recusar_symlink_no_caminho(raiz, 'raiz do projeto')
    if not (raiz / '.git').exists():
        raise ValueError('a raiz do projeto precisa conter .git para validar a origem')
    conteudos = {}
    for relativo in FONTES_COPIADAS:
        atual = _ler_arquivo_regular(raiz, relativo)
        congelado = _git_show(raiz, commit_origem, relativo)
        if atual != congelado:
            raise ValueError('fonte diverge do commit de origem: {}'.format(relativo))
        conteudos[relativo] = atual
    return conteudos


def _ler_template(raiz, relativo):
    if relativo not in TEMPLATES:
        raise ValueError('template fora da allowlist: {}'.format(relativo))
    return _ler_arquivo_regular(raiz, relativo)


def _adicionar(arquivos, caminho, conteudo, modo, fonte=None, sha_origem=None, nota=None):
    if caminho in arquivos:
        raise ValueError('caminho duplicado no pacote: {}'.format(caminho))
    if caminho.startswith('/') or '..' in Path(caminho).parts:
        raise ValueError('caminho de destino inválido: {}'.format(caminho))
    arquivos[caminho] = {
        'conteudo': conteudo,
        'modo': modo,
        'fonte': fonte,
        'sha256_origem': sha_origem,
        'nota': nota,
    }


def _app_publico(conteudo):
    texto = conteudo.decode('utf-8')
    marcador_importacao = '\n\nRAIZ_PADRAO = Path(__file__).resolve().parent'
    if texto.count(marcador_importacao) != 1:
        raise ValueError('estrutura esperada de imports do app não encontrada')
    texto = texto.replace(
        marcador_importacao,
        '\n\nfrom documentacao_local import renderizar_documentacao_local' + marcador_importacao,
        1,
    )
    bloco_privado = """    st.markdown(
        '[Método](https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/experimento_modelo_v1.md) · '
        '[Relatório de 2024](https://github.com/mbpaschoal/pitwall-lab/blob/main/reports/modelo_v1/relatorio.md) · '
        '[Avaliação de 2025](https://github.com/mbpaschoal/pitwall-lab/blob/main/reports/avaliacao_final_v1/relatorio.md) · '
        '[Repositório](https://github.com/mbpaschoal/pitwall-lab)'
    )"""
    if texto.count(bloco_privado) != 1:
        raise ValueError('bloco privado GitHub esperado não encontrado no app')
    texto = texto.replace(bloco_privado, '    renderizar_documentacao_local(st)', 1)
    marcador_hachura = "        marker={'color': CORES['modelo'], 'pattern': {'shape': padroes, 'fgcolor': CORES['fundo']}},"
    hachura_publica = (
        "        marker={'color': CORES['modelo'], 'pattern': {'shape': padroes, "
        "'fgcolor': CORES['fundo'], 'bgcolor': CORES['modelo'], 'fillmode': 'overlay'}},"
    )
    if texto.count(marcador_hachura) != 1:
        raise ValueError('marcador de hachura esperado no gráfico de probabilidades não encontrado')
    texto = texto.replace(marcador_hachura, hachura_publica, 1)
    return texto.encode('utf-8')


def _teste_app_portavel(conteudo):
    texto = conteudo.decode('utf-8')
    workaround = """# O terminal do agente injeta um site-packages Python 3.14 antes do .venv 3.9.
# AppTest deve usar a cópia compatível de click instalada no ambiente do projeto.
sys.path[:] = [p for p in sys.path if '/.hermes/installs/' not in p]
SITE_LOCAL = str(RAIZ / '.venv/lib/python3.9/site-packages')
if SITE_LOCAL in sys.path:
    sys.path.remove(SITE_LOCAL)
sys.path.insert(0, SITE_LOCAL)
"""
    if texto.count(workaround) != 1:
        raise ValueError('workaround Python 3.9/Hermes esperado não encontrado no teste')
    return texto.replace(workaround, '', 1).encode('utf-8')


def _relatorio_2024_publico(conteudo):
    texto = conteudo.decode('utf-8')
    substituicoes = {
        '[cobertura_treino.csv](cobertura_treino.csv)': 'cobertura_treino.csv (artefato de auditoria fora desta demonstração)',
        '[previsoes_validacao.csv](previsoes_validacao.csv)': '[previsoes_validacao.csv](../reports/modelo_v1/previsoes_validacao.csv)',
        '[Abrir o gráfico SVG de calibração](calibracao.svg)': 'Gráfico SVG de calibração (artefato de auditoria fora desta demonstração)',
        '[coeficientes.csv](coeficientes.csv)': 'coeficientes.csv (artefato de auditoria fora desta demonstração)',
    }
    for original, adaptado in substituicoes.items():
        if texto.count(original) != 1:
            raise ValueError('link esperado não encontrado no relatório de 2024: {}'.format(original))
        texto = texto.replace(original, adaptado, 1)
    sha_origem = _sha256(conteudo)
    cabecalho = (
        '> Nota de adaptação pública: este documento deriva de '
        '`reports/modelo_v1/relatorio.md`; preserva os resultados textuais. '
        'Somente os quatro links locais foram ajustados para a demonstração mínima.\n'
        '> SHA-256 da origem: {}.\n\n'.format(sha_origem)
    )
    return (cabecalho + texto).encode('utf-8')


def _metricas_para_readme(conteudos):
    metricas = json.loads(conteudos['reports/avaliacao_final_v1/metricas.json'].decode('utf-8'))
    linhas = csv.DictReader(conteudos['reports/avaliacao_final_v1/avaliacao_corridas.csv'].decode('utf-8').splitlines())
    avaliaveis = [linha for linha in linhas if linha['avaliavel_ranking'] == '1']
    return {
        'casos_2025': metricas['probabilisticas']['linhas_avaliaveis'],
        'gps_2025': metricas['ranking_modelo']['corridas_avaliaveis'],
        'media_modelo_2025': metricas['ranking_modelo']['media_integrantes_corretos'],
        'media_classificacao_2025': metricas['ranking_classificacao']['media_integrantes_corretos'],
        'completos_modelo_2025': metricas['ranking_modelo']['distribuicao_0_1_2_3']['3'],
        'acertos_modelo_2025': sum(int(linha['acertos_modelo']) for linha in avaliaveis),
        'acertos_classificacao_2025': sum(int(linha['acertos_classificacao']) for linha in avaliaveis),
    }


def _lista_templates_com_hashes(raiz):
    itens = [('exportar_dashboard.py', _sha256(_ler_arquivo_regular(raiz, 'exportar_dashboard.py')))]
    itens.extend((relativo, _sha256(_ler_template(raiz, relativo))) for relativo in TEMPLATES)
    return [{'caminho': caminho, 'sha256': resumo} for caminho, resumo in itens]


def _montar_arquivos(raiz, conteudos, commit):
    arquivos = {}
    for relativo in FONTES_CIENTIFICAS + DOCUMENTOS_COPIADOS:
        _adicionar(arquivos, relativo, conteudos[relativo], 'copia', relativo, _sha256(conteudos[relativo]))
    _adicionar(
        arquivos,
        'dashboard_dados.py',
        conteudos['dashboard_dados.py'],
        'copia',
        'dashboard_dados.py',
        _sha256(conteudos['dashboard_dados.py']),
    )
    _adicionar(
        arquivos,
        'app.py',
        _app_publico(conteudos['app.py']),
        'gerado',
        'app.py',
        _sha256(conteudos['app.py']),
        'app gerado com transformações estreitas do bloco privado GitHub e da apresentação das hachuras no gráfico de probabilidades',
    )
    _adicionar(
        arquivos,
        'tests/test_dashboard_app.py',
        _teste_app_portavel(conteudos['tests/test_dashboard_app.py']),
        'gerado',
        'tests/test_dashboard_app.py',
        _sha256(conteudos['tests/test_dashboard_app.py']),
        'cópia com remoção exclusiva do workaround Python 3.9/Hermes',
    )
    _adicionar(
        arquivos,
        'tests/test_dashboard_dados.py',
        conteudos['tests/test_dashboard_dados.py'],
        'copia',
        'tests/test_dashboard_dados.py',
        _sha256(conteudos['tests/test_dashboard_dados.py']),
    )
    _adicionar(
        arquivos,
        'reports/dashboard_v1/desempenho_desktop.png',
        conteudos['reports/dashboard_v1/desempenho_desktop.png'],
        'copia',
        'reports/dashboard_v1/desempenho_desktop.png',
        _sha256(conteudos['reports/dashboard_v1/desempenho_desktop.png']),
    )
    _adicionar(
        arquivos,
        'docs/relatorio_2024.md',
        _relatorio_2024_publico(conteudos['reports/modelo_v1/relatorio.md']),
        'adaptado_documentacao',
        'reports/modelo_v1/relatorio.md',
        _sha256(conteudos['reports/modelo_v1/relatorio.md']),
        'links locais ajustados; resultados textuais preservados',
    )

    metricas = _metricas_para_readme(conteudos)
    template_readme = _ler_template(raiz, 'publicacao/templates/README_PUBLICO.md.tpl')
    _adicionar(
        arquivos,
        'README.md',
        template_readme.decode('utf-8').format(**metricas).encode('utf-8'),
        'gerado',
        'publicacao/templates/README_PUBLICO.md.tpl',
        _sha256(template_readme),
    )
    for origem, destino in (
        ('publicacao/templates/FONTES_E_DADOS.md', 'FONTES_E_DADOS.md'),
        ('publicacao/templates/LICENCA_CODIGO.md', 'LICENCA_CODIGO.md'),
        ('publicacao/templates/GUIA_HOSPEDAGEM.md', 'GUIA_HOSPEDAGEM.md'),
        ('publicacao/templates/documentacao_local.py', 'documentacao_local.py'),
        ('publicacao/templates/test_distribuicao.py', 'tests/test_distribuicao.py'),
        ('publicacao/templates/requirements.txt', 'requirements.txt'),
        ('publicacao/templates/.python-version', '.python-version'),
        ('publicacao/templates/.gitignore', '.gitignore'),
        ('publicacao/templates/config.toml', '.streamlit/config.toml'),
    ):
        conteudo = _ler_template(raiz, origem)
        _adicionar(arquivos, destino, conteudo, 'gerado', origem, _sha256(conteudo))
    return arquivos


def _manifesto(arquivos, raiz, commit):
    registros = []
    for caminho in sorted(arquivos):
        item = arquivos[caminho]
        registro = {
            'caminho': caminho,
            'modo': item['modo'],
            'fonte': item['fonte'],
            'sha256_origem': item['sha256_origem'],
            'sha256_destino': _sha256(item['conteudo']),
        }
        if item['nota']:
            registro['nota'] = item['nota']
        registros.append(registro)
    return {
        'formato': 'pitwall-dashboard-publicacao-v1',
        'commit_origem': commit,
        'data_referencia_reprodutivel_utc': _data_do_commit(raiz, commit),
        'fontes_cientificas': list(FONTES_CIENTIFICAS),
        'arquivos': registros,
        'origens_novas_fora_do_commit_base': _lista_templates_com_hashes(raiz),
        'nota_reprodutibilidade': (
            'Não registra relógio de execução: a mesma receita, templates e commit de origem '
            'produzem os mesmos bytes. O próprio MANIFESTO.json não lista nem contém seu hash.'
        ),
    }


def _arvore(raiz):
    if raiz.is_symlink() or not raiz.is_dir():
        raise ValueError('destino inválido ou symlink')
    resultado = {}
    for caminho in raiz.rglob('*'):
        if caminho.is_symlink():
            raise ValueError('destino contém symlink: {}'.format(caminho))
        if caminho.is_file():
            resultado[caminho.relative_to(raiz).as_posix()] = caminho.read_bytes()
    return resultado


def _ancestral_com_mesma_identidade(caminho, referencia):
    """Retorna o ancestral existente de caminho que é o mesmo diretório físico."""
    try:
        identidade_referencia = referencia.stat()
    except OSError:
        return None
    atual = caminho
    while True:
        try:
            if os.path.samestat(atual.stat(), identidade_referencia):
                return atual
        except OSError:
            pass
        if atual == atual.parent:
            return None
        atual = atual.parent


def _validar_destino(raiz, destino):
    raiz = _caminho_absoluto_sem_diretorio_pai(raiz, 'raiz do projeto')
    destino = _caminho_absoluto_sem_diretorio_pai(destino, 'destino')
    raiz_temporaria = Path(tempfile.gettempdir()).absolute()
    limite_symlink = raiz_temporaria if _contem(raiz_temporaria, destino) else None
    _recusar_symlink_no_caminho(destino, 'destino', limite_symlink)
    if destino == raiz:
        raise ValueError('destino não pode ser a raiz do projeto')
    if any(parte in {'.venv', '.env'} for parte in destino.parts):
        raise ValueError('destino não pode apontar para ambiente virtual ou segredo')
    ancestral_raiz = _ancestral_com_mesma_identidade(destino, raiz)
    if ancestral_raiz is not None:
        permitido = raiz / 'distribuicao' / 'pitwall-dashboard'
        if destino != permitido:
            raise ValueError('destino dentro do projeto só pode ser distribuicao/pitwall-dashboard')
        _recusar_symlink_no_caminho(destino, 'destino', raiz)
    return destino


def _escrever_arquivos(raiz, arquivos):
    for relativo, item in arquivos.items():
        caminho = raiz / relativo
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(item['conteudo'])


def exportar(raiz_projeto=None, destino=None, commit_origem=COMMIT_BASE_PADRAO):
    """Gera o pacote ou aceita somente uma cópia pré-existente byte idêntica."""
    raiz = _caminho_absoluto_sem_diretorio_pai(
        raiz_projeto or Path(__file__).resolve().parent,
        'raiz do projeto',
    )
    destino = _validar_destino(raiz, destino or (raiz / 'distribuicao' / 'pitwall-dashboard'))
    conteudos = validar_fontes_no_commit(raiz, commit_origem)
    arquivos = _montar_arquivos(raiz, conteudos, commit_origem)

    caminhos_publicados = sorted(list(arquivos) + ['ARQUIVOS_PUBLICACAO.txt', 'MANIFESTO.json'])
    lista = ('\n'.join(caminhos_publicados) + '\n').encode('utf-8')
    _adicionar(arquivos, 'ARQUIVOS_PUBLICACAO.txt', lista, 'gerado')
    manifesto = _manifesto(arquivos, raiz, commit_origem)
    _adicionar(
        arquivos,
        'MANIFESTO.json',
        (json.dumps(manifesto, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8'),
        'gerado',
        nota='autorreferência excluída da lista de hashes do manifesto',
    )
    esperado = {caminho: item['conteudo'] for caminho, item in arquivos.items()}

    if destino.exists():
        existente = _arvore(destino)
        if existente != esperado:
            raise ValueError('destino não vazio diverge do pacote esperado; nada foi sobrescrito')
        return {'destino': str(destino), 'arquivos': len(esperado), 'idempotente': True}

    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.parent.is_symlink():
        raise ValueError('diretório pai do destino não pode usar symlink: {}'.format(destino.parent))
    temporario = Path(tempfile.mkdtemp(prefix='.pitwall-export-', dir=str(destino.parent)))
    try:
        _escrever_arquivos(temporario, arquivos)
        if _arvore(temporario) != esperado:
            raise RuntimeError('falha ao verificar a exportação temporária')
        os.replace(str(temporario), str(destino))
    except Exception:
        if temporario.exists():
            shutil.rmtree(temporario)
        raise
    return {'destino': str(destino), 'arquivos': len(esperado), 'idempotente': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', help='pasta nova para o pacote exportado')
    parser.add_argument('--commit-origem', default=COMMIT_BASE_PADRAO)
    argumentos = parser.parse_args()
    resultado = exportar(destino=argumentos.destino, commit_origem=argumentos.commit_origem)
    print('Pacote exportado: {destino} ({arquivos} arquivos; idempotente={idempotente})'.format(**resultado))


if __name__ == '__main__':
    main()
