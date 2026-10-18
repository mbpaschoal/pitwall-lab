#!/usr/bin/env python3
"""Treina o experimento v1 sem abrir o teste final reservado de 2025.

O programa lê exclusivamente treino.csv, validacao.csv e colunas.json na pasta
indicada. O protocolo em docs/experimento_modelo_v1.md foi fixado antes do
ajuste; este código não escolhe entradas ou parâmetros a partir da validação.
"""
import argparse
import csv
from datetime import datetime
from hashlib import sha256
from importlib import metadata as importlib_metadata
import io
import json
import math
from pathlib import Path
import sys
import warnings

import joblib
import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


ENTRADAS_AUTORIZADAS = [
    'posicao_classificacao',
    'posicao_classificacao_repetida',
    'classificacao_ausente',
    'posicao_classificacao_ausente',
    'media_posicao_final_5',
    'taxa_podios_5',
    'n_posicoes_5',
    'n_podios_5',
    'media_pontos_equipe_5',
    'n_corridas_equipe_5',
    'n_participacoes_equipe_5',
    'historico_piloto_insuficiente',
    'historico_equipe_insuficiente',
    'equipe_pre_corrida_ausente',
    'referencia_temporal_ausente',
]
BOOLEANOS = {
    'posicao_classificacao_repetida',
    'classificacao_ausente',
    'posicao_classificacao_ausente',
    'historico_piloto_insuficiente',
    'historico_equipe_insuficiente',
    'equipe_pre_corrida_ausente',
    'referencia_temporal_ausente',
}
ARQUIVOS_DADOS_PERMITIDOS = ('treino.csv', 'validacao.csv', 'colunas.json')
VERSAO_ARTEFATO = 'modelo_v1.0'


def _sha256_bytes(conteudo):
    return sha256(conteudo).hexdigest()


def _ler_bytes(caminho):
    try:
        return Path(caminho).read_bytes()
    except OSError as erro:
        raise ValueError('Não foi possível ler a fonte permitida: {}'.format(caminho)) from erro


def _proibir_2025(caminho):
    partes = [parte.lower() for parte in Path(caminho).parts]
    if any('2025' in parte or 'reservado' in parte for parte in partes):
        raise ValueError('O teste de 2025 é reservado e não pode ser aberto neste experimento.')


def _ler_csv_permitido(caminho):
    _proibir_2025(caminho)
    texto = _ler_bytes(caminho).decode('utf-8')
    leitor = csv.DictReader(io.StringIO(texto))
    if not leitor.fieldnames:
        raise ValueError('CSV sem cabeçalho: {}'.format(caminho))
    return list(leitor), list(leitor.fieldnames), texto.encode('utf-8')


def _bool_csv(valor, coluna, indice):
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int) and valor in (0, 1):
        return bool(valor)
    if isinstance(valor, str):
        texto = valor.strip()
        if texto in ('1', 'True'):
            return True
        if texto in ('0', 'False'):
            return False
    raise ValueError('Booleano inválido em {} na linha {}: {!r}'.format(coluna, indice, valor))


def _numero_csv(valor, coluna, indice):
    if valor is None or (isinstance(valor, str) and valor.strip() == ''):
        return math.nan
    try:
        numero = float(valor)
    except (TypeError, ValueError) as erro:
        raise ValueError('Número inválido em {} na linha {}: {!r}'.format(coluna, indice, valor)) from erro
    if not math.isfinite(numero):
        raise ValueError('Número deve ser finito em {} na linha {}'.format(coluna, indice))
    return numero


def _alvo_csv(valor, indice):
    if valor is None or (isinstance(valor, str) and valor.strip() == ''):
        return None
    if isinstance(valor, bool):
        raise ValueError('podio deve ser vazio, 0 ou 1 na linha {}'.format(indice))
    if isinstance(valor, str):
        valor = valor.strip()
    if valor in (0, '0'):
        return 0
    if valor in (1, '1'):
        return 1
    raise ValueError('podio deve ser vazio, 0 ou 1 na linha {}'.format(indice))


def _validar_esquema(esquema):
    if not isinstance(esquema, dict):
        raise ValueError('colunas.json deve conter um objeto JSON.')
    if esquema.get('entradas') != ENTRADAS_AUTORIZADAS:
        raise ValueError('As entradas permitidas em colunas.json não correspondem ao protocolo fixado.')
    for chave in ('chaves', 'alvos', 'identificacao', 'auditoria_proibida_como_entrada'):
        if not isinstance(esquema.get(chave), list):
            raise ValueError('colunas.json sem lista válida: {}'.format(chave))
    if esquema.get('alvos') != ['podio']:
        raise ValueError('O único alvo permitido é podio.')


def selecionar_entradas(linhas, esquema, features=None):
    """Retorna só a matriz explicitamente autorizada, sem inferência por tipo.

    A API aceita a lista omitida ou exatamente a allowlist completa na ordem do
    protocolo. Subconjuntos não são aceitos neste experimento, porque seriam uma
    nova escolha de variáveis após o plano fixado.
    """
    _validar_esquema(esquema)
    escolhidas = ENTRADAS_AUTORIZADAS if features is None else list(features)
    proibidas = (set(esquema['chaves']) | set(esquema['alvos']) |
                 set(esquema['identificacao']) |
                 set(esquema['auditoria_proibida_como_entrada']))
    if any(coluna in proibidas or coluna not in ENTRADAS_AUTORIZADAS for coluna in escolhidas):
        raise ValueError('Há coluna proibida ou não permitida como entrada.')
    if escolhidas != ENTRADAS_AUTORIZADAS:
        raise ValueError('A ordem e a lista de entradas permitidas são fixas no protocolo.')
    return [{coluna: linha[coluna] for coluna in escolhidas} for linha in linhas]


