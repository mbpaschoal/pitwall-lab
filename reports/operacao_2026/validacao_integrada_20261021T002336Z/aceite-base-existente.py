"""Aceite real: ensaio sem ler resultado-alvo; sem rede ou fit."""
from pathlib import Path
import sys,json,hashlib,math,datetime
R=Path('/Users/MBPaschoal/Dropbox/Projetos pessoais/F1');S=Path.home()/'.hermes/cache/scratch';sys.path.insert(0,str(R))
import operar_2026 as cli
from operacao2026 import previsao as op
snap='coleta-20261019T164713Z';base=cli.SNAPSHOTS/snap;idx=json.loads((base/'indice.json').read_text())
calendar=[]
for src in idx['fontes']:
 if src['endpoint']=='calendario':calendar+=json.loads((base/src['arquivo']).read_text())['MRData']['RaceTable']['Races']
target=next(x for x in calendar if x['Circuit']['circuitId']=='marina_bay');rd=target['round']
forbidden={(base/x['arquivo']).resolve() for x in idx['fontes'] if x['endpoint']=='resultados' and int(x['rodada'])>=int(rd)};reads=[]
def audit(event,args):
 if event!='open' or not isinstance(args[0],(str,bytes)):return
 p=Path(args[0]).resolve()
 if p in forbidden:raise AssertionError('LEITURA_PROIBIDA_RESULTADO_ALVO_FUTURO:'+str(p))
 if p.parent==base/'raw':reads.append(p.name)
sys.addaudithook(audit)
eid=sys.argv[1] if len(sys.argv)>1 else 'ensaio-integracao-20261019'
previous=sys.argv[2] if len(sys.argv)>2 else 'ensaio-integracao-20261019'
original_writer=op.gravar_emissao
def linked_writer(root,emission_id,data,**kwargs):
 data=dict(data);data['versao_anterior']=previous;data['motivo_correcao']='Novo ensaio após correções operacionais e de proveniência; mesmas entradas e modelo congelado.'
 return original_writer(root,emission_id,data,**kwargs)
op.gravar_emissao=linked_writer
before={str(R/x):hashlib.sha256((R/x).read_bytes()).hexdigest() for x in ['models/modelo_v1/modelo.joblib','models/modelo_v1/metadados.json','data/preparado/colunas.json']}
with op._sem_fit():
 assert cli.main(['estado','--snapshot',snap])==0
 if len(sys.argv)>3 and sys.argv[3]=='verificar-existente':
  fluxo=cli._preparar_fluxo(snap,'marina_bay')
  recalculado=op.inferir(op.carregar_modelo(),fluxo[6])
 else:
  assert cli.main(['ensaio','--snapshot',snap,'--id',eid])==0
out=cli.EMISSOES/eid;manifest=json.loads((out/'manifesto.json').read_text());inputs=json.loads((out/'entradas.json').read_text());hist=json.loads((out/'historicos.json').read_text());meta=json.loads((R/'models/modelo_v1/metadados.json').read_text());learn=meta['parametros_aprendidos'];errors=[]
assert manifest['modo']=='ENSAIO_RETROSPECTIVO';assert len(inputs['ordem'])==15
if len(sys.argv)>3 and sys.argv[3]=='verificar-existente':assert recalculado==inputs['linhas']
history_sets = [hist['registros']] if 'registros' in hist else [hist['resultados_lidos'], hist['resultados_fornecidos']]
for records in history_sets:
 assert all(str(x['evento'][0])!='2026' or int(x['evento'][1])<int(rd) for x in records), 'Resultado alvo/futuro no histórico'
for name,h in manifest['hashes_saidas'].items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==h
for row in inputs['linhas']:
 assert 'podio' not in row and 'posicao_final' not in row
 if not row['elegivel_previsao']:continue
 vector=[learn['medianas_imputador'][i] if row[f] is None else float(row[f]) for i,f in enumerate(meta['entradas'])]
 z=learn['intercepto']+math.fsum((x-learn['media_normalizador'][i])/learn['escala_normalizador'][i]*learn['coeficientes'][i] for i,x in enumerate(vector));p=1/(1+math.exp(-z));err=abs(p-row['probabilidade_modelo']);errors.append(err);assert err<1e-12
for p,h in before.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
report={'ensaiado_em_utc':manifest['emitido_em_utc'],'verificado_em_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'emissao':eid,'modo':'ENSAIO_RETROSPECTIVO','fonte':'DADOS_REAIS_JOLPICA','snapshot':snap,'alvo_rodada_descoberta':rd,'linhas':len(inputs['linhas']),'elegiveis':sum(bool(x['elegivel_previsao']) for x in inputs['linhas']),'ordem_15_entradas':inputs['ordem']==meta['entradas'],'raw_alvo_e_futuro_bloqueados_por_audit_hook':True,'raw_lidos':sorted(set(reads)),'fit_fit_transform_partial_fit_bloqueados':True,'sem_resultados_alvo_nas_saidas':True,'hashes_todas_saidas_e_modelo_preservados':True,'probabilidade_oraculo_sigmoid_metadados_sem_fit':True,'max_erro_probabilidade':max(errors),'git':manifest['git'],'favoritos_modelo':[x['piloto_id'] for x in inputs['linhas'] if x.get('favorito_modelo')],'favoritos_classificacao':[x['piloto_id'] for x in inputs['linhas'] if x.get('favorito_classificacao')],'nao_e_previsao_real_de_austin':True}
(S/('pitwall-stage8-acceptance-'+eid+'.json')).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))

old=json.loads((cli.EMISSOES/previous/'entradas.json').read_text());assert inputs['linhas']==old['linhas'];assert inputs['matriz']==old['matriz'];assert inputs['ordem']==old['ordem'];print('ENTRADAS_PROBABILIDADES_RANKINGS_IDENTICOS_A_VERSAO_ANTERIOR',previous)
