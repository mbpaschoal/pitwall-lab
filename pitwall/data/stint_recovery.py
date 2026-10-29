"""Tentativa limitada em fonte alternativa, sem credenciais ou alteração de fontes anteriores."""

import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import requests
import fastf1


def main():
    ROOT = Path("data/acervo_historico/resolucao-20261029/fastf1")
    ROOT.mkdir(parents=True, exist_ok=True)
    if (ROOT / "tentativas.json").exists():
        raise FileExistsError(
            "Tentativa preservada; escolha novo destino antes de repetir"
        )
    (ROOT / "cache").mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(ROOT / "cache"))
    original = requests.Session.send
    recibos = []
    falhas = 0

    def enviar(self, request, **kwargs):
        nonlocal falhas
        if len(recibos) >= 24:
            raise RuntimeError("Teto de 24 consultas da tentativa")
        if falhas >= 3:
            raise RuntimeError("Falhas permanentes: não consultar novos canais")
        kwargs["timeout"] = 20
        response = original(self, request, **kwargs)
        raw = response.content
        nome = "http_{:03d}.bin".format(len(recibos) + 1)
        (ROOT / nome).write_bytes(raw)
        recibos.append(
            {
                "url": request.url,
                "status": response.status_code,
                "arquivo": nome,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "obtido_em_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        (ROOT / "recibos_http.json").write_text(json.dumps(recibos, indent=2) + "\n")
        if response.status_code in (401, 403, 404, 429):
            falhas += 1
        if response.status_code == 429:
            raise RuntimeError("Limite do provedor: não repetir")
        return response

    requests.Session.send = enviar
    resultados = []
    for year, round_, sessao in [(2024, 7, "FP1"), (2025, 11, "FP2")]:
        try:
            s = fastf1.get_session(year, round_, sessao)
            s.load(laps=True, telemetry=False, weather=False, messages=False)
            laps = s.laps
            subset = laps[
                [
                    "DriverNumber",
                    "LapNumber",
                    "Stint",
                    "Compound",
                    "TyreLife",
                    "FastF1Generated",
                    "IsAccurate",
                ]
            ]
            nome = "{}-{}-{}.csv".format(year, round_, sessao)
            subset.to_csv(ROOT / nome, index=False)
            resultados.append(
                {
                    "temporada": year,
                    "rodada": round_,
                    "sessao": sessao,
                    "estado": "voltas_observadas_recuperadas",
                    "linhas": len(subset),
                    "arquivo": nome,
                    "limite": "Min/max observados por stint são outra medida; não sobrescrever lap_start/lap_end publicados.",
                }
            )
        except Exception as e:
            resultados.append(
                {
                    "temporada": year,
                    "rodada": round_,
                    "sessao": sessao,
                    "estado": "fonte_alternativa_indisponivel",
                    "erro": type(e).__name__ + ": " + str(e),
                }
            )
        if falhas >= 3:
            break
    (ROOT / "tentativas.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(resultados, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
