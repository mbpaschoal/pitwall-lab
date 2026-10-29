"""Normalização offline do acervo descritivo, sem alterar dados ou previsões v1.

As identidades OpenF1 permanecem nativas. Uma associação canônica usa apenas o
número literal do piloto no resultado Jolpica do mesmo GP, nunca nomes parecidos.
Estratégias são sequências observadas de stints, sem interpretação causal.
"""

import csv
import hashlib
import io
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse


CHAVE = ("temporada", "rodada", "circuito_id")
IDENTIDADE = (
    "driver_number",
    "piloto_id",
    "equipe_id",
    "identidade_piloto",
    "team_name_openf1",
    "fonte_identidade_canonica",
)
PROVENIENCIA = ("provider", "fonte_arquivo", "fonte_sha256", "obtido_em_utc")
COMUM = CHAVE + ("meeting_key", "session_key", "session_name", "session_type")
SCHEMAS = {
    "sessoes": COMUM
    + (
        "date_start",
        "date_end",
        "data_corrida_calendario",
        "gmt_offset_openf1",
        "location_openf1",
        "metodo_mapeamento",
    )
    + PROVENIENCIA,
    "pilotos_sessoes": COMUM
    + IDENTIDADE
    + ("full_name", "name_acronym", "broadcast_name")
    + PROVENIENCIA,
    "tempos_sessoes": COMUM
    + IDENTIDADE
    + (
        "position",
        "duration_original_json",
        "gap_to_leader_original_json",
        "number_of_laps",
        "dnf",
        "dns",
        "dsq",
    )
    + PROVENIENCIA,
    "laps_sessoes": COMUM
    + IDENTIDADE
    + (
        "lap_number",
        "date_start",
        "lap_duration",
        "duration_sector_1",
        "duration_sector_2",
        "duration_sector_3",
        "is_pit_out_lap",
        "segments_sector_1_json",
        "segments_sector_2_json",
        "segments_sector_3_json",
    )
    + PROVENIENCIA,
    "stints": COMUM
    + IDENTIDADE
    + (
        "stint_number",
        "lap_start",
        "lap_end",
        "compound",
        "tyre_age_at_start",
        "limites_voltas_comparaveis",
        "qualidade_limites_json",
    )
    + PROVENIENCIA,
    "paradas_openf1": COMUM
    + IDENTIDADE
    + ("date", "lap_number", "pit_duration", "stop_duration", "lane_duration")
    + PROVENIENCIA,
    "clima_pista": COMUM
    + (
        "date",
        "air_temperature",
        "track_temperature",
        "humidity",
        "pressure",
        "rainfall",
        "wind_direction",
        "wind_speed",
    )
    + PROVENIENCIA,
    "clima_open_meteo": CHAVE
    + (
        "date_utc",
        "latitude_fonte",
        "longitude_fonte",
        "elevation_fonte",
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "rain",
        "weather_code",
        "cloud_cover",
        "wind_speed_10m",
        "wind_direction_10m",
        "surface_pressure",
        "unidades_json",
        "origin",
        "model",
    )
    + PROVENIENCIA,
    "comparativo_equipes": CHAVE
    + (
        "tipo_sessao",
        "equipe_id",
        "pilotos_id_json",
        "n_resultados",
        "n_pontos_conhecidos",
        "pontos_soma_observada",
        "pontos_completos",
        "n_posicoes_conhecidas",
        "posicao_media_observada",
        "melhor_posicao_observada",
        "fontes_id_json",
        "escopo",
    ),
    "estrategias_pneus": COMUM
    + IDENTIDADE
    + (
        "n_stints_observados",
        "compostos_observados_json",
        "sequencia_stints_json",
        "tem_lacunas_entre_stints",
        "n_stints_limites_incompletos",
        "limites_voltas_comparaveis",
        "qualidade_limites_json",
        "interpretacao",
    ),
    "cobertura": CHAVE
    + (
        "tipo",
        "provider",
        "estado",
        "n_registros",
        "n_sessoes_observadas",
        "n_sessoes_catalogadas",
        "n_horas_observadas",
        "n_horas_esperadas",
        "n_horas_ausentes",
        "n_valores_nulos",
        "n_valores_invalidos",
        "n_campos_unidade_invalida",
        "n_horas_sessoes_ausentes",
        "motivo",
        "fontes_json",
    ),
}
ENDPOINTS = {
    "drivers": "pilotos_openf1",
    "session_result": "tempos_sessoes",
    "laps": "laps_sessoes",
    "stints": "stints",
    "pit": "paradas_openf1",
    "weather": "clima_pista",
}
LOCAIS = {
    "resultados.csv": "resultado_corrida",
    "classificacao.csv": "classificacao_principal",
    "voltas_corrida.csv": "voltas_corrida",
    "pit_stops.csv": "paradas_jolpica",
    "sprint_resultados.csv": "sprint_resultados",
}
METEO_UNIDADES = {
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "precipitation": "mm",
    "rain": "mm",
    "wind_speed_10m": "m/s",
    "wind_direction_10m": "°",
    "surface_pressure": "hPa",
}


def _json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _inteiro(value, rotulo, minimo=1):
    if isinstance(value, bool) or value is None:
        raise ValueError("{} inválido".format(rotulo))
    try:
        numero = int(value)
    except (ValueError, TypeError):
        raise ValueError("{} inválido".format(rotulo))
    if str(numero) != str(value).strip() or numero < minimo:
        raise ValueError("{} inválido".format(rotulo))
    return numero


