"""Aquisição serial e limitada de sessões FastF1 para o piloto B1."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import csv
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from pitwall.paths import PROJECT_ROOT


COORTE_B1 = (
    {
        "temporada": 2021,
        "rodada": 1,
        "circuito_id": "bahrain",
        "corrida": "Bahrain Grand Prix",
    },
    {
        "temporada": 2021,
        "rodada": 10,
        "circuito_id": "silverstone",
        "corrida": "British Grand Prix",
    },
    {
        "temporada": 2022,
        "rodada": 1,
        "circuito_id": "bahrain",
        "corrida": "Bahrain Grand Prix",
    },
    {
        "temporada": 2022,
        "rodada": 10,
        "circuito_id": "silverstone",
        "corrida": "British Grand Prix",
    },
    {
        "temporada": 2023,
        "rodada": 1,
        "circuito_id": "bahrain",
        "corrida": "Bahrain Grand Prix",
    },
    {
        "temporada": 2023,
        "rodada": 10,
        "circuito_id": "silverstone",
        "corrida": "British Grand Prix",
    },
    {
        "temporada": 2024,
        "rodada": 1,
        "circuito_id": "bahrain",
        "corrida": "Bahrain Grand Prix",
    },
    {
        "temporada": 2024,
        "rodada": 10,
        "circuito_id": "catalunya",
        "corrida": "Spanish Grand Prix",
    },
    {
        "temporada": 2025,
        "rodada": 1,
        "circuito_id": "albert_park",
        "corrida": "Australian Grand Prix",
    },
    {
        "temporada": 2025,
        "rodada": 10,
        "circuito_id": "villeneuve",
        "corrida": "Canadian Grand Prix",
    },
)
LIMITE_BYTES = 1024**3


def _agora():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _tamanho(raiz):
    return sum(
        caminho.stat().st_size for caminho in Path(raiz).rglob("*") if caminho.is_file()
    )


def validar_sessao_antes_do_corte(fim_utc, corte_utc):
    try:
        fim = datetime.fromisoformat(str(fim_utc).replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
        corte = datetime.fromisoformat(
            str(corte_utc).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except ValueError:
        return False
    return fim <= corte


def normalizar_horarios_fastf1(info):
    """Lê o schema FastF1 3.6: StartDate/EndDate locais + GmtOffset."""
    inicio, fim, offset = (
        info.get("StartDate"),
        info.get("EndDate"),
        info.get("GmtOffset"),
    )
    if inicio is None or fim is None or offset is None:
        return None, None
    try:
        segundos = offset.total_seconds() if hasattr(offset, "total_seconds") else None
        if segundos is None:
            texto = str(offset)
            encontrado = re.search(
                r"(?:(\d+)\s+days?\s+)?([+-]?\d+):(\d+):(\d+)", texto
            )
            if not encontrado:
                return None, None
            dias, horas, minutos, segundos_texto = encontrado.groups()
            segundos = (
                (int(dias or 0) * 86400)
                + (int(horas) * 3600)
                + (int(minutos) * 60)
                + int(segundos_texto)
            )

        def converter(valor):
            if hasattr(valor, "to_pydatetime"):
                valor = valor.to_pydatetime()
            if isinstance(valor, str):
                valor = datetime.fromisoformat(valor)
            if valor.tzinfo is None:
                return valor.replace(tzinfo=timezone.utc).timestamp() - segundos
            return valor.astimezone(timezone.utc).timestamp()

        return tuple(
            datetime.fromtimestamp(converter(valor), timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
            for valor in (inicio, fim)
        )
    except (TypeError, ValueError, OverflowError):
        return None, None


def corte_evento(evento, raiz=PROJECT_ROOT):
    caminho = Path(raiz) / "data" / "preparado" / "base_historica.csv"
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        encontrados = {
            linha["limite_inferior_referencia_utc"]
            for linha in csv.DictReader(arquivo)
            if int(linha["temporada"]) == evento["temporada"]
            and int(linha["rodada"]) == evento["rodada"]
        }
    if len(encontrados) != 1 or not next(iter(encontrados)):
        return None
    return next(iter(encontrados))


def escrever_manifesto(destino, registros):
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "manifesto_coleta.json").write_text(
        json.dumps(
            {
                "schema": "metodologia-v2-b1-coleta-v2",
                "coorte": list(COORTE_B1),
                "limite_bytes": LIMITE_BYTES,
                "registros": registros,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _segundos(valor):
    if valor is None or str(valor) in {"NaT", "nan", "None"}:
        return None
    try:
        if hasattr(valor, "total_seconds"):
            return float(valor.total_seconds())
        return float(valor)
    except (TypeError, ValueError):
        return None


def _booleano_ou_nulo(valor):
    if valor is None or str(valor) in {"NaT", "nan", "None"}:
        return None
    return bool(valor)


def normalizar_voltas(voltas):
    obrigatorias = [
        "Driver",
        "DriverNumber",
        "LapNumber",
        "LapTime",
        "Compound",
        "TyreLife",
        "Stint",
        "TrackStatus",
        "Deleted",
        "FastF1Generated",
        "IsAccurate",
        "PitInTime",
        "PitOutTime",
    ]
    ausentes = [campo for campo in obrigatorias if campo not in voltas.columns]
    if ausentes:
        raise ValueError("colunas de volta ausentes: {}".format(",".join(ausentes)))
    resultado = []
    for item in voltas[obrigatorias].to_dict("records"):
        resultado.append(
            {
                "driver_fastf1": str(item["Driver"]),
                "driver_number": str(item["DriverNumber"]),
                "lap_number": _segundos(item["LapNumber"]),
                "lap_time_s": _segundos(item["LapTime"]),
                "compound": (
                    None
                    if str(item["Compound"]) in {"nan", "None"}
                    else str(item["Compound"])
                ),
                "tyre_life": _segundos(item["TyreLife"]),
                "stint": _segundos(item["Stint"]),
                "track_status": (
                    None
                    if str(item["TrackStatus"]) in {"nan", "None"}
                    else str(item["TrackStatus"])
                ),
                "deleted": _booleano_ou_nulo(item["Deleted"]),
                "fastf1_generated": _booleano_ou_nulo(item["FastF1Generated"]),
                "is_accurate": _booleano_ou_nulo(item["IsAccurate"]),
                "pit_in_s": _segundos(item["PitInTime"]),
                "pit_out_s": _segundos(item["PitOutTime"]),
            }
        )
    return resultado


def coletar(
    destino,
    limite_bytes=LIMITE_BYTES,
    fastf1_module=None,
    coorte=COORTE_B1,
    corte_fn=corte_evento,
):
    """Coleta uma sessão por vez; indisponibilidade é registrada, nunca substituída."""
    if fastf1_module is None:
        import fastf1 as fastf1_module
    destino = Path(destino)
    cache = destino / "cache_fastf1"
    cache.mkdir(parents=True, exist_ok=True)
    fastf1_module.Cache.enable_cache(str(cache))
    registros = []
    for evento in coorte:
        corte = corte_fn(evento)
        for nome in ("FP1", "FP2", "FP3"):
            if _tamanho(destino) >= limite_bytes:
                registros.append(
                    {
                        **evento,
                        "sessao": nome,
                        "estado": "limite_disco",
                        "obtido_em_utc": _agora(),
                    }
                )
                escrever_manifesto(destino, registros)
                return registros
            registro = {
                **evento,
                "sessao": nome,
                "corte_utc": corte,
                "obtido_em_utc": _agora(),
            }
            try:
                sessao = fastf1_module.get_session(
                    evento["temporada"], evento["rodada"], nome
                )
                sessao.load(telemetry=False, weather=False, messages=True)
                inicio, fim = normalizar_horarios_fastf1(
                    getattr(sessao, "session_info", {})
                )
                if inicio is None or fim is None:
                    registro.update(
                        {
                            "estado": "indisponivel",
                            "motivo": "horário de sessão ausente",
                        }
                    )
                elif corte is None or not validar_sessao_antes_do_corte(
                    str(fim), corte
                ):
                    registro.update(
                        {
                            "estado": "posterior_ao_corte",
                            "motivo": "sessão posterior ao corte ou corte ausente",
                            "fim_utc": str(fim),
                        }
                    )
                else:
                    saida = destino / "{}-r{:02d}-{}.json".format(
                        evento["temporada"], evento["rodada"], nome.lower()
                    )
                    voltas = normalizar_voltas(sessao.laps)
                    payload = {
                        "schema": "metodologia-v2-b1-sessao-v2",
                        "evento": evento,
                        "sessao": nome,
                        "inicio_utc": inicio,
                        "fim_utc": fim,
                        "voltas": voltas,
                    }
                    texto = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                    saida.write_text(texto, encoding="utf-8")
                    registro.update(
                        {
                            "estado": "coletado",
                            "arquivo": saida.name,
                            "linhas": len(voltas),
                            "inicio_utc": str(inicio),
                            "fim_utc": str(fim),
                            "sha256": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
                        }
                    )
            except Exception as erro:
                registro.update(
                    {
                        "estado": "indisponivel",
                        "motivo": "{}: {}".format(type(erro).__name__, erro)[:500],
                    }
                )
            registros.append(registro)
            escrever_manifesto(destino, registros)
    return registros


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destino", required=True)
    parser.add_argument("--limite-bytes", type=int, default=LIMITE_BYTES)
    argumentos = parser.parse_args()
    coletar(argumentos.destino, argumentos.limite_bytes)


if __name__ == "__main__":
    main()
