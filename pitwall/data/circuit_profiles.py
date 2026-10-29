"""Compõe fichas descritivas com fontes oficiais e elevação DEM explícita."""

import json
from pathlib import Path
from pitwall.paths import PROJECT_ROOT
import re
from pitwall.data.adjudication import TabelaHTML

ROOT = PROJECT_ROOT
SLUGS = {
    "bahrain": "bahrain",
    "jeddah": "saudi-arabia",
    "albert_park": "australia",
    "suzuka": "japan",
    "shanghai": "china",
    "miami": "miami",
    "imola": "imola_corrigido",
    "monaco": "monaco",
    "villeneuve": "canada",
    "catalunya": "spain",
    "red_bull_ring": "austria",
    "silverstone": "great-britain",
    "hungaroring": "hungary",
    "spa": "belgium",
    "zandvoort": "netherlands",
    "monza": "italy",
    "baku": "azerbaijan",
    "marina_bay": "singapore",
    "americas": "austin",
    "rodriguez": "mexico",
    "interlagos": "brazil",
    "vegas": "las-vegas",
    "losail": "qatar",
    "yas_marina": "abudhabi_corrigido",
    "madring": "madring",
    "sepang": "sepang",
}


def ficha_oficial(raw):
    p = TabelaHTML()
    p.feed(raw.decode("utf8"))
    text = p.text

    def campo(label):
        i = text.index(label)
        return text[i + 1]

    def km(label):
        return float(campo(label).replace("km", "").strip())

    metricas = {
        "comprimento_km": km("Circuit Length"),
        "primeiro_gp": int(campo("First Grand Prix")),
    }
    corrida = {
        "voltas": int(campo("Number of Laps")),
        "distancia_corrida_km": km("Race Distance"),
    }
    i = text.index("Fastest lap time")
    tempo = text[i + 1]
    autor = text[i + 2]
    if re.fullmatch(r"\d+:\d{2}\.\d{3}", tempo) and re.search(r"\(\d{4}\)", autor):
        corrida["recorde_volta"] = tempo + " · " + autor
    corpo = " ".join(text[text.index("About") :])
    curvas = re.findall(r"\b(\d{1,2})[ -](?:turn|corner)s?\b", corpo, re.I)
    curvas = {int(n) for n in curvas if 5 <= int(n) <= 30}
    if len(curvas) == 1:
        metricas["curvas"] = curvas.pop()
    final = re.search(r"final hairpin of Turn (\d+)", corpo)
    if final:
        metricas["curvas"] = int(final[1])
    if re.search(r"anti.clockwise|counter.clockwise", corpo, re.I):
        metricas["sentido"] = "Anti-horário"
    elif re.search(r"\bclockwise\b", corpo, re.I):
        metricas["sentido"] = "Horário"
    return metricas, corrida


def preparar():
    root = ROOT / "data/acervo_historico/resolucao-20261029"
    fontes = root / "fontes"
    recibos = {r["id"]: r for r in json.loads((fontes / "recibos.json").read_text())}
    coords = json.loads(
        (
            ROOT / "reports/resolucao_dados_20261028/coordenadas_elevacao.json"
        ).read_text()
    )
    alturas = json.loads((fontes / "elevacao_circuitos.bin").read_text())["elevation"]
    if len(coords) != len(alturas):
        raise ValueError("Elevações não correspondem às coordenadas")
    elev = {c["circuito_id"]: (v, c) for c, v in zip(coords, alturas)}
    asset = json.loads(
        (
            ROOT
            / "reports/resolucao_dados_20261028/assets_anteriores/paineis_editoriais.json"
        ).read_text()
    )
    mapas = json.loads((root / "transcricao_mapas_fia.json").read_text())
    anteriores = asset.get("circuitos", {})
    circuitos = {}
    for cid, slug in SLUGS.items():
        sid = "f1_austin_circuito" if cid == "americas" else "f1_circuito_" + slug
        r = recibos.get(sid)
        if not r or r["status"] != 200:
            continue
        estaveis, corrida = ficha_oficial((fontes / r["arquivo"]).read_bytes())
        campos_f1 = list(estaveis) + list(corrida)
        # Os campos já confirmados de Austin permanecem, com sua fonte própria.
        estaveis = {**anteriores.get(cid, {}).get("metricas_estaveis", {}), **estaveis}
        estaveis["altitude_m"] = elev[cid][0]
        if cid in mapas:
            estaveis.update(curvas=mapas[cid]["curvas"], sentido=mapas[cid]["sentido"])
        anos = {}
        for ano in [2024, 2025, 2026]:
            if estaveis["primeiro_gp"] > ano:
                continue
            dados = dict(corrida)
            recorde = dados.get("recorde_volta")
            if recorde and int(re.search(r"\((\d{4})\)", recorde)[1]) > ano:
                del dados["recorde_volta"]
            anos[str(ano)] = dados
        if cid in mapas:
            for ano in ["2024", "2025"]:
                anos[ano]["zonas_drs"] = mapas[cid]["zonas_drs"]
        circuitos[cid] = {
            "uso": "contexto_descritivo_atual_sem_uso_no_modelo",
            "verificado_em": "2026-10-29",
            "metricas_estaveis": estaveis,
            "por_temporada": anos,
            "fontes": anteriores.get(cid, {}).get("fontes", [])
            + [
                {
                    "titulo": "Formula 1 — ficha do circuito (referência descritiva consultada em 2026)",
                    "url": r["url"],
                    "campos": campos_f1,
                    "sha256": r["sha256"],
                },
                {
                    "titulo": "Open-Meteo / Copernicus DEM GLO-90 — altitude aproximada no ponto do calendário",
                    "url": "https://open-meteo.com/en/docs/elevation-api",
                    "campos": ["altitude_m"],
                    "coordenadas": elev[cid][1],
                    "sha256": recibos["elevacao_circuitos"]["sha256"],
                },
                {
                    "titulo": "F1 — DRS substituído por aerodinâmica ativa em 2026",
                    "url": recibos["f1_regras2026"]["url"],
                    "campos": ["zonas_drs"],
                },
            ],
        }
        if cid in mapas:
            circuitos[cid]["fontes"].append(
                {
                    "titulo": "FIA — mapa de referência 2025 (página {})".format(
                        mapas[cid]["pagina_pdf"]
                    ),
                    "url": recibos["fia_media_kit_2025"]["url"]
                    + "#page="
                    + str(mapas[cid]["pagina_pdf"]),
                    "campos": ["curvas", "sentido", "zonas_drs"],
                    "sha256": recibos["fia_media_kit_2025"]["sha256"],
                    "criterio": mapas[cid]["criterio"],
                }
            )
        if cid == "americas":
            circuitos[cid]["fontes"].append(
                {
                    "titulo": "FIA — mapa de Austin 2025, zonas DRS 1 e 2",
                    "url": recibos["fia_austin_drs2025"]["url"],
                    "campos": ["zonas_drs"],
                    "sha256": recibos["fia_austin_drs2025"]["sha256"],
                }
            )
    asset["circuitos"] = circuitos
    destino = root / "paineis_editoriais_complementados.json"
    with destino.open("x") as f:
        json.dump(asset, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Fichas:", len(circuitos))


if __name__ == "__main__":
    preparar()