def _numero(value, rotulo):
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError("{} inválido".format(rotulo))
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError("{} inválido".format(rotulo))
    if not math.isfinite(number):
        raise ValueError("{} não finito".format(rotulo))
    return number


def _utc(value, rotulo):
    if not isinstance(value, str):
        raise ValueError("{} UTC ausente".format(rotulo))
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("{} UTC inválido".format(rotulo))
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("{} precisa declarar UTC".format(rotulo))
    return parsed


def _path(raiz, relativo):
    if not isinstance(relativo, str):
        raise ValueError("arquivo de fonte ausente")
    rel = Path(relativo)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("arquivo fora do acervo")
    atual = raiz
    for parte in rel.parts:
        atual = atual / parte
        if atual.is_symlink():
            raise ValueError("symlink na fonte")
    if not atual.is_file():
        raise ValueError("arquivo de fonte ausente: {}".format(relativo))
    return atual


def _key(row):
    circuito = row.get("circuito_id")
    if not isinstance(circuito, str) or not circuito.strip():
        raise ValueError("circuito_id ausente")
    return (
        _inteiro(row.get("temporada"), "temporada"),
        _inteiro(row.get("rodada"), "rodada"),
        circuito,
    )


def _dictkey(key):
    return dict(zip(CHAVE, key))


def _unique(mapping, key, value, rotulo):
    if key in mapping:
        raise ValueError("{} duplicado: {}".format(rotulo, key))
    mapping[key] = value


def _proveniencia(fonte):
    return {
        "provider": fonte["provider"],
        "fonte_arquivo": fonte["arquivo"],
        "fonte_sha256": fonte["sha256"],
        "obtido_em_utc": fonte["obtido_em_utc"],
    }


def _eventos(raiz):
    arquivo = raiz / "eventos.json"
    if not arquivo.exists():
        arquivo = raiz / "local" / "eventos.json"
    raw = json.loads(arquivo.read_text(encoding="utf-8"))
    eventos = raw.get("eventos") if isinstance(raw, dict) else raw
    if not isinstance(eventos, list) or not eventos:
        raise ValueError("catálogo de eventos vazio ou inválido")
    index = {}
    for evento in eventos:
        if not isinstance(evento, dict):
            raise ValueError("evento inválido")
        _unique(index, _key(evento), evento, "evento")
    return index


def _fontes(raiz):
    caminho = raiz / "coleta_online.json"
    if not caminho.exists():
        return []
    manifesto = json.loads(caminho.read_text(encoding="utf-8"))
    fontes = manifesto.get("fontes")
    if not isinstance(fontes, list):
        raise ValueError("manifesto online sem fontes")
    arquivos = set()
    declaracoes = set()
    saida = []
    for fonte in fontes:
        if (
            not isinstance(fonte, dict)
            or not fonte.get("provider")
            or not fonte.get("endpoint")
        ):
            raise ValueError("declaração de fonte incompleta")
        if fonte.get("status") != 200:
            saida.append((fonte, None))
            continue
        for campo in ("url", "obtido_em_utc", "sha256", "arquivo", "temporada"):
            if fonte.get(campo) in (None, ""):
                raise ValueError("fonte 200 incompleta: {}".format(campo))
        _utc(fonte["obtido_em_utc"], "obtenção")
        if not str(fonte["url"]).startswith(("https://", "http://")):
            raise ValueError("URL de fonte inválida")
        assinatura = (
            fonte["provider"],
            fonte["endpoint"],
            fonte["temporada"],
            fonte.get("rodada"),
            fonte.get("circuito_id"),
            fonte.get("meeting_key"),
            fonte["url"],
        )
        ativa = fonte.get("normalizar") is not False
        if (ativa and assinatura in declaracoes) or fonte["arquivo"] in arquivos:
            raise ValueError("fonte duplicada no manifesto")
        if ativa:
            declaracoes.add(assinatura)
        arquivos.add(fonte["arquivo"])
        dados = _path(raiz, fonte["arquivo"]).read_bytes()
        if hashlib.sha256(dados).hexdigest() != fonte["sha256"]:
            raise ValueError("hash divergente: {}".format(fonte["arquivo"]))
        if fonte.get("normalizar") is False:
            saida.append((fonte, None))
            continue
        raw = json.loads(
            dados.decode("utf-8"),
            parse_constant=lambda x: (_ for _ in ()).throw(
                ValueError("JSON não finito")
            ),
        )
        saida.append((fonte, raw))
    return saida


def _locais(raiz, eventos):
    tabelas, identidades = {}, {}
    for nome in LOCAIS:
        arquivo = raiz / "local" / nome
        linhas = []
        if arquivo.exists():
            with arquivo.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or not set(CHAVE).issubset(reader.fieldnames):
                    raise ValueError("schema local incompleto: {}".format(nome))
                linhas = list(reader)
        visto = {}
        for linha in linhas:
            key = _key(linha)
            if key not in eventos:
                raise ValueError("CSV local contém GP fora do catálogo")
            if nome in ("resultados.csv", "classificacao.csv", "sprint_resultados.csv"):
                piloto = linha.get("piloto_id")
                if not piloto:
                    raise ValueError("piloto_id local ausente")
                _unique(visto, key + (piloto,), linha, "piloto local")
            if nome == "resultados.csv" and linha.get("numero") not in (None, ""):
                numero = _inteiro(linha["numero"], "numero do piloto")
                _unique(
                    identidades,
                    key + (numero,),
                    {
                        "piloto_id": linha["piloto_id"],
                        "equipe_id": linha.get("equipe_id", ""),
                        "fonte_id": linha.get("fonte_id", ""),
                    },
                    "número de piloto local",
                )
        tabelas[nome] = linhas
    return tabelas, identidades


