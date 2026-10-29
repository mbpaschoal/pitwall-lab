"""Acervo descritivo 2024–2026 a partir de fontes locais preservadas, sem rede.

Não prepara entradas de modelos nem modifica snapshots. O calendário/resultados
canônicos prevalecem; o archive complementa voltas, paradas, Sprint e campeonatos.
"""

from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import math
from pathlib import Path

from coletar_historico import carregar_temporada
from operacao2026 import fontes


SNAPSHOT_2026 = "austin-pos-corrida-20261026T111018Z-r2"
SNAPSHOTS_Q = (
    "classificacoes-retro-20261024T064010Z",
    "coleta-20261020T020130Z",
    SNAPSHOT_2026,
)
AUSTIN = "data/operacao_2026/pos_corrida/austin-20261026T111018Z"
AUDITORIA_ARCHIVE = (
    "data/metodologia_v2/a1_archive_audit_20261026T0102Z/manifesto_archive_v2.json"
)
SESSOES = (
    "FirstPractice",
    "SecondPractice",
    "ThirdPractice",
    "Qualifying",
    "Sprint",
    "SprintQualifying",
    "SprintShootout",
)
CHAVES = ["temporada", "rodada", "circuito_id"]
PROV = ["fonte_id", "obtido_em_utc"]
RESULTADO = [
    "piloto_id",
    "piloto",
    "equipe_id",
    "numero",
    "posicao_final",
    "position_text",
    "pontos",
    "grid_resultado_auditoria",
    "voltas",
    "status",
    "tempo_original",
    "tempo_millis_original",
    "melhor_volta",
    "melhor_tempo",
]
SCHEMAS = {
    "resultados.csv": CHAVES + RESULTADO + PROV,
    "classificacao.csv": CHAVES
    + [
        "piloto_id",
        "piloto",
        "equipe_id",
        "posicao_classificacao",
        "q1_original",
        "q2_original",
        "q3_original",
    ]
    + PROV,
    "voltas_corrida.csv": CHAVES
    + ["piloto_id", "equipe_id", "volta", "posicao", "tempo_original", "tempo_segundos"]
    + PROV,
    "pit_stops.csv": CHAVES
    + [
        "piloto_id",
        "equipe_id",
        "parada",
        "volta",
        "hora_original",
        "duracao_original",
        "duracao_segundos",
    ]
    + PROV,
    "sprint_resultados.csv": CHAVES + RESULTADO + PROV,
    "campeonato_equipes.csv": CHAVES
    + ["equipe_id", "posicao", "pontos", "vitorias"]
    + PROV,
    "campeonato_pilotos.csv": CHAVES
    + ["piloto_id", "equipes_publicadas", "posicao", "pontos", "vitorias"]
    + PROV,
    "conflitos_classificacao.csv": CHAVES
    + [
        "piloto_id",
        "campo",
        "valor_canonico",
        "valor_archive",
        "fonte_canonica",
        "fonte_archive",
        "decisao",
    ],
}


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _valor(value):
    return None if value is None or str(value).strip() in ("", "\\N") else value


def _segundos(value):
    value = _valor(value)
    if value is None:
        return None
    try:
        total = 0.0
        for part in str(value).split(":"):
            total = total * 60 + float(part)
    except (TypeError, ValueError) as error:
        raise ValueError("Tempo inválido: {!r}".format(value)) from error
    if not math.isfinite(total) or total < 0:
        raise ValueError("Tempo não finito ou negativo: {!r}".format(value))
    return total


def _chave(race):
    return int(race["season"]), int(race["round"])


