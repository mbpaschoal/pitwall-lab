"""Pitwall Lab: coleta os resultados oficiais disponíveis na Jolpica-F1.

Somente biblioteca padrão do Python: não é necessário instalar pacotes.
"""
import csv
import io
import json
from pathlib import Path
import sys
import time
import unicodedata
from urllib.request import Request, urlopen
from urllib.error import HTTPError

RAIZ = Path(__file__).resolve().parent
BASE_API = 'https://api.jolpi.ca/ergast/f1'
USER_AGENT = 'PitwallLab/0.1.0 Python/{} (educational portfolio; urllib)'.format(sys.version.split()[0])
INTERVALO_SEGUNDOS = 8.0
ULTIMA_REQUISICAO = None
COLUNAS = ['piloto', 'equipe', 'posicao_largada', 'posicao_final', 'status']


def salvar_preservando(caminho, conteudo):
    """Nunca substitui conteúdo existente diferente, nem mesmo no cache."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists():
        if caminho.read_text(encoding='utf-8') == conteudo:
            return
        raise FileExistsError(
            'Arquivo existente diferente: {}. Mova-o para um backup antes de repetir.'.format(caminho)
        )
    with caminho.open('x', encoding='utf-8', newline='') as arquivo:
        arquivo.write(conteudo)


class RespostaInvalida(ValueError):
    """Dados externos não atendem à estrutura necessária para a coleta."""


def exigir_campo(objeto, nome, tipo, contexto):
    """Verifica presença e tipo sem converter nem modificar os dados da fonte."""
    caminho = contexto + '.' + nome
    if nome not in objeto:
        raise RespostaInvalida('{}: campo obrigatório ausente'.format(caminho))
    valor = objeto[nome]
    tipos = {dict: 'um objeto', list: 'uma lista', str: 'um texto'}
    if not isinstance(valor, tipo):
        raise RespostaInvalida('{}: deve ser {}'.format(caminho, tipos[tipo]))
    if tipo is str and not valor.strip():
        raise RespostaInvalida('{}: texto não pode estar vazio'.format(caminho))
    return valor


def exigir_inteiro(objeto, nome, contexto, minimo=1):
    """A Jolpica representa números por textos; exige dígitos e faixa válida."""
    valor = exigir_campo(objeto, nome, str, contexto)
    if not (valor.isascii() and valor.isdecimal()) or int(valor) < minimo:
        raise RespostaInvalida('{}: deve ser um inteiro em texto maior ou igual a {}'.format(
            contexto + '.' + nome, minimo,
        ))
    return int(valor)


def validar_resposta(dados, endpoint, temporada, rodada=None):
    """Valida o envelope e os campos consumidos pelo endpoint, sem alterá-los."""
    if endpoint not in ('calendario', 'resultados'):
        raise ValueError('Endpoint de validação desconhecido: {}'.format(endpoint))
    if not isinstance(dados, dict):
        raise RespostaInvalida('o JSON deve ser um objeto, não uma lista ou valor isolado')
    mrdata = exigir_campo(dados, 'MRData', dict, 'JSON')
    tabela = exigir_campo(mrdata, 'RaceTable', dict, 'MRData')
    total = exigir_inteiro(mrdata, 'total', 'MRData')
    temporada_tabela = exigir_campo(tabela, 'season', str, 'MRData.RaceTable')
    if temporada_tabela != temporada:
        raise RespostaInvalida('MRData.RaceTable.season: temporada diferente da solicitada')
    corridas = exigir_campo(tabela, 'Races', list, 'MRData.RaceTable')
    if not corridas:
        raise RespostaInvalida('MRData.RaceTable.Races: lista de corridas vazia')
    if endpoint == 'calendario' and len(corridas) != total:
        raise RespostaInvalida('MRData.total: calendário incompleto, quantidade de corridas diferente do total')
    if endpoint == 'resultados':
        if exigir_campo(tabela, 'round', str, 'MRData.RaceTable') != rodada:
            raise RespostaInvalida('MRData.RaceTable.round: rodada diferente da solicitada')
        if len(corridas) != 1:
            raise RespostaInvalida('MRData.RaceTable.Races: esperava uma única corrida nos resultados')
    for indice, corrida in enumerate(corridas):
        contexto = 'MRData.RaceTable.Races[{}]'.format(indice)
        if not isinstance(corrida, dict):
            raise RespostaInvalida('{}: deve ser um objeto'.format(contexto))
        if exigir_campo(corrida, 'season', str, contexto) != temporada:
            raise RespostaInvalida(contexto + '.season: temporada diferente da solicitada')
        exigir_inteiro(corrida, 'round', contexto)
        if endpoint == 'calendario':
            exigir_campo(corrida, 'raceName', str, contexto)
            exigir_campo(corrida, 'date', str, contexto)
            circuito = exigir_campo(corrida, 'Circuit', dict, contexto)
            local = exigir_campo(circuito, 'Location', dict, contexto + '.Circuit')
            exigir_campo(local, 'locality', str, contexto + '.Circuit.Location')
            exigir_campo(local, 'country', str, contexto + '.Circuit.Location')
        else:
            if corrida['round'] != rodada:
                raise RespostaInvalida(contexto + '.round: rodada diferente da solicitada')
            resultados = exigir_campo(corrida, 'Results', list, contexto)
            if not resultados or len(resultados) != total:
                raise RespostaInvalida(contexto + '.Results: resultados vazios ou incompletos em relação a MRData.total')
            for numero, resultado in enumerate(resultados):
                caminho = contexto + '.Results[{}]'.format(numero)
                if not isinstance(resultado, dict):
                    raise RespostaInvalida(caminho + ': deve ser um objeto')
                piloto = exigir_campo(resultado, 'Driver', dict, caminho)
                exigir_campo(piloto, 'givenName', str, caminho + '.Driver')
                exigir_campo(piloto, 'familyName', str, caminho + '.Driver')
                equipe = exigir_campo(resultado, 'Constructor', dict, caminho)
                exigir_campo(equipe, 'name', str, caminho + '.Constructor')
                exigir_inteiro(resultado, 'grid', caminho, minimo=0)
                exigir_inteiro(resultado, 'position', caminho)
                exigir_campo(resultado, 'status', str, caminho)


def interpretar_resposta(conteudo, endpoint, temporada, rodada=None):
    """Decodifica JSON e valida sua estrutura, sem gravar nenhum arquivo."""
    try:
        texto = conteudo.decode('utf-8')
    except UnicodeDecodeError as erro:
        raise RespostaInvalida('o conteúdo não é texto UTF-8 válido') from erro
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as erro:
        raise RespostaInvalida('JSON malformado na linha {}, coluna {}'.format(erro.lineno, erro.colno)) from erro
    validar_resposta(dados, endpoint, temporada, rodada)
    return dados


def obter_json(url, cache, *, endpoint='calendario', temporada='2024', rodada=None):
    """Valida rede e cache com as mesmas regras; só grava respostas válidas."""
    global ULTIMA_REQUISICAO
    if cache.exists():
        try:
            dados = interpretar_resposta(cache.read_bytes(), endpoint, temporada, rodada)
        except RespostaInvalida as erro:
            raise RespostaInvalida(
                'Cache inválido: {}. {}. O arquivo foi preservado. '
                'Mova somente este arquivo para um backup fora de data/raw/ '
                'e execute novamente; mantenha os demais dados válidos. '
                'Nenhuma nova consulta deste endpoint será feita enquanto este cache estiver neste caminho.'.format(cache, erro)
            ) from erro
        print('Cache local validado: {}'.format(cache))
        return dados
    if ULTIMA_REQUISICAO is not None:
        espera = INTERVALO_SEGUNDOS - (time.monotonic() - ULTIMA_REQUISICAO)
        if espera > 0:
            time.sleep(espera)
    requisicao = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    print('Consultando: {}'.format(url))
    ULTIMA_REQUISICAO = time.monotonic()
    try:
        with urlopen(requisicao, timeout=30) as resposta:
            conteudo = resposta.read()
    except HTTPError as erro:
        if erro.code == 429:
            espera_servidor = erro.headers.get('Retry-After', 'não informado')
            raise ValueError(
                'HTTP 429: limite da API atingido. Retry-After: {}. '
                'Nenhuma nova tentativa automática será feita; aguarde o prazo '
                'do servidor antes de executar novamente'.format(espera_servidor)
            ) from erro
        raise ValueError('HTTP {}: a API recusou a consulta; tente novamente mais tarde'.format(erro.code)) from erro
    try:
        dados = interpretar_resposta(conteudo, endpoint, temporada, rodada)
    except RespostaInvalida as erro:
        raise RespostaInvalida('Resposta inválida da API ({}): {}. Cache não foi gravado.'.format(url, erro)) from erro
    salvar_preservando(cache, conteudo.decode('utf-8'))
    return dados


def coletar():
    """Descobre a etapa pelo calendário; não pressupõe o número da rodada."""
    calendario = obter_json(
        BASE_API + '/2024/?limit=100', RAIZ / 'data/raw/calendario_2024.json',
        endpoint='calendario', temporada='2024',
    )
    corridas = calendario['MRData']['RaceTable']['Races']
    if len(corridas) != int(calendario['MRData']['total']):
        raise ValueError('Calendário incompleto: não foi possível consultar todas as corridas.')
    candidatas = []
    for corrida in corridas:
        local = corrida['Circuit']['Location']
        cidade = ''.join(
            letra for letra in unicodedata.normalize('NFKD', local['locality'])
            if not unicodedata.combining(letra)
        ).casefold()
        if local['country'] == 'Brazil' and cidade == 'sao paulo':
            candidatas.append(corrida)
    if len(candidatas) != 1:
        raise ValueError('Esperava uma única corrida em São Paulo, Brasil; encontrei {}.'.format(len(candidatas)))
    corrida = candidatas[0]
    temporada, rodada = corrida['season'], corrida['round']
    print('Identificador descoberto: temporada {}, rodada {}; {} em {}.'.format(
        temporada, rodada, corrida['raceName'], corrida['date'],
    ))
    url = BASE_API + '/{}/{}/results/?limit=100'.format(temporada, rodada)
    dados = obter_json(
        url, RAIZ / 'data/raw/resultados_sao_paulo_2024.json',
        endpoint='resultados', temporada=temporada, rodada=rodada,
    )
    corridas_resultado = dados['MRData']['RaceTable']['Races']
    if len(corridas_resultado) != 1:
        raise ValueError('Resultados ausentes ou ambíguos para a corrida selecionada.')
    resultado_corrida = corridas_resultado[0]
    if (resultado_corrida['season'], resultado_corrida['round']) != (temporada, rodada):
        raise ValueError('Os resultados não correspondem à corrida descoberta no calendário.')
    resultados = resultado_corrida['Results']
    if not resultados or len(resultados) != int(dados['MRData']['total']):
        raise ValueError('Resultados vazios ou incompletos; nenhum CSV será criado.')
    saida = io.StringIO(newline='')
    escritor = csv.DictWriter(saida, fieldnames=COLUNAS, lineterminator='\n')
    escritor.writeheader()
    for resultado in sorted(resultados, key=lambda item: int(item['position'])):
        escritor.writerow({
            'piloto': resultado['Driver']['givenName'] + ' ' + resultado['Driver']['familyName'],
            'equipe': resultado['Constructor']['name'],
            'posicao_largada': resultado['grid'],
            'posicao_final': resultado['position'],
            'status': resultado['status'],
        })
    destino = RAIZ / 'data/resultados_sao_paulo_2024.csv'
    salvar_preservando(destino, saida.getvalue())
    print('CSV verificado/criado: {} ({} pilotos).'.format(destino, len(resultados)))


if __name__ == '__main__':
    try:
        coletar()
    except (OSError, ValueError) as erro:
        print('Falha na coleta: {}. Nenhum dado será inventado. Verifique sua conexão e os arquivos locais.'.format(erro), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nColeta interrompida pelo usuário.', file=sys.stderr)
        sys.exit(130)
