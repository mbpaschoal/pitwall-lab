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


def obter_json(url, cache):
    """Reutiliza a resposta local; acessa a API apenas se ela não existir."""
    global ULTIMA_REQUISICAO
    if cache.exists():
        print('Cache local: {}'.format(cache.relative_to(RAIZ)))
        return json.loads(cache.read_text(encoding='utf-8'))
    if ULTIMA_REQUISICAO is not None:
        espera = INTERVALO_SEGUNDOS - (time.monotonic() - ULTIMA_REQUISICAO)
        if espera > 0:
            time.sleep(espera)
    requisicao = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    print('Consultando: {}'.format(url))
    ULTIMA_REQUISICAO = time.monotonic()
    try:
        with urlopen(requisicao, timeout=30) as resposta:
            texto = resposta.read().decode('utf-8')
    except HTTPError as erro:
        if erro.code == 429:
            espera_servidor = erro.headers.get('Retry-After', 'não informado')
            raise ValueError(
                'HTTP 429: limite da API atingido. Retry-After: {}. '
                'Nenhuma nova tentativa automática será feita; aguarde o prazo '
                'do servidor antes de executar novamente'.format(espera_servidor)
            ) from erro
        raise ValueError('HTTP {}: a API recusou a consulta; tente novamente mais tarde'.format(erro.code)) from erro
    dados = json.loads(texto)
    if not isinstance(dados.get('MRData'), dict):
        raise ValueError('Resposta não contém MRData: formato inesperado da API.')
    salvar_preservando(cache, texto)
    return dados


def coletar():
    """Descobre a etapa pelo calendário; não pressupõe o número da rodada."""
    calendario = obter_json(BASE_API + '/2024/?limit=100', RAIZ / 'data/raw/calendario_2024.json')
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
    dados = obter_json(url, RAIZ / 'data/raw/resultados_sao_paulo_2024.json')
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
    except (OSError, ValueError, KeyError, TypeError, IndexError) as erro:
        print('Falha na coleta: {}. Nenhum dado será inventado. Verifique sua conexão e os arquivos locais.'.format(erro), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nColeta interrompida pelo usuário.', file=sys.stderr)
        sys.exit(130)
