"""Painéis editoriais locais, separados das entradas e probabilidades do modelo.

O asset portátil contém somente snapshots oficiais completos, com a identidade
da rodada e a proveniência das respostas originais. Não se calculam campeonatos
a partir de resultados de GPs: isso omitiria Sprint e ajustes administrativos.
"""
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from contexto_editorial import carregar as carregar_contextos, para_gp


ASSET = 'frontend_assets/paineis_editoriais.json'
INVENTARIO_AUSTIN = 'data/operacao_2026/pos_corrida/austin-20261026T111018Z/inventario.json'
TIPOS = {
    'driver_standings': ('classificacao_pilotos', 'driverstandings', 'DriverStandings'),
    'constructor_standings': ('classificacao_equipes', 'constructorstandings', 'ConstructorStandings'),
}
# Consultados em 2026-10-27. São contexto editorial atual, não uma fotografia
# histórica disponível no corte das previsões de 2024/2025 ou novas entradas.
CIRCUITOS_DESCRITIVOS = {
    'americas': {
        'uso': 'contexto_descritivo_atual_sem_uso_no_modelo',
        'verificado_em': '2026-10-27',
        'metricas_estaveis': {
            'comprimento_km': 5.513, 'curvas': 20,
            'primeiro_gp': 2012, 'sentido': 'Anti-horário',
        },
        'por_temporada': {
            '2026': {
                'voltas': 56, 'distancia_corrida_km': 308.432,
                'recorde_volta': '1:36.169 · Charles Leclerc (2019)',
            },
        },
        'fontes': [
            {
                'titulo': 'Formula 1 — United States Grand Prix 2026',
                'url': 'https://www.formula1.com/en/racing/2026/united-states',
                'campos': ['comprimento_km', 'primeiro_gp', 'voltas', 'distancia_corrida_km', 'recorde_volta'],
            },
            {
                'titulo': 'Circuit of The Americas — Austin, Circuit Of The Americas Get High Praise From Formula One Drivers',
                'url': 'https://circuitoftheamericas.com/blog/2014/10/25/austin-circuit-of-the-americas-get-high-praise-from-formula-one-drivers-teams/',
                'campos': ['curvas', 'sentido'],
            },
        ],
    },
}


class PaineisDadosErro(ValueError):
    pass


def _ler(raiz, relativo):
    raiz = Path(raiz).resolve()
    relativo = Path(relativo)
    if relativo.is_absolute() or '..' in relativo.parts:
        raise PaineisDadosErro('Fonte fora da raiz do projeto.')
    candidato = raiz / relativo
    atual = candidato
    while atual != raiz:
        if atual.is_symlink():
            raise PaineisDadosErro('Fonte dos painéis não pode usar symlink.')
        atual = atual.parent
    candidato.resolve(strict=True).relative_to(raiz)
    return candidato.read_bytes()


def _inteiro(valor, minimo=0):
    if isinstance(valor, bool) or not re.fullmatch(r'[0-9]+', str(valor)):
        raise PaineisDadosErro('Contagem ou posição inválida nos painéis.')
    numero = int(valor)
    if numero < minimo:
        raise PaineisDadosErro('Contagem ou posição fora do intervalo.')
    return numero


def _pontos(valor):
    if isinstance(valor, bool):
        raise PaineisDadosErro('Pontuação inválida.')
    try:
        pontos = float(valor)
    except (ValueError, TypeError) as erro:
        raise PaineisDadosErro('Pontuação inválida.') from erro
    if not math.isfinite(pontos) or pontos < 0:
        raise PaineisDadosErro('Pontuação inválida.')
    return pontos


def _texto(valor):
    if not isinstance(valor, str) or not valor.strip():
        raise PaineisDadosErro('Identificação ausente nos painéis.')
    return valor.strip()


def _validar_url(url, temporada, rodada, endpoint):
    partes = urlparse(_texto(url))
    if partes.scheme != 'https' or partes.hostname != 'api.jolpi.ca' or partes.path != '/ergast/f1/{}/{}/{}/'.format(temporada, rodada, endpoint):
        raise PaineisDadosErro('URL de proveniência não corresponde ao campeonato.')


def _utc(valor):
    valor = _texto(valor)
    try:
        instante = datetime.fromisoformat(valor.replace('Z', '+00:00'))
    except ValueError as erro:
        raise PaineisDadosErro('Captura do campeonato inválida.') from erro
    if not valor.endswith('Z') or instante.tzinfo != timezone.utc:
        raise PaineisDadosErro('Captura do campeonato sem UTC explícito.')
    return valor


