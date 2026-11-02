"""Portable, offline tyre-age revisions; never modifies source snapshots."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

ASSET = 'frontend_assets/complemento_idade_pneus_v1.json'
SCHEMA = 'pitwall-tyre-age-complement-v1'
COMPLEMENT_ID = 'openf1-tyre-age-20261101-v1'
BASE_ORIGIN = 'coleta-20261027T230248Z'
BASE_SHA256 = '6c7c3b4cf82a346ec626135444001ec5e156481545ba0889d2ec30b715948dfb'
ORIGINAL_CONTENT_SHA256 = '10728d1f96603fba097002a65835074f347ada286a690592a1bae3c585271a30'
COMPLEMENT_SHA256 = '4cc4da683474bfd836ce5f198a7e1e07d503f120cdd413ce3b071bcbf2982fb2'
RESULT_SHA256 = 'b5c1c1e3350db0eeecee92451bda72c12cf64293326af4a80aaaa814fb58c2e8'
MAX_BYTES = 512 * 1024

class TyreAgeError(ValueError):
    pass

def _int(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise TyreAgeError('Identidade ou idade inválida no complemento de pneus.')
    return value

def _utc(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise TyreAgeError('Data UTC inválida no complemento de pneus.')

def _gps_hash(gps):
    return sha256(json.dumps(gps, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()

def aplicar(asset, complemento):
    """Validate all targets on a private copy and return only the accepted revision."""
    if (not isinstance(complemento, dict) or complemento.get('schema') != SCHEMA
        or complemento.get('id') != COMPLEMENT_ID or type(complemento.get('versao')) is not int
        or complemento['versao'] != 1 or complemento.get('base_sha256') != BASE_SHA256
        or complemento.get('natureza') != 'revisao_descritiva_posterior_sem_alterar_previsoes'):
        raise TyreAgeError('Contrato do complemento de pneus não reconhecido.')
    _utc(complemento.get('criado_em_utc'))
    if complemento.get('conteudo_original_sha256') != _gps_hash(asset['gps']):
        raise TyreAgeError('Conteúdo original diverge da base auditada dos pneus.')
    sources = complemento.get('fontes')
    if not isinstance(sources, list) or len(sources) != 3:
        raise TyreAgeError('Fontes do complemento de pneus ausentes.')
    years = set()
    for source in sources:
        year = _int(source.get('temporada'), 2024)
        if year not in (2024, 2025, 2026) or year in years:
            raise TyreAgeError('Temporada de fonte inválida no complemento de pneus.')
        years.add(year)
        _utc(source.get('obtido_em_utc'))
        if not str(source.get('url', '')).startswith('https://api.openf1.org/v1/stints?'):
            raise TyreAgeError('Fonte de idade de pneus inválida.')
        if not isinstance(source.get('sha256'), str) or len(source['sha256']) != 64:
            raise TyreAgeError('Hash de fonte de idade de pneus inválido.')
    patches = complemento.get('correcoes')
    if not isinstance(patches, list) or len(patches) != 262:
        raise TyreAgeError('O complemento deve conter exatamente 262 idades auditadas.')
    result = deepcopy(asset)
    seen = set()
    targets = set()
    for patch in patches:
        if not isinstance(patch, dict):
            raise TyreAgeError('Correção de idade inválida.')
        skey = _int(patch.get('session_key'), 1)
        number = _int(patch.get('driver_number'), 1)
        stint_number = _int(patch.get('stint_number'), 1)
        _int(patch.get('meeting_key'), 1)
        start = _int(patch.get('inicio'), 1)
        end = _int(patch.get('fim'), 1)
        if end < start or patch.get('composto') not in ('SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET'):
            raise TyreAgeError('Composto ou limites inválidos no complemento de pneus.')
        native = skey, number, stint_number
        if native in seen:
            raise TyreAgeError('Identidade nativa duplicada no complemento de pneus.')
        seen.add(native)
        old = _int(patch.get('idade_original'))
        new = _int(patch.get('idade_revisada'))
        if old == new:
            raise TyreAgeError('Complemento de pneus contém idade sem alteração.')
        gp = result['gps'].get(patch.get('gp_key'))
        if not isinstance(gp, dict):
            raise TyreAgeError('GP do complemento de pneus não encontrado.')
        identity = gp['identidade']
        if (patch['gp_key'] != '{}:{}'.format(identity['temporada'], identity['rodada'])
            or patch.get('circuito_id') != identity['circuito_id']
            or patch.get('fonte_temporada') != identity['temporada']):
            raise TyreAgeError('Identidade do GP diverge do complemento de pneus.')
        sessions = [s for s in gp['sessoes'] if s.get('session_key') == skey]
        if len(sessions) != 1 or sessions[0].get('nome') != patch.get('modalidade') or patch.get('modalidade') not in ('Race', 'Sprint'):
            raise TyreAgeError('Sessão ou modalidade diverge do complemento de pneus.')
        matches = []
        for item in gp['estrategias']:
            if (item.get('session_key'), item.get('numero'), item.get('modalidade')) != (skey, number, patch['modalidade']):
                continue
            for stint in item['sequencia_stints']:
                if (stint.get('composto'), stint.get('inicio'), stint.get('fim'), stint.get('idade')) == (patch.get('composto'), patch.get('inicio'), patch.get('fim'), old):
                    matches.append(stint)
        if len(matches) != 1 or id(matches[0]) in targets:
            raise TyreAgeError('Stint ausente, ambíguo ou divergente da idade auditada.')
        targets.add(id(matches[0]))
        matches[0]['idade'] = new
    content_hash = _gps_hash(result['gps'])
    if content_hash != RESULT_SHA256 or content_hash != complemento.get('conteudo_revisado_sha256'):
        raise TyreAgeError('Resultado do complemento de pneus não confere com a revisão aprovada.')
    result['conteudo_sha256'] = content_hash
    result['complementos_aplicados'] = [{'id': COMPLEMENT_ID, 'versao': 1,
        'sha256': COMPLEMENT_SHA256, 'base_sha256': BASE_SHA256,
        'correcoes': len(patches), 'criado_em_utc': complemento['criado_em_utc'],
        'fontes': deepcopy(sources), 'natureza': complemento['natureza']}]
    return result

def carregar(raiz, asset, base_bytes):
    """Load the pinned complement; absence never silently restores known old ages."""
    root = Path(raiz).resolve()
    path = root / ASSET
    current = path
    while current != root:
        if current.is_symlink():
            raise TyreAgeError('O complemento de pneus não pode usar symlink.')
        current = current.parent
    if not path.exists():
        if (asset.get('acervo_origem') == BASE_ORIGIN
            or sha256(base_bytes).hexdigest() == BASE_SHA256
            or _gps_hash(asset['gps']) == ORIGINAL_CONTENT_SHA256):
            raise TyreAgeError('Complemento obrigatório de idade dos pneus ausente.')
        return asset  # Other/synthetic archives have no corresponding accepted revision.
    if sha256(base_bytes).hexdigest() != BASE_SHA256:
        raise TyreAgeError('Base do complemento de pneus diverge do snapshot auditado.')
    if path.stat().st_size > MAX_BYTES:
        raise TyreAgeError('Complemento de pneus excede o tamanho permitido.')
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != COMPLEMENT_SHA256:
        raise TyreAgeError('Hash do complemento de pneus inválido.')
    data = json.loads(raw.decode('utf-8'), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    return aplicar(asset, data)
