"""Verify a P1 pair against public GitHub release-asset server metadata.

Read-only, keyless, one request. Can audit after the GP because the server's
asset creation/update timestamps, size and digest bind the pre-deadline bytes.
"""
import argparse
from datetime import timedelta
import json
import math
from pathlib import Path
import re
from urllib.request import Request, urlopen
from pair_predictions import utc, utc_now, sha, load, Q_SHA, V1_HASHES


def validate(pair_file, asset):
    pair = load(pair_file); digest = sha(pair_file)
    if pair.get('schema') != 'pitwall-p1-prepared-pair-v1' or pair.get('status') != 'prepared_not_published':
        raise ValueError('Not an immutable prepared P1 pair')
    if pair.get('q_baseline_sha256') != Q_SHA or pair.get('v1_model_hashes') != V1_HASHES:
        raise ValueError('Frozen model identity differs')
    if pair.get('fitting_performed') is not False or pair.get('current_targets_read') is not False:
        raise ValueError('Unexpected fitting/target use')
    event = pair['event']; rows = pair.get('pairs', [])
    required = {'temporada', 'rodada', 'piloto_id', 'circuito_id', 'equipe_id_entrada', 'probabilidade_v1', 'probabilidade_q'}
    if len(rows) < 3 or (int(event['temporada']) == 2026 and len(rows) != 22): raise ValueError('Incomplete public pair')
    if len({r.get('piloto_id') for r in rows}) != len(rows): raise ValueError('Duplicate public driver')
    for row in rows:
        if (set(row) != required or not row['piloto_id'] or not row['equipe_id_entrada']
                or (str(row['temporada']), str(row['rodada']), row['circuito_id']) !=
                (str(event['temporada']), str(event['rodada']), event['circuito_id'])):
            raise ValueError('Foreign/invalid public row')
        if any(not math.isfinite(row[k]) or not 0 <= row[k] <= 1 for k in ('probabilidade_v1', 'probabilidade_q')):
            raise ValueError('Invalid public probability')
    for field in ('v1_manifest_sha256', 'v1_inputs_sha256', 'v1_probabilities_sha256'):
        if not re.fullmatch(r'[a-f0-9]{64}', pair.get(field, '')): raise ValueError('Missing native evidence hash')
    deadline = utc(pair['public_receipt_required_before_utc'])
    created, updated = utc(asset['created_at']), utc(asset['updated_at'])
    if not (utc(pair['cutoff_utc']) <= utc(pair['created_at_utc']) <= created <= updated < deadline and updated <= utc_now()):
        raise ValueError('Public asset was created/updated outside the fixed margin')
    if (asset.get('state') != 'uploaded' or asset.get('digest') != 'sha256:'+digest
            or asset.get('size') != Path(pair_file).stat().st_size):
        raise ValueError('Uploaded asset bytes differ')
    url = asset.get('browser_download_url', '')
    if not url.startswith('https://github.com/mbpaschoal/pitwall-lab/releases/download/'):
        raise ValueError('Asset is outside the approved public repository')
    return {'schema': 'pitwall-p1-public-pair-receipt-v1', 'event': pair['event'],
        'verified_at_utc': utc_now().isoformat(), 'pair_sha256': digest, 'size': asset['size'],
        'asset_id': asset['id'], 'url': url, 'asset_created_at_utc': asset['created_at'],
        'asset_updated_at_utc': asset['updated_at'], 'deadline_exclusive_utc': pair['public_receipt_required_before_utc'],
        'publication_verified': True, 'server_digest_matched': True,
        'note': 'Public pair file verified; served dashboard forecast acceptance remains a separate receipt.'}


def verify(pair_file, asset_id, destination):
    if not re.fullmatch(r'[0-9]+', str(asset_id)): raise ValueError('Numeric GitHub release asset ID required')
    destination = Path(destination)
    if destination.exists(): raise FileExistsError('Public receipt exists')
    url = 'https://api.github.com/repos/mbpaschoal/pitwall-lab/releases/assets/'+str(asset_id)
    request = Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Pitwall-Lab-P1-audit'})
    with urlopen(request, timeout=30) as response:
        if response.status != 200: raise ValueError('Public asset metadata unavailable')
        asset = json.load(response)
    if asset.get('id') != int(asset_id) or asset.get('url') != url: raise ValueError('Asset API identity differs')
    receipt = validate(pair_file, asset); receipt['api_url'] = url
    # Preserve prepared file bytes; write a distinct public-verification receipt.
    with destination.open('x') as f: json.dump({'receipt': receipt, 'server_asset_metadata': asset}, f, indent=2); f.write('\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--pair-file', type=Path, required=True)
    parser.add_argument('--asset-id', required=True); parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(verify(args.pair_file, args.asset_id, args.destination)))
