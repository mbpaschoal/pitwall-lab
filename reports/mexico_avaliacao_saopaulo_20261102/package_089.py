"""Materialise the unchanged export recipe with COW media, without a local ZIP.

CI independently runs the normal exporter, compares every byte and builds the
release ZIP. No recipe, baseline or expected hash is altered to fit the package.
"""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import exportar_dashboard as e
report=Path(__file__).parent
changed=set(subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).splitlines())
allowed={'VERSION','CHANGELOG.md','CHANGELOG.en.md','publicacao/templates/requirements.txt'}
assert not ((changed & set(e.RUNTIME_WORKTREE))-allowed),changed
assert (ROOT/'VERSION').read_text().strip()=='0.8.9'
commit=e.COMMIT_BASE_PADRAO
files=e._montar_arquivos(ROOT,e.validar_fontes_no_commit(ROOT,commit),commit)
paths=sorted(list(files)+['ARQUIVOS_PUBLICACAO.txt','MANIFESTO.json'])
e._adicionar(files,'ARQUIVOS_PUBLICACAO.txt',('\n'.join(paths)+'\n').encode(),'gerado')
manifest=e._manifesto(files,ROOT,commit)
e._adicionar(files,'MANIFESTO.json',(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode(),'gerado',nota='autorreferência excluída da lista de hashes do manifesto')
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
stage=Path('/private/tmp')/('pitwall-saopaulo-089-'+stamp)/'pitwall-dashboard';stage.mkdir(parents=True,exist_ok=False)
previous=ROOT/'distribuicao/pitwall-dashboard'
expected={name:sha256(item['conteudo']).hexdigest() for name,item in files.items()}
cloned=0
for name,item in files.items():
    target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);source=previous/name;content=item['conteudo']
    if source.is_file() and not source.is_symlink() and sha256(source.read_bytes()).hexdigest()==expected[name]:
        subprocess.run(['cp','-c',str(source),str(target)],check=True);cloned+=1
    else:target.write_bytes(content)
    del item['conteudo']
    del content
assert {str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file()}==set(expected)
for name,digest in expected.items():
    assert sha256((stage/name).read_bytes()).hexdigest()==digest,name
receipt=dict(stage=str(stage),version='0.8.9',build=manifest['apresentacao_build_sha256'],files=len(expected),cow_files=cloned,matches_export_recipe=True,zip='generated independently by standard exporter in CI/release workflow')
(report/'package-089.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
