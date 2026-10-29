"""Estratégias observadas: paradas registradas, nunca recomendações ou entradas.

O runtime lê somente um asset portátil. A preparação explícita valida hashes,
paginação e identidades locais; não consulta rede. Jolpica/Ergast não fornece
compostos neste material: paradas não são convertidas em trocas de pneus.
"""

import copy
import csv
import hashlib
import io
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from pitwall.data.editorial import carregar as carregar_contextos, para_gp


ASSET = "frontend_assets/estrategias_gp.json"
AUDITORIA_ARCHIVE = (
    "data/metodologia_v2/a1_archive_audit_20261026T0102Z/manifesto_archive_v2.json"
)
AUSTIN = "data/operacao_2026/pos_corrida/austin-20261026T111018Z"
SNAPSHOT_AUSTIN = "data/operacao_2026/snapshots/austin-pos-corrida-20261026T111018Z-r2"
AVISO = "Dados observados após a corrida; não são recomendações nem entradas do modelo."
LIMITE = (
    "São paradas registradas na fonte. A duração publicada não é o tempo parado de troca de pneus; "
    "pode incluir trânsito no pit lane e interrupções. Não há compostos, idade dos pneus ou trocas "
    "sob bandeira vermelha documentados neste asset."
)


class EstrategiasDadosErro(ValueError):
    pass


def _ler(root, relativo):
    root = Path(root).resolve()
    rel = Path(relativo)
    if rel.is_absolute() or ".." in rel.parts:
        raise EstrategiasDadosErro("Arquivo fora da raiz.")
    arquivo = root / rel
    atual = arquivo
    while atual != root:
        if atual.is_symlink():
            raise EstrategiasDadosErro("Arquivo de estratégia não pode usar symlink.")
        atual = atual.parent
    arquivo.resolve(strict=True).relative_to(root)
    return arquivo.read_bytes()


def _inteiro(valor, minimo=0):
    if (
        isinstance(valor, bool)
        or not re.fullmatch(r"[0-9]+", str(valor))
        or int(valor) < minimo
    ):
        raise EstrategiasDadosErro("Inteiro inválido na estratégia.")
    return int(valor)


def _texto(valor):
    if not isinstance(valor, str) or not valor.strip():
        raise EstrategiasDadosErro("Identificação ausente na estratégia.")
    return valor.strip()


def _segundos(valor):
    try:
        partes = str(valor).split(":")
        if len(partes) > 3:
            raise ValueError()
        total = 0.0
        for parte in partes:
            total = total * 60 + float(parte)
    except (ValueError, TypeError):
        raise EstrategiasDadosErro("Duração publicada inválida.")
    if not math.isfinite(total) or total <= 0:
        raise EstrategiasDadosErro("Duração publicada inválida.")
    return total


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _fonte_json(root, pasta, fonte, fontes, prefixo):
    raw = _ler(root, str(Path(pasta) / fonte["arquivo"]))
    if _sha(raw) != fonte["sha256"]:
        raise EstrategiasDadosErro(
            "SHA-256 divergente na estratégia: {}.".format(fonte["arquivo"])
        )
    fid = "{}:{}".format(prefixo, fonte["arquivo"])
    fontes[fid] = {
        "origem": "Jolpica-F1",
        "arquivo": str(Path(pasta) / fonte["arquivo"]),
        "sha256": fonte["sha256"],
        "url": fonte.get("url_real") or fonte.get("url_consultada"),
        "obtido_em_utc": fonte.get("obtido_em_utc", "desconhecida"),
    }
    return fid, json.loads(raw)["MRData"]


def _url_resultados(dados, ano, rodada=None):
    url = urlparse(dados["url"])
    path = (
        "/ergast/f1/{}/".format(ano)
        + ("{}/".format(rodada) if rodada else "")
        + "results/"
    )
    if url.scheme != "https" or url.hostname != "api.jolpi.ca" or url.path != path:
        raise EstrategiasDadosErro(
            "Proveniência de resultado incompatível com a corrida."
        )


