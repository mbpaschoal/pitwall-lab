"""Diagnósticos offline de previsões v2 preservadas; não ajusta modelos."""

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path


def _media(valores):
    return (
        sum(valores) / len(valores)
        if valores and all(x is not None for x in valores)
        else None
    )


def _log_loss(linha):
    p = linha["probabilidade"] if linha["podio"] else 1 - linha["probabilidade"]
    return -math.log(p) if p > 0 else None


def _quantil(valores, q):
    pos = (len(valores) - 1) * q
    i = int(pos)
    return valores[i] + (valores[min(i + 1, len(valores) - 1)] - valores[i]) * (pos - i)


def intervalo_blocos(por_temporada):
    """2.000 réplicas, blocos móveis de dois GPs, sem cruzar temporadas."""
    if not por_temporada or any(len(v) < 2 for v in por_temporada.values()):
        return None
    rng = random.Random(42)
    medias = []
    for _ in range(2000):
        amostra = []
        for temporada in sorted(por_temporada):
            valores = por_temporada[temporada]
            bloco = []
            while len(bloco) < len(valores):
                inicio = rng.randrange(len(valores) - 1)
                bloco.extend(valores[inicio : inicio + 2])
            amostra.extend(bloco[: len(valores)])
        medias.append(_media(amostra))
    medias.sort()
    return [_quantil(medias, 0.025), _quantil(medias, 0.975)]


