import unittest
from datetime import datetime, timedelta, timezone

from pitwall.data.driver_source_audit import atmospheric_samples, classify_start
from pitwall.data.tyre_reconciliation import TyreReconciliationError, verify_identity


class DriverSourceAuditTests(unittest.TestCase):
    def test_retirement_without_completed_lap_is_a_start(self):
        self.assertTrue(classify_start({"dnf": True, "dns": False, "number_of_laps": 0}, 0, 0)[0])

    def test_disqualified_driver_with_observed_laps_started(self):
        self.assertTrue(classify_start({"dsq": True, "dns": False, "number_of_laps": None}, 0, 56)[0])

    def test_dns_is_not_started_and_conflicting_laps_block(self):
        self.assertFalse(classify_start({"dns": True}, 0, 0)[0])
        with self.assertRaises(ValueError):
            classify_start({"dns": True}, 5, 5)

    def test_unknown_start_is_not_assumed_from_zero_laps(self):
        with self.assertRaises(ValueError):
            classify_start({"dnf": False, "dns": False}, 0, 0)

    def test_zero_cloud_and_code_are_not_missing(self):
        data = {"utc_offset_seconds": 0, "timezone": "GMT", "hourly_units": {"cloud_cover": "%", "weather_code": "wmo code"},
                "hourly": {"time": ["2024-01-01T09:00", "2024-01-01T10:00", "2024-01-01T11:00"],
                           "cloud_cover": [100, 0, 100], "weather_code": [61, 0, 61]}}
        window = {"intervalos_ativos": [["2024-01-01T09:30:00Z", "2024-01-01T10:30:00Z"]]}
        self.assertEqual(atmospheric_samples(data, window), [{"time_utc": "2024-01-01T10:00:00+00:00", "cloud_cover": 0, "weather_code": 0}])
        data["utc_offset_seconds"] = 3600
        with self.assertRaises(ValueError):
            atmospheric_samples(data, window)

    def fingerprint(self, shift_days=0, duplicate=False):
        base = datetime(2026, 3, 8, 4, tzinfo=timezone.utc)
        native, rows = {}, []
        for i in range(1, 11):
            dt = base + timedelta(seconds=i * 90)
            native[("1", i)] = {"lap_duration": str(90 + i), "date_start": dt.isoformat()}
            source_time = dt + timedelta(days=shift_days)
            rows.append({"dNum": "1", "drv": "AAA", "lap": i + 1, "ff1G": False,
                         "time": 90 + i, "lSD": source_time.strftime("%Y-%m-%dT%H:%M:%S") + ".000000000"})
        if duplicate:
            rows[-1]["lSD"], rows[-1]["time"] = rows[0]["lSD"], rows[0]["time"]
        return verify_identity(rows, {"drivers": [{"driver": "AAA", "dn": "1"}]}, {"1": {"name_acronym": "AAA"}}, native)

    def test_number_drift_requires_unique_time_and_duration_evidence(self):
        result = self.fingerprint()
        self.assertEqual(result["fracao_concordante"], 1)
        self.assertEqual(len(result["numeros_voltas_divergentes"]), 10)
        self.assertEqual(result["metodo_correspondencia"], "piloto_horario_utc_e_duracao_unicos")

    def test_other_date_or_reused_matching_lap_cannot_validate_join(self):
        for kwargs in ({"shift_days": 1}, {"duplicate": True}):
            with self.assertRaises(TyreReconciliationError):
                self.fingerprint(**kwargs)


if __name__ == "__main__":
    unittest.main()
