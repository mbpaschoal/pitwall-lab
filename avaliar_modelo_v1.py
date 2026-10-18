#!/usr/bin/env python3
"""Avalia retrospectivamente em 2025 o modelo v1 já congelado, sem reajustá-lo.

A execução padrão usa somente data/preparado/teste_final_reservado.csv como
fonte de teste e publica artefatos determinísticos em reports/avaliacao_final_v1.
Nenhuma opção desta CLI treina, calibra ou altera o modelo salvo.
"""
import argparse
import csv
from datetime import datetime
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import tempfile
import warnings

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from treinar_modelo_v1 import (
    BOOLEANOS,
    ENTRADAS_AUTORIZADAS,
    _alvo_csv,
    _bool_csv,
    _calibracao,
    _csv_bytes,
    _json_bytes,
    _matriz,
    _numero_texto,
    _numero_csv,
    _svg_calibracao,
    _validar_esquema,
    avaliar,
    classificar_previsoes,
    motivos_inelegibilidade,
    selecionar_entradas,
)


DIVISAO_TESTE = 'teste_final_reservado'
TEMPORADA_TESTE = '2025'
CONSTANTE_CONGELADA = 0.15011372251705837
HASHES_CONGELADOS = {
    'plano_avaliacao': '7b67a47d1136dc02bc24236dfbf6acb8e9e4e646a6d9cb68cba09a4fc6da8983',
    'plano_original': 'd6c671526aafe1ca8a1a6b98934a1d1915eb7a102872d51e5385991257fec569',
    'modelo': '16718ea5c4a7f662e72f09d38b073e545df1bba5c64c87b2cc1a0973ad9116e3',
    'metadados': '77d24dc765d773e49b717b79844dd4678a91087dbbc091e3e9cb184215ea9cc6',
    'treinador': 'cdf1c2ea005f36f032ebd1694786e9118ae343a282172fafb748cbf5c2294de3',
    'metricas_2024': 'e06613f5178fecdd06e7afdccb0503ab4f277e5712c61c5cf85f193ae240686f',
}
NOMES_SAIDAS = (
    'previsoes_pre_corrida.csv', 'avaliacao_por_piloto.csv', 'cobertura_pilotos.csv',
    'cobertura_gps.csv', 'avaliacao_corridas.csv', 'metricas.json', 'calibracao.csv', 'calibracao.svg',
    'comparacao_2024.json', 'relatorio.md', 'manifesto.json',
)


def _campos_previsao(esquema):
    return set(esquema['chaves'] + esquema['identificacao'] + ENTRADAS_AUTORIZADAS)


def validar_linhas_teste(linhas, esquema):
    """Valida apenas informação pré-corrida de 2025, sem ler alvo ou auditoria."""
    _validar_esquema(esquema)
    obrigatorias = _campos_previsao(esquema)
    saida = []
    chaves = set()
    for indice, original in enumerate(linhas, 2):
        if not obrigatorias.issubset(original):
            faltantes = sorted(obrigatorias - set(original))
            raise ValueError('CSV sem colunas pré-corrida obrigatórias: {}'.format(', '.join(faltantes)))
        registro = {campo: original[campo] for campo in obrigatorias}
        chave = tuple(str(registro[campo]).strip() for campo in esquema['chaves'])
        if any(not valor for valor in chave):
            raise ValueError('Chave vazia na linha {}'.format(indice))
        if chave in chaves:
            raise ValueError('Chave duplicada: {}'.format('/'.join(chave)))
        chaves.add(chave)
        if registro.get('divisao') != DIVISAO_TESTE:
            raise ValueError('Divisão incoerente na linha {}; esperado teste_final_reservado.'.format(indice))
        if str(registro['temporada']) != TEMPORADA_TESTE:
            raise ValueError('Período incoerente na linha {}; esperado 2025.'.format(indice))
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


