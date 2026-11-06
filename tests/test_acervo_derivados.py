import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from acervo_derivados import gerar_derivados


class AcervoDerivadosTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        (self.raiz / "local").mkdir()
        self.evento = {"temporada":2024, "rodada":1, "circuito_id":"bahrain",
                       "data_corrida":"2024-03-02", "sessoes_calendario":{"Sprint":{}}}
        self.gravar("local/eventos.json", [self.evento])
        self.fontes = []
        self.adicionar("sessions", [self.sessao(100, "Race", "Race"),
                                   self.sessao(101, "Sprint", "Race"),
                                   self.sessao(99, "Qualifying", "Qualifying")], anual=True)
        self.gravar("mapeamento_sessoes.json", [dict(self.evento, session_key=n, meeting_key=10)
                                                for n in (99,100,101)])

    def sessao(self, numero, nome, tipo):
        return {"session_key":numero, "meeting_key":10, "year":2024,
                "session_name":nome, "session_type":tipo,
                "date_start":"2024-03-02T12:00:00+00:00",
                "date_end":"2024-03-02T14:00:00+00:00"}

    def gravar(self, relativo, dados):
        arquivo = self.raiz / relativo
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(json.dumps(dados), encoding="utf-8")
        return arquivo

    def adicionar(self, endpoint, rows, anual=False, provider="openf1", **extras):
        relativo = "raw/{}-{}.json".format(endpoint, len(self.fontes))
        arquivo = self.gravar(relativo, rows)
        fonte = {"provider":provider, "endpoint":endpoint, "temporada":2024,
                 "arquivo":relativo, "sha256":hashlib.sha256(arquivo.read_bytes()).hexdigest(),
                 "status":200, "url":"https://example.test/" + endpoint,
                 "obtido_em_utc":"2026-10-27T12:00:00Z"}
        if not anual:
            fonte.update(rodada=1, circuito_id="bahrain", meeting_key=10)
        fonte.update(extras)
        self.fontes.append(fonte)
        self.gravar("coleta_online.json", {"fontes":self.fontes})
        return fonte

    def pilotos(self, sessoes=(99,100,101), numero=4, team="Equipe nativa"):
        self.adicionar("drivers", [{"session_key":n, "meeting_key":10, "driver_number":numero,
                                    "team_name":team, "full_name":"Nome aproximado"} for n in sessoes], anual=True)

    def local(self, nome, rows):
        campos = sorted({key for row in rows for key in row})
        with (self.raiz / "local" / nome).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=campos)
            writer.writeheader()
            writer.writerows(rows)

    def csv(self, nome):
        with (self.raiz / "normalizado" / (nome + ".csv")).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_tempos_preservam_duration_array_nulo_zero_e_gap_textual(self):
        self.pilotos()
        self.adicionar("session_result", [
            {"session_key":99, "meeting_key":10, "driver_number":4, "position":1,
             "duration":[90.2, None, 0], "gap_to_leader":[0, None, "+1 LAP"]},
            {"session_key":100, "meeting_key":10, "driver_number":4, "position":2,
             "duration":None, "gap_to_leader":"+1 LAP"}], anual=True)
        gerar_derivados(self.raiz)
        rows = self.csv("tempos_sessoes")
        self.assertEqual(json.loads(rows[0]["duration_original_json"]), [90.2,None,0])
        self.assertEqual(json.loads(rows[1]["duration_original_json"]), None)
        self.assertEqual(json.loads(rows[1]["gap_to_leader_original_json"]), "+1 LAP")
        self.assertEqual(rows[0]["piloto_id"], "")
        self.assertEqual(rows[0]["identidade_piloto"], "openf1:99:4")

    def test_identidade_exige_numero_literal_no_mesmo_gp(self):
        self.pilotos()
        self.local("resultados.csv", [dict(self.evento, piloto_id="piloto_canonico", equipe_id="equipe_canonica",
                                          numero=5, piloto="Nome aproximado", pontos=0, posicao_final=1)])
        self.adicionar("laps", [{"session_key":100, "meeting_key":10, "driver_number":4, "lap_number":1,
                                 "lap_duration":None, "is_pit_out_lap":False}], anual=True)
        gerar_derivados(self.raiz)
        row = self.csv("laps_sessoes")[0]
        self.assertEqual(row["piloto_id"], "")
        self.assertEqual(row["equipe_id"], "")
        self.assertEqual(row["team_name_openf1"], "Equipe nativa")
        self.assertEqual(row["lap_duration"], "")
        self.assertEqual(row["is_pit_out_lap"], "False")

    def test_identidade_canonica_numero_no_gp_preserva_equipe_nativa(self):
        self.pilotos()
        self.local("resultados.csv", [dict(self.evento, piloto_id="canonico", equipe_id="equipe_id",
                                          numero=4, pontos=0, posicao_final=1)])
        self.adicionar("session_result", [{"session_key":100, "meeting_key":10,
                                            "driver_number":4, "duration":0}], anual=True)
        gerar_derivados(self.raiz)
        row = self.csv("tempos_sessoes")[0]
        self.assertEqual(row["piloto_id"], "canonico")
        self.assertEqual(row["equipe_id"], "equipe_id")
        self.assertEqual(row["team_name_openf1"], "Equipe nativa")
        self.assertEqual(row["duration_original_json"], "0")

    def test_sem_endpoint_drivers_mantem_chave_nativa_e_equipe_ausente(self):
        self.adicionar("laps", [{"session_key":100, "meeting_key":10, "driver_number":4,
                                 "lap_number":1}], anual=True)
        gerar_derivados(self.raiz)
        row = self.csv("laps_sessoes")[0]
        self.assertEqual(row["identidade_piloto"], "openf1:100:4")
        self.assertEqual(row["team_name_openf1"], "")
        cobertura = next(r for r in self.csv("cobertura") if r["tipo"] == "pilotos_openf1")
        self.assertEqual(cobertura["estado"], "indisponivel")

    def test_receipts_por_gp_funcionam_sem_mapeamento_arquivo(self):
        (self.raiz / "mapeamento_sessoes.json").unlink()
        self.adicionar("drivers", [{"session_key":100, "meeting_key":10, "driver_number":4,
                                    "team_name":"Equipe nativa"}])
        self.adicionar("laps", [{"session_key":100, "meeting_key":10, "driver_number":4,
                                 "lap_number":1}])
        gerar_derivados(self.raiz)
        self.assertEqual(self.csv("laps_sessoes")[0]["team_name_openf1"], "Equipe nativa")
        self.assertEqual(self.csv("pilotos_sessoes")[0]["identidade_piloto"], "openf1:100:4")

    def test_hash_e_fontes_incompletas_falham_antes_de_escrever(self):
        fonte = self.fontes[0]
        (self.raiz / fonte["arquivo"]).write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash"):
            gerar_derivados(self.raiz)
        self.assertFalse((self.raiz / "normalizado").exists())
        fonte["sha256"] = hashlib.sha256(b"[]").hexdigest()
        del fonte["obtido_em_utc"]
        self.gravar("coleta_online.json", {"fontes":self.fontes})
        with self.assertRaisesRegex(ValueError, "incompleta"):
            gerar_derivados(self.raiz)

    def test_duplicata_de_volta_ou_piloto_local_e_rejeitada(self):
        self.pilotos()
        lap = {"session_key":100, "meeting_key":10, "driver_number":4, "lap_number":1}
        self.adicionar("laps", [lap, lap], anual=True)
        with self.assertRaisesRegex(ValueError, "volta duplicado"):
            gerar_derivados(self.raiz)
        self.fontes.pop()
        self.gravar("coleta_online.json", {"fontes":self.fontes})
        row = dict(self.evento, piloto_id="canonico", numero=4)
        self.local("resultados.csv", [row, row])
        with self.assertRaisesRegex(ValueError, "piloto local duplicado"):
            gerar_derivados(self.raiz)

    def test_conflito_de_gp_no_raw_e_rejeitado(self):
        self.pilotos()
        self.adicionar("laps", [{"session_key":100, "meeting_key":11, "driver_number":4, "lap_number":1}], anual=True)
        with self.assertRaisesRegex(ValueError, "meeting_key conflitante"):
            gerar_derivados(self.raiz)

    def test_linhas_anuais_sem_mapeamento_sao_contadas_e_excluidas(self):
        self.pilotos(sessoes=(100,777))
        fonte = self.adicionar("laps", [{"session_key":100, "meeting_key":10, "driver_number":4, "lap_number":1},
                                         {"session_key":777, "meeting_key":77, "driver_number":4, "lap_number":1}], anual=True)
        resultado = gerar_derivados(self.raiz)
        self.assertEqual(len(self.csv("laps_sessoes")), 1)
        self.assertEqual(resultado["excluidos_raw_sem_mapeamento"][fonte["arquivo"]], 1)

    def test_stints_ordenados_e_sprint_separada_sem_inferir_troca_por_pit(self):
        self.pilotos()
        self.adicionar("stints", [
            {"session_key":100, "meeting_key":10, "driver_number":4, "stint_number":2,
             "lap_start":11, "lap_end":20, "compound":"HARD", "tyre_age_at_start":0},
            {"session_key":101, "meeting_key":10, "driver_number":4, "stint_number":1,
             "lap_start":1, "lap_end":9, "compound":None, "tyre_age_at_start":None},
            {"session_key":100, "meeting_key":10, "driver_number":4, "stint_number":1,
             "lap_start":1, "lap_end":10, "compound":"MEDIUM", "tyre_age_at_start":2}], anual=True)
        self.adicionar("pit", [{"session_key":100, "meeting_key":10, "driver_number":4,
                                "date":"2024-03-02T12:20:00Z", "lap_number":15, "pit_duration":0}], anual=True)
        gerar_derivados(self.raiz)
        rows = self.csv("estrategias_pneus")
        self.assertEqual(len(rows), 2)
        race = next(r for r in rows if r["session_name"] == "Race")
        sprint = next(r for r in rows if r["session_name"] == "Sprint")
        self.assertEqual(json.loads(race["compostos_observados_json"]), ["MEDIUM", "HARD"])
        self.assertEqual(json.loads(race["sequencia_stints_json"])[1]["tyre_age_at_start"], 0)
        self.assertEqual(json.loads(sprint["sequencia_stints_json"])[0]["compound"], None)
        self.assertEqual(race["n_stints_observados"], "2")

    def test_fronteira_compartilhada_preservada_com_flag_sem_somar_voltas(self):
        self.pilotos()
        self.adicionar("stints", [
            {"session_key":100, "meeting_key":10, "driver_number":4, "stint_number":1, "lap_start":1, "lap_end":10},
            {"session_key":100, "meeting_key":10, "driver_number":4, "stint_number":2, "lap_start":10, "lap_end":20}], anual=True)
        gerar_derivados(self.raiz)
        estrategia = self.csv("estrategias_pneus")[0]
        self.assertIn("fronteira_compartilhada_na_fonte", estrategia["qualidade_limites_json"])
        self.assertEqual(json.loads(estrategia["sequencia_stints_json"])[1]["lap_start"], 10)
        self.assertNotIn("n_voltas", estrategia)

    def test_intervalos_invertidos_ou_sobrepostos_sao_contexto_de_qualidade(self):
        self.pilotos()
        self.adicionar("stints", [
            {"session_key":100, "meeting_key":10, "driver_number":4, "stint_number":1, "lap_start":1, "lap_end":15},
            {"session_key":100, "meeting_key":10, "driver_number":4, "stint_number":2, "lap_start":10, "lap_end":9}], anual=True)
        gerar_derivados(self.raiz)
        stints = self.csv("stints")
        self.assertEqual(stints[1]["lap_end"], "9")
        self.assertIn("lap_end_anterior_lap_start_na_fonte", stints[1]["qualidade_limites_json"])
        estrategia = self.csv("estrategias_pneus")[0]
        self.assertIn("intervalos_sobrepostos_na_fonte", estrategia["qualidade_limites_json"])
        self.assertEqual(estrategia["limites_voltas_comparaveis"], "False")

    def test_limites_de_stint_nulos_e_zero_preservados_com_cobertura_parcial(self):
        self.pilotos()
        limites = [(None,None), (0,0), (1,0), (10,20)]
        self.adicionar("stints", [dict(session_key=100, meeting_key=10, driver_number=4,
                                      stint_number=n, lap_start=inicio, lap_end=fim,
                                      compound="MEDIUM", tyre_age_at_start=0)
                                  for n, (inicio,fim) in enumerate(limites, 1)], anual=True)
        self.adicionar("laps", [{"session_key":100, "meeting_key":10, "driver_number":4,
                                 "lap_number":1, "lap_duration":90.0}], anual=True)
        gerar_derivados(self.raiz)
        stints = self.csv("stints")
        self.assertEqual([(r["lap_start"],r["lap_end"]) for r in stints],
                         [("",""), ("0","0"), ("1","0"), ("10","20")])
        self.assertEqual([r["limites_voltas_comparaveis"] for r in stints],
                         ["False","False","False","True"])
        self.assertIn("lap_start_ausente", json.loads(stints[0]["qualidade_limites_json"]))
        self.assertIn("lap_end_zero_na_fonte", json.loads(stints[2]["qualidade_limites_json"]))
        estrategia = self.csv("estrategias_pneus")[0]
        self.assertEqual(estrategia["n_stints_observados"], "4")
        self.assertEqual(estrategia["n_stints_limites_incompletos"], "3")
        self.assertEqual(estrategia["tem_lacunas_entre_stints"], "")
        sequencia = json.loads(estrategia["sequencia_stints_json"])
        self.assertEqual([s["lap_start"] for s in sequencia], [None,0,1,10])
        self.assertEqual(self.csv("laps_sessoes")[0]["lap_duration"], "90.0")
        cobertura = {r["tipo"]:r for r in self.csv("cobertura")}
        for tipo in ("stints", "estrategias_pneus"):
            self.assertEqual(cobertura[tipo]["estado"], "parcial")
            self.assertIn("limites de voltas", cobertura[tipo]["motivo"])

    def meteo(self):
        return {"latitude":26.0, "longitude":50.5, "elevation":7, "timezone":"GMT", "utc_offset_seconds":0,
                "hourly":{"time":["2024-03-02T12:00", "2024-03-02T13:00"],
                          "temperature_2m":[0, None], "precipitation":[0, 0]},
                "hourly_units":{"time":"iso8601", "temperature_2m":"°C", "precipitation":"mm"}}

    def test_clima_modelado_zero_nulo_e_pista_separados_com_origem(self):
        self.adicionar("weather", [{"session_key":100, "meeting_key":10, "date":"2024-03-02T12:00:00Z",
                                    "air_temperature":20, "track_temperature":35, "rainfall":0}], anual=True)
        self.adicionar("archive", self.meteo(), provider="open-meteo", model="ecmwf_ifs", origin="historical_atmospheric_model")
        gerar_derivados(self.raiz)
        rows = self.csv("clima_open_meteo")
        self.assertEqual([r["temperature_2m"] for r in rows], ["0", ""])
        self.assertEqual(rows[0]["origin"], "historical_atmospheric_model")
        self.assertNotIn("track_temperature", rows[0])
        self.assertEqual(self.csv("clima_pista")[0]["track_temperature"], "35")

    def test_clima_pista_copias_identicas_sao_contadas_e_conflitos_falham(self):
        medida = dict(session_key=100, meeting_key=10, date="2024-03-02T12:00:00Z",
                      air_temperature=20, track_temperature=35, rainfall=0)
        fonte = self.adicionar("weather", [medida, medida], anual=True)
        resultado = gerar_derivados(self.raiz)
        self.assertEqual(len(self.csv("clima_pista")), 1)
        self.assertEqual(resultado["duplicatas_identicas_raw"], {fonte["arquivo"]:1})
        dados = [medida, dict(medida, air_temperature=21)]
        arquivo = self.gravar(fonte["arquivo"], dados)
        fonte["sha256"] = hashlib.sha256(arquivo.read_bytes()).hexdigest()
        self.gravar("coleta_online.json", {"fontes":self.fontes})
        with self.assertRaisesRegex(ValueError, "clima duplicado"):
            gerar_derivados(self.raiz)

    def test_clima_200_parcial_quantifica_horas_ausentes_e_nulos(self):
        self.adicionar("archive", self.meteo(), provider="open-meteo", model="ecmwf_ifs",
                       origin="historical_atmospheric_model", start_date="2024-03-02", end_date="2024-03-02",
                       url="https://weather.example/v1/archive?hourly=temperature_2m,precipitation")
        gerar_derivados(self.raiz)
        cobertura = next(r for r in self.csv("cobertura") if r["tipo"] == "clima_open_meteo")
        self.assertEqual(cobertura["estado"], "parcial")
        self.assertEqual(cobertura["n_horas_observadas"], "2")
        self.assertEqual(cobertura["n_horas_esperadas"], "24")
        self.assertEqual(cobertura["n_horas_ausentes"], "22")
        self.assertEqual(cobertura["n_valores_nulos"], "1")
        self.assertIn("22 de 24 horas", cobertura["motivo"])
        self.assertIn("1 valores ausentes", cobertura["motivo"])
        self.assertEqual(self.csv("clima_open_meteo")[0]["temperature_2m"], "0")

    def meteo_completo(self):
        dados = self.meteo()
        dados["hourly"] = {"time":["2024-03-02T{:02d}:00".format(h) for h in range(24)]}
        unidades = {"temperature_2m":"°C", "relative_humidity_2m":"%", "precipitation":"mm", "rain":"mm",
                    "wind_speed_10m":"m/s", "wind_direction_10m":"°", "surface_pressure":"hPa"}
        dados["hourly"].update({campo:[0] * 24 for campo in unidades})
        dados["hourly"]["surface_pressure"] = [1010] * 24
        dados["hourly_units"] = dict(time="iso8601", **unidades)
        return dados

    def test_clima_janela_completa_zero_valido_e_pressao_preservada(self):
        self.adicionar("archive", self.meteo_completo(), provider="open-meteo", model="ecmwf_ifs",
                       origin="historical_atmospheric_model", start_date="2024-03-02", end_date="2024-03-02")
        gerar_derivados(self.raiz)
        cobertura = next(r for r in self.csv("cobertura") if r["tipo"] == "clima_open_meteo")
        self.assertEqual(cobertura["estado"], "disponivel")
        self.assertEqual(cobertura["n_horas_esperadas"], "24")
        self.assertEqual(cobertura["n_horas_ausentes"], "0")
        self.assertEqual(cobertura["n_valores_nulos"], "0")
        self.assertEqual(cobertura["n_campos_unidade_invalida"], "0")
        self.assertEqual(self.csv("clima_open_meteo")[0]["surface_pressure"], "1010")

    def test_clima_janela_declarada_completa_nao_oculta_sessao_de_dia_posterior(self):
        fonte = self.fontes[0]
        sessoes = [self.sessao(100, "Race", "Race"), self.sessao(101, "Sprint", "Race"),
                   self.sessao(99, "Qualifying", "Qualifying")]
        sessoes[0]["date_start"] = "2024-03-03T12:00:00Z"
        sessoes[0]["date_end"] = "2024-03-03T14:00:00Z"
        arquivo = self.gravar(fonte["arquivo"], sessoes)
        fonte["sha256"] = hashlib.sha256(arquivo.read_bytes()).hexdigest()
        self.adicionar("archive", self.meteo_completo(), provider="open-meteo", model="ecmwf_ifs",
                       origin="historical_atmospheric_model", start_date="2024-03-02", end_date="2024-03-02")
        gerar_derivados(self.raiz)
        cobertura = next(r for r in self.csv("cobertura") if r["tipo"] == "clima_open_meteo")
        self.assertEqual(cobertura["n_horas_ausentes"], "0")
        self.assertEqual(cobertura["n_horas_sessoes_ausentes"], "3")
        self.assertEqual(cobertura["estado"], "parcial")
        self.assertIn("sessões catalogadas", cobertura["motivo"])

    def test_clima_sem_unidade_compativel_e_sem_origem_nao_certifica_cobertura(self):
        dados = self.meteo_completo()
        dados["hourly_units"]["wind_speed_10m"] = "km/h"
        del dados["hourly_units"]["surface_pressure"]
        self.adicionar("archive", dados, provider="open-meteo", start_date="2024-03-02", end_date="2024-03-02")
        gerar_derivados(self.raiz)
        cobertura = next(r for r in self.csv("cobertura") if r["tipo"] == "clima_open_meteo")
        self.assertEqual(cobertura["estado"], "parcial")
        self.assertEqual(cobertura["n_campos_unidade_invalida"], "2")
        self.assertIn("origem/modelo", cobertura["motivo"])
        self.assertEqual(self.csv("clima_open_meteo")[0]["wind_speed_10m"], "0")

    def test_clima_hora_duplicada_com_formatos_utc_equivalentes_e_rejeitada(self):
        dados = self.meteo()
        dados["hourly"]["time"] = ["2024-03-02T12:00Z", "2024-03-02T12:00+00:00"]
        self.adicionar("archive", dados, provider="open-meteo")
        with self.assertRaisesRegex(ValueError, "hora meteorológica duplicado"):
            gerar_derivados(self.raiz)

    def test_stint_com_chave_duplicada_continua_erro_estrutural(self):
        stint = dict(session_key=100, meeting_key=10, driver_number=4, stint_number=1,
                     lap_start=None, lap_end=None, compound="MEDIUM")
        self.adicionar("stints", [stint, stint], anual=True)
        with self.assertRaisesRegex(ValueError, "stint duplicado"):
            gerar_derivados(self.raiz)

    def test_clima_array_truncado_e_fuso_nao_utc_falham(self):
        dados = self.meteo()
        dados["hourly"]["temperature_2m"] = [1]
        fonte = self.adicionar("archive", dados, provider="open-meteo")
        with self.assertRaisesRegex(ValueError, "array meteorológico incompleto"):
            gerar_derivados(self.raiz)
        dados = self.meteo()
        dados["utc_offset_seconds"] = 10800
        arquivo = self.gravar(fonte["arquivo"], dados)
        fonte["sha256"] = hashlib.sha256(arquivo.read_bytes()).hexdigest()
        self.gravar("coleta_online.json", {"fontes":self.fontes})
        with self.assertRaisesRegex(ValueError, "UTC"):
            gerar_derivados(self.raiz)

    def test_fontes_substituidas_sao_preservadas_sem_duplicar_horas(self):
        antiga = self.adicionar("archive", self.meteo(), provider="open-meteo",
                                normalizar=False, motivo="janela substituída")
        # Uma captura substituta tem a mesma identidade lógica; a antiga não entra no índice ativo.
        self.adicionar("archive", self.meteo(), provider="open-meteo")
        resultado = gerar_derivados(self.raiz)
        self.assertEqual(len(self.csv("clima_open_meteo")), 2)
        self.assertEqual(resultado["fontes_nao_normalizadas"], [
            {"arquivo":antiga["arquivo"], "motivo":"janela substituída"}])

    def test_cobertura_parcial_informa_sessoes_catalogadas_sem_registros(self):
        self.adicionar("laps", [{"session_key":100, "meeting_key":10, "driver_number":4, "lap_number":1}], anual=True)
        gerar_derivados(self.raiz)
        cobertura = next(r for r in self.csv("cobertura") if r["tipo"] == "laps_sessoes")
        self.assertEqual(cobertura["estado"], "parcial")
        self.assertEqual(cobertura["n_sessoes_catalogadas"], "3")
        self.assertEqual(cobertura["n_sessoes_observadas"], "1")
        self.assertIn("99", cobertura["motivo"])

    def test_equipes_preservam_pontos_zero_ausencia_e_sprint(self):
        self.local("resultados.csv", [dict(self.evento, piloto_id="a", equipe_id="time", numero=4,
                                          pontos=0, posicao_final=10, fonte_id="origem"),
                                      dict(self.evento, piloto_id="b", equipe_id="time", numero=5,
                                          pontos="", posicao_final="", fonte_id="origem")])
        self.local("sprint_resultados.csv", [dict(self.evento, piloto_id="a", equipe_id="time", pontos=2,
                                                 posicao_final=7, fonte_id="sprint")])
        gerar_derivados(self.raiz)
        rows = self.csv("comparativo_equipes")
        race = next(r for r in rows if r["tipo_sessao"] == "Race")
        sprint = next(r for r in rows if r["tipo_sessao"] == "Sprint")
        self.assertEqual(race["pontos_soma_observada"], "0.0")
        self.assertEqual(race["n_pontos_conhecidos"], "1")
        self.assertEqual(race["pontos_completos"], "False")
        self.assertEqual(sprint["pontos_soma_observada"], "2.0")

    def test_cobertura_erro_ou_ausencia_nao_vira_zero_e_saida_idempotente(self):
        self.fontes.append(dict(provider="openf1", endpoint="laps", temporada=2024,
                                status=429, erro="limite atingido"))
        self.gravar("coleta_online.json", {"fontes":self.fontes})
        primeiro = gerar_derivados(self.raiz)
        rows = self.csv("cobertura")
        lap = next(r for r in rows if r["tipo"] == "laps_sessoes")
        self.assertEqual(lap["n_registros"], "")
        self.assertEqual(lap["estado"], "indisponivel")
        self.assertIn("429", lap["motivo"])
        self.assertEqual(primeiro, gerar_derivados(self.raiz))
        destino = self.raiz / "normalizado" / "cobertura.csv"
        destino.write_text("alterado", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "divergente"):
            gerar_derivados(self.raiz)
        self.assertEqual(destino.read_text(), "alterado")


if __name__ == "__main__":
    unittest.main()
