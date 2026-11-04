"""Offline F1DB/Pirelli supplements. No network, model fitting or inference.

Canonical values remain available beside candidates. Only reviewed FIA claims
can replace qualifying values in a newly generated descriptive projection.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlparse
import zipfile

SCHEMA = "pitwall-complementary-sources-v1"
FIELDS = {"q1", "q2", "q3", "posicao", "estado"}
ASSET = "frontend_assets/complemento_fontes_v1.json"
APPROVED_SHA256 = "4bdae38750d73989e7d90e631c0d0aa56a322f0e920963e7f5ce482873ae60cb"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc(value):
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("Timestamp requires timezone")
    return d.astimezone(timezone.utc)


def dump(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n").encode()


def seal(value):
    value["conteudo_sha256"] = sha(dump({k:v for k,v in value.items() if k != "conteudo_sha256"}))
    return value


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def lap(value):
    if value in (None, ""):
        return None
    if not re.fullmatch(r"\d+:\d{2}\.\d{3}", value):
        raise ValueError("Invalid qualifying time")
    m, s = value.split(":")
    if Decimal(s) >= 60:
        raise ValueError("Invalid seconds")
    return int((Decimal(m)*60+Decimal(s))*1000)


def time_text(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Invalid milliseconds")
    seconds, ms = divmod(value,1000)
    minutes, seconds = divmod(seconds,60)
    return "{}:{:02d}.{:03d}".format(minutes,seconds,ms)


def _source(root, spec, host):
    relative = Path(spec["arquivo"])
    path = root / relative
    if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Source path outside evidence directory")
    raw = path.read_bytes()
    u = urlparse(spec["url"])
    if u.scheme != "https" or u.hostname != host or u.username or u.password:
        raise ValueError("Unexpected source origin")
    if spec.get("status") != 200 or not raw or sha(raw) != spec["sha256"]:
        raise ValueError("Source hash/status mismatch")
    utc(spec["obtido_em_utc"])
    return raw


def _canonical(document, year, round_):
    mr = document["MRData"]
    races = mr["RaceTable"]["Races"]
    if len(races) != 1 or int(mr["offset"]) != 0:
        raise ValueError("Partial/ambiguous canonical event")
    race = races[0]
    rows = race.get("QualifyingResults", [])
    if (int(race["season"]),int(race["round"])) != (year,round_) or not rows or int(mr["total"]) != len(rows):
        raise ValueError("Incomplete canonical event")
    if len({r["number"] for r in rows}) != len(rows):
        raise ValueError("Duplicate driver number")
    return race,rows


def _distance(a,b):
    x,y,z,w = map(math.radians, (*a,*b))
    h = math.sin((z-x)/2)**2 + math.cos(x)*math.cos(z)*math.sin((w-y)/2)**2
    return 12742*math.asin(min(1,math.sqrt(h)))


def build(plan_path):
    plan_path = Path(plan_path)
    root, plan = plan_path.parent, read(plan_path)
    if plan.get("schema") != "pitwall-complementary-plan-v1":
        raise ValueError("Unknown source plan")
    f = plan["f1db"]
    raw = _source(root,f,"github.com")
    tag = f["release"]
    if not re.fullmatch(r"v\d{4}\.\d+\.\d+",tag) or urlparse(f["url"]).path != "/f1db/f1db/releases/download/"+tag+"/f1db-json-splitted.zip":
        raise ValueError("Release URL not pinned")
    import io
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if len(z.namelist()) != len(set(z.namelist())) or sum(x.file_size for x in z.infolist()) > 200*1024**2:
            raise ValueError("Invalid archive limits/members")
        tables = {n:json.loads(z.read("f1db-"+n+".json")) for n in ("races","races-qualifying-results","drivers","circuits")}
    drivers = {d["id"]:d for d in tables["drivers"]}
    circuits = {c["id"]:c for c in tables["circuits"]}
    events, seen = [], set()
    for spec in plan["canonical"]:
        year, rnd = spec["temporada"],spec["rodada"]
        if (year,rnd) in seen:
            raise ValueError("Duplicate event")
        seen.add((year,rnd))
        jr,jrows = _canonical(json.loads(_source(root,spec,"api.jolpi.ca")),year,rnd)
        races = [r for r in tables["races"] if (r["year"],r["round"]) == (year,rnd)]
        if len(races) != 1:
            raise ValueError("Missing/ambiguous F1DB event")
        fr = races[0]
        circuit = circuits[fr["circuitId"]]
        loc = jr["Circuit"]["Location"]
        if fr["date"] != jr["date"] or _distance((circuit["latitude"],circuit["longitude"]),(float(loc["lat"]),float(loc["long"]))) > 5:
            raise ValueError("Event date/circuit mismatch")
        frows = [r for r in tables["races-qualifying-results"] if r["raceId"] == fr["id"]]
        fm = {str(r["driverNumber"]):r for r in frows}
        if len(fm) != len(frows):
            raise ValueError("Ambiguous F1DB identity")
        rows=[]
        for j in jrows:
            candidate = fm.get(j["number"])
            if candidate is None:
                continue
            if drivers[candidate["driverId"]]["dateOfBirth"] != j["Driver"]["dateOfBirth"]:
                raise ValueError("Driver birth date mismatch")
            canonical = {q:time_text(lap(j.get(q.upper()))) for q in ("q1","q2","q3")}
            proposed={}
            for q in ("q1","q2","q3"):
                v = candidate.get(q+"Millis")
                if v != lap(candidate.get(q)):
                    raise ValueError("F1DB phase milliseconds/text disagree")
                proposed[q]=time_text(v)
            canonical.update(posicao=int(j["position"]),estado=None)
            proposed.update(posicao=candidate["positionNumber"],estado=candidate["positionText"])
            rows.append({"numero":int(j["number"]),"piloto_id":j["Driver"]["driverId"],
                "f1db_driver_id":candidate["driverId"],"canonical":canonical,"candidate":proposed,"admitted":{},
                "uso":"descriptive_posterior_only"})
        events.append({"temporada":year,"rodada":rnd,"circuito_id":jr["Circuit"]["circuitId"],
            "data_corrida":jr["date"],"f1db_circuit_id":fr["circuitId"],"layout_id":fr["circuitLayoutId"],
            "canonical_source":spec,"rows":rows,
            "unmatched_canonical_numbers":[int(r["number"]) for r in jrows if r["number"] not in fm]})
    proofs=[]
    for claim in plan.get("fia_claims",[]):
        raw_proof = _source(root,claim["source"],"www.fia.com")
        if not raw_proof.startswith(b"%PDF") or not claim.get("reviewed_by") or claim.get("page",0) < 1:
            raise ValueError("Reviewed PDF required")
        if str(claim["temporada"]) not in urlparse(claim["source"]["url"]).path:
            raise ValueError("FIA document season mismatch")
        event = next(e for e in events if (e["temporada"],e["rodada"]) == (claim["temporada"],claim["rodada"]))
        row = next(r for r in event["rows"] if r["numero"] == claim["numero"])
        field,value = claim["field"],claim["value"]
        if field not in FIELDS or field in row["admitted"]:
            raise ValueError("Invalid/duplicate FIA field")
        if field.startswith("q"):
            lap(value)
        elif field == "estado" and value not in ("DSQ","DNS","NC"):
            raise ValueError("Unsupported status")
        elif field == "posicao" and value is not None and (type(value) is not int or value < 1):
            raise ValueError("Invalid official position")
        row["admitted"][field] = {"value":value,"source":claim["source"],"reviewed_by":claim["reviewed_by"],"page":claim["page"]}
        proofs.append(claim)
    contexts=[]
    for c in plan.get("pirelli",[]):
        article=_source(root,c["source"],"press.pirelli.com").decode("utf-8")
        match = re.search(r'"datePublished"\s*:\s*"([^"]+)"',article)
        if not match or match[1] != c["published_at"] or utc(c["published_at"]) > utc(c["source"]["obtido_em_utc"]):
            raise ValueError("Unverified article publication")
        if not c.get("reviewed_by") or set(c["compounds"]) != {"HARD","MEDIUM","SOFT"} or any(not re.fullmatch(r"C[0-6]",v) for v in c["compounds"].values()):
            raise ValueError("Reviewed compound allocation required")
        cal=json.loads(_source(root,c["calendar_source"],"api.jolpi.ca"))["MRData"]["RaceTable"]["Races"]
        if len(cal)!=1 or (int(cal[0]["season"]),int(cal[0]["round"]),cal[0]["Circuit"]["circuitId"]) != (c["temporada"],c["rodada"],c["circuito_id"]):
            raise ValueError("Pirelli event identity mismatch")
        contexts.append(c)
    return seal({"schema":SCHEMA,"use":"descriptive_posterior_only","model_promotion":False,
        "f1db_source":f,"events":events,"pirelli":contexts,"fia_claims":proofs})


def validate(bundle):
    if bundle.get("schema") != SCHEMA or bundle.get("model_promotion") is not False or bundle.get("use") != "descriptive_posterior_only":
        raise ValueError("Invalid supplement scope")
    if seal(deepcopy(bundle))["conteudo_sha256"] != bundle.get("conteudo_sha256"):
        raise ValueError("Supplement integrity mismatch")
    seen=set()
    for e in bundle["events"]:
        key=(e["temporada"],e["rodada"])
        if key in seen:
            raise ValueError("Duplicate supplement event")
        seen.add(key)
        nums=set()
        for row in e["rows"]:
            if type(row["numero"]) is not int or row["numero"] < 1 or row["numero"] in nums:
                raise ValueError("Invalid supplement driver identity")
            nums.add(row["numero"])
            for field,claim in row["admitted"].items():
                if field not in FIELDS or not claim.get("reviewed_by") or urlparse(claim["source"]["url"]).hostname != "www.fia.com":
                    raise ValueError("Invalid admitted field")
                if field.startswith("q"):
                    lap(claim["value"])
                if field=="posicao" and claim["value"] is not None and (type(claim["value"]) is not int or claim["value"]<1):
                    raise ValueError("Invalid official position")
                if field=="estado" and claim["value"] not in ("DSQ","DNS","NC"):
                    raise ValueError("Invalid official status")


def project(asset,bundle):
    """Copy on write; never modifies original asset or its frozen producers."""
    validate(bundle)
    result=deepcopy(asset)
    previous=result.get("complemento_fontes")
    if previous is not None:
        if previous["sha256"] != bundle["conteudo_sha256"]:
            raise ValueError("Use the original projection for another supplement")
        return result
    admitted=[]
    for event in bundle["events"]:
        key="{}:{}".format(event["temporada"],event["rodada"])
        gp=result["gps"].get(key)
        if gp is None:
            continue
        if gp["identidade"]["circuito_id"] != event["circuito_id"] or gp.get("data_corrida") != event["data_corrida"]:
            raise ValueError("Projection event identity mismatch")
        gp["complemento_f1db"]={"release":bundle["f1db_source"]["release"],"layout_id":event["layout_id"],"claims":event["rows"]}
        for row in event["rows"]:
            for session in gp["sessoes"]:
                if session["nome"] != "Qualifying":
                    continue
                for target in session["tempos"]:
                    if target["numero"] != row["numero"]:
                        continue
                    if target.get("piloto_id") != row["piloto_id"]:
                        raise ValueError("Projection driver identity mismatch")
                    if row["admitted"]:
                        target["antes_complemento"]=deepcopy({k:target.get(k) for k in ("posicao","posicao_original","duracao","q1","q2","q3","gap")})
                        target["fontes_por_campo"]=deepcopy(row["admitted"])
                        for field,claim in row["admitted"].items():
                            target[field]=claim["value"]
                        phases=[target.get(q) for q in ("q1","q2","q3") if target.get(q) is not None]
                        if any(q in row["admitted"] for q in ("q1","q2","q3")):
                            target["duracao"]=phases[-1] if phases else None
                            if target["duracao"] != target["antes_complemento"]["duracao"]:
                                target["gap"]=None
                        if row["admitted"].get("estado",{}).get("value") in ("DSQ","DNS","NC"):
                            target.update(posicao=None,posicao_original=row["admitted"]["estado"]["value"],duracao=None,q1=None,q2=None,q3=None,gap=None)
                        admitted.append([key,row["numero"]])
    # Future contexts remain explicitly separate from observed session data.
    result["contextos_pirelli"]=deepcopy(bundle["pirelli"])
    result.setdefault("fontes",[]).extend([
        {"nome":"F1DB","url":bundle["f1db_source"]["url"],"licenca":"CC BY 4.0","release":bundle["f1db_source"]["release"]},
        {"nome":"Pirelli","url":"https://press.pirelli.com/","licenca":None,"nota":"Published facts and expectations, manually reviewed; no third-party licence extended."}])
    result["complemento_fontes"]={"sha256":bundle["conteudo_sha256"],"uso":bundle["use"],"aplicados":admitted}
    from pitwall.data.archive import conteudo_sha256, validar
    result["conteudo_sha256"]=conteudo_sha256(result["gps"])
    validar(result)
    return result


def load_projection(root, asset):
    """Apply the explicitly packaged revision after prior archive complements."""
    root = Path(root).resolve()
    path = root / ASSET
    current = path
    while current != root:
        if current.is_symlink():
            raise ValueError("Complementary sources cannot use symlinks")
        current = current.parent
    if not path.exists():
        return asset
    if not path.is_file() or path.stat().st_size > 512 * 1024:
        raise ValueError("Invalid complementary source asset size/type")
    raw = path.read_bytes()
    if sha(raw) != APPROVED_SHA256:
        raise ValueError("Unapproved complementary source asset hash")
    return project(asset, json.loads(raw.decode("utf-8")))


def write_new(path,value):
    raw=dump(value)
    path=Path(path)
    if path.is_symlink() or (path.exists() and path.read_bytes() != raw):
        raise FileExistsError("Existing divergent output preserved")
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with path.open("xb") as f:
            f.write(raw)
    return {"arquivo":str(path),"sha256":sha(raw),"bytes":len(raw)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    b=sub.add_parser("build");b.add_argument("--plan",type=Path,required=True);b.add_argument("--output",type=Path,required=True)
    p=sub.add_parser("project");p.add_argument("--asset",type=Path,required=True);p.add_argument("--bundle",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=build(args.plan) if args.command=="build" else project(read(args.asset),read(args.bundle))
    print(json.dumps(write_new(args.output,result),ensure_ascii=False))


if __name__=="__main__":
    main()