def prever_teste(pipeline, constante, registros_pre_corrida, esquema):
    """Gera probabilidades e favoritos sem receber ou ler alvos/auditoria."""
    if constante != CONSTANTE_CONGELADA:
        raise ValueError('A constante de treino congelada não corresponde ao valor fixado.')
    elegiveis = [registro for registro in registros_pre_corrida if not motivos_inelegibilidade(registro)]
    if elegiveis:
        with threadpool_limits(limits=1), warnings.catch_warnings():
            warnings.simplefilter('error', RuntimeWarning)
            probabilidades = pipeline.predict_proba(_matriz(elegiveis, esquema))[:, 1]
    else:
        probabilidades = []
    por_id = {id(registro): float(probabilidade) for registro, probabilidade in zip(elegiveis, probabilidades)}
    previsoes = []
    for original in registros_pre_corrida:
        registro = dict(original)
        motivos = motivos_inelegibilidade(registro)
        registro['elegivel_previsao'] = not motivos
        registro['motivos_inelegibilidade'] = ';'.join(motivos)
        registro['probabilidade_modelo'] = por_id.get(id(original))
        registro['probabilidade_constante'] = constante if not motivos else None
        previsoes.append(registro)
    classificar_previsoes(previsoes)
    return previsoes


def _sha256_bytes(conteudo):
    return sha256(conteudo).hexdigest()


def _ler_bytes(caminho):
    try:
        return Path(caminho).read_bytes()
    except OSError as erro:
        raise ValueError('Não foi possível ler o artefato permitido: {}'.format(caminho)) from erro


