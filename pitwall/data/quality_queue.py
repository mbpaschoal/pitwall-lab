"""Gera fila de qualidade a partir de evidências locais, sem coletar ou adjudicar dados."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


def ler_csv(path):
    with Path(path).open(newline="", encoding="utf8") as f:
        return list(csv.DictReader(f))


def planejar(lacunas, conflitos, inventario):
    fila = []

    def adicionar(
        tipo, identidade, motivo, alternativa, criterio, prioridade, fontes=None
    ):
        chave = json.dumps([tipo, identidade], sort_keys=True, ensure_ascii=False)
        fila.append(
            {
                "id": hashlib.sha256(chave.encode("utf8")).hexdigest()[:20],
                "responsavel": "dados",
                "prioridade": prioridade,
                "tipo": tipo,
                "identidade_json": json.dumps(identidade, sort_keys=True),
                "estado": "aguardando_evidencia",
                "motivo": motivo,
                "fonte_alternativa": alternativa,
                "fontes_evidencia_json": json.dumps(fontes or [], ensure_ascii=False),
                "criterio_encerramento": criterio,
                "evidencia_resolucao": "",
                "sha256_resolucao": "",
                "restricao": "preservar fontes, canônico, v1 e emissões; sem retry automático de 404",
            }
        )

    for x in lacunas:
        tipo = x["tipo"]
        adicionar(
            tipo,
            {k: x[k] for k in ["temporada", "rodada", "circuito_id"]},
            x["motivo"],
            "timing oficial documentado ou fotografia independente com identidade literal",
            "Recibo, hash e chaves verificados; nova saída comprova cobertura/qualidade, ou encerrar como lacuna explicada com as tentativas documentadas.",
            "alta" if tipo == "laps_sessoes" else "media",
            fontes=json.loads(x.get("fontes_json") or "[]"),
        )
    for x in conflitos:
        adicionar(
            "conflito_classificacao",
            {
                k: x[k]
                for k in ["temporada", "rodada", "circuito_id", "piloto_id", "campo"]
            },
            "canônico={} / archive={}".format(x["valor_canonico"], x["valor_archive"]),
            "documento oficial da sessão e proveniência do archive",
            "Adjudicação explícita com documento e hash, sem escolher por métrica; gerar artefato separado e preservar valores brutos.",
            "alta",
            fontes=[x.get("fonte_canonica"), x.get("fonte_archive")],
        )
    for gp in inventario["cobertura_por_gp"]:
        for piloto in gp["pilotos_resultado_sem_classificacao"]:
            adicionar(
                "classificacao_canonica_ausente",
                {
                    "temporada": gp["temporada"],
                    "rodada": gp["rodada"],
                    "piloto_id": piloto,
                },
                "Resultado presente e classificação canônica ausente; não cria elegibilidade prospectiva.",
                "classificação oficial com identidade e proveniência verificáveis",
                "Registrar presença/ausência documental em complemento separado; não modificar população nem entradas congeladas.",
                "alta",
            )
    adicionar(
        "proveniencia_archive",
        {"camada": "archive"},
        "Publicador/URLs conflitantes e UTC original desconhecido.",
        "recibo original ou página documental da distribuição exata",
        "Comprovar origem/licença por documentação; UTC original permanece desconhecido sem recibo contemporâneo. Lacuna explicada é encerramento válido.",
        "alta",
    )
    if len({x["id"] for x in fila}) != len(fila):
        raise ValueError("pendência duplicada: conferir identidade e evidências")
    return sorted(
        fila, key=lambda x: (x["prioridade"] != "alta", x["tipo"], x["identidade_json"])
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lacunas", required=True, type=Path)
    p.add_argument("--conflitos", required=True, type=Path)
    p.add_argument("--inventario", required=True, type=Path)
    p.add_argument("--destino", required=True, type=Path)
    a = p.parse_args()
    recibo = a.destino.with_suffix(".fontes.json")
    if a.destino.exists() or recibo.exists():
        raise FileExistsError("Fila ou recibo já existente; escolha um destino novo")
    fila = planejar(
        ler_csv(a.lacunas), ler_csv(a.conflitos), json.loads(a.inventario.read_text())
    )
    with a.destino.open("x", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=list(fila[0]))
        w.writeheader()
        w.writerows(fila)
    with recibo.open("x", encoding="utf8") as f:
        json.dump(
            {
                "fontes": [
                    {
                        "path": str(p.resolve()),
                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    }
                    for p in [a.lacunas, a.conflitos, a.inventario]
                ],
                "fila_sha256": hashlib.sha256(a.destino.read_bytes()).hexdigest(),
                "implementacao_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
            },
            f,
            indent=2,
        )
    print("{} pendências; nenhuma fonte foi modificada.".format(len(fila)))


if __name__ == "__main__":
    main()
