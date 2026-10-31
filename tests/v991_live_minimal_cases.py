"""Durable actual-App Directo minimal-mode cases for the owned V991 worker.

No App import, fresh App/Runtime, standalone Flask or guards are created here.
The caller supplies the SAME Runtime used by the eleven API prepare-only cases.
"""
from collections import Counter
from contextlib import closing, contextmanager
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET


class LiveMinimalContracts(unittest.TestCase):
    runtime = None

    def setUp(self):
        self.r = self.runtime
        self.a = self.r.app
        self.r.seed(live=True)
        self.details = []

    def tearDown(self):
        after = self.r.table_hashes()
        self.assertEqual(self.r.business_before, after)
        self.r.business_checks.append({'test':self.id(), 'before':self.r.business_before, 'after':after, 'equal':True})
        self.r.live_minimal_details.append({'test':self.id(), 'details':self.details})

    @contextmanager
    def captured(self):
        from flask import template_rendered
        data = []
        def observe(sender, template, context, **kwargs):
            data.append(context.get('data') or {})
        template_rendered.connect(observe, self.a.app, weak=False)
        try:
            yield data
        finally:
            template_rendered.disconnect(observe, self.a.app)

    def test_01_actual_aliases_five_roles_own_members_and_fresh_boundaries(self):
        expected = sorted(row['id'] for row in self.r.rows)
        for role in self.r.clients:
            for route in ('/live', '/live-center', '/directo', '/en-directo'):
                with self.subTest(role=role, route=route), self.captured() as contexts:
                    response, _, probe = self.r.request({'f':'live'}, role=role, path=route)
                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(contexts)
                    data = contexts[-1]
                    experience = data['live_experience']
                    self.assertEqual(data['v932_authenticated_scope'], 'client')
                    self.assertEqual(data['v931_route_guard']['status'], 'compact_read_only_context')
                    self.assertNotIn('home_summary', data)
                    self.assertNotIn('v925_calendar', data)
                    self.assertNotIn('v925_live', data)
                    self.assertEqual(experience['sports_metrics']['matches_today'], 2)
                    self.assertEqual(experience['sports_metrics']['live_confirmed'], 2)
                    self.assertEqual(experience['sports_metrics']['snapshot_id'], data['sports_metrics']['snapshot_id'])
                    self.assertEqual(len(experience['matches']), 2)
                    self.assertIn('sdb-901003', [row['id'] for row in experience['matches']])
                    for row in experience['matches']:
                        self.assertIn(row['id'], expected)
                        own = row['realtime_state']
                        self.assertEqual((own['score_home'],own['score_away']), (1,0))
                        self.assertTrue(own['provider_observed_at'])
                        self.assertTrue(own['live_valid_until_madrid'])
                    html = response.get_data(as_text=True)
                    scripts = re.findall(r'<script\b(?=[^>]*\bdata-directo-fixture-identity\b)[^>]*>(.*?)</script>', html, re.S)
                    self.assertEqual(len(scripts), 1)
                    bootstrap = json.loads(scripts[0])
                    self.assertEqual(sorted(row['id'] for row in bootstrap['matches']), expected)
                    self.assertEqual(bootstrap['fixture_identity']['general']['counts']['live'], 2)
                    counts = self.r.totals(probe)
                    builds = [row for row in probe['calls'] if row['function']=='build_sports_metrics_contract']
                    acceptance = sum(row['cache_acceptance'] for row in builds)
                    self.assertEqual(len(builds)-acceptance, 2)
                    self.assertIn(acceptance, (0,1))
                    self.assertEqual(counts['get_sports_metrics_contract'], 2)
                    self.assertEqual(self.r.post_finish(probe, 'build_sports_metrics_contract'), 0)
                    self.assertEqual(counts['_v931_minimal_client_data'], 0)
                    self.assertEqual(counts['_v931_legacy_home_summary'], 0)
                    self.assertEqual(counts['_v931_provider_context'], 0)
                    self.assertEqual(counts['get_v932_real_sports_value_context'], 1)
                    self.assertLessEqual(probe['reference_PK_batches'], 1)
                    self.details.append({'role':role,'route':route,'metrics_builds':len(builds),
                        'cache_acceptance_builds':acceptance,'consumer_builds':len(builds)-acceptance,
                        'member_ids':expected,'retained_card_ids':[row['id'] for row in experience['matches']]})

    def test_02_default_flags_and_noncompact_fallback_keep_legacy_contract(self):
        for value in (False, None, 1, 'true'):
            with self.subTest(flag=value), self.r.context('/live'):
                summary = self.a.get_public_home_sports_summary()
                data, owner = self.a.v932_safe_dashboard_data('/live', compact=True, sports_summary=summary, _directo_minimal=value)
                self.assertIs(owner, summary)
                self.assertIn('home_summary', data)
                self.assertIn('match_hub', data)
                self.assertIn('v925_live', data)
                self.assertEqual(data['sports_metrics']['live_confirmed'], 2)
        # The actual FULL callback is fault-injected at its boundary, not bypassed:
        # compact=False must still invoke it and preserve its real safe fallback.
        owned_log_root = self.r.out/'live-minimal-full-fallback'
        with self.r.context('/live'), patch.object(self.a, 'BASE_DIR', owned_log_root):
            summary = self.a.get_public_home_sports_summary()
            with patch.object(self.a, 'dashboard_data', side_effect=RuntimeError('synthetic_full_dashboard_failure')) as callback:
                data, owner = self.a.v932_safe_dashboard_data('/live', compact=False, sports_summary=summary, _directo_minimal=True)
            callback.assert_called_once()
            self.assertIs(owner, summary)
            self.assertIn('home_summary', data)
            self.assertIn('match_hub', data)
            self.assertEqual(data['v931_route_guard']['status'], 'safe_fallback')
            self.assertEqual(data['sports_metrics']['live_confirmed'], 2)

    def test_03_locked_actual_logs_precede_formatting_and_preserve_scopes(self):
        from flask import request
        for role in ('anonymous', 'pro', 'admin'):
            events = []
            codes = {self.a.v931_record_client_route_issue.__code__:'client_log',
                     self.a.v932_record_authenticated_issue.__code__:'authenticated_log'}
            def profile(frame, event, arg):
                if event == 'call':
                    if frame.f_code in codes:
                        events.append({'name':codes[frame.f_code], 'scope':frame.f_locals.get('scope')})
                    elif frame.f_code.co_name == '_directo_client_data' and Path(frame.f_code.co_filename).resolve() == Path(self.a.__file__).resolve():
                        events.append({'name':'minimal_formatter'})
            with self.subTest(role=role), self.r.context('/live'), patch.object(self.a, 'BASE_DIR', self.r.out/('live-locked-'+role)):
                if role != 'anonymous': self.a.set_login_session(self.a.get_user_by_id('prepare-only-'+role))
                summary = self.a._v932_locked_sports_summary()
                previous = sys.getprofile()
                self.assertIsNone(previous)
                sys.setprofile(profile)
                try:
                    data, owner = self.a.v932_safe_dashboard_data('/live', compact=True, sports_summary=summary, _directo_minimal=True)
                finally:
                    sys.setprofile(previous)
                self.assertIs(owner, summary)
                self.assertTrue(request.environ['nemesis.v931.degraded'])
                self.assertEqual(data['v931_route_guard']['status'], 'safe_fallback')
                names = [event['name'] for event in events]
                self.assertEqual(names[0], 'client_log')
                self.assertEqual(names[-1], 'minimal_formatter')
                if role == 'anonymous': self.assertNotIn('authenticated_log', names)
                else:
                    self.assertEqual(names, ['client_log','authenticated_log','minimal_formatter'])
                    self.assertEqual(events[1]['scope'], 'admin' if role=='admin' else 'client')
                self.assertTrue((Path(self.a.BASE_DIR)/'data/runtime/sentinel_client_route_issues.json').is_file())
                if role != 'anonymous': self.assertTrue((Path(self.a.BASE_DIR)/'data/runtime/sentinel_authenticated_issues.json').is_file())
                self.details.append({'role':role,'events':events,'degraded':True})

    def test_04_preserved_real_provider_callback_mutation_rebuilds_unknown(self):
        with self.r.context('/live'):
            summary = self.a.get_public_home_sports_summary()
            operation = self.a._v991_operation_for(summary)
            row = next(row for row in summary['all_valid_matches'] if row['source']=='api_football_live' and row.get('competition_key')=='laliga')
            self.assertEqual(operation.snapshot.context_for(row).state, 'RESOLVED')
            before = summary['sports_metrics']
            self.assertEqual(before['matches_available'], 2)
            mutated = []
            def adversary(frame, event, arg):
                if event == 'return' and frame.f_code is self.a.get_v932_real_sports_value_context.__code__ and not mutated:
                    row['home_canonical_team_id'] = 'synthetic-live-after-provider-callback'
                    mutated.append(True)
            previous = sys.getprofile()
            self.assertIsNone(previous)
            sys.setprofile(adversary)
            try:
                data, owner = self.a.v932_safe_dashboard_data('/live', compact=True, sports_summary=summary, _directo_minimal=True)
            finally:
                sys.setprofile(previous)
            self.assertEqual(mutated, [True])
            self.assertIs(owner, summary)
            self.assertIs(self.a._v991_operation_for(summary), operation)
            self.assertEqual(operation.snapshot.context_for(row).state, 'UNKNOWN_IDENTITY_CHANGED')
            self.assertEqual(before['matches_available'], 2)
            self.assertEqual(data['sports_metrics']['matches_available'], 3)
            self.assertNotEqual(data['sports_metrics']['snapshot_id'], before['snapshot_id'])
            self.assertEqual({r['id'] for r in operation.snapshot.select_rows(summary['all_valid_matches']).raw_rows}, {r['id'] for r in self.r.rows})
            self.details.append({'callback_executed_real':True,'state':'UNKNOWN_IDENTITY_CHANGED','old_count':2,'fresh_count':3,'rebindings':0})

    def test_05_actual_missing_HTML_is_unknown_and_known_empty_is_zero(self):
        self.r.seed(empty=True)
        with closing(sqlite3.connect(self.r.db)) as conn:
            self.assertEqual(conn.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0], 0)
        original = hashlib.sha256(self.r.db.read_bytes()).hexdigest()
        files = [self.r.db]+[Path(str(self.r.db)+suffix) for suffix in ('-wal','-shm','-journal')]
        moves = [(p,self.r.out/('live-missing-preserved-'+p.name)) for p in files if p.exists()]
        self.assertTrue(all(p.resolve().is_relative_to(self.r.out) and q.resolve().is_relative_to(self.r.out) and not q.exists() for p,q in moves))
        moved = []
        fully_moved = False
        try:
            for path, backup in moves:
                path.rename(backup); moved.append((path,backup))
            fully_moved = True
            self.r.invalidate()
            with self.captured() as contexts:
                response, _, _ = self.r.request({}, path='/live', headers={'Accept-Language':'es'})
            self.assertEqual(response.status_code, 200)
            data = contexts[-1]
            self.assertEqual(data['v934_realtime']['source_snapshot_state'], 'READ_UNAVAILABLE')
            identity = data['live_experience']['fixture_identity']
            self.assertEqual(identity['state'], 'NOT_ESTABLISHED')
            self.assertTrue(all(value is None for value in identity['general']['counts'].values()))
            html = response.get_data(as_text=True)
            notices = re.findall(r'<p\b([^>]*\bdata-directo-notice[^>]*)>(.*?)</p>', html, re.S|re.I)
            self.assertTrue(notices)
            self.assertFalse(re.search(r'\bhidden(?:\s|=|$)', notices[0][0]))
            self.assertIn('Datos no disponibles temporalmente', html)
            self.assertNotIn('No hay partidos para este estado', html)
        finally:
            for path in files if fully_moved else ():
                if path.exists():
                    target=self.r.out/('live-missing-auto-created-'+path.name)
                    if target.exists(): raise RuntimeError('Refusing to overwrite preserved synthetic missing-store evidence')
                    path.rename(target)
            for path, backup in reversed(moved): backup.rename(path)
        self.assertEqual(hashlib.sha256(self.r.db.read_bytes()).hexdigest(), original)
        self.r.invalidate()
        with self.captured() as contexts:
            response, _, _ = self.r.request({}, path='/live', headers={'Accept-Language':'es'})
        self.assertEqual(response.status_code, 200)
        data = contexts[-1]
        self.assertEqual(data['v934_realtime']['source_snapshot_state'], 'LOCAL_SNAPSHOT')
        identity = data['live_experience']['fixture_identity']
        self.assertEqual(identity['state'], 'ESTABLISHED_FOR_EMITTED_COHORT')
        self.assertTrue(all(type(value) is int and value==0 for value in identity['general']['counts'].values()))
        self.assertIn('No hay partidos para este estado', response.get_data(as_text=True))


