"""Adjudicação documental offline; fontes e base congelada permanecem intactas."""

import csv
from collections import Counter
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path

BASE = Path("data/acervo_historico/coleta-20261027T230248Z")
DESTINO = Path("data/acervo_historico/resolucao-20261029")
SLUGS = {
    "monaco": "monaco",
    "zandvoort": "netherlands",
    "baku": "azerbaijan",
    "marina_bay": "singapore",
    "interlagos": "brazil",
    "miami": "miami",
    "imola": "emilia-romagna",
    "albert_park": "australia",
    "madring": "spain",
}


def csv_ler(p):
    with Path(p).open(newline="", encoding="utf8") as f:
        return list(csv.DictReader(f))


def csv_gravar(p, rows):
    if not rows:
        return
    with p.open("x", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class TabelaHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.script = False
        self.text = []

    def handle_starttag(self, t, a):
        if t == "script":
            self.script = True
        if t == "tr":
            self.row = []
        if t in ("td", "th"):
            self.cell = []

    def handle_endtag(self, t):
        if t == "script":
            self.script = False
        if t in ("td", "th") and self.cell is not None:
            if self.row is not None:
                self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        if t == "tr" and self.row:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, d):
        if self.cell is not None:
            self.cell.append(d)
        if not self.script and d.strip():
            self.text.append(d.strip())


def classificacao_html(raw):
    p = TabelaHTML()
    p.feed(raw.decode("utf8"))
    if ["Pos.", "No.", "Driver", "Team", "Q1", "Q2", "Q3", "Laps"] not in p.rows:
        raise ValueError("Tabela de classificação oficial não reconhecida")
    rows = [r for r in p.rows if len(r) == 8 and r[1].isdigit()]
    if not 15 <= len(rows) <= 24 or len({r[1] for r in rows}) != len(rows):
        raise ValueError("Pilotos/contagem oficial divergentes")
    return {
        r[1]: dict(
            posicao_classificacao=r[0],
            q1_original=r[4],
            q2_original=r[5],
            q3_original=r[6],
            piloto_rotulo=r[2],
        )
        for r in rows
    }, "\n".join(p.text)


