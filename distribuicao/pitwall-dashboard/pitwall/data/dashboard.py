"""Leitura e validação dos artefatos de apresentação do dashboard local."""

import csv
import hashlib
import io
import json
import math
from pathlib import Path


class DashboardDadosErro(ValueError):
    """Informa artefato inválido sem tentar corrigir a entrega."""


FONTES_POR_TEMPORADA = {
    2024: (
        "reports/modelo_v1/previsoes_validacao.csv",
        "reports/modelo_v1/avaliacao_corridas.csv",
        "reports/modelo_v1/metricas.json",
        "reports/modelo_v1/calibracao.csv",
    ),
    2025: (
        "reports/avaliacao_final_v1/previsoes_pre_corrida.csv",
        "reports/avaliacao_final_v1/avaliacao_por_piloto.csv",
        "reports/avaliacao_final_v1/avaliacao_corridas.csv",
        "reports/avaliacao_final_v1/metricas.json",
        "reports/avaliacao_final_v1/calibracao.csv",
    ),
}

CAMPOS_PREVISAO = (
    "temporada",
    "rodada",
    "piloto_id",
    "corrida",
    "data_corrida",
    "elegivel_previsao",
    "motivos_inelegibilidade",
    "probabilidade_modelo",
    "probabilidade_constante",
    "ranking_modelo",
    "favorito_modelo",
    "ranking_classificacao",
    "favorito_classificacao",
    "empates_modelo",
    "empates_classificacao",
)
CAMPOS_ALVO = ("alvo_conhecido", "podio")
CAMPOS_CORRIDA = (
    "temporada",
    "rodada",
    "corrida",
    "participantes_preparados",
    "elegiveis",
    "alvos_conhecidos",
    "podios_conhecidos",
    "avaliavel_ranking",
    "motivos_nao_avaliavel",
    "favoritos_modelo",
    "favoritos_classificacao",
    "podio_observado",
    "acertos_modelo",
    "acertos_classificacao",
)


def temporadas_disponiveis():
    return [2024, 2025]


def _erro(arquivo, mensagem):
    raise DashboardDadosErro(
        "{}: {}. Confira ou restaure a entrega verificada; o dashboard não gera nem corrige artefatos.".format(
            arquivo, mensagem
        )
    )


def _texto(valor, arquivo, campo):
    texto = str(valor).strip()
    if not texto:
        _erro(arquivo, "campo obrigatório vazio: {}".format(campo))
    return texto


def _inteiro(valor, arquivo, campo, minimo=None, permitir_vazio=False):
    texto = str(valor).strip()
    if not texto and permitir_vazio:
        return None
    if not texto or not texto.isdigit():
        _erro(
            arquivo,
            "{} deve ser inteiro{}".format(campo, " positivo" if minimo else ""),
        )
    numero = int(texto)
    if minimo is not None and numero < minimo:
        _erro(arquivo, "{} fora do intervalo permitido".format(campo))
    return numero


def _booleano(valor, arquivo, campo):
    texto = str(valor).strip()
    if texto not in ("0", "1"):
        _erro(arquivo, "{} deve ser 0 ou 1".format(campo))
    return texto == "1"


def _float_finito(valor, arquivo, campo, permitir_vazio=False):
    texto = str(valor).strip()
    if not texto and permitir_vazio:
        return None
    try:
        numero = float(texto)
    except (TypeError, ValueError):
        _erro(arquivo, "{} deve ser número finito".format(campo))
    if not math.isfinite(numero):
        _erro(arquivo, "{} deve ser número finito".format(campo))
    return numero


def _probabilidade(valor, arquivo, campo, permitir_vazio=False):
    numero = _float_finito(valor, arquivo, campo, permitir_vazio=permitir_vazio)
    if numero is not None and not 0.0 <= numero <= 1.0:
        _erro(arquivo, "{} fora do intervalo [0, 1]".format(campo))
    return numero


