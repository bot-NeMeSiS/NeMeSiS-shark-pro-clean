"""Persistent stdlib cases for the real App, invoked only by the owned fresh worker.

Importing this file does not import App or install any parent-process hook. Tests
observe real code objects; no getter/finalizer/normalizer/C3 binding is replaced.
"""
from collections import Counter
from contextlib import closing, contextmanager
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import threading
import unittest
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class Runtime:
    def __init__(self, app, repo, database, out, references):
        self.app, self.repo, self.db, self.out, self.references = app, repo, database, out, references
        assert Path(app.__file__).resolve() == repo / 'app.py'
        assert Path(app.DB_PATH).resolve() == database and database.is_relative_to(out)
        from engines.v934_realtime_sports_engine import invalidate_realtime_cache
        self.invalidate = invalidate_realtime_cache
        self.fixture = json.loads((Path(__file__).parent / 'v991_fixture_identity.json').read_bytes())['input']
        self.now = datetime.now(ZoneInfo('Europe/Madrid'))
        self.observed = self.now - timedelta(seconds=30)
        self.requests, self.observations, self.business_checks = [], [], []
        self.codes = {getattr(app, name).__code__: name for name in (
            'get_public_home_sports_summary', '_v991_finish_summary', '_v991_prepare_summary_operation',
            '_build_public_home_sports_summary', 'build_sports_home_sections',
            'build_sports_metrics_contract', 'get_v934_realtime_context')}
        self.clients = {}
        from flask import session
        with closing(sqlite3.connect(database)) as conn, conn:
            for reference in self.fixture['catalogue']:
                conn.execute('DELETE FROM competitions WHERE key=?', (reference['key'],))
                self.insert(conn, 'competitions', reference)
            for role, tier in (('free', 'FREE'), ('pro', 'PRO'), ('elite', 'ELITE'), ('admin', 'ELITE')):
                self.insert(conn, 'users', {'id':'prepare-only-'+role, 'username':'prepare-'+role,
                    'email':'prepare-'+role+'@example.invalid', 'name':'Synthetic '+role,
                    'password_hash':app.generate_password_hash('synthetic-prepare-only'), 'auth_version':0,
                    'role':role.upper(), 'membership':tier,
                    'membership_expires_at':(self.now+timedelta(days=2)).isoformat(), 'created_at':self.now.isoformat()})
        for role in ('anonymous', 'free', 'pro', 'elite', 'admin'):
            client = app.app.test_client()
            if role != 'anonymous':
                with app.app.test_request_context('/'):
                    app.set_login_session(app.get_user_by_id('prepare-only-'+role)); state = dict(session)
                with client.session_transaction() as target:
                    target.update(state)
            self.clients[role] = client

    def insert(self, conn, table, row):
        columns = {r[1] for r in conn.execute('PRAGMA table_info("'+table+'")')}
        values = {key:value for key,value in row.items() if key in columns}
        conn.execute('INSERT INTO "'+table+'" ('+','.join('"'+key+'"' for key in values)+') VALUES ('+
                     ','.join('?' for _ in values)+')', tuple(values.values()))

    def table_hashes(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.row_factory = sqlite3.Row
            return {table:digest([dict(row) for row in conn.execute('SELECT * FROM '+table+' ORDER BY id')])
                    for table in ('matches', 'picks')}

    def seed(self, *, live=False, empty=False):
        rows = [] if empty else deepcopy(self.fixture['rows'])
        kickoff = (self.now-timedelta(minutes=20)).replace(second=0, microsecond=0) if live else (
            self.now+timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)
        for row in rows:
            row.update(match_date=kickoff.date().isoformat(), kickoff_iso=kickoff.isoformat(),
                kickoff_time=kickoff.strftime('%H:%M'), match_time=kickoff.strftime('%H:%M'),
                status='LIVE' if live else 'NS', minute=20 if live else None,
                home_score=1 if live else None, away_score=0 if live else None,
                updated_at=self.observed.isoformat(), last_synced_at=self.observed.isoformat())
            raw = json.loads(row['raw_json'])
            if row['source'] == 'api_football_live':
                raw['fixture'].update(date=kickoff.isoformat(), status={'short':'1H' if live else 'NS','elapsed':20 if live else None})
                raw['goals'] = {'home':1 if live else None, 'away':0 if live else None}
            else:
                raw.update(strTimestamp=kickoff.isoformat(), strStatus='1H' if live else 'NS',
                    intMinute='20' if live else None, intHomeScore='1' if live else None, intAwayScore='0' if live else None)
            row['raw_json'] = json.dumps(raw)
        self.rows = rows
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute('DELETE FROM matches'); conn.execute('DELETE FROM picks')
            for row in rows:
                self.insert(conn, 'matches', row)
            for index, odds in enumerate((1.83, 2.14)) if rows else ():
                row = rows[index]
                self.insert(conn, 'picks', {'id':'prepare-pick-'+str(index), 'match_id':row['id'],
                    'home_team':row['home_team'], 'away_team':row['away_team'], 'competition_name':row['competition_name'],
                    'match_date':row['match_date'], 'kickoff_iso':row['kickoff_iso'], 'match_time':row['match_time'],
                    'market':'1x2','pick_type':'1x2','selection':'1','odds':odds,'bookmaker':'Synthetic own bookmaker',
                    'status':'published','membership_required':'PRO' if index == 0 else 'ELITE',
                    'match_status':'LIVE' if live else 'NS','source':'The Odds API',
                    'created_at':self.observed.isoformat(),'updated_at':self.observed.isoformat(),
                    'raw_json':json.dumps({'odds_updated_at':self.observed.isoformat(),'synthetic_fixture':True})})
        self.invalidate()
        self.business_before = self.table_hashes()

    @contextmanager
    def observed_calls(self, label):
        old, rows, start = sys.getprofile(), [], len(self.references)
        def profile(frame, event, arg):
            if event == 'call' and frame.f_code in self.codes:
                name = self.codes[frame.f_code]
                rows.append({'function':name, 'caller':frame.f_back.f_code.co_name if frame.f_back else None,
                    'prepare_only':frame.f_locals.get('_prepare_only', False),
                    'cache_acceptance':bool(self.app._v991_cache_acceptance.get())})
        sys.setprofile(profile)
        record = {'label':label,'calls':rows}
        try:
            yield record
        finally:
            sys.setprofile(old)
            record['reference_PK_batches'] = len(self.references)-start
            self.observations.append(record)

    @contextmanager
    def bounded(self, label):
        def stop():
            import os
            (self.out/'REQUEST_TIMEOUT.json').write_text(json.dumps({'label':label,'cap_seconds':20}))
            os._exit(124)
        timer = threading.Timer(20, stop); timer.daemon = True; timer.start()
        try:
            yield
        finally:
            timer.cancel()

    @contextmanager
    def context(self, path='/api/realtime/sports?scope=matches&consumer=directo-v2'):
        with self.bounded('request_context:'+path), self.app.app.test_request_context(path):
            yield

    def request(self, query, *, method='GET', role='anonymous', headers=None, path='/api/realtime/sports'):
        with self.bounded(method+path), self.observed_calls(method+path+str(query)) as probe:
            response = self.clients[role].open(path, method=method, query_string=query, headers=headers or {})
            raw = response.get_data()
        body = response.get_json(silent=True)
        index = len(self.requests)+1
        self.requests.append({'index':index,'path':path,'query':query,'method':method,'role':role,
            'http':response.status_code,'bytes':len(raw),'ETag':response.headers.get('ETag'),
            'Vary':response.headers.get('Vary'),'getter_modes':[r['prepare_only'] for r in probe['calls']
                if r['function']=='get_public_home_sports_summary'],'reference_PK_batches':probe['reference_PK_batches']})
        if body is not None:
            (self.out/('response-%03d.json'%index)).write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return response, body, probe

    def totals(self, probe):
        return Counter(row['function'] for row in probe['calls'])

    def post_finish(self, probe, name):
        return sum(row['function'] == name and row['caller'] == '_v991_finish_summary' for row in probe['calls'])


class ApiPrepareOnlyContracts(unittest.TestCase):
    runtime = None

    def setUp(self):
        self.r = self.runtime
        self.a = self.r.app
        self.r.seed()

    def tearDown(self):
        after = self.r.table_hashes()
        self.assertEqual(self.r.business_before, after)
        self.r.business_checks.append({'test':self.id(),'before':self.r.business_before,'after':after,'equal':True})

    def anchor(self, summary):
        operation = self.a._v991_operation_for(summary)
        self.assertIsNotNone(operation)
        return operation, operation.snapshot, tuple(map(id,summary['all_valid_matches']))

    def assert_full(self, summary):
        self.assertIn('sports_home',summary);self.assertIn('sports_metrics',summary)
        self.assertEqual(summary['raw_matches_count'],3)
        self.assertEqual(summary['sports_metrics']['matches_available'],2)

    def assert_source(self, summary):
        self.assertNotIn('sports_home',summary);self.assertNotIn('sports_metrics',summary)

    def test_default_FULL_preserves_real_acceptance_and_preparation(self):
        with self.r.context(), self.r.observed_calls('default_FULL') as probe:
            summary = self.a.get_public_home_sports_summary()
            self.assert_full(summary);self.anchor(summary)
        counts = self.r.totals(probe)
        self.assertEqual(counts['_v991_finish_summary'],1)
        self.assertEqual(counts['_v991_prepare_summary_operation'],1)
        self.assertEqual(self.r.post_finish(probe,'build_sports_home_sections'),1)
        self.assertEqual(self.r.post_finish(probe,'build_sports_metrics_contract'),1)
        self.assertEqual(probe['reference_PK_batches'],1)
        self.assertTrue(any(row['cache_acceptance'] and row['function']=='build_sports_home_sections' for row in probe['calls']))
        self.assertTrue(any(row['cache_acceptance'] and row['function']=='build_sports_metrics_contract' for row in probe['calls']))

    def transitions(self, initial):
        with self.r.context():
            summary = self.a.get_public_home_sports_summary(_prepare_only=initial)
            operation, snapshot, objects = self.anchor(summary)
            original_rows = digest(summary['all_valid_matches'])
            with self.r.observed_calls('mode_transitions:'+str(initial)) as probe:
                for mode in (not initial, initial):
                    again = self.a.get_public_home_sports_summary(_prepare_only=mode)
                    self.assertIs(again,summary);self.assertIs(self.a._v991_operation_for(again),operation)
                    self.assertIs(operation.snapshot,snapshot)
                    self.assertEqual(tuple(map(id,again['all_valid_matches'])),objects)
                    self.assertEqual(digest(again['all_valid_matches']),original_rows)
                    (self.assert_source if mode else self.assert_full)(again)
            self.assertEqual(self.r.totals(probe)['_v991_finish_summary'],0)
            self.assertEqual(self.r.totals(probe)['_v991_prepare_summary_operation'],0)
            self.assertEqual(probe['reference_PK_batches'],0)

    def test_FULL_prepare_FULL_same_owner_operation_snapshot(self):self.transitions(False)
    def test_prepare_FULL_prepare_same_owner_operation_snapshot(self):self.transitions(True)

    def test_identity_mutation_is_UNKNOWN_and_not_refinalized_during_switch(self):
        for initial in (False,True):
            self.r.invalidate()
            with self.subTest(initial=initial), self.r.context():
                summary = self.a.get_public_home_sports_summary(_prepare_only=initial)
                operation, snapshot, _ = self.anchor(summary)
                row = next(row for row in summary['all_valid_matches'] if row['source']=='api_football_live'
                           and row.get('competition_key')=='laliga')
                self.assertEqual(snapshot.context_for(row).state,'RESOLVED')
                row['home_canonical_team_id'] = 'synthetic-post-prepare-identity-mutation'
                with self.r.observed_calls('identity_mutation_switch') as probe:
                    again = self.a.get_public_home_sports_summary(_prepare_only=not initial)
                    self.assertIs(again,summary);self.assertIs(self.a._v991_operation_for(again),operation)
                    self.assertEqual(snapshot.context_for(row).state,'UNKNOWN_IDENTITY_CHANGED')
                    selection = snapshot.select_rows(summary['all_valid_matches'])
                    self.assertEqual(selection.count,3);self.assertEqual(len(selection.raw_rows),3)
                    self.assertEqual({r['id'] for r in selection.raw_rows},{r['id'] for r in self.r.rows})
                self.assertEqual(self.r.totals(probe)['_v991_finish_summary'],0)
                self.assertEqual(self.r.totals(probe)['_v991_prepare_summary_operation'],0)
                self.assertEqual(probe['reference_PK_batches'],0)

    def test_presentation_only_mutation_keeps_prepared_identity(self):
        with self.r.context():
            summary = self.a.get_public_home_sports_summary(_prepare_only=True)
            operation,snapshot,_ = self.anchor(summary)
            row = next(r for r in summary['all_valid_matches'] if r.get('competition_key')=='laliga')
            row['is_favorite'] = True
            again = self.a.get_public_home_sports_summary()
            self.assertIs(again,summary);self.assertIs(self.a._v991_operation_for(again),operation)
            self.assertEqual(snapshot.context_for(row).state,'RESOLVED');self.assert_full(again)

    def test_real_cache_clone_complete_and_isolated_after_prepare_only(self):
        from engines import v934_realtime_sports_engine as engine
        with self.r.context():
            first = self.a.get_public_home_sports_summary(_prepare_only=True)
            stored = engine._CACHE[self.a._public_sports_cache_key()]['payload']
            before = digest(stored)
            self.assertIsNot(first,stored);self.assertIn('sports_home',stored);self.assertIn('sports_metrics',stored)
            first['all_valid_matches'][0]['source'] = 'synthetic-mutated-request-only'
            self.assertEqual(digest(stored),before)
        with self.r.context():
            second = self.a.get_public_home_sports_summary()
            self.assertIsNot(second,first);self.assertEqual(second['summary_cache_status'],'hit')
            self.assert_full(second);self.assertEqual(digest(stored),before)
            self.assertFalse(any(r['source']=='synthetic-mutated-request-only' for r in second['all_valid_matches']))

    def test_actual_HTTP_activation_closed_and_other_consumers_remain_FULL(self):
        matrix = [(consumer,'matches','GET',True) for consumer in ('directo-v2','fixture-metrics-v1')]
        matrix += [(consumer,scope,'GET',False) for consumer in ('directo-v2','fixture-metrics-v1')
                   for scope in ('all','live','picks','odds','combis')]
        matrix += [(c,'matches','GET',False) for c in ('unknown-consumer','directo-v2-alt','Directo-v2',' directo-v2')]
        matrix += [(consumer,'matches','HEAD',False) for consumer in ('directo-v2','fixture-metrics-v1')]
        matrix += [('fixture-metrics-v1',' MATCHES ','GET',True),('directo-v2',' MATCHES ','GET',False)]
        for consumer,scope,method,expected in matrix:
            with self.subTest(consumer=consumer,scope=scope,method=method):
                self.r.invalidate()
                response,body,probe = self.r.request({'consumer':consumer,'scope':scope},method=method)
                self.assertEqual(response.status_code,200)
                modes = [r['prepare_only'] for r in probe['calls'] if r['function']=='get_public_home_sports_summary']
                self.assertTrue(modes);self.assertEqual(set(modes),{expected})
                self.assertEqual(self.r.post_finish(probe,'build_sports_home_sections'),0 if expected else 1)
                self.assertEqual(self.r.post_finish(probe,'build_sports_metrics_contract'),0 if expected else 1)
                self.assertEqual(probe['reference_PK_batches'],1)
        self.r.invalidate()
        response,_,probe = self.r.request({'scope':'matches','_prepare_only':'true'})
        self.assertEqual(response.status_code,200)
        self.assertTrue(all(not r['prepare_only'] for r in probe['calls'] if r['function']=='get_public_home_sports_summary'))
        self.r.invalidate()
        response,_,probe = self.r.request({'consumer':'directo-v2','scope':'matches'},path='/live')
        self.assertEqual(response.status_code,200)
        self.assertTrue(all(not r['prepare_only'] for r in probe['calls'] if r['function']=='get_public_home_sports_summary'))

    def test_explicit_prepared_summary_does_not_select_getter_mode(self):
        for consumer in ('directo-v2','fixture-metrics-v1'):
            with self.subTest(consumer=consumer), self.r.context('/api/realtime/sports?scope=matches&consumer='+consumer):
                summary = self.a.get_public_home_sports_summary()
                before = digest(summary);operation,_,_ = self.anchor(summary)
                with self.r.observed_calls('explicit_summary') as probe:
                    snapshot = self.a.get_v934_realtime_context(summary)
                self.assertEqual(digest(summary),before);self.assertIs(self.a._v991_operation_for(summary),operation)
                self.assertEqual(self.r.totals(probe)['get_public_home_sports_summary'],0)
                self.assertEqual(self.r.totals(probe)['_v991_finish_summary'],0)
                self.assertEqual(snapshot['counts']['matches'],2);self.assert_full(summary)

    def test_REAL_LIVE_admission_and_own_stale_evidence_in_both_modes(self):
        self.r.seed(live=True)
        with self.r.context():
            base = self.a._v991_validated_base_summary()
            positive = next(r for r in base['all_valid_matches'] if r['source']=='api_football_live' and r.get('competition_key')=='laliga')
            self.assertTrue(self.a._v991_normalize_frame(positive,self.r.now)['is_live'])
            base['valid_live_events'] = [positive]
            for mode in (False,True):
                source = deepcopy(base)
                prepared,op = self.a._v991_finish_summary(source,_prepare_only=mode)
                self.assertIs(prepared,source);self.assertEqual(len(prepared['all_valid_matches']),1)
                own = prepared['all_valid_matches'][0]
                self.assertIs(own,prepared['valid_live_events'][0]);self.assertIs(own,op.snapshot.cohorts['current'][0])
                self.assertEqual(own['raw_json'],positive['raw_json']);self.assertEqual(own['last_synced_at'],positive['last_synced_at'])
                projection = self.a._v991_realtime_projection(prepared)
                self.assertEqual(projection['counts']['live'],1)
                stale = deepcopy(base)
                for row in stale['all_valid_matches']:
                    row['updated_at'] = row['last_synced_at'] = (self.r.now-timedelta(hours=2)).isoformat()
                stale,_ = self.a._v991_finish_summary(stale,_prepare_only=mode)
                self.assertEqual(stale['valid_live_events'],[])
                self.assertEqual(self.a._v991_realtime_projection(stale)['counts']['live'],0)

    def test_real_missing_source_is_NULL_but_verified_empty_is_zero(self):
        self.r.seed(empty=True)
        with closing(sqlite3.connect(self.r.db)) as conn:
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        original = hashlib.sha256(self.r.db.read_bytes()).hexdigest()
        files = [self.r.db]+[Path(str(self.r.db)+suffix) for suffix in ('-wal','-shm','-journal')]
        moves = [(p,self.r.out/('missing-preserved-'+p.name)) for p in files if p.exists()]
        self.assertTrue(all(p.resolve().is_relative_to(self.r.out) and q.resolve().is_relative_to(self.r.out) and not q.exists() for p,q in moves))
        missing = {}
        try:
            for path,backup in moves:path.rename(backup)
            for index,consumer in enumerate(('directo-v2','fixture-metrics-v1')):
                self.r.invalidate()
                response,body,_ = self.r.request({'scope':'matches','consumer':consumer})
                self.assertEqual(response.status_code,200);self.assertEqual(body['source_snapshot_state'],'READ_UNAVAILABLE')
                self.assertIsNone(body['counts']['matches']);self.assertIsNone(body['counts']['live'])
                metadata = body['fixture_identity' if consumer=='directo-v2' else 'fixture_metrics']
                self.assertEqual(metadata['state'],'NOT_ESTABLISHED')
                missing[consumer] = response.headers['ETag']
                for path in files:
                    if path.exists():path.rename(self.r.out/('missing-auto-created-'+str(index)+'-'+path.name))
        finally:
            for path,backup in reversed(moves):
                if path.exists():path.rename(self.r.out/('missing-final-auto-created-'+path.name))
                backup.rename(path)
        self.assertEqual(hashlib.sha256(self.r.db.read_bytes()).hexdigest(),original)
        for consumer in ('directo-v2','fixture-metrics-v1'):
            self.r.invalidate()
            response,body,_ = self.r.request({'scope':'matches','consumer':consumer},headers={'If-None-Match':missing[consumer]})
            self.assertEqual(response.status_code,200);self.assertEqual(body['source_snapshot_state'],'LOCAL_SNAPSHOT')
            self.assertEqual(body['source_read_state'],'ok');self.assertEqual(body['counts']['matches'],0)
            self.assertEqual(body['counts']['live'],0);self.assertNotEqual(response.headers['ETag'],missing[consumer])

    def test_five_roles_weak_ETag_304_and_own_clocks_are_not_renewed(self):
        self.r.seed(live=True)
        original = {str(row['id']):row for row in self.r.rows}
        for role in self.r.clients:
            for consumer in ('directo-v2','fixture-metrics-v1'):
                with self.subTest(role=role,consumer=consumer):
                    response,body,probe = self.r.request({'scope':'matches','consumer':consumer},role=role)
                    self.assertEqual(response.status_code,200);self.assertEqual(body['counts']['matches'],2)
                    self.assertEqual({str(r['id']) for r in body['matches']},set(original))
                    self.assertTrue(response.headers['ETag'].startswith('W/'))
                    self.assertIn('Cookie',response.headers.get('Vary',''))
                    clocks = {r['id']:{key:r['realtime_state'].get(key) for key in
                        ('provider_observed_at','live_valid_until_madrid','score_home','score_away','minute')} for r in body['matches']}
                    for row in body['matches']:
                        self.assertEqual(row['realtime_state']['provider_observed_at'],original[row['id']]['last_synced_at'])
                        self.assertEqual(row['realtime_state']['score_home'],1);self.assertEqual(row['realtime_state']['score_away'],0)
                    conditional,_,_ = self.r.request({'scope':'matches','consumer':consumer},role=role,
                        headers={'If-None-Match':response.headers['ETag']})
                    self.assertEqual(conditional.status_code,304);self.assertEqual(conditional.get_data(),b'')
                    again,newer,_ = self.r.request({'scope':'matches','consumer':consumer},role=role)
                    newer_clocks = {r['id']:{key:r['realtime_state'].get(key) for key in
                        ('provider_observed_at','live_valid_until_madrid','score_home','score_away','minute')} for r in newer['matches']}
                    self.assertEqual(clocks,newer_clocks)
                    self.assertEqual(response.headers['ETag'],again.headers['ETag'])
                    self.assertEqual(self.a._v991_semantic_validator_payload(body),self.a._v991_semantic_validator_payload(newer))


def run_contracts(app, repo, database, out, references):
    runtime = Runtime(app, repo, database, out, references)
    ApiPrepareOnlyContracts.runtime = runtime
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ApiPrepareOnlyContracts)
    text = io.StringIO();result = unittest.TextTestRunner(stream=text,verbosity=2).run(suite)
    (out/'unittest-output.txt').write_text(text.getvalue(),encoding='utf-8')
    xml = ET.Element('testsuite',name='V991 API prepare-only actual App',tests=str(result.testsRun),
                     failures=str(len(result.failures)),errors=str(len(result.errors)))
    for test,trace in result.failures+result.errors:
        case = ET.SubElement(xml,'testcase',name=test.id())
        ET.SubElement(case,'failure').text=trace
    ET.ElementTree(xml).write(out/'junit.xml',encoding='utf-8',xml_declaration=True)
    return {'unittest_run':result.testsRun,'failures':[{'test':t.id(),'trace':s} for t,s in result.failures],
        'errors':[{'test':t.id(),'trace':s} for t,s in result.errors], 'requests':runtime.requests,
        'observational_calls':runtime.observations,'business_SQL_checks':runtime.business_checks,
        'shared_fixture_observed_at':runtime.observed.isoformat(),'App_getter_normalizer_C3_rebindings':0,
        'entitlement_certification':False,'success':result.wasSuccessful()}
