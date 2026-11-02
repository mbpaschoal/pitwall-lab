"""Scientific states and navigation behind the results/methodology UX changes."""

from contextlib import contextmanager
import copy
import csv
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from pitwall.dashboard import fan_views, tarot
from pitwall.data.dashboard import carregar_temporada
from pitwall.i18n import set_language
from pitwall.publishing import documentation


ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.links = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs))


def evaluated_rows(package):
    return [dict(rodada=row["rodada"], corrida=row["corrida"],
                 modelo=row["acertos_modelo"], classificacao=row["acertos_classificacao"])
            for row in package["corridas"] if row["avaliavel_ranking"]]


class RecordingStreamlit:
    def __init__(self, query):
        self.query_params = query
        self.events = []

    def markdown(self, content, **kwargs):
        self.events.append(("markdown", content))

    def caption(self, content):
        self.events.append(("caption", content))

    def subheader(self, content):
        self.events.append(("subheader", content))

    def download_button(self, label, **kwargs):
        self.events.append(("download", kwargs))

    def button(self, *args, **kwargs):
        return False

    def dialog(self, *args, **kwargs):
        return lambda function: function

    @contextmanager
    def expander(self, label):
        self.events.append(("expander", label))
        yield


class ResultsMethodUXTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = carregar_temporada(ROOT, 2025)

    def setUp(self):
        set_language("pt")

    def tearDown(self):
        set_language("pt")

    def test_sao_paulo_retains_19_historical_probabilities_and_unknown_score(self):
        # Oracle is the preserved producer output, independently of UI markup.
        path = ROOT / "reports/avaliacao_final_v1/previsoes_pre_corrida.csv"
        with path.open(encoding="utf-8", newline="") as source:
            predictions = [row for row in csv.DictReader(source)
                           if row["temporada"] == "2025" and row["rodada"] == "21"]
        self.assertEqual(len(predictions), 20)
        self.assertEqual(sum(row["probabilidade_modelo"] != "" for row in predictions), 19)
        self.assertEqual(sum(row["elegivel_previsao"] == "1" for row in predictions), 19)
        race = next(row for row in self.package["corridas"] if row["rodada"] == 21)
        self.assertFalse(race["avaliavel_ranking"])
        self.assertEqual(race["motivos_nao_avaliavel"], "participante_inelegivel")
        self.assertIsNone(race["acertos_modelo"])
        original = copy.deepcopy(self.package)
        for lang, state, reason in [
            ("pt", "Fora da avaliação", "Há participante inelegível para a avaliação."),
            ("en", "Not evaluated", "A participant is ineligible for evaluation."),
        ]:
            with self.subTest(lang=lang):
                set_language(lang)
                markup = fan_views.performance_cards(evaluated_rows(self.package), self.package["corridas"], 2025)
                self.assertIn(state, markup)
                self.assertIn(reason, markup)
                self.assertNotIn("Sem previsão registrada", markup)
                self.assertNotIn("No recorded prediction", markup)
                self.assertIn("gp=21", markup)
        self.assertEqual(self.package, original)

    def test_historical_last_excluded_gp_is_not_dropped_from_window(self):
        rows = [dict(rodada=23, corrida="Qatar Grand Prix", modelo=2, classificacao=1)]
        races = [dict(rodada=23, corrida="Qatar Grand Prix"),
                 dict(rodada=24, corrida="Abu Dhabi Grand Prix", elegiveis=20, motivos_nao_avaliavel="alvo_desconhecido")]
        markup = fan_views.performance_cards(rows, races, 2025)
        self.assertIn("gp=24", markup)
        self.assertIn("Resultado necessário à avaliação ausente.", markup)
        self.assertEqual(markup.count('data-evaluated="false"'), 1)
        self.assertNotIn("0 de 3", markup)

    def test_unknown_historical_reason_does_not_invent_missing_forecasts_or_zero(self):
        rows = [dict(rodada=1, corrida="Bahrain Grand Prix", modelo=2, classificacao=1)]
        markup = fan_views.performance_cards(rows, [dict(rodada=1, corrida="Bahrain Grand Prix"),
             dict(rodada=2, corrida="Saudi Arabian Grand Prix", elegiveis=20, motivos_nao_avaliavel="unknown")], 2024)
        self.assertIn("Critérios de avaliação não atendidos.", markup)
        self.assertNotIn("Sem previsão registrada", markup)
        self.assertNotIn("0 de 3", markup)

    def test_historical_missing_probabilities_remain_explicitly_missing(self):
        rows = [dict(rodada=1, corrida="Bahrain Grand Prix", modelo=2, classificacao=1)]
        races = [dict(rodada=1, corrida="Bahrain Grand Prix", elegiveis=20),
                 dict(rodada=2, corrida="Saudi Arabian Grand Prix", elegiveis=0,
                      motivos_nao_avaliavel="participante_inelegivel")]
        for lang, missing in [("pt", "Sem probabilidades históricas disponíveis"),
                              ("en", "No historical probabilities available")]:
            with self.subTest(lang=lang):
                set_language(lang)
                markup = fan_views.performance_cards(rows, races, 2025)
                self.assertIn(missing, markup)
                self.assertNotIn("Fora da avaliação", markup)
                self.assertNotIn("Not evaluated", markup)
                self.assertNotIn("0 de 3", markup)

    def test_2026_unissued_awaited_and_under_review_remain_distinct(self):
        rows = [dict(rodada=18, corrida="United States Grand Prix", modelo=2, classificacao=2)]
        races = [dict(rodada=17, corrida="Singapore Grand Prix"),
                 dict(rodada=18, corrida="United States Grand Prix", estado_previsao="previsao_registrada"),
                 dict(rodada=19, corrida="Mexico City Grand Prix", estado_previsao="previsao_registrada")]
        awaited = fan_views.performance_cards(rows, races, 2026)
        review = fan_views.performance_cards(rows, races, 2026, observed_rounds={19})
        self.assertIn("Sem previsão registrada", awaited)
        self.assertIn("Corrida aguardada", awaited)
        self.assertIn("Resultado em conferência", review)
        self.assertNotIn("Corrida aguardada", review)
        self.assertNotIn("Fora da avaliação", awaited + review)
        self.assertEqual(review.count('data-evaluated="true"'), 1)

    def test_six_recent_cards_and_whole_season_have_separate_denominators(self):
        rows = evaluated_rows(self.package)
        for lang, window, summary, denominator in [
            ("pt", "Últimos 6 GPs", "Resumo da temporada", "22 GPs avaliáveis nesta temporada."),
            ("en", "Latest 6 GPs", "Season summary", "22 evaluable GPs in this season."),
        ]:
            with self.subTest(lang=lang):
                set_language(lang)
                markup = fan_views.performance_cards(rows, self.package["corridas"], 2025)
                self.assertEqual(markup.count('class="fan-gp-result"'), 6)
                self.assertIn(window, markup)
                self.assertIn(summary, markup)
                self.assertIn(denominator, markup)
                self.assertIn('class="fan-results-status"', markup)
                self.assertLess(markup.index(window), markup.index('class="fan-gp-results"'))
                self.assertGreater(markup.index(summary), markup.index('class="fan-gp-results"'))

    def test_forecast_profile_links_retain_origin_gp_without_changing_probabilities(self):
        rows = [dict(id="norris", name="Lando Norris", team="McLaren", probability=.682),
                dict(id="unknown", name="Unknown", team="Team", probability=None)]
        original = copy.deepcopy(rows)
        for year, round_ in [(2024, 19), (2026, 18)]:
            for lang, percent in [("pt", "68,2%"), ("en", "68.2%")]:
                with self.subTest(year=year, lang=lang):
                    set_language(lang)
                    markup = fan_views.forecast_rows(rows, year, origin_round=round_)
                    links = Links(markup).links
                    self.assertEqual(len(links), 1)
                    query = parse_qs(urlsplit(links[0]["href"]).query)
                    expected = dict(tela="Pilotos", piloto="norris", visao="perfil", anos=str(year),
                                    temporada=str(year), gp=str(round_), origem_tela="Previsões",
                                    origem_temporada=str(year), origem_gp=str(round_), lang=lang)
                    self.assertEqual(query, {key:[value] for key,value in expected.items()})
                    self.assertIn(percent, markup)
                    self.assertNotIn("fan-place-", markup)
        self.assertEqual(rows, original)

    def test_three_steps_distinguish_frozen_inputs_and_context_and_keep_two_shortcuts(self):
        for lang, inputs, context, boundary in [
            ("pt", "Entradas do modelo v1", "Contexto do dashboard", "não alteram as entradas ou previsões registradas"),
            ("en", "v1 model inputs", "Dashboard context", "do not change model inputs or recorded predictions"),
        ]:
            with self.subTest(lang=lang):
                set_language(lang)
                markup = fan_views.process_steps()
                self.assertEqual(markup.count('class="fan-process-step"'), 3)
                self.assertIn(inputs, markup)
                self.assertIn(context, markup)
                self.assertIn(boundary, markup)
                queries = [parse_qs(urlsplit(link["href"]).query) for link in Links(markup).links]
                self.assertEqual([query["documento"] for query in queries], [["metodo-v1"], ["fontes-atuais"]])
                self.assertTrue(all(query["lang"] == [lang] for query in queries))

    def test_document_shortcuts_and_return_keep_the_valid_selected_gp(self):
        for year, round_ in [(2024, 19), (2026, 18)]:
            with self.subTest(year=year):
                shortcuts = Links(fan_views.process_steps(year=year, round_=round_)).links
                for shortcut in shortcuts:
                    query = parse_qs(urlsplit(shortcut["href"]).query)
                    self.assertEqual(query["temporada"], [str(year)])
                    self.assertEqual(query["gp"], [str(round_)])
                recorder = RecordingStreamlit({"documento":"relatorio-2024", "temporada":str(year), "gp":str(round_)})
                documentation.renderizar_documentacao_local(recorder, documento_primeiro=True)
                for event, content in recorder.events:
                    if event != "markdown":
                        continue
                    for link in Links(content).links:
                        query = parse_qs(urlsplit(link["href"]).query)
                        if query.get("tela") == ["Metodologia"]:
                            self.assertEqual(query["temporada"], [str(year)])
                            self.assertEqual(query["gp"], [str(round_)])
        query = parse_qs(urlsplit(documentation.url_documento("metodo-v1", temporada="invalid", rodada="../../private")).query)
        self.assertNotIn("temporada", query)
        self.assertNotIn("gp", query)

    def test_current_sources_choose_language_in_checkout_and_portable_package(self):
        bilingual = "# Sources\n\n## Português\n\nFontes atuais em português.\n\n## English\n\nCurrent sources in English.\n\n## Shared appendix\n\nShared bilingual material.\n"
        for relative in ["FONTES_E_DADOS.md", "publicacao/templates/FONTES_E_DADOS.md"]:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(bilingual, encoding="utf-8")
                with patch.object(documentation, "RAIZ", root):
                    set_language("pt")
                    self.assertIn("Fontes atuais em português.", documentation.conteudo_documento("fontes-atuais"))
                    self.assertNotIn("Current sources in English.", documentation.conteudo_documento("fontes-atuais"))
                    set_language("en")
                    content = documentation.conteudo_documento("fontes-atuais")
                    self.assertIn("Current sources in English.", content)
                    self.assertNotIn("Fontes atuais em português.", content)
                    self.assertNotIn("Shared appendix", content)

    def test_sources_stay_allowlisted_and_reject_symlink_outside_root(self):
        set_language("en")
        unavailable = documentation.reescrever_links("[PT/EN credits](dashboard_assets/fan/ATTRIBUTION.md)")
        self.assertEqual(unavailable, "PT/EN credits (audit artefact outside this demonstration)")
        self.assertFalse(documentation.documento_disponivel("../../segredo"))
        with self.assertRaises(ValueError):
            documentation.conteudo_documento("../../segredo")
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "package"
            root.mkdir()
            outside = directory / "outside.md"
            outside.write_text("Private text", encoding="utf-8")
            (root / "FONTES_E_DADOS.md").symlink_to(outside)
            with patch.object(documentation, "RAIZ", root), self.assertRaises(ValueError):
                documentation.conteudo_documento("fontes-atuais")

    def test_selected_document_precedes_index_and_keeps_scientific_download_bytes(self):
        recorder = RecordingStreamlit({"documento":"relatorio-2024"})
        with patch.object(documentation, "RAIZ", ROOT):
            documentation.renderizar_documentacao_local(recorder, documento_primeiro=True)
        report = next(index for index, event in enumerate(recorder.events)
                      if event[0] == "markdown" and event[1].startswith("# "))
        index = next(index for index, event in enumerate(recorder.events) if event[0] == "subheader")
        self.assertLess(report, index)
        back = Links(recorder.events[0][1]).links[0]
        self.assertEqual(parse_qs(urlsplit(back["href"]).query), {"tela":["Metodologia"], "lang":["pt"]})
        download = next(event[1] for event in recorder.events if event[0] == "download")
        self.assertEqual(download["data"], (ROOT / "reports/modelo_v1/previsoes_validacao.csv").read_bytes())
        self.assertTrue(any("Protocolo histórico (etapa 3)" in event[1]
                            for event in recorder.events if event[0] == "markdown"))

    def test_tarot_return_promises_only_the_selected_gp_and_dismisses_cards(self):
        rows = [dict(driver_id="norris", name="Lando Norris", team="McLaren", probability=.682)]
        for lang, label in [("pt", "Voltar às chances deste GP"), ("en", "Back to this GP’s podium chances")]:
            with self.subTest(lang=lang):
                set_language(lang)
                recorder = RecordingStreamlit({"cartas":"1"})
                with patch.object(tarot, "cards_html", return_value="<div>Cards</div>"):
                    tarot.render(recorder, ROOT, rows, 2026, 18, True)
                markup = recorder.events[-1][1]
                self.assertIn(label, markup)
                query = parse_qs(urlsplit(Links(markup).links[0]["href"]).query)
                self.assertEqual(query, {"tela":["Previsões"], "temporada":["2026"], "gp":["18"], "lang":[lang]})
                self.assertNotIn("cartas", query)
                self.assertNotIn("como calculamos", markup)


if __name__ == "__main__":
    unittest.main()
