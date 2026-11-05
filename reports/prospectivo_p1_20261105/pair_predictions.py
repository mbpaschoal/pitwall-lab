"""P1 companion: prepare Q alongside an already validated prospective v1.

No fitting, collecting, v1 rewriting or remote publication. Public receipt remains
pending until both probability files are verifiably available before the deadline.
"""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
Q_SHA = '7288daba4658cc98d5790b8a3b85df75bf33946df422dcc492750dda4e1c1ed7'
V1_HASHES = {'modelo': '16718ea5c4a7f662e72f09d38b073e545df1bba5c64c87b2cc1a0973ad9116e3',
    'metadados': '77d24dc765d773e49b717b79844dd4678a91087dbbc091e3e9cb184215ea9cc6',
    'esquema': '1b14e532cd3001ad6b38442cab4a14e52e63208fbe37bec77d8b464dfb98efdd'}
KEY = ('temporada', 'rodada', 'piloto_id')
FORBIDDEN = {'podio', 'posicao_final', 'pontos', 'status', 'grid_resultado', 'resultado_ausente'}


def utc_now(): return datetime.now(timezone.utc)
def utc(value):
    d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if d.tzinfo is None: raise ValueError('Explicit timezone required')
    return d.astimezone(timezone.utc)
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text())
def frozen_q():
    path = HERE/'q-baseline-frozen.json'
    if sha(path) != Q_SHA: raise ValueError('Frozen Q changed')
    return load(path)


def q_probability(row, model):
    # Reject extra fields rather than infer predictors from a descriptive table.
    if set(row) != set(model['fields']): raise ValueError('Q feature allowlist mismatch')
    x = []
    for field, median, mean, scale in zip(model['fields'], model['medians'], model['scaler_mean'], model['scaler_scale']):
        value = row[field]
        if value is None or value == '': value = median
        value = float(value)
        if not math.isfinite(value) or scale <= 0: raise ValueError('Invalid frozen Q input')
        x.append((value-mean)/scale)
    logit = model['intercept']+sum(a*b for a, b in zip(x, model['coefficients']))
    if logit >= 0: return 1/(1+math.exp(-logit))
    z = math.exp(logit); return z/(1+z)


def inspect_manifest(folder, model, now):
    manifest = load(folder/'manifesto.json')
    if manifest.get('modo') != 'PROSPECTIVO': raise ValueError('Requires prospective v1, not a retrospective rehearsal')
    if manifest.get('modelos') != V1_HASHES: raise ValueError('Frozen v1 identity changed')
    clock = manifest['corte_temporal']; start = utc(clock['corrida_programada_em_utc'])
    cutoff, issued = utc(manifest['corte_utc']), utc(manifest['emitido_em_utc'])
    qstart = utc(manifest['sessao_qualifying_inicio_utc']); end = utc(manifest['sessao_qualifying_encerrada_utc'])
    acquired = utc(manifest['obtido_classificacao_utc'])
    if not qstart <= end <= acquired <= cutoff <= issued <= now < start-timedelta(minutes=60):
        raise ValueError('Pair creation is outside the observed chronology/publication margin')
    if not utc(model['frozen_at_utc']) <= cutoff: raise ValueError('Q baseline frozen after this cutoff')
    if clock.get('resultado_alvo_incluido') is not False: raise ValueError('Current target admitted')
    if clock['corte_utc'] != manifest['corte_utc']: raise ValueError('Cutoff declarations disagree')
    required = {'entradas.json', 'probabilidades.csv', 'historicos.json', 'fontes.json', 'cobertura.json'}
    hashes = manifest.get('hashes_saidas', {})
    if not required <= set(hashes): raise ValueError('Incomplete scientific evidence inventory')
    for relative, digest in hashes.items():
        name = Path(relative)
        if name.is_absolute() or '..' in name.parts: raise ValueError('Unsafe evidence path')
        path = folder/name
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file() or sha(path) != digest:
            raise ValueError('Changed/missing evidence')
    return manifest, start


