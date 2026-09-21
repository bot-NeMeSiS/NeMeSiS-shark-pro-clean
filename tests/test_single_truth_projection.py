"""Read-only performance contracts: cache text, never time-dependent decisions."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta
import json
import re
import unicodedata
from zoneinfo import ZoneInfo

import pytest
from engines import realtime_state_engine as state_engine
from engines import v934_realtime_sports_engine as snapshot
from engines import v935_launch_trust_engine as truth_engine

NOW = datetime(2026, 9, 21, 20, 0, tzinfo=ZoneInfo('Europe/Madrid'))


def record(**changes):
    value = dict(id='synthetic-1', home_team='Local QA', away_team='Visitante QA',
        competition_name='Liga QA', match_date='2026-09-21', kickoff_time='19:00',
        kickoff_iso='2026-09-21T19:00:00+02:00', source='TheSportsDB API', status='LIVE',
        minute=0, home_score=0, away_score=1, last_synced_at=NOW.isoformat())
    value.update(changes)
    return value


@pytest.mark.parametrize('token', [None, '', False, 0, 1, [], {}, {'key':'LIVE'},
    'LIVE', 'live', 'En directo', '  PRÓXIMO  ', 'FINALIZADO', 'Después-de_prórroga',
    '\n2H\r', 'e\u0301', 'İ', 'ß', 'FT\tFT', 'x'*400])
def test_text_normalization_preserves_original_semantics(token):
    expected = truth_engine._text(token, 180).casefold().replace('_',' ').replace('-',' ')
    expected = ''.join(c for c in unicodedata.normalize('NFD', expected) if unicodedata.category(c)!='Mn')
    expected = re.sub(r'\s+', ' ', expected).strip()
    assert truth_engine._status_key(token) == expected
    assert truth_engine._status_key(token) == expected


def test_token_cache_is_bounded_and_only_keeps_bounded_strings():
    normalize = truth_engine._normalized_status_text
    normalize.cache_clear()
    for i in range(700):
        truth_engine._status_key(str(i) + '-' + 'x'*400)
    assert normalize.cache_info().currsize <= 256
    # The input is trimmed BEFORE admission. Distinct truncated suffixes share one key.
    normalize.cache_clear()
    truth_engine._status_key('x'*180+'A')
    truth_engine._status_key('x'*180+'B')
    assert normalize.cache_info().misses == 1
    assert normalize.cache_info().hits == 1


def test_status_objects_are_converted_each_time_not_stored_as_cache_keys():
    class Changing:
        calls = 0
        def __str__(self):
            self.calls += 1
            return 'LIVE' if self.calls == 1 else 'FT'
    value = Changing()
    assert truth_engine._status_key(value) == 'live'
    assert truth_engine._status_key(value) == 'ft'
    assert value.calls == 2


@pytest.mark.parametrize('changes', [ {}, {'status':'HT'}, {'status':'FT'},
    {'status':'FT','home_score':None}, {'status':'NS','kickoff_iso':'2026-09-21T22:00:00+02:00'},
    {'status':'PST'}, {'status':'SUSP'}, {'status':'CANC'}, {'status':'ABD'}, {'status':'ET'},
    {'status':'P'}, {'status':'PEN'}, {'status':'ARCHIVED'}, {'strProgress':'FT'},
    {'last_synced_at':''}, {'live_updated_at':'invalid'}, {'is_stale':True},
    {'last_synced_at':(NOW-timedelta(seconds=121)).isoformat()},
    {'last_synced_at':(NOW+timedelta(minutes=10)).isoformat()},
    {'raw_json':json.dumps({'status':'FT','coverage':{'lineups':{'available':False}}})}])
def test_shared_projection_equals_authoritative_truth_and_public_contract(changes):
    row = record(**changes); before = deepcopy(row)
    projected, truth = state_engine.build_realtime_match_evidence(row, now=NOW)
    normalized = snapshot.normalize_match(row, now=NOW)
    expected = truth_engine.match_status_truth(row, now=NOW)
    assert truth == expected
    assert normalized['status_truth'] == expected
    assert normalized['realtime_state'] == projected == state_engine.build_realtime_match_state(row, now=NOW)
    assert 'status_truth' not in projected
    assert normalized['is_live'] == expected['is_live'] == projected['is_live']
    assert normalized['is_finished'] == expected['is_finished'] == projected['is_finished']
    assert normalized['is_stale'] == expected['is_stale'] == projected['is_stale']
    assert row == before


def test_snapshot_uses_one_truth_call_per_accepted_match(monkeypatch):
    original = truth_engine.match_status_truth
    calls = []
    def observed(item, now=None):
        calls.append((item.get('id'), now))
        return original(item, now)
    monkeypatch.setattr(state_engine, 'match_status_truth', observed)
    monkeypatch.setattr(snapshot, 'match_status_truth', observed)
    rows = [record(id=f'qa-{i}') for i in range(12)]
    result = snapshot.build_realtime_snapshot({'all_valid_matches':rows, 'valid_matches_today':rows}, now=NOW)
    assert len(result['matches']) == 12
    assert len(calls) == 12
    assert {now for _, now in calls} == {NOW}


def test_text_cache_never_renews_a_live_deadline_or_freezes_score():
    row = record()
    early = snapshot.normalize_match(row, now=NOW)
    late = snapshot.normalize_match(row, now=NOW+timedelta(seconds=121))
    assert early['is_live'] is True
    assert late['is_live'] is False and late['is_stale'] is True
    assert early['realtime_state']['provider_observed_at'] == late['realtime_state']['provider_observed_at']
    final = snapshot.normalize_match(record(status='FT', home_score=0, away_score=0), now=NOW)
    assert final['is_live'] is False and final['is_finished'] is True
    assert final['home_score'] == final['away_score'] == 0


def test_outputs_do_not_share_mutable_truth_or_coverage():
    row = record(coverage={'lineups':{'available':False}})
    first = snapshot.normalize_match(row, now=NOW)
    first['status_truth']['signal_kinds'].append('FAKE')
    first['realtime_state']['coverage']['lineups']['state'] = 'FAKE'
    second = snapshot.normalize_match(row, now=NOW)
    assert 'FAKE' not in second['status_truth']['signal_kinds']
    assert second['realtime_state']['coverage']['lineups']['state'] != 'FAKE'
    assert row['coverage']['lineups'] == {'available':False}


def test_cached_labels_do_not_mix_concurrent_clocks():
    def project(i):
        return snapshot.normalize_match(record(id=str(i)), now=NOW+timedelta(seconds=i%2*121))
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(project, range(64)))
    assert all(item['is_live'] is (i%2==0) for i,item in enumerate(rows))
    rows[0]['status_truth']['signal_kinds'].clear()
    assert rows[2]['status_truth']['signal_kinds']


def test_original_standalone_status_adapter_remains_compatible():
    expected = truth_engine.match_status_truth(record(), now=NOW)
    assert snapshot._status_from_truth(record(), NOW)['truth'] == expected


def test_preclassified_payload_cannot_inject_verified_truth():
    row = record(last_synced_at='',status_truth={'is_live':True},realtime_state={'is_live':True})
    assert snapshot.normalize_match(row,now=NOW)['is_live'] is False