def _resultados_historicos(root, ano, fontes):
    pasta = "data/historico/{}".format(ano)
    manifesto = json.loads(_ler(root, pasta + "/manifesto.json"))
    entradas = sorted(
        (x for x in manifesto["proveniencia"] if x["endpoint"] == "resultados"),
        key=lambda x: int(x["parametros"]["offset"]),
    )
    corridas, referencias, proximo, total = {}, defaultdict(list), 0, None
    for fonte in entradas:
        fid, dados = _fonte_json(root, pasta, fonte, fontes, "jolpica-" + str(ano))
        _url_resultados(dados, ano)
        if _inteiro(dados["offset"]) != proximo or str(
            dados["RaceTable"]["season"]
        ) != str(ano):
            raise EstrategiasDadosErro("Paginação ou temporada de resultados inválida.")
        pagina_total = _inteiro(dados["total"], 1)
        total = pagina_total if total is None else total
        if total != pagina_total:
            raise EstrategiasDadosErro("Total de resultados inconsistente.")
        n = 0
        for corrida in dados["RaceTable"]["Races"]:
            rodada = _inteiro(corrida["round"], 1)
            identidade = (
                str(corrida["season"]),
                rodada,
                corrida["Circuit"]["circuitId"],
                corrida["date"],
            )
            if identidade[0] != str(ano):
                raise EstrategiasDadosErro("Corrida de outra temporada.")
            if rodada not in corridas:
                corridas[rodada] = {k: v for k, v in corrida.items() if k != "Results"}
                corridas[rodada]["Results"] = []
            existente = corridas[rodada]
            if (existente["Circuit"]["circuitId"], existente["date"]) != identidade[2:]:
                raise EstrategiasDadosErro("Fragmentos de corrida incompatíveis.")
            existente["Results"].extend(corrida["Results"])
            referencias[rodada].append(fid)
            n += len(corrida["Results"])
        limite = _inteiro(dados["limit"], 1)
        if n != min(limite, total - proximo):
            raise EstrategiasDadosErro("Página de resultados incompleta.")
        proximo += n
    if not entradas or proximo != total:
        raise EstrategiasDadosErro("Resultados históricos incompletos.")
    return corridas, referencias


def _participantes(corrida):
    saida = []
    for item in corrida["Results"]:
        d, equipe = item["Driver"], item["Constructor"]
        saida.append(
            {
                "piloto_id": d["driverId"],
                "piloto": "{} {}".format(d["givenName"], d["familyName"]),
                "equipe_id": equipe["constructorId"],
                "equipe": equipe["name"],
                "posicao_final": _inteiro(item["position"], 1),
                "voltas_completadas": _inteiro(item["laps"]),
            }
        )
    if len({p["piloto_id"] for p in saida}) != len(saida):
        raise EstrategiasDadosErro("Piloto duplicado no resultado.")
    return sorted(saida, key=lambda x: x["posicao_final"])


def _gp(corrida, paradas, referencias):
    participantes = _participantes(corrida)
    return {
        "temporada": int(corrida["season"]),
        "rodada": int(corrida["round"]),
        "circuito_id": corrida["Circuit"]["circuitId"],
        "data": corrida["date"],
        "corrida": corrida["raceName"],
        "voltas_corrida": max(p["voltas_completadas"] for p in participantes),
        "participantes": participantes,
        "paradas": sorted(
            paradas, key=lambda p: (p["volta"], p["piloto_id"], p["parada"])
        ),
        "pneus_disponiveis": False,
        "fontes_ids": sorted(set(referencias)),
    }


