import io
import tempfile
import unittest

from pitwall.data.archive_collection import CaptureClient
from pitwall.data.f1_timing_stream import disclosed_compounds, parse_stream
from pitwall.data.tyre_reconciliation import (
    TyreReconciliationError, absence_status, columnar_rows, observed_stints,
    positive_integer, verify_identity,
)


class Response(io.BytesIO):
    status = 200

    def geturl(self):
        return "https://example.test/archive"


def lap(number=1, **kwargs):
    return {"lap": number, "stint": 1, "compound": "SOFT", "ff1G": False,
            "dNum": "1", "drv": "AAA", "time": 90, **kwargs}


class TyreReconciliationTests(unittest.TestCase):
    def test_generated_placeholder_does_not_supply_bounds(self):
        self.assertEqual(observed_stints([lap(ff1G=True)], {}), {})

    def test_missing_compound_stays_unknown(self):
        value = observed_stints([lap(compound="None")], {})[1]
        self.assertIsNone(value["compound"])
        self.assertFalse(value["compound_elegivel"])

    def test_field_level_native_compound_retains_own_provenance(self):
        value = observed_stints([lap(compound="None")], {1: {"compound": "MEDIUM"}})[1]
        self.assertEqual(value["compound"], "MEDIUM")
        self.assertEqual(value["fonte_composto"], "openf1_stints")
        self.assertEqual(value["fonte_limites"], "tracinginsights_lap_number")

    def test_conflicting_native_compound_is_explicit(self):
        value = observed_stints([lap()], {1: {"compound": "HARD"}})[1]
        self.assertTrue(value["conflito_composto_nativo"])

    def test_ordinal_conflict_blocks_native_compound_fill_in_other_stints(self):
        values = observed_stints([lap(), lap(2, stint=2, compound="None")],
                                 {1: {"compound": "HARD"}, 2: {"compound": "MEDIUM"}})
        self.assertIsNone(values[2]["compound"])
        self.assertFalse(values[2]["mapa_ordinais_compativel"])

    def test_gap_or_overlap_cannot_form_complete_stint(self):
        for rows in ([lap(1), lap(3)], [lap(1), lap(1, stint=2)]):
            with self.assertRaises(TyreReconciliationError):
                observed_stints(rows, {})

    def test_boolean_negative_and_fractional_lap_rejected(self):
        for value in (True, 0, -1, 1.5, "nan"):
            with self.assertRaises(TyreReconciliationError):
                positive_integer(value)

    def test_malformed_parallel_arrays_rejected(self):
        data = {k: [v] for k, v in lap().items()}
        data["lap"] = []
        with self.assertRaises(TyreReconciliationError):
            columnar_rows(data)

    def test_zero_without_start_flags_is_not_a_structural_absence(self):
        with self.assertRaises(TyreReconciliationError):
            absence_status({"number_of_laps": 0, "dns": False, "dnf": False})
        self.assertIn("nao_largou", absence_status({"number_of_laps": 0, "dns": True}))
        self.assertIn("zero_voltas", absence_status({"number_of_laps": 0, "dnf": True}))

    def test_driver_number_and_acronym_both_verified(self):
        rows = [lap(i) for i in range(1, 11)]
        native = {("1", i): {"lap_duration": "90"} for i in range(1, 11)}
        metadata = {"drivers": [{"driver": "AAA"}]}
        self.assertEqual(verify_identity(rows, metadata, {"1": {"name_acronym": "AAA"}}, native)["fracao_concordante"], 1)
        with self.assertRaises(TyreReconciliationError):
            verify_identity(rows, metadata, {"1": {"name_acronym": "BBB"}}, native)

    def test_stream_parser_preserves_explicit_compound_and_line(self):
        raw = b'00:00:00.000{"Lines":{"1":{"Stints":[{"Compound":"SOFT"}]}}}\r\n'
        value = disclosed_compounds(parse_stream(raw))[("1", 1)]
        self.assertEqual(value["compound"], "SOFT")
        self.assertEqual(value["linha_fonte"], 1)
        with self.assertRaises(ValueError):
            parse_stream(b"<html>Access denied</html>")

    def test_raw_capture_cache_preserves_bytes_without_network_repeat(self):
        raw = b'00:00:00.000{"Lines":{}}\r\n'
        calls = []

        def opener(*args, **kwargs):
            calls.append(1)
            return Response(raw)

        with tempfile.TemporaryDirectory() as directory:
            client = CaptureClient(directory, opener=opener)
            args = ("f1-livetiming", "timing_app_data", "data.jsonStream", "https://example.test/archive")
            self.assertEqual(client.capture(*args, response_format="bytes"), raw)
            self.assertEqual(client.capture(*args, response_format="bytes"), raw)
            self.assertEqual(len(calls), 1)
            self.assertNotIn("erro_formato", client.manifest["fontes"][0])


if __name__ == "__main__":
    unittest.main()
