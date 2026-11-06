"""Explicit source-admission addendum; original audit/code remain untouched."""
import copy
import json
from pathlib import Path

from threadpoolctl import threadpool_limits
from pitwall.data.adjudication import TabelaHTML
from . import qualifying_gaps as q
from .calibration_v2 import load_dataset

SOURCE="data/acervo_historico/resolucao-20261029"
ADDENDUM="docs/adendo_gaps_q_miami_20261102.md"
TEAMS={'red_bull':'Red Bull Racing','mclaren':'McLaren','mercedes':'Mercedes','ferrari':'Ferrari','williams':'Williams','aston_martin':'Aston Martin','alpine':'Alpine','haas':'Haas F1 Team','sauber':'Kick Sauber','rb':'Racing Bulls','racing_bulls':'Racing Bulls'}


def reconcile(html, canonical):
    parser=TabelaHTML();parser.feed(html)
    if ['Pos.','No.','Driver','Team','Q1','Q2','Q3','Laps'] not in parser.rows:raise ValueError('unrecognized official qualifying table')
    official=[r for r in parser.rows if len(r)==8 and r[1].isdigit()]
    if len(official)!=20 or len(canonical)!=20:raise ValueError('Miami requires 20 canonical and official drivers')
    by_number={r['number']: (driver,r) for driver,r in canonical.items()}
    if len(by_number)!=20 or {r[1] for r in official}!=set(by_number):raise ValueError('official/canonical car-number identities disagree')
    merged=copy.deepcopy(canonical);changes=[]
    for position,number,label,team,t1,t2,t3,laps in official:
        driver,original=by_number[number];code=original['Driver']['code']
        if not code or not label.endswith(code) or str(original['position'])!=position or TEAMS.get(original['Constructor']['constructorId'])!=team:raise ValueError('official driver code/position/team conflict')
        for phase,value in zip(q.PHASES,(t1,t2,t3)):
            previous=original.get(phase)
            if previous not in (None,'') and previous!=value:raise ValueError('populated canonical time conflicts with supplement')
            if previous in (None,'') and value:
                if q.seconds(value) is None:raise ValueError('invalid official supplemental time')
                merged[driver][phase]=value;changes.append({'temporada':2025,'rodada':6,'piloto_id':driver,'number':number,'driver_code':code,'phase':phase,'previous':previous,'supplement':value})
    return merged,changes


def recover(root,rows,identification,coverage):
    root=Path(root);base=root/SOURCE;path=base/'fontes/f1_q_2025_miami.bin'
    manifest=json.loads((base/'MANIFESTO_RESOLUCAO.json').read_text());receipts=json.loads((base/'fontes/recibos.json').read_text())
    receipt=[r for r in receipts if r['id']=='f1_q_2025_miami']
    if len(receipt)!=1:raise ValueError('ambiguous source receipt')
    receipt=receipt[0];digest=q._sha(path);url='https://www.formula1.com/en/results/2025/races/1259/miami/qualifying'
    if digest!=manifest['arquivos']['fontes/f1_q_2025_miami.bin'] or receipt['sha256']!=digest or receipt['status']!=200 or receipt['url']!=url or receipt['ano']!=2025 or receipt['slug']!='miami':raise ValueError('official supplement provenance mismatch')
    raw={}
    for file in sorted((root/'data/historico/2025/raw').glob('classificacao_offset_*.json')):
        for race in json.loads(file.read_text())['MRData']['RaceTable']['Races']:
            if int(race['season'])==2025 and int(race['round'])==6:
                for record in race['QualifyingResults']:raw[record['Driver']['driverId']]=record
    for driver in raw:
        if identification[(2025,6,driver)]['circuito_id']!='miami':raise ValueError('supplement wrong circuit')
    merged,changes=reconcile(path.read_text(),raw);features=q.phase_features(merged)
    for row in rows:
        if q.key(row)[:2]==(2025,6):row.update(features[row['piloto_id']])
    updated=copy.deepcopy(coverage)
    for item in updated['seasons']:
        eligible=[r for r in rows if r['temporada']==item['year'] and r['elegivel_previsao']]
        for phase in q.PHASES:item['valid_'+phase]=sum(r['q_gap_pct_'+phase] is not None for r in eligible)
        item['Q1_fraction']=item['valid_Q1']/item['eligible_rows']
    updated['status']='sufficient' if not updated['conflicts'] and all(r['Q1_fraction']>=.95 and r['gps_with_source']==r['n_gp'] for r in updated['seasons']) else 'cobertura_insuficiente'
    updated['supplement']={'source':str(path.relative_to(root)),'sha256':digest,'url':url,'obtido_em_utc':receipt.get('obtido_em_utc'),'historical_availability_proven':False,'changed_times':len(changes),'identity_rule':'same GP; number, literal driver code, position, documented team'}
    return updated,changes


