"""Hash-bound posterior targets; frozen forecasts remain read-only.

The offline producer checks original sources. The portable reader checks the
explicit public annex without depending on private captures or model files.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path

ANNEX = 'frontend_assets/avaliacao_posterior_mexico_2026.json'
ANNEX_SHA256 = '55432f9010b201dba5b61702ce708eebea085957790dcee5e5c82c8aff2ba606'
EVENT = (2026, 19, 'rodriguez')
KEY = '2026:19:rodriguez'
FIELDS = ('temporada', 'rodada', 'piloto_id', 'equipe_id',
          'elegivel_previsao', 'probabilidade_modelo', 'ranking_modelo',
          'ranking_classificacao')


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def forecast_digest(rows):
    frozen = sorted(({key: row[key] for key in FIELDS} for row in rows),
                    key=lambda row: row['piloto_id'])
    return hashlib.sha256(json.dumps(frozen, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def _utc(value):
    instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if instant.tzinfo is None:
        raise ValueError('Posterior timestamp has no timezone')
    return instant


def _load(root):
    path = Path(root) / ANNEX
    if _hash(path) != ANNEX_SHA256:
        raise ValueError('Posterior annex hash mismatch')
    annex = json.loads(path.read_text(encoding='utf-8'))
    emission, window, source = annex['emissao'], annex['janela'], annex['fonte']
    if not (_utc(emission['emitido_em_utc']) < _utc(window['largada_utc'])
            < _utc(window['encerramento_observado_utc'])
            < _utc(window['resultado_final_publicado_utc'])
            <= _utc(source['obtido_em_utc'])):
        raise ValueError('Posterior chronology is invalid')
    return annex


def _race_rows(data):
    races = [r for r in data['corridas'] if
             (r.get('temporada'), r.get('rodada'), r.get('circuito_id')) == EVENT]
    if len(races) != 1:
        raise ValueError('Posterior event identity mismatch')
    return races[0], [r for r in data['previsoes']
                      if (r.get('temporada'), r.get('rodada')) == EVENT[:2]]


def _bind(annex, race, rows, provenance):
    emission = annex['emissao']
    original = provenance['emissoes'][KEY]
    ids = [row['piloto_id'] for row in rows]
    expected = {row['piloto_id'] for row in annex['resultado']}
    population = race['participantes_esperados_previsao']
    if (len(ids) != 22 or len(set(ids)) != 22 or set(ids) != expected
            or len(population) != 22 or set(population) != expected
            or race['estado_previsao'] != 'previsao_registrada'
            or any(row.get('modo_previsao') != 'previsao_registrada' for row in rows)
            or race['emissao_sha256'] != emission['manifesto_sha256']
            or original['modo'] != 'PROSPECTIVO'
            or original['evento'] != dict(temporada=2026, rodada=19, circuito_id='rodriguez')
            or _utc(original['emitido_em_utc']) != _utc(emission['emitido_em_utc'])
            or original['hashes_saidas']['probabilidades.csv'] != emission['probabilidades_sha256']
            or forecast_digest(rows) != emission['projecao_previsao_sha256']):
        raise ValueError('Posterior targets do not match the frozen emission')


def _metadata(annex):
    return dict(anexo=ANNEX, sha256=ANNEX_SHA256,
                fonte=annex['fonte'], janela=annex['janela'],
                cobertura=annex['cobertura'], avaliacao=annex['avaliacao'])


def apply_posterior(root, asset):
    """Called only by the offline producer, after building frozen forecasts."""
    root = Path(root)
    annex = _load(root)
    race, rows = _race_rows(asset['dados_2026'])
    _bind(annex, race, rows, asset['proveniencia'])
    emission = root / annex['emissao']['diretorio']
    normalized = root / annex['normalizacao']['arquivo']
    source = root / 'reports/avaliacao_mexico_20261102/fia_final_race_classification.pdf'
    checks = [(emission / 'manifesto.json', annex['emissao']['manifesto_sha256']),
              (emission / 'probabilidades.csv', annex['emissao']['probabilidades_sha256']),
              (normalized, annex['normalizacao']['sha256'])]
    # Raw official documents remain in the private capture. Reproduction uses
    # the audited, hash-pinned normalization; an available original must match.
    if source.exists():
        checks.append((source, annex['fonte']['sha256']))
    for path, expected in checks:
        if _hash(path) != expected:
            raise ValueError('Posterior source hash mismatch: {}'.format(path))
    by_id = {r['piloto_id']: r for r in annex['resultado']}
    for row in rows:
        target = by_id[row['piloto_id']]
        if target['equipe_id'] != row['equipe_id']:
            raise ValueError('Posterior team identity mismatch')
        row.update({key: target[key] for key in (
            'resultado_observado', 'status_resultado', 'podio_resultado_confirmado')})
    race.update(estado_resultado='observado_local', estado_operacao='resultado_observado',
                resultado_posterior_validado=True, motivo_resultado=None,
                fonte_resultado_sha256=annex['fonte']['sha256'],
                resultado_obtido_em_utc=annex['fonte']['obtido_em_utc'],
                resultado_circuito_id='rodriguez', resultado_data_fonte='2026-11-01')
    asset['proveniencia']['avaliacoes_posteriores'] = {KEY: _metadata(annex)}
    asset['proveniencia']['fontes_sha256'].update(
        {str(path.relative_to(root)): digest for path, digest in checks})
    asset['proveniencia']['fontes_sha256'][ANNEX] = ANNEX_SHA256
    asset['proveniencia']['fontes_sha256'][str(source.relative_to(root))] = annex['fonte']['sha256']
    validate_projected_asset(root, asset)


def validate_projected_asset(root, asset):
    """Reject an altered public result, forecast, or audit binding."""
    metadata = asset.get('proveniencia', {}).get('avaliacoes_posteriores', {})
    if KEY not in metadata:
        # Other rounds and old pending assets remain compatible. A completed
        # real Mexico emission must carry its explicit posterior audit.
        for race in asset['dados_2026']['corridas']:
            if ((race.get('temporada'), race.get('rodada'), race.get('circuito_id')) == EVENT
                    and race.get('resultado_posterior_validado') is True
                    and race.get('emissao_sha256')):
                raise ValueError('Validated Mexico result is missing its posterior audit')
        return
    annex = _load(root)
    race, rows = _race_rows(asset['dados_2026'])
    _bind(annex, race, rows, asset['proveniencia'])
    if (metadata != {KEY: _metadata(annex)}
            or race.get('resultado_posterior_validado') is not True
            or race.get('estado_resultado') != 'observado_local'
            or race.get('resultado_circuito_id') != 'rodriguez'
            or race.get('resultado_data_fonte') != '2026-11-01'
            or race.get('fonte_resultado_sha256') != annex['fonte']['sha256']
            or race.get('resultado_obtido_em_utc') != annex['fonte']['obtido_em_utc']
            or asset['proveniencia']['fontes_sha256'].get(ANNEX) != ANNEX_SHA256):
        raise ValueError('Posterior projected provenance mismatch')
    by_id = {r['piloto_id']: r for r in annex['resultado']}
    for row in rows:
        target = by_id[row['piloto_id']]
        if any(row.get(key) != target[key] or type(row.get(key)) is not type(target[key])
               for key in ('resultado_observado', 'status_resultado', 'podio_resultado_confirmado')):
            raise ValueError('Posterior projected target mismatch')
