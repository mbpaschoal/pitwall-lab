"""Leitura segura do catálogo local de fotografia e mapas de circuitos."""

import json
import re
import hashlib
from html import unescape
from pathlib import Path


class CatalogoVisualErro(ValueError):
    pass


def _ler_ativo_regular(raiz, relativo):
    raiz = Path(raiz).resolve()
    caminho_relativo = Path(relativo)
    if caminho_relativo.is_absolute() or ".." in caminho_relativo.parts:
        raise CatalogoVisualErro("Ativo visual fora da raiz: {}.".format(relativo))
    candidato = raiz / caminho_relativo
    if candidato.is_symlink() or any(
        p.is_symlink() for p in candidato.parents if p != raiz.parent
    ):
        raise CatalogoVisualErro(
            "Ativo visual não pode usar symlink: {}.".format(relativo)
        )
    try:
        arquivo = candidato.resolve(strict=True)
        arquivo.relative_to(raiz)
    except (OSError, ValueError) as erro:
        raise CatalogoVisualErro(
            "Ativo visual fora da raiz: {}.".format(relativo)
        ) from erro
    if not arquivo.is_file():
        raise CatalogoVisualErro("Ativo visual ausente: {}.".format(relativo))
    return arquivo.read_bytes()


def _texto_publicavel(valor):
    return re.sub(
        r"\s+", " ", unescape(re.sub(r"<[^>]*>", "", str(valor or "")))
    ).strip()


def carregar(raiz):
    try:
        dados = json.loads(
            _ler_ativo_regular(
                raiz, "dashboard_assets/circuit/catalogo_visual.json"
            ).decode("utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise CatalogoVisualErro("Catálogo visual indisponível.") from erro
    if dados.get("versao") != 1 or not isinstance(dados.get("circuitos"), dict):
        raise CatalogoVisualErro("Catálogo visual inválido.")
    saida = {}
    for circuito, ativos in dados["circuitos"].items():
        if (
            not isinstance(circuito, str)
            or not circuito
            or not isinstance(ativos, dict)
        ):
            raise CatalogoVisualErro("Catálogo visual com circuito inválido.")
        foto, mapa = ativos.get("foto"), ativos.get("mapa")
        if not isinstance(foto, dict) or not isinstance(mapa, dict):
            raise CatalogoVisualErro("Catálogo visual com ativos incompletos.")
        for item in (foto, mapa):
            obrigatorios = ("caminho", "sha256", "autor", "licenca", "pagina", "mime")
            if any(
                not isinstance(item.get(campo), str) or not item[campo]
                for campo in obrigatorios
            ):
                raise CatalogoVisualErro(
                    "Catálogo visual com metadado obrigatório ausente."
                )
            conteudo = _ler_ativo_regular(raiz, item["caminho"])
            if hashlib.sha256(conteudo).hexdigest() != item["sha256"]:
                raise CatalogoVisualErro(
                    "Hash divergente no ativo visual: {}.".format(item["caminho"])
                )
        foto_publica, mapa_publico = dict(foto), dict(mapa)
        foto_publica["autor"] = _texto_publicavel(foto_publica["autor"])
        mapa_publico["autor"] = _texto_publicavel(mapa_publico["autor"])
        saida[circuito] = {
            "foto": foto_publica,
            "mapa": mapa_publico,
            "alt_foto": ativos.get("alt_foto", ""),
        }
    return saida


def para_circuito(catalogo, circuito_id):
    return catalogo.get(circuito_id)
