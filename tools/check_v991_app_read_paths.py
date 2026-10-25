"""Standalone CI unittest gate; the parent never imports App or installs guards."""
from __future__ import annotations
import argparse
from functools import lru_cache
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).with_name('v991_app_read_path_worker.py')
OUTPUT = None

@lru_cache(maxsize=1)
def receipt():
    output = OUTPUT or Path(tempfile.mkdtemp(prefix='nemesis-v991-app-'))
    output.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-B', str(WORKER), '--repo-root', str(REPO), '--output-dir', str(output)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    result = subprocess.run(command, cwd=REPO, env=env, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=180)
    (output/'worker.stdout.txt').write_text(result.stdout, encoding='utf-8')
    (output/'worker.stderr.txt').write_text(result.stderr, encoding='utf-8')
    if result.returncode:
        raise AssertionError('Fresh App worker failed; evidence at '+str(output)+'\n'+result.stdout[-3000:]+result.stderr[-1000:])
    return json.loads((output/'receipt.json').read_text(encoding='utf-8'))

class AppReadPathContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = receipt()

    def test_01_real_app_isolated_and_sources_unchanged(self):
        e = self.evidence
        self.assertEqual(e['errors'], [])
        self.assertEqual(e['boundary_events'], [])
        self.assertTrue(e['sources_unchanged'])
        self.assertTrue(e['actual_app_file'])
        self.assertTrue(e['database_is_external'])
        self.assertTrue(e['blueprints'])
        self.assertLessEqual(max(e['reference_reads_per_request']), 1)
        self.assertGreaterEqual(sum(e['reference_reads_per_request']), 1)

    def test_02_real_roles_and_registered_handlers(self):
        for role, fact in self.evidence['roles'].items():
            with self.subTest(role=role):
                self.assertEqual(fact['home_http'], 200)
                self.assertEqual(fact['app_http'], 302 if role == 'anonymous' else 200)
        self.assertEqual(set(self.evidence['roles']), {'anonymous','free','pro','elite','admin'})
        self.assertTrue(all(item['unique'] and item['module'] == 'app' for item in self.evidence['bindings']))

    def test_03_home_and_calendar_share_group_count(self):
        for role, fact in self.evidence['roles'].items():
            with self.subTest(role=role):
                self.assertEqual(fact['raw_count'], 3)
                self.assertEqual(fact['today_count'], 2)
                self.assertEqual(len(fact['home_live_ids']), 2)
                self.assertIn('sdb-901003', fact['home_live_ids'])
        calendar = self.evidence['calendar']
        self.assertEqual(calendar['http'], 200)
        self.assertEqual(len(calendar['ids']), 2)
        self.assertEqual(calendar['today_count'], 2)
        self.assertEqual(calendar['raw_count'], 3)

    def test_04_directo_real_html_maps_all_original_members(self):
        expected = ['af-901001','sdb-901002','sdb-901003']
        for route, fact in self.evidence['live'].items():
            with self.subTest(route=route):
                self.assertEqual(fact['http'], 200)
                self.assertEqual(fact['bootstrap_count'], 1)
                self.assertEqual(fact['member_ids'], expected)
                self.assertEqual(fact['emitted_ids'], expected)
                self.assertEqual(fact['live_count'], 2)
                self.assertEqual(fact['view_count'], 2)
                self.assertEqual(len(fact['rendered_ids']), 2)
                self.assertIn('sdb-901003', fact['rendered_ids'])
                self.assertEqual(fact['groups']['af-901001'], fact['groups']['sdb-901002'])
                self.assertNotEqual(fact['groups']['af-901001'], fact['groups']['sdb-901003'])

    def test_05_current_picks_and_odds_retain_legacy_evidence(self):
        self.assertEqual(self.evidence['publishable_pick_ids'], ['v991-ci-pick-1','v991-ci-pick-2'])
        for fact in self.evidence['retention']:
            with self.subTest(role=fact['role'], scope=fact['scope']):
                self.assertEqual(fact['http'], [200,200])
                self.assertEqual(fact['modern'], fact['legacy'])
                if fact['role'] in {'pro','elite'}:
                    self.assertEqual(len(fact['legacy']), 2)

    def test_06_unavailable_is_not_an_observed_zero(self):
        for consumer, fact in self.evidence['missing'].items():
            with self.subTest(consumer=consumer):
                self.assertEqual(fact['storage_status'], 'missing_database')
                self.assertEqual(fact['state'], 'NOT_ESTABLISHED')
                self.assertEqual(fact['snapshot_state'], 'READ_UNAVAILABLE')
                self.assertTrue(fact['counts'])
                self.assertTrue(all(value is None for value in fact['counts'].values()))
        self.assertTrue(self.evidence['original_database_restored'])

    def test_07_verified_empty_can_be_zero(self):
        for consumer, fact in self.evidence['empty'].items():
            with self.subTest(consumer=consumer):
                self.assertEqual(fact['storage_status'], 'ok')
                self.assertEqual(fact['state'], 'ESTABLISHED_FOR_EMITTED_COHORT' if consumer == 'directo-v2' else 'ESTABLISHED_FOR_CURRENT_COHORT')
                self.assertEqual(fact['snapshot_state'], 'LOCAL_SNAPSHOT')
                self.assertTrue(fact['counts'])
                self.assertTrue(all(type(value) is int and value == 0 for value in fact['counts'].values()))

    def test_08_validators_change_with_proof_without_renewing_live_lease(self):
        for consumer in ('directo-v2','fixture-metrics-v1'):
            self.assertNotEqual(self.evidence['missing'][consumer]['etag'], self.evidence['empty'][consumer]['etag'])
            self.assertEqual(self.evidence['empty'][consumer]['conditional_old_missing_http'], 200)
        live = self.evidence['live_poll']
        self.assertEqual(live['http'], [200,304,200])
        self.assertEqual(live['conditional_bytes'], 0)
        self.assertTrue(live['first_etag'].startswith('W/'))
        self.assertEqual(live['first_etag'], live['last_etag'])
        self.assertEqual(live['first_clocks'], live['last_clocks'])
        self.assertEqual(live['first_ids'], ['af-901001','sdb-901002','sdb-901003'])

    def test_09_first_html_distinguishes_unavailable_from_verified_empty(self):
        for language in ('es','en','fr'):
            with self.subTest(language=language):
                missing = self.evidence['missing_html'][language]
                empty = self.evidence['empty_html'][language]
                self.assertEqual(missing['http'], 200)
                self.assertEqual(missing['storage_status'], 'missing_database')
                self.assertTrue(missing['notice_visible'])
                self.assertTrue(missing['expected_title_present'])
                self.assertTrue(missing['expected_notice_present'])
                self.assertFalse(missing['confirmed_empty_title_present'])
                self.assertEqual(empty['http'], 200)
                self.assertEqual(empty['storage_status'], 'ok')
                self.assertFalse(empty['notice_visible'])
                self.assertFalse(empty['expected_title_present'])
                self.assertTrue(empty['confirmed_empty_title_present'])

    def test_10_pages_without_realtime_bar_do_not_build_unused_descriptors(self):
        calls = self.evidence['fixture_projection_requests']
        for path in ('/','/app','/calendario'):
            observed = [item for item in calls if item['path'] == path]
            self.assertTrue(observed, path)
            for item in observed:
                with self.subTest(path=path, role=item['role']):
                    self.assertEqual(item['calls'], 0)
        active = [item for item in calls if item['path'] in {'/live','/directo','/en-directo','/api/realtime/sports'}]
        self.assertTrue(any(item['calls'] > 0 for item in active), 'Profiler must observe real used projections')
        calendar = self.evidence['calendar_html']
        self.assertEqual(calendar['http'], 200)
        self.assertEqual(calendar['count'], 2)
        self.assertEqual(len(calendar['ids']), 2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--repo-root', type=Path)
    parser.add_argument('--output-dir', type=Path)
    args, rest = parser.parse_known_args()
    if args.repo_root: REPO = args.repo_root.resolve()  # External review only; installed default is file-relative.
    if args.output_dir: OUTPUT = args.output_dir.resolve()
    unittest.main(argv=[sys.argv[0], *rest])
