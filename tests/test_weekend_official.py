"""Synthetic standings identity and completeness checks."""
from copy import deepcopy
import unittest
from operacao2026.weekend_official import standings
from operacao2026.weekend_projection import project

class Client:

    def __init__(self, round_number=19, total=1):
        self.round = round_number
        self.total = total
        self.manifest = {'fontes': []}

    def capture(self, *args):
        self.manifest['fontes'].append(dict(obtido_em_utc='2026-11-02T00:00:00Z'))
        driver = dict(position='1', points='25', wins='1', Driver=dict(driverId='synthetic', givenName='Synthetic', familyName='Driver', nationality='British'), Constructors=[dict(constructorId='synthetic', name='Synthetic')])
        return {'MRData': dict(total=str(self.total), offset='0', StandingsTable={'StandingsLists': [dict(season='2026', round=str(self.round), DriverStandings=[driver])] if self.total else []})}

class OfficialTests(unittest.TestCase):

    def test_exact_round_published_without_invented_points(self):
        data = standings(Client(), dict(temporada=2026, rodada=19))
        self.assertTrue(data['disponivel'])
        self.assertEqual(data['classificacao'][0]['pontos'], 25)

    def test_previous_round_rejected(self):
        with self.assertRaises(ValueError):
            standings(Client(18), dict(temporada=2026, rodada=19))

    def test_unpublished_not_zero_score(self):
        data = standings(Client(total=0), dict(temporada=2026, rodada=19))
        self.assertFalse(data['disponivel'])
        self.assertEqual(data['classificacao'], [])

    def test_conflicting_lap_or_unknown_driver_rejected(self):
        session = {'session_name': 'Race', 'session_key': 11404}
        data = {'drivers': [{'driver_number': 7}], 'laps': [dict(driver_number=7, lap_number=1, lap_duration=90)]}
        bad = deepcopy(data)
        bad['laps'].append(dict(driver_number=7, lap_number=1, lap_duration=80))
        with self.assertRaises(ValueError):
            project(bad, session)
        bad = deepcopy(data)
        bad['laps'][0]['driver_number'] = 8
        with self.assertRaises(ValueError):
            project(bad, session)
if __name__ == '__main__':
    unittest.main()