def _validar_gp(gp):
    ano, rodada = _inteiro(gp["temporada"], 2024), _inteiro(gp["rodada"], 1)
    if ano not in (2024, 2025, 2026) or rodada > 24:
        raise EstrategiasDadosErro("Temporada ou rodada inválida.")
    _texto(gp["circuito_id"])
    _texto(gp["data"])
    _texto(gp["corrida"])
    max_lap = _inteiro(gp["voltas_corrida"], 1)
    participantes, pits = gp["participantes"], gp["paradas"]
    if (
        not isinstance(participantes, list)
        or not participantes
        or not isinstance(pits, list)
        or not pits
    ):
        raise EstrategiasDadosErro("População ou paradas ausentes.")
    ids = [_texto(p["piloto_id"]) for p in participantes]
    if len(ids) != len(set(ids)):
        raise EstrategiasDadosErro("Identidade de piloto duplicada.")
    for p in participantes:
        _texto(p["piloto"])
        _texto(p["equipe"])
        _texto(p["equipe_id"])
        _inteiro(p["posicao_final"], 1)
        if _inteiro(p["voltas_completadas"]) > max_lap:
            raise EstrategiasDadosErro("Voltas de piloto incompatíveis.")
    contagens = defaultdict(list)
    for pit in pits:
        if pit["piloto_id"] not in ids:
            raise EstrategiasDadosErro("Parada de piloto fora do resultado.")
        numero, lap = _inteiro(pit["parada"], 1), _inteiro(pit["volta"], 1)
        if lap > max_lap:
            raise EstrategiasDadosErro("Parada fora das voltas da corrida.")
        duracao = pit["duracao_segundos"]
        if (
            isinstance(duracao, bool)
            or not isinstance(duracao, (int, float))
            or not math.isfinite(duracao)
            or duracao <= 0
        ):
            raise EstrategiasDadosErro("Duração publicada inválida.")
        if abs(_segundos(pit["duracao_original"]) - duracao) > 0.001:
            raise EstrategiasDadosErro("Unidade de duração inconsistente.")
        if not re.fullmatch(r"[0-9]{2}:[0-9]{2}:[0-9]{2}", pit["hora_original"]):
            raise EstrategiasDadosErro("Horário da parada inválido.")
        contagens[pit["piloto_id"]].append((numero, lap))
    for sequencia in contagens.values():
        sequencia.sort()
        if [n for n, lap in sequencia] != list(range(1, len(sequencia) + 1)) or [
            lap for n, lap in sequencia
        ] != sorted(lap for n, lap in sequencia):
            raise EstrategiasDadosErro("Paradas duplicadas ou sequência incompleta.")
    if gp.get("pneus_disponiveis") is not False or not gp.get("fontes_ids"):
        raise EstrategiasDadosErro("Contrato de pneus ou proveniência inválido.")


def _archive(root, archive, fontes):
    archive = Path(archive)
    manifesto = json.loads(_ler(root, AUDITORIA_ARCHIVE))
    hashes = {x["arquivo"]: x["sha256"] for x in manifesto["fontes"]}
    tabelas = {}
    ids_fontes = []
    for nome in ("races.csv", "drivers.csv", "circuits.csv", "pit_stops.csv"):
        caminho = archive / nome
        if caminho.is_symlink():
            raise EstrategiasDadosErro("Archive não pode usar symlink.")
        raw = caminho.read_bytes()
        if _sha(raw) != hashes[nome]:
            raise EstrategiasDadosErro("SHA-256 do archive diverge da auditoria A1.")
        tabelas[nome] = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
        fid = "archive:" + nome
        ids_fontes.append(fid)
        fontes[fid] = {
            "origem": "Archive local Ergast/Kaggle",
            "arquivo": nome,
            "sha256": hashes[nome],
            "url": "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020",
            "obtido_em_utc": "desconhecida",
        }
    drivers = {x["driverId"]: x for x in tabelas["drivers.csv"]}
    circuits = {x["circuitId"]: x for x in tabelas["circuits.csv"]}
    races = {
        x["raceId"]: x for x in tabelas["races.csv"] if int(x["year"]) in (2024, 2025)
    }
    pits = defaultdict(list)
    for x in tabelas["pit_stops.csv"]:
        if x["raceId"] not in races:
            continue
        duration = _inteiro(x["milliseconds"], 1) / 1000
        if abs(_segundos(x["duration"]) - duration) > 0.001:
            raise EstrategiasDadosErro("Milissegundos divergentes do tempo original.")
        pits[x["raceId"]].append(
            {
                "piloto_id": drivers[x["driverId"]]["driverRef"],
                "parada": _inteiro(x["stop"], 1),
                "volta": _inteiro(x["lap"], 1),
                "hora_original": x["time"],
                "duracao_original": x["duration"],
                "duracao_segundos": duration,
            }
        )
    saida = []
    for ano in (2024, 2025):
        canon, referencias = _resultados_historicos(root, ano, fontes)
        for rid, race in races.items():
            if int(race["year"]) != ano or not pits[rid]:
                continue
            rodada = int(race["round"])
            circuito = circuits[race["circuitId"]]["circuitRef"]
            if rodada not in canon or (
                canon[rodada]["Circuit"]["circuitId"],
                canon[rodada]["date"],
            ) != (circuito, race["date"]):
                raise EstrategiasDadosErro(
                    "RaceId não corresponde literalmente ao calendário canônico."
                )
            saida.append(
                _gp(canon[rodada], pits[rid], ids_fontes + referencias[rodada])
            )
    return saida


