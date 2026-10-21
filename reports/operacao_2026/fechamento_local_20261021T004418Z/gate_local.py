"""Gate local determinístico do fechamento da etapa 8; não altera código nem índice."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLOSURE = Path(__file__).resolve().parent
PAYLOAD = CLOSURE / "payload_local.json"
BASE = "b067ad55dd97d964b132129838773cf6108773e3"
HASHES = ROOT / "reports/operacao_2026/revisao_r4_20261021T003337Z/hashes_pre_revisao.json"
PARECER = ROOT / "reports/operacao_2026/revisao_r4_20261021T003337Z/parecer.json"
STATIC = {
    "reports/operacao_2026/fechamento_local_20261021T004418Z/gate_local.py",
    "reports/operacao_2026/fechamento_local_20261021T004418Z/payload_local.json",
    "reports/operacao_2026/fechamento_local_20261021T004418Z/LIMITES_E_EXCLUSOES.md",
    "reports/operacao_2026/fechamento_local_20261021T004418Z/ensaio_pos_commit.py",
    "reports/operacao_2026/fechamento_local_20261021T004418Z/inventario_implementacao.json",
}
EXCEPTIONS = {"docs/estado_hermes.md", "reports/operacao_2026/revisao_independente.json"}


def run(*args: str) -> str:
    return subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=True).stdout


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    failures: list[str] = []
    details: dict[str, object] = {}
    payload = json.loads(PAYLOAD.read_text())
    allow = set(payload["implementation_allowlist"])
    expected = allow | STATIC
    try:
        details["head"] = run("git", "rev-parse", "HEAD").strip()
        details["branch"] = run("git", "branch", "--show-current").strip()
        if details["head"] != BASE:
            failures.append("HEAD divergente do commit-base")
        if details["branch"] != "main":
            failures.append("branch divergente de main")
        if run("git", "diff", "--cached", "--name-only").strip():
            failures.append("índice não estava vazio antes do stage")
        hooks = [p.name for p in (ROOT / ".git/hooks").iterdir() if p.is_file() and not p.name.endswith(".sample")]
        details["hooks_ativos"] = hooks
        if hooks:
            failures.append("hook local ativo inesperado")
    except Exception as exc:
        failures.append(f"falha Git: {exc}")
    parecer = json.loads(PARECER.read_text())
    details["r4"] = {k: parecer.get(k) for k in ("parecer", "escopo", "achados")}
    uso = parecer.get("uso_efetivo", {})
    details["uso_efetivo"] = {k: uso.get(k) for k in ("model", "billing_provider", "billing_mode", "task")}
    if (parecer.get("parecer"), parecer.get("achados")) != ("aprovado", []):
        failures.append("parecer R4 não aprovado sem achados")
    if (uso.get("model"), uso.get("billing_provider"), uso.get("billing_mode"), uso.get("task")) != ("gpt-6-astra", "openai-codex", "subscription_included", ""):
        failures.append("metadados duráveis da revisão R4 divergentes")
    recorded = json.loads(HASHES.read_text())["sha256"]
    mismatches = []
    for rel, digest in recorded.items():
        if rel in EXCEPTIONS:
            continue
        path = ROOT / rel
        if not path.is_file() or sha(path) != digest:
            mismatches.append(rel)
    details["hashes_r4_conferidos"] = len(recorded) - len(EXCEPTIONS)
    details["hashes_r4_divergentes"] = mismatches
    if mismatches:
        failures.append("hashes R4 divergentes fora das exceções autorizadas")
    init = ROOT / "operacao2026/__init__.py"
    try:
        module = ast.parse(init.read_text())
        if len(module.body) != 1 or not isinstance(module.body[0], ast.Expr) or not isinstance(module.body[0].value, ast.Constant) or not isinstance(module.body[0].value.value, str):
            failures.append("operacao2026/__init__.py não é somente docstring")
    except Exception as exc:
        failures.append(f"não foi possível validar __init__.py: {exc}")
    dashboard = ROOT / "docs/dashboard_artefatos_preservados.json"
    try:
        if sha(dashboard) != hashlib.sha256(subprocess.run(["git", "show", f"{BASE}:docs/dashboard_artefatos_preservados.json"], cwd=ROOT, check=True, capture_output=True).stdout).hexdigest():
            failures.append("âncora dashboard diverge do commit-base")
        data = json.loads(dashboard.read_text())
        registros_dashboard = []
        erros_dashboard = []
        hashes68 = data.get("sha256_artefatos_preservados") if isinstance(data, dict) else None
        details["dashboard_hashes_declarados"] = len(hashes68) if isinstance(hashes68, dict) else 0
        if not isinstance(data, dict):
            erros_dashboard.append("manifesto não é objeto JSON")
        if not isinstance(hashes68, dict):
            erros_dashboard.append("sha256_artefatos_preservados não é dicionário")
        elif len(hashes68) != 68:
            erros_dashboard.append(f"sha256_artefatos_preservados tem {len(hashes68)} entradas, esperado 68")
        if isinstance(hashes68, dict):
            for rel, esperado in hashes68.items():
                registro = {"path": rel, "hash_esperado": esperado, "hash_observado": None, "status": "FALHOU"}
                seguro = isinstance(rel, str) and bool(rel) and "\\" not in rel and not Path(rel).is_absolute() and all(parte not in {"", ".", ".."} for parte in rel.split("/")) and rel == Path(rel).as_posix()
                if not seguro:
                    registro["erro"] = "path literal não é relativo seguro dentro do projeto"
                elif not isinstance(esperado, str) or len(esperado) != 64 or any(caractere not in "0123456789abcdef" for caractere in esperado):
                    registro["erro"] = "hash de referência não é SHA-256 hexadecimal literal de 64 caracteres"
                else:
                    path = ROOT / rel
                    try:
                        path.resolve().relative_to(ROOT.resolve())
                    except ValueError:
                        registro["erro"] = "path resolve fora do projeto"
                    else:
                        if path.is_symlink() or not path.is_file():
                            registro["erro"] = "arquivo ausente, não regular ou symlink"
                        else:
                            observado = sha(path)
                            registro["hash_observado"] = observado
                            if observado == esperado:
                                registro["status"] = "OK"
                            else:
                                registro["erro"] = "SHA-256 observado diverge da referência literal"
                if registro["status"] != "OK":
                    erros_dashboard.append(f"{rel!r}: {registro.get('erro', 'falha não especificada')}")
                registros_dashboard.append(registro)
        details["dashboard_artefatos"] = registros_dashboard
        details["dashboard_erros"] = erros_dashboard
        if erros_dashboard:
            failures.append("manifestações dashboard inválidas ou divergentes: " + "; ".join(erros_dashboard))
    except Exception as exc:
        failures.append(f"falha na âncora dashboard: {exc}")
    invalid = []
    for rel in sorted(expected):
        path = ROOT / rel
        if not path.is_file() or path.is_symlink():
            invalid.append(rel)
    details["paths_esperados"] = len(expected)
    details["paths_invalidos_ou_symlinks"] = invalid
    if invalid:
        failures.append("allowlist contém path ausente, não regular ou symlink")
    result = {
        "status": "APROVADO" if not failures else "FALHOU",
        "base_commit": BASE,
        "allowlist_implementacao": len(allow),
        "estaticos_fechamento": sorted(STATIC),
        "detalhes": details,
        "falhas": failures,
        "limite_init_sem_baseline_r4": "__init__.py novo é somente docstring; não consta em hashes_pre_revisao e não foi alegado baseline anterior.",
        "testes_reexecutados": False,
        "ensaio_reexecutado": False,
    }
    (CLOSURE / "resultado_gate_implementacao.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
