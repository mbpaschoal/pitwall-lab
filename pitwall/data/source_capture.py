"""Captura serial, limitada e retomável de documentos públicos para adjudicação."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def capturar(plano, destino):
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    recibo = destino / "recibos.json"
    registros = json.loads(recibo.read_text()) if recibo.exists() else []
    for x in registros:
        if (
            hashlib.sha256((destino / x["arquivo"]).read_bytes()).hexdigest()
            != x["sha256"]
        ):
            raise ValueError("Cache divergente")
    if len(plano) > 50:
        raise ValueError("Teto de 50 documentos")
    urls = {x["url"] for x in registros}
    for item in plano:
        url = item["url"]
        host = urlsplit(url).hostname
        if urlsplit(url).scheme != "https" or host not in {
            "www.formula1.com",
            "www.fia.com",
            "api.openf1.org",
            "api.open-meteo.com",
            "archive-api.open-meteo.com",
            "www.kaggle.com",
        }:
            raise ValueError("Origem não admitida")
        if url in urls:
            continue
        if registros:
            time.sleep(8)
        nome = item["id"] + ".bin"
        if Path(nome).name != nome or (destino / nome).exists():
            raise ValueError("Destino inválido/existente")
        try:
            with urlopen(
                Request(
                    url,
                    headers={
                        "User-Agent": "PitwallLab/quality-audit (educational; serial; cached)"
                    },
                ),
                timeout=35,
            ) as r:
                raw = r.read(16 * 1024 * 1024 + 1)
                status = r.status
                final = r.url
                headers = dict(r.headers)
        except HTTPError as e:
            raw = e.read()
            status = e.code
            final = e.url
            headers = dict(e.headers)
        except (URLError, TimeoutError, OSError) as e:
            raw = str(e).encode()
            status = None
            final = url
            headers = {}
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError("Documento excede 16 MiB")
        (destino / nome).write_bytes(raw)
        registros.append(
            dict(
                item,
                arquivo=nome,
                status=status,
                url_final=final,
                headers=headers,
                obtido_em_utc=datetime.now(timezone.utc).isoformat(),
                sha256=hashlib.sha256(raw).hexdigest(),
                bytes=len(raw),
            )
        )
        recibo.write_text(json.dumps(registros, ensure_ascii=False, indent=2) + "\n")
        print(item["id"], status, len(raw), flush=True)
        if status == 429:
            raise RuntimeError("429: parar e respeitar Retry-After registrado")
        urls.add(url)
    return registros


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plano", required=True, type=Path)
    p.add_argument("--destino", required=True, type=Path)
    a = p.parse_args()
    capturar(json.loads(a.plano.read_text()), a.destino)
