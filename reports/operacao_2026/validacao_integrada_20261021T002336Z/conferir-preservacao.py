from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess
R=Path('/Users/MBPaschoal/Dropbox/Projetos pessoais/F1');OUT=Path(__file__).parent;BASE='b067ad55dd97d964b132129838773cf6108773e3'
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert git('rev-parse','--show-object-format').strip()==b'sha1'
allowed={'README.md','projects/Pitwall Lab.md'};unchanged=[];intentional=[];unexpected=[];base_paths=set()
for rec in git('ls-tree','-r','-z',BASE).split(b'\0'):
 if not rec:continue
 meta,name=rec.split(b'\t',1);mode,kind,oid=meta.split();name=os.fsdecode(name);base_paths.add(name);p=R/name
 if kind!=b'blob':continue
 if not p.exists() and not p.is_symlink():unexpected.append({'path':name,'reason':'ausente'});continue
 data=os.fsencode(os.readlink(p)) if mode==b'120000' else p.read_bytes()
 actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 item={'path':name,'git_oid_original':oid.decode(),'igual_ao_commit':actual==oid.decode()}
 if actual==oid.decode():unchanged.append(item)
 elif name in allowed:intentional.append(item)
 else:unexpected.append(item)
manifest_name='docs/dashboard_artefatos_preservados.json';manifest_path=R/manifest_name
trusted=git('show',BASE+':'+manifest_name);assert manifest_path.read_bytes()==trusted
old68=json.loads(trusted)['sha256_artefatos_preservados'];assert len(old68)==68
check68=[{'path':n,'expected_sha256':h,'actual_sha256':sha(R/n),'match':sha(R/n)==h} for n,h in old68.items()]
def anchored(base,rel):
 p=(base/rel).resolve();assert base.resolve() in p.parents and not Path(rel).is_absolute();return p
snapshots=[];emissions=[]
for sid in ['coleta-20261019T164713Z','cache-verificado-20261019','coleta-20261020T020130Z']:
 base=R/'data/operacao_2026/snapshots'/sid;idx=json.loads((base/'indice.json').read_text());assert idx['snapshot_id']==sid
 rows=[{'path':x['arquivo'],'expected_sha256':x['sha256'],'actual_sha256':sha(anchored(base,x['arquivo']))} for x in idx['fontes']]
 for row in rows:row['match']=row['actual_sha256']==row['expected_sha256']
 snapshots.append({'snapshot':sid,'reference':str((base/'indice.json').relative_to(R)),'reference_sha256_observado_agora':sha(base/'indice.json'),'files':rows})
for eid in ['ensaio-integracao-20261019','ensaio-r1-corrigido-20261020','ensaio-r2-corrigido-20261020']:
 base=R/'reports/operacao_2026/emissoes'/eid;m=json.loads((base/'manifesto.json').read_text())
 rows=[{'path':n,'expected_sha256':h,'actual_sha256':sha(anchored(base,n))} for n,h in m['hashes_saidas'].items()]
 for row in rows:row['match']=row['actual_sha256']==row['expected_sha256']
 emissions.append({'emission':eid,'reference':str((base/'manifesto.json').relative_to(R)),'reference_sha256_observado_agora':sha(base/'manifesto.json'),'files':rows})
newcode=[R/'operar_2026.py',*sorted((R/'operacao2026').glob('*.py')),*sorted((R/'tests').glob('test_operacao_2026*.py')),R/'docs/estado_hermes.md',R/'docs/comandos_operacao_2026.md',R/'docs/fontes_operacao_2026.md']
limitations=['Código/testes/documentação novos da etapa8 não possuem baseline histórico imutável nesta validação; alterações intencionais não são falhas de preservação de artefatos congelados.','Hashes dos manifestos/índices calculados agora identificam a referência usada, NÃO reconstroem prova de seu estado passado. Manifestos locais não são prova externa imutável.']
report={'utc':datetime.now(timezone.utc).isoformat(),'reference_commit':BASE,'tracked_unchanged_count':len(unchanged),'tracked_unchanged':unchanged,'intentional_document_changes':intentional,'unexpected_changes':unexpected,'manifest68_anchored_in_base_commit':True,'manifest68':check68,'canonical_snapshots':snapshots,'canonical_rehearsals':emissions,'snapshot_files_checked':sum(len(x['files']) for x in snapshots),'rehearsal_files_checked':sum(len(x['files']) for x in emissions),'new_code_docs_without_historical_immutable_reference':[p.relative_to(R).as_posix() for p in newcode if p.relative_to(R).as_posix() not in base_paths],'limitations':limitations}
report['all_preservation_checks_passed']=not unexpected and all(x['match'] for x in check68) and all(f['match'] for group in snapshots+emissions for f in group['files'])
(OUT/'02-preservacao.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['tracked_unchanged','manifest68','canonical_snapshots','canonical_rehearsals']},ensure_ascii=False,indent=2));raise SystemExit(0 if report['all_preservation_checks_passed'] else 1)
