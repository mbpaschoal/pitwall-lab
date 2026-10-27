"""Adaptador somente leitura do asset Race Weekend gerado offline."""
import json
import math
from pathlib import Path


class RaceWeekendDadosErro(ValueError):
    pass

def _nao_avaliavel(motivo, podio=None):
    return {
        'avaliavel_ranking': False, 'motivo': motivo, 'podio_observado': podio or [],
        'acertos_modelo': None, 'acertos_classificacao': None,
    }


def _inteiro_positivo(valor):
    return isinstance(valor, int) and not isinstance(valor, bool) and valor > 0


def avaliar_previsao_registrada(
    modo, participantes, *, populacao_esperada=None,
    estado_resultado='observado_local', resultado_validado=True,
):
    """Audita uma emissão registrada sem modificar probabilidades ou o ensaio histórico."""
    if modo != 'previsao_registrada':
        return _nao_avaliavel('ensaio_retrospectivo_ou_sem_previsao_registrada')
    if estado_resultado != 'observado_local' or resultado_validado is not True:
        return _nao_avaliavel('resultado_posterior_nao_validado')
    ids = [item.get('piloto_id') for item in participantes]
    if not ids or any(not isinstance(piloto_id, str) or not piloto_id for piloto_id in ids) or len(set(ids)) != len(ids):
        return _nao_avaliavel('participantes_invalidos_ou_duplicados')
    elegiveis = [item for item in participantes if item.get('elegivel_previsao') is True]
    esperada = set(populacao_esperada) if populacao_esperada is not None else set(ids)
    if (len(elegiveis) < 3 or len(elegiveis) != len(participantes)
            or set(ids) != esperada or any(not isinstance(x, str) or not x for x in esperada)):
        return _nao_avaliavel('cobertura_elegivel_incompleta')
    if any(item.get('resultado_observado') is None for item in participantes):
        return _nao_avaliavel('resultado_posterior_ausente')
    posicoes = [item.get('resultado_observado') for item in participantes]
    if any(not _inteiro_positivo(posicao) for posicao in posicoes) or len(set(posicoes)) != len(posicoes):
        return _nao_avaliavel('resultado_posterior_invalido')
    podio = [item['piloto_id'] for item in participantes if item['resultado_observado'] in (1, 2, 3)]
    if {item['resultado_observado'] for item in participantes if item['resultado_observado'] in (1, 2, 3)} != {1, 2, 3}:
        return _nao_avaliavel('podio_posterior_incompleto')
    for item in elegiveis:
        probabilidade = item.get('probabilidade_modelo')
        if (not isinstance(probabilidade, (int, float)) or isinstance(probabilidade, bool)
                or not math.isfinite(probabilidade) or not 0 <= probabilidade <= 1):
            return _nao_avaliavel('probabilidade_publicada_invalida', podio)
    rankings = ('ranking_modelo', 'ranking_classificacao')
    if any(
        any(not _inteiro_positivo(item.get(campo)) for item in elegiveis)
        or {item[campo] for item in elegiveis if item[campo] in (1, 2, 3)} != {1, 2, 3}
        for campo in rankings
    ):
        return _nao_avaliavel('ranking_publicado_invalido', podio)
    favoritos_modelo = {item['piloto_id'] for item in elegiveis if item['ranking_modelo'] in (1, 2, 3)}
    favoritos_q = {item['piloto_id'] for item in elegiveis if item['ranking_classificacao'] in (1, 2, 3)}
    if len(favoritos_modelo) != 3 or len(favoritos_q) != 3:
        return _nao_avaliavel('ranking_publicado_incompleto', podio)
    return {
        'avaliavel_ranking': True, 'motivo': 'avaliacao_posterior_previsao_registrada',
        'podio_observado': podio, 'acertos_modelo': len(favoritos_modelo & set(podio)),
        'acertos_classificacao': len(favoritos_q & set(podio)),
    }