def _austin(root, fontes):
    index = json.loads(_ler(root, SNAPSHOT_AUSTIN + "/indice.json"))
    result_source = [
        x
        for x in index["fontes"]
        if x["endpoint"] == "resultados" and x.get("rodada") == "18"
    ]
    if len(result_source) != 1:
        raise EstrategiasDadosErro("Resultado de Austin ausente ou ambíguo.")
    result_id, dados = _fonte_json(
        root, SNAPSHOT_AUSTIN, result_source[0], fontes, "austin-resultados"
    )
    _url_resultados(dados, 2026, 18)
    if _inteiro(dados["offset"]) != 0 or _inteiro(dados["total"]) != len(
        dados["RaceTable"]["Races"][0]["Results"]
    ):
        raise EstrategiasDadosErro("Resultado de Austin incompleto.")
    corrida = dados["RaceTable"]["Races"][0]
    if (
        corrida["season"],
        corrida["round"],
        corrida["Circuit"]["circuitId"],
        corrida["date"],
    ) != ("2026", "18", "americas", "2026-10-25"):
        raise EstrategiasDadosErro("Identidade de Austin divergente.")
    inventory = json.loads(_ler(root, AUSTIN + "/inventario.json"))
    if inventory.get("estado") != "coleta_concluida" or inventory.get("identidade") != {
        "temporada": 2026,
        "rodada": 18,
        "circuito_id": "americas",
        "data": "2026-10-25",
    }:
        raise EstrategiasDadosErro("Inventário de Austin inválido.")
    sources = sorted(
        (x for x in inventory["fontes"] if x["endpoint"] == "pit_stops"),
        key=lambda x: x["parametros"]["offset"],
    )
    pits, refs, offset = [], [result_id], 0
    total = _inteiro(inventory["endpoints"]["pit_stops"]["total"], 1)
    for source in sources:
        fid, data = _fonte_json(root, AUSTIN, source, fontes, "austin-pit-stops")
        url = urlparse(data["url"])
        if (
            source["status"] != 200
            or url.scheme != "https"
            or url.hostname != "api.jolpi.ca"
            or url.path != "/ergast/f1/2026/18/pitstops/"
        ):
            raise EstrategiasDadosErro("Proveniência de pit stops de Austin inválida.")
        if _inteiro(data["offset"]) != offset or _inteiro(data["total"]) != total:
            raise EstrategiasDadosErro("Paginação de pit stops incompleta.")
        races = data["RaceTable"]["Races"]
        if len(races) != 1 or (
            races[0]["season"],
            races[0]["round"],
            races[0]["Circuit"]["circuitId"],
            races[0]["date"],
        ) != ("2026", "18", "americas", "2026-10-25"):
            raise EstrategiasDadosErro("Pit stops de outro GP.")
        rows = races[0]["PitStops"]
        if len(rows) != min(_inteiro(data["limit"], 1), total - offset):
            raise EstrategiasDadosErro("Página de pit stops incompleta.")
        pits.extend(
            {
                "piloto_id": x["driverId"],
                "parada": int(x["stop"]),
                "volta": int(x["lap"]),
                "hora_original": x["time"],
                "duracao_original": x["duration"],
                "duracao_segundos": _segundos(x["duration"]),
            }
            for x in rows
        )
        offset += len(rows)
        refs.append(fid)
    if offset != total:
        raise EstrategiasDadosErro("Pit stops de Austin incompletos.")
    return _gp(corrida, pits, refs)


