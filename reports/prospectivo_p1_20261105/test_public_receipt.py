"""Server-metadata fixtures only; no publication or HTTP request."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pair_predictions as p
import verify_published_pair as v


class PublicReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        clock = patch.object(v, 'utc_now', return_value=p.utc('2026-11-07T20:06:00Z')); clock.start(); self.addCleanup(clock.stop)
        self.path = Path(self.tmp.name)/'paired-probabilities.json'
        self.pair = {'schema': 'pitwall-p1-prepared-pair-v1', 'status': 'prepared_not_published',
            'event': {'temporada': '2026', 'rodada': '20', 'circuito_id': 'interlagos'},
            'q_baseline_sha256': p.Q_SHA, 'v1_model_hashes': p.V1_HASHES, 'cutoff_utc': '2026-11-07T20:00:00Z',
            'created_at_utc': '2026-11-07T20:01:00Z', 'public_receipt_required_before_utc': '2026-11-08T16:00:00Z',
            'fitting_performed': False, 'current_targets_read': False,
            'v1_manifest_sha256': '0'*64, 'v1_inputs_sha256': '1'*64, 'v1_probabilities_sha256': '2'*64,
            'pairs': [{'temporada': '2026', 'rodada': '20', 'circuito_id': 'interlagos',
                'piloto_id': 'fixture-driver-'+str(i), 'equipe_id_entrada': 'fixture-team',
                'probabilidade_v1': .15, 'probabilidade_q': .15} for i in range(22)]}
        self.path.write_text(json.dumps(self.pair)); self.asset = {'id': 123, 'state': 'uploaded',
            'digest': 'sha256:'+p.sha(self.path), 'size': self.path.stat().st_size,
            'created_at': '2026-11-07T20:05:00Z', 'updated_at': '2026-11-07T20:05:01Z',
            'browser_download_url': 'https://github.com/mbpaschoal/pitwall-lab/releases/download/vFIXTURE/pair.json'}

    def test_server_metadata_confirms_public_bytes_without_rewriting_pair(self):
        before = self.path.read_bytes(); receipt = v.validate(self.path, self.asset)
        self.assertTrue(receipt['publication_verified']); self.assertEqual(before, self.path.read_bytes())

    def test_late_creation_or_update_or_boundary_rejects(self):
        for field in ['created_at', 'updated_at']:
            asset = deepcopy(self.asset); asset[field] = '2026-11-08T16:00:00Z'
            with self.assertRaises(ValueError): v.validate(self.path, asset)

    def test_metadata_cannot_retrodate_pair_calculated_after_upload(self):
        asset = deepcopy(self.asset); asset['created_at'] = '2026-11-07T20:00:01Z'
        with self.assertRaises(ValueError): v.validate(self.path, asset)

    def test_changed_hash_size_state_and_foreign_repository_reject(self):
        for field, value in [('digest', 'sha256:changed'), ('size', 0), ('state', 'new'),
                             ('browser_download_url', 'https://example.com/pair.json')]:
            asset = deepcopy(self.asset); asset[field] = value
            with self.assertRaises(ValueError): v.validate(self.path, asset)

    def test_changed_model_or_target_use_rejects(self):
        for field, value in [('q_baseline_sha256', 'changed'), ('current_targets_read', True), ('fitting_performed', True)]:
            changed = deepcopy(self.pair); changed[field] = value; self.path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError): v.validate(self.path, self.asset)

    def test_after_race_audit_does_not_create_after_race_forecast(self):
        with patch.object(v, 'utc_now', return_value=p.utc('2026-11-09T12:00:00Z')):
            receipt = v.validate(self.path, self.asset)
        self.assertTrue(receipt['publication_verified']); self.assertIn('2026-11-07', receipt['asset_created_at_utc'])

    def test_no_arbitrary_url_or_existing_receipt_allowed(self):
        with self.assertRaises(ValueError): v.verify(self.path, '../other', self.path.parent/'new.json')
        with self.assertRaises(FileExistsError): v.verify(self.path, 123, self.path)

    def test_incomplete_foreign_or_invalid_probability_pair_rejects(self):
        for alteration in ['empty', 'foreign', 'invalid']:
            pair = deepcopy(self.pair)
            if alteration == 'empty': pair['pairs'] = []
            elif alteration == 'foreign': pair['pairs'][0]['circuito_id'] = 'americas'
            else: pair['pairs'][0]['probabilidade_q'] = 1.2
            self.path.write_text(json.dumps(pair))
            with self.assertRaises(ValueError): v.validate(self.path, self.asset)

    def test_future_server_time_or_missing_native_hash_rejects(self):
        with patch.object(v, 'utc_now', return_value=p.utc('2026-11-07T20:04:00Z')):
            with self.assertRaises(ValueError): v.validate(self.path, self.asset)
        pair = deepcopy(self.pair); del pair['v1_inputs_sha256']; self.path.write_text(json.dumps(pair))
        with self.assertRaises(ValueError): v.validate(self.path, self.asset)


if __name__ == '__main__': unittest.main()
