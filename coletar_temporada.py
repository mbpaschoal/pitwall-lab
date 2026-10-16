"""Coleta paginada das corridas principais de 2024; somente biblioteca padrão."""
from datetime import date
from decimal import Decimal, InvalidOperation
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from coletar_resultados import RespostaInvalida, exigir_campo, exigir_inteiro, salvar_preservando

TEMPORADA = '2024'
RAIZ = Path(__file__).resolve().parent
PASTA = RAIZ / 'data/temporada_2024'
BASE_API = 'https://api.jolpi.ca/ergast/f1'
USER_AGENT = 'PitwallLab/0.2.0 Python/{} (educational portfolio; urllib)'.format(sys.version.split()[0])
INTERVALO_SEGUNDOS = 8.0
ULTIMA_REQUISICAO = None
COLUNAS = ['temporada', 'rodada', 'corrida', 'data_corrida', 'circuito_id', 'circuito',
           'piloto_id', 'piloto', 'equipe_id', 'equipe', 'posicao_largada',
           'posicao_final', 'status', 'pontos', 'podio']


def validar_pagina(dados, endpoint, offset, total_esperado=None):
    """Valida uma parte da resposta, sem confundi-la com a base completa."""
    if endpoint not in ('calendario', 'resultados'):
        raise ValueError('Endpoint desconhecido: {}'.format(endpoint))
    if not isinstance(dados, dict):
        raise RespostaInvalida('JSON deve ser um objeto')
    mr = exigir_campo(dados, 'MRData', dict, 'JSON')
    total = exigir_inteiro(mr, 'total', 'MRData')
    limite = exigir_inteiro(mr, 'limit', 'MRData')
    recebido = exigir_inteiro(mr, 'offset', 'MRData', minimo=0)
    if recebido != offset or limite > 100:
        raise RespostaInvalida('Paginação inválida: offset inesperado ou limite acima de 100')
    if total_esperado is not None and total != total_esperado:
        raise RespostaInvalida('O total mudou entre páginas; não é seguro declarar a base completa')
    tabela = exigir_campo(mr, 'RaceTable', dict, 'MRData')
    if exigir_campo(tabela, 'season', str, 'RaceTable') != TEMPORADA:
        raise RespostaInvalida('Temporada diferente de 2024')
    corridas = exigir_campo(tabela, 'Races', list, 'RaceTable')
    quantidade = 0
    for indice, corrida in enumerate(corridas):
        contexto = 'Races[{}]'.format(indice)
        if not isinstance(corrida, dict):
            raise RespostaInvalida(contexto + ': deve ser um objeto')
        if exigir_campo(corrida, 'season', str, contexto) != TEMPORADA:
            raise RespostaInvalida(contexto + ': temporada incorreta')
        exigir_inteiro(corrida, 'round', contexto)
        exigir_campo(corrida, 'raceName', str, contexto)
        data = exigir_campo(corrida, 'date', str, contexto)
        try:
            if date.fromisoformat(data).year != int(TEMPORADA):
                raise ValueError('ano incorreto')
        except ValueError as erro:
            raise RespostaInvalida(contexto + '.date: data ISO de 2024 esperada') from erro
        circuito = exigir_campo(corrida, 'Circuit', dict, contexto)
        exigir_campo(circuito, 'circuitId', str, contexto + '.Circuit')
        exigir_campo(circuito, 'circuitName', str, contexto + '.Circuit')
        if endpoint == 'calendario':
            quantidade += 1
            continue
        resultados = exigir_campo(corrida, 'Results', list, contexto)
        if not resultados:
            raise RespostaInvalida(contexto + '.Results: lista vazia')
        quantidade += len(resultados)
        for numero, resultado in enumerate(resultados):
            caminho = contexto + '.Results[{}]'.format(numero)
            if not isinstance(resultado, dict):
                raise RespostaInvalida(caminho + ': deve ser um objeto')
            piloto = exigir_campo(resultado, 'Driver', dict, caminho)
            for campo in ('driverId', 'givenName', 'familyName'):
                exigir_campo(piloto, campo, str, caminho + '.Driver')
            equipe = exigir_campo(resultado, 'Constructor', dict, caminho)
            for campo in ('constructorId', 'name'):
                exigir_campo(equipe, campo, str, caminho + '.Constructor')
            exigir_inteiro(resultado, 'grid', caminho, minimo=0)
            exigir_inteiro(resultado, 'position', caminho)
            exigir_campo(resultado, 'status', str, caminho)
            pontos = exigir_campo(resultado, 'points', str, caminho)
            try:
                valor = Decimal(pontos)
            except InvalidOperation as erro:
                raise RespostaInvalida(caminho + '.points: número decimal esperado') from erro
            if not valor.is_finite() or valor < 0:
                raise RespostaInvalida(caminho + '.points: valor inválido')
    if quantidade <= 0 or quantidade != min(limite, total - offset):
        raise RespostaInvalida('Página incompleta: quantidade incompatível com total, limit e offset')
    return total, quantidade