def _normalizar_linha(linha, tipo):
    saida = {'posicao': _inteiro(linha['position'], 1), 'pontos': _pontos(linha['points']), 'vitorias': _inteiro(linha['wins'])}
    if tipo == 'driver_standings':
        piloto = linha['Driver']
        equipes = linha['Constructors']
        if not isinstance(equipes, list) or not equipes:
            raise PaineisDadosErro('Piloto sem equipes documentadas.')
        saida.update({
            'piloto_id': _texto(piloto['driverId']),
            'piloto': '{} {}'.format(_texto(piloto['givenName']), _texto(piloto['familyName'])),
            'nacionalidade': _texto(piloto['nationality']),
            'equipe': ' / '.join(_texto(equipe['name']) for equipe in equipes),
            'equipe_ids': [_texto(equipe['constructorId']) for equipe in equipes],
        })
    else:
        equipe = linha['Constructor']
        saida.update({'equipe_id': _texto(equipe['constructorId']), 'equipe': _texto(equipe['name'])})
    return saida


def _validar_classificacao(linhas, tipo, total):
    if not isinstance(linhas, list) or len(linhas) != total or not linhas:
        raise PaineisDadosErro('Campeonato incompleto.')
    campo = 'piloto_id' if tipo == 'driver_standings' else 'equipe_id'
    ids = [_texto(linha.get(campo)) for linha in linhas]
    posicoes = [_inteiro(linha.get('posicao'), 1) for linha in linhas]
    if len(set(ids)) != total or sorted(posicoes) != list(range(1, total + 1)):
        raise PaineisDadosErro('Identidades ou posições duplicadas/incompletas no campeonato.')
    for linha in linhas:
        _pontos(linha.get('pontos'))
        _inteiro(linha.get('vitorias'))
        _texto(linha.get('piloto' if tipo == 'driver_standings' else 'equipe'))
        if tipo == 'driver_standings':
            _texto(linha.get('equipe'))
            _texto(linha.get('nacionalidade'))
            equipes = linha.get('equipe_ids')
            if not isinstance(equipes, list) or not equipes or len(set(equipes)) != len(equipes):
                raise PaineisDadosErro('Identidades de equipe inválidas no campeonato.')
            for equipe in equipes:
                _texto(equipe)
    return sorted(linhas, key=lambda linha: linha['posicao'])


def _snapshot_do_inventario(raiz, relativo, inventario, tipo):
    endpoint, url_endpoint, nome_linhas = TIPOS[tipo]
    identidade = inventario['identidade']
    temporada, rodada = identidade['temporada'], identidade['rodada']
    estado = inventario['endpoints'][endpoint]
    if estado['estado'] != 'completo':
        raise PaineisDadosErro('Inventário registra campeonato incompleto.')
    total = _inteiro(estado['total'], 1)
    fontes = [fonte for fonte in inventario['fontes'] if fonte.get('endpoint') == endpoint]
    fontes.sort(key=lambda fonte: _inteiro(fonte['parametros']['offset']))
    linhas, hashes, urls, capturas = [], [], [], []
    proximo = 0
    for fonte in fontes:
        if fonte['status'] != 200:
            raise PaineisDadosErro('Resposta do campeonato sem sucesso.')
        _validar_url(fonte['url_real'], temporada, rodada, url_endpoint)
        raw = _ler(raiz, str(Path(relativo).parent / fonte['arquivo']))
        if hashlib.sha256(raw).hexdigest() != fonte['sha256']:
            raise PaineisDadosErro('SHA-256 da resposta do campeonato divergente.')
        dados = json.loads(raw)['MRData']
        _validar_url(dados['url'], temporada, rodada, url_endpoint)
        limite = _inteiro(dados['limit'], 1)
        offset = _inteiro(dados['offset'])
        if offset != proximo or offset != _inteiro(fonte['parametros']['offset']) or limite != _inteiro(fonte['parametros']['limit'], 1) or _inteiro(dados['total'], 1) != total:
            raise PaineisDadosErro('Paginação do campeonato descontínua ou inconsistente.')
        tabela = dados['StandingsTable']
        blocos = tabela['StandingsLists']
        if str(tabela['season']) != str(temporada) or str(tabela['round']) != str(rodada) or len(blocos) != 1:
            raise PaineisDadosErro('Temporada/rodada do campeonato divergente.')
        bloco = blocos[0]
        if str(bloco['season']) != str(temporada) or str(bloco['round']) != str(rodada):
            raise PaineisDadosErro('Temporada/rodada do bloco divergente.')
        pagina = bloco[nome_linhas]
        if not isinstance(pagina, list) or len(pagina) != min(limite, total - offset):
            raise PaineisDadosErro('Página de campeonato incompleta.')
        linhas.extend(_normalizar_linha(linha, tipo) for linha in pagina)
        proximo += len(pagina)
        hashes.append(fonte['sha256'])
        urls.append(fonte['url_real'])
        captura = _utc(fonte['obtido_em_utc'])
        capturas.append(captura)
    if proximo != total:
        raise PaineisDadosErro('Cobertura de páginas do campeonato insuficiente.')
    return {
        'tipo': tipo, 'temporada': temporada, 'rodada_referencia': rodada,
        'circuito_id': identidade['circuito_id'], 'disponivel': True,
        'classificacao': _validar_classificacao(linhas, tipo, total),
        'total': total, 'snapshot_id': inventario['snapshot_canonico'] + ':' + endpoint,
        'paginas_validadas': len(fontes), 'obtido_em_utc': max(capturas),
        'fontes_sha256': hashes, 'fontes_url': urls,
        'escopo': 'Classificação oficial pós-GP da Jolpica-F1; contexto descritivo separado das probabilidades.',
    }