def _catalogo(raiz, fontes, eventos):
    encontros, sessoes = {}, {}
    excluidos = defaultdict(int)
    mapeamento = {}
    metadados_mapeamento = {}
    caminho = raiz / "mapeamento_sessoes.json"
    if caminho.exists():
        registros = json.loads(caminho.read_text(encoding="utf-8"))
        if not isinstance(registros, list):
            raise ValueError("mapeamento_sessoes precisa ser lista")
        for row in registros:
            key = _key(row)
            if key not in eventos:
                raise ValueError("mapeamento de sessão fora do catálogo")
            skey = _inteiro(row.get("session_key"), "session_key do mapeamento")
            meeting = _inteiro(row.get("meeting_key"), "meeting_key do mapeamento")
            _unique(mapeamento, skey, (key, meeting), "mapeamento de sessão")
            metadados_mapeamento[skey] = row
            encontro = (key[0], meeting)
            if encontro in encontros and encontros[encontro] != key:
                raise ValueError("meeting_key associado a dois GPs")
            encontros[encontro] = key
    for key, evento in eventos.items():
        if evento.get("meeting_key") is not None:
            encontro = (key[0], _inteiro(evento["meeting_key"], "meeting_key"))
            if encontro in encontros and encontros[encontro] != key:
                raise ValueError("meeting_key associado a dois GPs")
            encontros[encontro] = key
    for fonte, raw in fontes:
        if fonte["provider"] != "openf1" or not fonte.get("rodada"):
            continue
        key = _key(fonte)
        if key not in eventos:
            raise ValueError("fonte OpenF1 de GP fora do catálogo")
        if fonte.get("meeting_key") is not None:
            encontro = (key[0], _inteiro(fonte["meeting_key"], "meeting_key"))
            if encontro in encontros and encontros[encontro] != key:
                raise ValueError("meeting_key associado a dois GPs")
            encontros[encontro] = key
    for fonte, raw in fontes:
        if (
            fonte["provider"] != "openf1"
            or fonte["endpoint"] != "sessions"
            or raw is None
        ):
            continue
        if not isinstance(raw, list):
            raise ValueError("sessions precisa ser lista")
        ano = _inteiro(fonte.get("temporada"), "temporada da fonte")
        for row in raw:
            encontro = (ano, _inteiro(row.get("meeting_key"), "meeting_key"))
            sessao = _inteiro(row.get("session_key"), "session_key")
            if mapeamento:
                if sessao not in mapeamento:
                    excluidos[fonte["arquivo"]] += 1
                    continue
                key, meeting = mapeamento[sessao]
                if key[0] != ano or meeting != encontro[1]:
                    raise ValueError("mapeamento e catálogo de sessão conflitantes")
            elif encontro not in encontros:
                excluidos[fonte["arquivo"]] += 1
                continue
            else:
                key = encontros[encontro]
            if row.get("year") is not None and _inteiro(row["year"], "year") != ano:
                raise ValueError("ano da sessão conflitante")
            inicio, fim = _utc(row.get("date_start"), "início da sessão"), _utc(
                row.get("date_end"), "fim da sessão"
            )
            if fim < inicio:
                raise ValueError("fim anterior ao início da sessão")
            if not row.get("session_name") or not row.get("session_type"):
                raise ValueError("nome/tipo de sessão ausente")
            base = dict(
                _dictkey(key),
                meeting_key=encontro[1],
                session_key=sessao,
                session_name=row["session_name"],
                session_type=row["session_type"],
                date_start=row["date_start"],
                date_end=row["date_end"],
                data_corrida_calendario=eventos[key].get("data_corrida"),
                gmt_offset_openf1=row.get("gmt_offset"),
                location_openf1=row.get("location"),
                metodo_mapeamento=(
                    metadados_mapeamento.get(sessao, {}).get("criterio_identidade")
                    or metadados_mapeamento.get(sessao, {}).get("metodo_mapeamento")
                    or metadados_mapeamento.get(sessao, {}).get("metodo")
                ),
                **_proveniencia(fonte),
            )
            _unique(sessoes, sessao, base, "sessão")
    anos_catalogados = {
        int(fonte["temporada"])
        for fonte, raw in fontes
        if fonte["provider"] == "openf1"
        and fonte["endpoint"] == "sessions"
        and raw is not None
    }
    faltantes = {
        skey
        for skey, (key, _) in mapeamento.items()
        if key[0] in anos_catalogados and skey not in sessoes
    }
    if faltantes:
        raise ValueError(
            "catálogo de sessões incompleto para o mapeamento: {}".format(
                sorted(faltantes)
            )
        )
    return sessoes, dict(excluidos)