def gerar_diagnosticos(previsoes):
    grupos = defaultdict(list)
    identidades = set()
    for original in previsoes:
        x = dict(original)
        for c in ("fold", "temporada", "rodada"):
            x[c] = int(x[c])
        if x["temporada"] not in range(2022, 2026) or x["fold"] != x["temporada"]:
            raise ValueError("diagnóstico exige folds retrospectivos 2022–2025")
        x["alvo_conhecido"] = str(x["alvo_conhecido"]) in ("1", "True")
        x["probabilidade"] = float(x["probabilidade"])
        if not math.isfinite(x["probabilidade"]) or not 0 <= x["probabilidade"] <= 1:
            raise ValueError(
                "probabilidade deve estar entre zero e um; diagnóstico não aplica clipping"
            )
        x["podio"] = int(x["podio"]) if x["alvo_conhecido"] else None
        if x["alvo_conhecido"] and x["podio"] not in (0, 1):
            raise ValueError("alvo conhecido deve ser binário")
        key = (x["metodo"], x["temporada"], x["rodada"], x["piloto_id"])
        if key in identidades:
            raise ValueError("previsão duplicada")
        identidades.add(key)
        grupos[x["metodo"]].append(x)
    metricas, calibracao, rankings, resumos = [], [], [], []
    indices = {}
    for metodo, linhas in sorted(grupos.items()):
        gps = defaultdict(list)
        indices[metodo] = {
            (x["temporada"], x["rodada"], x["piloto_id"]): (
                x["podio"],
                x["alvo_conhecido"],
            )
            for x in linhas
        }
        bins = [
            {
                "faixa": i,
                "inicio": i / 10,
                "fim": (i + 1) / 10,
                "n": 0,
                "probabilidade_media": None,
                "frequencia_podio": None,
            }
            for i in range(10)
        ]
        for x in linhas:
            gps[(x["temporada"], x["rodada"])].append(x)
        conhecidas = [x for x in linhas if x["alvo_conhecido"]]
        for i, faixa in enumerate(bins):
            b = [x for x in conhecidas if min(9, int(x["probabilidade"] * 10)) == i]
            faixa.update(
                n=len(b),
                probabilidade_media=_media([x["probabilidade"] for x in b]),
                frequencia_podio=_media([x["podio"] for x in b]),
            )
        calibracao.append({"metodo": metodo, "faixas": bins})
        distribuicao = {str(i): 0 for i in range(4)}
        for (ano, rodada), gp in sorted(gps.items()):
            conhecidos = [x for x in gp if x["alvo_conhecido"]]
            if conhecidos:
                metricas.append(
                    {
                        "metodo": metodo,
                        "fold": ano,
                        "temporada": ano,
                        "rodada": rodada,
                        "n": len(conhecidos),
                        "brier": _media(
                            [(x["probabilidade"] - x["podio"]) ** 2 for x in conhecidos]
                        ),
                        "log_loss": _media([_log_loss(x) for x in conhecidos]),
                    }
                )
            avaliavel = (
                len(conhecidos) == len(gp) and sum(x["podio"] for x in conhecidos) == 3
            )
            acertos = None
            if avaliavel:
                top = sorted(gp, key=lambda x: (-x["probabilidade"], x["piloto_id"]))[
                    :3
                ]
                acertos = sum(x["podio"] for x in top)
                distribuicao[str(acertos)] += 1
            rankings.append(
                {
                    "metodo": metodo,
                    "temporada": ano,
                    "rodada": rodada,
                    "avaliavel": avaliavel,
                    "acertos_top3": acertos,
                    "podio_completo": acertos == 3 if avaliavel else None,
                }
            )
        mg = [m for m in metricas if m["metodo"] == metodo]
        resumos.append(
            {
                "metodo": metodo,
                "n_pilotos_conhecidos": len(conhecidas),
                "n_gps": len(mg),
                "brier_por_piloto": _media(
                    [(x["probabilidade"] - x["podio"]) ** 2 for x in conhecidas]
                ),
                "log_loss_por_piloto": _media([_log_loss(x) for x in conhecidas]),
                "brier_medio_gp": _media([x["brier"] for x in mg]),
                "log_loss_medio_gp": _media([x["log_loss"] for x in mg]),
                "distribuicao_acertos_top3": distribuicao,
                "n_gps_ranking": sum(distribuicao.values()),
                "podios_completos": distribuicao["3"],
            }
        )
    ranking_classificacao = []
    if grupos:
        gps = defaultdict(list)
        for x in grupos[sorted(grupos)[0]]:
            gps[(x["temporada"], x["rodada"])].append(x)
        for (ano, rodada), gp in sorted(gps.items()):
            posicoes = [
                (
                    float(x["posicao_classificacao"])
                    if x.get("posicao_classificacao") not in (None, "")
                    else None
                )
                for x in gp
            ]
            avaliavel = (
                all(x["alvo_conhecido"] for x in gp)
                and sum(x["podio"] for x in gp) == 3
                and all(p is not None and math.isfinite(p) and p > 0 for p in posicoes)
                and len(set(posicoes)) == len(posicoes)
            )
            top = (
                sorted(
                    zip(posicoes, gp), key=lambda par: (par[0], par[1]["piloto_id"])
                )[:3]
                if avaliavel
                else []
            )
            acertos = sum(x["podio"] for _, x in top) if avaliavel else None
            ranking_classificacao.append(
                {
                    "temporada": ano,
                    "rodada": rodada,
                    "avaliavel": avaliavel,
                    "acertos_top3": acertos,
                    "podio_completo": acertos == 3 if avaliavel else None,
                }
            )
    comparacoes = []
    candidato = "q_a3_completo"
    for comparador in ("q_flexivel", "v1_replicado_temporal"):
        registro = {
            "candidato": candidato,
            "comparador": comparador,
            "conclusao": "cobertura_insuficiente",
        }
        if (
            candidato not in indices
            or comparador not in indices
            or indices[candidato] != indices[comparador]
        ):
            registro["motivo"] = (
                "coortes/estados dos alvos diferentes ou método ausente; não selecionar interseção favorável"
            )
            comparacoes.append(registro)
            continue
        c = {
            (m["temporada"], m["rodada"]): m
            for m in metricas
            if m["metodo"] == candidato
        }
        b = {
            (m["temporada"], m["rodada"]): m
            for m in metricas
            if m["metodo"] == comparador
        }
        temporadas = defaultdict(list)
        deltas = []
        for key in sorted(c):
            delta = {
                "temporada": key[0],
                "rodada": key[1],
                "fold": key[0],
                "brier": c[key]["brier"] - b[key]["brier"],
                "log_loss": (
                    (c[key]["log_loss"] - b[key]["log_loss"])
                    if c[key]["log_loss"] is not None and b[key]["log_loss"] is not None
                    else None
                ),
            }
            temporadas[key[0]].append(delta["brier"])
            deltas.append(delta)
        ic = intervalo_blocos(temporadas)
        delta = _media([d["brier"] for d in deltas])
        ll = _media([d["log_loss"] for d in deltas])
        maioria = sum(_media(v) < 0 for v in temporadas.values()) > len(temporadas) / 2
        folds_completos = set(temporadas) == {2022, 2023, 2024, 2025}
        contiguos = all(
            b[1] == a[1] + 1
            for ano in temporadas
            for a, b in zip(
                sorted(k for k in c if k[0] == ano),
                sorted(k for k in c if k[0] == ano)[1:],
            )
        )
        if ic is not None and ll is not None and folds_completos and contiguos:
            registro["conclusao"] = (
                "melhora_sustentada"
                if delta <= -0.002 and ll <= 0 and maioria and ic[1] < 0
                else "sem_ganho" if delta >= 0 else "inconclusivo"
            )
        registro.update(
            n_gps=len(deltas),
            deltas_por_gp=deltas,
            delta_brier=delta,
            delta_log_loss=ll,
            ic95_brier=ic if contiguos else None,
            maioria_folds_melhora=maioria,
            folds_completos=folds_completos,
            gps_contiguos=contiguos,
        )
        comparacoes.append(registro)
    return {
        "schema": "diagnosticos-v2-v1",
        "bootstrap": {"replicas": 2000, "bloco_gps": 2, "seed": 42},
        "metricas_por_gp": metricas,
        "resumos": resumos,
        "calibracao": calibracao,
        "ranking_por_gp": rankings,
        "ranking_classificacao": ranking_classificacao,
        "comparacoes": comparacoes,
        "recomendacao_estatistica_a3": (
            "melhora_sustentada"
            if all(x["conclusao"] == "melhora_sustentada" for x in comparacoes)
            else "nao_demonstrada"
        ),
        "promocao_automatica": False,
        "log_loss_nao_finito": "null quando a probabilidade do alvo é zero; sem clipping",
        "b1": "cobertura_insuficiente",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--previsoes", required=True, type=Path)
    p.add_argument("--destino", required=True, type=Path)
    p.add_argument(
        "--entradas",
        type=Path,
        help="CSV canônico opcional para o ranking de classificação por chaves literais",
    )
    args = p.parse_args()
    fonte = args.previsoes.resolve()
    raw = fonte.read_bytes()
    with fonte.open(newline="", encoding="utf8") as f:
        linhas = list(csv.DictReader(f))
    if args.entradas:
        with args.entradas.open(newline="", encoding="utf8") as f:
            entradas = list(csv.DictReader(f))

        def chave(x):
            return (str(x["temporada"]), str(x["rodada"]), x["piloto_id"])

        por_chave = {chave(x): x for x in entradas}
        if len(por_chave) != len(entradas):
            raise ValueError("entradas canônicas duplicadas")
        for x in linhas:
            if chave(x) not in por_chave:
                raise ValueError("previsão sem chave nas entradas canônicas")
            x["posicao_classificacao"] = por_chave[chave(x)]["posicao_classificacao"]
    resultado = gerar_diagnosticos(linhas)
    resultado["fonte"] = {"path": str(fonte), "sha256": hashlib.sha256(raw).hexdigest()}
    resultado["implementacao_sha256"] = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()
    if args.entradas:
        resultado["entradas_ranking"] = {
            "path": str(args.entradas.resolve()),
            "sha256": hashlib.sha256(args.entradas.read_bytes()).hexdigest(),
        }
    with args.destino.open("x", encoding="utf8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


if __name__ == "__main__":
    main()