def _ler_json(caminho, rotulo):
    try:
        return json.loads(_ler_bytes(caminho).decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ValueError('{} inválido.'.format(rotulo)) from erro


def _verificar_hash(rotulo, conteudo, esperado):
    obtido = _sha256_bytes(conteudo)
    if obtido != esperado:
        raise ValueError('SHA-256 divergente para {}: artefato preservado, avaliação interrompida.'.format(rotulo))
    return obtido


def _fingerprint_pipeline(pipeline):
    try:
        imputador = pipeline.named_steps['imputador']
        normalizador = pipeline.named_steps['normalizador']
        modelo = pipeline.named_steps['modelo']
        return {
            'medianas': [float(valor) for valor in imputador.statistics_],
            'medias': [float(valor) for valor in normalizador.mean_],
            'escalas': [float(valor) for valor in normalizador.scale_],
            'coeficientes': [float(valor) for valor in modelo.coef_[0]],
            'intercepto': float(modelo.intercept_[0]),
            'parametros': {
                'C': float(modelo.C), 'penalty': modelo.penalty, 'solver': modelo.solver,
                'max_iter': int(modelo.max_iter), 'tol': float(modelo.tol),
                'class_weight': modelo.class_weight, 'random_state': modelo.random_state,
            },
        }
    except (AttributeError, KeyError, TypeError) as erro:
        raise ValueError('Pipeline congelado sem os estágios v1 esperados.') from erro


def _verificar_metadados(meta, esquema, pipeline):
    if meta.get('entradas') != ENTRADAS_AUTORIZADAS or len(meta.get('entradas', [])) != 15:
        raise ValueError('Metadados não preservam as 15 entradas congeladas.')
    if meta.get('constante_treino') != CONSTANTE_CONGELADA:
        raise ValueError('Constante de treino divergente dos metadados congelados.')
    configuracao = meta.get('configuracao', {})
    regressao = configuracao.get('regressao_logistica', {})
    if regressao != {'C': 1.0, 'penalty': 'l2', 'solver': 'lbfgs', 'max_iter': 2000,
                     'tol': 0.0001, 'class_weight': None, 'random_state': 42}:
        raise ValueError('Parâmetros da regressão congelada divergentes.')
    if configuracao.get('imputador') != {'strategy': 'median', 'keep_empty_features': True, 'add_indicator': False}:
        raise ValueError('Parâmetros do imputador congelado divergentes.')
    if configuracao.get('normalizador') != 'StandardScaler' or configuracao.get('threads_nativas') != 1:
        raise ValueError('Parâmetros do normalizador congelado divergentes.')
    _validar_esquema(esquema)
    if esquema['entradas'] != meta['entradas']:
        raise ValueError('Esquema e metadados não concordam sobre as entradas.')
    aprendidos = meta.get('parametros_aprendidos', {})
    atual = _fingerprint_pipeline(pipeline)
    esperado = {
        'medianas': aprendidos.get('medianas_imputador'),
        'medias': aprendidos.get('media_normalizador'),
        'escalas': aprendidos.get('escala_normalizador'),
        'coeficientes': aprendidos.get('coeficientes'),
        'intercepto': aprendidos.get('intercepto'),
    }
    if {chave: atual[chave] for chave in esperado} != esperado:
        raise ValueError('Parâmetros aprendidos do pipeline divergem dos metadados congelados.')
    if atual['parametros'] != regressao:
        raise ValueError('Pipeline carregado diverge dos parâmetros congelados.')
    return atual


def _verificar_integridade(plano_avaliacao, plano_original, modelo, metadados, treinador,
                           esquema, metricas_2024):
    caminhos = {
        'plano_avaliacao': Path(plano_avaliacao), 'plano_original': Path(plano_original),
        'modelo': Path(modelo), 'metadados': Path(metadados), 'treinador': Path(treinador),
        'esquema': Path(esquema), 'metricas_2024': Path(metricas_2024),
    }
    bytes_por_nome = {nome: _ler_bytes(caminho) for nome, caminho in caminhos.items()}
    hashes = {}
    for nome, esperado in HASHES_CONGELADOS.items():
        hashes[nome] = _verificar_hash(nome, bytes_por_nome[nome], esperado)
    hashes['esquema'] = _sha256_bytes(bytes_por_nome['esquema'])
    meta = _ler_json(caminhos['metadados'], 'metadados.json')
    esquema_objeto = _ler_json(caminhos['esquema'], 'colunas.json')
    metricas_2024_objeto = _ler_json(caminhos['metricas_2024'], 'metricas de 2024')
    if meta.get('hashes_fontes_permitidas', {}).get('colunas.json') != hashes['esquema']:
        raise ValueError('SHA-256 de colunas.json diverge do metadado congelado.')
    try:
        carga = joblib.load(caminhos['modelo'])
    except Exception as erro:
        raise ValueError('Não foi possível carregar o modelo local congelado.') from erro
    if not isinstance(carga, dict) or carga.get('entradas') != ENTRADAS_AUTORIZADAS:
        raise ValueError('Carga do modelo congelado inválida.')
    pipeline = carga.get('pipeline')
    antes = _verificar_metadados(meta, esquema_objeto, pipeline)
    return {
        'caminhos': caminhos, 'hashes': hashes, 'metadados': meta, 'esquema': esquema_objeto,
        'metricas_2024': metricas_2024_objeto, 'pipeline': pipeline, 'fingerprint_antes': antes,
    }


def _confirmar_congelamento(contexto):
    if _sha256_bytes(_ler_bytes(contexto['caminhos']['modelo'])) != contexto['hashes']['modelo']:
        raise ValueError('modelo.joblib foi alterado durante a avaliação.')
    depois = _verificar_metadados(contexto['metadados'], contexto['esquema'], contexto['pipeline'])
    if depois != contexto['fingerprint_antes']:
        raise ValueError('Pipeline congelado foi alterado durante a avaliação.')


def _ler_teste(caminho, esquema):
    caminho = Path(caminho)
    if caminho.name != 'teste_final_reservado.csv':
        raise ValueError('A única fonte de teste aceita é teste_final_reservado.csv.')
    conteudo = _ler_bytes(caminho)
    try:
        texto = conteudo.decode('utf-8')
    except UnicodeDecodeError as erro:
        raise ValueError('CSV de teste não está em UTF-8.') from erro
    leitor = csv.DictReader(io.StringIO(texto))
    if not leitor.fieldnames:
        raise ValueError('CSV de teste sem cabeçalho.')
    obrigatorias = _campos_previsao(esquema) | set(esquema['alvos']) | set(esquema['auditoria_proibida_como_entrada'])
    faltantes = sorted(obrigatorias - set(leitor.fieldnames))
    if faltantes:
        raise ValueError('CSV de teste sem colunas obrigatórias: {}'.format(', '.join(faltantes)))
    linhas = list(leitor)
    if not linhas:
        raise ValueError('CSV de teste vazio.')
    return linhas, conteudo


def extrair_alvos(linhas_brutas, previsoes, esquema):
    """Lê alvo somente após previsão/ranking, sem consultar colunas de auditoria."""
    alvos = {}
    for indice, original in enumerate(linhas_brutas, 2):
        chave = tuple(str(original[campo]).strip() for campo in esquema['chaves'])
        if chave in alvos:
            raise ValueError('Chave duplicada ao extrair alvo: {}'.format('/'.join(chave)))
        alvos[chave] = _alvo_csv(original['podio'], indice)
    chaves_previsoes = {(registro['temporada'], registro['rodada'], registro['piloto_id']) for registro in previsoes}
    if set(alvos) != chaves_previsoes:
        raise ValueError('Chaves de alvo não correspondem às previsões pré-corrida.')
    final = []
    for previsao in previsoes:
        registro = dict(previsao)
        chave = (registro['temporada'], registro['rodada'], registro['piloto_id'])
        registro['podio'] = alvos[chave]
        registro['alvo_conhecido'] = registro['podio'] is not None
        final.append(registro)
    return final


def avaliar_teste(registros):
    metricas, corridas, calibracao = avaliar(registros)
    cobertura = metricas['cobertura']
    cobertura['linhas_teste'] = cobertura.pop('linhas_validacao')
    return metricas, corridas, calibracao


def _svg_calibracao_2025(calibracao):
    return _svg_calibracao(calibracao).replace('Calibração descritiva (2024)', 'Calibração descritiva (2025)')


def _cobertura_pilotos(registros):
    return [{'temporada': registro['temporada'], 'rodada': registro['rodada'],
             'corrida': registro.get('corrida', ''), 'piloto_id': registro['piloto_id'],
             'elegivel_previsao': registro['elegivel_previsao'],
             'motivos_inelegibilidade': registro['motivos_inelegibilidade'],
             'alvo_conhecido': registro['alvo_conhecido']}
            for registro in registros]


def _comparacao_2024(metricas_2025, metricas_2024):
    return {
        'aviso': 'Comparação descritiva entre temporadas diferentes; não testa significância nem prevê desempenho futuro.',
        '2024': metricas_2024,
        '2025': metricas_2025,
        'denominadores_separados': {
            '2024_linhas_probabilisticas': metricas_2024['probabilisticas']['linhas_avaliaveis'],
            '2025_linhas_probabilisticas': metricas_2025['probabilisticas']['linhas_avaliaveis'],
            '2024_gps_ranking': metricas_2024['ranking_modelo']['corridas_avaliaveis'],
            '2025_gps_ranking': metricas_2025['ranking_modelo']['corridas_avaliaveis'],
        },
    }


def _resultado_menor_melhor(valor_modelo, valor_referencia):
    if valor_modelo is None or valor_referencia is None:
        return 'não comparável (denominador sem linhas avaliáveis)'
    if valor_modelo < valor_referencia:
        return 'o modelo foi menor que a constante'
    if valor_modelo > valor_referencia:
        return 'o modelo perdeu para a constante (valor maior)'
    return 'modelo e constante empataram'


def _relatorio(metricas, comparacao):
    prob = metricas['probabilisticas']
    cobertura = metricas['cobertura']
    ranking = metricas['ranking_modelo']
    classificacao = metricas['ranking_classificacao']
    n = lambda valor: 'n/d' if valor is None else _numero_texto(valor)
    return """# Etapa 5 — avaliação final retrospectiva do modelo v1 em 2025

Status: avaliado_para_modelo_v1

Esta avaliação usa o modelo v1 congelado e a fonte de teste de 2025. A previsão e a seleção dos favoritos ocorreram antes de extrair `podio`; o alvo vazio permaneceu desconhecido, nunca foi convertido em zero. Não houve ajuste, calibração, seleção de variáveis ou mudança de limiar.

## Cobertura

- Linhas de teste: {linhas}; elegíveis para previsão: {elegiveis}; inelegíveis: {inelegiveis}.
- Linhas com alvo conhecido: {conhecidos}; alvo desconhecido: {desconhecidos}; linhas nas métricas probabilísticas: {probabilisticas}.
- GPs presentes: {gps}; GPs avaliáveis no ranking comum: {gps_avaliaveis}.

## Métricas probabilísticas

| Método | Log loss | Brier |
| --- | ---: | ---: |
| Modelo | {ll_modelo} | {brier_modelo} |
| Constante de treino | {ll_constante} | {brier_constante} |

Para Brier, {comparacao_brier}. Menor é melhor, mas um Brier menor sozinho não prova calibração melhor. A calibração descritiva tem dez faixas e mantém faixas vazias sem frequência artificial.

## Rankings top 3

| Método | GPs avaliáveis | Média de integrantes corretos | Proporção de 3 corretos |
| --- | ---: | ---: | ---: |
| Modelo | {gps_modelo} | {media_modelo} | {top3_modelo} |
| Classificação | {gps_classificacao} | {media_classificacao} | {top3_classificacao} |

Os dois rankings compartilham a mesma coorte de GPs avaliáveis. GPs com menos de três elegíveis, participante inelegível, alvo desconhecido ou número de pódios diferente de três têm pontuação indefinida, não zero artificial. Empates seguem `piloto_id` lexicográfico; posições de classificação ausentes ficam após as conhecidas. Probabilidades individuais não foram renormalizadas para somar três por GP.

## Comparação descritiva com 2024 e limites

Os valores de 2024 em `comparacao_2024.json` têm denominadores próprios: {linhas_2024} linhas probabilísticas e {gps_2024} GPs de ranking, contra {linhas_2025} e {gps_2025} em 2025. São temporadas diferentes. Esta comparação não afirma significância estatística, causalidade ou desempenho futuro.

As fontes históricas podem conter revisões posteriores ao corte. Este estudo continua retrospectivo e não comprova que uma previsão foi emitida antes de cada corrida.
""".format(
        linhas=cobertura['linhas_teste'], elegiveis=cobertura['linhas_elegiveis'],
        inelegiveis=cobertura['linhas_inelegiveis'], conhecidos=cobertura['linhas_com_alvo_conhecido'],
        desconhecidos=cobertura['linhas_alvo_desconhecido'], probabilisticas=prob['linhas_avaliaveis'],
        gps=cobertura['gps_total'], gps_avaliaveis=cobertura['gps_avaliaveis_ranking'],
        ll_modelo=n(prob['modelo']['log_loss']), brier_modelo=n(prob['modelo']['brier']),
        ll_constante=n(prob['constante']['log_loss']), brier_constante=n(prob['constante']['brier']),
        comparacao_brier=_resultado_menor_melhor(prob['modelo']['brier'], prob['constante']['brier']),
        gps_modelo=ranking['corridas_avaliaveis'], media_modelo=n(ranking['media_integrantes_corretos']),
        top3_modelo=n(ranking['proporcao_3_corretos']), gps_classificacao=classificacao['corridas_avaliaveis'],
        media_classificacao=n(classificacao['media_integrantes_corretos']),
        top3_classificacao=n(classificacao['proporcao_3_corretos']),
        linhas_2024=comparacao['denominadores_separados']['2024_linhas_probabilisticas'],
        gps_2024=comparacao['denominadores_separados']['2024_gps_ranking'],
        linhas_2025=comparacao['denominadores_separados']['2025_linhas_probabilisticas'],
        gps_2025=comparacao['denominadores_separados']['2025_gps_ranking'],
    )


def _dentro(caminho, raiz):
    try:
        caminho.relative_to(raiz)
        return True
    except ValueError:
        return False


def _validar_destino(relatorios, contexto, teste):
    destino = Path(relatorios).resolve()
    protegidos = [Path(teste).resolve(), contexto['caminhos']['esquema'].resolve(),
                  contexto['caminhos']['modelo'].resolve(), contexto['caminhos']['metadados'].resolve(),
                  contexto['caminhos']['plano_avaliacao'].resolve(), contexto['caminhos']['plano_original'].resolve(),
                  contexto['caminhos']['metricas_2024'].resolve()]
    for protegido in protegidos:
        if destino == protegido or _dentro(destino, protegido.parent):
            raise ValueError('Destino de avaliação não pode sobrescrever fonte, plano ou artefato v1.')
    return destino


def _publicar_lote(destino, saidas):
    if set(saidas) != set(NOMES_SAIDAS):
        raise ValueError('Conjunto de saídas da avaliação incompleto.')
    if destino.exists():
        if not destino.is_dir():
            raise FileExistsError('Destino de relatórios não é uma pasta: {}'.format(destino))
        existentes = {caminho.name for caminho in destino.iterdir() if caminho.is_file()}
        if existentes != set(saidas) or any((destino / nome).read_bytes() != conteudo for nome, conteudo in saidas.items()):
            raise FileExistsError('Destino existente diverge e foi preservado: {}'.format(destino))
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = Path(tempfile.mkdtemp(prefix='.avaliacao_final_v1-', dir=str(destino.parent)))
    try:
        for nome, conteudo in saidas.items():
            (temporario / nome).write_bytes(conteudo)
        if destino.exists():
            raise FileExistsError('Destino passou a existir durante a publicação: {}'.format(destino))
        os.replace(str(temporario), str(destino))
    except Exception:
        if temporario.exists():
            for caminho in temporario.iterdir():
                caminho.unlink()
            temporario.rmdir()
        raise


def executar(teste='data/preparado/teste_final_reservado.csv', esquema='data/preparado/colunas.json',
             modelo='models/modelo_v1/modelo.joblib', metadados='models/modelo_v1/metadados.json',
             plano_avaliacao='docs/avaliacao_final_v1.md', plano_original='docs/experimento_modelo_v1.md',
             metricas_2024='reports/modelo_v1/metricas.json', relatorios='reports/avaliacao_final_v1'):
    """Executa a avaliação congelada; só lê o teste depois da verificação de hashes."""
    treinador = Path(__file__).with_name('treinar_modelo_v1.py')
    contexto = _verificar_integridade(plano_avaliacao, plano_original, modelo, metadados, treinador,
                                      esquema, metricas_2024)
    destino = _validar_destino(relatorios, contexto, teste)
    linhas_brutas, teste_bytes = _ler_teste(teste, contexto['esquema'])
    pre_corrida = validar_linhas_teste(linhas_brutas, contexto['esquema'])
    previsoes = prever_teste(contexto['pipeline'], contexto['metadados']['constante_treino'],
                              pre_corrida, contexto['esquema'])
    avaliacao_pilotos = extrair_alvos(linhas_brutas, previsoes, contexto['esquema'])
    metricas, corridas, calibracao = avaliar_teste(avaliacao_pilotos)
    _confirmar_congelamento(contexto)
    comparacao = _comparacao_2024(metricas, contexto['metricas_2024'])
    campos_pre = ['temporada', 'rodada', 'piloto_id', 'corrida', 'data_corrida', 'elegivel_previsao',
                  'motivos_inelegibilidade', 'probabilidade_modelo', 'probabilidade_constante',
                  'ranking_modelo', 'favorito_modelo', 'ranking_classificacao', 'favorito_classificacao',
                  'empates_modelo', 'empates_classificacao']
    campos_final = campos_pre + ['alvo_conhecido', 'podio']
    campos_cobertura = ['temporada', 'rodada', 'corrida', 'piloto_id', 'elegivel_previsao',
                        'motivos_inelegibilidade', 'alvo_conhecido']
    campos_cobertura_gps = ['temporada', 'rodada', 'corrida', 'participantes_preparados', 'elegiveis',
                            'alvos_conhecidos', 'podios_conhecidos', 'avaliavel_ranking',
                            'motivos_nao_avaliavel']
    campos_corridas = ['temporada', 'rodada', 'corrida', 'participantes_preparados', 'elegiveis',
                       'alvos_conhecidos', 'podios_conhecidos', 'avaliavel_ranking',
                       'motivos_nao_avaliavel', 'favoritos_modelo', 'favoritos_classificacao',
                       'podio_observado', 'acertos_modelo', 'acertos_classificacao']
    campos_calibracao = ['metodo', 'faixa', 'limite_inferior', 'limite_superior', 'contagem',
                         'media_prevista', 'frequencia_observada']
    saidas_sem_manifesto = {
        'previsoes_pre_corrida.csv': _csv_bytes(previsoes, campos_pre),
        'avaliacao_por_piloto.csv': _csv_bytes(avaliacao_pilotos, campos_final),
        'cobertura_pilotos.csv': _csv_bytes(_cobertura_pilotos(avaliacao_pilotos), campos_cobertura),
        'cobertura_gps.csv': _csv_bytes(corridas, campos_cobertura_gps),
        'avaliacao_corridas.csv': _csv_bytes(corridas, campos_corridas),
        'metricas.json': _json_bytes(metricas),
        'calibracao.csv': _csv_bytes(calibracao, campos_calibracao),
        'calibracao.svg': _svg_calibracao_2025(calibracao).encode('utf-8'),
        'comparacao_2024.json': _json_bytes(comparacao),
        'relatorio.md': _relatorio(metricas, comparacao).encode('utf-8'),
    }
    hashes = dict(contexto['hashes'])
    hashes['teste_final_reservado.csv'] = _sha256_bytes(teste_bytes)
    hashes['script_executado'] = _sha256_bytes(_ler_bytes(Path(__file__)))
    manifesto = {
        'versao': 'avaliacao_final_v1', 'status_2025': 'avaliado_para_modelo_v1',
        'registro_utc_plano_previo': '2026-10-18T06:43:57.198266+00:00',
        'constante_treino': CONSTANTE_CONGELADA, 'hashes_entradas': hashes,
        'hashes_saidas': {nome: _sha256_bytes(conteudo) for nome, conteudo in sorted(saidas_sem_manifesto.items())},
    }
    saidas = dict(saidas_sem_manifesto)
    saidas['manifesto.json'] = _json_bytes(manifesto)
    _publicar_lote(destino, saidas)
    return metricas


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--teste', default='data/preparado/teste_final_reservado.csv',
                        help='CSV de teste, com nome literal teste_final_reservado.csv.')
    parser.add_argument('--esquema', default='data/preparado/colunas.json')
    parser.add_argument('--modelo', default='models/modelo_v1/modelo.joblib')
    parser.add_argument('--metadados', default='models/modelo_v1/metadados.json')
    parser.add_argument('--plano-avaliacao', default='docs/avaliacao_final_v1.md')
    parser.add_argument('--plano-original', default='docs/experimento_modelo_v1.md')
    parser.add_argument('--metricas-2024', default='reports/modelo_v1/metricas.json')
    parser.add_argument('--relatorios', default='reports/avaliacao_final_v1')
    argumentos = parser.parse_args(argv)
    metricas = executar(teste=argumentos.teste, esquema=argumentos.esquema, modelo=argumentos.modelo,
                        metadados=argumentos.metadados, plano_avaliacao=argumentos.plano_avaliacao,
                        plano_original=argumentos.plano_original, metricas_2024=argumentos.metricas_2024,
                        relatorios=argumentos.relatorios)
    print('Avaliação concluída: {} linhas probabilísticas avaliáveis; {} GPs avaliáveis para ranking.'.format(
        metricas['probabilisticas']['linhas_avaliaveis'], metricas['cobertura']['gps_avaliaveis_ranking']))


if __name__ == '__main__':
    main()
