"""Local error diagnosis and fixed temporal qualifying-gap experiment.

No network, executable v1 model, collectors, or operational emissions are used.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import re

import numpy as np
from scipy.special import expit
from threadpoolctl import threadpool_limits

from .calibration_v2 import load_dataset, _partition, _check_temporal_partition
from .run_calibration_v2 import evaluate_methods, paired_interval, preservation, key
from .run_statsmodels_audit import _rows, _json, _csv, _sha
from .statsmodels_audit import _preprocess, fit_ridge

PARENT = "reports/erros_gaps_q_20261102"
PRIOR = "reports/modelo_v2_calibracao_20261102/run-001"
PHASES = ("Q1", "Q2", "Q3")
SUPPORT = tuple("q_gap_missing_"+q for q in PHASES)+tuple("q_n_valid_"+q for q in PHASES)
GAPS = tuple("q_gap_pct_"+q for q in PHASES)
METHODS = ("v1_temporal", "q_probability", "v1_q_support", "v1_q_gaps")
PROTOCOL = "docs/experimento_gaps_q_20261102.md"


def seconds(value):
    """A missing/invalid time stays missing, never a zero-duration lap."""
    if not isinstance(value, str) or not re.fullmatch(r"\d+:[0-5]\d\.\d{3}", value):
        return None
    minutes, rest = value.split(":")
    result = int(minutes)*60+float(rest)
    return result if math.isfinite(result) and result>0 else None


def phase_features(records):
    """Compare each phase only to its own positive-time minimum."""
    result = {driver:{} for driver in records}
    for phase in PHASES:
        times = {d:seconds(r.get(phase)) for d,r in records.items()}
        valid = [v for v in times.values() if v is not None]
        reference = min(valid) if len(valid)>=2 else None
        for driver,time in times.items():
            gap = 100*(time/reference-1) if time is not None and reference is not None else None
            result[driver].update({"q_gap_pct_"+phase:gap,"q_gap_missing_"+phase:int(gap is None),"q_n_valid_"+phase:len(valid)})
    return result


def local_gaps(root, rows, identification):
    root=Path(root); canonical={key(r):r for r in rows}; sources={}; sessions=defaultdict(dict); conflicts=[]
    if len(canonical)!=len(rows) or any(k[0] not in range(2021,2026) for k in canonical):raise ValueError("unique retrospective identities required")
    for year in range(2021,2026):
        pages=[]
        for path in sorted((root/"data/historico"/str(year)/"raw").glob("classificacao_offset_*.json")):
            receipt=path.parent.parent/"proveniencia"/path.name
            if not receipt.is_file() or json.loads(receipt.read_text()).get("sha256")!=_sha(path):
                raise ValueError("qualifying source hash/receipt mismatch: "+str(path))
            sources[str(path.relative_to(root))]=_sha(path);sources[str(receipt.relative_to(root))]=_sha(receipt)
            mr=json.loads(path.read_text())["MRData"]
            if int(mr["RaceTable"]["season"])!=year:raise ValueError("source season mismatch")
            flat=[]
            for race in mr["RaceTable"]["Races"]:
                if int(race["season"])!=year:raise ValueError("race season mismatch")
                for record in race.get("QualifyingResults",[]):flat.append((int(race["round"]),record))
            pages.append((int(mr["offset"]),int(mr["limit"]),int(mr["total"]),flat))
        if not pages:raise ValueError("missing canonical qualifying pages")
        expected=0;total=pages[0][2]
        for offset,limit,declared,flat in sorted(pages):
            if offset!=expected or declared!=total or limit<=0 or len(flat)>limit:raise ValueError("qualifying pagination incomplete or inconsistent")
            expected+=len(flat)
            for race,record in flat:
                driver=record["Driver"]["driverId"];identity=(year,race,driver)
                if driver in sessions[(year,race)]:raise ValueError("duplicate qualifying identity")
                sessions[(year,race)][driver]=record
                if identity not in canonical:conflicts.append({"key":list(identity),"reason":"raw identity absent from prepared population"});continue
                prepared=canonical[identity];meta=identification[identity]
                if str(record.get("Constructor",{}).get("constructorId",""))!=meta["equipe_id_entrada"] or (prepared["posicao_classificacao"] is not None and float(record["position"])!=prepared["posicao_classificacao"]):
                    conflicts.append({"key":list(identity),"reason":"qualifying team/position conflict"})
        if expected!=total:raise ValueError("qualifying pages do not reach declared total")
    features={}
    for gp,records in sorted(sessions.items()):
        for driver,values in phase_features(records).items():features[gp+(driver,)]=values
    coverage=[]
    for year in range(2021,2026):
        eligible=[r for r in rows if r["temporada"]==year and r["elegivel_previsao"]]
        gps={key(r)[:2] for r in eligible}
        counts={q:sum(features.get(key(r),{}).get("q_gap_pct_"+q) is not None for r in eligible) for q in PHASES}
        invalid={"invalid_times_"+q:sum(r.get(q) not in (None,"") and seconds(r.get(q)) is None for gp,records in sessions.items() if gp[0]==year for r in records.values()) for q in PHASES}
        coverage.append({"year":year,"eligible_rows":len(eligible),"n_gp":len(gps),"gps_with_source":len(gps & sessions.keys()),**{"valid_"+q:counts[q] for q in PHASES},**invalid,"Q1_fraction":counts["Q1"]/len(eligible) if eligible else 0})
    passed=not conflicts and all(c["gps_with_source"]==c["n_gp"] and c["Q1_fraction"]>=.95 for c in coverage)
    for row in rows:
        row.update(features.get(key(row),{**{g:None for g in GAPS},**{"q_gap_missing_"+q:1 for q in PHASES},**{"q_n_valid_"+q:0 for q in PHASES}}))
    return {"status":"sufficient" if passed else "cobertura_insuficiente","seasons":coverage,"conflicts":conflicts,"sources":sources,"features":features}


def preserved_predictions(root, rows):
    root=Path(root);manifest=json.loads((root/PRIOR/"manifest.json").read_text())
    for name,digest in manifest["files"].items():
        if _sha(root/PRIOR/name)!=digest:raise ValueError("previous experiment artefact changed")
    canonical={key(r):r for r in rows};output=[]
    for row in _rows(root/PRIOR/"predictions.csv"):
        if row["metodo"] not in ("v1_temporal","q_probability"):continue
        k=key(row)
        if k not in canonical:raise ValueError("preserved prediction key mismatch")
        target=None if row["podio"]=="" else int(row["podio"])
        if target!=canonical[k]["podio"]:raise ValueError("preserved target mismatch")
        output.append({"metodo":row["metodo"],"temporada":k[0],"rodada":k[1],"piloto_id":k[2],"probabilidade":None if not row["probabilidade"] else float(row["probabilidade"]),"podio":target})
    return output


def diagnose(predictions, identification, audit):
    cases=[];groups=defaultdict(list)
    for p in predictions:
        if p["metodo"]!="v1_temporal" or p["probabilidade"] is None or p["podio"] is None:continue
        k=key(p);meta=identification[k];prob=p["probabilidade"];y=p["podio"]
        assigned=prob if y else 1-prob
        if assigned<=0:raise ValueError("non-finite log loss in preserved prediction")
        pos=meta.get("_q")
        bucket="missing" if pos is None else ("1-3" if pos<=3 else "4-6" if pos<=6 else "7-10" if pos<=10 else "11+")
        r={**p,"corrida":meta["corrida"],"circuito_id":meta["circuito_id"],"equipe_id_entrada":meta["equipe_id_entrada"],"qualifying_bucket":bucket,"status_posterior":audit.get(k,{}).get("status"),"brier":(prob-y)**2,"log_loss":-math.log(assigned)}
        cases.append(r)
        labels={"year":str(k[0]),"gp":"{}/{} {}".format(k[0],k[1],meta["corrida"]),"driver":k[2],"team":meta["equipe_id_entrada"],"circuit":meta["circuito_id"],"qualifying":bucket,"probability_bin":str(min(9,int(prob*10)))}
        for dimension,value in labels.items():groups[(dimension,value)].append(r)
    summaries=[]
    for (dimension,value),values in sorted(groups.items()):
        n=len(values)
        summaries.append({"dimension":dimension,"group":value,"n":n,"n_gp":len({key(r)[:2] for r in values}),"mean_probability":sum(r["probabilidade"] for r in values)/n,"observed_rate":sum(r["podio"] for r in values)/n,"brier":sum(r["brier"] for r in values)/n,"log_loss":sum(r["log_loss"] for r in values)/n})
    return {"n":len(cases),"high_confidence_failures":sum(r["probabilidade"]>=.7 and not r["podio"] for r in cases),"underestimated_podiums":sum(r["probabilidade"]<=.1 and r["podio"] for r in cases),"worst_cases":sorted(cases,key=lambda r:(-r["log_loss"],key(r)))[:20],"worst_gps":sorted([g for g in summaries if g["dimension"]=="gp"],key=lambda g:-g["log_loss"])[:10],"groups":summaries,"cases":cases}


def fit_candidate(training, external, features):
    """New design; frozen base features and existing producers are untouched."""
    if any(r['temporada'] not in range(2021,2026) for r in training+external):raise ValueError("2026 and future seasons are not admitted")
    _check_temporal_partition(training,external)
    raw=np.array([[np.nan if r[f] is None else r[f] for f in features] for r in training],float)
    z,med,mean,scale=_preprocess(raw)
    fitted=fit_ridge(z,[r["podio"] for r in training])
    if not fitted["converged"]:raise ValueError("gap candidate failed gradient convergence")
    x=np.array([[np.nan if r[f] is None else r[f] for f in features] for r in external],float)
    p=expit(fitted["intercept"]+((np.where(np.isnan(x),med,x)-mean)/scale)@np.array(fitted["coef"]))
    return p.tolist(),{**fitted,"features":list(features),"medians":med.tolist(),"means":mean.tolist(),"scales":scale.tolist(),"train_partition":_partition(training,features,True),"predict_partition":_partition(external,features,False)}


def experiment(rows,baseline_predictions):
    from .calibration_v2 import FEATURES_V1
    if any(r['temporada'] not in range(2021,2026) for r in rows):raise ValueError("only retrospective seasons are admitted")
    predictions=list(baseline_predictions);fits=[]
    for year in (2022,2023,2024,2025):
        train=[r for r in rows if r["temporada"]<year and r["elegivel_previsao"] and r["podio"] is not None]
        population=[r for r in rows if r["temporada"]==year];external=[r for r in population if r["elegivel_previsao"]]
        for method,extra in (("v1_q_support",SUPPORT),("v1_q_gaps",SUPPORT+GAPS)):
            print("fit",year,method,flush=True)
            values,model=fit_candidate(train,external,FEATURES_V1+extra)
            model.update(method=method,year=year);fits.append(model)
            available={key(r):p for r,p in zip(external,values)}
            predictions.extend({"metodo":method,"temporada":r["temporada"],"rodada":r["rodada"],"piloto_id":r["piloto_id"],"probabilidade":available.get(key(r)),"podio":r["podio"]} for r in population)
    evaluation=evaluate_methods([r for r in rows if r["temporada"]>=2022],predictions,methods=METHODS)
    contrasts=[]
    for reference in ("v1_temporal","q_probability","v1_q_support"):
        c=paired_interval(evaluation["gp_scores"]["v1_q_gaps"],evaluation["gp_scores"][reference]);c.update(candidate="v1_q_gaps",reference=reference)
        required=-.002 if reference!="v1_q_support" else 0
        c["favourable_folds"]=sum(f["brier"]<0 for f in c.get("folds",{}).values())
        c["criteria_met"]=bool(c.get("status")=="ok" and c["delta_brier"]<required and c.get("ci95_brier") and c["ci95_brier"][1]<0 and c["delta_log_loss"]<=0 and c["favourable_folds"]>=3)
        # The original practical threshold includes equality at -0.002.
        if required==-0.002 and c.get("delta_brier")==required and c.get("ci95_brier") and c["ci95_brier"][1]<0 and c["delta_log_loss"]<=0 and c["favourable_folds"]>=3:c["criteria_met"]=True
        contrasts.append(c)
    support=paired_interval(evaluation["gp_scores"]["v1_q_support"],evaluation["gp_scores"]["v1_temporal"]);support.update(candidate="v1_q_support",reference="v1_temporal");contrasts.append(support)
    return {"predictions":predictions,"fits":fits,"evaluation":evaluation,"contrasts":contrasts,"all_primary_criteria_met":all(c["criteria_met"] for c in contrasts[:3]),"automatic_promotion":False}


def write_reports(out,diagnostic,coverage,result):
    for lang in ("pt","en"):
        en=lang=="en"
        lines=["# "+("Error diagnosis and qualifying gaps" if en else "Diagnóstico de erros e gaps de classificação"),"","Created by: MBPaschoal","Status: executed locally; retrospective research","Type: research report","Date: 2026-11-02","","[Português](README.md) · [English](README.en.md)","",
               ("Preserved temporal-v1 errors; groups are descriptive, not causal. Later status is audit only. No new data collection or 2026 fitting." if en else "Erros da réplica temporal v1 preservada; grupos são descritivos, não causais. Status posterior é somente auditoria. Sem coleta nova ou ajuste com 2026."),"",
               "N: {}. High-confidence failures / falhas com confiança alta: {}. Underestimated podiums / pódios subestimados: {}.".format(diagnostic["n"],diagnostic["high_confidence_failures"],diagnostic["underestimated_podiums"]),"",
               "## "+("Largest individual losses" if en else "Maiores perdas individuais"),"","| GP | Piloto / Driver | p | y | Log loss | Status posterior / Later status |","|---|---|---:|---:|---:|---|"]
        for r in diagnostic["worst_cases"][:10]:lines.append("| {} {} | {} | {:.4f} | {} | {:.4f} | {} |".format(r["temporada"],r["corrida"],r["piloto_id"],r["probabilidade"],r["podio"],r["log_loss"],r["status_posterior"]))
        lines += ["","## "+("Local coverage" if en else "Cobertura local"),"",coverage["status"],"","| Ano / Year | N elegível / eligible | GPs | Q1 | Q2 | Q3 |","|---|---:|---:|---:|---:|---:|"]
        for c in coverage["seasons"]:lines.append("| {} | {} | {} | {} | {} | {} |".format(c["year"],c["eligible_rows"],c["n_gp"],c["valid_Q1"],c["valid_Q2"],c["valid_Q3"]))
        lines += ["",("Q2/Q3 absence does not prove elimination. Gaps compare only the same phase. Current captures do not certify historical availability." if en else "Ausência de Q2/Q3 não prova eliminação. Gaps comparam somente a mesma fase. Capturas atuais não certificam disponibilidade histórica."),""]
        if result:
            lines += ["## "+("Temporal evaluation" if en else "Avaliação temporal"),"","| Método / Method | N | GPs | Brier GP | Log loss GP | CITL | Top 3 | Pódios / Podiums |","|---|---:|---:|---:|---:|---:|---:|---:|"]
            for method,d in result["evaluation"]["methods"].items():
                r=d["overall"];lines.append("| {} | {} | {} | {:.6f} | {:.6f} | {:.6f} | {:.4f} | {}/{} |".format(method,r["n"],r["n_gp"],r["brier_mean_gp"],r["log_loss_mean_gp"],r["citl"],r["top3_mean"],r["complete_podiums"],r["top3_n_gp"]))
            lines += ["","| Candidato / Candidate | Referência / Reference | Δ Brier GP | IC95% / CI95% | Δ log loss GP |","|---|---|---:|---|---:|"]
            for c in result["contrasts"]:lines.append("| {} | {} | {:.6f} | {} | {:.6f} |".format(c["candidate"],c["reference"],c["delta_brier"],c["ci95_brier"],c["delta_log_loss"]))
            lines += ["",("All predeclared criteria met: {}. No automatic promotion." if en else "Todos os critérios pré-fixados atendidos: {}. Sem promoção automática.").format(result["all_primary_criteria_met"]),"",("Previously explored 2022–2025 folds use prior-year training, identical eligibility and cohorts, C=1, training-only transforms. Paired intervals use 2,000 two-GP blocks within seasons, seed42, conditional on fitted predictions. Raw qualifying receives ranking metrics only. Detailed per-fold scores/calibration/bins/raw ranking live in evaluation.json. Smaller average losses do not by themselves establish calibration or causality." if en else "Folds 2022–2025 já explorados usam treino nos anos anteriores, mesma elegibilidade/coortes, C=1 e transformações somente no treino. ICs pareados usam 2.000 blocos de dois GPs dentro da temporada, seed42, condicionais às previsões ajustadas. Classificação bruta recebe somente ranking. Escores por fold/calibração/faixas/ranking bruto estão em evaluation.json. Perdas médias menores não demonstram isoladamente calibração ou causalidade."),""]
        lines += ["[Diagnosis](diagnosis.json) · [Groups](error_groups.csv) · [Cases](error_cases.csv) · [Coverage](coverage.json) · [Features](gap_features.csv) · [Preservation](preservation.json) · [Frozen execution](execution_frozen.json) · [Manifest](manifest.json)",""]
        (out/("README.en.md" if en else "README.md")).write_text("\n".join(lines))


def plot_results(out, diagnostic, result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),constrained_layout=True)
    worst=diagnostic["worst_gps"][:8]
    axes[0].barh([g["group"] for g in worst][::-1],[g["log_loss"] for g in worst][::-1],color="#135E82")
    axes[0].set_title("Maiores perdas / Largest losses — v1 temporal")
    axes[0].set_xlabel("Log loss por piloto / per driver")
    if result:
        for method,data in result["evaluation"]["methods"].items():
            years=list(data["folds"])
            axes[1].plot(years,[data["folds"][y]["brier_mean_gp"] for y in years],marker="o",label=method)
        axes[1].legend(fontsize=8);axes[1].set_ylabel("Brier médio GP / GP mean Brier")
    axes[1].set_title("Validação temporal / Temporal validation")
    fig.savefig(out/"diagnosis_experiment.png",dpi=160);plt.close(fig)


def run(root,out):
    root=Path(root).resolve();out=Path(out).resolve();parent=root/PARENT
    if out.exists() or out==parent or not out.is_relative_to(parent):raise ValueError("output must be a new child of the experiment directory")
    baseline=json.loads((parent/"protected_before.json").read_text())
    if preservation(root,baseline)["status"]!="preserved":raise ValueError("protected source changed before run")
    paths=[PROTOCOL,"pitwall/research/qualifying_gaps.py","tests/test_qualifying_gaps.py","pitwall/research/calibration_v2.py","pitwall/research/run_calibration_v2.py","pitwall/research/statsmodels_audit.py","requirements_statsmodels_audit.txt",PRIOR+"/predictions.csv","data/preparado/identificacao.csv","data/preparado/auditoria_resultados.csv"]
    paths += ["data/preparado/"+p for p in ("treino.csv","validacao.csv","teste_final_reservado.csv","colunas.json")]
    paths += [str(p.relative_to(root)) for p in sorted((root/"data/historico").glob("*/raw/classificacao_offset_*.json"))]+[str(p.relative_to(root)) for p in sorted((root/"data/historico").glob("*/proveniencia/classificacao_offset_*.json"))]
    frozen={"hashes":{p:_sha(root/p) for p in paths},"config":{"C":1,"folds":[2022,2023,2024,2025],"primary":"v1_q_gaps","support_ablation":"v1_q_support","Q1_coverage_gate":.95,"bootstrap_replicates":2000,"seed":42}}
    out.mkdir(parents=True);_json(out/"execution_frozen.json",frozen)
    try:
        with threadpool_limits(limits=1):
            rows=load_dataset(root);identification={key(r):r for r in _rows(root/"data/preparado/identificacao.csv")};audit={key(r):r for r in _rows(root/"data/preparado/auditoria_resultados.csv")}
            if set(identification)!={key(r) for r in rows}:raise ValueError("identification population mismatch")
            for r in rows:identification[key(r)]["_q"]=r["posicao_classificacao"]
            predicted=preserved_predictions(root,rows);diagnostic=diagnose(predicted,identification,audit)
            _json(out/"diagnosis.json",{k:v for k,v in diagnostic.items() if k!="cases"});_csv(out/"error_groups.csv",diagnostic["groups"]);_csv(out/"error_cases.csv",diagnostic["cases"])
            try:coverage=local_gaps(root,rows,identification)
            except ValueError as error:coverage={"status":"cobertura_insuficiente","reason":str(error),"seasons":[],"conflicts":[],"sources":{}}
            _json(out/"coverage.json",{k:v for k,v in coverage.items() if k!="features"})
            _csv(out/"gap_features.csv",[{"temporada":r["temporada"],"rodada":r["rodada"],"piloto_id":r["piloto_id"],**{f:r.get(f) for f in SUPPORT+GAPS}} for r in rows])
            result=None
            if coverage["status"]=="sufficient":
                result=experiment(rows,predicted);_json(out/"experiment.json",result);_json(out/"evaluation.json",result["evaluation"]);_csv(out/"predictions.csv",result["predictions"])
            write_reports(out,diagnostic,coverage,result)
            plot_results(out,diagnostic,result)
        after=preservation(root,baseline);_json(out/"preservation.json",after)
        if after["status"]!="preserved" or any(_sha(root/p)!=v for p,v in frozen["hashes"].items()):raise ValueError("source or code changed during experiment")
        manifest={"status":"completed" if result else "cobertura_insuficiente","protected_files":after["checked_files"],"all_primary_criteria_met":result["all_primary_criteria_met"] if result else False,"automatic_promotion":False,"files":{p.name:_sha(p) for p in sorted(out.iterdir()) if p.is_file()}}
        _json(out/"manifest.json",manifest);return manifest
    except Exception as error:
        _json(out/"failure.json",{"error":str(error),"preservation":preservation(root,baseline)});raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument("--destination",type=Path);a=p.parse_args()
    print(json.dumps(run(a.root,a.destination or a.root/PARENT/"run-001")))


if __name__=="__main__":main()
