"""Leitura somente local do contrato editorial comum do dashboard."""

import json
from pathlib import Path


class ContextoEditorialErro(ValueError):
    pass


def carregar(raiz):
    caminho = Path(raiz) / "frontend_assets" / "contexto_editorial.json"
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ContextoEditorialErro(
            "Contexto editorial indisponível: {}.".format(caminho)
        ) from erro
    if dados.get("versao") != 1 or dados.get("temporadas") != [2024, 2025, 2026]:
        raise ContextoEditorialErro(
            "Contexto editorial com versão ou temporadas inválidas."
        )
    eventos = dados.get("eventos")
    if not isinstance(eventos, list):
        raise ContextoEditorialErro("Contexto editorial sem eventos válidos.")
    por_chave = {}
    obrigatorios = (
        "temporada",
        "rodada",
        "corrida",
        "data",
        "circuito_id",
        "circuito_nome",
        "cidade",
        "pais",
    )
    for evento in eventos:
        if not isinstance(evento, dict) or any(
            campo not in evento for campo in obrigatorios
        ):
            raise ContextoEditorialErro("Contexto editorial com evento incompleto.")
        if (
            evento["temporada"] not in (2024, 2025, 2026)
            or not isinstance(evento["rodada"], int)
            or evento["rodada"] < 1
        ):
            raise ContextoEditorialErro("Contexto editorial com chave inválida.")
        if any(
            not isinstance(evento[campo], str) or not evento[campo]
            for campo in obrigatorios[2:]
        ):
            raise ContextoEditorialErro(
                "Contexto editorial com texto obrigatório inválido."
            )
        chave = (evento["temporada"], evento["rodada"])
        if chave in por_chave:
            raise ContextoEditorialErro("Contexto editorial com evento duplicado.")
        por_chave[chave] = dict(evento)
    return por_chave


def para_gp(contextos, temporada, rodada):
    try:
        return dict(contextos[(int(temporada), int(rodada))])
    except (KeyError, TypeError, ValueError) as erro:
        raise ContextoEditorialErro(
            "Contexto editorial ausente para temporada {} rodada {}.".format(
                temporada, rodada
            )
        ) from erro
