"""Executa A1–A3 offline em um destino v2 novo; não toca em v1 nem em 2026."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from pitwall.paths import PROJECT_ROOT

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from pitwall.research.methodology_v2 import ErroContratoV2, metricas_probabilisticas

RAIZ = PROJECT_ROOT
V1 = RAIZ / "data" / "preparado"
ARCHIVE = (Path.home() / "Downloads" / "archive")
Q_FEATURES = [
    "posicao_classificacao",
    "posicao_classificacao_ausente",
    "posicao_classificacao_repetida",
    "tamanho_pelotao",
]
V1_FEATURES = [
    "posicao_classificacao",
    "posicao_classificacao_repetida",
    "classificacao_ausente",
    "posicao_classificacao_ausente",
    "media_posicao_final_5",
    "taxa_podios_5",
    "n_posicoes_5",
    "n_podios_5",
    "media_pontos_equipe_5",
    "n_corridas_equipe_5",
    "n_participacoes_equipe_5",
    "historico_piloto_insuficiente",
    "historico_equipe_insuficiente",
    "equipe_pre_corrida_ausente",
    "referencia_temporal_ausente",
]
A3_FEATURES = [
    "media_posicao_final_5",
    "taxa_podios_5",
    "n_posicoes_5",
    "n_podios_5",
    "media_pontos_equipe_5",
    "n_corridas_equipe_5",
    "n_participacoes_equipe_5",
    "equipe_entrada_ausente",
    "historico_piloto_insuficiente",
    "historico_equipe_insuficiente",
    "dias_desde_ultima_participacao",
    "media_posicao_final_ewma",
    "taxa_podios_ewma",
    "suporte_forma_ewma",
    "n_status_piloto_conhecido_5",
    "n_falha_mecanica_piloto_5",
    "n_incidente_piloto_5",
    "n_outro_nao_finalizado_piloto_5",
    "n_status_desconhecido_piloto_5",
    "taxa_falha_mecanica_piloto_5",
    "taxa_incidente_piloto_5",
    "historico_confiabilidade_piloto_insuficiente",
    "n_gps_status_equipe_conhecido_5",
    "taxa_falha_mecanica_equipe_5",
    "taxa_incidente_equipe_5",
    "historico_confiabilidade_equipe_insuficiente",
]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def agora():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def numero(valor):
    return None if valor in (None, "") else float(valor)


def inteiro(valor):
    return None if valor in (None, "") else int(float(valor))


def chave(linha):
    return (int(linha["temporada"]), int(linha["rodada"]), linha["piloto_id"])


def evento(linha):
    return (int(linha["temporada"]), int(linha["rodada"]))


def gravar_csv(path, linhas):
    if not linhas:
        raise ErroContratoV2("não há linhas para {}".format(path.name))
    campos = list(linhas[0])
    with path.open("w", encoding="utf-8", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos)
        writer.writeheader()
        writer.writerows(linhas)


def carregar_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def _utc(texto):
    if not isinstance(texto, str) or not texto.endswith("Z"):
        raise ValueError("timestamp sem UTC explícito")
    return datetime.fromisoformat(str(texto).replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def liberado_pelo_protocolo_utc(linha):
    """Liberação administrativa: 00:00Z no dia seguinte ao GP histórico."""
    data = datetime.fromisoformat(linha["data_corrida"]).date()
    return datetime.combine(
        data + __import__("datetime").timedelta(days=1),
        datetime.min.time(),
        timezone.utc,
    )


def validar_base_v2(base):
    """Contrato aplicado ao CSV realmente consumido antes da preparação v2."""
    vistos = set()
    obrigatorios = {
        "temporada",
        "rodada",
        "piloto_id",
        "classificacao_ausente",
        "referencia_temporal_ausente",
        "limite_inferior_referencia_utc",
        "fim_sessao_referencia_utc",
    }
    for linha in base:
        if not obrigatorios.issubset(linha):
            raise ValueError("coluna obrigatória ausente na base v2")
        try:
            temporada, rodada = int(linha["temporada"]), int(linha["rodada"])
        except (ValueError, TypeError):
            raise ValueError("temporada ou rodada inválida")
        if temporada not in range(2021, 2026):
            raise ValueError("temporada fora de 2021–2025")
        identificador = (temporada, rodada, linha["piloto_id"])
        if not linha["piloto_id"] or identificador in vistos:
            raise ValueError("chave v2 ausente ou duplicada")
        vistos.add(identificador)
        try:
            _utc(linha["limite_inferior_referencia_utc"])
            fim = linha.get("fim_sessao_referencia_utc")
            if fim:
                _utc(fim)
        except ValueError as erro:
            raise ValueError("timestamp UTC da referência inválido") from erro


def categoria_status(status):
    if status in ("Finished", "Lapped") or (
        isinstance(status, str) and status.startswith("+")
    ):
        return "finalizado"
    if status in {
        "Engine",
        "Gearbox",
        "Hydraulics",
        "Brakes",
        "Suspension",
        "Power Unit",
        "Turbo",
        "Oil leak",
        "Mechanical",
        "Power loss",
        "Fuel pressure",
        "Undertray",
    }:
        return "mecanica"
    if status in {"Collision", "Accident", "Collision damage", "Spun off"}:
        return "incidente"
    if status in {"Retired", "Did not start", "Withdrew", "Disqualified"}:
        return "outro"
    return "desconhecido"


def _historico(rows, atual):
    corte = _utc(atual["limite_inferior_referencia_utc"])
    return [
        item
        for item in rows
        if evento(item) < evento(atual) and liberado_pelo_protocolo_utc(item) <= corte
    ]


def construir_linhas_v2(base):
    validar_base_v2(base)
    base = sorted(base, key=lambda item: (evento(item), item["piloto_id"]))
    tamanhos = Counter(
        evento(item) for item in base if inteiro(item["classificacao_ausente"]) == 0
    )
    saida, janelas = [], []
    for atual in base:
        if inteiro(atual["classificacao_ausente"]) != 0 or atual[
            "referencia_temporal_ausente"
        ] not in ("0", "False", False):
            continue
        anteriores = [
            item
            for item in _historico(base, atual)
            if item.get("resultado_ausente") in ("0", 0, False)
            and item.get("podio") in ("0", "1", 0, 1)
        ]
        piloto = [
            item for item in anteriores if item["piloto_id"] == atual["piloto_id"]
        ][-5:]
        equipes = defaultdict(list)
        for item in anteriores:
            if (
                item["equipe_id_entrada"]
                and item["equipe_id_entrada"] == atual["equipe_id_entrada"]
            ):
                equipes[evento(item)].append(item)
        eventos_equipe = [equipes[ch] for ch in sorted(equipes)[-5:]]
        equipe_linhas = [item for grupo in eventos_equipe for item in grupo]

        def dados_status(linhas):
            cats = [
                categoria_status(item["status"])
                for item in linhas
                if item.get("status") not in (None, "")
            ]
            return Counter(cats)

        sp, se = dados_status(piloto), dados_status(equipe_linhas)
        conhecidos_p = sum(
            sp[c] for c in ("finalizado", "mecanica", "incidente", "outro")
        )
        conhecidos_e = sum(
            se[c] for c in ("finalizado", "mecanica", "incidente", "outro")
        )
        posicoes = [
            inteiro(item["posicao_final"])
            for item in piloto
            if inteiro(item["posicao_final"]) is not None
        ]
        podios = [
            inteiro(item["podio"])
            for item in piloto
            if item["podio"] in ("0", "1", 0, 1)
        ]
        pontos_equipe = [
            numero(item["pontos"])
            for item in equipe_linhas
            if numero(item["pontos"]) is not None
        ]
        dias = None
        if piloto:
            dias = (
                datetime.fromisoformat(atual["data_corrida"])
                - datetime.fromisoformat(piloto[-1]["data_corrida"])
            ).days
        pesos_pos = (
            np.array([0.5 ** (len(posicoes) - 1 - i) for i in range(len(posicoes))])
            if posicoes
            else np.array([])
        )
        pesos_pod = (
            np.array([0.5 ** (len(podios) - 1 - i) for i in range(len(podios))])
            if podios
            else np.array([])
        )
        ewma_pos = (
            None if not posicoes else float(np.average(posicoes, weights=pesos_pos))
        )
        ewma_pod = None if not podios else float(np.average(podios, weights=pesos_pod))
        linha = {
            "temporada": int(atual["temporada"]),
            "rodada": int(atual["rodada"]),
            "piloto_id": atual["piloto_id"],
            "circuito_id": atual["circuito_id"],
            "data_corrida": atual["data_corrida"],
            "equipe_id_entrada": atual["equipe_id_entrada"],
            "equipe_entrada_ausente": int(not atual["equipe_id_entrada"]),
            "limite_inferior_referencia_utc": atual["limite_inferior_referencia_utc"],
            "posicao_classificacao": inteiro(atual["posicao_classificacao"]),
            "classificacao_ausente": inteiro(atual["classificacao_ausente"]),
            "posicao_classificacao_ausente": inteiro(
                atual["posicao_classificacao_ausente"]
            ),
            "equipe_pre_corrida_ausente": inteiro(
                atual.get("equipe_pre_corrida_ausente")
                or int(not atual["equipe_id_entrada"])
            ),
            "referencia_temporal_ausente": int(
                atual["referencia_temporal_ausente"] in ("1", "True", True)
            ),
            "posicao_classificacao_repetida": inteiro(
                atual["posicao_classificacao_repetida"]
            ),
            "tamanho_pelotao": tamanhos[evento(atual)],
            "media_posicao_final_5": (
                None if not posicoes else sum(posicoes) / len(posicoes)
            ),
            "taxa_podios_5": None if not podios else sum(podios) / len(podios),
            "n_posicoes_5": len(posicoes),
            "n_podios_5": len(podios),
            "media_pontos_equipe_5": (
                None if not pontos_equipe else sum(pontos_equipe) / len(pontos_equipe)
            ),
            "n_corridas_equipe_5": len(eventos_equipe),
            "n_participacoes_equipe_5": len(equipe_linhas),
            "historico_piloto_insuficiente": int(len(piloto) < 5),
            "historico_equipe_insuficiente": int(len(eventos_equipe) < 5),
            "dias_desde_ultima_participacao": dias,
            "media_posicao_final_ewma": ewma_pos,
            "taxa_podios_ewma": ewma_pod,
            "suporte_forma_ewma": len(posicoes),
            "n_status_piloto_conhecido_5": conhecidos_p,
            "n_falha_mecanica_piloto_5": sp["mecanica"],
            "n_incidente_piloto_5": sp["incidente"],
            "n_outro_nao_finalizado_piloto_5": sp["outro"],
            "n_status_desconhecido_piloto_5": sp["desconhecido"],
            "taxa_falha_mecanica_piloto_5": (
                None if not conhecidos_p else sp["mecanica"] / conhecidos_p
            ),
            "taxa_incidente_piloto_5": (
                None if not conhecidos_p else sp["incidente"] / conhecidos_p
            ),
            "historico_confiabilidade_piloto_insuficiente": int(conhecidos_p < 5),
            "n_gps_status_equipe_conhecido_5": sum(
                any(categoria_status(x["status"]) != "desconhecido" for x in grupo)
                for grupo in eventos_equipe
            ),
            "taxa_falha_mecanica_equipe_5": (
                None if not conhecidos_e else se["mecanica"] / conhecidos_e
            ),
            "taxa_incidente_equipe_5": (
                None if not conhecidos_e else se["incidente"] / conhecidos_e
            ),
            "historico_confiabilidade_equipe_insuficiente": int(conhecidos_e < 5),
            "b1_disponivel": 0,
            "podio": inteiro(atual["podio"]),
            "alvo_conhecido": int(atual["podio"] in ("0", "1", 0, 1)),
        }
        saida.append(linha)
        janelas.append(
            {
                "chave": chave(atual),
                "historico_piloto": [chave(x) for x in piloto],
                "historico_equipe": [chave(x) for x in equipe_linhas],
            }
        )
    return saida, janelas


def aplicar_oraculo_entradas_v1(linhas):
    """A réplica usa as 15 entradas canônicas v1 sem regravar a fotografia."""
    entradas = carregar_csv(V1 / "entradas.csv")
    por_chave = {chave(x): x for x in entradas}
    for linha in linhas:
        origem = por_chave.get(chave(linha))
        if origem is None:
            raise ErroContratoV2("entrada v1 ausente para chave v2")
        for campo in V1_FEATURES:
            linha[campo] = (
                (1 if origem[campo] in ("1", "True", 1, True) else 0)
                if campo
                in {
                    "posicao_classificacao_repetida",
                    "classificacao_ausente",
                    "posicao_classificacao_ausente",
                    "historico_piloto_insuficiente",
                    "historico_equipe_insuficiente",
                    "equipe_pre_corrida_ausente",
                    "referencia_temporal_ausente",
                }
                else numero(origem[campo])
            )


def matriz(linhas, campos):
    return np.array(
        [
            [np.nan if item[campo] is None else float(item[campo]) for campo in campos]
            for item in linhas
        ]
    )


def modelo_logistico():
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=1.0, penalty="l2", solver="lbfgs", max_iter=2000, random_state=42
                ),
            ),
        ]
    )


def modelo_v1_replicado():
    return Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median", keep_empty_features=True, add_indicator=False
                ),
            ),
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=1.0,
                    penalty="l2",
                    solver="lbfgs",
                    max_iter=2000,
                    tol=1e-4,
                    class_weight=None,
                    random_state=42,
                ),
            ),
        ]
    )


def modelo_hgb():
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            (
                "model",
                HistGradientBoostingClassifier(
                    max_leaf_nodes=15,
                    learning_rate=0.1,
                    l2_regularization=1,
                    max_iter=100,
                    random_state=42,
                    early_stopping=False,
                ),
            ),
        ]
    )


def candidatos(familia):
    campos = (
        Q_FEATURES
        if familia == "q"
        else A3_FEATURES if familia == "a3" else Q_FEATURES + A3_FEATURES
    )
    saida = []
    for c in (0.1, 1.0, 10.0):
        saida.append(
            (
                "logistica_C{}".format(c),
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(strategy="median", keep_empty_features=True),
                        ),
                        ("scale", StandardScaler()),
                        (
                            "model",
                            LogisticRegression(
                                C=c,
                                penalty="l2",
                                solver="lbfgs",
                                max_iter=2000,
                                random_state=42,
                            ),
                        ),
                    ]
                ),
                campos,
            )
        )
    for folhas in (7, 15):
        for taxa in (0.03, 0.1):
            for l2 in (0.0, 1.0):
                saida.append(
                    (
                        "hgb_l{}_r{}_l2{}".format(folhas, taxa, l2),
                        Pipeline(
                            [
                                (
                                    "imputer",
                                    SimpleImputer(
                                        strategy="median", keep_empty_features=True
                                    ),
                                ),
                                (
                                    "model",
                                    HistGradientBoostingClassifier(
                                        max_leaf_nodes=folhas,
                                        learning_rate=taxa,
                                        l2_regularization=l2,
                                        max_iter=100,
                                        random_state=42,
                                        early_stopping=False,
                                    ),
                                ),
                            ]
                        ),
                        campos,
                    )
                )
    return saida


def dividir_selecao_temporal(treino):
    """Partições por GP; a divisão registrada é a mesma usada na seleção."""
    temporadas = sorted({x["temporada"] for x in treino})
    if len(temporadas) < 2:
        eventos = sorted({evento(x) for x in treino})
        corte = max(1, len(eventos) // 5)
        eventos_valid = set(eventos[-corte:])
        ajuste = [x for x in treino if evento(x) not in eventos_valid]
        valid = [x for x in treino if evento(x) in eventos_valid]
    else:
        interna = temporadas[-1]
        ajuste = [x for x in treino if x["temporada"] < interna]
        valid = [x for x in treino if x["temporada"] == interna]
    if (
        not ajuste
        or not valid
        or max(evento(x) for x in ajuste) >= min(evento(x) for x in valid)
    ):
        raise ErroContratoV2(
            "seleção interna exige partições temporais não vazias e disjuntas"
        )
    return ajuste, valid


def registrar_selecao(treino, fold, metodo, nome, fixa=False):
    ajuste, valid = (treino, []) if fixa else dividir_selecao_temporal(treino)
    registro = {
        "fold": fold,
        "metodo": metodo,
        "selecao_interna": nome,
        "tipo": "receita_fixa" if fixa else "selecao_temporal",
        "registrado_em_utc": agora(),
    }
    for rotulo, linhas in [
        ("ajuste", ajuste),
        ("validacao_interna", valid),
        ("treino_externo", treino),
    ]:
        ordenadas = sorted(linhas, key=chave)
        registro["temporadas_" + rotulo] = ",".join(
            map(str, sorted({x["temporada"] for x in linhas}))
        )
        registro["gps_" + rotulo] = json.dumps(sorted({evento(x) for x in linhas}))
        registro["chaves_" + rotulo] = json.dumps([chave(x) for x in ordenadas])
        registro["n_" + rotulo] = len(linhas)
        registro["sha256_" + rotulo] = hashlib.sha256(
            json.dumps(
                ordenadas, sort_keys=True, ensure_ascii=False, allow_nan=False
            ).encode("utf8")
        ).hexdigest()
        registro["referencias_utc_" + rotulo] = json.dumps(
            sorted({x.get("limite_inferior_referencia_utc", "") for x in linhas})
        )
    return registro


def selecionar_temporal(treino, familia):
    """Escolhe por Brier médio de GP, sem tocar no fold externo."""
    ajuste, valid = dividir_selecao_temporal(treino)
    escolhas = []
    for nome, modelo, campos in candidatos(familia):
        modelo.fit(matriz(ajuste, campos), [x["podio"] for x in ajuste])
        prob = modelo.predict_proba(matriz(valid, campos))[:, 1]
        linhas = [
            {
                "temporada": x["temporada"],
                "rodada": x["rodada"],
                "podio": x["podio"],
                "probabilidade": p,
                "alvo_conhecido": 1,
            }
            for x, p in zip(valid, prob)
        ]
        escolhas.append(
            (
                sum(x["brier"] for x in brier_por_gp(linhas))
                / len(brier_por_gp(linhas)),
                nome,
                modelo,
                campos,
            )
        )
    _, nome, modelo, campos = sorted(escolhas, key=lambda x: (x[0], x[1]))[0]
    return nome, modelo, campos


def validar_destino(destino):
    destino = Path(destino).resolve()
    permitido = (RAIZ / "reports" / "modelo_v2_a_b1").resolve()
    if permitido not in destino.parents:
        raise ValueError("destino v2 fora de reports/modelo_v2_a_b1")
    return destino


def separar_previsao_e_metricas(linhas):
    """Todos elegíveis recebem previsão; somente alvos conhecidos são pontuados."""
    return list(linhas), [linha for linha in linhas if linha["alvo_conhecido"]]


def brier_por_gp(linhas):
    grupos = defaultdict(list)
    for linha in linhas:
        if linha["alvo_conhecido"] in (1, "1"):
            grupos[(int(linha["temporada"]), int(linha["rodada"]))].append(linha)
    saida = []
    for (temporada, rodada), grupo in sorted(grupos.items()):
        valores = [(float(x["probabilidade"]) - int(x["podio"])) ** 2 for x in grupo]
        saida.append(
            {
                "temporada": temporada,
                "rodada": rodada,
                "n": len(valores),
                "brier": sum(valores) / len(valores),
            }
        )
    return saida


@threadpool_limits.wrap(limits=1)
def executar_folds(linhas, modelos_dir):
    resultados = []
    previsoes = []
    selecoes = []
    for ano in (2022, 2023, 2024, 2025):
        treino = [x for x in linhas if x["temporada"] < ano and x["alvo_conhecido"]]
        teste, teste_metrica = separar_previsao_e_metricas(
            [x for x in linhas if x["temporada"] == ano]
        )
        y = [x["podio"] for x in treino]
        alvo = [x["podio"] for x in teste_metrica]
        constante = sum(y) / len(y)
        q = selecionar_temporal(treino, "q")
        a3 = selecionar_temporal(treino, "a3")
        completo = selecionar_temporal(treino, "completo")
        metodos = {
            "constante": None,
            "q_flexivel": q,
            "v1_replicado_temporal": (
                "v1_logistica_C1",
                modelo_v1_replicado(),
                V1_FEATURES,
            ),
            "a3_sem_q": a3,
            "q_a3_completo": completo,
        }
        for metodo, escolha in metodos.items():
            if escolha:
                selecoes.append(
                    registrar_selecao(
                        treino,
                        ano,
                        metodo,
                        escolha[0],
                        fixa=metodo == "v1_replicado_temporal",
                    )
                )
        for nome, objeto in metodos.items():
            if objeto is None:
                prob = [constante] * len(teste)
            else:
                _, model, campos = objeto
                model.fit(matriz(treino, campos), y)
                prob = model.predict_proba(matriz(teste, campos))[:, 1].tolist()
                joblib.dump(model, modelos_dir / "{}-{}.joblib".format(nome, ano))
            por_chave = {chave(linha): valor for linha, valor in zip(teste, prob)}
            m = metricas_probabilisticas(
                alvo, [por_chave[chave(linha)] for linha in teste_metrica]
            )
            resultados.append({"fold": ano, "metodo": nome, **m, "b1_cobertura": 0})
            previsoes.extend(
                {
                    "fold": ano,
                    "metodo": nome,
                    "temporada": x["temporada"],
                    "rodada": x["rodada"],
                    "piloto_id": x["piloto_id"],
                    "probabilidade": p,
                    "podio": x["podio"],
                    "alvo_conhecido": x["alvo_conhecido"],
                    "posicao_classificacao": x.get("posicao_classificacao"),
                }
                for x, p in zip(teste, prob)
            )
    return resultados, previsoes, selecoes


def executar(destino):
    destino = validar_destino(destino)
    if destino.exists() and any(destino.iterdir()):
        raise FileExistsError("destino v2 já existe e não está vazio")
    dados = destino / "data"
    modelos = destino / "models"
    dados.mkdir(parents=True)
    modelos.mkdir()
    base = carregar_csv(V1 / "base_historica.csv")
    linhas, janelas = construir_linhas_v2(base)
    aplicar_oraculo_entradas_v1(linhas)
    gravar_csv(
        dados / "features_v2.csv",
        [
            {k: v for k, v in x.items() if k not in ("podio", "alvo_conhecido")}
            for x in linhas
        ],
    )
    gravar_csv(
        dados / "alvos_v2.csv",
        [
            {
                "temporada": x["temporada"],
                "rodada": x["rodada"],
                "piloto_id": x["piloto_id"],
                "podio": x["podio"],
                "alvo_conhecido": x["alvo_conhecido"],
            }
            for x in linhas
        ],
    )
    (dados / "janelas_v2.json").write_text(
        json.dumps(janelas, ensure_ascii=False, indent=2), encoding="utf8"
    )
    fontes = [
        V1 / "base_historica.csv",
        V1 / "entradas.csv",
        V1 / "colunas.json",
        RAIZ / "docs/experimento_modelo_v2_a_b1.md",
        RAIZ / "executar_metodologia_v2.py",
        RAIZ / "metodologia_v2.py",
        RAIZ / "diagnosticos_v2.py",
    ]
    manifesto = {
        "schema": "metodologia-v2-v2",
        "gerado_em_utc": agora(),
        "fontes": [
            {
                "path": str(p.relative_to(RAIZ)),
                "sha256": sha256(p),
                "publicado_em_utc": None,
            }
            for p in fontes
        ],
        "b1": "indisponível nesta execução até leitura de snapshots FastF1 válidos",
    }
    import platform, sklearn

    manifesto["ambiente"] = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
        "joblib": joblib.__version__,
    }
    manifesto["configuracao"] = {
        "seed": 42,
        "threads_nativas": 1,
        "folds_externos": [2022, 2023, 2024, 2025],
        "calibracao_aprendida": False,
    }
    (dados / "manifesto_fontes_v2.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf8",
    )
    resultados, previsoes, selecoes = executar_folds(linhas, modelos)
    gravar_csv(destino / "metricas_folds.csv", resultados)
    gravar_csv(destino / "previsoes_fora_treino.csv", previsoes)
    gravar_csv(destino / "selecoes_temporais.csv", selecoes)
    from pitwall.research.diagnostics_v2 import gerar_diagnosticos

    diagnosticos = gerar_diagnosticos(previsoes)
    gravar_csv(destino / "metricas_por_gp.csv", diagnosticos["metricas_por_gp"])
    (destino / "diagnosticos.json").write_text(
        json.dumps(diagnosticos, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf8",
    )
    resumo = {
        "execucao_utc": agora(),
        "linhas_pre_corrida": len(linhas),
        "folds": [2022, 2023, 2024, 2025],
        "comparacoes_medidas": sorted({x["metodo"] for x in resultados}),
        "b1": "cobertura insuficiente: nenhuma sessão FastF1 validada foi integrada a esta execução",
        "resultados": resultados,
    }
    (destino / "resumo.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf8"
    )
    return resumo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destino", required=True)
    args = parser.parse_args()
    print(json.dumps(executar(args.destino), ensure_ascii=False))


if __name__ == "__main__":
    main()
