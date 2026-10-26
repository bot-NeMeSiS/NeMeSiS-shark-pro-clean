"""Real /picks efficiency and isolation contracts, run by the guarded V991 worker.

The supervisor imports this module only after its original boundary and fixtures
are active. Observations extend its profiler; App functions are never replaced.
"""
from contextlib import closing, contextmanager
from copy import deepcopy
from datetime import datetime, timedelta
import io
import json
import sqlite3
import unittest
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo


def mutable_ids(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return set()
    seen.add(id(value))
    if isinstance(value, dict):
        result = {id(value)}
        for item in value.values():
            result.update(mutable_ids(item, seen))
        return result
    if isinstance(value, (list, tuple, set)):
        result = set() if isinstance(value, tuple) else {id(value)}
        for item in value:
            result.update(mutable_ids(item, seen))
        return result
    return set()


class PicksProjectionContracts(unittest.TestCase):
    runtime = None

    def setUp(self):
        self.r, self.a = self.runtime, self.runtime.app
        self.r.seed()
        self.read_checks = []

    def tearDown(self):
        after = self.r.table_hashes()
        self.assertEqual(self.r.business_before, after)
        self.r.business_checks.append({'test': self.id(), 'before': self.r.business_before,
            'after': after, 'equal': True, 'HTTP_reads': self.read_checks})

    @contextmanager
    def captured(self):
        from flask import template_rendered
        contexts = []
        def receive(sender, template, context, **kwargs):
            contexts.append(context.get('data') or {})
        template_rendered.connect(receive, self.a.app, weak=False)
        try:
            yield contexts
        finally:
            template_rendered.disconnect(receive, self.a.app)

    def page(self, role='anonymous'):
        before = self.r.table_hashes()
        with self.captured() as contexts:
            response, _, probe = self.r.request({}, path='/picks', role=role)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(contexts)
        self.assertEqual(self.r.table_hashes(), before)
        self.read_checks.append({'role': role, 'equal': True})
        return response, contexts[-1], probe

    def stable_realtime(self, value):
        # Exclude only evaluation metadata, preserving own observation clocks,
        # leases, identity, prices, sources, statuses and permission results.
        result = deepcopy(self.a._v991_semantic_validator_payload(value))
        for name in ('picks', 'items'):
            for item in result.get(name) or []:
                if isinstance(item.get('odds_freshness'), dict):
                    item['odds_freshness'].pop('age_seconds', None)
        return result

    def stable_odds(self, value):
        result = deepcopy(value)
        for item in result.get('items') or []:
            if isinstance(item.get('freshness'), dict):
                item['freshness'].pop('age_seconds', None)
        return result

    def test_01_warm_page_one_projection_and_legacy_output_equivalence(self):
        self.page()
        _, data, probe = self.page()
        calls = self.r.totals(probe)
        self.assertEqual(calls['_v991_realtime_projection'], 1)
        self.assertEqual(calls['_build_public_home_sports_summary'], 0)
        self.assertEqual(calls['_v991_prepare_summary_operation'], 1)
        self.assertEqual(calls['build_sports_metrics_contract'], 6)
        with self.r.context('/picks'), self.r.observed_calls('independent_public_wrappers') as control:
            summary = self.a.get_public_home_sports_summary()
            expected_picks = self.a.get_realtime_safe_picks_context(summary)
            expected_odds = self.a.get_realtime_safe_odds_context(summary)
            # The actual render applies presentation overlays (for example,
            # highlight availability). Give both paths that same real stage.
            reference_data = deepcopy(data)
            reference_data.update(v934_realtime=expected_picks, v934_odds=expected_odds)
            with self.captured() as rendered:
                self.a.render_template('picks.html', data=reference_data)
            expected_picks = rendered[-1]['v934_realtime']
            expected_odds = rendered[-1]['v934_odds']
        self.assertEqual(self.r.totals(control)['_v991_realtime_projection'], 2)
        self.assertEqual(self.stable_realtime(data['v934_realtime']), self.stable_realtime(expected_picks))
        self.assertEqual(self.stable_odds(data['v934_odds']), self.stable_odds(expected_odds))
        self.r.picks_projection_details.append({'case': 'warm_page', 'projections': 1,
            'independent_wrapper_projections': 2, 'metrics_builds': 6,
            'base_rebuilds': 0, 'output_equivalent': True})

    def test_02_contexts_share_no_mutable_containers_or_freshness(self):
        _, data, _ = self.page()
        realtime, odds = data['v934_realtime'], data['v934_odds']
        self.assertTrue(realtime['picks'])
        self.assertTrue(odds['items'])
        self.assertFalse(mutable_ids(realtime) & mutable_ids(odds))
        original_realtime = deepcopy(realtime)
        original_odds = deepcopy(odds)
        odds['items'][0]['freshness']['status'] = 'QA_MUTATION_ODDS'
        odds['items'][0]['odds'] = -1
        self.assertEqual(realtime, original_realtime)
        realtime['picks'][0]['odds_freshness']['status'] = 'QA_MUTATION_PICK'
        self.assertEqual(odds['items'][0]['freshness']['status'], 'QA_MUTATION_ODDS')
        _, again, probe = self.page()
        self.assertEqual(self.r.totals(probe)['_v991_realtime_projection'], 1)
        self.assertEqual(self.stable_odds(again['v934_odds']), self.stable_odds(original_odds))
        self.assertFalse(mutable_ids(again['v934_odds']) & mutable_ids(odds))
        self.assertFalse(mutable_ids(again['v934_odds']) & mutable_ids(realtime))

    def test_03_real_sql_update_and_cache_invalidation_refresh_both_contexts(self):
        _, before, _ = self.page()
        pick_id = 'prepare-pick-0'
        def quote(data):
            return next(item for item in data['v934_odds']['items'] if item['pick_id'] == pick_id)
        self.assertEqual(quote(before)['odds'], 1.83)
        observed = datetime.now(ZoneInfo('Europe/Madrid')).isoformat()
        with closing(sqlite3.connect(self.r.db)) as conn, conn:
            conn.execute('UPDATE picks SET odds=?,updated_at=?,raw_json=? WHERE id=?',
                (3.25, observed, json.dumps({'odds_updated_at': observed, 'synthetic_fixture': True}), pick_id))
        self.r.business_before = self.r.table_hashes()  # Deliberate fixture write precedes subsequent read checks.
        _, still_cached, _ = self.page()
        self.assertEqual(quote(still_cached)['odds'], 1.83)
        self.r.invalidate()
        _, after, probe = self.page()
        self.assertEqual(self.r.totals(probe)['_build_public_home_sports_summary'], 1)
        self.assertEqual(self.r.totals(probe)['_v991_realtime_projection'], 1)
        self.assertEqual(quote(after)['odds'], 3.25)
        self.assertEqual(quote(after)['recorded_at'], observed)
        projected = next(item for item in after['v934_realtime']['picks'] if item['id'] == pick_id)
        self.assertEqual(projected['odds'], 3.25)
        self.assertEqual(projected['odds_recorded_at'], observed)
        self.assertEqual(quote(before)['odds'], 1.83)
        self.assertFalse(mutable_ids(before['v934_odds']) & mutable_ids(after['v934_odds']))
        self.r.picks_projection_details.append({'case': 'real_invalidation',
            'before': 1.83, 'after': 3.25, 'own_clock_preserved': True})

    def test_04_warm_requests_keep_real_users_and_outputs_isolated(self):
        expected = {'admin': ['prepare-pick-0', 'prepare-pick-1'], 'anonymous': [],
            'pro': ['prepare-pick-0'], 'elite': ['prepare-pick-0', 'prepare-pick-1'], 'free': []}
        previous_odds = []
        for role, visible in expected.items():
            with self.subTest(role=role):
                response, data, probe = self.page(role)
                self.assertEqual(self.r.totals(probe)['_v991_realtime_projection'], 1)
                self.assertEqual(sorted(row['id'] for row in data['picks']), visible)
                self.assertEqual(sorted(row['id'] for row in data['v925_picks']['picks']), visible)
                html = response.get_data(as_text=True)
                for hidden in set(expected['admin']) - set(visible):
                    self.assertNotIn(hidden, html)
                for prior in previous_odds:
                    self.assertFalse(mutable_ids(prior) & mutable_ids(data['v934_odds']))
                previous_odds.append(data['v934_odds'])
        self.r.picks_projection_details.append({'case': 'real_roles', 'visible_picks': expected,
            'cross_request_odds_aliases': 0})

    def test_05_identity_guard_and_own_live_clock_remain_authoritative(self):
        self.r.seed(live=True)
        with self.r.context('/picks'):
            summary = self.a.get_public_home_sports_summary()
            operation = self.a._v991_operation_for(summary)
            row = next(item for item in summary['all_valid_matches']
                if item['source'] == 'api_football_live' and item.get('competition_key') == 'laliga')
            self.assertEqual(operation.snapshot.context_for(row).state, 'RESOLVED')
            row['home_canonical_team_id'] = 'qa-post-prepare-changed-identity'
            with self.r.observed_calls('changed_identity_is_not_reprepared') as probe:
                realtime = self.a.get_realtime_safe_picks_context(summary)
                odds = self.a._v934_odds_context_from_snapshot(realtime)
            self.assertEqual(operation.snapshot.context_for(row).state, 'UNKNOWN_IDENTITY_CHANGED')
            self.assertIs(self.a._v991_operation_for(summary), operation)
            self.assertEqual(self.r.totals(probe)['_v991_prepare_summary_operation'], 0)
            self.assertEqual(self.r.totals(probe)['_v991_realtime_projection'], 1)
            self.assertEqual(operation.snapshot.select_rows(summary['all_valid_matches']).count, 3)
            self.assertEqual(realtime['fixture_metrics']['coverage']['reference_state'], 'PARTIAL_UNKNOWN')
            self.assertEqual(realtime['fixture_metrics']['counts']['matches'], 3)
            own = next(item for item in realtime['matches'] if item['id'] == row['id'])
            self.assertEqual(own['realtime_state']['provider_observed_at'], row['last_synced_at'])
            self.assertTrue(own['realtime_state']['live_valid_until_madrid'])
            self.assertFalse(mutable_ids(realtime) & mutable_ids(odds))
        stale = (self.r.now - timedelta(hours=2)).isoformat()
        with closing(sqlite3.connect(self.r.db)) as conn, conn:
            conn.execute('UPDATE matches SET updated_at=?,last_synced_at=?', (stale, stale))
        self.r.business_before = self.r.table_hashes()
        self.r.invalidate()
        _, data, _ = self.page()
        self.assertEqual(data['v934_realtime']['live'], [])
        self.assertEqual(data['v934_realtime']['counts']['live'], 0)
        self.r.picks_projection_details.append({'case': 'identity_and_clock',
            'changed_state': 'UNKNOWN_IDENTITY_CHANGED', 'stale_live_count': 0})


def run_picks_projection_contracts(runtime):
    PicksProjectionContracts.runtime = runtime
    runtime.picks_projection_details = []
    extra = ('_v991_realtime_projection', 'get_realtime_safe_picks_context',
        'get_realtime_safe_odds_context', '_v934_odds_context_from_snapshot')
    bindings = {name: getattr(runtime.app, name) for name in extra}
    old_codes = dict(runtime.codes)
    runtime.codes.update({value.__code__: name for name, value in bindings.items()})
    starts = len(runtime.requests), len(runtime.observations), len(runtime.business_checks)
    text = io.StringIO()
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(PicksProjectionContracts)
        result = unittest.TextTestRunner(stream=text, verbosity=2).run(suite)
    finally:
        runtime.codes.clear(); runtime.codes.update(old_codes)
    unchanged = all(getattr(runtime.app, name) is value for name, value in bindings.items())
    (runtime.out/'picks-unittest-output.txt').write_text(text.getvalue(), encoding='utf-8')
    xml = ET.Element('testsuite', name='V1001 picks actual App projection', tests=str(result.testsRun),
        failures=str(len(result.failures)), errors=str(len(result.errors)))
    for test, trace in result.failures + result.errors:
        ET.SubElement(ET.SubElement(xml, 'testcase', name=test.id()), 'failure').text = trace
    ET.ElementTree(xml).write(runtime.out/'picks-junit.xml', encoding='utf-8', xml_declaration=True)
    return {'unittest_run': result.testsRun, 'failures': [{'test': t.id(), 'trace': s} for t, s in result.failures],
        'errors': [{'test': t.id(), 'trace': s} for t, s in result.errors],
        'requests': runtime.requests[starts[0]:], 'observational_calls': runtime.observations[starts[1]:],
        'business_SQL_checks': runtime.business_checks[starts[2]:], 'details': runtime.picks_projection_details,
        'product_bindings_unchanged': unchanged, 'success': result.wasSuccessful() and unchanged}