def obter_pagina(endpoint, offset, pasta, total_esperado=None, somente_cache=False):
    """Preserva a resposta original e aplica as mesmas regras na rede e no cache."""
    global ULTIMA_REQUISICAO
    cache = pasta / ('{}_offset_{:04d}.json'.format(endpoint, offset))
    rota = '/2024/' if endpoint == 'calendario' else '/2024/results/'
    url = BASE_API + rota + '?limit=100&offset={}'.format(offset)
    existe = cache.exists()
    if existe:
        conteudo = cache.read_bytes()
    else:
        if somente_cache:
            raise ValueError('Falta cache de página: {}. Execute coletar_temporada.py primeiro.'.format(cache))
        if ULTIMA_REQUISICAO is not None:
            time.sleep(max(0, INTERVALO_SEGUNDOS - (time.monotonic() - ULTIMA_REQUISICAO)))
        print('Consultando: {}'.format(url), flush=True)
        ULTIMA_REQUISICAO = time.monotonic()
        try:
            with urlopen(Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}), timeout=30) as resposta:
                conteudo = resposta.read()
        except HTTPError as erro:
            if erro.code == 429:
                raise ValueError('HTTP 429. Retry-After: {}. Aguarde o prazo; não há repetição automática.'.format(
                    erro.headers.get('Retry-After', 'não informado'),
                )) from erro
            raise ValueError('HTTP {} na consulta {}'.format(erro.code, url)) from erro
    try:
        dados = json.loads(conteudo.decode('utf-8'))
        validar_pagina(dados, endpoint, offset, total_esperado)
    except (UnicodeDecodeError, json.JSONDecodeError, RespostaInvalida) as erro:
        if existe:
            raise RespostaInvalida('Cache inválido: {}. {}. Preserve-o em backup fora do projeto e execute novamente; nenhum arquivo foi apagado.'.format(cache, erro)) from erro
        raise RespostaInvalida('Resposta inválida de {}: {}. A página não foi gravada no cache.'.format(url, erro)) from erro
    if not existe:
        salvar_preservando(cache, conteudo.decode('utf-8'))
    print('Página validada: {}'.format(cache.name), flush=True)
    return dados


def coletar_paginas(endpoint, pasta, somente_cache=False):
    """O offset avança por registros recebidos, não pelo número de corridas."""
    offset, total, corridas = 0, None, []
    while total is None or offset < total:
        dados = obter_pagina(endpoint, offset, pasta, total, somente_cache)
        total, quantidade = validar_pagina(dados, endpoint, offset, total)
        corridas.extend(dados['MRData']['RaceTable']['Races'])
        offset += quantidade
    if offset != total:
        raise RespostaInvalida('Paginação incompleta; base final bloqueada')
    return corridas, total


