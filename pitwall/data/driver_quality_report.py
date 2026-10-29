"""Close the data gate explicitly, distinguishing recovered values from limits."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


def consolidate(acquisition_path, initial_report_path, destination):
    acquisition_path, initial_report_path, destination = map(
        Path, (acquisition_path, initial_report_path, destination)
    )
    if destination.exists():
        raise FileExistsError("Use a new destination; preserve prior evidence")
    weather_path = acquisition_path / "clima_validado_v1/clima_corridas.json"
    source_path = acquisition_path / "fontes_validadas_v2/fontes_auditadas.json"
    tyres_path = acquisition_path / "pneus_validados_v2/pneus_adjudicados.json"
    circuit_path = acquisition_path / "circuitos_validados_v1/circuitos_corridas.json"
    weather, sources, tyres, circuits = [json.loads(p.read_text()) for p in (weather_path, source_path, tyres_path, circuit_path)]
    protected = json.loads((initial_report_path / "protegidos_antes.json").read_text())
    changed = [name for name, digest in protected.items()
               if not Path(name).is_file() or hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest]
    if changed:
        raise ValueError("Protected scientific/source files changed: " + str(changed))
    identities = lambda records: {(int(x["temporada"]), int(x["rodada"]), int(x["session_key"])) for x in records}
    expected = identities(json.loads((acquisition_path / "plano_corridas.json").read_text()))
    if any(identities(records) != expected for records in (weather["corridas"], sources["atmosfera_modelada"], circuits["corridas"])):
        raise ValueError("Race/source/circuit coverage differs from audited main races")
    if any(not field["elegivel"] for race in weather["corridas"] for field in race["campos"].values()):
        raise ValueError("Insufficient sensor coverage for driver-condition comparisons")
    if any(x["largou"] not in (True, False) for x in sources["largadas"]):
        raise ValueError("Unknown race-start denominator")
    decisions = tyres["adjudicacoes"]
    if len(decisions) != 50 or any(x["status"] not in {
            "limites_recuperados_fonte_alternativa", "nao_largou_limites_nao_aplicaveis",
            "zero_voltas_completadas_limites_nao_aplicaveis"} for x in decisions):
        raise ValueError("Unadjudicated native tyre-bound issue")
    evidence = {
        "janela_efetiva_corrida": weather_path, "clima_durante_corrida": weather_path,
        "nuvens_codigo_meteorologico": source_path, "estrategias_pneus": tyres_path,
        "stints": tyres_path, "sentido_circuito": circuit_path,
        "separacao_corrida_sprint": weather_path, "denominadores_largadas": source_path,
        "configuracao_historica_circuitos": circuit_path,
    }
    with (initial_report_path / "pendencias_iniciais.csv").open(newline="") as stream:
        ledger = list(csv.DictReader(stream))
    for row in ledger:
        row.update(estado="encerrada_com_evidencia", evidencia=str(evidence[row["tipo"]]),
                   bloqueia_pilotos=False, escopo="condicoes_e_resultados_de_corridas")
    for item in sources["compostos"]:
        unavailable = item["status_adjudicacao"] == "indisponivel_nas_duas_fontes_consultadas"
        ledger.append({"id": "composto-{}-{}-{}".format(item["session_key"], item["driver_number"], item["stint_number"]),
            "tipo": "composto_pneu", "identidade_json": json.dumps({k: item[k] for k in ("temporada", "rodada", "session_key", "driver_number", "stint_number")}),
            "prioridade": "media", "estado": "lacuna_explicada_limite_fonte" if unavailable else item["status_adjudicacao"],
            "criterio_encerramento": "Composto documentado ou ausencia explicada; valores desconhecidos continuam nulos e nao podem sustentar cruzamentos de pneus.",
            "evidencia": str(source_path), "bloqueia_pilotos": False,
            "escopo": "compostos_por_stint_fora_dos_indicadores_de_vitorias_por_clima_circuito"})
    for code, kind, path in (("lap-counter-11234", "numeracao_voltas", source_path),
                              ("compound-disagreement-9693-30-5", "divergencia_composto_entre_fontes", tyres_path)):
        ledger.append({"id": code, "tipo": kind, "identidade_json": "{}", "prioridade": "alta",
            "estado": "encerrada_por_selecao_integral_da_fonte_alternativa", "criterio_encerramento":
            "Preservar nativo; nao misturar numeracoes/compostos conflitantes; selecionar voltas observadas da fonte alternativa com identidade verificada.",
            "evidencia": str(path), "bloqueia_pilotos": False, "escopo": "dados_complementares_descritivos"})
    counts = Counter(x["status_adjudicacao"] for x in sources["compostos"])
    result = {"schema": "pitwall-driver-data-quality-v1", "gate_pilotos": True,
        "pendencias_obrigatorias_sem_tratamento": 0, "completude_fisica_de_todos_os_campos": False,
        "compostos_indisponiveis_declarados": counts["indisponivel_nas_duas_fontes_consultadas"],
        "corridas": len(expected), "chuva_registrada": sum(x["condicao_chuva"] == "com_chuva_registrada" for x in weather["corridas"]),
        "resultados": len(sources["largadas"]), "largadas": sum(x["largou"] for x in sources["largadas"]),
        "dns": sum(not x["largou"] for x in sources["largadas"]), "compostos": dict(counts),
        "limites_pneus": dict(Counter(x["status"] for x in decisions)), "mapas_fia": len(circuits["corridas"]),
        "originais_protegidos_verificados": len(protected), "arquivos_protegidos_alterados": changed,
        "ledger_registros": len(ledger), "proibicoes": ["Inferir pneus ausentes", "Tratar linhas FastF1Generated como observadas",
            "Misturar Sprint e Race", "Usar chuva da agenda/fim de semana como chuva durante a prova", "Alterar entradas/probabilidades congeladas do v1"],
        "fontes_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (weather_path, source_path, tyres_path, circuit_path)}}
    destination.mkdir(parents=True)
    with (destination / "pendencias.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ledger[0])); writer.writeheader(); writer.writerows(ledger)
    (destination / "gate_dados.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("acquisition", "initial-report", "destination"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    value = consolidate(args.acquisition, args.initial_report, args.destination)
    print(json.dumps({k: value[k] for k in ("gate_pilotos", "corridas", "largadas", "compostos_indisponiveis_declarados", "ledger_registros")}))