def carregar_asset(raiz):
    caminho = Path(raiz) / 'frontend_assets/race_weekend.json'
    try:
        asset = json.loads(caminho.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise RaceWeekendDadosErro('Asset Race Weekend indisponível: {}'.format(caminho)) from erro
    if asset.get('versao') != 2 or asset.get('temporadas') != [2024, 2025, 2026]:
        raise RaceWeekendDadosErro('Asset Race Weekend inválido; gere-o novamente offline.')
    dados = asset.get('dados_2026')
    if not isinstance(asset.get('identidades'), dict) or not isinstance(dados, dict):
        raise RaceWeekendDadosErro('Asset Race Weekend sem identidades ou dados 2026 válidos.')
    corridas, previsoes = dados.get('corridas'), dados.get('previsoes')
    if not isinstance(corridas, list) or not isinstance(previsoes, list):
        raise RaceWeekendDadosErro('Asset Race Weekend com listas 2026 inválidas.')
    campeonato = dados.get('campeonato_pilotos')
    if not isinstance(campeonato, dict):
        raise RaceWeekendDadosErro('Asset Race Weekend sem campeonato 2026 local válido.')
    if not isinstance(campeonato.get('disponivel'), bool) or not isinstance(campeonato.get('classificacao'), list):
        raise RaceWeekendDadosErro('Asset Race Weekend sem estado válido do campeonato de pilotos.')
    if campeonato['disponivel']:
        if not isinstance(campeonato.get('snapshot_id'), str) or not isinstance(campeonato.get('rodada_referencia'), int):
            raise RaceWeekendDadosErro('Asset Race Weekend com referência de campeonato inválida.')
        if not isinstance(campeonato.get('obtido_em_utc'), str) or not isinstance(campeonato.get('paginas_validadas'), int):
            raise RaceWeekendDadosErro('Asset Race Weekend sem paginação válida do campeonato de pilotos.')
        for item in campeonato['classificacao']:
            if not all(campo in item for campo in ('posicao', 'pontos', 'vitorias', 'piloto_id', 'piloto', 'equipe')):
                raise RaceWeekendDadosErro('Asset Race Weekend com DriverStandings incompleto.')
    elif not isinstance(campeonato.get('motivo'), str):
        raise RaceWeekendDadosErro('Asset Race Weekend sem motivo de indisponibilidade do campeonato.')
    tempos_sessoes = dados.get('tempos_sessoes', {})
    if not isinstance(tempos_sessoes, dict):
        raise RaceWeekendDadosErro('Asset Race Weekend com tempos de sessão inválidos.')
    chaves_corrida, chaves_previsao = set(), set()
    for corrida in corridas:
        if not isinstance(corrida, dict) or not isinstance(corrida.get('rodada'), int) or corrida['rodada'] < 1:
            raise RaceWeekendDadosErro('Asset Race Weekend com rodada inválida.')
        if corrida['rodada'] in chaves_corrida:
            raise RaceWeekendDadosErro('Asset Race Weekend com rodada 2026 duplicada.')
        chaves_corrida.add(corrida['rodada'])
        estados_por_campo = {
            'estado_qualificacao': ('indisponivel', 'local_disponivel'),
            'estado_previsao': ('indisponivel', 'previsao_registrada', 'ensaio_retrospectivo'),
            'estado_resultado': ('indisponivel', 'observado_local'),
        }
        for campo, aceitos in estados_por_campo.items():
            if corrida.get(campo) not in aceitos:
                raise RaceWeekendDadosErro('Asset Race Weekend com estado inválido: {}.'.format(campo))
        for campo in ('corrida', 'cidade', 'pais', 'data'):
            if not isinstance(corrida.get(campo), str) or not corrida[campo]:
                raise RaceWeekendDadosErro('Asset Race Weekend sem contexto do GP: {}.'.format(campo))
        if corrida.get('estado_operacao') not in (
            'aguardando_dados', 'classificacao_disponivel', 'previsao_registrada',
            'ensaio_retrospectivo', 'resultado_observado',
        ):
            raise RaceWeekendDadosErro('Asset Race Weekend com estado operacional inválido.')
    for item in previsoes:
        if not isinstance(item, dict) or item.get('temporada') != 2026 or not isinstance(item.get('rodada'), int) or not item.get('piloto_id'):
            raise RaceWeekendDadosErro('Asset Race Weekend com participante 2026 inválido.')
        chave = (item['rodada'], item['piloto_id'])
        if chave in chaves_previsao:
            raise RaceWeekendDadosErro('Asset Race Weekend com participante 2026 duplicado: {}.'.format(chave))
        chaves_previsao.add(chave)
        for campo in ('probabilidade_modelo', 'ranking_modelo', 'ranking_classificacao'):
            if campo not in item:
                raise RaceWeekendDadosErro('Asset Race Weekend sem campo consumido: {}.'.format(campo))
    return asset


def nome_exibicao_piloto(piloto_id, nome):
    """Expande um nome conhecido apenas na UI; identidade e fonte ficam intactas."""
    if piloto_id == 'antonelli' and nome == 'Kimi Antonelli':
        return 'Andrea Kimi Antonelli'
    return nome


def identidade(asset, temporada, rodada, piloto_id):
    valor = asset.get('identidades', {}).get('{}:{}:{}'.format(temporada, rodada, piloto_id), {})
    nome = valor.get('piloto')
    return {
        'piloto': nome_exibicao_piloto(piloto_id, nome) if nome else 'Nome indisponível ({})'.format(piloto_id),
        'equipe_id': valor.get('equipe_id'),
        'equipe': valor.get('equipe'),
    }


def pacote_2026(asset):
    dados = asset.get('dados_2026')
    if not isinstance(dados, dict):
        raise RaceWeekendDadosErro('Dados 2026 ausentes no asset Race Weekend.')
    participantes_por_rodada = {}
    for item in dados.get('previsoes', []):
        participante = dict(item)
        participante.update({
            'motivos_inelegibilidade': participante.get('motivos_inelegibilidade') or 'probabilidade local indisponível',
            'favorito_modelo': participante.get('ranking_modelo') in (1, 2, 3),
            'favorito_classificacao': participante.get('ranking_classificacao') in (1, 2, 3),
            'alvo_conhecido': participante.get('resultado_observado') is not None,
            'podio': None if participante.get('resultado_observado') is None else int(participante['resultado_observado'] <= 3),
        })
        participantes_por_rodada.setdefault(participante['rodada'], []).append(participante)
    corridas = []
    for fonte in dados.get('corridas', []):
        corrida = dict(fonte)
        participantes = participantes_por_rodada.get(corrida['rodada'], [])
        podio_observado = [item['piloto_id'] for item in participantes if item['resultado_observado'] in (1, 2, 3)]
        avaliacao = avaliar_previsao_registrada(
            corrida.get('estado_previsao'), participantes,
            populacao_esperada=corrida.get('participantes_esperados_previsao'),
            estado_resultado=corrida.get('estado_resultado', 'indisponivel'),
            resultado_validado=corrida.get('resultado_posterior_validado', False),
        )
        corrida.update({
            'participantes_preparados': len(participantes),
            'elegiveis': sum(item['elegivel_previsao'] for item in participantes),
            'alvos_conhecidos': sum(item['alvo_conhecido'] for item in participantes),
            'avaliavel_ranking': avaliacao['avaliavel_ranking'],
            'motivos_nao_avaliavel': avaliacao['motivo'],
            'podio_observado': avaliacao['podio_observado'] if avaliacao['avaliavel_ranking'] else podio_observado,
            'acertos_modelo': avaliacao['acertos_modelo'], 'acertos_classificacao': avaliacao['acertos_classificacao'],
        })
        corridas.append(corrida)
    return {
        'temporada': 2026,
        'corridas': corridas,
        'previsoes': dados.get('previsoes', []),
        'participantes_por_rodada': participantes_por_rodada,
        'campeonato_pilotos': dados['campeonato_pilotos'],
        'tempos_sessoes': dados.get('tempos_sessoes', {}),
    }


def dados_do_gp_2026(pacote, rodada):
    corrida = next((item for item in pacote['corridas'] if item['rodada'] == rodada), None)
    if corrida is None:
        raise ValueError('Rodada não encontrada: {}'.format(rodada))
    participantes = list(pacote['participantes_por_rodada'].get(rodada, []))
    participantes.sort(key=lambda item: (not item['elegivel_previsao'], item['ranking_modelo'] or 9999, item['piloto_id']))
    return {
        'corrida': corrida,
        'participantes': participantes,
        'favoritos_modelo': [item for item in participantes if item['favorito_modelo']],
        'favoritos_classificacao': [item for item in participantes if item['favorito_classificacao']],
        'integrantes_identificados': [item['piloto_id'] for item in participantes if item['podio'] == 1],
        'tempos_sessoes': pacote.get('tempos_sessoes', {}).get(str(rodada)),
    }