class _Acervo:
    def __init__(self, raiz, archive, as_of):
        self.raiz, self.archive, self.as_of = Path(raiz), Path(archive), as_of
        self.fontes, self.eventos, self.calendario = {}, {}, {}
        self.linhas = {name: [] for name in SCHEMAS}
        self.lacunas, self.conflitos_identidade = [], []
        self.pagina_por_registro, self.resultados_por_piloto = {}, {}
        self.qual_por_piloto = {}

    def fonte(self, path, origem, meta=None, esperado=None, dependencias=()):
        path = Path(path)
        if path.is_symlink() or not path.is_file():
            raise ValueError("Fonte inexistente ou insegura: {}".format(path))
        digest = _sha(path)
        if esperado is not None and digest != esperado:
            raise ValueError("SHA-256 divergente: {}".format(path))
        fid = str(path.resolve())
        meta = meta or {}
        info = {
            "arquivo": fid,
            "sha256": digest,
            "origem": origem,
            "obtido_em_utc": meta.get("obtido_em_utc", "desconhecida"),
            "url": meta.get("url_real")
            or meta.get("url_consultada")
            or meta.get("url_solicitada"),
            "dependencias": list(dependencias),
        }
        if fid in self.fontes and self.fontes[fid]["sha256"] != digest:
            raise ValueError("Fonte mudou durante a preparação: " + fid)
        self.fontes[fid] = info
        return fid

    def comum(self, key, fid):
        event = self.eventos[key]
        return dict(
            zip(CHAVES, [*key, event["circuito_id"]]),
            fonte_id=fid,
            obtido_em_utc=self.fontes[fid]["obtido_em_utc"],
        )

    def registrar_paginas(self, pasta, sources):
        for source in sources:
            path = Path(pasta) / source["arquivo"]
            fid = self.fonte(path, "Jolpica-F1", source, source["sha256"])
            payload = _json(path)
            endpoint = source["endpoint"]
            field = {"classificacao": "QualifyingResults", "resultados": "Results"}.get(
                endpoint
            )
            for race in payload["MRData"]["RaceTable"]["Races"]:
                key = _chave(race)
                if field is None:
                    self.pagina_por_registro[(endpoint, *key, "")] = fid
                else:
                    for row in race[field]:
                        self.pagina_por_registro[
                            (endpoint, *key, row["Driver"]["driverId"])
                        ] = fid

    def admitir(self, calendarios, resultados, classificacoes):
        for race in calendarios:
            key = _chave(race)
            if key in self.calendario and self.calendario[key] != race:
                raise ValueError("Calendários canônicos conflitantes: {}".format(key))
            self.calendario[key] = race
        for race in resultados:
            key = _chave(race)
            calendar = self.calendario[key]
            if (race["date"], race["Circuit"]["circuitId"]) != (
                calendar["date"],
                calendar["Circuit"]["circuitId"],
            ):
                raise ValueError(
                    "Identidade de resultado diverge do calendário: {}".format(key)
                )
            timestamp = calendar["date"] + "T" + (calendar.get("time") or "23:59:59Z")
            when = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(
                timezone.utc
            )
            if when >= self.as_of or not race.get("Results"):
                continue
            location = calendar["Circuit"]["Location"]
            latitude, longitude = float(location["lat"]), float(location["long"])
            if (
                not math.isfinite(latitude)
                or not math.isfinite(longitude)
                or not -90 <= latitude <= 90
                or not -180 <= longitude <= 180
            ):
                raise ValueError("Coordenadas inválidas: {}".format(key))
            self.eventos[key] = {
                "temporada": key[0],
                "rodada": key[1],
                "circuito_id": calendar["Circuit"]["circuitId"],
                "corrida": calendar["raceName"],
                "data_corrida": calendar["date"],
                "hora_utc": calendar.get("time") or None,
                "latitude": latitude,
                "longitude": longitude,
                "localidade": location.get("locality"),
                "pais": location.get("country"),
                "sessoes_calendario": {
                    name: calendar[name] for name in SESSOES if name in calendar
                },
            }
            for row in race["Results"]:
                driver = row["Driver"]["driverId"]
                fid = self.pagina_por_registro[("resultados", *key, driver)]
                normalized = self.normalizar_resultado(key, row, fid)
                if (*key, driver) in self.resultados_por_piloto:
                    raise ValueError(
                        "Resultado canônico duplicado: {}".format((*key, driver))
                    )
                self.linhas["resultados.csv"].append(normalized)
                self.resultados_por_piloto[(*key, driver)] = normalized
        self.admitir_q(classificacoes)

    def normalizar_resultado(self, key, row, fid):
        return dict(
            self.comum(key, fid),
            piloto_id=row["Driver"]["driverId"],
            piloto=" ".join(
                row["Driver"].get(k, "") for k in ("givenName", "familyName")
            ).strip(),
            equipe_id=row["Constructor"]["constructorId"],
            numero=row.get("number"),
            posicao_final=row.get("position"),
            position_text=row.get("positionText"),
            pontos=row.get("points"),
            grid_resultado_auditoria=row.get("grid"),
            voltas=row.get("laps"),
            status=row.get("status"),
            tempo_original=row.get("Time", {}).get("time"),
            tempo_millis_original=row.get("Time", {}).get("millis"),
            melhor_volta=row.get("FastestLap", {}).get("lap"),
            melhor_tempo=row.get("FastestLap", {}).get("Time", {}).get("time"),
        )

    def admitir_q(self, classificacoes):
        for race in classificacoes:
            key = _chave(race)
            if key not in self.eventos:
                continue
            event = self.eventos[key]
            if (race["date"], race["Circuit"]["circuitId"]) != (
                event["data_corrida"],
                event["circuito_id"],
            ):
                raise ValueError(
                    "Identidade de classificação diverge do calendário: {}".format(key)
                )
            for row in race.get("QualifyingResults", []):
                driver = row["Driver"]["driverId"]
                record_key = (*key, driver)
                if record_key in self.qual_por_piloto:
                    continue
                fid = self.pagina_por_registro[("classificacao", *key, driver)]
                normalized = dict(
                    self.comum(key, fid),
                    piloto_id=driver,
                    piloto=" ".join(
                        row["Driver"].get(k, "") for k in ("givenName", "familyName")
                    ).strip(),
                    equipe_id=row["Constructor"]["constructorId"],
                    posicao_classificacao=row.get("position"),
                    q1_original=row.get("Q1"),
                    q2_original=row.get("Q2"),
                    q3_original=row.get("Q3"),
                )
                self.linhas["classificacao.csv"].append(normalized)
                self.qual_por_piloto[record_key] = normalized

    def historico(self):
        for year in ("2024", "2025"):
            pasta = self.raiz / "data/historico" / year
            data = carregar_temporada(year, raiz_dados=self.raiz / "data/historico")
            for name in ("manifesto.json", "verificacao.json"):
                self.fonte(pasta / name, "validação histórica Jolpica")
            self.registrar_paginas(pasta, data["proveniencia"])
            self.admitir(data["calendario"], data["resultados"], data["classificacao"])

    def operacional(self):
        pasta = self.raiz / "data/operacao_2026/snapshots"
        if not (pasta / SNAPSHOT_2026 / "indice.json").exists():
            self.lacunas.append(
                {
                    "temporada": 2026,
                    "tipo": "snapshot_canonico_ausente",
                    "snapshot": SNAPSHOT_2026,
                }
            )
            return
        index, pages = fontes.ler_snapshot(
            pasta, SNAPSHOT_2026, endpoints=("calendario", "resultados")
        )
        self.fonte(pasta / SNAPSHOT_2026 / "indice.json", "índice operacional Jolpica")
        self.registrar_paginas(
            pasta / SNAPSHOT_2026,
            [source for group in pages.values() for source, _ in group],
        )
        races = lambda ep: [
            race
            for _, payload in pages.get(ep, [])
            for race in payload["MRData"]["RaceTable"]["Races"]
        ]
        self.admitir(races("calendario"), races("resultados"), [])
        for sid in SNAPSHOTS_Q:
            if not (pasta / sid / "indice.json").exists():
                self.lacunas.append(
                    {"temporada": 2026, "tipo": "snapshot_q_ausente", "snapshot": sid}
                )
                continue
            _, qpages = fontes.ler_snapshot(pasta, sid, endpoints=("classificacao",))
            self.fonte(pasta / sid / "indice.json", "índice operacional classificação")
            self.registrar_paginas(
                pasta / sid, [source for source, _ in qpages.get("classificacao", [])]
            )
            self.admitir_q(
                [
                    race
                    for _, payload in qpages.get("classificacao", [])
                    for race in payload["MRData"]["RaceTable"]["Races"]
                ]
            )

    def complementar_archive(self):
        auditoria = self.raiz / AUDITORIA_ARCHIVE
        manifest = _json(auditoria)
        self.fonte(auditoria, "auditoria anterior do archive")
        expected = {x["arquivo"]: x["sha256"] for x in manifest["fontes"]}
        source_ids = {}

        def tabela(name):
            path = self.archive / (name + ".csv")
            if name not in source_ids:
                source_ids[name] = self.fonte(
                    path, "Archive local Ergast/Kaggle", esperado=expected[path.name]
                )
            with path.open(encoding="utf-8", newline="") as stream:
                for row in csv.DictReader(stream):
                    yield {k: _valor(v) for k, v in row.items()}

        drivers = {r["driverId"]: r for r in tabela("drivers")}
        constructors = {r["constructorId"]: r for r in tabela("constructors")}
        circuits = {r["circuitId"]: r for r in tabela("circuits")}
        status = {r["statusId"]: r["status"] for r in tabela("status")}
        races = {}
        for row in tabela("races"):
            key = int(row["year"]), int(row["round"])
            if key not in self.eventos:
                continue
            circuit = circuits[row["circuitId"]]["circuitRef"]
            event = self.eventos[key]
            if (circuit, row["date"]) != (event["circuito_id"], event["data_corrida"]):
                self.conflitos_identidade.append(
                    {
                        "tipo": "evento_archive",
                        "temporada": key[0],
                        "rodada": key[1],
                        "circuito_archive": circuit,
                        "data_archive": row["date"],
                    }
                )
                continue
            races[row["raceId"]] = key
        dimensions = [
            source_ids[n] for n in ("drivers", "constructors", "circuits", "races")
        ]

        def driver(row):
            return drivers[row["driverId"]]["driverRef"]

        def team(row, key, pilot):
            if row.get("constructorId"):
                return constructors[row["constructorId"]]["constructorRef"]
            return self.resultados_por_piloto.get((*key, pilot), {}).get("equipe_id")

        for table, output in (
            ("lap_times", "voltas_corrida.csv"),
            ("pit_stops", "pit_stops.csv"),
            ("sprint_results", "sprint_resultados.csv"),
            ("constructor_standings", "campeonato_equipes.csv"),
            ("driver_standings", "campeonato_pilotos.csv"),
            ("qualifying", "conflitos_classificacao.csv"),
        ):
            for row in tabela(table):
                key = races.get(row["raceId"])
                if key is None:
                    continue
                fid = source_ids[table]
                common = self.comum(key, fid)
                pilot = driver(row) if row.get("driverId") else None
                if table == "lap_times":
                    normalized = dict(
                        common,
                        piloto_id=pilot,
                        equipe_id=team(row, key, pilot),
                        volta=row["lap"],
                        posicao=row["position"],
                        tempo_original=row["time"],
                        tempo_segundos=_segundos(row["time"]),
                    )
                elif table == "pit_stops":
                    normalized = dict(
                        common,
                        piloto_id=pilot,
                        equipe_id=team(row, key, pilot),
                        parada=row["stop"],
                        volta=row["lap"],
                        hora_original=row["time"],
                        duracao_original=row["duration"],
                        duracao_segundos=_segundos(row["duration"]),
                    )
                elif table == "sprint_results":
                    normalized = dict(
                        common,
                        piloto_id=pilot,
                        piloto=drivers[row["driverId"]]["forename"]
                        + " "
                        + drivers[row["driverId"]]["surname"],
                        equipe_id=team(row, key, pilot),
                        numero=row["number"],
                        posicao_final=row["positionOrder"],
                        position_text=row["positionText"],
                        pontos=row["points"],
                        grid_resultado_auditoria=row["grid"],
                        voltas=row["laps"],
                        status=status.get(row.get("statusId")),
                        tempo_original=row["time"],
                        tempo_millis_original=row["milliseconds"],
                        melhor_volta=row.get("fastestLap"),
                        melhor_tempo=row.get("fastestLapTime"),
                    )
                elif table == "constructor_standings":
                    normalized = dict(
                        common,
                        equipe_id=team(row, key, None),
                        posicao=row["position"],
                        pontos=row["points"],
                        vitorias=row["wins"],
                    )
                elif table == "driver_standings":
                    normalized = dict(
                        common,
                        piloto_id=pilot,
                        equipes_publicadas=None,
                        posicao=row["position"],
                        pontos=row["points"],
                        vitorias=row["wins"],
                    )
                else:
                    canonical = self.qual_por_piloto.get((*key, pilot))
                    if canonical:
                        for original, field in (
                            ("position", "posicao_classificacao"),
                            ("q1", "q1_original"),
                            ("q2", "q2_original"),
                            ("q3", "q3_original"),
                        ):
                            if _valor(canonical.get(field)) != _valor(
                                row.get(original)
                            ):
                                self.linhas[output].append(
                                    dict(
                                        zip(
                                            CHAVES,
                                            [*key, self.eventos[key]["circuito_id"]],
                                        ),
                                        piloto_id=pilot,
                                        campo=field,
                                        valor_canonico=canonical.get(field),
                                        valor_archive=row.get(original),
                                        fonte_canonica=canonical["fonte_id"],
                                        fonte_archive=fid,
                                        decisao="preservar_canonico_sem_adjudicacao",
                                    )
                                )
                    continue
                self.linhas[output].append(normalized)
            self.fontes[source_ids[table]]["dependencias"] = dimensions + (
                [source_ids["status"]] if table == "sprint_results" else []
            )

    def complementar_austin(self):
        key = (2026, 18)
        path = self.raiz / AUSTIN
        if key not in self.eventos or not (path / "inventario.json").exists():
            return
        inv = _json(path / "inventario.json")
        if inv.get("estado") != "coleta_concluida" or inv.get("identidade") != {
            "temporada": 2026,
            "rodada": 18,
            "circuito_id": "americas",
            "data": self.eventos[key]["data_corrida"],
        }:
            raise ValueError(
                "Inventário pós-Austin incompleto ou identidade divergente."
            )
        self.fonte(path / "inventario.json", "inventário pós-corrida Austin")
        mapping = {
            "voltas": "voltas_corrida.csv",
            "pit_stops": "pit_stops.csv",
            "classificacao_pilotos": "campeonato_pilotos.csv",
            "classificacao_equipes": "campeonato_equipes.csv",
        }
        for endpoint, output in mapping.items():
            sources = sorted(
                (s for s in inv["fontes"] if s["endpoint"] == endpoint),
                key=lambda s: s["parametros"]["offset"],
            )
            offset, total = 0, None
            for source in sources:
                fid = self.fonte(
                    path / source["arquivo"],
                    "Jolpica-F1 pós-Austin",
                    source,
                    source["sha256"],
                )
                payload = _json(path / source["arquivo"])["MRData"]
                count_total, page_offset, limit = (
                    int(payload["total"]),
                    int(payload["offset"]),
                    int(payload["limit"]),
                )
                if (
                    limit != 100
                    or page_offset != offset
                    or (total is not None and total != count_total)
                ):
                    raise ValueError("Paginação pós-Austin divergente.")
                total = count_total
                if endpoint in ("voltas", "pit_stops"):
                    records = []
                    for race in payload["RaceTable"]["Races"]:
                        if (
                            _chave(race),
                            race["Circuit"]["circuitId"],
                            race["date"],
                        ) != (key, "americas", self.eventos[key]["data_corrida"]):
                            raise ValueError("Identidade de raw pós-Austin divergente.")
                        if endpoint == "voltas":
                            for lap in race["Laps"]:
                                records.extend(
                                    dict(r, lap=lap["number"]) for r in lap["Timings"]
                                )
                        else:
                            records.extend(race["PitStops"])
                else:
                    field = (
                        "DriverStandings"
                        if endpoint == "classificacao_pilotos"
                        else "ConstructorStandings"
                    )
                    records = []
                    for standing in payload["StandingsTable"]["StandingsLists"]:
                        if (int(standing["season"]), int(standing["round"])) != key:
                            raise ValueError(
                                "Identidade de campeonato pós-Austin divergente."
                            )
                        records.extend(standing[field])
                if len(records) != min(limit, total - offset):
                    raise ValueError("Página pós-Austin incompleta.")
                for row in records:
                    common = self.comum(key, fid)
                    if endpoint == "voltas":
                        pilot = row["driverId"]
                        normalized = dict(
                            common,
                            piloto_id=pilot,
                            equipe_id=self.resultados_por_piloto.get(
                                (*key, pilot), {}
                            ).get("equipe_id"),
                            volta=row["lap"],
                            posicao=row["position"],
                            tempo_original=row["time"],
                            tempo_segundos=_segundos(row["time"]),
                        )
                    elif endpoint == "pit_stops":
                        pilot = row["driverId"]
                        normalized = dict(
                            common,
                            piloto_id=pilot,
                            equipe_id=self.resultados_por_piloto.get(
                                (*key, pilot), {}
                            ).get("equipe_id"),
                            parada=row["stop"],
                            volta=row["lap"],
                            hora_original=row["time"],
                            duracao_original=row["duration"],
                            duracao_segundos=_segundos(row["duration"]),
                        )
                    elif endpoint == "classificacao_pilotos":
                        normalized = dict(
                            common,
                            piloto_id=row["Driver"]["driverId"],
                            equipes_publicadas=";".join(
                                c["constructorId"] for c in row["Constructors"]
                            ),
                            posicao=row["position"],
                            pontos=row["points"],
                            vitorias=row["wins"],
                        )
                    else:
                        normalized = dict(
                            common,
                            equipe_id=row["Constructor"]["constructorId"],
                            posicao=row["position"],
                            pontos=row["points"],
                            vitorias=row["wins"],
                        )
                    self.linhas[output].append(normalized)
                offset += len(records)
            if (
                total is None
                or offset != total
                or inv["endpoints"][endpoint]["total"] != total
            ):
                raise ValueError("Endpoint pós-Austin incompleto: " + endpoint)

    def validar(self):
        keys = {
            "resultados.csv": ["piloto_id"],
            "classificacao.csv": ["piloto_id"],
            "voltas_corrida.csv": ["piloto_id", "volta"],
            "pit_stops.csv": ["piloto_id", "parada"],
            "sprint_resultados.csv": ["piloto_id"],
            "campeonato_equipes.csv": ["equipe_id"],
            "campeonato_pilotos.csv": ["piloto_id"],
        }
        for name, suffix in keys.items():
            seen = set()
            for row in self.linhas[name]:
                key = tuple(str(row[k]) for k in CHAVES + suffix)
                if key in seen:
                    raise ValueError("Chave duplicada em {}: {}".format(name, key))
                seen.add(key)
        self.cobertura = []
        for key in sorted(self.eventos):
            grupos = {
                name: [
                    r for r in self.linhas[name] if (r["temporada"], r["rodada"]) == key
                ]
                for name in keys
            }
            participantes = {r["piloto_id"] for r in grupos["resultados.csv"]}
            classificados = {r["piloto_id"] for r in grupos["classificacao.csv"]}
            pilotos_voltas = {r["piloto_id"] for r in grupos["voltas_corrida.csv"]}
            pilotos_paradas = {r["piloto_id"] for r in grupos["pit_stops.csv"]}
            self.cobertura.append(
                {
                    "temporada": key[0],
                    "rodada": key[1],
                    "registros": {name: len(rows) for name, rows in grupos.items()},
                    "pilotos_resultado_sem_classificacao": sorted(
                        participantes - classificados
                    ),
                    "pilotos_classificacao_sem_resultado": sorted(
                        classificados - participantes
                    ),
                    "pilotos_resultado_sem_voltas": sorted(
                        participantes - pilotos_voltas
                    ),
                    "pilotos_sem_parada_observada": sorted(
                        participantes - pilotos_paradas
                    ),
                }
            )
            for tipo, pilotos in (
                ("resultado_sem_classificacao", participantes - classificados),
                ("classificacao_sem_resultado", classificados - participantes),
                ("resultado_sem_voltas", participantes - pilotos_voltas),
            ):
                if pilotos:
                    self.lacunas.append(
                        {
                            "temporada": key[0],
                            "rodada": key[1],
                            "tipo": tipo,
                            "pilotos": sorted(pilotos),
                            "motivo": "ausência preservada; não foi imputado resultado ou tempo",
                        }
                    )
            for name in (
                "classificacao.csv",
                "voltas_corrida.csv",
                "pit_stops.csv",
                "campeonato_equipes.csv",
                "campeonato_pilotos.csv",
            ):
                if not grupos[name]:
                    self.lacunas.append(
                        {
                            "temporada": key[0],
                            "rodada": key[1],
                            "tipo": name,
                            "motivo": "sem registros no complemento local; ausência não equivale a zero",
                        }
                    )
        for fid, source in self.fontes.items():
            if _sha(source["arquivo"]) != source["sha256"]:
                raise ValueError("Fonte mudou durante preparação: " + fid)


