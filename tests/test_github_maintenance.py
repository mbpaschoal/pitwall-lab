"""Out-of-order publication and incident transitions, without real API writes."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import unittest

from operacao2026.github_maintenance import (
    INCIDENT_MARKER, all_pages, collection_health, latest_candidate, monitor, repair_latest,
)

NOW = datetime(2026, 11, 3, 18, tzinfo=timezone.utc)


def release(tag, **changes):
    row = dict(id=int(tag.split('.')[-1]), tag_name=tag, published_at='2026-11-03T00:00:00Z',
               draft=False, prerelease=False,
               assets=[dict(name='pitwall-dashboard.zip', state='uploaded', size=100, digest='sha256:'+'a'*64)])
    row.update(changes)
    return row


def run(conclusion='success', number=10, **changes):
    row = dict(id=number, run_number=number, head_branch='main', event='schedule', status='completed',
               conclusion=conclusion, updated_at='2026-11-03T17:40:00Z',
               html_url='https://github.com/mbpaschoal/pitwall-lab/actions/runs/'+str(number))
    row.update(changes)
    return row


class FakeAPI:
    def __init__(self, runs=None, issues=None):
        self.runs = runs or [run()]
        self.issues = issues or []
        self.writes = []

    def __call__(self, method, path, body=None):
        if method == 'GET':
            return {'workflow_runs': self.runs} if '/actions/' in path else self.issues
        self.writes.append((method, path, deepcopy(body)))
        return dict(number=7)


class MaintenanceTests(unittest.TestCase):
    def test_numeric_order_beats_publication_order_and_lexical_order(self):
        rows = [release('v0.8.19'), release('v0.8.9'), release('v0.8.20')]
        self.assertEqual(latest_candidate(rows, '0.8.21')['tag_name'], 'v0.8.20')
        self.assertEqual(rows[0]['tag_name'], 'v0.8.19')

    def test_unpublished_prerelease_missing_upload_and_future_main_are_excluded(self):
        rows = [release('v0.8.20'), release('v0.8.21', assets=[]),
                release('v0.8.22', draft=True), release('v0.8.23', prerelease=True),
                release('v0.8.24', published_at=None), release('v0.8.99')]
        self.assertEqual(latest_candidate(rows, '0.8.24')['tag_name'], 'v0.8.20')
        rows[0]['assets'][0]['state'] = 'new'
        with self.assertRaisesRegex(ValueError, 'No complete'):
            latest_candidate(rows, '0.8.20')

    def test_missing_digest_and_non_product_tags_cannot_be_promoted(self):
        row = release('v0.8.20'); row['assets'][0].pop('digest')
        with self.assertRaises(ValueError): latest_candidate([row, release('v01.8.21')], '0.8.21')

    def test_newer_existing_highlight_is_never_demoted_on_a_partial_inventory(self):
        writes=[]
        def api(method,path,body=None):
            if method!='GET':writes.append((method,path))
            if 'contents/VERSION' in path:return {'content':base64.b64encode(b'0.8.22').decode()}
            if path=='/releases/latest':return release('v0.8.21')
            return [release('v0.8.20')]
        with self.assertRaisesRegex(ValueError,'demote'):repair_latest(api,True)
        self.assertFalse(writes)

    def test_repair_has_a_read_only_preview_and_idempotent_verification(self):
        current = release('v0.8.19'); writes = []
        def api(method, path, body=None):
            nonlocal current
            if method == 'PATCH':
                writes.append(body); current=release('v0.8.20');return current
            if 'contents/VERSION' in path:
                return {'content': base64.b64encode(b'0.8.21\n').decode()}
            if path == '/releases/latest':return current
            return [release('v0.8.19'), release('v0.8.20')]
        self.assertEqual(repair_latest(api)['selected'], 'v0.8.20')
        self.assertFalse(writes)
        self.assertTrue(repair_latest(api, True)['applied'])
        self.assertFalse(repair_latest(api, True)['changed'])
        self.assertEqual(writes, [{'make_latest': 'true'}])

    def test_pagination_does_not_silently_ignore_an_inventory_tail(self):
        pages=[]
        def api(method,path,body=None):
            pages.append(path)
            return list(range(100)) if 'page=1' == path.split('&')[-1] else [101]
        self.assertEqual(len(all_pages(api, '/releases')),101)
        self.assertEqual(len(pages),2)
        with self.assertRaisesRegex(ValueError,'pagination'):
            all_pages(lambda *args: list(range(100)), '/releases')

    def test_success_pending_and_stale_runs_have_distinct_meaning(self):
        self.assertIsNone(collection_health([run(),run(None,11,status='in_progress')], NOW)['problem'])
        self.assertEqual(collection_health([run(updated_at='2026-11-03T10:00:00Z')],NOW)['problem'],'collection_stale')
        self.assertEqual(collection_health([run(head_branch='untrusted')],NOW)['problem'],'no_completed_collection')
        with self.assertRaisesRegex(ValueError,'Future'):
            collection_health([run(updated_at='2026-11-04T10:00:00Z')],NOW)

    def test_failure_opens_once_repeated_failure_is_quiet_and_success_resolves(self):
        api=FakeAPI([run('failure')]);preview=monitor(api,NOW)
        self.assertEqual(preview['action'],'open_incident');self.assertFalse(api.writes)
        monitor(api,NOW,True)
        self.assertEqual(len(api.writes),1)
        payload=api.writes[0][2]
        self.assertIn('Português',payload['body']);self.assertIn('English',payload['body'])
        api.issues=[dict(number=7,body=payload['body'],user={'login':'github-actions[bot]'})]
        api.writes.clear()
        self.assertEqual(monitor(api,NOW,True)['action'],'unchanged');self.assertFalse(api.writes)
        api.runs=[run(number=12),run('failure')]
        self.assertEqual(monitor(api,NOW,True)['action'],'resolve_incident')
        self.assertEqual([a[0] for a in api.writes],['POST','PATCH'])
        self.assertEqual(api.writes[-1][2],{'state':'closed','state_reason':'completed'})

    def test_unrelated_and_forged_issues_are_never_closed(self):
        issues=[dict(number=8,body=INCIDENT_MARKER,user={'login':'other-user'}),
                dict(number=9,body='manual issue',user={'login':'github-actions[bot]'})]
        api=FakeAPI(issues=issues)
        self.assertEqual(monitor(api,NOW,True)['action'],'unchanged');self.assertFalse(api.writes)

    def test_duplicate_incidents_and_foreign_links_fail_without_writes(self):
        issue=dict(number=7,body=INCIDENT_MARKER,user={'login':'github-actions[bot]'})
        api=FakeAPI(issues=[issue,dict(issue,number=8)])
        with self.assertRaisesRegex(ValueError,'Duplicate'):monitor(api,NOW,True)
        self.assertFalse(api.writes)
        api=FakeAPI([run('failure',html_url='https://example.org')])
        with self.assertRaisesRegex(ValueError,'Foreign'):monitor(api,NOW,True)
        self.assertFalse(api.writes)


if __name__=='__main__':unittest.main()