def _normalizar_openf1(
    fontes, eventos, sessoes, identidades, tabelas, duplicatas_identicas=None
):
    pilotos, vistos = {}, defaultdict(dict)
    cobertura_fontes = defaultdict(list)
    excluidos = defaultdict(int)
    # Pilotos primeiro: a ordem de fontes no manifesto não determina a identidade.
    ordenadas = sorted(fontes, key=lambda item: item[0]["endpoint"] != "drivers")
    for fonte, raw in ordenadas:
        if fonte["provider"] != "openf1" or fonte["endpoint"] not in ENDPOINTS:
            continue
        endpoint = fonte["endpoint"]
        gp_fonte = _key(fonte) if fonte.get("rodada") is not None else None
        if gp_fonte is not None and gp_fonte not in eventos:
            raise ValueError("fonte OpenF1 fora dos eventos")
        ano = _inteiro(fonte.get("temporada"), "temporada da fonte")
        for event_key in eventos:
            aplicavel = event_key == gp_fonte if gp_fonte else event_key[0] == ano
            if aplicavel:
                cobertura_fontes[(event_key, ENDPOINTS[endpoint], "openf1")].append(
                    fonte
                )
        if raw is None:
            continue
        if not isinstance(raw, list):
            raise ValueError("{} precisa ser lista".format(endpoint))
        meeting = (
            _inteiro(fonte["meeting_key"], "meeting_key da fonte")
            if fonte.get("meeting_key") is not None
            else None
        )
        for row in raw:
            if not isinstance(row, dict):
                raise ValueError("linha OpenF1 inválida")
            skey = _inteiro(row.get("session_key"), "session_key")
            if skey not in sessoes:
                if gp_fonte:
                    raise ValueError("sessão sem catálogo validado")
                excluidos[fonte["arquivo"]] += 1
                continue
            sessao = sessoes[skey]
            key = _key(sessao)
            if (
                key[0] != ano
                or (gp_fonte is not None and key != gp_fonte)
                or (meeting is not None and sessao["meeting_key"] != meeting)
            ):
                raise ValueError("identidade de GP/sessão conflitante")
            if (
                row.get("meeting_key") is not None
                and _inteiro(row["meeting_key"], "meeting_key") != sessao["meeting_key"]
            ):
                raise ValueError("meeting_key conflitante no raw")
            base = {campo: sessao[campo] for campo in COMUM}
            base.update(_proveniencia(fonte))
            if endpoint == "weather":
                date = row.get("date")
                _utc(date, "data clima")
                chave_clima = (skey, date)
                if (
                    chave_clima in vistos[endpoint]
                    and vistos[endpoint][chave_clima] == row
                ):
                    # A resposta integral continua preservada e hashada. Somente
                    # cópias iguais de todos os campos não viram novas medições.
                    if duplicatas_identicas is not None:
                        duplicatas_identicas[fonte["arquivo"]] += 1
                    continue
                _unique(vistos[endpoint], chave_clima, row, "clima")
                base.update(
                    {
                        campo: row.get(campo)
                        for campo in SCHEMAS["clima_pista"]
                        if campo not in base
                    }
                )
                tabelas["clima_pista"].append(base)
                continue
            numero = _inteiro(row.get("driver_number"), "driver_number")
            pid = (skey, numero)
            cadastro = row if endpoint == "drivers" else pilotos.get(pid, {})
            canonico = identidades.get(key + (numero,), {})
            base.update(
                driver_number=numero,
                piloto_id=canonico.get("piloto_id", ""),
                equipe_id=canonico.get("equipe_id", ""),
                identidade_piloto=(
                    "jolpica:{}:{}:{}".format(key[0], key[1], canonico["piloto_id"])
                    if canonico
                    else "openf1:{}:{}".format(skey, numero)
                ),
                team_name_openf1=cadastro.get("team_name"),
                fonte_identidade_canonica=canonico.get("fonte_id", ""),
            )
            if endpoint == "drivers":
                _unique(pilotos, pid, row, "piloto OpenF1")
                base.update(
                    {
                        campo: row.get(campo)
                        for campo in ("full_name", "name_acronym", "broadcast_name")
                    }
                )
                tabelas["pilotos_sessoes"].append(base)
                continue
            tipo = ENDPOINTS[endpoint]
            if endpoint == "session_result":
                _unique(vistos[endpoint], pid, row, "resultado de sessão")
                for campo in ("position", "number_of_laps", "dnf", "dns", "dsq"):
                    base[campo] = row.get(campo)
                base["duration_original_json"] = _json(row.get("duration"))
                base["gap_to_leader_original_json"] = _json(row.get("gap_to_leader"))
            elif endpoint == "laps":
                lap = _inteiro(row.get("lap_number"), "lap_number")
                _unique(vistos[endpoint], pid + (lap,), row, "volta")
                for campo in SCHEMAS[tipo]:
                    if campo not in base and not campo.endswith("_json"):
                        base[campo] = row.get(campo)
                for setor in (1, 2, 3):
                    campo = "segments_sector_{}".format(setor)
                    base[campo + "_json"] = _json(row.get(campo))
            elif endpoint == "stints":
                stint = _inteiro(row.get("stint_number"), "stint_number")
                inicio = (
                    _inteiro(row["lap_start"], "lap_start", minimo=0)
                    if row.get("lap_start") is not None
                    else None
                )
                fim = (
                    _inteiro(row["lap_end"], "lap_end", minimo=0)
                    if row.get("lap_end") is not None
                    else None
                )
                qualidade = []
                for campo, valor in (("lap_start", inicio), ("lap_end", fim)):
                    if valor is None:
                        qualidade.append(campo + "_ausente")
                    elif valor == 0:
                        qualidade.append(campo + "_zero_na_fonte")
                if inicio not in (None, 0) and fim not in (None, 0) and fim < inicio:
                    qualidade.append("lap_end_anterior_lap_start_na_fonte")
                _unique(vistos[endpoint], pid + (stint,), row, "stint")
                base.update(
                    stint_number=stint,
                    lap_start=inicio,
                    lap_end=fim,
                    compound=row.get("compound"),
                    tyre_age_at_start=row.get("tyre_age_at_start"),
                    limites_voltas_comparaveis=not qualidade,
                    qualidade_limites_json=_json(qualidade),
                )
            elif endpoint == "pit":
                date = row.get("date")
                _utc(date, "data parada")
                _unique(vistos[endpoint], pid + (date,), row, "parada")
                for campo in (
                    "date",
                    "lap_number",
                    "pit_duration",
                    "stop_duration",
                    "lane_duration",
                ):
                    base[campo] = row.get(campo)
            tabelas[tipo].append(base)
    return pilotos, cobertura_fontes, dict(excluidos)


