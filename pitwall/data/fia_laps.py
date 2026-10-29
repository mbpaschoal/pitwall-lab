"""Leitura conservadora do layout FIA; relógio da primeira passagem não é duração."""

import csv
import json
from pathlib import Path
import re


def extrair_layout(texto):
    rows = []
    vistos = set()
    # O documento de Baku tem três pilotos lado a lado, cada qual com duas colunas de voltas.
    for pagina, conteudo in enumerate(texto.split("\f"), 1):
        linhas = conteudo.splitlines()
        header = next(
            (
                l
                for l in linhas
                if re.search(r"^\d+\s{5,}[A-Z][a-z]+\s+[A-Z]", l.strip())
            ),
            None,
        )
        if header is None:
            continue
        pos = [
            m.start() for m in re.finditer(r"\b\d+\s{5,}[A-Z][a-z]+\s+[A-Z]", header)
        ]
        if not pos or len(pos) > 3:
            raise ValueError("Colunas do PDF não reconhecidas")
        limites = pos + [max(len(l) for l in linhas) + 1]
        for i, inicio in enumerate(pos):
            driver = None
            for linha in linhas:
                segmento = linha[inicio : limites[i + 1]].strip()
                h = re.fullmatch(
                    r"(\d+)\s{3,}([A-Za-zÀ-ÿ]+(?:\s+[A-ZÀ-Ÿ]+)+)", segmento
                )
                if h:
                    driver = int(h[1])
                    continue
                if driver is None:
                    continue
                for m in re.finditer(
                    r"\b(\d+)\s+(P\s+)?(\d+:\d{2}(?:\.\d{3}|:\d{2}))", segmento
                ):
                    volta = int(m[1])
                    tempo = m[3]
                    chave = (driver, volta)
                    if chave in vistos:
                        raise ValueError("Volta duplicada no PDF")
                    vistos.add(chave)
                    duracao = None
                    if "." in tempo:
                        minutos, segundos = tempo.split(":")
                        duracao = int(minutos) * 60 + float(segundos)
                    rows.append(
                        {
                            "temporada": 2025,
                            "rodada": 17,
                            "circuito_id": "baku",
                            "session_key": 9900,
                            "driver_number": driver,
                            "lap_number_fia": volta,
                            "tempo_publicado": tempo,
                            "duracao_s": duracao,
                            "natureza_tempo": (
                                "duracao_publicada"
                                if duracao is not None
                                else "horario_referencia"
                            ),
                            "marcador_pit": bool(m[2]),
                            "pagina_pdf": pagina,
                        }
                    )
    if len({r["driver_number"] for r in rows}) != 20:
        raise ValueError("PDF não cobre os vinte pilotos esperados")
    for driver in {r["driver_number"] for r in rows}:
        voltas = sorted(
            r["lap_number_fia"] for r in rows if r["driver_number"] == driver
        )
        if voltas != list(range(1, max(voltas) + 1)):
            raise ValueError("Sequência de voltas do PDF incompleta")
    return sorted(rows, key=lambda r: (r["driver_number"], r["lap_number_fia"]))


if __name__ == "__main__":
    texto = Path("reports/resolucao_dados_20261028/baku2025_voltas_fia.txt").read_text()
    rows = extrair_layout(texto)
    r = next(
        r
        for r in json.loads(
            Path(
                "data/acervo_historico/resolucao-20261029/fontes/recibos.json"
            ).read_text()
        )
        if r["id"] == "fia_laps_baku2025"
    )
    destino = Path(
        "data/acervo_historico/resolucao-20261029/voltas_classificacao_fia.csv"
    )
    for row in rows:
        row.update(
            provider="fia_documento",
            fonte_url=r["url"],
            fonte_sha256=r["sha256"],
            obtido_em_utc=r["obtido_em_utc"],
        )
    with destino.open("x", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(
        "Passagens:",
        len(rows),
        "Durações:",
        sum(r["duracao_s"] is not None for r in rows),
    )
