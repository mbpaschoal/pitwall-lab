"""Exporta uma demonstração mínima e reproduzível do dashboard Pitwall Lab."""
import argparse
import csv
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import zipfile
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
FONTES_COPIADAS = FONTES_CIENTIFICAS
# Explicit presentation identities, never discovered by walking private folders.
TAROT_DRIVER_IDS = (
    'albon', 'alonso', 'antonelli', 'arvid_lindblad', 'bearman', 'bortoleto',
    'bottas', 'colapinto', 'doohan', 'gasly', 'hadjar', 'hamilton', 'hulkenberg',
    'kevin_magnussen', 'lawson', 'leclerc', 'max_verstappen', 'norris', 'ocon',
    'perez', 'piastri', 'ricciardo', 'russell', 'ryo_hirakawa', 'sainz',
    'sargeant', 'stroll', 'tsunoda', 'zhou',
)
TAROT_VARIANTS = tuple(
    'dashboard_assets/tarot/variants/{}/pose-{}.png'.format(driver, pose)
    for driver in TAROT_DRIVER_IDS for pose in (0, 1, 2)
)
TAROT_TEAM_PAIRS = (
    ('albon', 'williams'),
    ('alonso', 'aston_martin'),
    ('antonelli', 'mercedes'),
    ('arvid_lindblad', 'rb'),
    ('bearman', 'ferrari'),
    ('bearman', 'haas'),
    ('bortoleto', 'audi'),
    ('bortoleto', 'sauber'),
    ('bottas', 'cadillac'),
    ('bottas', 'sauber'),
    ('colapinto', 'alpine'),
    ('colapinto', 'williams'),
    ('doohan', 'alpine'),
    ('gasly', 'alpine'),
    ('hadjar', 'rb'),
    ('hadjar', 'red_bull'),
    ('hamilton', 'ferrari'),
    ('hamilton', 'mercedes'),
    ('hulkenberg', 'audi'),
    ('hulkenberg', 'haas'),
    ('hulkenberg', 'sauber'),
    ('kevin_magnussen', 'haas'),
    ('lawson', 'rb'),
    ('lawson', 'red_bull'),
    ('leclerc', 'ferrari'),
    ('max_verstappen', 'red_bull'),
    ('norris', 'mclaren'),
    ('ocon', 'alpine'),
    ('ocon', 'haas'),
    ('perez', 'cadillac'),
    ('perez', 'red_bull'),
    ('piastri', 'mclaren'),
    ('ricciardo', 'rb'),
    ('russell', 'mercedes'),
    ('ryo_hirakawa', 'haas'),
    ('sainz', 'ferrari'),
    ('sainz', 'williams'),
    ('sargeant', 'williams'),
    ('stroll', 'aston_martin'),
    ('tsunoda', 'rb'),
    ('tsunoda', 'red_bull'),
    ('zhou', 'sauber'),
)
TAROT_TEAM_VARIANTS = tuple(
    'dashboard_assets/tarot/teams/{}/{}/pose-{}.png'.format(team, driver, pose)
    for driver, team in TAROT_TEAM_PAIRS for pose in (0, 1, 2)
)
RUNTIME_WORKTREE = (
    'docs/PILOTOS_ATUALIZACAO.md',
    'docs/en/DRIVER_UPDATES.md',
    'pitwall/dashboard/motion.py',
    'frontend_assets/motion.js',
    'pitwall/data/post_race_evaluation.py',
    'frontend_assets/avaliacao_posterior_mexico_2026.json',
    'pitwall/dashboard/media.py',
    'static/pitwall-media/catalog.json',
    'static/pitwall-media/method-9776d0597fe6-1200.webp',
    'static/pitwall-media/method-9776d0597fe6-2400.webp',
    'static/pitwall-media/method-9776d0597fe6-3600.webp',
    'pitwall/dashboard/fan_views.py',
    'pitwall/dashboard/hero_assets.py',
    'pitwall/dashboard/tarot_catalog.py',
    'tests/test_fan_composition.py',
    'tests/test_tarot_catalog.py',
    'tests/test_high_resolution_assets.py',
    'dashboard_assets/fan/ATTRIBUTION.md',
    'dashboard_assets/fan/hero_catalog.json',
    'dashboard_assets/fan/generation.json',
    'dashboard_assets/fan/photos/ricciardo-miami-2024-original.webp',
    'dashboard_assets/fan/photos/piastri-silverstone-2024.jpg',
    'dashboard_assets/fan/photos/hamilton-bahrain-2025.webp',
    'dashboard_assets/fan/photos/verstappen-silverstone-2024.jpg',
    'dashboard_assets/fan/photos/antonelli-cockpit-mercedes.jpg',
    'dashboard_assets/fan/banner-norris.png',
    'dashboard_assets/fan/banner-verstappen.png',
    'dashboard_assets/fan/logos/alpine.svg',
    'dashboard_assets/fan/logos/aston_martin.svg',
    'dashboard_assets/fan/logos/audi.svg',
    'dashboard_assets/fan/logos/cadillac.svg',
    'dashboard_assets/fan/logos/ferrari.svg',
    'dashboard_assets/fan/logos/haas.svg',
    'dashboard_assets/fan/logos/mclaren.svg',
    'dashboard_assets/fan/logos/mclaren-swoosh.svg',
    'dashboard_assets/fan/logos/mercedes.svg',
    'dashboard_assets/fan/logos/rb.svg',
    'dashboard_assets/fan/logos/red_bull.svg',
    'dashboard_assets/fan/logos/williams.svg',
    'dashboard_assets/fan/portraits/albon.png',
    'dashboard_assets/fan/portraits/alonso.png',
    'dashboard_assets/fan/portraits/antonelli.png',
    'dashboard_assets/fan/portraits/arvid_lindblad.png',
    'dashboard_assets/fan/portraits/bearman.png',
    'dashboard_assets/fan/portraits/bortoleto.png',
    'dashboard_assets/fan/portraits/bottas.png',
    'dashboard_assets/fan/portraits/colapinto.png',
    'dashboard_assets/fan/portraits/doohan.png',
    'dashboard_assets/fan/portraits/gasly.png',
    'dashboard_assets/fan/portraits/hadjar.png',
    'dashboard_assets/fan/portraits/hamilton.png',
    'dashboard_assets/fan/portraits/hulkenberg.png',
    'dashboard_assets/fan/portraits/kevin_magnussen.png',
    'dashboard_assets/fan/portraits/lawson.png',
    'dashboard_assets/fan/portraits/leclerc.png',
    'dashboard_assets/fan/portraits/max_verstappen.png',
    'dashboard_assets/fan/portraits/norris.png',
    'dashboard_assets/fan/portraits/ocon.png',
    'dashboard_assets/fan/portraits/perez.png',
    'dashboard_assets/fan/portraits/piastri.png',
    'dashboard_assets/fan/portraits/ricciardo.png',
    'dashboard_assets/fan/portraits/russell.png',
    'dashboard_assets/fan/portraits/ryo_hirakawa.jpg',
    'dashboard_assets/fan/portraits/sainz.png',
    'dashboard_assets/fan/portraits/sargeant.png',
    'dashboard_assets/fan/portraits/stroll.png',
    'dashboard_assets/fan/portraits/tsunoda.png',
    'dashboard_assets/fan/portraits/zhou.png',
    'dashboard_assets/fan/sources.json',

    ".gitattributes",
    'LICENSE', 'VERSION', 'pitwall/version.py', 'CHANGELOG.md', 'CHANGELOG.en.md',
    'pitwall/__init__.py',
    'pitwall/paths.py',
    'pitwall/dashboard/__init__.py',
    'pitwall/data/__init__.py',
    'pitwall/publishing/__init__.py',
    'pitwall/i18n/__init__.py',
    'pitwall/i18n/streamlit.py',
    'pitwall/i18n/controls.py',
    'pitwall/i18n/en.json',
    'docs/en/avaliacao_final_v1.md',
    'docs/en/dicionario_variaveis.md',
    'docs/en/experimento_modelo_v1.md',
    'docs/en/protocolo_temporal.md',
    'docs/en/relatorio_2024.md',
    'docs/en/relatorio_2025.md',

    'pitwall/dashboard/app.py',
    'pitwall/publishing/documentation.py',
    'pitwall/data/dashboard.py',
    'pitwall/data/race_weekend.py',
    'pitwall/data/archive.py',
    'pitwall/data/standings_state.py',
    'pitwall/data/tyre_age.py',
    'pitwall/dashboard/archive_views.py',
    'pitwall/dashboard/pilot_views.py',
    'docs/galeria-cartas.html',
    'docs/JORNADA_DO_FA.md', 'docs/en/FAN_JOURNEY.md', 'docs/OPERACAO_FIM_SEMANA.md', 'docs/en/WEEKEND_OPERATION.md',
    'docs/PREPARACAO_SAO_PAULO.md', 'docs/en/SAO_PAULO_PREPARATION.md',
    'docs/REVISAO_030.md', 'docs/en/REVIEW_030.md',
    'docs/images/pitwall-pilotos.png', 'docs/images/pitwall-pilotos-en.png',
    'pitwall/dashboard/tokens.py',
    'dashboard_assets/tarot/catalog.json',
    'tests/test_fan_journey.py', 'tests/test_weekend_ui.py', 'pitwall/dashboard/journey.py', 'pitwall/dashboard/tarot.py', 'dashboard_assets/tarot/verstappen.png', 'dashboard_assets/tarot/hamilton.png', 'dashboard_assets/tarot/russell.png', 'dashboard_assets/tarot/ATTRIBUTION.md', 'frontend_assets/journey.css', 'pitwall/dashboard/weekend_views.py', 'pitwall/research/prospective_evaluation.py',
    'frontend_assets/operacao_fim_semana.json',
    'pitwall/dashboard/model_views.py', 'pitwall/dashboard/favorites.py',
    'pitwall/dashboard/search.py', 'pitwall/dashboard/share_cards.py',
    'pitwall/research/driver_duel.py', 'frontend_assets/favorite/index.html',
    'tests/test_fan_exploration.py', 'tests/test_review_regressions.py',
    'pitwall/data/driver_conditions.py',
    'pitwall/data/driver_updates.py',
    'pitwall/data/driver_archive_projection.py',
    'pitwall/research/__init__.py',
    'pitwall/research/driver_conditions.py',
    'frontend_assets/pilotos_condicoes.json',
    'frontend_assets/pilotos_condicoes_operacao.json',
    'reports/pilotos_condicoes_20261029/README.md',
    'reports/pilotos_condicoes_20261029/README.en.md',
    'reports/pilotos_condicoes_20261029/circuitos_revisados.csv',
    'reports/pilotos_condicoes_20261029/consolidado_v1/gate_dados.json',
    'reports/pilotos_condicoes_20261029/consolidado_v1/pendencias.csv',
    'tests/test_driver_conditions.py', 'tests/test_driver_projection.py', 'tests/test_pilot_views.py',
    'pitwall/data/circuit_history.py',
    'pitwall/dashboard/components.py',
    'pitwall/data/editorial_panels.py',
    'pitwall/data/editorial.py',
    'pitwall/data/visual_catalog.py',

    'app.py', 'documentacao_local.py', 'dashboard_dados.py', 'race_weekend_dados.py',
    'acervo_dashboard_dados.py', 'acervo_dashboard_ui.py', 'historico_circuito.py',
    'frontend_assets/acervo_dashboard.json',
    'frontend_assets/complemento_idade_pneus_v1.json',
    'pitwall/data/complementary_sources.py',
    'pitwall/data/identity_revision.py',
    'frontend_assets/revisao_identidade_pilotos_v1.json',
    'frontend_assets/complemento_fontes_v1.json',
    'pitwall_ui.py', 'pitwall_ui_dados.py', 'frontend_assets/pitwall.css',
    'frontend_assets/paineis_editoriais.json',
    'frontend_assets/race_weekend.json', 'dashboard_assets/fonts/abrilfatface.ttf',
    'dashboard_assets/fonts/lato.ttf', 'dashboard_assets/fonts/lato-bold.ttf',
    'dashboard_assets/fonts/abrilfatface-OFL.txt', 'dashboard_assets/fonts/lato-OFL.txt',
    'dashboard_assets/circuit/ATRIBUICOES.md', 'tests/test_dashboard_app.py',
    'tests/test_dashboard_dados.py', 'tests/test_interface_editorial.py',
)
TEMPLATES = (
    'publicacao/templates/README_PUBLICO.md.tpl',
    'publicacao/templates/README_PUBLICO.en.md.tpl',
    'publicacao/templates/FONTES_E_DADOS.md',
    'publicacao/templates/LICENCA_CODIGO.md',
    'publicacao/templates/GUIA_HOSPEDAGEM.md',
    'publicacao/templates/config.toml',
    'publicacao/templates/requirements.txt',
    'publicacao/templates/.python-version',
    'publicacao/templates/.gitignore',
    'publicacao/templates/test_distribuicao.py',
    'publicacao/templates/test_acervo_publico.py',
    'publicacao/templates/test_complemento_idade_publico.py',
    'publicacao/templates/test_pneus_apresentacao.py',
    'publicacao/templates/test_avaliacao_posterior_publico.py',
    'publicacao/templates/test_standings_publication.py',
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
    raiz = Path(raiz).resolve()
    relativo = Path(relativo)
    if relativo.is_absolute() or '..' in relativo.parts:
        raise ValueError('caminho de fonte fora da raiz: {}'.format(relativo))
    caminho = raiz / relativo
    if not _contem(raiz, caminho.resolve(strict=False)):
        raise ValueError('caminho de fonte fora da raiz: {}'.format(relativo))
    _recusar_symlink_no_caminho(caminho, 'fonte', raiz)
    if caminho.is_symlink() or not caminho.is_file():
        raise ValueError('fonte ausente, inválida ou symlink: {}'.format(relativo))
    return caminho.read_bytes()


def _ler_catalogo_visual(raiz):
    relativo = 'dashboard_assets/circuit/catalogo_visual.json'
    try:
        catalogo = json.loads(_ler_arquivo_regular(raiz, relativo).decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ValueError('catálogo visual inválido') from erro
    if not isinstance(catalogo, dict):
        raise ValueError('catálogo visual inválido')
    circuitos = catalogo.get('circuitos')
    if catalogo.get('versao') != 1 or not isinstance(circuitos, dict) or len(circuitos) != 26:
        raise ValueError('catálogo visual sem a cobertura esperada de 26 circuitos')
    for circuito, ativos in circuitos.items():
        if not isinstance(circuito, str) or not isinstance(ativos, dict):
            raise ValueError('catálogo visual com circuito inválido')
        for tipo in ('foto', 'mapa'):
            ativo = ativos.get(tipo)
            if not isinstance(ativo, dict) or not isinstance(ativo.get('caminho'), str):
                raise ValueError('catálogo visual com ativo inválido')
            conteudo = _ler_arquivo_regular(raiz, ativo['caminho'])
            if _sha256(conteudo) != ativo.get('sha256'):
                raise ValueError('hash divergente no catálogo visual: {}'.format(ativo['caminho']))
    return catalogo


def runtime_worktree(raiz):
    """Allowlist de runtime: núcleo explícito + ativos declarados no catálogo validado."""
    arquivos = list(RUNTIME_WORKTREE) + list(TAROT_VARIANTS) + list(TAROT_TEAM_VARIANTS) + [
        'contexto_editorial.py', 'catalogo_visual.py', 'registro_emissoes.py',
        'frontend_assets/contexto_editorial.json', 'dashboard_assets/circuit/catalogo_visual.json',
    ]
    catalogo = _ler_catalogo_visual(raiz)
    for ativos in catalogo['circuitos'].values():
        arquivos.extend((ativos['foto']['caminho'], ativos['mapa']['caminho']))
        derivative = 'dashboard_assets/presentation/' + Path(ativos['foto']['caminho']).stem + '.webp'
        if (Path(raiz) / derivative).is_file():
            arquivos.append(derivative)
    if len(arquivos) != len(set(arquivos)):
        raise ValueError('allowlist de runtime contém caminho duplicado')
    return tuple(arquivos)


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
    for relativo in FONTES_CIENTIFICAS:
        _adicionar(arquivos, relativo, conteudos[relativo], 'copia', relativo, _sha256(conteudos[relativo]))
    for relativo in DOCUMENTOS_COPIADOS:
        conteudo = _ler_arquivo_regular(raiz, relativo)
        _adicionar(arquivos, relativo, conteudo, 'copia', relativo, _sha256(conteudo))
    for relativo in runtime_worktree(raiz):
        conteudo = _ler_arquivo_regular(raiz, relativo)
        if relativo in ('CHANGELOG.md', 'CHANGELOG.en.md'):
            conteudo = conteudo.replace(b'(docs/APRENDIZADOS.md)', b'(https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/APRENDIZADOS.md)').replace(b'(docs/en/LEARNING.md)', b'(https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/en/LEARNING.md)')
            modo = 'adaptado_documentacao'
            nota = 'link para o diário publicado; notas da versão preservadas'
        elif relativo == 'docs/en/relatorio_2024.md':
            conteudo = conteudo.replace(b'(../../reports/modelo_v1/relatorio.md)', b'(../relatorio_2024.md)')
            modo = 'adaptado_documentacao'
            nota = 'link PT resolvido dentro do pacote portatil'
        else:
            modo = 'copia'
            nota = None
        _adicionar(arquivos, relativo, conteudo, modo, relativo, _sha256(_ler_arquivo_regular(raiz, relativo)), nota)
    _adicionar(
        arquivos,
        'docs/relatorio_2024.md',
        _relatorio_2024_publico(_ler_arquivo_regular(raiz, 'reports/modelo_v1/relatorio.md')),
        'adaptado_documentacao',
        'reports/modelo_v1/relatorio.md',
        _sha256(_ler_arquivo_regular(raiz, 'reports/modelo_v1/relatorio.md')),
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
    readme_en = _ler_template(raiz, 'publicacao/templates/README_PUBLICO.en.md.tpl')
    _adicionar(arquivos, 'README.en.md', readme_en.decode('utf-8').format(**metricas).encode('utf-8'),
               'gerado', 'publicacao/templates/README_PUBLICO.en.md.tpl', _sha256(readme_en))
    for origem, destino in (
        ('publicacao/templates/FONTES_E_DADOS.md', 'FONTES_E_DADOS.md'),
        ('publicacao/templates/LICENCA_CODIGO.md', 'LICENCA_CODIGO.md'),
        ('publicacao/templates/GUIA_HOSPEDAGEM.md', 'GUIA_HOSPEDAGEM.md'),
        ('publicacao/templates/test_distribuicao.py', 'tests/test_distribuicao.py'),
        ('publicacao/templates/test_acervo_publico.py', 'tests/test_acervo_publico.py'),
        ('publicacao/templates/test_complemento_idade_publico.py', 'tests/test_complemento_idade_publico.py'),
        ('publicacao/templates/test_pneus_apresentacao.py', 'tests/test_pneus_apresentacao.py'),
        ('publicacao/templates/test_avaliacao_posterior_publico.py', 'tests/test_avaliacao_posterior_publico.py'),
        ('publicacao/templates/test_standings_publication.py', 'tests/test_standings_publication.py'),
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
        'formato': 'pitwall-dashboard-publicacao-v2',
        'commit_origem': commit,
        'versao_produto': (raiz / 'VERSION').read_text().strip(),
        'baseline_cientifico_commit': commit,
        'apresentacao_build_sha256': _sha256(json.dumps(
            [(r['caminho'], r['sha256_destino']) for r in registros],
            separators=(',', ':'), ensure_ascii=False).encode('utf8')),
        'data_referencia_reprodutivel_utc': _data_do_commit(raiz, commit),
        'fontes_cientificas': list(FONTES_CIENTIFICAS),
        'arquivos': registros,
        'origens_novas_fora_do_commit_base': _lista_templates_com_hashes(raiz),
        'nota_reprodutibilidade': (
            'Os nove dados científicos são bytes do commit-base; UI, asset e fontes locais são '
            'do working tree e registram hashes de origem e destino. MANIFESTO.json não se lista.'
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


def _ler_zip_regular(caminho):
    """Lê um ZIP existente sem seguir links nem aceitar outros tipos de arquivo."""
    try:
        modo = os.lstat(caminho).st_mode
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(modo):
        raise ValueError('ZIP de destino não pode usar symlink: {}'.format(caminho))
    if not stat.S_ISREG(modo):
        raise ValueError('ZIP de destino não é arquivo regular: {}'.format(caminho))
    try:
        descritor = os.open(str(caminho), os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    except FileNotFoundError:
        return None
    except OSError as erro:
        raise ValueError('ZIP de destino inválido ou symlink: {}'.format(caminho)) from erro
    try:
        if not stat.S_ISREG(os.fstat(descritor).st_mode):
            raise ValueError('ZIP de destino não é arquivo regular: {}'.format(caminho))
        with os.fdopen(descritor, 'rb') as arquivo:
            descritor = None
            return arquivo.read()
    finally:
        if descritor is not None:
            os.close(descritor)


def _preparar_zip_deterministico(destino, esperado):
    """Cria o ZIP privado e recusa previamente qualquer destino não idêntico."""
    caminho = destino.parent / 'pitwall-dashboard.zip'
    _recusar_symlink_no_caminho(caminho, 'ZIP de destino')
    descritor, nome_temporario = tempfile.mkstemp(prefix='.pitwall-dashboard-', suffix='.zip', dir=str(destino.parent))
    os.close(descritor)
    temporario = Path(nome_temporario)
    try:
        with zipfile.ZipFile(temporario, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as arquivo:
            for nome in sorted(esperado):
                info = zipfile.ZipInfo(nome, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                arquivo.writestr(info, esperado[nome])
        existente = _ler_zip_regular(caminho)
        if existente is not None:
            if existente != temporario.read_bytes():
                raise ValueError('ZIP de destino diverge do pacote esperado; nada foi sobrescrito')
            temporario.unlink()
            return None, caminho
        return temporario, caminho
    except Exception:
        if temporario.exists():
            temporario.unlink()
        raise


def _publicar_zip_temporario(temporario, caminho):
    """Publica somente por link exclusivo; nunca substitui um destino existente."""
    if temporario is None:
        return caminho
    try:
        os.link(str(temporario), str(caminho))
    except FileExistsError:
        existente = _ler_zip_regular(caminho)
        if existente != temporario.read_bytes():
            raise ValueError('ZIP de destino apareceu ou diverge do pacote esperado; nada foi sobrescrito')
    finally:
        if temporario.exists():
            temporario.unlink()
    return caminho


def _zip_deterministico(destino, esperado):
    """Compatibilidade interna: prepara e publica o ZIP sem sobrescrever destinos."""
    temporario, caminho = _preparar_zip_deterministico(destino, esperado)
    return _publicar_zip_temporario(temporario, caminho)


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
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.parent.is_symlink():
        raise ValueError('diretório pai do destino não pode usar symlink: {}'.format(destino.parent))
    zip_temporario = None
    try:
        zip_temporario, zip_path = _preparar_zip_deterministico(destino, esperado)
        if destino.exists():
            existente = _arvore(destino)
            if existente != esperado:
                raise ValueError('destino não vazio diverge do pacote esperado; nada foi sobrescrito')
            zip_path = _publicar_zip_temporario(zip_temporario, zip_path)
            return {'destino': str(destino), 'zip': str(zip_path), 'arquivos': len(esperado), 'idempotente': True}

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
        zip_path = _publicar_zip_temporario(zip_temporario, zip_path)
        return {'destino': str(destino), 'zip': str(zip_path), 'arquivos': len(esperado), 'idempotente': False}
    except Exception:
        if zip_temporario is not None and zip_temporario.exists():
            zip_temporario.unlink()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', help='pasta nova para o pacote exportado')
    parser.add_argument('--commit-origem', default=COMMIT_BASE_PADRAO)
    argumentos = parser.parse_args()
    resultado = exportar(destino=argumentos.destino, commit_origem=argumentos.commit_origem)
    print('Pacote exportado: {destino} ({arquivos} arquivos; idempotente={idempotente})'.format(**resultado))


if __name__ == '__main__':
    main()
