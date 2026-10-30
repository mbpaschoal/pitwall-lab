"""Validate bilingual product versions and prepare reproducible release notes.

This module neither changes VERSION nor publishes automatically. GitHub's tag
workflow calls publish only after the release tests have passed.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.request import Request, urlopen
from pitwall.paths import PROJECT_ROOT
from pitwall.version import version

DOCUMENT_PAIRS = (
    ("docs/OPERACAO_FIM_SEMANA.md", "docs/en/WEEKEND_OPERATION.md"),
    ("docs/REVISAO_030.md", "docs/en/REVIEW_030.md"),
    ("README.md", "README.en.md"),
    ("CHANGELOG.md", "CHANGELOG.en.md"),
    ("CONTRIBUTING.md", "CONTRIBUTING.en.md"),
    ("docs/ARQUITETURA.md", "docs/en/ARCHITECTURE.md"),
    ("docs/APRENDIZADOS.md", "docs/en/LEARNING.md"),
    ("docs/VERSOES.md", "docs/en/VERSIONS.md"),
    ("docs/DADOS_ATUAIS.md", "docs/en/CURRENT_DATA.md"),
    ("docs/experimento_modelo_v1.md", "docs/en/experimento_modelo_v1.md"),
    ("docs/protocolo_temporal.md", "docs/en/protocolo_temporal.md"),
    ("docs/dicionario_variaveis.md", "docs/en/dicionario_variaveis.md"),
    ("docs/avaliacao_final_v1.md", "docs/en/avaliacao_final_v1.md"),
    ("reports/modelo_v1/relatorio.md", "docs/en/relatorio_2024.md"),
    ("reports/avaliacao_final_v1/relatorio.md", "docs/en/relatorio_2025.md"),
)


def notes(selected_language, root=PROJECT_ROOT):
    if selected_language not in ("pt", "en"):
        raise ValueError("Language must be pt or en")
    filename = "CHANGELOG.md" if selected_language == "pt" else "CHANGELOG.en.md"
    text = (Path(root) / filename).read_text(encoding="utf-8")
    heading = re.search(
        r"^## " + re.escape(version(root)) + r" — (\d{4}-\d{2}-\d{2})\s*$", text, re.M
    )
    if not heading:
        raise ValueError("Current version is missing from " + filename)
    end = re.search(r"^## ", text[heading.end() :], re.M)
    body = text[
        heading.end() : heading.end() + end.start() if end else len(text)
    ].strip()
    if len(body) < 100:
        raise ValueError("Release notes must explain the delivered change")
    return body


def _git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def check(root=PROJECT_ROOT, base=None):
    root = Path(root)
    current = version(root)
    for pair in DOCUMENT_PAIRS:
        for name in pair:
            if not (root / name).is_file():
                raise ValueError("Missing bilingual document: " + name)
    for selected_language in ("pt", "en"):
        notes(selected_language, root)
    if base:
        # Read one file from an existing revision. No checkout/reset or scientific execution.
        existing = _git(root, "ls-tree", "--name-only", base, "VERSION")
        if existing:
            previous = _git(root, "show", base + ":VERSION")
            changed = _git(
                root,
                "diff",
                "--name-only",
                base,
                "--",
                "pitwall/",
                "frontend_assets/",
                "dashboard_assets/",
                "app.py",
                "operacao2026/",
                "distribuicao/pitwall-dashboard/",
            )
            if changed and tuple(map(int, current.split("."))) <= tuple(
                map(int, previous.split("."))
            ):
                raise ValueError("Product/data changes require a new version")
    return {
        "version": current,
        "document_pairs": len(DOCUMENT_PAIRS),
        "languages": ["pt", "en"],
    }


def publish(root=PROJECT_ROOT, asset=None):
    """Explicit tag-workflow operation; credentials are never printed or persisted."""
    check(root)
    current = version(root)
    if os.environ.get("GITHUB_REF") != "refs/tags/v" + current:
        raise ValueError("Release tag must match VERSION")
    repository = os.environ["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository")
    payload = {
        "tag_name": "v" + current,
        "name": "Pitwall Lab " + current,
        "body": "## Português\n\n"
        + notes("pt", root)
        + "\n\n## English\n\n"
        + notes("en", root),
        "draft": False,
        "prerelease": False,
    }
    request = Request(
        "https://api.github.com/repos/" + repository + "/releases",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if asset:
        from urllib.parse import urlencode
        asset = Path(asset)
        upload = Request(result["upload_url"].split("{")[0] + "?" + urlencode({"name": asset.name}),
            data=asset.read_bytes(), method="POST", headers={
                "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                "Content-Type": "application/zip", "Accept": "application/vnd.github+json"})
        with urlopen(upload, timeout=120) as response:
            uploaded = json.load(response)
        if uploaded.get("state") != "uploaded":
            raise ValueError("Release asset upload incomplete")
    return {"tag": payload["tag_name"], "url": result["html_url"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "notes", "publish"))
    parser.add_argument("--base")
    parser.add_argument("--asset", type=Path)
    parser.add_argument("--language", choices=("pt", "en"), default="pt")
    args = parser.parse_args()
    if args.command == "notes":
        print(notes(args.language))
    elif args.command == "publish":
        print(json.dumps(publish(asset=args.asset)))
    else:
        print(json.dumps(check(base=args.base)))


if __name__ == "__main__":
    main()
