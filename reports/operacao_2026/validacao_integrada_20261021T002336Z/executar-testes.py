from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,os,socket,sys,unittest
from unittest.mock import patch
R=Path('/Users/MBPaschoal/Dropbox/Projetos pessoais/F1');OUT=Path(__file__).parent;S=Path.home()/'.hermes/cache/scratch';sys.path.insert(0,str(R))
from operacao2026 import previsao
names=['tests.'+p.stem for p in sorted((R/'tests').glob('test_operacao_2026*.py'))]
violations=[]
def audit(event,args):
 if event in ('socket.connect','socket.getaddrinfo'):raise AssertionError('Rede real bloqueada')
 if event=='open' and isinstance(args[0],(str,bytes)):
  mode,flags=args[1:3]
  if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
   p=Path(os.fsdecode(args[0])).resolve()
   if not any(base.resolve() in p.parents for base in (S,OUT)):
    violations.append(str(p));raise AssertionError('Escrita fora das pastas de verificação: '+str(p))
sys.addaudithook(audit)
def blocked(*a,**k):raise AssertionError('Rede real proibida')
suite=unittest.defaultTestLoader.loadTestsFromNames(names)
with previsao._sem_fit(),patch.object(socket.socket,'connect',blocked),patch.object(socket,'create_connection',blocked),patch.object(socket,'getaddrinfo',blocked):
 result=unittest.TextTestRunner(verbosity=2).run(suite)
report={'utc':datetime.now(timezone.utc).isoformat(),'execucoes_da_suite_nesta_entrega':1,'modules':names,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'all_passed':result.wasSuccessful(),'network_blocked':True,'fit_fit_transform_partial_fit_blocked':True,'forbidden_write_attempts':violations,'failure_details':[str(x) for x in result.failures+result.errors]}
(OUT/'01-testes.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if result.wasSuccessful() and not violations else 1)
