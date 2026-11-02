"""Verify the public release ZIP in memory without allocating disk for it."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import io
import json
import urllib.request
import zipfile
import subprocess

ROOT=Path(__file__).resolve().parents[2]
VERSION='0.8.15'
TAG='v'+VERSION
OUT=ROOT/'reports/interface_audit_20261102'
OUT.mkdir(exist_ok=True)
headers={'Accept':'application/vnd.github+json','User-Agent':'Pitwall-Lab-release-verifier'}
url='https://api.github.com/repos/mbpaschoal/pitwall-lab/releases/tags/v'+VERSION
with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as response:
    release=json.load(response)
asset=next(a for a in release['assets'] if a['name']=='pitwall-dashboard.zip')
blob=io.BytesIO();digest=hashlib.sha256()
with urllib.request.urlopen(urllib.request.Request(asset['browser_download_url'],headers={'User-Agent':headers['User-Agent']}),timeout=90) as response:
    while True:
        block=response.read(1024*1024)
        if not block:break
        digest.update(block);blob.write(block)
assert blob.tell()==asset['size']
assert 'sha256:'+digest.hexdigest()==asset['digest']
manifest_bytes=subprocess.check_output(['git','show',TAG+':distribuicao/pitwall-dashboard/MANIFESTO.json'],cwd=ROOT)
manifest=json.loads(manifest_bytes)
assert manifest['versao_produto']==VERSION
expected={r['caminho']:r['sha256_destino'] for r in manifest['arquivos']}
expected['MANIFESTO.json']=hashlib.sha256(manifest_bytes).hexdigest()
with zipfile.ZipFile(blob) as archive:
    names=[i.filename for i in archive.infolist() if not i.is_dir()]
    assert len(names)==len(set(names)) and set(names)==set(expected)
    for name in names:
        h=hashlib.sha256()
        with archive.open(name) as source:
            while True:
                block=source.read(1024*1024)
                if not block:break
                h.update(block)
        assert h.hexdigest()==expected[name],name
record=dict(utc=datetime.now(timezone.utc).isoformat(),version=VERSION,status='passed',release=release['html_url'],published_at=release['published_at'],asset_id=asset['id'],bytes=asset['size'],sha256=digest.hexdigest(),github_digest_matches=True,members_verified=len(names),every_member_matches_tagged_manifest=True,tag=TAG,build=manifest['apresentacao_build_sha256'],disk_zip_created=False)
(OUT/'release-zip.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