def validar_linhas(linhas, esquema, divisao_esperada):
    """Valida CSV completo, mas converte somente a allowlist para a matriz."""
    _validar_esquema(esquema)
    if divisao_esperada not in ('treino', 'validacao'):
        raise ValueError('Divisão não permitida: {}'.format(divisao_esperada))
    obrigatorias = set(esquema['chaves'] + esquema['alvos'] + esquema['identificacao'] + ENTRADAS_AUTORIZADAS)
    saida, chaves = [], set()
    anos = {'2021', '2022', '2023'} if divisao_esperada == 'treino' else {'2024'}
    for indice, original in enumerate(linhas, 2):
        if not obrigatorias.issubset(original):
            faltantes = sorted(obrigatorias - set(original))
            raise ValueError('CSV sem colunas obrigatórias: {}'.format(', '.join(faltantes)))
        registro = dict(original)
        chave = tuple(str(registro[campo]).strip() for campo in esquema['chaves'])
        if any(not valor for valor in chave):
            raise ValueError('Chave vazia na linha {}'.format(indice))
        if chave in chaves:
            raise ValueError('Chave duplicada: {}'.format('/'.join(chave)))
        chaves.add(chave)
        if registro.get('divisao') != divisao_esperada:
            raise ValueError('Divisão incoerente na linha {}'.format(indice))
        if str(registro['temporada']) not in anos:
            raise ValueError('Período incoerente na linha {}'.format(indice))
        try:
            rodada = int(str(registro['rodada']))
        except ValueError as erro:
            raise ValueError('Rodada inválida na linha {}'.format(indice)) from erro
        if rodada <= 0:
            raise ValueError('Rodada inválida na linha {}'.format(indice))
        for coluna in ENTRADAS_AUTORIZADAS:
            if coluna in BOOLEANOS:
                registro[coluna] = _bool_csv(registro[coluna], coluna, indice)
            else:
                registro[coluna] = _numero_csv(registro[coluna], coluna, indice)
        posicao = registro['posicao_classificacao']
        if not math.isnan(posicao) and posicao <= 0:
            raise ValueError('Posição da classificação deve ser positiva na linha {}'.format(indice))
        registro['podio'] = _alvo_csv(registro['podio'], indice)
        referencia = str(registro.get('limite_inferior_referencia_utc') or '').strip()
        if not registro['referencia_temporal_ausente']:
            if not referencia:
                raise ValueError('Referência temporal ausente na linha {}'.format(indice))
            try:
                datetime.fromisoformat(referencia.replace('Z', '+00:00'))
            except ValueError as erro:
                raise ValueError('Referência temporal inválida na linha {}'.format(indice)) from erro
        registro['limite_inferior_referencia_utc'] = referencia
        registro['temporada'] = str(registro['temporada'])
        registro['rodada'] = str(rodada)
        registro['piloto_id'] = str(registro['piloto_id'])
        saida.append(registro)
    selecionar_entradas(saida, esquema)
    return saida