def montar_base(calendario, fragmentos, total):
    """Relaciona por temporada/rodada/piloto, sem filtrar os status finais."""
    esperadas = {(r['season'], r['round']): r for r in calendario}
    if len(esperadas) != len(calendario):
        raise RespostaInvalida('Calendário com rodada duplicada')
    linhas, chaves, por_corrida = [], set(), defaultdict(list)
    for corrida in fragmentos:
        chave = (corrida['season'], corrida['round'])
        if chave not in esperadas:
            raise RespostaInvalida('Resultado de corrida ausente do calendário: {}'.format(chave))
        prevista = esperadas[chave]
        for campo in ('raceName', 'date'):
            if corrida[campo] != prevista[campo]:
                raise RespostaInvalida('Metadados diferentes do calendário: {} {}'.format(chave, campo))
        if corrida['Circuit']['circuitId'] != prevista['Circuit']['circuitId'] or corrida['Circuit']['circuitName'] != prevista['Circuit']['circuitName']:
            raise RespostaInvalida('Circuito diferente do calendário: {}'.format(chave))
        for resultado in corrida['Results']:
            piloto, equipe = resultado['Driver'], resultado['Constructor']
            identificador = chave + (piloto['driverId'],)
            if identificador in chaves:
                raise RespostaInvalida('Duplicação por temporada, rodada e piloto: {}'.format(identificador))
            chaves.add(identificador)
            linha = dict(zip(COLUNAS, [
                corrida['season'], corrida['round'], corrida['raceName'], corrida['date'],
                corrida['Circuit']['circuitId'], corrida['Circuit']['circuitName'],
                piloto['driverId'], piloto['givenName'] + ' ' + piloto['familyName'],
                equipe['constructorId'], equipe['name'], resultado['grid'], resultado['position'],
                resultado['status'], resultado['points'], '1' if 1 <= int(resultado['position']) <= 3 else '0',
            ]))
            linhas.append(linha)
            por_corrida[chave].append(linha)
    if set(por_corrida) != set(esperadas) or len(linhas) != total:
        raise RespostaInvalida('Base incompleta: corridas ou total de registros não conferem com a API/calendário')
    ausentes = {c: sum(not r.get(c, '').strip() for r in linhas) for c in COLUNAS}
    if any(ausentes.values()):
        raise RespostaInvalida('Campos ausentes na base: {}'.format(ausentes))
    por_rodada = []
    for chave in sorted(por_corrida, key=lambda item: int(item[1])):
        grupo = por_corrida[chave]
        posicoes = [int(r['posicao_final']) for r in grupo]
        if len(set(posicoes)) != len(posicoes) or sum(int(r['podio']) for r in grupo) != 3:
            raise RespostaInvalida('Posições finais duplicadas ou pódio diferente de três pilotos: {}'.format(chave))
        por_rodada.append({'rodada': chave[1], 'corrida': grupo[0]['corrida'],
                           'registros': len(grupo), 'podios': sum(int(r['podio']) for r in grupo)})
    linhas.sort(key=lambda r: (int(r['rodada']), int(r['posicao_final'])))
    resumo = {'completa': True, 'temporada': TEMPORADA, 'corridas_esperadas': len(esperadas),
              'corridas_coletadas': len(por_corrida), 'registros': len(linhas),
              'registros_por_corrida': por_rodada, 'campos_ausentes': ausentes,
              'duplicacoes_temporada_rodada_piloto': 0,
              'distribuicao_status': dict(sorted(Counter(r['status'] for r in linhas).items()))}
    return linhas, resumo


def coletar():
    """Somente produz o CSV e o comprovante após concluir todas as verificações."""
    raw = PASTA / 'raw'
    antigo = RAIZ / 'data/raw/calendario_2024.json'
    novo = raw / 'calendario_offset_0000.json'
    if not novo.exists() and antigo.exists():
        conteudo = antigo.read_bytes()
        try:
            validar_pagina(json.loads(conteudo.decode('utf-8')), 'calendario', 0)
        except (UnicodeDecodeError, json.JSONDecodeError, RespostaInvalida) as erro:
            raise RespostaInvalida('Calendário antigo inválido: {}. Preserve-o em backup antes de repetir: {}'.format(antigo, erro)) from erro
        salvar_preservando(novo, conteudo.decode('utf-8'))
        print('Calendário original reutilizado sem alterá-lo.', flush=True)
    calendario, total_calendario = coletar_paginas('calendario', raw)
    fragmentos, total_resultados = coletar_paginas('resultados', raw)
    linhas, resumo = montar_base(calendario, fragmentos, total_resultados)
    if len(calendario) != total_calendario:
        raise RespostaInvalida('Calendário incompleto')
    tabela = io.StringIO(newline='')
    escritor = csv.DictWriter(tabela, fieldnames=COLUNAS, lineterminator='\n')
    escritor.writeheader()
    escritor.writerows(linhas)
    csv_texto = tabela.getvalue()
    resumo['csv_sha256'] = hashlib.sha256(csv_texto.encode('utf-8')).hexdigest()
    resumo['paginas_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.glob('*.json'))}
    saidas = [(PASTA / 'resultados_2024.csv', csv_texto),
              (PASTA / 'verificacao.json', json.dumps(resumo, ensure_ascii=False, indent=2) + '\n')]
    # Preflight de todo o lote, antes de qualquer saída final. O comprovante vai por último.
    for caminho, texto in saidas:
        if caminho.exists() and caminho.read_bytes() != texto.encode('utf-8'):
            raise FileExistsError('Arquivo existente diferente: {}. Faça um backup explícito; nada será sobrescrito.'.format(caminho))
    for caminho, texto in saidas:
        salvar_preservando(caminho, texto)
    print('BASE COMPLETA: {}/{} corridas; {} registros. {}'.format(
        resumo['corridas_coletadas'], resumo['corridas_esperadas'], len(linhas), PASTA / 'resultados_2024.csv',
    ), flush=True)
    return linhas, resumo


if __name__ == '__main__':
    try:
        coletar()
    except (OSError, ValueError) as erro:
        print('Falha na coleta da temporada: {}. Esta execução não produziu uma nova base completa; caches parciais não são uma tabela final. Saídas anteriores foram preservadas.'.format(erro), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Coleta interrompida. Execute novamente para reutilizar as páginas válidas.', file=sys.stderr)
        sys.exit(130)
