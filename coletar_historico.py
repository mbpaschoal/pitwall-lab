"""Jolpica 2021–2025: JSON original, paginação por registros e prova offline.

Não usa sprint nem altera os coletores das etapas anteriores.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from coletar_resultados import RespostaInvalida, exigir_campo, exigir_inteiro, salvar_preservando

RAIZ = Path(__file__).resolve().parent
BASE_API = 'https://api.jolpi.ca/ergast/f1'
USER_AGENT = 'PitwallLab/0.3.0 Python/{}'.format(sys.version.split()[0])
ULTIMA_REQUISICAO = None
INTERVALO_SEGUNDOS = 8.0
ENDPOINTS = {'calendario': '', 'resultados': 'results/', 'classificacao': 'qualifying/'}
CHAVES = {'resultados': 'Results', 'classificacao': 'QualifyingResults'}


def validar_pagina(dados, endpoint, temporada, offset, total_esperado=None):
    """Campos opcionais são preservados; número de registros não é fixado em 20."""
    temporada = str(temporada)
    if endpoint not in ENDPOINTS:
        raise ValueError('Endpoint desconhecido: ' + endpoint)
    if not isinstance(dados, dict):
        raise RespostaInvalida('JSON deve ser objeto')
    mr = exigir_campo(dados, 'MRData', dict, 'JSON')
    total = exigir_inteiro(mr, 'total', 'MRData', minimo=0)
    limite = exigir_inteiro(mr, 'limit', 'MRData')
    recebido = exigir_inteiro(mr, 'offset', 'MRData', minimo=0)
    if recebido != offset or limite > 100 or offset > total:
        raise RespostaInvalida('Paginação inválida: offset/limit/total')
    if total_esperado is not None and total != total_esperado:
        raise RespostaInvalida('O total mudou entre páginas')
    tabela = exigir_campo(mr, 'RaceTable', dict, 'MRData')
    if exigir_campo(tabela, 'season', str, 'RaceTable') != temporada:
        raise RespostaInvalida('Temporada diferente da solicitada')
    corridas = exigir_campo(tabela, 'Races', list, 'RaceTable')
    quantidade = 0
    for corrida in corridas:
        if not isinstance(corrida, dict):
            raise RespostaInvalida('Corrida deve ser objeto')
        if exigir_campo(corrida, 'season', str, 'Race') != temporada:
            raise RespostaInvalida('Temporada incorreta em corrida')
        exigir_inteiro(corrida, 'round', 'Race')
        exigir_campo(corrida, 'raceName', str, 'Race')
        data = exigir_campo(corrida, 'date', str, 'Race')
        try:
            if date.fromisoformat(data).year != int(temporada):
                raise ValueError('ano diferente')
        except ValueError as erro:
            raise RespostaInvalida('Data de corrida inválida') from erro
        circuito = exigir_campo(corrida, 'Circuit', dict, 'Race')
        for campo in ('circuitId', 'circuitName'):
            exigir_campo(circuito, campo, str, 'Circuit')
        if 'time' in corrida and not isinstance(corrida['time'], str):
            raise RespostaInvalida('Race.time: deve ser texto')
        for sessao in ('FirstPractice', 'SecondPractice', 'ThirdPractice', 'Qualifying', 'Sprint', 'SprintQualifying', 'SprintShootout'):
            if sessao in corrida:
                bloco = exigir_campo(corrida, sessao, dict, 'Race')
                for campo in ('date', 'time'):
                    if campo in bloco and not isinstance(bloco[campo], str):
                        raise RespostaInvalida('{}.{}: deve ser texto'.format(sessao, campo))
        if endpoint == 'calendario':
            quantidade += 1
            continue
        itens = exigir_campo(corrida, CHAVES[endpoint], list, 'Race')
        if not itens:
            raise RespostaInvalida('Lista de resultados vazia em corrida')
        quantidade += len(itens)
        pilotos_pagina, posicoes_pagina = set(), {}
        for r in itens:
            if not isinstance(r, dict):
                raise RespostaInvalida('Resultado deve ser objeto')
            piloto = exigir_campo(r, 'Driver', dict, 'Result')
            for campo in ('driverId', 'givenName', 'familyName'):
                exigir_campo(piloto, campo, str, 'Driver')
            equipe = exigir_campo(r, 'Constructor', dict, 'Result')
            for campo in ('constructorId', 'name'):
                exigir_campo(equipe, campo, str, 'Constructor')
            if piloto['driverId'] in pilotos_pagina:
                raise RespostaInvalida('Piloto duplicado na página')
            pilotos_pagina.add(piloto['driverId'])
            if 'position' in r:
                posicao = exigir_inteiro(r, 'position', 'Result')
                if posicao in posicoes_pagina and endpoint == 'resultados':
                    raise RespostaInvalida('Posição duplicada na página: {}/{} posição {} pilotos {} e {}'.format(
                        temporada, corrida['round'], posicao, posicoes_pagina[posicao], piloto['driverId']))
                posicoes_pagina[posicao] = piloto['driverId']
            if endpoint == 'classificacao':
                if 'position' in r:
                    exigir_inteiro(r, 'position', 'QualifyingResult')
                for campo in ('Q1', 'Q2', 'Q3', 'number'):
                    if campo in r and not isinstance(r[campo], str):
                        raise RespostaInvalida('QualifyingResult.{}: deve ser texto (vazio é preservado)'.format(campo))
            else:
                exigir_inteiro(r, 'grid', 'Result', minimo=0)
                exigir_inteiro(r, 'position', 'Result')
                exigir_campo(r, 'status', str, 'Result')
                pontos = exigir_campo(r, 'points', str, 'Result')
                try:
                    valor = Decimal(pontos)
                    if not valor.is_finite() or valor < 0:
                        raise InvalidOperation
                except InvalidOperation as erro:
                    raise RespostaInvalida('Pontos inválidos') from erro
    if quantidade != min(limite, total - offset):
        raise RespostaInvalida('Página incompleta: quantidade diferente de total/limit/offset')
    return total, quantidade


def montar_temporada(calendario, resultados, classificacao, totais):
    """Une fragmentos sem perder campos opcionais nem esconder ausências."""
    esperadas = {(r['season'], r['round']): r for r in calendario}
    if len(esperadas) != len(calendario) or len(calendario) != totais['calendario'] or not calendario:
        raise RespostaInvalida('Calendário incompleto ou rodada duplicada')
    rodadas = sorted(int(r['round']) for r in calendario)
    if rodadas != list(range(1, len(calendario) + 1)):
        raise RespostaInvalida('Calendário com rodadas ausentes')
    base: dict = {'calendario': copy.deepcopy(sorted(calendario, key=lambda r: int(r['round'])))}
    qualidade = {'completa': True, 'temporada': calendario[0]['season'],
                 'corridas_esperadas': len(calendario), 'totais': dict(totais)}
    for endpoint, fragmentos in (('resultados', resultados), ('classificacao', classificacao)):
        campo = CHAVES[endpoint]
        unidas, vistos, posicoes = {}, {}, {}
        for corrida in fragmentos:
            chave = (corrida['season'], corrida['round'])
            if chave not in esperadas:
                raise RespostaInvalida('Corrida ausente do calendário: {}'.format(chave))
            prevista = esperadas[chave]
            for atributo in ('raceName', 'date'):
                if corrida[atributo] != prevista[atributo]:
                    raise RespostaInvalida('Metadados incoerentes: {} {}'.format(chave, atributo))
            for atributo in ('circuitId', 'circuitName'):
                if corrida['Circuit'][atributo] != prevista['Circuit'][atributo]:
                    raise RespostaInvalida('Circuito incoerente: {}'.format(chave))
            meta = {k: v for k, v in corrida.items() if k != campo}
            if chave not in unidas:
                unidas[chave] = copy.deepcopy(meta)
                unidas[chave][campo] = []
                vistos[chave], posicoes[chave] = set(), set()
            elif {k: v for k, v in unidas[chave].items() if k != campo} != meta:
                raise RespostaInvalida('Metadados incoerentes entre fragmentos: {}'.format(chave))
            for r in corrida[campo]:
                piloto = r['Driver']['driverId']
                if piloto in vistos[chave]:
                    raise RespostaInvalida('Piloto duplicado: {} {}'.format(chave, piloto))
                vistos[chave].add(piloto)
                if 'position' in r:
                    posicao = int(r['position'])
                    if posicao in posicoes[chave] and endpoint == 'resultados':
                        raise RespostaInvalida('Posição duplicada: {}'.format(chave))
                    posicoes[chave].add(posicao)
                unidas[chave][campo].append(copy.deepcopy(r))
        if endpoint == 'resultados' and set(unidas) != set(esperadas):
            raise RespostaInvalida('Resultados incompletos: falta corrida do calendário')
        quantidade = sum(len(r[campo]) for r in unidas.values())
        if quantidade != totais[endpoint]:
            raise RespostaInvalida('Total de registros incoerente: ' + endpoint)
        base[endpoint] = sorted(unidas.values(), key=lambda r: int(r['round']))
        qualidade['corridas_' + endpoint] = len(unidas)
        qualidade['registros_' + endpoint] = quantidade
    qualidade['rodadas_sem_classificacao'] = sorted(
        set(r['round'] for r in calendario) - set(r['round'] for r in base['classificacao']), key=int)
    qualidade['classificacao_sem_posicao'] = [
        {'rodada': r['round'], 'piloto_id': q['Driver']['driverId']}
        for r in base['classificacao'] for q in r['QualifyingResults'] if 'position' not in q]
    qualidade['registros_por_rodada'] = [
        {'rodada': r['round'], 'resultados': len(r['Results']),
         'classificacao': next((len(q['QualifyingResults']) for q in base['classificacao'] if q['round'] == r['round']), 0)}
        for r in base['resultados']]
    repetidas = []
    for corrida in base['classificacao']:
        por_posicao = {}
        for r in corrida['QualifyingResults']:
            if 'position' in r:
                por_posicao.setdefault(r['position'], []).append(r['Driver']['driverId'])
        for posicao in sorted(por_posicao, key=int):
            if len(por_posicao[posicao]) > 1:
                repetidas.append({'temporada': corrida['season'], 'rodada': corrida['round'],
                                  'posicao': posicao, 'pilotos': por_posicao[posicao]})
    # Campo opcional para preservar manifestos já válidos sem ocorrências.
    if repetidas:
        qualidade['posicoes_classificacao_repetidas'] = repetidas
    base['qualidade'] = qualidade
    base['proveniencia'] = []
    return base


def texto_json(dados):
    return json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + '\n'


def salvar_lote(saidas):
    """Preflight de todos os destinos; escrita UTF-8 preserva bytes originais."""
    for caminho, conteudo in saidas:
        if caminho.exists() and caminho.read_bytes() != conteudo:
            raise FileExistsError('Arquivo existente diferente: {}. Faça backup; nada será sobrescrito.'.format(caminho))
    for caminho, conteudo in saidas:
        if not caminho.exists():
            salvar_preservando(caminho, conteudo.decode('utf-8'))


def validar_proveniencia(prov, endpoint, temporada, offset, digest):
    """Exige identificação e instante explícito (ou desconhecida), nunca mtime."""
    nome = '{}_offset_{:04d}.json'.format(endpoint, offset)
    if not isinstance(prov, dict):
        raise RespostaInvalida('Proveniência deve ser objeto')
    for campo in ('url_consultada', 'url_real', 'obtido_em_utc', 'sha256'):
        exigir_campo(prov, campo, str, 'proveniência')
    if (prov.get('arquivo') != 'raw/' + nome or prov.get('sha256') != digest
            or prov.get('endpoint') != endpoint or prov.get('temporada') != temporada
            or prov.get('parametros') != {'limit': 100, 'offset': offset}
            or not isinstance(prov.get('url_reconstruida'), bool)):
        raise RespostaInvalida('Metadados de proveniência incoerentes')
    obtido = prov['obtido_em_utc']
    if obtido != 'desconhecida':
        try:
            if not obtido.endswith('Z'):
                raise ValueError('UTC Z obrigatório')
            datetime.fromisoformat(obtido[:-1] + '+00:00')
        except ValueError as erro:
            raise RespostaInvalida('Instante de proveniência inválido') from erro


def obter_pagina(endpoint, temporada, offset, pasta, total_esperado=None, somente_cache=False):
    """Rede/cache/legado passam pela mesma validação, antes de qualquer escrita."""
    global ULTIMA_REQUISICAO
    temporada, pasta = str(temporada), Path(pasta)
    nome = '{}_offset_{:04d}.json'.format(endpoint, offset)
    cache = pasta / 'raw' / nome
    metacache = pasta / 'proveniencia' / nome
    url = BASE_API + '/{}/{}?limit=100&offset={}'.format(temporada, ENDPOINTS[endpoint], offset)
    url_real, obtido = url, 'desconhecida'
    legado = RAIZ / 'data/temporada_2024/raw' / nome
    origem = None
    existe = cache.exists()
    if existe:
        conteudo = cache.read_bytes()
    elif temporada == '2024' and endpoint != 'classificacao' and legado.exists():
        conteudo = legado.read_bytes()
        origem = str(legado.relative_to(RAIZ))
    else:
        if somente_cache:
            raise ValueError('Falta cache de página: {}'.format(cache))
        if ULTIMA_REQUISICAO is not None:
            time.sleep(max(0, INTERVALO_SEGUNDOS - (time.monotonic() - ULTIMA_REQUISICAO)))
        print('Consultando: ' + url, flush=True)
        ULTIMA_REQUISICAO = time.monotonic()
        try:
            with urlopen(Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}), timeout=30) as resposta:
                conteudo = resposta.read()
                url_real = resposta.geturl() if hasattr(resposta, 'geturl') else url
        except HTTPError as erro:
            if erro.code == 429:
                raise ValueError('HTTP 429. Retry-After: {}. Aguarde; sem repetição automática.'.format(erro.headers.get('Retry-After', 'não informado'))) from erro
            raise ValueError('HTTP {} na consulta {}'.format(erro.code, url)) from erro
        obtido = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    try:
        dados = json.loads(conteudo.decode('utf-8'))
        validar_pagina(dados, endpoint, temporada, offset, total_esperado)
        digest = hashlib.sha256(conteudo).hexdigest()
        if metacache.exists():
            prov = json.loads(metacache.read_bytes())
            if prov.get('sha256') != digest or prov.get('arquivo') != 'raw/' + nome:
                raise RespostaInvalida('SHA256 ou arquivo não confere com proveniência')
        else:
            desconhecida = existe or origem is not None
            prov = {'arquivo': 'raw/' + nome, 'endpoint': endpoint,
                    'temporada': temporada, 'parametros': {'limit': 100, 'offset': offset},
                    'sha256': digest, 'url_consultada': url,
                    'url_real': url if desconhecida else url_real,
                    'url_reconstruida': desconhecida,
                    'obtido_em_utc': 'desconhecida' if desconhecida else obtido}
            if origem is not None:
                prov['origem_arquivo_legado'] = origem
        validar_proveniencia(prov, endpoint, temporada, offset, digest)
    except (ValueError, UnicodeDecodeError, TypeError, AttributeError) as erro:
        local = 'Cache inválido' if existe or origem else 'Resposta inválida'
        raise RespostaInvalida('{}: {}. {}. Arquivo preservado; faça backup explícito. Nenhuma resposta inválida foi gravada.'.format(local, cache, erro)) from erro
    saidas = [(cache, conteudo)]
    if not metacache.exists():
        saidas.append((metacache, texto_json(prov).encode('utf-8')))
    salvar_lote(saidas)
    print('Página validada: {}/{}'.format(temporada, nome), flush=True)
    return dados, prov


def validar_temporada(temporada):
    temporada = str(temporada)
    if temporada not in ('2021', '2022', '2023', '2024', '2025'):
        raise ValueError('Temporada deve ser uma de 2021, 2022, 2023, 2024, 2025')
    return temporada


def coletar_temporada(temporada, raiz_dados=RAIZ / 'data/historico', somente_cache=False):
    """Coleta uma temporada e escreve o comprovante de integridade por último."""
    temporada = validar_temporada(temporada)
    pasta = Path(raiz_dados) / temporada
    if (pasta / 'verificacao.json').exists():
        return carregar_temporada(temporada, raiz_dados)
    fragmentos, totais, proveniencia = {}, {}, []
    for endpoint in ENDPOINTS:
        offset, total, corridas = 0, None, []
        while total is None or offset < total:
            dados, prov = obter_pagina(endpoint, temporada, offset, pasta, total, somente_cache)
            total, quantidade = validar_pagina(dados, endpoint, temporada, offset, total)
            corridas.extend(dados['MRData']['RaceTable']['Races'])
            proveniencia.append(prov)
            offset += quantidade
        fragmentos[endpoint], totais[endpoint] = corridas, total
    base = montar_temporada(fragmentos['calendario'], fragmentos['resultados'], fragmentos['classificacao'], totais)
    base['proveniencia'] = proveniencia
    hashes_meta = {'proveniencia/' + Path(p['arquivo']).name:
                   hashlib.sha256((pasta / 'proveniencia' / Path(p['arquivo']).name).read_bytes()).hexdigest()
                   for p in proveniencia}
    manifesto = {'versao': 1, 'temporada': temporada, 'proveniencia': proveniencia,
                 'proveniencia_sha256': hashes_meta}
    conteudo = texto_json(manifesto).encode('utf-8')
    prova = dict(base['qualidade'], manifesto_sha256=hashlib.sha256(conteudo).hexdigest())
    salvar_lote([(pasta / 'manifesto.json', conteudo),
                 (pasta / 'verificacao.json', texto_json(prova).encode('utf-8'))])
    # Leitura independente do que foi escrito: integridade e lista exata de arquivos.
    return carregar_temporada(temporada, raiz_dados)


def carregar_temporada(temporada, raiz_dados=RAIZ / 'data/historico'):
    """Nunca faz rede ou escreve: verifica hashes, filelist, totais e joins offline.

    Retorna calendario/resultados/classificacao como listas de Race objects unidos
    por season/round, qualidade como dict e proveniencia como lista por página.
    """
    temporada = validar_temporada(temporada)
    pasta = Path(raiz_dados) / temporada
    try:
        prova = json.loads((pasta / 'verificacao.json').read_bytes())
        conteudo = (pasta / 'manifesto.json').read_bytes()
        manifesto = json.loads(conteudo)
        if not prova.get('completa') or prova.get('manifesto_sha256') != hashlib.sha256(conteudo).hexdigest():
            raise RespostaInvalida('Comprovante incompleto ou SHA256 do manifesto diferente')
        if manifesto.get('temporada') != temporada or manifesto.get('versao') != 1:
            raise RespostaInvalida('Manifesto de temporada/versão incorreta')
        proveniencia = manifesto['proveniencia']
        if not isinstance(proveniencia, list) or not proveniencia:
            raise RespostaInvalida('Proveniência ausente')
        esperados = {p['arquivo'] for p in proveniencia}
        reais = {str(p.relative_to(pasta)) for p in (pasta / 'raw').rglob('*') if p.is_file()}
        metas = {str(p.relative_to(pasta / 'proveniencia')) for p in (pasta / 'proveniencia').rglob('*') if p.is_file()}
        if len(esperados) != len(proveniencia) or reais != esperados or metas != {Path(p).name for p in esperados}:
            raise RespostaInvalida('Lista de arquivos difere do manifesto: página ausente, extra ou duplicada')
        hashes_meta = {'proveniencia/' + nome:
                       hashlib.sha256((pasta / 'proveniencia' / nome).read_bytes()).hexdigest()
                       for nome in metas}
        if hashes_meta != manifesto.get('proveniencia_sha256'):
            raise RespostaInvalida('SHA256 dos arquivos de proveniência diferente')
        fragmentos, totais = {}, {}
        for endpoint in ENDPOINTS:
            paginas = [p for p in proveniencia if p['endpoint'] == endpoint]
            if not paginas:
                raise RespostaInvalida('Falta endpoint no manifesto: ' + endpoint)
            offset, total, corridas = 0, None, []
            for prov in paginas:
                nome = '{}_offset_{:04d}.json'.format(endpoint, offset)
                if prov['arquivo'] != 'raw/' + nome or prov['temporada'] != temporada or prov['parametros'] != {'limit': 100, 'offset': offset}:
                    raise RespostaInvalida('Metadados de página/offset incoerentes')
                raw = (pasta / prov['arquivo']).read_bytes()
                validar_proveniencia(prov, endpoint, temporada, offset, hashlib.sha256(raw).hexdigest())
                if hashlib.sha256(raw).hexdigest() != prov['sha256']:
                    raise RespostaInvalida('SHA256 da página diferente: ' + prov['arquivo'])
                if json.loads((pasta / 'proveniencia' / nome).read_bytes()) != prov:
                    raise RespostaInvalida('Proveniência individual difere do manifesto')
                dados = json.loads(raw.decode('utf-8'))
                total, quantidade = validar_pagina(dados, endpoint, temporada, offset, total)
                corridas.extend(dados['MRData']['RaceTable']['Races'])
                offset += quantidade
            if offset != total:
                raise RespostaInvalida('Paginação incompleta: ' + endpoint)
            fragmentos[endpoint], totais[endpoint] = corridas, total
        if any(p['endpoint'] not in ENDPOINTS for p in proveniencia):
            raise RespostaInvalida('Endpoint extra no manifesto')
        base = montar_temporada(fragmentos['calendario'], fragmentos['resultados'], fragmentos['classificacao'], totais)
        esperada = dict(base['qualidade'], manifesto_sha256=hashlib.sha256(conteudo).hexdigest())
        if prova != esperada:
            raise RespostaInvalida('Comprovante difere da qualidade recalculada')
        base['proveniencia'] = proveniencia
        return base
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as erro:
        raise RespostaInvalida('Histórico inválido em {}: {}. Arquivos preservados; faça backup explícito antes de corrigir.'.format(pasta, erro)) from erro


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temporadas', nargs='+', choices=['2021', '2022', '2023', '2024', '2025'], default=['2021', '2022', '2023', '2024', '2025'])
    parser.add_argument('--somente-cache', action='store_true')
    parser.add_argument('--pasta-dados', type=Path, default=RAIZ / 'data/historico')
    args = parser.parse_args(argv)
    inicio = time.monotonic()
    try:
        for temporada in args.temporadas:
            base = coletar_temporada(temporada, args.pasta_dados, somente_cache=args.somente_cache)
            q = base['qualidade']
            if q.get('posicoes_classificacao_repetidas'):
                print('AVISO {}: posições de classificação repetidas preservadas: {}'.format(
                    temporada, q['posicoes_classificacao_repetidas']), flush=True)
            print('ÍNTEGRA {}: {} corridas; {} resultados; {} classificações; rodadas sem classificação: {}'.format(
                temporada, q['corridas_esperadas'], q['registros_resultados'], q['registros_classificacao'], q['rodadas_sem_classificacao']), flush=True)
    except (OSError, ValueError) as erro:
        print('Falha na coleta histórica: {}. Nenhum dado inventado; arquivos anteriores preservados.'.format(erro), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Coleta interrompida. Páginas válidas podem ser reutilizadas.', file=sys.stderr)
        return 130
    print('Duração: {:.1f}s'.format(time.monotonic() - inicio), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
