"""Histórico descritivo da mesma pista, estritamente anterior ao GP selecionado."""

from collections import defaultdict


def construir_historico(evento, corridas):
    pista = evento["circuito_id"]
    data = evento["data_corrida"]
    anteriores = [
        x for x in corridas if x["circuito_id"] == pista and x["data_corrida"] < data
    ]
    anteriores.sort(
        key=lambda x: (x["data_corrida"], x["temporada"], x["rodada"]), reverse=True
    )
    anteriores = anteriores[:5]
    vistos = set()
    pilotos = defaultdict(list)
    for prova in anteriores:
        identidade = (prova["temporada"], prova["rodada"])
        if identidade in vistos:
            raise ValueError("Edição histórica duplicada")
        vistos.add(identidade)
        ids = set()
        for r in prova["resultados"]:
            if r["piloto_id"] in ids:
                raise ValueError("Piloto duplicado na edição histórica")
            ids.add(r["piloto_id"])
            pilotos[r["piloto_id"]].append(
                dict(
                    r,
                    temporada=prova["temporada"],
                    rodada=prova["rodada"],
                    data=prova["data_corrida"],
                )
            )
    resumo = []
    for pid, rows in pilotos.items():
        posicoes = [r["posicao"] for r in rows if r.get("posicao") is not None]
        pontos = [r["pontos"] for r in rows if r.get("pontos") is not None]
        resumo.append(
            {
                "piloto_id": pid,
                "piloto": rows[0]["piloto"],
                "participacoes": len(rows),
                "vitorias": sum(p == 1 for p in posicoes),
                "podios": sum(p <= 3 for p in posicoes),
                "melhor_posicao": min(posicoes) if posicoes else None,
                "posicao_media": sum(posicoes) / len(posicoes) if posicoes else None,
                "pontos_observados": sum(pontos) if pontos else None,
                "n_posicoes_conhecidas": len(posicoes),
                "n_pontos_conhecidos": len(pontos),
                "resultados": rows,
            }
        )
    resumo.sort(
        key=lambda r: (
            -r["vitorias"],
            -r["podios"],
            r["posicao_media"] or 999,
            r["piloto_id"],
        )
    )
    return {
        "circuito_id": pista,
        "corte_data_exclusivo": data,
        "edicoes": anteriores,
        "pilotos": resumo,
        "escopo": "Até cinco edições anteriores disponíveis na mesma pista; fontes locais, com proveniência por edição. Não inclui a prova selecionada, Sprint ou outras pistas do mesmo país.",
    }


def para_corrida_planejada(asset, temporada, rodada, circuito_id, data_corrida):
    """Histórico de GP ainda sem acervo próprio, usando apenas provas anteriores preservadas."""
    banco = {}
    for gp in asset.get("gps", {}).values():
        if gp["identidade"]["circuito_id"] != circuito_id:
            continue
        provas = list((gp.get("historico_circuito") or {}).get("edicoes", []))
        if (gp.get("historico") or {}).get("resultados"):
            provas.append(
                dict(
                    gp["identidade"],
                    data_corrida=gp["data_corrida"],
                    corrida=gp["corrida"],
                    resultados=gp["historico"]["resultados"],
                )
            )
        for p in provas:
            key = (p["temporada"], p["rodada"])

            def valores(prova):
                return sorted(
                    (r["piloto_id"], r.get("posicao"), r.get("pontos"), r.get("status"))
                    for r in prova["resultados"]
                )

            if key in banco and valores(banco[key]) != valores(p):
                raise ValueError("Resultados conflitantes no histórico da pista")
            banco[key] = p
    identidade = {"temporada": temporada, "rodada": rodada, "circuito_id": circuito_id}
    return {
        "identidade": identidade,
        "data_corrida": data_corrida,
        "historico": {"resultados": []},
        "historico_circuito": construir_historico(
            dict(identidade, data_corrida=data_corrida), list(banco.values())
        ),
    }