def run(root,out):
    root=Path(root).resolve();out=Path(out).resolve();parent=root/q.PARENT
    if out.exists() or out==parent or not out.is_relative_to(parent):raise ValueError('new experiment child required')
    baseline=json.loads((parent/'protected_before_supplement.json').read_text())
    if q.preservation(root,baseline)['status']!='preserved':raise ValueError('protected sources differ')
    frozen=json.loads((parent/'run-001/execution_frozen.json').read_text())
    for relative in (ADDENDUM,'pitwall/research/qualifying_gaps_miami.py','tests/test_qualifying_gaps_miami.py','pitwall/data/adjudication.py',SOURCE+'/fontes/f1_q_2025_miami.bin',SOURCE+'/fontes/recibos.json',SOURCE+'/MANIFESTO_RESOLUCAO.json'):
        frozen['hashes'][relative]=q._sha(root/relative)
    if any(q._sha(root/p)!=v for p,v in frozen['hashes'].items()):raise ValueError('previous code/input changed')
    frozen['source_addendum']=ADDENDUM;out.mkdir(parents=True);q._json(out/'execution_frozen.json',frozen)
    try:
        with threadpool_limits(limits=1):
            rows=load_dataset(root);ident={q.key(r):r for r in q._rows(root/'data/preparado/identificacao.csv')};audit={q.key(r):r for r in q._rows(root/'data/preparado/auditoria_resultados.csv')}
            for r in rows:ident[q.key(r)]['_q']=r['posicao_classificacao']
            predictions=q.preserved_predictions(root,rows);diagnostic=q.diagnose(predictions,ident,audit)
            q._json(out/'diagnosis.json',{k:v for k,v in diagnostic.items() if k!='cases'});q._csv(out/'error_cases.csv',diagnostic['cases']);q._csv(out/'error_groups.csv',diagnostic['groups'])
            coverage=q.local_gaps(root,rows,ident);coverage,changes=recover(root,rows,ident,coverage)
            q._json(out/'coverage.json',{k:v for k,v in coverage.items() if k!='features'});q._csv(out/'supplement_changes.csv',changes)
            q._csv(out/'gap_features.csv',[{'temporada':r['temporada'],'rodada':r['rodada'],'piloto_id':r['piloto_id'],**{f:r[f] for f in q.SUPPORT+q.GAPS}} for r in rows])
            result=None
            if coverage['status']=='sufficient':
                result=q.experiment(rows,predictions);q._json(out/'experiment.json',result);q._json(out/'evaluation.json',result['evaluation']);q._csv(out/'predictions.csv',result['predictions'])
            q.write_reports(out,diagnostic,coverage,result);q.plot_results(out,diagnostic,result)
        after=q.preservation(root,baseline);q._json(out/'preservation.json',after)
        if after['status']!='preserved' or any(q._sha(root/p)!=v for p,v in frozen['hashes'].items()):raise ValueError('source/code changed during run')
        manifest={'status':'completed' if result else 'cobertura_insuficiente','protected_files':after['checked_files'],'all_primary_criteria_met':result['all_primary_criteria_met'] if result else False,'automatic_promotion':False,'files':{p.name:q._sha(p) for p in sorted(out.iterdir()) if p.is_file()}}
        q._json(out/'manifest.json',manifest);return manifest
    except Exception as error:
        q._json(out/'failure.json',{'error':str(error),'preservation':q.preservation(root,baseline)});raise


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];print(json.dumps(run(root,root/q.PARENT/'run-002')))