def _numero_json_finito(valor, arquivo, campo):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        _erro(arquivo, "{} deve ter tipo numérico real e finito".format(campo))
    if not math.isfinite(valor):
        _erro(arquivo, "{} deve ter tipo numérico real e finito".format(campo))
    return valor


def _inteiro_json(valor, arquivo, campo, minimo=None):
    if isinstance(valor, bool) or not isinstance(valor, int):
        _erro(arquivo, "{} deve ter tipo numérico inteiro".format(campo))
    if minimo is not None and valor < minimo:
        _erro(arquivo, "{} fora do intervalo permitido".format(campo))
    return valor


def _ler_csv(nome, conteudo, obrigatorios):
    try:
        texto = conteudo.decode("utf-8")
    except UnicodeDecodeError:
        _erro(nome, "CSV não está em UTF-8")
    try:
        linhas_brutas = list(csv.reader(io.StringIO(texto)))
    except csv.Error as erro:
        _erro(nome, "CSV inválido ({})".format(erro))
    if not linhas_brutas:
        _erro(nome, "CSV vazio")
    cabecalho = linhas_brutas[0]
    if not cabecalho or any(not campo.strip() for campo in cabecalho):
        _erro(nome, "cabeçalho inválido")
    if len(set(cabecalho)) != len(cabecalho):
        _erro(nome, "cabeçalho com coluna duplicada")
    faltantes = sorted(set(obrigatorios) - set(cabecalho))
    if faltantes:
        _erro(nome, "colunas obrigatórias ausentes: {}".format(", ".join(faltantes)))
    linhas = []
    for indice, valores in enumerate(linhas_brutas[1:], start=2):
        if not valores:
            continue
        if len(valores) != len(cabecalho):
            _erro(nome, "linha {} tem quantidade de colunas inválida".format(indice))
        linhas.append(dict(zip(cabecalho, valores)))
    if not linhas:
        _erro(nome, "CSV sem registros")
    return linhas