def _meteo(fontes, eventos, tabelas, cobertura_fontes):
    vistos = {}
    for fonte, raw in fontes:
        if fonte["provider"] not in ("open-meteo", "open_meteo"):
            continue
        key = _key(fonte)
        if key not in eventos:
            raise ValueError("fonte meteorológica fora do catálogo")
        cobertura_fontes[(key, "clima_open_meteo", "open-meteo")].append(fonte)
        if raw is None:
            continue
        if not isinstance(raw, dict) or not isinstance(raw.get("hourly"), dict):
            raise ValueError("fonte meteorológica incompleta: hourly")
        if raw.get("utc_offset_seconds") != 0 or raw.get("timezone") not in (
            "GMT",
            "UTC",
            "Etc/UTC",
            "Etc/GMT",
        ):
            raise ValueError("horas meteorológicas precisam estar em UTC")
        hourly, unidades = raw["hourly"], raw.get("hourly_units")
        times = hourly.get("time")
        if not isinstance(times, list) or not isinstance(unidades, dict):
            raise ValueError("fonte meteorológica sem horas/unidades")
        for campo, valores in hourly.items():
            if not isinstance(valores, list) or len(valores) != len(times):
                raise ValueError("array meteorológico incompleto: {}".format(campo))
        latitude = _numero(raw.get("latitude"), "latitude")
        longitude = _numero(raw.get("longitude"), "longitude")
        if latitude is None or longitude is None:
            raise ValueError("coordenadas meteorológicas ausentes")
        for i, date in enumerate(times):
            # A API declara timezone UTC e retorna datas ISO sem sufixo.
            date_utc = (
                date
                if isinstance(date, str)
                and (date.endswith("Z") or date.endswith("+00:00"))
                else str(date) + "Z"
            )
            instante = _utc(date_utc, "hora meteorológica")
            if (
                fonte.get("start_date")
                and instante.date().isoformat() < fonte["start_date"]
            ):
                continue
            if (
                fonte.get("end_date")
                and instante.date().isoformat() > fonte["end_date"]
            ):
                continue
            _unique(vistos, key + (instante,), date, "hora meteorológica")
            row = dict(
                _dictkey(key),
                date_utc=date_utc,
                latitude_fonte=latitude,
                longitude_fonte=longitude,
                elevation_fonte=raw.get("elevation"),
                unidades_json=_json(unidades),
                origin=fonte.get("origin"),
                model=fonte.get("model"),
                **_proveniencia(fonte),
            )
            for campo in SCHEMAS["clima_open_meteo"]:
                if campo not in row:
                    row[campo] = hourly[campo][i] if campo in hourly else None
            tabelas["clima_open_meteo"].append(row)