def carregar_dados(dados):
    """Lê somente as três fontes autorizadas da divisão treino/validação."""
    raiz = Path(dados)
    _proibir_2025(raiz)
    if not raiz.is_dir():
        raise ValueError('Pasta de dados inexistente: {}'.format(raiz))
    caminhos = {nome: raiz / nome for nome in ARQUIVOS_DADOS_PERMITIDOS}
    for nome, caminho in caminhos.items():
        if not caminho.is_file():
            raise ValueError('Fonte permitida ausente: {}'.format(nome))
    treino_bruto, _, treino_bytes = _ler_csv_permitido(caminhos['treino.csv'])
    validacao_bruto, _, validacao_bytes = _ler_csv_permitido(caminhos['validacao.csv'])
    colunas_bytes = _ler_bytes(caminhos['colunas.json'])
    try:
        esquema = json.loads(colunas_bytes.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ValueError('colunas.json inválido.') from erro
    treino = validar_linhas(treino_bruto, esquema, 'treino')
    validacao = validar_linhas(validacao_bruto, esquema, 'validacao')
    return {
        'treino': treino,
        'validacao': validacao,
        'esquema': esquema,
        'hashes_fontes': {
            'treino.csv': _sha256_bytes(treino_bytes),
            'validacao.csv': _sha256_bytes(validacao_bytes),
            'colunas.json': _sha256_bytes(colunas_bytes),
        },
    }


def motivos_inelegibilidade(registro):
    motivos = []
    if registro['classificacao_ausente']:
        motivos.append('classificacao_ausente')
    if registro['referencia_temporal_ausente'] or not registro['limite_inferior_referencia_utc']:
        motivos.append('referencia_temporal_ausente')
    return motivos


def _matriz(registros, esquema):
    selecionadas = selecionar_entradas(registros, esquema)
    return np.asarray([[linha[coluna] for coluna in ENTRADAS_AUTORIZADAS] for linha in selecionadas], dtype=float)


def criar_pipeline():
    return Pipeline([
        ('imputador', SimpleImputer(strategy='median', keep_empty_features=True, add_indicator=False)),
        ('normalizador', StandardScaler()),
        ('modelo', LogisticRegression(C=1.0, penalty='l2', solver='lbfgs', max_iter=2000,
                                      tol=1e-4, class_weight=None, random_state=42)),
    ])


def ajustar(treino, esquema):
    elegiveis = [registro for registro in treino if not motivos_inelegibilidade(registro)]
    rotulados = [registro for registro in elegiveis if registro['podio'] is not None]
    if not rotulados:
        raise ValueError('Não há linha de treino elegível com alvo conhecido.')
    alvos = np.asarray([registro['podio'] for registro in rotulados], dtype=int)
    if len(set(alvos.tolist())) < 2:
        raise ValueError('O treino elegível precisa conter as classes 0 e 1.')
    exclusoes = []
    for registro in treino:
        motivos = motivos_inelegibilidade(registro)
        if motivos:
            exclusoes.append({'temporada': registro['temporada'], 'rodada': registro['rodada'],
                              'piloto_id': registro['piloto_id'], 'corrida': registro.get('corrida', ''),
                              'motivos_inelegibilidade': ';'.join(motivos),
                              'alvo_conhecido': registro['podio'] is not None})
    pipeline = criar_pipeline()
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        warnings.simplefilter('error', RuntimeWarning)
        pipeline.fit(_matriz(rotulados, esquema), alvos)
    return pipeline, rotulados, float(alvos.mean()), {'treino_total': len(treino),
                                                        'treino_elegivel': len(elegiveis),
                                                        'treino_inelegivel': len(exclusoes),
                                                        'treino_fit': len(rotulados),
                                                        'exclusoes_treino': exclusoes}


def _numero_texto(valor):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return ''
    if isinstance(valor, bool):
        return '1' if valor else '0'
    if isinstance(valor, (float, np.floating)):
        return format(float(valor), '.17g')
    return str(valor)


def _resumo_empates(ordenados, modo):
    grupos = []
    inicio = 0
    while inicio < len(ordenados):
        if modo == 'classificacao':
            valor = ordenados[inicio]['posicao_classificacao']
            if math.isnan(valor):
                tamanho = 1
                while inicio + tamanho < len(ordenados) and math.isnan(
                        ordenados[inicio + tamanho]['posicao_classificacao']):
                    tamanho += 1
            else:
                tamanho = 1
                while inicio + tamanho < len(ordenados) and ordenados[inicio + tamanho]['posicao_classificacao'] == valor:
                    tamanho += 1
        else:
            valor = ordenados[inicio]['probabilidade_modelo']
            tamanho = 1
            while inicio + tamanho < len(ordenados) and ordenados[inicio + tamanho]['probabilidade_modelo'] == valor:
                tamanho += 1
        if tamanho > 1:
            fim = inicio + tamanho
            impacto = inicio < 3 < fim
            if modo == 'classificacao':
                rotulo = 'posicao=ausente' if math.isnan(valor) else 'posicao={}'.format(_numero_texto(valor))
            else:
                rotulo = 'probabilidade={}'.format(_numero_texto(valor))
            grupos.append('{}:{}; impacto_fronteira={}'.format(
                rotulo, ','.join(r['piloto_id'] for r in ordenados[inicio:fim]), 'sim' if impacto else 'nao'))
        inicio += tamanho
    return ' | '.join(grupos) if grupos else 'sem_empates; impacto_fronteira=nao'


def classificar_previsoes(registros):
    por_gp = {}
    for registro in registros:
        por_gp.setdefault((registro['temporada'], registro['rodada']), []).append(registro)
    for grupo in por_gp.values():
        elegiveis = [r for r in grupo if r['elegivel_previsao']]
        modelo = sorted(elegiveis, key=lambda r: (-r['probabilidade_modelo'], r['piloto_id']))
        classificacao = sorted(elegiveis, key=lambda r: (
            math.isnan(r['posicao_classificacao']),
            r['posicao_classificacao'] if not math.isnan(r['posicao_classificacao']) else math.inf,
            r['piloto_id']))
        empate_modelo = _resumo_empates(modelo, 'modelo')
        empate_classificacao = _resumo_empates(classificacao, 'classificacao')
        for indice, registro in enumerate(modelo, 1):
            registro['ranking_modelo'] = indice
            registro['favorito_modelo'] = indice <= 3
            registro['empates_modelo'] = empate_modelo
        for indice, registro in enumerate(classificacao, 1):
            registro['ranking_classificacao'] = indice
            registro['favorito_classificacao'] = indice <= 3
            registro['empates_classificacao'] = empate_classificacao
        for registro in grupo:
            registro.setdefault('ranking_modelo', None)
            registro.setdefault('ranking_classificacao', None)
            registro.setdefault('favorito_modelo', False)
            registro.setdefault('favorito_classificacao', False)
            registro.setdefault('empates_modelo', '')
            registro.setdefault('empates_classificacao', '')


def prever_validacao(pipeline, constante, validacao, esquema):
    registros = []
    elegiveis = [r for r in validacao if not motivos_inelegibilidade(r)]
    if elegiveis:
        with threadpool_limits(limits=1), warnings.catch_warnings():
            warnings.simplefilter('error', RuntimeWarning)
            probabilidades = pipeline.predict_proba(_matriz(elegiveis, esquema))[:, 1]
    else:
        probabilidades = []
    por_id = {id(registro): float(probabilidade) for registro, probabilidade in zip(elegiveis, probabilidades)}
    for original in validacao:
        registro = dict(original)
        motivos = motivos_inelegibilidade(registro)
        registro['elegivel_previsao'] = not motivos
        registro['motivos_inelegibilidade'] = ';'.join(motivos)
        registro['alvo_conhecido'] = registro['podio'] is not None
        registro['probabilidade_modelo'] = por_id.get(id(original))
        registro['probabilidade_constante'] = constante if not motivos else None
        registros.append(registro)
    classificar_previsoes(registros)
    return registros


def _calibracao(registros, campo, nome):
    saida = []
    for faixa in range(10):
        inferior, superior = faixa / 10.0, (faixa + 1) / 10.0
        grupo = [r for r in registros if min(int(r[campo] * 10), 9) == faixa]
        if grupo:
            media = sum(r[campo] for r in grupo) / len(grupo)
            frequencia = sum(r['podio'] for r in grupo) / len(grupo)
        else:
            media = frequencia = None
        texto_faixa = '[{:.1f},{:.1f}]'.format(inferior, superior) if faixa == 9 else '[{:.1f},{:.1f})'.format(inferior, superior)
        saida.append({'metodo': nome, 'faixa': texto_faixa,
                      'limite_inferior': inferior, 'limite_superior': superior, 'contagem': len(grupo),
                      'media_prevista': media, 'frequencia_observada': frequencia})
    return saida


def avaliar(registros):
    rotulados = [r for r in registros if r['elegivel_previsao'] and r['alvo_conhecido']]
    metricas_prob = {'linhas_avaliaveis': len(rotulados)}
    if rotulados:
        alvos = [r['podio'] for r in rotulados]
        for campo, nome in [('probabilidade_modelo', 'modelo'), ('probabilidade_constante', 'constante')]:
            probabilidades = [r[campo] for r in rotulados]
            metricas_prob[nome] = {'log_loss': float(log_loss(alvos, probabilidades, labels=[0, 1])),
                                   'brier': float(brier_score_loss(alvos, probabilidades))}
    else:
        metricas_prob['modelo'] = {'log_loss': None, 'brier': None}
        metricas_prob['constante'] = {'log_loss': None, 'brier': None}
    por_gp = {}
    for registro in registros:
        por_gp.setdefault((registro['temporada'], registro['rodada']), []).append(registro)
    corridas, resultados_modelo, resultados_classificacao = [], [], []
    for (temporada, rodada), grupo in sorted(por_gp.items(), key=lambda item: (item[0][0], int(item[0][1]))):
        elegiveis = [r for r in grupo if r['elegivel_previsao']]
        motivos = []
        if len(elegiveis) < 3:
            motivos.append('menos_de_3_elegiveis')
        if len(elegiveis) != len(grupo):
            motivos.append('participante_inelegivel')
        if not all(r['alvo_conhecido'] for r in grupo):
            motivos.append('alvo_desconhecido')
        positivos = sum(r['podio'] for r in grupo if r['alvo_conhecido'])
        if all(r['alvo_conhecido'] for r in grupo) and positivos != 3:
            motivos.append('quantidade_de_podios_diferente_de_3')
        avaliavel = not motivos
        favoritos_modelo = [r['piloto_id'] for r in elegiveis if r['favorito_modelo']]
        favoritos_classificacao = [r['piloto_id'] for r in elegiveis if r['favorito_classificacao']]
        podio = [r['piloto_id'] for r in grupo if r['podio'] == 1] if avaliavel else []
        acertos_modelo = len(set(favoritos_modelo) & set(podio)) if avaliavel else None
        acertos_classificacao = len(set(favoritos_classificacao) & set(podio)) if avaliavel else None
        if avaliavel:
            resultados_modelo.append(acertos_modelo)
            resultados_classificacao.append(acertos_classificacao)
        corridas.append({'temporada': temporada, 'rodada': rodada, 'corrida': grupo[0].get('corrida', ''),
                         'participantes_preparados': len(grupo), 'elegiveis': len(elegiveis),
                         'alvos_conhecidos': sum(r['alvo_conhecido'] for r in grupo), 'podios_conhecidos': positivos,
                         'avaliavel_ranking': avaliavel, 'motivos_nao_avaliavel': ';'.join(motivos),
                         'favoritos_modelo': ';'.join(favoritos_modelo),
                         'favoritos_classificacao': ';'.join(favoritos_classificacao),
                         'podio_observado': ';'.join(podio), 'acertos_modelo': acertos_modelo,
                         'acertos_classificacao': acertos_classificacao})
    def resumo_ranking(resultados):
        quantidade = len(resultados)
        distribuicao = {str(valor): resultados.count(valor) for valor in range(4)}
        return {'corridas_avaliaveis': quantidade,
                'media_integrantes_corretos': (sum(resultados) / quantidade) if quantidade else None,
                'distribuicao_0_1_2_3': distribuicao,
                'proporcao_3_corretos': (resultados.count(3) / quantidade) if quantidade else None}
    calibracao = _calibracao(rotulados, 'probabilidade_modelo', 'modelo') + _calibracao(rotulados, 'probabilidade_constante', 'constante')
    metricas = {'probabilisticas': metricas_prob,
                'cobertura': {'linhas_validacao': len(registros), 'linhas_elegiveis': sum(r['elegivel_previsao'] for r in registros),
                              'linhas_inelegiveis': sum(not r['elegivel_previsao'] for r in registros),
                              'linhas_com_alvo_conhecido': sum(r['alvo_conhecido'] for r in registros),
                              'linhas_alvo_desconhecido': sum(not r['alvo_conhecido'] for r in registros),
                              'linhas_classificacao_ambigua': sum(r['posicao_classificacao_repetida'] for r in registros),
                              'gps_total': len(corridas), 'gps_avaliaveis_ranking': len(resultados_modelo)},
                'ranking_modelo': resumo_ranking(resultados_modelo),
                'ranking_classificacao': resumo_ranking(resultados_classificacao)}
    return metricas, corridas, calibracao


def _svg_calibracao(calibracao):
    largura, altura = 1120, 650
    esquerda, direita, topo, base = 105, 1040, 100, 365
    largura_reliability = direita - esquerda
    altura_reliability = base - topo
    hist_topo, hist_base = 475, 590
    maximo = max([linha['contagem'] for linha in calibracao] or [1]) or 1
    nomes = {'modelo': 'Modelo', 'constante': 'Constante'}
    partes = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 {} {}" role="img" aria-labelledby="titulo-calibracao descricao-calibracao" data-grafico="calibracao-confiabilidade" data-reliability-left="{}" data-reliability-width="{}" data-reliability-bottom="{}" data-reliability-height="{}">'.format(
            largura, altura, largura, altura, esquerda, largura_reliability, base, altura_reliability),
        '<title id="titulo-calibracao">Curva de confiabilidade e distribuição das faixas de probabilidade</title>',
        '<desc id="descricao-calibracao">No painel superior, cada ponto usa a probabilidade média prevista da faixa no eixo x e a frequência observada no eixo y. A diagonal tracejada representa calibração ideal. No painel inferior, barras lado a lado mostram as contagens por faixa para modelo e constante.</desc>',
        '<style>text{font-family:Arial,sans-serif;fill:#172033}.titulo{font-size:20px;font-weight:bold}.subtitulo{font-size:12px;fill:#475569}.grade{stroke:#cbd5e1;stroke-width:1}.eixo{stroke:#334155;stroke-width:1.25}.ideal{stroke:#64748b;stroke-width:1.5;stroke-dasharray:6 5}.modelo{fill:#2563eb}.constante{fill:#f97316}.barra-modelo{fill:#93c5fd;stroke:#2563eb;stroke-width:1}.barra-constante{fill:#fdba74;stroke:#f97316;stroke-width:1}.rotulo{font-size:11px}.contagem{font-size:10px;font-weight:bold}.legenda{font-size:12px}</style>',
        '<text x="{}" y="34" class="titulo">Calibração descritiva (2024)</text>'.format(esquerda),
        '<text x="{}" y="56" class="subtitulo">Curva de confiabilidade: x = probabilidade média prevista na faixa; y = frequência observada. Faixas vazias não recebem ponto.</text>'.format(esquerda),
        '<text x="{}" y="84" font-size="15" font-weight="bold">Curva de confiabilidade</text>'.format(esquerda),
        '<rect x="{}" y="{}" width="{}" height="{}" fill="#f8fafc" stroke="#cbd5e1"/>'.format(esquerda, topo, largura_reliability, altura_reliability),
    ]
    for valor in range(11):
        proporcao = valor / 10
        x = esquerda + proporcao * largura_reliability
        y = base - proporcao * altura_reliability
        partes.extend([
            '<line class="grade" x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(x, topo, x, base),
            '<line class="grade" x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(esquerda, y, direita, y),
            '<text class="rotulo" x="{}" y="{}" text-anchor="middle">{:.1f}</text>'.format(x, base + 19, proporcao),
            '<text class="rotulo" x="{}" y="{}" text-anchor="end" dominant-baseline="middle">{:.1f}</text>'.format(esquerda - 10, y, proporcao),
        ])
    partes.extend([
        '<line class="ideal" x1="{}" y1="{}" x2="{}" y2="{}"/><text x="{}" y="{}" class="subtitulo">ideal</text>'.format(esquerda, base, direita, topo, direita - 5, topo + 15),
        '<line class="eixo" x1="{}" y1="{}" x2="{}" y2="{}"/><line class="eixo" x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(esquerda, base, direita, base, esquerda, topo, esquerda, base),
        '<text x="{}" y="{}" font-size="13" text-anchor="middle">Probabilidade média prevista</text>'.format((esquerda + direita) / 2, base + 45),
        '<text x="25" y="{}" font-size="13" text-anchor="middle" transform="rotate(-90 25 {})">Frequência observada</text>'.format((topo + base) / 2, (topo + base) / 2),
        '<circle class="modelo" cx="760" cy="82" r="5"/><text x="771" y="86" class="legenda">modelo</text><circle class="constante" cx="855" cy="82" r="5"/><text x="866" y="86" class="legenda">constante</text>',
        '<text x="{}" y="450" font-size="15" font-weight="bold">Contagens por faixa de probabilidade</text>'.format(esquerda),
        '<rect x="{}" y="{}" width="{}" height="{}" fill="#f8fafc" stroke="#cbd5e1"/>'.format(esquerda, hist_topo, largura_reliability, hist_base - hist_topo),
        '<line class="eixo" x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(esquerda, hist_base, direita, hist_base),
    ])
    largura_faixa = largura_reliability / 10
    for indice in range(10):
        x_centro = esquerda + (indice + 0.5) * largura_faixa
        partes.append('<text class="rotulo" x="{}" y="{}" text-anchor="middle">{:.1f}–{:.1f}</text>'.format(
            x_centro, hist_base + 18, indice / 10, (indice + 1) / 10))
    for metodo in ('modelo', 'constante'):
        linhas = [linha for linha in calibracao if linha['metodo'] == metodo]
        for indice, linha in enumerate(linhas):
            x_centro = esquerda + (indice + 0.5) * largura_faixa
            deslocamento = -12 if metodo == 'modelo' else 12
            largura_barra = 20
            altura_barra = linha['contagem'] / maximo * (hist_base - hist_topo - 24)
            x_barra = x_centro + deslocamento - largura_barra / 2
            y_barra = hist_base - altura_barra
            partes.extend([
                '<rect class="barra-{}" x="{}" y="{}" width="{}" height="{}" data-metodo="{}" data-faixa="{}" data-contagem="{}"><title>{}: faixa {}; contagem {}</title></rect>'.format(
                    metodo, x_barra, y_barra, largura_barra, altura_barra, metodo, linha['faixa'], linha['contagem'], nomes[metodo], linha['faixa'], linha['contagem']),
                '<text class="contagem" x="{}" y="{}" text-anchor="middle">{}</text>'.format(x_centro + deslocamento, y_barra - 5, linha['contagem']),
            ])
            if linha['media_prevista'] is not None:
                media = float(linha['media_prevista'])
                frequencia = float(linha['frequencia_observada'])
                x_ponto = esquerda + media * largura_reliability
                y_ponto = base - frequencia * altura_reliability
                partes.append('<circle class="{}" cx="{}" cy="{}" r="5" data-metodo="{}" data-faixa="{}" data-media-prevista="{}" data-frequencia="{}" data-contagem="{}"><title>{}: faixa {}; média prevista {}; frequência observada {}; contagem {}</title></circle>'.format(
                    metodo, x_ponto, y_ponto, metodo, linha['faixa'], _numero_texto(media), _numero_texto(frequencia), linha['contagem'], nomes[metodo], linha['faixa'], _numero_texto(media), _numero_texto(frequencia), linha['contagem']))
    partes.extend([
        '<rect class="barra-modelo" x="760" y="438" width="14" height="10"/><text x="779" y="447" class="legenda">modelo</text><rect class="barra-constante" x="855" y="438" width="14" height="10"/><text x="874" y="447" class="legenda">constante</text>',
        '<text x="{}" y="630" class="subtitulo">Barras lado a lado e rótulos mostram a contagem de cada método, inclusive zero.</text>'.format(esquerda),
        '</svg>',
    ])
    return ''.join(partes) + '\n'


