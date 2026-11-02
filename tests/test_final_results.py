"""Final classifications preserve captures and bounded event collection."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from operacao2026 import final_results, weekend, cloud
from operacao2026.weekend_reconciliation import load_review, reconcile

ROOT = Path(__file__).resolve().parents[1]


class FinalResultTests(unittest.TestCase):
    def setUp(self):
        self.event = weekend.load_event(ROOT / 'operacao2026/eventos/mexico2026.json')
        self.review = load_review(ROOT, self.event)
        self.race = next(s for s in self.event['sessions'] if s['session_name'] == 'Race')
        self.final = self.review['sessoes'][str(self.race['session_key'])]['classificacao_final']
        self.data = dict(drivers=[dict(driver_number=r['numero'], full_name=r['full_name'], team_name=r['team_name'])
                                  for r in self.final['linhas']],
                         session_result=[dict(driver_number=r['numero'], position=r['ordem'], duration=1,
                                              gap_to_leader=0, points=0) for r in self.final['linhas']])

    def test_final_penalties_apply_without_changing_native_capture(self):
        before = deepcopy(self.data)
        output, audit = reconcile(self.data, self.race, self.review)
        by_number = {r['driver_number']: r for r in output['session_result']}
        self.assertEqual(self.data, before)
        self.assertEqual([by_number[n]['position'] for n in (81, 43, 10)], [13, 15, 17])
        self.assertEqual([by_number[n]['gap_to_leader'] for n in (81, 43, 10)], [29.475, 30.204, 51.483])
        self.assertEqual(by_number[30]['points'], 6)
        self.assertIsNone(by_number[14]['position'])
        self.assertIsNone(by_number[14]['duration'])
        self.assertTrue(by_number[14]['dnf'])
        self.assertEqual([r['position'] for r in output['session_result'][:17]], list(range(1, 18)))
        self.assertEqual(audit['acoes'][-1]['tipo'], 'classificacao_final_oficial')

    def test_partial_or_conflicting_native_population_is_rejected(self):
        for case in ('missing', 'duplicate', 'profile'):
            with self.subTest(case=case):
                data = deepcopy(self.data)
                if case == 'missing': data['session_result'].pop()
                if case == 'duplicate': data['session_result'][-1] = data['session_result'][0]
                if case == 'profile': data['drivers'][0]['full_name'] = 'Other Driver'
                with self.assertRaisesRegex(ValueError, 'population|profile'):
                    reconcile(data, self.race, self.review)

    def test_missing_team_is_supplied_only_in_the_reviewed_copy(self):
        profile = next(p for p in self.data['drivers'] if p['driver_number'] == 50)
        profile['team_name'] = None
        output, audit = reconcile(self.data, self.race, self.review)
        restored = next(p for p in output['drivers'] if p['driver_number'] == 50)
        self.assertEqual(restored['team_name'], 'Haas F1 Team')
        self.assertIsNone(profile['team_name'])
        before = next(r for r in audit['acoes'][-1]['anterior'] if r['driver_number'] == 50)
        self.assertIsNone(before['perfil']['team_name'])

    def test_invalid_review_does_not_turn_nc_into_a_finish(self):
        final = deepcopy(self.final)
        final['linhas'][-1]['duracao'] = 100
        with self.assertRaisesRegex(ValueError, 'Unclassified'):
            final_results.validated_rows(final)
        final = deepcopy(self.final); final['linhas'][-1]['numero'] = final['linhas'][0]['numero']
        with self.assertRaisesRegex(ValueError, 'Duplicated'):
            final_results.validated_rows(final)

    def test_unverified_or_pre_finish_source_cannot_rewrite_results(self):
        for key, value in [('url', 'https://example.com/final_race_classification.pdf'),
                           ('obtido_em_utc', '2026-11-01T00:00:00Z')]:
            with self.subTest(key=key):
                review = deepcopy(self.review)
                review['fontes'][self.final['fonte']][key] = value
                with self.assertRaisesRegex(ValueError, 'verified posterior'):
                    reconcile(self.data, self.race, review)

    def test_sao_paulo_schedule_and_collection_window(self):
        event = weekend.load_event(ROOT / 'operacao2026/eventos/saopaulo2026.json')
        self.assertEqual((event['rodada'], event['circuito_id']), (20, 'interlagos'))
        self.assertEqual(len(event['sessions']), 5)
        self.assertFalse(any('Sprint' in s['session_name'] for s in event['sessions']))
        self.assertEqual(event['largada_utc'], '2026-11-08T17:00:00Z')
        self.assertFalse(cloud.in_window(event, datetime(2026, 11, 2, tzinfo=timezone.utc)))
        self.assertTrue(cloud.in_window(event, datetime(2026, 11, 6, tzinfo=timezone.utc)))
        self.assertFalse(cloud.in_window(self.event, datetime(2026, 11, 6, tzinfo=timezone.utc)))

    def test_identical_discovered_weekend_prefers_explicit_configuration(self):
        event = weekend.load_event(ROOT / 'operacao2026/eventos/saopaulo2026.json')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            explicit = root / 'operacao2026/eventos/saopaulo2026.json'
            discovered = root / cloud.STATE / 'configuracoes/interlagos-2026.json'
            for path in (explicit, discovered):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(event))
            selected = cloud.discover(root, datetime(2026, 11, 6, tzinfo=timezone.utc),
                                      client_factory=lambda *a: self.fail('No HTTP needed'))
            self.assertEqual(selected, explicit)
            # A genuinely different schedule cannot be silently selected.
            event['sessions'][0]['date_end'] = '2026-11-06T17:30:00+00:00'
            discovered.write_text(json.dumps(event))
            with self.assertRaisesRegex(ValueError, 'Overlapping'):
                cloud.discover(root, datetime(2026, 11, 6, tzinfo=timezone.utc))



if __name__ == '__main__':
    unittest.main()