def _qualidade_meteo(rows, refs, sessoes=()):
    """Cobertura da janela e dos campos solicitados, sem tratar null como zero."""
    esperadas = set()
    sem_janela, fonte_incompleta = [], []
    campos_por_fonte, unidades_invalidas = {}, set()
    for fonte in refs:
        arquivo = fonte.get("arquivo")
        consulta = parse_qs(urlparse(fonte.get("url", "")).query)
        campos = tuple(
            c for lote in consulta.get("hourly", []) for c in lote.split(",") if c
        )
        campos_por_fonte[arquivo] = campos or tuple(METEO_UNIDADES)
        if fonte.get("status") != 200:
            continue
        inicio, fim = fonte.get("start_date"), fonte.get("end_date")
        try:
            if not (
                isinstance(inicio, str)
                and isinstance(fim, str)
                and len(inicio) == len(fim) == 10
            ):
                raise ValueError
            inicio, fim = datetime.fromisoformat(inicio), datetime.fromisoformat(fim)
            if fim < inicio:
                raise ValueError
        except (TypeError, ValueError):
            sem_janela.append(arquivo)
        else:
            hora = inicio.replace(tzinfo=timezone.utc)
            limite = fim.replace(tzinfo=timezone.utc) + timedelta(days=1)
            while hora < limite:
                esperadas.add(hora)
                hora += timedelta(hours=1)
        origem_esperada = {
            "archive": "historical_atmospheric_model",
            "forecast": "archived_forecast",
        }.get(fonte.get("endpoint"))
        if (
            not origem_esperada
            or fonte.get("origin") != origem_esperada
            or not isinstance(fonte.get("model"), str)
            or not fonte["model"].strip()
        ):
            fonte_incompleta.append(arquivo)
    observadas = {_utc(row["date_utc"], "hora meteorológica") for row in rows}
    horas_sessoes = set()
    for sessao in sessoes:
        hora = _utc(sessao["date_start"], "início de sessão").replace(
            minute=0, second=0, microsecond=0
        )
        limite = _utc(sessao["date_end"], "fim de sessão").replace(
            minute=0, second=0, microsecond=0
        )
        while hora <= limite:
            horas_sessoes.add(hora)
            hora += timedelta(hours=1)
    nulos = invalidos = 0
    for row in rows:
        arquivo = row.get("fonte_arquivo")
        unidades = json.loads(row["unidades_json"])
        for campo in campos_por_fonte.get(arquivo, METEO_UNIDADES):
            valor = row.get(campo)
            if valor is None:
                nulos += 1
            elif (
                isinstance(valor, bool)
                or not isinstance(valor, (int, float))
                or not math.isfinite(valor)
            ):
                invalidos += 1
            unidade = unidades.get(campo)
            if (
                not isinstance(unidade, str)
                or not unidade.strip()
                or (campo in METEO_UNIDADES and unidade != METEO_UNIDADES[campo])
            ):
                unidades_invalidas.add((arquivo, campo))
    ausentes = len(esperadas - observadas)
    horas_sessoes_ausentes = len(horas_sessoes - observadas)
    fora_da_grade = sum(
        h.minute != 0 or h.second != 0 or h.microsecond != 0 for h in observadas
    )
    motivos = []
    if ausentes:
        motivos.append(
            "{} de {} horas esperadas ausentes".format(ausentes, len(esperadas))
        )
    if nulos:
        motivos.append(
            "{} valores ausentes nos campos meteorológicos solicitados".format(nulos)
        )
    if invalidos:
        motivos.append(
            "{} valores meteorológicos não numéricos ou não finitos".format(invalidos)
        )
    if unidades_invalidas:
        motivos.append(
            "{} campos/fonte com unidade ausente ou incompatível".format(
                len(unidades_invalidas)
            )
        )
    if sem_janela:
        motivos.append(
            "{} fontes sem janela diária válida declarada; completude temporal não certificada".format(
                len(sem_janela)
            )
        )
    if fonte_incompleta:
        motivos.append(
            "{} fontes sem origem/modelo compatíveis com o endpoint".format(
                len(fonte_incompleta)
            )
        )
    if fora_da_grade:
        motivos.append(
            "{} instantes fora da grade horária declarada".format(fora_da_grade)
        )
    if horas_sessoes_ausentes:
        motivos.append(
            "{} horas das sessões catalogadas sem cobertura meteorológica".format(
                horas_sessoes_ausentes
            )
        )
    return {
        "n_horas_observadas": len(observadas),
        "n_horas_esperadas": len(esperadas) if not sem_janela and esperadas else None,
        "n_horas_ausentes": ausentes if not sem_janela and esperadas else None,
        "n_valores_nulos": nulos,
        "n_valores_invalidos": invalidos,
        "n_campos_unidade_invalida": len(unidades_invalidas),
        "n_horas_sessoes_ausentes": horas_sessoes_ausentes,
    }, motivos


def _equipes(locais, tabelas):
    for arquivo, tipo in (
        ("resultados.csv", "Race"),
        ("sprint_resultados.csv", "Sprint"),
    ):
        grupos = defaultdict(list)
        for row in locais[arquivo]:
            if row.get("equipe_id"):
                grupos[_key(row) + (row["equipe_id"],)].append(row)
        for group, rows in sorted(grupos.items()):
            pontos = [_numero(row.get("pontos"), "pontos") for row in rows]
            posicoes = [
                _numero(row.get("posicao_final"), "posicao_final") for row in rows
            ]
            conhecidos = [valor for valor in pontos if valor is not None]
            posicoes = [valor for valor in posicoes if valor is not None]
            tabelas["comparativo_equipes"].append(
                dict(
                    _dictkey(group[:3]),
                    tipo_sessao=tipo,
                    equipe_id=group[3],
                    pilotos_id_json=_json(sorted(row["piloto_id"] for row in rows)),
                    n_resultados=len(rows),
                    n_pontos_conhecidos=len(conhecidos),
                    pontos_soma_observada=sum(conhecidos) if conhecidos else None,
                    pontos_completos=len(conhecidos) == len(rows),
                    n_posicoes_conhecidas=len(posicoes),
                    posicao_media_observada=(
                        sum(posicoes) / len(posicoes) if posicoes else None
                    ),
                    melhor_posicao_observada=min(posicoes) if posicoes else None,
                    fontes_id_json=_json(
                        sorted({row.get("fonte_id", "") for row in rows})
                    ),
                    escopo="descritivo dos resultados disponíveis; sem inferência causal ou campeonato reconstruído",
                )
            )