def _csv_bytes(linhas, campos):
    destino = io.StringIO(newline='')
    escritor = csv.DictWriter(destino, fieldnames=campos, extrasaction='raise', lineterminator='\n')
    escritor.writeheader()
    for linha in linhas:
        escritor.writerow({campo: _numero_texto(linha.get(campo)) for campo in campos})
    return destino.getvalue().encode('utf-8')


def _json_bytes(objeto):
    _recusar_nan_json(objeto)
    return (json.dumps(objeto, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def _recusar_nan_json(objeto):
    if isinstance(objeto, float) and not math.isfinite(objeto):
        raise ValueError('NaN/infinito não é JSON válido.')
    if isinstance(objeto, dict):
        for valor in objeto.values():
            _recusar_nan_json(valor)
    elif isinstance(objeto, (list, tuple)):
        for valor in objeto:
            _recusar_nan_json(valor)


def _metadados(pipeline, constante, dados, plano_bytes, contadores):
    imputador = pipeline.named_steps['imputador']
    normalizador = pipeline.named_steps['normalizador']
    modelo = pipeline.named_steps['modelo']
    aprendidos = {'medianas_imputador': [float(v) for v in imputador.statistics_],
                  'media_normalizador': [float(v) for v in normalizador.mean_],
                  'escala_normalizador': [float(v) for v in normalizador.scale_],
                  'coeficientes': [float(v) for v in modelo.coef_[0]],
                  'intercepto': float(modelo.intercept_[0])}
    retorno = {'versao_artefato': VERSAO_ARTEFATO, 'entradas': ENTRADAS_AUTORIZADAS,
               'configuracao': {'imputador': {'strategy': 'median', 'keep_empty_features': True, 'add_indicator': False},
                                'normalizador': 'StandardScaler',
                                'regressao_logistica': {'C': 1.0, 'penalty': 'l2', 'solver': 'lbfgs',
                                                        'max_iter': 2000, 'tol': 0.0001, 'class_weight': None,
                                                        'random_state': 42}, 'threads_nativas': 1},
               'constante_treino': constante, 'contadores_treino': contadores,
               'parametros_aprendidos': aprendidos,
               'versoes': {'python': sys.version.split()[0], 'numpy': np.__version__, 'scikit_learn': sklearn.__version__,
                            'joblib': joblib.__version__, 'threadpoolctl': importlib_metadata.version('threadpoolctl')},
               'hashes_fontes_permitidas': dados['hashes_fontes'], 'sha256_plano_fixado': _sha256_bytes(plano_bytes),
               'aviso_seguranca': 'Nao carregar modelo.joblib de terceiros: arquivos joblib/pickle podem executar codigo.'}
    _recusar_nan_json(retorno)
    return retorno


def _coeficientes(pipeline):
    imputador = pipeline.named_steps['imputador']
    normalizador = pipeline.named_steps['normalizador']
    modelo = pipeline.named_steps['modelo']
    return [{'entrada': entrada, 'coeficiente_padronizado': float(modelo.coef_[0][indice]),
             'mediana_treino': float(imputador.statistics_[indice]),
             'media_treino_pos_imputacao': float(normalizador.mean_[indice]),
             'escala_treino_pos_imputacao': float(normalizador.scale_[indice])}
            for indice, entrada in enumerate(ENTRADAS_AUTORIZADAS)]


def _relatorio(metricas, constante, contadores, coeficientes):
    probabilisticas = metricas['probabilisticas']
    modelo = probabilisticas['modelo']
    referencia = probabilisticas['constante']
    def n(valor):
        return 'n/d' if valor is None else _numero_texto(valor)
    def distribuicao(ranking):
        valores = ranking['distribuicao_0_1_2_3']
        return '{} / {} / {} / {}'.format(valores['0'], valores['1'], valores['2'], valores['3'])
    exemplos = sorted(coeficientes, key=lambda linha: abs(linha['coeficiente_padronizado']), reverse=True)[:3]
    exemplos_texto = '; '.join('{} ({:+.4f})'.format(linha['entrada'], linha['coeficiente_padronizado']) for linha in exemplos)
    exclusoes = contadores['exclusoes_treino']
    exclusoes_texto = '; '.join('{temporada}/{rodada} — {piloto_id} — {corrida}: {motivos_inelegibilidade}'.format(**linha)
                              for linha in exclusoes) if exclusoes else 'nenhuma'
    return """# Etapa 4 — modelo v1 de probabilidade de pódio

Este é um estudo retrospectivo. O protocolo em `docs/experimento_modelo_v1.md` foi fixado antes do ajuste. O treino usa somente 2021–2023; a validação usa somente 2024, que já havia sido explorada. O teste de 2025 não foi aberto nem avaliado.

## Cobertura

- Linhas de validação: {linhas}; elegíveis para previsão: {elegiveis}; inelegíveis: {inelegiveis}; com alvo conhecido: {alvos}; alvo desconhecido: {alvos_desconhecidos}.
- Linhas usadas nas métricas probabilísticas: {prob_linhas}.
- GPs presentes em 2024: {gps}; GPs avaliáveis para os rankings comuns: {gps_rank}.
- Treino: {fit} linhas elegíveis e rotuladas ajustaram o pipeline; {treino_inelegivel} linha ficou inelegível; a referência constante foi {constante} nessas mesmas linhas.
- Exclusão de treino: {exclusoes}. A auditoria completa está em [cobertura_treino.csv](cobertura_treino.csv).
- Classificação ambígua em validação: {ambiguas} linha(s). Os desempates e o impacto na fronteira estão registrados por piloto em [previsoes_validacao.csv](previsoes_validacao.csv), nas colunas `empates_classificacao` e `empates_modelo`.

## Métricas probabilísticas

| Método | Log loss | Brier |
| --- | ---: | ---: |
| Modelo logístico | {ll_modelo} | {br_modelo} |
| Constante de treino | {ll_constante} | {br_constante} |

Menor é melhor nas duas métricas. O CSV e o SVG de calibração usam dez faixas fixas e mostram contagens; faixa vazia não é interpretada como frequência zero.

[Abrir o gráfico SVG de calibração](calibracao.svg).

## Rankings top 3

| Método | GPs avaliáveis | Média de integrantes corretos | Proporção de 3 corretos |
| --- | ---: | ---: | ---: |
| Modelo por probabilidade | {n_modelo} | {m_modelo} | {p_modelo} |
| Classificação | {n_classificacao} | {m_classificacao} | {p_classificacao} |

Distribuição de GPs com 0 / 1 / 2 / 3 integrantes corretos: modelo = **{dist_modelo}**; classificação = **{dist_classificacao}**.

Os rankings só são pontuados quando todos os participantes preparados são elegíveis, todos têm alvo conhecido e existem exatamente três pódios. GP incompleto não recebe zero artificial. A referência de classificação é ranking, não probabilidade; posição ausente fica ao final e empates usam `piloto_id` em ordem lexicográfica. O modelo usa probabilidade decrescente e o mesmo desempate somente em empate exato.

## Leitura e limites

Os coeficientes padronizados completos estão em [coeficientes.csv](coeficientes.csv). Os três maiores valores absolutos nesta execução foram: {exemplos_coeficientes}. Sinal positivo/negativo descreve associação condicionada às demais entradas, ao treino e à regularização; não é efeito causal. As probabilidades individuais não precisam somar três em um GP e não foram renormalizadas. Há poucas temporadas, pilotos do mesmo GP são correlacionados, 2024 já foi explorada e as fontes históricas podem conter revisões posteriores. Este resultado não alega generalização para 2025.

O modelo salvo é um arquivo joblib local confiável; não carregue arquivo joblib/pickle recebido de terceiros.
""".format(linhas=metricas['cobertura']['linhas_validacao'], elegiveis=metricas['cobertura']['linhas_elegiveis'],
           inelegiveis=metricas['cobertura']['linhas_inelegiveis'], alvos=metricas['cobertura']['linhas_com_alvo_conhecido'],
           alvos_desconhecidos=metricas['cobertura']['linhas_alvo_desconhecido'],
           prob_linhas=probabilisticas['linhas_avaliaveis'], gps=metricas['cobertura']['gps_total'],
           gps_rank=metricas['cobertura']['gps_avaliaveis_ranking'], fit=contadores['treino_fit'],
           treino_inelegivel=contadores['treino_inelegivel'], exclusoes=exclusoes_texto,
           ambiguas=metricas['cobertura']['linhas_classificacao_ambigua'], constante=_numero_texto(constante),
           ll_modelo=n(modelo['log_loss']), br_modelo=n(modelo['brier']),
           ll_constante=n(referencia['log_loss']), br_constante=n(referencia['brier']),
           n_modelo=metricas['ranking_modelo']['corridas_avaliaveis'],
           m_modelo=n(metricas['ranking_modelo']['media_integrantes_corretos']),
           p_modelo=n(metricas['ranking_modelo']['proporcao_3_corretos']),
           dist_modelo=distribuicao(metricas['ranking_modelo']),
           n_classificacao=metricas['ranking_classificacao']['corridas_avaliaveis'],
           m_classificacao=n(metricas['ranking_classificacao']['media_integrantes_corretos']),
           p_classificacao=n(metricas['ranking_classificacao']['proporcao_3_corretos']),
           dist_classificacao=distribuicao(metricas['ranking_classificacao']), exemplos_coeficientes=exemplos_texto)


def _preflight(saidas):
    for caminho, conteudo in saidas.items():
        if caminho.exists():
            if not caminho.is_file() or caminho.read_bytes() != conteudo:
                raise FileExistsError('Destino existente diverge e foi preservado: {}'.format(caminho))


def _gravar_lote(saidas):
    _preflight(saidas)
    for caminho in saidas:
        caminho.parent.mkdir(parents=True, exist_ok=True)
    for caminho, conteudo in saidas.items():
        if not caminho.exists():
            caminho.write_bytes(conteudo)


def executar(dados='data/preparado', modelos='models/modelo_v1', relatorios='reports/modelo_v1',
             plano='docs/experimento_modelo_v1.md'):
    """Executa o experimento inteiro e retorna as métricas, sem acesso à rede."""
    caminho_plano = Path(plano)
    _proibir_2025(caminho_plano)
    plano_bytes = _ler_bytes(caminho_plano)
    fontes = carregar_dados(dados)
    pipeline, treino_fit, constante, contadores = ajustar(fontes['treino'], fontes['esquema'])
    previsoes = prever_validacao(pipeline, constante, fontes['validacao'], fontes['esquema'])
    metricas, corridas, calibracao = avaliar(previsoes)
    metadados = _metadados(pipeline, constante, fontes, plano_bytes, contadores)
    carga_modelo = {'versao_artefato': VERSAO_ARTEFATO, 'entradas': ENTRADAS_AUTORIZADAS,
                    'configuracao': metadados['configuracao'], 'pipeline': pipeline}
    buffer = io.BytesIO()
    joblib.dump(carga_modelo, buffer, compress=0, protocol=4)
    campos_previsoes = ['temporada', 'rodada', 'piloto_id', 'corrida', 'data_corrida', 'elegivel_previsao',
                        'motivos_inelegibilidade', 'alvo_conhecido', 'podio', 'probabilidade_modelo',
                        'probabilidade_constante', 'ranking_modelo', 'favorito_modelo', 'ranking_classificacao',
                        'favorito_classificacao', 'empates_modelo', 'empates_classificacao']
    campos_corridas = ['temporada', 'rodada', 'corrida', 'participantes_preparados', 'elegiveis', 'alvos_conhecidos',
                       'podios_conhecidos', 'avaliavel_ranking', 'motivos_nao_avaliavel', 'favoritos_modelo',
                       'favoritos_classificacao', 'podio_observado', 'acertos_modelo', 'acertos_classificacao']
    campos_calibracao = ['metodo', 'faixa', 'limite_inferior', 'limite_superior', 'contagem', 'media_prevista', 'frequencia_observada']
    campos_coeficientes = ['entrada', 'coeficiente_padronizado', 'mediana_treino', 'media_treino_pos_imputacao', 'escala_treino_pos_imputacao']
    cobertura_treino = []
    for registro in fontes['treino']:
        motivos = motivos_inelegibilidade(registro)
        cobertura_treino.append({'temporada': registro['temporada'], 'rodada': registro['rodada'],
                                 'piloto_id': registro['piloto_id'], 'corrida': registro.get('corrida', ''),
                                 'elegivel_previsao': not motivos, 'motivos_inelegibilidade': ';'.join(motivos),
                                 'alvo_conhecido': registro['podio'] is not None})
    campos_cobertura_treino = ['temporada', 'rodada', 'piloto_id', 'corrida', 'elegivel_previsao',
                               'motivos_inelegibilidade', 'alvo_conhecido']
    coeficientes = _coeficientes(pipeline)
    modelos = Path(modelos)
    relatorios = Path(relatorios)
    saidas = {modelos / 'modelo.joblib': buffer.getvalue(), modelos / 'metadados.json': _json_bytes(metadados),
              relatorios / 'previsoes_validacao.csv': _csv_bytes(previsoes, campos_previsoes),
              relatorios / 'avaliacao_corridas.csv': _csv_bytes(corridas, campos_corridas),
              relatorios / 'calibracao.csv': _csv_bytes(calibracao, campos_calibracao),
              relatorios / 'coeficientes.csv': _csv_bytes(coeficientes, campos_coeficientes),
              relatorios / 'cobertura_treino.csv': _csv_bytes(cobertura_treino, campos_cobertura_treino),
              relatorios / 'metricas.json': _json_bytes(metricas),
              relatorios / 'relatorio.md': _relatorio(metricas, constante, contadores, coeficientes).encode('utf-8'),
              relatorios / 'calibracao.svg': _svg_calibracao(calibracao).encode('utf-8')}
    _gravar_lote(saidas)
    return metricas


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dados', default='data/preparado', help='Pasta que contém somente as fontes permitidas.')
    parser.add_argument('--modelos', default='models/modelo_v1', help='Pasta de artefatos do modelo.')
    parser.add_argument('--relatorios', default='reports/modelo_v1', help='Pasta de relatórios.')
    parser.add_argument('--plano', default='docs/experimento_modelo_v1.md', help='Plano fixado antes do treino.')
    argumentos = parser.parse_args(argv)
    plano_bytes = _ler_bytes(Path(argumentos.plano))
    print('Plano fixado previamente (não alterado por esta execução); SHA-256: {}'.format(_sha256_bytes(plano_bytes)))
    metricas = executar(argumentos.dados, argumentos.modelos, argumentos.relatorios, argumentos.plano)
    print('Experimento concluído: {} linhas probabilísticas avaliáveis; {} GPs avaliáveis para ranking.'.format(
        metricas['probabilisticas']['linhas_avaliaveis'], metricas['cobertura']['gps_avaliaveis_ranking']))


if __name__ == '__main__':
    main()