def gerar_asset(root, destino, archive=Path.home() / "Downloads" / "archive"):
    """Preparação offline explícita; não sobrescreve saída divergente."""
    fontes = {}
    gps = sorted(
        _archive(root, archive, fontes) + [_austin(root, fontes)],
        key=lambda x: (x["temporada"], x["rodada"]),
    )
    contextos = carregar_contextos(root)
    for gp in gps:
        _validar_gp(gp)
        contexto = para_gp(contextos, gp["temporada"], gp["rodada"])
        if (contexto["circuito_id"], contexto["data"]) != (
            gp["circuito_id"],
            gp["data"],
        ):
            raise EstrategiasDadosErro(
                "Identidade do GP incompatível com o contexto editorial."
            )
    asset = {
        "versao": 1,
        "uso": "contexto_descritivo_pos_corrida",
        "aviso": AVISO,
        "limites": LIMITE,
        "fontes": fontes,
        "gps": gps,
    }
    raw = (
        json.dumps(asset, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    destino = Path(destino)
    if destino.exists() and destino.read_bytes() != raw:
        raise EstrategiasDadosErro("Asset existente diverge; não sobrescrito.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(raw)
    return asset


def carregar_estrategia(root, temporada, rodada, circuito_id):
    """API portátil: paradas observadas por GP, com ausência explícita de pneus.

    Retorna disponivel,motivo,aviso,limites,identidade,voltas_corrida,paradas,
    participantes (inclui n_paradas_registradas),fontes,pneus_disponiveis=False.
    """
    vazio = {
        "disponivel": False,
        "motivo": "Paradas desta corrida indisponíveis no snapshot local.",
        "aviso": AVISO,
        "limites": LIMITE,
        "temporada": temporada,
        "rodada": rodada,
        "circuito_id": circuito_id,
        "paradas": [],
        "participantes": [],
        "fontes": [],
        "pneus_disponiveis": False,
    }
    try:
        contexto = para_gp(carregar_contextos(root), temporada, rodada)
        if contexto["circuito_id"] != circuito_id:
            raise EstrategiasDadosErro("Circuito não corresponde ao GP selecionado.")
        dados = json.loads(_ler(root, ASSET))
        if (
            dados.get("versao") != 1
            or dados.get("uso") != "contexto_descritivo_pos_corrida"
            or not isinstance(dados.get("gps"), list)
        ):
            raise EstrategiasDadosErro("Asset de estratégias inválido.")
        chaves = [(g["temporada"], g["rodada"]) for g in dados["gps"]]
        if len(chaves) != len(set(chaves)):
            raise EstrategiasDadosErro("GP duplicado no asset de estratégias.")
        matches = [
            g
            for g in dados["gps"]
            if (g["temporada"], g["rodada"]) == (temporada, rodada)
        ]
        if not matches:
            return vazio
        gp = copy.deepcopy(matches[0])
        _validar_gp(gp)
        if (gp["circuito_id"], gp["data"]) != (circuito_id, contexto["data"]):
            raise EstrategiasDadosErro("Estratégia pertence a outro circuito ou data.")
        refs = []
        for fid in gp["fontes_ids"]:
            fonte = dados["fontes"][fid]
            if (
                not re.fullmatch("[0-9a-f]{64}", fonte["sha256"])
                or not fonte.get("url")
                or not fonte.get("obtido_em_utc")
            ):
                raise EstrategiasDadosErro("Proveniência de estratégia incompleta.")
            refs.append(fonte)
        por_piloto = defaultdict(int)
        for pit in gp["paradas"]:
            por_piloto[pit["piloto_id"]] += 1
        for piloto in gp["participantes"]:
            piloto["n_paradas_registradas"] = por_piloto[piloto["piloto_id"]]
        gp.update(
            {
                "disponivel": True,
                "motivo": "",
                "aviso": AVISO,
                "limites": LIMITE,
                "fontes": refs,
            }
        )
        return gp
    except (OSError, ValueError, KeyError, TypeError) as erro:
        vazio["motivo"] = "Estratégias indisponíveis: {}.".format(erro)
        return vazio