def _estrategias(tabelas):
    grupos = defaultdict(list)
    for row in tabelas["stints"]:
        if row["session_name"] in ("Race", "Sprint"):
            grupos[(row["session_key"], row["driver_number"])].append(row)
    for _, rows in sorted(grupos.items()):
        ordenados = sorted(rows, key=lambda row: row["stint_number"])
        lacunas = False
        limites_incompletos = 0
        qualidade = []
        sequencia_comparavel = True
        anterior = None
        sequencia = []
        for row in ordenados:
            if not row["limites_voltas_comparaveis"]:
                limites_incompletos += 1
                qualidade.append(
                    {
                        "stint_number": row["stint_number"],
                        "flags": json.loads(row["qualidade_limites_json"]),
                    }
                )
            if anterior:
                inicio = row["lap_start"]
                inicio_anterior, fim_anterior = (
                    anterior["lap_start"],
                    anterior["lap_end"],
                )
                flags_sequencia = []
                if (
                    inicio not in (None, 0)
                    and inicio_anterior not in (None, 0)
                    and inicio <= inicio_anterior
                ):
                    flags_sequencia.append("ordem_limites_diverge_stint_number")
                    sequencia_comparavel = False
                if inicio not in (None, 0) and fim_anterior not in (None, 0):
                    if inicio < fim_anterior:
                        flags_sequencia.append("intervalos_sobrepostos_na_fonte")
                        sequencia_comparavel = False
                    elif inicio == fim_anterior:
                        flags_sequencia.append("fronteira_compartilhada_na_fonte")
                    lacunas = lacunas or inicio > fim_anterior + 1
                if flags_sequencia:
                    qualidade.append(
                        {
                            "stint_number": row["stint_number"],
                            "stint_anterior": anterior["stint_number"],
                            "flags": flags_sequencia,
                        }
                    )
            sequencia.append(
                {
                    campo: row[campo]
                    for campo in (
                        "stint_number",
                        "lap_start",
                        "lap_end",
                        "compound",
                        "tyre_age_at_start",
                    )
                }
            )
            anterior = row
        base = {campo: ordenados[0][campo] for campo in COMUM + IDENTIDADE}
        base.update(
            n_stints_observados=len(ordenados),
            compostos_observados_json=_json([row["compound"] for row in ordenados]),
            sequencia_stints_json=_json(sequencia),
            tem_lacunas_entre_stints=(
                lacunas
                if lacunas or (not limites_incompletos and sequencia_comparavel)
                else None
            ),
            n_stints_limites_incompletos=limites_incompletos,
            limites_voltas_comparaveis=not limites_incompletos and sequencia_comparavel,
            qualidade_limites_json=_json(qualidade),
            interpretacao="sequência observada; parada não comprova troca de pneu nem intenção estratégica",
        )
        tabelas["estrategias_pneus"].append(base)


def _cobertura(eventos, locais, tabelas, pilotos, fontes, cobertura_fontes):
    tipos = {
        "sessoes": "openf1",
        "pilotos_openf1": "openf1",
        "tempos_sessoes": "openf1",
        "laps_sessoes": "openf1",
        "stints": "openf1",
        "paradas_openf1": "openf1",
        "clima_pista": "openf1",
        "clima_open_meteo": "open-meteo",
        "comparativo_equipes": "local-jolpica",
        "estrategias_pneus": "openf1",
    }
    key_por_sessao = {row["session_key"]: _key(row) for row in tabelas["sessoes"]}
    sessoes_por_gp = defaultdict(set)
    provas_por_gp = defaultdict(set)
    for row in tabelas["sessoes"]:
        key = _key(row)
        sessoes_por_gp[key].add(row["session_key"])
        if row["session_name"] in ("Race", "Sprint"):
            provas_por_gp[key].add(row["session_key"])
    linhas_por_tipo = {}
    for tipo in tipos:
        if tipo == "pilotos_openf1":
            continue
        grupos = defaultdict(list)
        for row in tabelas[tipo]:
            grupos[_key(row)].append(row)
        linhas_por_tipo[tipo] = grupos
    locais_por_tipo = {}
    for nome in LOCAIS:
        grupos = defaultdict(list)
        for row in locais[nome]:
            grupos[_key(row)].append(row)
        locais_por_tipo[nome] = grupos
    pilotos_por_gp = defaultdict(list)
    for row in pilotos.values():
        pilotos_por_gp[key_por_sessao[row["session_key"]]].append(row)
    for key in sorted(eventos):
        for nome, tipo in LOCAIS.items():
            rows = locais_por_tipo[nome].get(key, [])
            estado = "disponivel" if rows else "indisponivel"
            motivo = "" if rows else "sem registros locais; ausência não significa zero"
            if (
                tipo == "sprint_resultados"
                and not rows
                and "Sprint" not in eventos[key].get("sessoes_calendario", {})
            ):
                estado, motivo = "nao_aplicavel", "calendário local não informa Sprint"
            tabelas["cobertura"].append(
                dict(
                    _dictkey(key),
                    tipo=tipo,
                    provider="local-jolpica",
                    estado=estado,
                    n_registros=len(rows) if rows else None,
                    n_sessoes_observadas=None,
                    n_sessoes_catalogadas=None,
                    motivo=motivo,
                    fontes_json=_json(sorted({r.get("fonte_id", "") for r in rows})),
                )
            )
        for tipo, provider in tipos.items():
            if tipo == "pilotos_openf1":
                rows = pilotos_por_gp.get(key, [])
            else:
                rows = linhas_por_tipo[tipo].get(key, [])
            refs = cobertura_fontes.get((key, tipo, provider), [])
            if tipo == "sessoes":
                refs = [
                    fonte
                    for fonte, raw in fontes
                    if fonte["provider"] == "openf1"
                    and fonte["endpoint"] == "sessions"
                    and int(fonte.get("temporada", 0)) == key[0]
                ]
            if tipo == "estrategias_pneus":
                refs = cobertura_fontes.get((key, "stints", "openf1"), [])
            sucessos = [r for r in refs if r.get("status") == 200]
            falhas = [r for r in refs if r.get("status") != 200]
            motivo = ""
            if rows:
                estado = "parcial" if falhas else "disponivel"
                if falhas:
                    motivo = "há registros e falhas de fonte; consultar manifesto"
            else:
                estado = "indisponivel"
                motivo = "resposta vazia" if sucessos else "fonte não coletada"
                if falhas:
                    motivo = "; ".join(
                        "{}: {}".format(
                            r.get("status"),
                            r.get("erro") or r.get("error") or "falha de fonte",
                        )
                        for r in falhas
                    )
                if tipo == "estrategias_pneus" and sucessos:
                    motivo = "sem stints de Race/Sprint; não inferir pneus de paradas"
            esperadas = (
                provas_por_gp[key]
                if tipo == "estrategias_pneus"
                else sessoes_por_gp[key]
            )
            observadas = {
                r["session_key"] for r in rows if r.get("session_key") is not None
            }
            if (
                rows
                and provider == "openf1"
                and tipo != "paradas_openf1"
                and observadas < esperadas
            ):
                estado = "parcial"
                faltantes = sorted(esperadas - observadas)
                motivo = (
                    motivo + "; " if motivo else ""
                ) + "sem registros das sessões {}".format(faltantes)
            if tipo in ("stints", "estrategias_pneus"):
                incompletos = sum(not r["limites_voltas_comparaveis"] for r in rows)
                sinalizados = sum(r["qualidade_limites_json"] != "[]" for r in rows)
                if sinalizados:
                    if incompletos:
                        estado = "parcial"
                    motivo = (
                        motivo + "; " if motivo else ""
                    ) + "{} registros sinalizados na qualidade dos limites de voltas; {} não comparáveis".format(
                        sinalizados, incompletos
                    )
            meteo = {}
            if tipo == "clima_open_meteo":
                meteo, qualidade = _qualidade_meteo(
                    rows, refs, linhas_por_tipo["sessoes"].get(key, [])
                )
                if qualidade:
                    if rows:
                        estado = "parcial"
                    motivo = "; ".join(([motivo] if motivo else []) + qualidade)
            tabelas["cobertura"].append(
                dict(
                    _dictkey(key),
                    tipo=tipo,
                    provider=provider,
                    estado=estado,
                    n_registros=len(rows) if rows else None,
                    n_sessoes_observadas=(
                        len(observadas) if rows and observadas else None
                    ),
                    n_sessoes_catalogadas=(
                        len(esperadas) if provider == "openf1" else None
                    ),
                    motivo=motivo,
                    fontes_json=_json(
                        [
                            {
                                "arquivo": r.get("arquivo"),
                                "status": r.get("status"),
                                "endpoint": r.get("endpoint"),
                            }
                            for r in refs
                        ]
                    ),
                    **meteo,
                )
            )


