"""Contratos locais e transformações puras do incremento metodológico v2.

Não lê rede, não carrega modelos v1 e não escreve na fotografia v1.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path


class ErroContratoV2(ValueError):
    """Entrada ou proveniência fora do contrato metodológico v2."""


CHAVE = ("temporada", "rodada", "piloto_id")
PROIBIDAS = {
    "posicao_final",
    "pontos",
    "status",
    "grid_resultado",
    "resultado_ausente",
    "results_grid",
    "existencia_resultado",
    "voltas",
    "paradas",
}


def _sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _utc(texto: str) -> datetime:
    if not isinstance(texto, str) or not texto.endswith("Z"):
        raise ErroContratoV2("timestamp UTC inválido")
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError as erro:
        raise ErroContratoV2("timestamp UTC inválido") from erro


def validar_linhas_pre_corrida(linhas: list[dict]) -> None:
    vistos = set()
    for linha in linhas:
        if not isinstance(linha, dict):
            raise ErroContratoV2("linha pré-corrida inválida")
        if any(campo in linha for campo in PROIBIDAS):
            raise ErroContratoV2("campo proibido na matriz pré-corrida")
        if linha.get("temporada") not in range(2021, 2026):
            raise ErroContratoV2("temporada deve estar entre 2021 e 2025")
        chave = tuple(linha.get(campo) for campo in CHAVE)
        if any(valor in (None, "") for valor in chave) or chave in vistos:
            raise ErroContratoV2("chave pré-corrida ausente ou duplicada")
        vistos.add(chave)
        if linha.get("classificacao_ausente") not in (0, False) or linha.get(
            "referencia_temporal_ausente"
        ) not in (0, False):
            raise ErroContratoV2(
                "população v2 requer classificação e referência temporal"
            )
        if not linha.get("equipe_id_entrada"):
            raise ErroContratoV2("equipe pré-corrida ausente")
        _utc(linha.get("limite_inferior_referencia_utc"))


def criar_manifesto_fontes(
    raiz: Path, relativos: list[str], manifesto_existente: dict | None = None
) -> dict:
    raiz = Path(raiz).resolve()
    fontes = []
    for relativo in sorted(relativos):
        caminho = (raiz / relativo).resolve()
        if not caminho.is_file() or raiz not in caminho.parents:
            raise ErroContratoV2("fonte ausente ou fora da raiz")
        hash_atual = _sha256(caminho)
        fontes.append(
            {
                "source_id": relativo,
                "relative_path": relativo,
                "sha256": hash_atual,
                "format": caminho.suffix.lstrip("."),
                "capturado_em_utc": None,
                "publicado_em_utc": None,
                "disponivel_em_utc": None,
                "schema_version": "metodologia-v2-fontes-v1",
            }
        )
    manifesto = {"schema": "metodologia-v2-fontes-v1", "fontes": fontes}
    if manifesto_existente is not None:
        anteriores = {
            item["relative_path"]: item["sha256"]
            for item in manifesto_existente.get("fontes", [])
        }
        for item in fontes:
            if (
                item["relative_path"] in anteriores
                and anteriores[item["relative_path"]] != item["sha256"]
            ):
                raise ErroContratoV2("hash de fonte divergente")
    return manifesto


def _ordem(linha: dict):
    return (linha["temporada"], linha["rodada"], linha["piloto_id"])


def construir_features_a3(linhas: list[dict]) -> dict[tuple, dict]:
    """Forma anterior; usa alvos somente de eventos estritamente anteriores."""
    validar_linhas_pre_corrida(linhas)
    ordenadas = sorted(linhas, key=_ordem)
    resultado = {}
    for atual in ordenadas:
        chave = tuple(atual[campo] for campo in CHAVE)
        anteriores = [
            item
            for item in ordenadas
            if (item["temporada"], item["rodada"])
            < (atual["temporada"], atual["rodada"])
        ]
        piloto = [
            item for item in anteriores if item["piloto_id"] == atual["piloto_id"]
        ][-5:]
        eventos_equipe = {}
        for item in anteriores:
            if item["equipe_id_entrada"] == atual["equipe_id_entrada"]:
                eventos_equipe.setdefault(
                    (item["temporada"], item["rodada"]), []
                ).append(item)
        eventos = [
            eventos_equipe[chave_evento] for chave_evento in sorted(eventos_equipe)[-5:]
        ]
        resultados_equipe = [item for evento in eventos for item in evento]
        podios_piloto = [
            item["podio"] for item in piloto if item.get("podio") in (0, 1)
        ]
        podios_equipe = [
            item["podio"] for item in resultados_equipe if item.get("podio") in (0, 1)
        ]
        resultado[chave] = {
            "n_piloto_5": len(piloto),
            "taxa_podios_piloto_5": (
                None if not podios_piloto else sum(podios_piloto) / len(podios_piloto)
            ),
            "n_gps_equipe_5": len(eventos),
            "n_participacoes_equipe_5": len(resultados_equipe),
            "taxa_podios_equipe_5": (
                None if not podios_equipe else sum(podios_equipe) / len(podios_equipe)
            ),
            "historico_piloto_insuficiente": int(len(piloto) < 5),
            "historico_equipe_insuficiente": int(len(eventos) < 5),
        }
    return resultado


def normalizar_ritmo_b1(sessao: dict, corte_utc: str) -> dict:
    """Valida fronteira temporal B1; ausência é devolvida sem ritmo sintético."""
    if not isinstance(sessao, dict) or sessao.get("sessao") not in {
        "FP1",
        "FP2",
        "FP3",
    }:
        raise ErroContratoV2("sessão B1 inválida")
    if _utc(sessao.get("fim_utc")) > _utc(corte_utc):
        raise ErroContratoV2("sessão B1 posterior ao corte")
    linhas = sessao.get("linhas")
    if not isinstance(linhas, list):
        raise ErroContratoV2("linhas B1 inválidas")
    return {
        "sessao": sessao["sessao"],
        "disponivel": bool(linhas),
        "motivo": None if linhas else "sem voltas utilizáveis",
        "linhas": linhas,
    }


def metricas_probabilisticas(alvos: list[int], probabilidades: list[float]) -> dict:
    """Métricas binárias puras; recusa coortes desalinhadas ou probabilidades inválidas."""
    if not alvos or len(alvos) != len(probabilidades):
        raise ErroContratoV2("coorte probabilística vazia ou desalinhada")
    if any(alvo not in (0, 1) for alvo in alvos):
        raise ErroContratoV2("alvo binário inválido")
    if any(
        not isinstance(probabilidade, (int, float))
        or not math.isfinite(probabilidade)
        or not 0 < probabilidade < 1
        for probabilidade in probabilidades
    ):
        raise ErroContratoV2("probabilidade inválida")
    n = len(alvos)
    return {
        "n": n,
        "brier": sum(
            (probabilidade - alvo) ** 2
            for alvo, probabilidade in zip(alvos, probabilidades)
        )
        / n,
        "log_loss": -sum(
            alvo * math.log(probabilidade) + (1 - alvo) * math.log(1 - probabilidade)
            for alvo, probabilidade in zip(alvos, probabilidades)
        )
        / n,
    }
