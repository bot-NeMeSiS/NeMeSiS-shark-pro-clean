"""SIMULATED_QA: existing sports snapshot -> real Directo card template.

No Flask/session emulation here: route integration lives in the HTTP tests.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from html.parser import HTMLParser
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from jinja2 import Environment, FileSystemLoader

import engines.v934_realtime_sports_engine as snapshot_engine
from engines.realtime_state_engine import build_realtime_match_state
from engines.v935_launch_trust_engine import match_status_truth

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 15, 20, 0, tzinfo=ZoneInfo('Europe/Madrid'))


def record(**changes):
    row = dict(id='live-consumer-qa', match_id='live-consumer-qa',
        home_team='Local QA', away_team='Visitante QA', competition_name='Liga QA',
        source='persisted-provider-cache', match_date=NOW.date().isoformat(),
        kickoff_time='19:00', status='LIVE', minute=67, home_score=1, away_score=0,
        last_synced_at=(NOW-timedelta(seconds=30)).isoformat())
    row.update(changes)
    return row


def summary(rows):
    return dict(valid_matches_today=rows, valid_upcoming_matches=[], valid_active_picks=[])


class Cards(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.articles = []; self.links = []; self.text = []; self.wrappers = []
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'article' and 'data-v934-match-card' in a:
            self.articles.append(a)
        if tag == 'a':
            self.links.append(a.get('href'))
        if a.get('data-realtime-consumer'):
            self.wrappers.append(a)
    def handle_data(self, data):
        self.text.append(data)


def render_card(row):
    import app as module
    env = Environment(loader=FileSystemLoader(ROOT/'templates'), autoescape=True)
    env.globals.update(module.app.jinja_env.globals)
    # Only cosmetic collaborators; the production macro and data projection run.
    env.filters['sync_madrid_label'] = lambda s: s
    env.globals.update(current_user=None,
        nemesis_source_label=lambda s: s,
        nemesis_data_confidence=lambda *a: dict(level='UNKNOWN', label='Pendiente', score=0),
        nemesis_attention_priority=lambda *a: dict(level=1, label='Informativo', disclaimer='QA'))
    with module.app.test_request_context('/'):
        return env.get_template('components/realtime_live_card.html').module.live_card(row)


@pytest.mark.parametrize('status,age,expected', [
    ('LIVE', 30, 'LIVE'), ('HT', 30, 'HALFTIME'), ('ET', 30, 'LIVE'),
    ('P', 30, 'LIVE'), ('FT', 30, 'FINISHED'), ('NS', 30, 'RESULT_PENDING'),
    ('PST', 30, 'POSTPONED'), ('SUSP', 30, 'SUSPENDED'),
    ('LIVE', 121, 'STALE'), ('LIVE', -900, 'STALE'),
])
def test_existing_snapshot_exposes_the_same_state_as_sports_truth(status, age, expected):
    row = record(status=status, last_synced_at=(NOW-timedelta(seconds=age)).isoformat())
    before = deepcopy(row)
    actual = snapshot_engine.normalize_match(row, now=NOW)
    state = actual['realtime_state']
    truth = match_status_truth(row, now=NOW)
    assert state == build_realtime_match_state(row, now=NOW)
    assert state['status_canonical'] == expected == truth['lifecycle']
    assert actual['is_live'] is state['is_live'] is truth['is_live']
    assert actual['is_stale'] is state['is_stale'] is truth['is_stale']
    assert actual['age_seconds'] == state['freshness_seconds']
    assert row == before


@pytest.mark.parametrize('minute,extra,label', [(0, None, 'Min 0'), (67, None, 'Min 67'), ('90+4', None, 'Min 90+4'), (45, 2, 'Min 45+2')])
def test_observed_minutes_reach_the_actual_card(minute, extra, label):
    normalized = snapshot_engine.normalize_match(record(minute=minute, extra=extra), now=NOW)
    rendered = str(render_card(normalized))
    parsed = Cards(rendered)
    assert parsed.articles[0]['data-canonical-live'] == 'true'
    assert parsed.articles[0]['data-canonical-status'] == 'LIVE'
    assert label in ''.join(parsed.text)
    assert parsed.links.count('/match/live-consumer-qa') == 1
    assert len(parsed.wrappers) == 1
    assert parsed.wrappers[0]['data-realtime-observed-at'] == record()['last_synced_at']


def test_stale_aliases_cannot_override_the_snapshot_in_directo():
    normalized = snapshot_engine.normalize_match(record(), now=NOW)
    normalized.update(client_status_label='Datos retrasados', client_live_minute=99,
        status_info={'key':'FT', 'is_live':False})
    html = str(render_card(normalized)); parsed = Cards(html)
    assert parsed.articles[0]['data-canonical-status'] == 'LIVE'
    assert parsed.articles[0]['data-canonical-live'] == 'true'
    assert 'Min 67' in html and 'Min 99' not in html
    assert 'Datos retrasados' not in html


@pytest.mark.parametrize('score', [(0,0), (1,0), (0,2)])
def test_confirmed_zero_and_scores_are_visible(score):
    normalized = snapshot_engine.normalize_match(record(home_score=score[0], away_score=score[1]), now=NOW)
    assert f'{score[0]} - {score[1]}' in str(render_card(normalized))


@pytest.mark.parametrize('value', [None, '', float('nan'), float('inf'), True, 'invalid'])
def test_partial_or_invalid_score_is_not_replaced_by_zero_or_old_score(value):
    row = record(home_score=value, away_score=2, score='4-2')
    normalized = snapshot_engine.normalize_match(row, now=NOW)
    json.dumps(normalized, allow_nan=False)
    html = str(render_card(normalized))
    assert 'Resultado pendiente' in html
    assert '4 - 2' not in html and '0 - 2' not in html


def test_legacy_macro_remains_available_for_non_projected_lanes():
    row = record(); html = str(render_card(row)); parsed = Cards(html)
    assert len(parsed.articles) == 1
    assert parsed.wrappers == []
    assert '/match/live-consumer-qa' in parsed.links


def test_fresh_then_expired_then_finished_snapshot_does_not_invent_live():
    row = record()
    fresh = snapshot_engine.build_realtime_snapshot(summary([row]), now=NOW)
    expired = snapshot_engine.build_realtime_snapshot(summary([row]), now=NOW+timedelta(minutes=5))
    finished = snapshot_engine.build_realtime_snapshot(summary([{**row,'status':'FT'}]), now=NOW+timedelta(minutes=5))
    assert fresh['counts']['live'] == 1
    assert expired['live'] == [] and expired['matches'] == []
    assert expired['stale_live'][0]['realtime_state']['is_stale'] is True
    assert finished['counts']['live'] == 0 and finished['counts']['finished'] == 1
    assert finished['matches'][0]['realtime_state']['status_canonical'] == 'FINISHED'
    assert 'Min 67' not in str(render_card(finished['matches'][0]))


def test_one_clock_across_multiple_rows(monkeypatch):
    calls = []; original = snapshot_engine._now
    def advancing(now=None):
        if now is None:
            calls.append(1)
            return NOW + timedelta(seconds=len(calls)-1)
        return original(now)
    monkeypatch.setattr(snapshot_engine, '_now', advancing)
    rows = [record(id=f'qa-{i}', match_id=f'qa-{i}') for i in range(3)]
    snap = snapshot_engine.build_realtime_snapshot(summary(rows))
    assert len(calls) == 1
    assert {m['realtime_state']['evaluated_at_madrid'] for m in snap['matches']} == {NOW.isoformat()}


def test_priority_invalid_clock_and_metadata_do_not_become_fresh_data():
    row = record(live_updated_at='not-a-timestamp', lineups={'status':'NOT_REQUESTED','available':False})
    normalized = snapshot_engine.normalize_match(row, now=NOW)
    assert normalized['is_live'] is False
    assert normalized['updated_at'] == ''
    assert normalized['realtime_state']['coverage']['lineups']['state'] == 'NOT_REQUESTED'


def test_sports_snapshot_is_read_only_and_does_not_emit_raw_payload(monkeypatch):
    import socket, sqlite3
    attempts = []
    def deny(*args, **kwargs):
        attempts.append(True); raise AssertionError('No external access')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(sqlite3, 'connect', deny)
    row = record(raw_json={'irrelevant_private':'must-not-leak'})
    result = snapshot_engine.build_realtime_snapshot(summary([row]), now=NOW)
    assert 'must-not-leak' not in json.dumps(result)
    assert attempts == []
