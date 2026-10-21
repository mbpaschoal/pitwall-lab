"""Wrapper offline do aceite existente para o ensaio posterior ao commit."""
from __future__ import annotations

import json
import runpy
import shutil
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLOSURE = Path(__file__).resolve().parent
HELPER = ROOT / "reports/operacao_2026/validacao_integrada_20261021T002336Z/aceite-base-existente.py"


def blocked(*_args, **_kwargs):
    raise AssertionError("REDE_DNS_BLOQUEADOS_NO_ENSAIO_POS_COMMIT")


def main() -> None:
    emission_id = sys.argv[1]
    previous = "ensaio-r2-corrigido-20261020"
    socket.socket = blocked
    socket.create_connection = blocked
    socket.getaddrinfo = blocked
    socket.gethostbyname = blocked
    socket.gethostbyname_ex = blocked
    socket.gethostbyaddr = blocked
    socket.getnameinfo = blocked
    sys.argv = [str(HELPER), emission_id, previous]
    runpy.run_path(str(HELPER), run_name="__main__")
    scratch = Path.home() / ".hermes/cache/scratch" / f"pitwall-stage8-acceptance-{emission_id}.json"
    report = json.loads(scratch.read_text())
    report["wrapper"] = {
        "socket_dns_bloqueados": True,
        "helper": str(HELPER.relative_to(ROOT)),
        "anterior": previous,
    }
    (CLOSURE / "resultado_ensaio_pos_commit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    shutil.copyfile(scratch, CLOSURE / "ensaio_pos_commit.log")


if __name__ == "__main__":
    main()