def proveniencia_archive(raiz, archive):
    desconhecida = {
        "obtido_em_utc": "desconhecida",
        "urls_documentadas_em_conflito": [
            "https://www.kaggle.com/datasets/jtrotman/formula-1-race-data/data",
            "https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020",
        ],
        "decisao": "Não atribuir origem sem prova correspondente aos bytes.",
    }
    prova = (
        Path(raiz)
        / "data/acervo_historico/resolucao-20261029/archive_proveniencia_resolvida.json"
    )
    if not prova.is_file():
        return desconhecida
    dados = json.loads(prova.read_text())
    if dados.get("schema") != "proveniencia-archive-v1":
        raise ValueError("Schema da prova de origem desconhecido")
    for nome, digest in dados["arquivos_sha256"].items():
        if Path(nome).name != nome:
            raise ValueError("Arquivo inválido na prova de origem")
        path = Path(archive) / nome
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            return dict(
                desconhecida,
                decisao="Prova existente não corresponde a estes bytes; não herdar sua origem.",
            )
    return dict(
        dados,
        prova_sha256=hashlib.sha256(prova.read_bytes()).hexdigest(),
        decisao="Origem identificada por ZIP/WhereFroms e hashes; aquisição UTC não inferida.",
    )


def preparar_local(raiz: Path, archive: Path, destino: Path, as_of: datetime) -> dict:
    """Grava destino/local uma única vez; retorna eventos e inventário completos.

    as_of precisa conter fuso. Saídas são contexto retrospectivo, não novas
    entradas, previsões ou evidência de disponibilidade histórica no corte v1.
    """
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of precisa de fuso horário explícito.")
    destination = Path(destino) / "local"
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(
            "Destino local existente foi preservado: {}".format(destination)
        )
    data = _Acervo(Path(raiz), Path(archive), as_of.astimezone(timezone.utc))
    data.historico()
    data.operacional()
    data.complementar_archive()
    data.complementar_austin()
    data.validar()
    eventos = [data.eventos[key] for key in sorted(data.eventos)]
    serialized = {}
    for name, fields in SCHEMAS.items():
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(
            stream, fields, lineterminator="\n", extrasaction="raise"
        )
        writer.writeheader()
        writer.writerows(data.linhas[name])
        serialized[name] = stream.getvalue().encode("utf-8")
    serialized["eventos.json"] = (
        json.dumps(eventos, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    counts = {
        name: dict(Counter(str(r["temporada"]) for r in rows))
        for name, rows in data.linhas.items()
    }
    inventory = {
        "schema": "pitwall-acervo-local-v1",
        "as_of_utc": data.as_of.isoformat().replace("+00:00", "Z"),
        "uso": "contexto_descritivo_retrospectivo_pos_corrida",
        "eventos": len(eventos),
        "fontes": data.fontes,
        "contagens": counts,
        "lacunas": data.lacunas,
        "cobertura_por_gp": data.cobertura,
        "conflitos_identidade": data.conflitos_identidade,
        "proveniencia_archive": proveniencia_archive(raiz, archive),
        "limites": [
            "Completude por GP não certifica cobertura por piloto.",
            "Ausência de pit stop não significa automaticamente zero paradas.",
            "Não há clima, composto ou idade de pneus no complemento archive.",
            "Timestamps desconhecidos não foram reconstruídos.",
            "Classificação canônica preservada, conflitos archive não adjudicados.",
        ],
        "arquivos_sha256": {
            name: hashlib.sha256(raw).hexdigest() for name, raw in serialized.items()
        },
    }
    destination.mkdir(parents=True, exist_ok=False)
    for name, raw in serialized.items():
        with (destination / name).open("xb") as stream:
            stream.write(raw)
    with (destination / "inventario_local.json").open("x", encoding="utf-8") as stream:
        json.dump(inventory, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    return {
        "eventos": eventos,
        "inventario": inventory,
        "pasta_local": str(destination),
    }