def assemble_pairs(inputs, csv_rows, event, model):
    rows, matrix, fields = inputs['linhas'], inputs['matriz'], inputs['ordem']
    if len(rows) != len(matrix) or len(rows) != len(csv_rows) or len(rows) < 3: raise ValueError('Pair coverage differs')
    if int(event['temporada']) == 2026 and len(rows) != 22: raise ValueError('2026 pair requires the full 22-driver roster')
    if not set(model['fields']) <= set(fields): raise ValueError('Q fields missing from v1 inputs')
    csv_index = {(str(r['temporada']), str(r['rodada']), r['piloto_id']): r for r in csv_rows}
    if len(csv_index) != len(rows): raise ValueError('Duplicate/missing v1 keys')
    output, seen = [], set()
    for row, numeric in zip(rows, matrix):
        if FORBIDDEN.intersection(row) or set(numeric) != set(fields): raise ValueError('Unexpected current-race outcome or matrix field')
        if any(row.get(f) != numeric[f] for f in fields): raise ValueError('Matrix/row mismatch')
        k = tuple(str(row[x]) for x in KEY)
        if k in seen or k not in csv_index or not k[2]: raise ValueError('Duplicate or unmatched driver')
        seen.add(k)
        if (k[:2] != (str(event['temporada']), str(event['rodada'])) or row.get('circuito_id') != event['circuito_id']
                or csv_index[k].get('circuito_id') != event['circuito_id']):
            raise ValueError('Foreign event row')
        if row.get('elegivel_previsao') is not True: raise ValueError('Incomplete eligible forecast')
        p = float(csv_index[k]['probabilidade_modelo'])
        if not math.isfinite(p) or not 0 <= p <= 1 or p != row.get('probabilidade_modelo'):
            raise ValueError('v1 probability disagrees')
        output.append({'temporada': k[0], 'rodada': k[1], 'piloto_id': k[2], 'circuito_id': event['circuito_id'],
            'equipe_id_entrada': row['equipe_id_entrada'], 'probabilidade_v1': p,
            'probabilidade_q': q_probability({f: numeric[f] for f in model['fields']}, model)})
    return output


def prepare(source_root, emission_id, destination):
    root = Path(source_root).resolve(); destination = Path(destination).resolve()
    if not emission_id or any(x not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for x in emission_id):
        raise ValueError('Unsafe emission ID')
    if destination.exists() or any(p.is_symlink() for p in (destination, *destination.parents)):
        raise FileExistsError('Pair destination exists or is unsafe')
    original_artifacts = {'modelo': 'models/modelo_v1/modelo.joblib',
        'metadados': 'models/modelo_v1/metadados.json', 'esquema': 'data/preparado/colunas.json'}
    if any(sha(root/name) != V1_HASHES[k] for k, name in original_artifacts.items()):
        raise ValueError('Original frozen v1 artifact changed')
    # Native registry validates preserved qualifying captures, IDs and chronology.
    sys.path.insert(0, str(root))
    from registro_emissoes import carregar
    registry = carregar(root)
    matches = [v for v in registry.values() if Path(v['diretorio']).name == emission_id]
    if len(matches) != 1 or matches[0]['modo'] != 'PROSPECTIVO': raise ValueError('Emission not uniquely validated in registry')
    relative = Path(matches[0]['diretorio'])
    if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe registered emission directory')
    folder = root/relative; model = frozen_q(); now = utc_now()
    manifest, start = inspect_manifest(folder, model, now)
    identity = lambda event: (int(event['temporada']), int(event['rodada']), event['circuito_id'])
    if identity(manifest['evento']) != identity(matches[0]['evento']): raise ValueError('Registry/manifest identity differs')
    with (folder/'probabilidades.csv').open(newline='') as f: csv_rows = list(csv.DictReader(f))
    inputs = load(folder/'entradas.json')
    if inputs['ordem'] != load(root/'data/preparado/colunas.json')['entradas']:
        raise ValueError('Original v1 input schema changed')
    pairs = assemble_pairs(inputs, csv_rows, manifest['evento'], model)
    if manifest['cobertura']['elegiveis'] != len(pairs) or manifest['cobertura']['registros_classificacao'] != len(pairs):
        raise ValueError('Manifest coverage differs')
    result = {'schema': 'pitwall-p1-prepared-pair-v1', 'created_at_utc': now.isoformat(), 'event': manifest['evento'],
        'status': 'prepared_not_published', 'publication_verified': False,
        'public_receipt_required_before_utc': (start-timedelta(minutes=60)).isoformat(),
        'source_emission_id': emission_id, 'v1_manifest_sha256': sha(folder/'manifesto.json'),
        'v1_inputs_sha256': sha(folder/'entradas.json'), 'v1_probabilities_sha256': sha(folder/'probabilidades.csv'),
        'q_baseline_sha256': Q_SHA, 'v1_model_hashes': V1_HASHES, 'cutoff_utc': manifest['corte_utc'],
        'fitting_performed': False, 'collection_performed': False, 'current_targets_read': False, 'pairs': pairs}
    # Recheck real clock after computation; no CLI backdating option.
    if utc_now() >= start-timedelta(minutes=60): raise ValueError('Publication margin closed during preparation')
    destination.mkdir(parents=True, exist_ok=False)
    with (destination/'paired-probabilities.json').open('x') as f: json.dump(result, f, indent=2, ensure_ascii=False); f.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--emission-id', required=True); parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args(); result = prepare(args.source_root, args.emission_id, args.destination)
    print(json.dumps({'status': result['status'], 'rows': len(result['pairs']), 'publication_verified': False}))