def resolver(fila, resultados, recibos, fontes):
    numeros = {
        (x["temporada"], x["rodada"], x["piloto_id"]): x["numero"] for x in resultados
    }
    oficiais = {}
    saida = []
    complementos = []
    for item in fila:
        p = dict(item)
        key = json.loads(p["identidade_json"])
        tipo = p["tipo"]
        p.update(
            estado="pendente",
            decisao="",
            valor_oficial="",
            adjudicacao="",
            natureza_dado="complemento_descritivo_sem_alterar_canonico",
        )
        if tipo in ("conflito_classificacao", "classificacao_canonica_ausente"):
            ano = str(key["temporada"])
            rodada = str(key["rodada"])
            pid = key["piloto_id"]
            rs = next(
                (
                    r
                    for r in resultados
                    if (r["temporada"], r["rodada"], r["piloto_id"])
                    == (ano, rodada, pid)
                ),
                None,
            )
            pista = key.get("circuito_id") or (rs or {}).get("circuito_id")
            source = recibos.get("f1_q_{}_{}".format(ano, SLUGS.get(pista, "")))
            if source and source["status"] == 200:
                if source["id"] not in oficiais:
                    oficiais[source["id"]] = classificacao_html(
                        (fontes / source["arquivo"]).read_bytes()
                    )
                rows, text = oficiais[source["id"]]
                numero = numeros.get((ano, rodada, pid))
                oficial = rows.get(numero)
                p.update(
                    evidencia_resolucao=str(fontes / source["arquivo"]),
                    sha256_resolucao=source["sha256"],
                )
                if oficial:
                    campo = key.get("campo", "posicao_classificacao")
                    valor = oficial[campo]
                    import re

                    anteriores = re.fullmatch(
                        r"canônico=(.*?) / archive=(.*)", p["motivo"]
                    )
                    decisao = (
                        "confirma_canonico"
                        if anteriores and valor == anteriores[1]
                        else (
                            "confirma_archive"
                            if anteriores and valor == anteriores[2]
                            else "valor_oficial_distinto"
                        )
                    )
                    p.update(
                        estado="resolvido_documentalmente",
                        valor_oficial=valor,
                        adjudicacao=decisao,
                        decisao="Classificação oficial atual adjudicada por número literal no mesmo evento; DQ/DNS não viram posição numérica. Valores antigos preservados.",
                    )
                    complementos.append(
                        dict(
                            temporada=ano,
                            rodada=rodada,
                            circuito_id=pista,
                            piloto_id=pid,
                            numero=numero,
                            campo=campo,
                            valor_oficial=valor,
                            estado_classificacao=oficial["posicao_classificacao"],
                            url=source["url"],
                            sha256=source["sha256"],
                        )
                    )
                else:
                    p.update(
                        estado="ausencia_confirmada_na_tabela_oficial",
                        decisao="Piloto ausente da tabela oficial capturada; nenhuma posição/tempo ou causa esportiva foi inventada. Preservar a ausência no canônico.",
                    )
        elif tipo == "laps_sessoes":
            fonte = recibos.get("fia_laps_baku2025")
            complemento = DESTINO / "voltas_classificacao_fia.csv"
            if fonte and fonte["status"] == 200 and complemento.is_file():
                p.update(
                    estado="resolvido_com_fonte_alternativa",
                    decisao="FIA: 243 passagens de 20 pilotos, sendo 223 durações e 20 horários de referência. Não equivale ao schema/telemetria OpenF1.",
                    evidencia_resolucao=str(complemento),
                    sha256_resolucao=hashlib.sha256(
                        complemento.read_bytes()
                    ).hexdigest(),
                )
        elif tipo in ("stints", "estrategias_pneus"):
            tabela = csv_ler(
                BASE
                / "normalizado"
                / ("stints.csv" if tipo == "stints" else "estrategias_pneus.csv")
            )
            rows = [
                r
                for r in tabela
                if str(r["temporada"]) == str(key["temporada"])
                and str(r["rodada"]) == str(key["rodada"])
            ]
            invalidos = [r for r in rows if r["limites_voltas_comparaveis"] == "False"]
            if not invalidos:
                p.update(
                    evidencia_resolucao=str(BASE / "normalizado/estrategias_pneus.csv"),
                    sha256_resolucao=hashlib.sha256(
                        (BASE / "normalizado/estrategias_pneus.csv").read_bytes()
                    ).hexdigest(),
                    estado="resolvido_classificacao_de_qualidade",
                    decisao="Apenas fronteiras compartilhadas sinalizadas; todos os limites são comparáveis. Aviso informativo não implica dado incompleto.",
                )
            else:
                fontes_revisadas = [
                    r
                    for r in recibos.values()
                    if r["id"].startswith("openf1_stints_")
                    and r.get("status") == 200
                    and any(
                        r["id"] == "openf1_stints_" + x["session_key"]
                        for x in invalidos
                    )
                ]
                p.update(
                    estado="lacuna_confirmada_na_origem",
                    decisao="Fonte consultada por sessão; limites ausentes/inconsistentes persistem. Nenhum intervalo foi estimado ou substituído por zero.",
                    evidencia_resolucao=json.dumps(
                        [str(fontes / r["arquivo"]) for r in fontes_revisadas]
                    ),
                    sha256_resolucao=json.dumps(
                        [r["sha256"] for r in fontes_revisadas]
                    ),
                )
        elif tipo == "proveniencia_archive":
            path = DESTINO / "archive_proveniencia_resolvida.json"
            proof = json.loads(path.read_text()) if path.exists() else None
            if (
                proof
                and proof.get("estado")
                == "origem_identificada_por_metadados_locais_e_bytes"
            ):
                for n, sha in proof["arquivos_sha256"].items():
                    if (
                        hashlib.sha256(
                            (
                                (Path.home() / "Downloads" / "archive") / n
                            ).read_bytes()
                        ).hexdigest()
                        != sha
                    ):
                        raise ValueError("Bytes do archive diferem da prova de origem")
                p.update(
                    estado="resolvido_origem_identificada",
                    decisao="Dataset jtrotman/formula-1-race-data, ID 1320004, versão de armazenamento 20597603. WhereFroms do ZIP original e 14 CSVs idênticos. UTC original desconhecido; CC0 é a declaração atual do catálogo, não verificação separada da licença histórica.",
                    evidencia_resolucao=str(path),
                    sha256_resolucao=hashlib.sha256(path.read_bytes()).hexdigest(),
                )
            else:
                p.update(
                    estado="proveniencia_nao_comprovada",
                    decisao="Falta vínculo entre bytes locais e origem original; preservar desconhecido.",
                )
        saida.append(p)
    return saida, complementos


def main():
    fontes = DESTINO / "fontes"
    recibos = json.loads((fontes / "recibos.json").read_text())
    for r in recibos:
        if (
            hashlib.sha256((fontes / r["arquivo"]).read_bytes()).hexdigest()
            != r["sha256"]
        ):
            raise ValueError("Hash de fonte divergente")
    fila = csv_ler("reports/melhorias_blueprint_20261028/pendencias_acervo.csv")
    saida, complementos = resolver(
        fila,
        csv_ler(BASE / "local/resultados.csv"),
        {r["id"]: r for r in recibos},
        fontes,
    )
    csv_gravar(DESTINO / "classificacao_complementar.csv", complementos)
    csv_gravar(DESTINO / "pendencias_adjudicadas.csv", saida)
    print(Counter(x["estado"] for x in saida))


if __name__ == "__main__":
    main()