def gerar_asset(raiz, destino):
    """Gera deterministicamente o asset portátil a partir do inventário existente.

    Operação explícita de preparação local: não consulta rede nem modifica raws.
    """
    inventario = json.loads(_ler(raiz, INVENTARIO_AUSTIN))
    if inventario.get('schema') != 'pitwall-pos-corrida-austin-captura-v1':
        raise PaineisDadosErro('Inventário de campeonato inválido.')
    contexto = para_gp(carregar_contextos(raiz), 2026, 18)
    identidade = inventario['identidade']
    if identidade != {'temporada': 2026, 'rodada': 18, 'circuito_id': contexto['circuito_id'], 'data': contexto['data']}:
        raise PaineisDadosErro('Inventário não corresponde ao GP editorial.')
    snapshots = [_snapshot_do_inventario(raiz, INVENTARIO_AUSTIN, inventario, tipo) for tipo in TIPOS]
    asset = {'versao': 1, 'uso': 'contexto_descritivo_pos_corrida', 'snapshots': snapshots, 'circuitos': CIRCUITOS_DESCRITIVOS}
    conteudo = (json.dumps(asset, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')
    destino = Path(destino)
    if destino.exists() and destino.read_bytes() != conteudo:
        raise PaineisDadosErro('Asset de painéis existente diverge; não sobrescrito.')
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo)
    return asset


def _indisponivel(temporada, rodada, motivo):
    return {'disponivel': False, 'classificacao': [], 'temporada': temporada, 'rodada_referencia': rodada, 'motivo': motivo}


def carregar_paineis(root, temporada, rodada, circuito_id):
    """Retorna o mesmo contrato visual em todas as temporadas, sem preencher lacunas.

    Standings são selecionados por temporada + rodada + circuito. Um snapshot de
    R18 nunca aparece como campeonato de R1 ou de outra temporada.
    """
    temporada, rodada = _inteiro(temporada), _inteiro(rodada, 1)
    contexto = para_gp(carregar_contextos(root), temporada, rodada)
    if circuito_id != contexto['circuito_id']:
        raise PaineisDadosErro('Circuito não corresponde à temporada/rodada selecionada.')
    saida = {
        'temporada': temporada, 'rodada': rodada, 'circuito_id': circuito_id,
        'circuit_info': {
            'nome': contexto['circuito_nome'], 'cidade': contexto['cidade'],
            'pais': contexto['pais'], 'data': contexto['data'],
            'comprimento_km': None, 'curvas': None, 'voltas': None,
            'distancia_corrida_km': None, 'primeiro_gp': None, 'sentido': None,
            'altitude_m': None, 'zonas_drs': None, 'recorde_volta': None,
            'motivo_metricas': 'Métricas técnicas não documentadas no snapshot local.',
        },
    }
    for tipo in TIPOS:
        saida[tipo] = _indisponivel(temporada, rodada, 'Classificação oficial desta rodada indisponível no snapshot local.')
    try:
        asset = json.loads(_ler(root, ASSET))
        if not isinstance(asset, dict) or asset.get('versao') != 1 or asset.get('uso') != 'contexto_descritivo_pos_corrida' or not isinstance(asset.get('snapshots'), list) or not all(isinstance(s, dict) for s in asset['snapshots']):
            raise PaineisDadosErro('Asset dos painéis inválido.')
        for tipo, (_, endpoint, _) in TIPOS.items():
            correspondentes = [s for s in asset['snapshots'] if s.get('tipo') == tipo and s.get('temporada') == temporada and s.get('rodada_referencia') == rodada and s.get('circuito_id') == circuito_id]
            if len(correspondentes) > 1:
                raise PaineisDadosErro('Snapshot de campeonato duplicado.')
            if not correspondentes:
                continue
            snapshot = correspondentes[0]
            total = _inteiro(snapshot['total'], 1)
            _validar_classificacao(snapshot['classificacao'], tipo, total)
            n_paginas = _inteiro(snapshot['paginas_validadas'], 1)
            if len(snapshot['fontes_sha256']) != n_paginas or len(snapshot['fontes_url']) != n_paginas or not all(re.fullmatch('[0-9a-f]{64}', h) for h in snapshot['fontes_sha256']):
                raise PaineisDadosErro('Proveniência dos painéis incompleta.')
            for url in snapshot['fontes_url']:
                _validar_url(url, temporada, rodada, endpoint)
            _utc(snapshot['obtido_em_utc'])
            _texto(snapshot['snapshot_id'])
            _texto(snapshot['escopo'])
            if snapshot.get('disponivel') is not True:
                raise PaineisDadosErro('Estado ou captura dos painéis inválido.')
            saida[tipo] = dict(snapshot)
        circuitos = asset.get('circuitos', {})
        if not isinstance(circuitos, dict):
            raise PaineisDadosErro('Metadados dos circuitos inválidos.')
        # Apenas os campos técnicos do contrato podem ser acrescentados. A
        # identidade da corrida continua vindo do calendário editorial validado.
        tecnico = circuitos.get(circuito_id)
        if tecnico is not None:
            if not isinstance(tecnico, dict) or tecnico.get('uso') != 'contexto_descritivo_atual_sem_uso_no_modelo':
                raise PaineisDadosErro('Escopo dos metadados do circuito inválido.')
            fontes = tecnico.get('fontes')
            if not isinstance(fontes, list) or not fontes or any(not isinstance(f, dict) or not isinstance(f.get('url'), str) or not f['url'].startswith('https://') for f in fontes):
                raise PaineisDadosErro('Fontes dos metadados do circuito ausentes.')
            metricas = dict(tecnico.get('metricas_estaveis', {}))
            metricas.update(tecnico.get('por_temporada', {}).get(str(temporada), {}))
            campos = {'comprimento_km', 'curvas', 'voltas', 'distancia_corrida_km', 'primeiro_gp', 'sentido', 'altitude_m', 'zonas_drs', 'recorde_volta'}
            if set(metricas) - campos:
                raise PaineisDadosErro('Campo técnico desconhecido no circuito.')
            for campo, valor in metricas.items():
                if campo in {'curvas', 'voltas', 'primeiro_gp', 'zonas_drs'}:
                    _inteiro(valor, 1)
                elif campo in {'comprimento_km', 'distancia_corrida_km', 'altitude_m'}:
                    _pontos(valor)
                elif campo == 'sentido' and valor not in {'Horário', 'Anti-horário'}:
                    raise PaineisDadosErro('Sentido do circuito inválido.')
                else:
                    _texto(valor)
            saida['circuit_info'].update(metricas)
            saida['circuit_info'].update({
                'fontes': fontes, 'verificado_em': tecnico['verificado_em'],
                'escopo': 'Contexto descritivo atual, consultado em {}. Não integra o modelo ou as probabilidades registradas.'.format(tecnico['verificado_em']),
                'motivo_metricas': 'Altitude e zonas de DRS não documentadas nas fontes locais.',
            })
    except (OSError, ValueError, KeyError, TypeError) as erro:
        for tipo in TIPOS:
            saida[tipo] = _indisponivel(temporada, rodada, 'Snapshot de painéis indisponível ou inválido: {}.'.format(erro))
    return saida
