"""Registro explícito de emissões por evento, sem seleção global implícita."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from operacao2026 import fontes as fontes_operacao, openf1_qualificacao


class RegistroEmissoesErro(ValueError):
    pass


# Para acrescentar uma emissão futura, declare-a aqui com a identidade do GP.
# A validação recusa manifestos com identidade, modo, UTC ou hashes inconsistentes.
DECLARACOES = (
    {
        'temporada': 2026, 'rodada': 1, 'circuito_id': 'albert_park',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r1-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 2, 'circuito_id': 'shanghai',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r2-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 3, 'circuito_id': 'suzuka',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r3-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 4, 'circuito_id': 'miami',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r4-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 5, 'circuito_id': 'villeneuve',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r5-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 6, 'circuito_id': 'monaco',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r6-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 7, 'circuito_id': 'catalunya',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r7-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 8, 'circuito_id': 'red_bull_ring',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r8-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 9, 'circuito_id': 'silverstone',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r9-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 10, 'circuito_id': 'spa',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r10-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 11, 'circuito_id': 'hungaroring',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r11-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 12, 'circuito_id': 'zandvoort',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r12-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 13, 'circuito_id': 'monza',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r13-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 14, 'circuito_id': 'madring',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r14-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 15, 'circuito_id': 'baku',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r15-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 16, 'circuito_id': 'sepang',
        'snapshot': 'classificacoes-retro-20261024T064010Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-retro-r16-20261024T141514Z',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 17, 'circuito_id': 'marina_bay',
        'snapshot': 'coleta-20261020T020130Z',
        'diretorio': 'reports/operacao_2026/emissoes/ensaio-commit-9e65ad25b125e78b671a763a43934385c1264363',
        'modo': 'ENSAIO_RETROSPECTIVO',
    },
    {
        'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas',
        'snapshot': 'coleta-20261020T020130Z',
        'diretorio': 'reports/operacao_2026/emissoes/austin-prospectivo-openf1-20261025T054420Z',
        'modo': 'PROSPECTIVO',
    },
)


def _sha256(caminho):
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _evento(valor):
    try:
        return {'temporada': int(valor['temporada']), 'rodada': int(valor['rodada']), 'circuito_id': str(valor['circuito_id'])}
    except (KeyError, TypeError, ValueError) as erro:
        raise RegistroEmissoesErro('Manifesto sem identidade de evento válida.') from erro


def _utc(valor):
    if not isinstance(valor, str) or not valor.endswith('Z'):
        raise RegistroEmissoesErro('UTC da emissão inválido.')
    try:
        return datetime.fromisoformat(valor.replace('Z', '+00:00'))
    except ValueError as erro:
        raise RegistroEmissoesErro('UTC da emissão inválido.') from erro


def _validar_corte_prospectivo(manifesto, emitido_em, fontes_qualificacao=None):
    corte = manifesto.get('corte_temporal')
    campos = ('qualificacao_inicio_utc', 'qualificacao_encerrada_em_utc',
              'qualificacao_disponivel_em_utc', 'corte_utc', 'corrida_programada_em_utc')
    if not isinstance(corte, dict) or corte.get('resultado_alvo_incluido') is not False:
        raise RegistroEmissoesErro('Emissão prospectiva sem corte temporal comprovado.')
    try:
        inicio, encerrada, qualificacao, corte_utc, corrida = (_utc(corte[campo]) for campo in campos)
    except (KeyError, RegistroEmissoesErro) as erro:
        raise RegistroEmissoesErro('Emissão prospectiva sem corte temporal comprovado.') from erro
    if not inicio <= encerrada <= qualificacao <= corte_utc <= emitido_em < corrida:
        raise RegistroEmissoesErro('Emissão prospectiva sem corte temporal comprovado.')
    if fontes_qualificacao is None:
        return
    try:
        obtidas = [_utc(fonte['obtido_em_utc']) for fonte in fontes_qualificacao]
    except (KeyError, RegistroEmissoesErro) as erro:
        raise RegistroEmissoesErro('Fonte de classificação sem UTC efetivo comprovado.') from erro
    if not obtidas or any(not inicio <= encerrada <= obtida <= corte_utc for obtida in obtidas):
        raise RegistroEmissoesErro('UTC efetivo de página de classificação incompatível com o corte temporal.')
    if max(obtidas) != qualificacao:
        raise RegistroEmissoesErro('UTC efetivo de classificação diverge da disponibilidade declarada.')


def _fontes_qualificacao_comprovadas(raiz, snapshot, evento, manifesto, exigir_utc=False):
    snapshots_manifesto = manifesto.get('source_snapshots')
    if not isinstance(snapshots_manifesto, list) or len(snapshots_manifesto) != 1 or not isinstance(snapshots_manifesto[0], str):
        raise RegistroEmissoesErro('Snapshot declarado diverge da proveniência da emissão.')
    raiz_snapshots = Path(raiz) / 'data' / 'operacao_2026' / 'snapshots'
    def ler(nome):
        try:
            _, paginas = fontes_operacao.ler_snapshot(
                raiz_snapshots, nome, endpoints={'classificacao'}, rodadas={str(evento['rodada'])},
            )
        except (OSError, ValueError) as erro:
            raise RegistroEmissoesErro('Snapshot declarado sem classificação comprovada.') from erro
        return [fonte for fonte, _ in paginas.get('classificacao', [])]
    fontes_snapshot = ler(snapshot)
    fontes_origem = ler(snapshots_manifesto[0])
    fontes_manifesto = [fonte for fonte in manifesto.get('fontes', [])
                         if isinstance(fonte, dict) and fonte.get('endpoint') == 'classificacao'
                         and str(fonte.get('rodada')) == str(evento['rodada'])]
    def identidade(fonte):
        identidade_base = (fonte.get('arquivo'), fonte.get('sha256'), fonte.get('endpoint'), str(fonte.get('rodada')))
        return identidade_base + ((fonte.get('obtido_em_utc'),) if exigir_utc else ())
    esperado = {identidade(fonte) for fonte in fontes_snapshot}
    if not esperado or esperado != {identidade(fonte) for fonte in fontes_origem}:
        raise RegistroEmissoesErro('Snapshot declarado diverge da proveniência da emissão.')
    if {identidade(fonte) for fonte in fontes_manifesto} != esperado:
        raise RegistroEmissoesErro('Fonte de classificação diverge do snapshot declarado.')
    return [dict(fonte) for fonte in fontes_snapshot]


def _qualificacao_alternativa_openf1(raiz, manifesto, evento):
    declarada = manifesto.get('qualificacao_alternativa')
    if not isinstance(declarada, dict) or declarada.get('origem') != 'openf1':
        return None
    diretorio = declarada.get('diretorio')
    if not isinstance(diretorio, str) or not diretorio:
        raise RegistroEmissoesErro('Diretório OpenF1 inválido.')
    base = Path(raiz).resolve()
    caminho = (base / diretorio).resolve()
    if base not in caminho.parents:
        raise RegistroEmissoesErro('Diretório OpenF1 fora da raiz.')
    try:
        dados = openf1_qualificacao.carregar(caminho)
    except (OSError, ValueError) as erro:
        raise RegistroEmissoesErro('Classificação OpenF1 comprovada inválida.') from erro
    if (dados['sessao']['session_key'], dados['sessao']['meeting_key']) != (declarada.get('session_key'), declarada.get('meeting_key')):
        raise RegistroEmissoesErro('Sessão OpenF1 diverge do manifesto.')
    if dados['encerramento_utc'] != declarada.get('encerramento_utc'):
        raise RegistroEmissoesErro('Encerramento OpenF1 diverge do manifesto.')
    if evento != {'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas'}:
        raise RegistroEmissoesErro('Identidade do evento não corresponde à Q OpenF1.')
    return dados


def validar_declaracoes(raiz, declaracoes):
    raiz = Path(raiz)
    saida = {}
    for declaracao in declaracoes:
        evento_declarado = _evento(declaracao)
        chave = (evento_declarado['temporada'], evento_declarado['rodada'], evento_declarado['circuito_id'])
        if chave in saida:
            raise RegistroEmissoesErro('Há mais de uma emissão declarada para a mesma identidade.')
        diretorio = declaracao.get('diretorio')
        if not isinstance(diretorio, str) or not diretorio:
            raise RegistroEmissoesErro('Declaração sem diretório de emissão.')
        snapshot = declaracao.get('snapshot')
        if not isinstance(snapshot, str) or not snapshot:
            raise RegistroEmissoesErro('Declaração sem snapshot canônico.')
        pasta = raiz / diretorio
        try:
            manifesto = json.loads((pasta / 'manifesto.json').read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
            raise RegistroEmissoesErro('Manifesto da emissão indisponível.') from erro
        if _evento(manifesto.get('evento')) != evento_declarado:
            raise RegistroEmissoesErro('A identidade declarada diverge do manifesto.')
        modo = manifesto.get('modo')
        if modo not in {'PROSPECTIVO', 'ENSAIO_RETROSPECTIVO'} or modo != declaracao.get('modo'):
            raise RegistroEmissoesErro('Modo da emissão inválido ou divergente.')
        emitido_em = _utc(manifesto.get('emitido_em_utc'))
        if modo == 'PROSPECTIVO':
            _validar_corte_prospectivo(manifesto, emitido_em)
        alternativa = _qualificacao_alternativa_openf1(raiz, manifesto, evento_declarado)
        if alternativa is None:
            fontes_qualificacao = _fontes_qualificacao_comprovadas(
                raiz, snapshot, evento_declarado, manifesto, exigir_utc=(modo == 'PROSPECTIVO'),
            )
        else:
            fontes_qualificacao = alternativa['fontes']
        if modo == 'PROSPECTIVO':
            _validar_corte_prospectivo(manifesto, emitido_em, fontes_qualificacao)
        modelos = manifesto.get('modelos')
        if not isinstance(modelos, dict) or not all(isinstance(modelos.get(campo), str) and modelos[campo] for campo in ('modelo', 'metadados', 'esquema')):
            raise RegistroEmissoesErro('Versão do modelo ausente no manifesto.')
        hashes = manifesto.get('hashes_saidas')
        if not isinstance(hashes, dict) or not hashes.get('probabilidades.csv'):
            raise RegistroEmissoesErro('Hash de probabilidades ausente no manifesto.')
        probabilidades = pasta / 'probabilidades.csv'
        if not probabilidades.is_file() or _sha256(probabilidades) != hashes['probabilidades.csv']:
            raise RegistroEmissoesErro('Hash de probabilidades inválido.')
        linhas = probabilidades.read_text(encoding='utf-8').splitlines()
        if len(linhas) < 2 or 'piloto_id' not in linhas[0] or 'probabilidade_modelo' not in linhas[0]:
            raise RegistroEmissoesErro('Probabilidades sem cobertura legível.')
        saida[chave] = {
            'evento': evento_declarado,
            'snapshot': snapshot,
            'diretorio': diretorio,
            'modo': modo,
            'emitido_em_utc': manifesto['emitido_em_utc'],
            'modelos': dict(modelos),
            'cobertura': dict(manifesto.get('cobertura') or {}),
            'hash_probabilidades': hashes['probabilidades.csv'],
            'fontes_qualificacao': fontes_qualificacao,
            'origem_qualificacao': 'openf1' if alternativa is not None else 'jolpica',
            'registros_qualificacao': alternativa['registros'] if alternativa is not None else None,
            'arquivos_qualificacao': alternativa['arquivos'] if alternativa is not None else None,
        }
    return saida


def carregar(raiz):
    return validar_declaracoes(raiz, DECLARACOES)