def gerar_derivados(destino):
    """Validar capturas e produzir CSVs descritivos; não acessa rede ou modelos."""
    raiz = Path(destino).resolve()
    eventos = _eventos(raiz)
    fontes_todas = _fontes(raiz)
    fontes = [
        (fonte, raw)
        for fonte, raw in fontes_todas
        if fonte.get("normalizar") is not False
    ]
    locais, identidades = _locais(raiz, eventos)
    tabelas = {nome: [] for nome in SCHEMAS}
    sessoes, excluidos_catalogo = _catalogo(raiz, fontes, eventos)
    tabelas["sessoes"] = sorted(
        sessoes.values(),
        key=lambda row: (_key(row), row["date_start"], row["session_key"]),
    )
    duplicatas_identicas = defaultdict(int)
    pilotos, cobertura_fontes, excluidos = _normalizar_openf1(
        fontes, eventos, sessoes, identidades, tabelas, duplicatas_identicas
    )
    excluidos.update(excluidos_catalogo)
    _meteo(fontes, eventos, tabelas, cobertura_fontes)
    _equipes(locais, tabelas)
    _estrategias(tabelas)
    _cobertura(eventos, locais, tabelas, pilotos, fontes, cobertura_fontes)
    conteudos = {}
    for nome, campos in SCHEMAS.items():
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(
            buffer, fieldnames=campos, extrasaction="raise", lineterminator="\n"
        )
        writer.writeheader()
        for row in tabelas[nome]:
            writer.writerow(
                {campo: "" if valor is None else valor for campo, valor in row.items()}
            )
        conteudos[nome + ".csv"] = buffer.getvalue().encode("utf-8")
    resultado = {
        "escopo": "descritivo posterior; sem alteração de modelo ou emissão",
        "eventos": len(eventos),
        "registros": {nome: len(rows) for nome, rows in tabelas.items()},
        "excluidos_raw_sem_mapeamento": excluidos,
        "duplicatas_identicas_raw": dict(duplicatas_identicas),
        "fontes_nao_normalizadas": [
            {
                "arquivo": fonte.get("arquivo"),
                "motivo": fonte.get("motivo")
                or fonte.get("motivo_exclusao")
                or "normalizar:false",
            }
            for fonte, raw in fontes_todas
            if fonte.get("normalizar") is False
        ],
        "arquivos": {
            nome: hashlib.sha256(content).hexdigest()
            for nome, content in conteudos.items()
        },
    }
    resumo = defaultdict(int)
    for row in tabelas["cobertura"]:
        resumo[row["estado"]] += 1
    resultado["cobertura_resumo"] = dict(resumo)
    conteudos["manifesto.json"] = (_json(resultado) + "\n").encode("utf-8")
    pasta = raiz / "normalizado"
    if pasta.is_symlink():
        raise ValueError("destino normalizado não pode ser symlink")
    for nome, dados in conteudos.items():
        arquivo = pasta / nome
        if arquivo.is_symlink() or (
            arquivo.exists()
            and (not arquivo.is_file() or arquivo.read_bytes() != dados)
        ):
            raise ValueError("destino normalizado divergente: {}".format(nome))
    pasta.mkdir(exist_ok=True)
    for nome, dados in conteudos.items():
        arquivo = pasta / nome
        if not arquivo.exists():
            with arquivo.open("xb") as handle:
                handle.write(dados)
    return resultado