def run_live_contracts(runtime):
    LiveMinimalContracts.runtime = runtime
    runtime.live_minimal_details = []
    # Only extend observation metadata; no product getter/handler binding changes.
    extra = ('get_sports_metrics_contract','_v931_minimal_client_data', '_v931_legacy_home_summary',
             '_v931_provider_context','get_v932_real_sports_value_context')
    old_codes = dict(runtime.codes)
    runtime.codes.update({getattr(runtime.app,name).__code__:name for name in extra})
    start_requests, start_observations, start_business = len(runtime.requests), len(runtime.observations), len(runtime.business_checks)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LiveMinimalContracts)
    text = io.StringIO()
    try:
        result = unittest.TextTestRunner(stream=text, verbosity=2).run(suite)
    finally:
        runtime.codes.clear(); runtime.codes.update(old_codes)
    (runtime.out/'live-unittest-output.txt').write_text(text.getvalue(),encoding='utf-8')
    xml = ET.Element('testsuite',name='V991 Live minimal actual App',tests=str(result.testsRun), failures=str(len(result.failures)),errors=str(len(result.errors)))
    for test, trace in result.failures+result.errors:
        ET.SubElement(ET.SubElement(xml,'testcase',name=test.id()),'failure').text=trace
    ET.ElementTree(xml).write(runtime.out/'live-junit.xml',encoding='utf-8',xml_declaration=True)
    return {'unittest_run':result.testsRun,'failures':[{'test':t.id(),'trace':s} for t,s in result.failures],
            'errors':[{'test':t.id(),'trace':s} for t,s in result.errors], 'requests':runtime.requests[start_requests:],
            'observational_calls':runtime.observations[start_observations:], 'business_SQL_checks':runtime.business_checks[start_business:],
            'details':runtime.live_minimal_details,'App_getter_normalizer_C3_rebindings':0,
            'dashboard_fault_injection':'one compact=False fallback only; healthy HTTP handlers/wrappers real',
            'success':result.wasSuccessful()}
