import tempfile
import unittest
from pathlib import Path

from pitwall.data.race_weather import (
    RaceWeatherError, build_audit, instant, main_race_session,
    race_windows, summarize_sensors,
)


def event(time, message, category="SessionStatus", **kwargs):
    return {"date": "2024-01-01T" + time + "+00:00", "session_key": 7,
            "category": category, "message": message, **kwargs}


def observation(time, rain=0, **kwargs):
    return {"date": "2024-01-01T" + time + "+00:00", "session_key": "7",
            "session_name": "Race", "rainfall": rain, "air_temperature": 0,
            "track_temperature": 0, "humidity": 0, "pressure": 1000,
            "wind_speed": 0, "wind_direction": 0, **kwargs}


def window():
    return race_windows([event("10:00:00", "SESSION STARTED"),
                         event("10:04:00", "SESSION FINISHED")], 7)


class RaceWeatherTests(unittest.TestCase):
    def test_race_name_separates_sprint_with_identical_native_type(self):
        self.assertEqual(main_race_session([
            {"nome": "Sprint", "tipo": "Race", "session_key": 6},
            {"nome": "Race", "tipo": "Race", "session_key": 7},
        ])["session_key"], 7)

    def test_ambiguous_main_race_rejected(self):
        with self.assertRaises(RaceWeatherError):
            main_race_session([{"nome": "Race"}, {"nome": "Race"}])

    def test_naive_time_rejected_and_offsets_normalized(self):
        with self.assertRaises(RaceWeatherError):
            instant("2024-01-01T10:00:00")
        self.assertEqual(instant("2024-01-01T07:00:00-03:00"),
                         instant("2024-01-01T10:00:00Z"))

    def test_planned_restart_is_not_actual_start(self):
        with self.assertRaises(RaceWeatherError):
            race_windows([event("10:00:00", "RACE WILL START AT 10:05", "Other"),
                          event("11:00:00", "SESSION FINISHED")], 7)

    def test_prestart_red_flag_and_later_pause(self):
        result = race_windows([
            event("09:00:00", "SESSION ABORTED"),
            event("10:00:00", "SESSION STARTED"),
            event("10:02:00", "SESSION ABORTED"),
            event("10:10:00", "SESSION STARTED"),
            event("10:12:00", "SESSION FINISHED"),
        ], 7)
        self.assertEqual(result["duracao_ativa_s"], 240)
        self.assertEqual(result["n_suspensoes"], 1)
        rows = [observation("09:59:00", 1), observation("10:00:30"),
                observation("10:01:30"), observation("10:05:00", 1),
                observation("10:10:30"), observation("10:11:30"),
                observation("10:12:00", 1)]
        self.assertEqual(summarize_sensors(rows, result)["condicao_chuva"],
                         "sem_chuva_registrada")

    def test_zero_is_valid_observation(self):
        result = summarize_sensors([observation("10:0{}:30".format(i)) for i in range(4)], window())
        self.assertEqual(result["condicao_chuva"], "sem_chuva_registrada")
        self.assertEqual(result["campos"]["track_temperature"]["media_amostras"], 0)
        self.assertEqual(result["campos"]["rainfall"]["cobertura_bins_60s"], 1)

    def test_unknown_rain_is_not_no_rain(self):
        result = summarize_sensors([observation("10:0{}:30".format(i), "") for i in range(4)], window())
        self.assertIsNone(result["chuva_observada_em_alguma_medicao"])
        self.assertEqual(result["condicao_chuva"], "desconhecido_cobertura_insuficiente")

    def test_sparse_samples_cannot_claim_complete_coverage(self):
        result = summarize_sensors([observation("10:00:00", 1)], window())
        self.assertFalse(result["campos"]["rainfall"]["elegivel"])
        self.assertTrue(result["chuva_observada_em_alguma_medicao"])
        self.assertEqual(result["condicao_chuva"], "desconhecido_cobertura_insuficiente")

    def test_conflicting_observations_rejected(self):
        with self.assertRaises(RaceWeatherError):
            summarize_sensors([observation("10:00:00", 0), observation("10:00:00", 1)], window())

    def test_wrong_session_rejected(self):
        with self.assertRaises(RaceWeatherError):
            summarize_sensors([observation("10:00:00", session_key=8)], window())
        with self.assertRaises(RaceWeatherError):
            race_windows([{**event("10:00:00", "SESSION STARTED"), "session_key": 8}], 7)

    def test_finish_must_exist(self):
        with self.assertRaises(RaceWeatherError):
            race_windows([event("10:00:00", "SESSION STARTED")], 7)

    def test_global_chequered_used_but_driver_flag_ignored(self):
        result = race_windows([
            event("10:00:00", "SESSION STARTED"),
            event("10:02:00", "CHEQUERED FLAG", "Flag", flag="CHEQUERED", scope="Driver", driver_number=1),
            event("10:03:59", "CHEQUERED FLAG", "Flag", flag="CHEQUERED", scope="Track"),
            event("10:04:00", "SESSION FINISHED"),
        ], 7)
        self.assertEqual(result["duracao_ativa_s"], 239)
        self.assertEqual(result["criterio_fim"], "chequered_flag")

    def test_existing_destination_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            with self.assertRaises(FileExistsError):
                build_audit("missing", "missing", "missing", target)


if __name__ == "__main__":
    unittest.main()
