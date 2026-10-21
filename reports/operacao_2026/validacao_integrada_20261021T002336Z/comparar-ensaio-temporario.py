from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,runpy,socket,sys,tempfile
from unittest.mock import patch
R=Path('/Users/MBPaschoal/Dropbox/Projetos pessoais/F1');OUT=Path(__file__).parent;S=Path.home()/'.hermes/cache/scratch';sys.path.insert(0,str(R))
import operar_2026 as cli
from operacao2026 import previsao as op
prior='ensaio-r2-corrigido-20261020';original=R/'reports/operacao_2026/emissoes'/prior
checks=json.loads((OUT/'02-preservacao.json').read_text());assert checks['all_preservation_checks_passed']
old=json.loads((original/'entradas.json').read_text());old_manifest=json.loads((original/'manifesto.json').read_text());assert len(old['ordem'])==15
model_paths=[R/'models/modelo_v1/modelo.joblib',R/'models/modelo_v1/metadados.json',R/'data/preparado/colunas.json'];before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in model_paths};violations=[]
def audit(event,args):
 if event in ('socket.connect','socket.getaddrinfo'):raise AssertionError('Rede real proibida')
 if event=='open' and isinstance(args[0],(str,bytes)):
  mode,flags=args[1:3]
  if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
   p=Path(os.fsdecode(args[0])).resolve()
   if not any(base.resolve() in p.parents for base in (S,OUT)):
    violations.append(str(p));raise AssertionError('Tentativa de escrita fora do temporário/relatório: '+str(p))
sys.addaudithook(audit)
def blocked(*a,**k):raise AssertionError('Rede real bloqueada')
with tempfile.TemporaryDirectory(prefix='pitwall-integrada-',dir=str(S)) as tmp:
 destination=Path(tmp)/'emissoes';destination.mkdir();(destination/prior).symlink_to(original,target_is_directory=True)
 cli.EMISSOES=destination;eid='offline-'+OUT.name.replace('_','-');sys.argv=[str(OUT/'aceite-base-existente.py'),eid,prior]
 with op._sem_fit(),patch.object(socket.socket,'connect',blocked),patch.object(socket,'create_connection',blocked),patch.object(socket,'getaddrinfo',blocked):
  runpy.run_path(str(OUT/'aceite-base-existente.py'),run_name='__main__')
 actual=json.loads((destination/eid/'entradas.json').read_text());manifest=json.loads((destination/eid/'manifesto.json').read_text());accept=json.loads((S/('pitwall-stage8-acceptance-'+eid+'.json')).read_text())
 fields=old['ordem'];prob=['probabilidade_modelo','probabilidade_constante'];rank=['ranking_modelo','favorito_modelo','ranking_classificacao','favorito_classificacao','empates_modelo','empates_classificacao']
 def extract(rows,keys):return [{k:row.get(k) for k in keys} for row in rows]
 report={'utc':datetime.now(timezone.utc).isoformat(),'temporary_execution':True,'canonical_snapshot':accept['snapshot'],'previous_rehearsal':prior,'rows':len(actual['linhas']),'features_order_identical':actual['ordem']==old['ordem'],'features15_identical':actual['matriz']==old['matriz'],'probabilities_identical':extract(actual['linhas'],prob)==extract(old['linhas'],prob),'rankings_identical':extract(actual['linhas'],rank)==extract(old['linhas'],rank),'all_semantic_rows_identical':actual['linhas']==old['linhas'],'execution_metadata_compared_for_equality':False,'new_timestamp':manifest['emitido_em_utc'],'previous_timestamp':old_manifest['emitido_em_utc'],'full_existing_acceptance':accept,'original_model_hashes_unchanged':all(hashlib.sha256(p.read_bytes()).hexdigest()==before[str(p)] for p in model_paths),'forbidden_write_attempts':violations,'network_and_fit_blocked':True,'existing_emissions_not_overwritten':True,'temporary_directory_removed_after_comparison':True}
 report['passed']=all(report[k] for k in ['features_order_identical','features15_identical','probabilities_identical','rankings_identical','all_semantic_rows_identical','original_model_hashes_unchanged']) and not violations
 with (OUT/'03-ensaio.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps(report,ensure_ascii=False,indent=2));assert report['passed']
