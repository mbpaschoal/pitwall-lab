"""Behavioural checks for both languages without changing scientific evidence."""

import hashlib
from pathlib import Path
from string import Formatter
import unittest
from urllib.parse import parse_qs, urlsplit
import pandas as pd
from streamlit.testing.v1 import AppTest
from pitwall.i18n import (
    catalogue,
    in_language,
    language,
    set_language,
    translate,
    visible_text,
)
from pitwall.i18n.streamlit import dataframe
from pitwall.publishing import documentation
from pitwall.dashboard import components

ROOT = Path(__file__).resolve().parents[1]


class TestTranslation(unittest.TestCase):
    def tearDown(self):
        set_language("pt")

    def test_default_invalid_and_independent_formatter_language(self):
        self.assertEqual(set_language("unexpected"), "pt")
        self.assertEqual(translate("Histórico"), "Histórico")
        self.assertEqual(in_language("Histórico", "en"), "History")
        self.assertEqual(language(), "pt")

    def test_html_translation_preserves_urls_ids_styles_and_names(self):
        source = '<style>.Corridas {color:red}</style><a href="/?tela=Corridas&amp;gp=18" id="Corridas" aria-label="Histórico">Histórico</a><span>Max Verstappen</span>'
        set_language("en")
        result = visible_text(source)
        self.assertIn(">History</a>", result)
        self.assertIn('aria-label="History"', result)
        self.assertIn('href="/?tela=Corridas&amp;gp=18" id="Corridas"', result)
        self.assertIn("<style>.Corridas {color:red}</style>", result)
        self.assertIn("Max Verstappen", result)

    def test_dynamic_messages_numbers_markdown_and_placeholders(self):
        set_language("en")
        self.assertEqual(
            translate(
                "5 edições anteriores, de 2021 a 2025. A corrida selecionada está excluída."
            ),
            "5 previous editions, from 2021 to 2025. The selected race is excluded.",
        )
        self.assertEqual(translate("25 out 2026"), "25 Oct 2026")
        self.assertEqual(translate("5,513 km"), "5.513 km")
        self.assertEqual(
            translate("[Histórico](https://example.org/Histórico)"),
            "[History](https://example.org/Histórico)",
        )
        for source, target in catalogue().items():
            a = [
                field
                for _, field, _, _ in Formatter().parse(source)
                if field is not None
            ]
            b = [
                field
                for _, field, _, _ in Formatter().parse(target)
                if field is not None
            ]
            self.assertEqual(len(a), len(b), source)

    def test_document_code_blocks_and_canonical_identifiers_are_preserved(self):
        set_language("en")
        source = "Histórico\n```text\nclassificacao_ausente\nreferencia_temporal_ausente\n```\n`Histórico`"
        result = visible_text(source)
        self.assertTrue(result.startswith("History\n"))
        self.assertIn("classificacao_ausente\nreferencia_temporal_ausente", result)
        self.assertTrue(result.endswith("`Histórico`"))
        self.assertEqual(
            visible_text("<code>Histórico</code>"), "<code>Histórico</code>"
        )

    def test_translated_table_is_a_copy_with_identical_numbers_and_missingness(self):
        original = pd.DataFrame(
            [{"Piloto": "Max Verstappen", "Pontos": 25.0, "Observação": None}]
        )
        before = original.copy(deep=True)
        set_language("en")
        result = dataframe(original)
        self.assertEqual(list(result.columns), ["Driver", "Points", "Note"])
        self.assertEqual(result["Points"].tolist(), before["Pontos"].tolist())
        self.assertTrue(result["Note"].isna().all())
        self.assertTrue(original.equals(before))

    def test_links_and_six_documents_keep_language_without_changing_scientific_csv(
        self,
    ):
        set_language("en")
        link = parse_qs(
            urlsplit(
                components.link_interno(2026, 18, tela="Corridas", aba="Histórico")
            ).query
        )
        self.assertEqual(
            link,
            {
                "tela": ["Corridas"],
                "temporada": ["2026"],
                "gp": ["18"],
                "aba": ["Histórico"],
                "lang": ["en"],
            },
        )
        for identifier in documentation.ENGLISH_DOCUMENTS:
            self.assertEqual(
                parse_qs(urlsplit(documentation.url_documento(identifier)).query)[
                    "lang"
                ],
                ["en"],
            )
            text = documentation.conteudo_documento(identifier)
            self.assertTrue(text.startswith("# "), identifier)
            self.assertNotIn("Arquivo fora da allowlist", text)
        download = documentation.downloads_documento("relatorio-2024")[0]["dados"]
        expected = (ROOT / "reports/modelo_v1/previsoes_validacao.csv").read_bytes()
        self.assertEqual(
            hashlib.sha256(download).digest(), hashlib.sha256(expected).digest()
        )


