"""Counterexamples for token, checkout and workflow trust boundaries."""
import copy
from pathlib import Path
import unittest

import yaml

from scripts.security.check_workflows import check, validate_workflow


ROOT = Path(__file__).resolve().parents[1]
SHA = 'a' * 40


class SecurityPolicyTests(unittest.TestCase):
    def workflow(self):
        return {'on': {'pull_request': None}, 'permissions': {'contents': 'read'},
                'jobs': {'test': {'steps': [{'uses': 'actions/checkout@' + SHA,
                                            'with': {'persist-credentials': False}}]}}}

    def test_current_workflows_obey_policy(self):
        self.assertEqual(check(ROOT), [])

    def test_fork_code_cannot_gain_write_permissions(self):
        workflow = self.workflow()
        workflow['jobs']['test']['permissions'] = {'contents': 'write'}
        errors = validate_workflow('product.yml', workflow)
        self.assertTrue(any('write token' in error for error in errors))

    def test_persisted_checkout_and_mutable_action_are_rejected(self):
        workflow = self.workflow()
        checkout = workflow['jobs']['test']['steps'][0]
        checkout['with']['persist-credentials'] = True
        checkout['uses'] = 'actions/checkout@v6'
        self.assertEqual(len(validate_workflow('product.yml', workflow)), 2)

    def test_workflow_run_never_checks_out_triggering_head(self):
        workflow = self.workflow()
        workflow['on'] = {'workflow_run': {'types': ['completed']}}
        workflow['jobs']['test']['steps'][0]['with']['ref'] = '${{ github.event.workflow_run.head_sha }}'
        self.assertTrue(any('trusted main' in error for error in validate_workflow('maintenance.yml', workflow)))

    def test_event_data_cannot_become_executable_shell(self):
        workflow = self.workflow()
        workflow['jobs']['test']['steps'].append({'run': 'echo "${{ github.event.pull_request.title }}"'})
        self.assertTrue(any('interpolated' in error for error in validate_workflow('product.yml', workflow)))

    def test_collection_guard_cannot_be_relaxed(self):
        path = ROOT / '.github/workflows/coletar-dados.yml'
        workflow = yaml.safe_load(path.read_text())
        workflow['jobs']['collect']['if'] = "github.repository == 'mbpaschoal/pitwall-lab'"
        self.assertTrue(any('trusted main' in error for error in validate_workflow(path.name, workflow)))

    def test_privileged_release_cannot_lose_tag_gate(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/product.yml').read_text())
        workflow['jobs']['release']['if'] = 'always()'
        self.assertTrue(any('write token' in error for error in validate_workflow('product.yml', workflow)))


if __name__ == '__main__':
    unittest.main()