def _ler_json(nome, conteudo):
    try:
        valor = json.loads(conteudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        _erro(nome, "JSON inválido ({})".format(erro))
    if not isinstance(valor, dict):
        _erro(nome, "JSON deve conter objeto")
    return valor


def conteudos_temporada(raiz, temporada):
    if temporada not in FONTES_POR_TEMPORADA:
        raise ValueError("Temporada não suportada: {}".format(temporada))
    raiz = Path(raiz)
    conteudos = []
    for relativo in FONTES_POR_TEMPORADA[temporada]:
        caminho = raiz / relativo
        if not caminho.is_file():
            _erro(relativo, "arquivo ausente")
        try:
            conteudos.append((relativo, caminho.read_bytes()))
        except OSError as erro:
            _erro(relativo, "não foi possível ler ({})".format(erro))
    return tuple(conteudos)


def assinatura_conteudos(conteudos):
    resumo = hashlib.sha256()
    for nome, bytes_arquivo in conteudos:
        resumo.update(nome.encode("utf-8"))
        resumo.update(b"\0")
        resumo.update(bytes_arquivo)
        resumo.update(b"\0")
    return resumo.hexdigest()


def _chave(linha):
    return (linha["temporada"], linha["rodada"], linha["piloto_id"])


def _normalizar_previsoes(nome, linhas, temporada, com_alvos):
    esperados = set(CAMPOS_PREVISAO + (CAMPOS_ALVO if com_alvos else ()))
    normalizadas = []
    chaves = set()
    por_gp = {}
    for crua in linhas:
        faltantes = esperados - set(crua)
        if faltantes:
            _erro(
                nome,
                "colunas obrigatórias ausentes: {}".format(
                    ", ".join(sorted(faltantes))
                ),
            )
        linha = {
            "temporada": _inteiro(crua["temporada"], nome, "temporada", minimo=1),
            "rodada": _inteiro(crua["rodada"], nome, "rodada", minimo=1),
            "piloto_id": _texto(crua["piloto_id"], nome, "piloto_id"),
            "corrida": _texto(crua["corrida"], nome, "corrida"),
            "data_corrida": _texto(crua["data_corrida"], nome, "data_corrida"),
            "elegivel_previsao": _booleano(
                crua["elegivel_previsao"], nome, "elegivel_previsao"
            ),
            "motivos_inelegibilidade": str(crua["motivos_inelegibilidade"]).strip(),
            "empates_modelo": str(crua["empates_modelo"]).strip(),
            "empates_classificacao": str(crua["empates_classificacao"]).strip(),
        }
        if linha["temporada"] != temporada:
            _erro(nome, "temporada divergente: {}".format(linha["temporada"]))
        chave = _chave(linha)
        if chave in chaves:
            _erro(nome, "chave duplicada: {}".format(chave))
        chaves.add(chave)
        if linha["elegivel_previsao"]:
            if linha["motivos_inelegibilidade"]:
                _erro(nome, "elegível não pode ter motivo de inelegibilidade")
            for campo in ("probabilidade_modelo", "probabilidade_constante"):
                linha[campo] = _probabilidade(crua[campo], nome, campo)
            for campo in ("ranking_modelo", "ranking_classificacao"):
                linha[campo] = _inteiro(crua[campo], nome, campo, minimo=1)
            for campo in ("favorito_modelo", "favorito_classificacao"):
                linha[campo] = _booleano(crua[campo], nome, campo)
        else:
            if not linha["motivos_inelegibilidade"]:
                _erro(nome, "inelegível sem motivo")
            for campo in ("probabilidade_modelo", "probabilidade_constante"):
                if str(crua[campo]).strip():
                    _erro(nome, "inelegível não pode ter {}".format(campo))
                linha[campo] = None
            for campo in ("ranking_modelo", "ranking_classificacao"):
                if str(crua[campo]).strip():
                    _erro(nome, "inelegível não pode ter {}".format(campo))
                linha[campo] = None
            for campo in ("favorito_modelo", "favorito_classificacao"):
                if str(crua[campo]).strip() not in ("", "0"):
                    _erro(nome, "inelegível não pode ser {}".format(campo))
                linha[campo] = False
        if com_alvos:
            linha["alvo_conhecido"] = _booleano(
                crua["alvo_conhecido"], nome, "alvo_conhecido"
            )
            alvo = str(crua["podio"]).strip()
            if linha["alvo_conhecido"]:
                linha["podio"] = _inteiro(alvo, nome, "podio", minimo=0)
                if linha["podio"] not in (0, 1):
                    _erro(nome, "podio deve ser 0 ou 1")
            else:
                if alvo:
                    _erro(nome, "alvo desconhecido deve permanecer vazio")
                linha["podio"] = None
        por_gp.setdefault((linha["temporada"], linha["rodada"]), []).append(linha)
        normalizadas.append(linha)
    for chave_gp, participantes in por_gp.items():
        corridas = {item["corrida"] for item in participantes}
        datas = {item["data_corrida"] for item in participantes}
        if len(corridas) != 1 or len(datas) != 1:
            _erro(nome, "GP {} tem nome ou data inconsistentes".format(chave_gp))
        elegiveis = [item for item in participantes if item["elegivel_previsao"]]
        for ranking, favorito in (
            ("ranking_modelo", "favorito_modelo"),
            ("ranking_classificacao", "favorito_classificacao"),
        ):
            ranks = [item[ranking] for item in elegiveis]
            if len(ranks) != len(set(ranks)):
                _erro(nome, "{} duplicado no GP {}".format(ranking, chave_gp))
            esperado = list(range(1, len(elegiveis) + 1))
            if sorted(ranks) != esperado:
                _erro(
                    nome,
                    "{} deve cobrir ranks elegíveis no GP {}".format(ranking, chave_gp),
                )
            for item in elegiveis:
                if item[favorito] != (item[ranking] <= 3):
                    _erro(nome, "{} incoerente com {}".format(favorito, ranking))
        ordenados_por_probabilidade = sorted(
            elegiveis,
            key=lambda item: (-item["probabilidade_modelo"], item["piloto_id"]),
        )
        if any(
            item["ranking_modelo"] != indice
            for indice, item in enumerate(ordenados_por_probabilidade, start=1)
        ):
            _erro(
                nome,
                "ranking_modelo incompatível com probabilidade decrescente e desempate por piloto_id no GP {}".format(
                    chave_gp
                ),
            )
    return normalizadas


def _juntar_alvos(nome, previsoes, avaliacao):
    por_chave = {_chave(linha): linha for linha in avaliacao}
    if set(map(_chave, previsoes)) != set(por_chave):
        _erro(
            nome,
            "chaves de avaliação por piloto não coincidem com as previsões pré-corrida",
        )
    resultado = []
    for previsao in previsoes:
        avaliada = por_chave[_chave(previsao)]
        for campo in CAMPOS_PREVISAO:
            if campo in ("alvo_conhecido", "podio"):
                continue
            if previsao[campo] != avaliada[campo]:
                _erro(nome, "valor pré-corrida divergente em {}".format(campo))
        mesclada = dict(previsao)
        mesclada["alvo_conhecido"] = avaliada["alvo_conhecido"]
        mesclada["podio"] = avaliada["podio"]
        resultado.append(mesclada)
    return resultado


def _separar_ids(valor):
    texto = str(valor).strip()
    if not texto:
        return []
    itens = texto.split(";")
    if any(not item for item in itens) or len(set(itens)) != len(itens):
        return None
    return itens


def _normalizar_corridas(nome, linhas, temporada, previsoes):
    if set(CAMPOS_CORRIDA) - set(linhas[0]):
        _erro(nome, "colunas obrigatórias ausentes")
    por_gp = {}
    for item in previsoes:
        por_gp.setdefault((item["temporada"], item["rodada"]), []).append(item)
    corridas = []
    chaves = set()
    for crua in linhas:
        linha = {
            "temporada": _inteiro(crua["temporada"], nome, "temporada", minimo=1),
            "rodada": _inteiro(crua["rodada"], nome, "rodada", minimo=1),
            "corrida": _texto(crua["corrida"], nome, "corrida"),
            "participantes_preparados": _inteiro(
                crua["participantes_preparados"],
                nome,
                "participantes_preparados",
                minimo=1,
            ),
            "elegiveis": _inteiro(crua["elegiveis"], nome, "elegiveis", minimo=0),
            "alvos_conhecidos": _inteiro(
                crua["alvos_conhecidos"], nome, "alvos_conhecidos", minimo=0
            ),
            "podios_conhecidos": _inteiro(
                crua["podios_conhecidos"], nome, "podios_conhecidos", minimo=0
            ),
            "avaliavel_ranking": _booleano(
                crua["avaliavel_ranking"], nome, "avaliavel_ranking"
            ),
            "motivos_nao_avaliavel": str(crua["motivos_nao_avaliavel"]).strip(),
        }
        if linha["temporada"] != temporada:
            _erro(nome, "temporada divergente")
        chave = (linha["temporada"], linha["rodada"])
        if chave in chaves:
            _erro(nome, "GP duplicado: {}".format(chave))
        chaves.add(chave)
        participantes = por_gp.get(chave)
        if participantes is None:
            _erro(nome, "GP sem previsões correspondentes: {}".format(chave))
        if linha["corrida"] != participantes[0]["corrida"]:
            _erro(nome, "nome de GP divergente")
        esperados = {
            "participantes_preparados": len(participantes),
            "elegiveis": sum(item["elegivel_previsao"] for item in participantes),
            "alvos_conhecidos": sum(item["alvo_conhecido"] for item in participantes),
            "podios_conhecidos": sum(item["podio"] == 1 for item in participantes),
        }
        for campo, esperado in esperados.items():
            if linha[campo] != esperado:
                _erro(nome, "{} inconsistente com previsões".format(campo))
        for campo in ("favoritos_modelo", "favoritos_classificacao", "podio_observado"):
            ids = _separar_ids(crua[campo])
            if ids is None:
                _erro(nome, "{} inválido".format(campo))
            linha[campo] = ids
        for campo in ("acertos_modelo", "acertos_classificacao"):
            linha[campo] = _inteiro(
                crua[campo], nome, campo, minimo=0, permitir_vazio=True
            )
            if linha[campo] is not None and linha[campo] > 3:
                _erro(nome, "{} fora do intervalo 0..3".format(campo))
        favoritos_modelo = [
            item["piloto_id"]
            for item in sorted(
                participantes,
                key=lambda item: (item["ranking_modelo"] or 9999, item["piloto_id"]),
            )
            if item["favorito_modelo"]
        ]
        favoritos_classificacao = [
            item["piloto_id"]
            for item in sorted(
                participantes,
                key=lambda item: (
                    item["ranking_classificacao"] or 9999,
                    item["piloto_id"],
                ),
            )
            if item["favorito_classificacao"]
        ]
        if set(linha["favoritos_modelo"]) != set(favoritos_modelo) or set(
            linha["favoritos_classificacao"]
        ) != set(favoritos_classificacao):
            _erro(nome, "favoritos não coincidem com rankings publicados")
        positivos = sorted(
            item["piloto_id"] for item in participantes if item["podio"] == 1
        )
        if linha["avaliavel_ranking"]:
            if linha["motivos_nao_avaliavel"]:
                _erro(nome, "GP avaliável com motivo")
            if len(positivos) != 3 or sorted(linha["podio_observado"]) != positivos:
                _erro(nome, "pódio observado não coincide com alvos conhecidos")
            if linha["acertos_modelo"] != len(set(favoritos_modelo) & set(positivos)):
                _erro(nome, "acertos_modelo inconsistente")
            if linha["acertos_classificacao"] != len(
                set(favoritos_classificacao) & set(positivos)
            ):
                _erro(nome, "acertos_classificacao inconsistente")
        else:
            if not linha["motivos_nao_avaliavel"]:
                _erro(nome, "GP não avaliável sem motivo")
            if (
                linha["acertos_modelo"] is not None
                or linha["acertos_classificacao"] is not None
            ):
                _erro(nome, "GP não avaliável não pode receber acertos")
            if linha["podio_observado"]:
                _erro(nome, "GP não avaliável deve manter pódio_observado vazio")
        corridas.append(linha)
    if set(por_gp) != chaves:
        _erro(nome, "conjuntos de GPs não coincidem com previsões")
    return sorted(corridas, key=lambda item: item["rodada"])


def _validar_metricas(nome, metricas, temporada, previsoes, corridas):
    for bloco in (
        "cobertura",
        "probabilisticas",
        "ranking_modelo",
        "ranking_classificacao",
    ):
        if not isinstance(metricas.get(bloco), dict):
            _erro(nome, "bloco ausente ou inválido: {}".format(bloco))
    cobertura = metricas["cobertura"]
    total = len(previsoes)
    esperado = {
        "gps_total": len(corridas),
        "gps_avaliaveis_ranking": sum(item["avaliavel_ranking"] for item in corridas),
        "linhas_elegiveis": sum(item["elegivel_previsao"] for item in previsoes),
        "linhas_inelegiveis": sum(not item["elegivel_previsao"] for item in previsoes),
        "linhas_com_alvo_conhecido": sum(item["alvo_conhecido"] for item in previsoes),
        "linhas_alvo_desconhecido": sum(
            not item["alvo_conhecido"] for item in previsoes
        ),
    }
    esperado["linhas_validacao" if temporada == 2024 else "linhas_teste"] = total
    for campo, valor in esperado.items():
        if (
            _inteiro_json(
                cobertura.get(campo), nome, "cobertura.{}".format(campo), minimo=0
            )
            != valor
        ):
            _erro(nome, "cobertura inconsistente em {}".format(campo))
    probabilisticas = metricas["probabilisticas"]
    linhas_prob = sum(
        item["elegivel_previsao"] and item["alvo_conhecido"] for item in previsoes
    )
    if (
        _inteiro_json(
            probabilisticas.get("linhas_avaliaveis"),
            nome,
            "probabilisticas.linhas_avaliaveis",
            minimo=0,
        )
        != linhas_prob
    ):
        _erro(nome, "denominador probabilístico inconsistente")
    for metodo in ("modelo", "constante"):
        valores = probabilisticas.get(metodo)
        if not isinstance(valores, dict):
            _erro(nome, "métricas ausentes para {}".format(metodo))
        for campo in ("log_loss", "brier"):
            numero = _numero_json_finito(
                valores.get(campo), nome, "{}.{}".format(metodo, campo)
            )
            if numero < 0:
                _erro(nome, "{}.{} não pode ser negativo".format(metodo, campo))
    avaliaveis = sum(item["avaliavel_ranking"] for item in corridas)
    for bloco in ("ranking_modelo", "ranking_classificacao"):
        valores = metricas[bloco]
        if (
            _inteiro_json(
                valores.get("corridas_avaliaveis"),
                nome,
                "{}.corridas_avaliaveis".format(bloco),
                minimo=0,
            )
            != avaliaveis
        ):
            _erro(nome, "{} com denominador de GP inconsistente".format(bloco))
        media = _numero_json_finito(
            valores.get("media_integrantes_corretos"),
            nome,
            "{}.media_integrantes_corretos".format(bloco),
        )
        proporcao = _numero_json_finito(
            valores.get("proporcao_3_corretos"),
            nome,
            "{}.proporcao_3_corretos".format(bloco),
        )
        if not 0 <= proporcao <= 1:
            _erro(
                nome, "{}.proporcao_3_corretos fora do intervalo [0, 1]".format(bloco)
            )
        distribuicao = valores.get("distribuicao_0_1_2_3")
        if not isinstance(distribuicao, dict):
            _erro(nome, "{} sem distribuição".format(bloco))
        contagens = []
        for valor in range(4):
            contagens.append(
                _inteiro_json(
                    distribuicao.get(str(valor)),
                    nome,
                    "{}.distribuicao_0_1_2_3.{}".format(bloco, valor),
                    minimo=0,
                )
            )
        if sum(contagens) != avaliaveis or not 0 <= media <= 3:
            _erro(nome, "{} com distribuição ou média inconsistente".format(bloco))
        if avaliaveis and not math.isclose(
            proporcao, contagens[3] / avaliaveis, rel_tol=0, abs_tol=1e-12
        ):
            _erro(
                nome, "{} com proporção de pódios completos inconsistente".format(bloco)
            )
        campo_acertos = (
            "acertos_modelo" if bloco == "ranking_modelo" else "acertos_classificacao"
        )
        acertos_publicados = [
            item[campo_acertos] for item in corridas if item["avaliavel_ranking"]
        ]
        distribuicao_publicada = [acertos_publicados.count(valor) for valor in range(4)]
        if contagens != distribuicao_publicada:
            _erro(
                nome,
                "{} com distribuição divergente dos acertos por GP publicados".format(
                    bloco
                ),
            )
        if avaliaveis:
            media_publicada = sum(acertos_publicados) / avaliaveis
            if not math.isclose(media, media_publicada, rel_tol=0, abs_tol=1e-12):
                _erro(
                    nome,
                    "{} com média divergente dos acertos por GP publicados".format(
                        bloco
                    ),
                )


def _normalizar_calibracao(nome, linhas, linhas_probabilisticas):
    obrigatorios = {
        "metodo",
        "faixa",
        "limite_inferior",
        "limite_superior",
        "contagem",
        "media_prevista",
        "frequencia_observada",
    }
    if obrigatorios - set(linhas[0]):
        _erro(nome, "colunas obrigatórias ausentes")
    if len(linhas) != 20:
        _erro(nome, "calibração deve conter 20 linhas")
    resultado = []
    por_metodo = {"modelo": [], "constante": []}
    for crua in linhas:
        metodo = str(crua["metodo"]).strip()
        if metodo not in por_metodo:
            _erro(nome, "método de calibração inválido")
        inferior = _probabilidade(crua["limite_inferior"], nome, "limite_inferior")
        superior = _probabilidade(crua["limite_superior"], nome, "limite_superior")
        assert inferior is not None and superior is not None
        contagem = _inteiro(crua["contagem"], nome, "contagem", minimo=0)
        media = _probabilidade(
            crua["media_prevista"], nome, "media_prevista", permitir_vazio=True
        )
        frequencia = _probabilidade(
            crua["frequencia_observada"],
            nome,
            "frequencia_observada",
            permitir_vazio=True,
        )
        if not inferior < superior:
            _erro(nome, "faixa de calibração inválida")
        if contagem == 0 and (media is not None or frequencia is not None):
            _erro(nome, "faixa vazia deve preservar valores indefinidos")
        if contagem > 0 and (media is None or frequencia is None):
            _erro(nome, "faixa preenchida sem média ou frequência")
        faixa = str(crua["faixa"]).strip()
        faixa_esperada = "[{:.1f},{:.1f}{}".format(
            inferior,
            superior,
            "]" if math.isclose(superior, 1.0, abs_tol=1e-9) else ")",
        )
        if faixa != faixa_esperada:
            _erro(nome, "faixa de calibração incompatível com seus limites")
        linha = {
            "metodo": metodo,
            "faixa": faixa,
            "limite_inferior": inferior,
            "limite_superior": superior,
            "contagem": contagem,
            "media_prevista": media,
            "frequencia_observada": frequencia,
        }
        por_metodo[metodo].append(linha)
        resultado.append(linha)
    for metodo, faixas in por_metodo.items():
        if len(faixas) != 10:
            _erro(nome, "{} deve ter dez faixas".format(metodo))
        faixas.sort(key=lambda item: item["limite_inferior"])
        if len({item["faixa"] for item in faixas}) != len(faixas):
            _erro(nome, "{} tem faixa de calibração duplicada".format(metodo))
        for indice, faixa in enumerate(faixas):
            if not math.isclose(
                faixa["limite_inferior"], indice / 10, abs_tol=1e-9
            ) or not math.isclose(
                faixa["limite_superior"], (indice + 1) / 10, abs_tol=1e-9
            ):
                _erro(nome, "{} tem faixas não uniformes".format(metodo))
        if sum(item["contagem"] for item in faixas) != linhas_probabilisticas:
            _erro(nome, "{} com denominador inconsistente".format(metodo))
    referencia = [
        (item["limite_inferior"], item["limite_superior"], item["faixa"])
        for item in por_metodo["modelo"]
    ]
    constante = [
        (item["limite_inferior"], item["limite_superior"], item["faixa"])
        for item in por_metodo["constante"]
    ]
    if referencia != constante:
        _erro(nome, "faixas de calibração incoerentes entre métodos")
    return resultado


def carregar_temporada_de_conteudos(temporada, conteudos):
    esperados = FONTES_POR_TEMPORADA.get(temporada)
    if esperados is None:
        raise ValueError("Temporada não suportada: {}".format(temporada))
    recebidos = dict(conteudos)
    if set(recebidos) != set(esperados):
        faltantes = sorted(set(esperados) - set(recebidos))
        _erro(
            ", ".join(faltantes) if faltantes else "artefatos",
            "conjunto de fontes inválido",
        )
    if temporada == 2024:
        previsoes_nome, corridas_nome, metricas_nome, calibracao_nome = esperados
        previsoes = _normalizar_previsoes(
            previsoes_nome,
            _ler_csv(
                previsoes_nome, recebidos[previsoes_nome], CAMPOS_PREVISAO + CAMPOS_ALVO
            ),
            2024,
            True,
        )
    else:
        (
            previsoes_nome,
            avaliacao_nome,
            corridas_nome,
            metricas_nome,
            calibracao_nome,
        ) = esperados
        previsoes_pre = _normalizar_previsoes(
            previsoes_nome,
            _ler_csv(previsoes_nome, recebidos[previsoes_nome], CAMPOS_PREVISAO),
            2025,
            False,
        )
        avaliacao = _normalizar_previsoes(
            avaliacao_nome,
            _ler_csv(
                avaliacao_nome, recebidos[avaliacao_nome], CAMPOS_PREVISAO + CAMPOS_ALVO
            ),
            2025,
            True,
        )
        previsoes = _juntar_alvos(avaliacao_nome, previsoes_pre, avaliacao)
    corridas = _normalizar_corridas(
        corridas_nome,
        _ler_csv(corridas_nome, recebidos[corridas_nome], CAMPOS_CORRIDA),
        temporada,
        previsoes,
    )
    metricas = _ler_json(metricas_nome, recebidos[metricas_nome])
    _validar_metricas(metricas_nome, metricas, temporada, previsoes, corridas)
    linhas_probabilisticas = metricas["probabilisticas"]["linhas_avaliaveis"]
    calibracao = _normalizar_calibracao(
        calibracao_nome,
        _ler_csv(calibracao_nome, recebidos[calibracao_nome], ("metodo", "faixa")),
        linhas_probabilisticas,
    )
    return {
        "temporada": temporada,
        "previsoes": sorted(
            previsoes, key=lambda item: (item["rodada"], item["piloto_id"])
        ),
        "corridas": corridas,
        "metricas": metricas,
        "calibracao": calibracao,
        "assinatura": assinatura_conteudos(conteudos),
    }


def carregar_temporada(raiz, temporada):
    return carregar_temporada_de_conteudos(
        temporada, conteudos_temporada(raiz, temporada)
    )


def opcoes_gps(pacote):
    return [
        {
            "rodada": corrida["rodada"],
            "corrida": corrida["corrida"],
            "valor": "{}:{}".format(pacote["temporada"], corrida["rodada"]),
        }
        for corrida in sorted(pacote["corridas"], key=lambda item: item["rodada"])
    ]


def dados_do_gp(pacote, rodada):
    rodada = int(rodada)
    corrida = next(
        (item for item in pacote["corridas"] if item["rodada"] == rodada), None
    )
    if corrida is None:
        raise ValueError("Rodada não encontrada: {}".format(rodada))
    participantes = [item for item in pacote["previsoes"] if item["rodada"] == rodada]
    participantes.sort(
        key=lambda item: (
            not item["elegivel_previsao"],
            item["ranking_modelo"] or 9999,
            item["piloto_id"],
        )
    )
    favoritos_modelo = sorted(
        (item for item in participantes if item["favorito_modelo"]),
        key=lambda item: (item["ranking_modelo"], item["piloto_id"]),
    )
    favoritos_classificacao = sorted(
        (item for item in participantes if item["favorito_classificacao"]),
        key=lambda item: (item["ranking_classificacao"], item["piloto_id"]),
    )
    integrantes_identificados = sorted(
        item["piloto_id"] for item in participantes if item["podio"] == 1
    )
    return {
        "corrida": corrida,
        "participantes": participantes,
        "favoritos_modelo": favoritos_modelo,
        "favoritos_classificacao": favoritos_classificacao,
        "integrantes_identificados": integrantes_identificados,
    }
