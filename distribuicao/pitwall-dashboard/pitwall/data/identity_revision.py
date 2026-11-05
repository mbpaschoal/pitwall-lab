"""Pinned, posterior-only driver identity repair; original archive stays intact."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ASSET = 'frontend_assets/revisao_identidade_pilotos_v1.json'
APPROVED_SHA256 = '9518dba59098c9c9b7e407ccd52a396ab1375e7f841105adb65f8e36f3bf1c0a'
ORIGIN = 'coleta-20261027T230248Z'


def row_hash(row):
    return sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def project(asset, bundle):
    from pitwall.data.archive import conteudo_sha256
    if bundle.get('schema')!='pitwall-driver-identity-revision-v1' or bundle.get('scope')!='descriptive_posterior_identity_only' or bundle.get('model_promotion') is not False:
        raise ValueError('Invalid identity revision scope')
    content=conteudo_sha256(asset['gps'])
    if asset.get('conteudo_sha256')!=content:
        raise ValueError('Invalid identity input content')
    marker=asset.get('revisao_identidade')
    if marker:
        if marker.get('sha256')!=APPROVED_SHA256 or content!=bundle['result_content_sha256']:
            raise ValueError('Invalid prior identity revision')
        return deepcopy(asset)
    if content!=bundle['base_content_sha256']:
        raise ValueError('Identity revision base content mismatch')
    revised=deepcopy(asset);seen=set();applied=[]
    for b in bundle['bindings']:
        key=(b['event_key'],b['session_key'],b['numero'])
        if key in seen:raise ValueError('Duplicate identity binding')
        seen.add(key)
        gp=revised['gps'][b['event_key']]
        if gp['identidade']['circuito_id']!=b['circuito_id'] or gp['data_corrida']!=b['data_corrida']:
            raise ValueError('Identity revision event mismatch')
        sessions=[s for s in gp['sessoes'] if s['session_key']==b['session_key']]
        if len(sessions)!=1 or sessions[0]['nome']!=b['session_name'] or sessions[0]['inicio_utc']!=b['inicio_utc']:
            raise ValueError('Identity revision session mismatch')
        rows=[r for r in sessions[0]['tempos'] if r['numero']==b['numero']]
        if len(rows)!=1 or rows[0].get('piloto_id') is not None or row_hash(rows[0])!=b['expected_row_sha256']:
            raise ValueError('Identity revision driver precondition mismatch')
        if b['piloto_id']!=bundle['canonical_driver']['piloto_id'] or b['numero']!=bundle['canonical_driver']['car']:
            raise ValueError('Conflicting canonical identity')
        rows[0]['piloto_id']=b['piloto_id'];applied.append({'event_key':b['event_key'],'session_key':b['session_key'],'numero':b['numero']})
    revised['conteudo_sha256']=conteudo_sha256(revised['gps'])
    if revised['conteudo_sha256']!=bundle['result_content_sha256']:
        raise ValueError('Identity revision result content mismatch')
    revised['revisao_identidade']={'sha256':APPROVED_SHA256,'scope':bundle['scope'],'aplicados':applied,
        'fontes':[b['source'] for b in bundle['bindings']], 'fonte_canonica':bundle['canonical_driver']}
    return revised


def load_projection(root, asset):
    if asset.get('acervo_origem')!=ORIGIN:return asset
    root=Path(root).resolve();path=root/ASSET
    if path.is_symlink() or not path.is_file() or path.stat().st_size>64*1024 or not path.resolve().is_relative_to(root):
        raise ValueError('Approved identity revision missing or invalid')
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=APPROVED_SHA256:
        raise ValueError('Unapproved identity revision hash')
    return project(asset,json.loads(raw))