class TestEnglishApplication(unittest.TestCase):
    def test_whole_app_english_then_portuguese_preserves_gp(self):
        at = AppTest.from_file(ROOT / "app.py", default_timeout=30)
        at.query_params.update({"lang": "en", "temporada": "2026", "gp": "18"})
        at.run(timeout=30)
        self.assertFalse(at.exception)
        self.assertEqual(
            [t.label for t in at.tabs],
            [
                "Overview",
                "Sessions and laps",
                "Tyres and stops",
                "Weather",
                "At this circuit",
                "Teams",
            ],
        )
        self.assertEqual(
            next(s for s in at.selectbox if s.key == "gp").value, "2026:18"
        )
        self.assertTrue(
            any("Driver performance at this circuit" == s.value for s in at.subheader)
        )
        tables = [d.value for d in at.dataframe]
        self.assertTrue(any("Observed points" in d.columns for d in tables))
        self.assertFalse(any("Pontos observados" in d.columns for d in tables))
        button = next(
            button
            for button in at.button
            if button.label == "🇧🇷" and "48697374c3b37269636f" in button.key
        )
        button.click()
        at.run(timeout=30)
        self.assertFalse(at.exception)
        self.assertEqual(
            next(s for s in at.selectbox if s.key == "gp").value, "2026:18"
        )
        self.assertIn("Nesta pista", [t.label for t in at.tabs])

    def test_native_language_button_retains_methodology_and_session_filter(self):
        import json

        at = AppTest.from_file(ROOT / "app.py", default_timeout=30)
        at.query_params.update(
            {"lang": "en", "temporada": "2025", "gp": "1", "tela": "Metodologia"}
        )
        at.run(timeout=30)
        next(b for b in at.button if b.label == "🇧🇷").click()
        at.run(timeout=30)
        self.assertFalse(at.exception)
        self.assertEqual(
            next(r for r in at.radio if r.key == "tela").value, "Metodologia"
        )
        self.assertTrue(any(s.value == "Método histórico" for s in at.subheader))
        at.query_params.update({"lang": "en", "tela": "Corridas", "aba": "Tempos"})
        at.run(timeout=30)
        asset = json.loads((ROOT / "frontend_assets/acervo_dashboard.json").read_text())
        qualifying = next(
            s["session_key"]
            for s in asset["gps"]["2025:1"]["sessoes"]
            if s["nome"] == "Qualifying"
        )
        next(
            s for s in at.selectbox if s.key == "acervo_2025_1_sessao_tempos"
        ).set_value(qualifying)
        at.run(timeout=30)
        next(
            b for b in at.button if b.label == "🇧🇷" and "54656d706f73" in b.key
        ).click()
        at.run(timeout=30)
        self.assertFalse(at.exception)
        self.assertEqual(
            next(
                s for s in at.selectbox if s.key == "acervo_2025_1_sessao_tempos"
            ).value,
            qualifying,
        )

    def test_english_plot_and_document_are_not_partial_translations(self):
        at = AppTest.from_file(ROOT / "app.py", default_timeout=30)
        at.query_params.update(
            {"lang": "en", "temporada": "2025", "gp": "1", "tela": "Previsões"}
        )
        at.run(timeout=30)
        self.assertFalse(at.exception)
        self.assertTrue(
            any("Who had the best podium chances" == s.value for s in at.subheader)
        )
        for chart in at.get("plotly_chart"):
            self.assertNotIn("Probabilidade individual de pódio", str(chart.proto.spec))
        at.query_params.update({"tela": "Metodologia", "documento": "relatorio-2024"})
        at.run(timeout=30)
        self.assertFalse(at.exception)
        self.assertTrue(
            any(
                "Stage 4 — v1 podium-probability model" in str(m.value)
                for m in at.markdown
            )
        )
        self.assertTrue(
            any(
                b.label == "Download 2024 predictions (CSV)"
                for b in at.get("download_button")
            )
        )
