"""Synthetic SQLite regression: canonical observations must not rewrite provider truth."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import sqlite3

import pytest
from engines import daily_automation_engine as daily
from engines.v935_launch_trust_engine import match_status_truth

NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)

@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    def reject(*args, **kwargs):
        pytest.fail('Reconciliation must not contact a provider or any network')
    monkeypatch.setattr(socket.socket, 'connect', reject)

@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'synthetic.db'
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute('''CREATE TABLE matches(id TEXT PRIMARY KEY,status TEXT,score TEXT,
            home_score INTEGER,away_score INTEGER,match_date TEXT,kickoff_time TEXT,match_time TEXT,
            kickoff_iso TEXT,updated_at TEXT,last_synced_at TEXT,provider_updated_at TEXT,
            provider_status TEXT,raw_json TEXT)''')
    return path

def add(db, status='NS', offset=2, scores=(0, 0), ident='qa', **kwargs):
    kickoff = NOW + timedelta(hours=offset)
    values = dict(id=ident,status=status,score='',home_score=scores[0],away_score=scores[1],
        match_date=kickoff.date().isoformat(),kickoff_time=kickoff.strftime('%H:%M'),match_time='',
        kickoff_iso=kickoff.isoformat(),updated_at=(NOW-timedelta(days=1)).isoformat(),
        last_synced_at=NOW.isoformat(),provider_updated_at=NOW.isoformat(),provider_status='',raw_json='{}')
    values.update(kwargs)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute('INSERT INTO matches VALUES ('+','.join('?' for _ in values)+')',tuple(values.values()))
    return values

def snapshot(db):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute('SELECT * FROM matches ORDER BY id').fetchall()

@pytest.mark.parametrize('status,offset,scores,expected',[
    ('NS',2,(0,0),'UPCOMING'), ('NS',2,(None,None),'UPCOMING'),
    ('PST',-24,(None,None),'POSTPONED'), ('CANC',-24,(None,None),'CANCELLED'),
    ('SUSP',-2,(1,0),'SUSPENDED'), ('ABD',-2,(1,0),'ABANDONED'),
    ('HT',-1,(0,0),'HALFTIME'), ('1H',-.5,(0,0),'LIVE'),
    ('2H',-1,(1,0),'LIVE'), ('ET',-2,(1,1),'LIVE'),
    ('FT',-3,(0,0),'FINISHED'), ('AET',-3,(2,1),'FINISHED'),
    ('FT',-3,(None,None),'RESULT_PENDING'), ('NS',-3,(None,None),'RESULT_PENDING'),
    ('',2,(None,None),'UPCOMING')])
def test_raw_status_scores_and_source_clocks_never_rewritten(db,status,offset,scores,expected):
    original=add(db,status,offset,scores)
    before=snapshot(db)
    result=daily.reconcile_match_lifecycle(str(db),now=NOW)
    assert snapshot(db)==before
    assert result['ok'] and result['mode']=='CANONICAL_READ_ONLY'
    assert result['lifecycle_counts'][expected]==1
    assert result['updated']=={'past_pending':0,'future_upcoming':0,'finalized':0}
    assert result['assessed']==1 and not result['truncated']
    assert match_status_truth(original,now=NOW)['lifecycle']==expected

def test_no_score_or_minute_infers_finish(db):
    add(db,'NS',3,(2,1))
    result=daily.reconcile_match_lifecycle(str(db),now=NOW)
    assert result['lifecycle_counts']['UPCOMING']==1
    assert snapshot(db)[0][1]=='NS'

def test_live_without_recent_provider_clock_is_stale_not_final(db):
    add(db,'LIVE',-1,(0,0),last_synced_at=(NOW-timedelta(hours=1)).isoformat(),
        provider_updated_at=(NOW-timedelta(hours=1)).isoformat())
    before=snapshot(db)
    result=daily.reconcile_match_lifecycle(str(db),now=NOW)
    assert result['lifecycle_counts']['STALE']==1 and snapshot(db)==before

def test_conflicting_provider_signals_remain_visible(db):
    add(db,'LIVE',-2,(1,0),provider_status='FT')
    before=snapshot(db)
    result=daily.reconcile_match_lifecycle(str(db),now=NOW)
    assert result['status_conflicts']==1 and snapshot(db)==before

def test_future_derived_state_can_change_without_mutating_provider_row(db):
    add(db,'NS',2,(0,0))
    before=snapshot(db)
    first=daily.reconcile_match_lifecycle(str(db),now=NOW)
    later=daily.reconcile_match_lifecycle(str(db),now=NOW+timedelta(hours=4))
    assert first['lifecycle_counts']['UPCOMING']==1
    assert later['lifecycle_counts']['RESULT_PENDING']==1 and snapshot(db)==before

def test_metadata_and_database_bytes_unchanged_by_read(db):
    add(db)
    before=db.read_bytes()
    daily.reconcile_match_lifecycle(str(db),now=NOW)
    assert db.read_bytes()==before
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()==[('matches',)]

def test_missing_database_is_not_created(tmp_path):
    path=tmp_path/'absent.db'
    result=daily.reconcile_match_lifecycle(str(path),now=NOW)
    assert not path.exists() and not result['ok']

def test_missing_table_is_reported_without_migration(tmp_path):
    path=tmp_path/'empty.db'
    with closing(sqlite3.connect(path)) as conn: conn.execute('CREATE TABLE untouched(id TEXT)')
    before=path.read_bytes()
    result=daily.reconcile_match_lifecycle(str(path),now=NOW)
    assert result['skipped'] and result['reason']=='matches_table_missing' and path.read_bytes()==before

def test_missing_primary_identity_is_safe(tmp_path):
    path=tmp_path/'schema.db'
    with closing(sqlite3.connect(path)) as conn: conn.execute('CREATE TABLE matches(status TEXT)')
    result=daily.reconcile_match_lifecycle(str(path),now=NOW)
    assert result['skipped'] and result['reason']=='matches_identity_missing'

def test_corrupt_database_not_presented_as_empty_success(tmp_path):
    path=tmp_path/'corrupt.db';path.write_bytes(b'not-a-database')
    result=daily.reconcile_match_lifecycle(str(path),now=NOW)
    assert not result['ok'] and result['reason']=='storage_unavailable'

def test_bounded_sampling_reports_truncation_and_limits_details(db):
    for i in range(205): add(db,ident=f'{i:04}')
    result=daily.reconcile_match_lifecycle(str(db),now=NOW)
    assert result['assessed']==200 and result['truncated']
    assert len(result['samples'])<=20 and not result['complete_database_audit']

def test_timezone_is_madrid_for_observation_day(db):
    add(db)
    result=daily.reconcile_match_lifecycle(str(db),now=NOW.replace(hour=23))
    assert result['madrid_date']=='2026-09-23'

def test_sql_trace_has_no_mutation(db,monkeypatch):
    add(db);statements=[];connect=sqlite3.connect
    def traced(*args,**kwargs):
        conn=connect(*args,**kwargs);conn.set_trace_callback(statements.append);return conn
    monkeypatch.setattr(daily.sqlite3,'connect',traced)
    assert daily.reconcile_match_lifecycle(str(db),now=NOW)['ok']
    assert not any(s.lstrip().split()[0].upper() in {'UPDATE','DELETE','INSERT','CREATE','ALTER','DROP','REPLACE'} for s in statements)

def test_master_retains_job_audit_without_rewriting_sports(db,monkeypatch):
    import secrets
    add(db,'NS',2,(0,0));before=snapshot(db)
    monkeypatch.setattr(daily,'madrid_now',lambda: NOW)
    monkeypatch.setattr(daily,'jobs_due',lambda *args,**kwargs:['match_lifecycle_reconciler'])
    result=daily.run_master_tick(str(db),'SIMULATED_QA',env={'AUTOMATION_SECRET':secrets.token_urlsafe(24)})
    assert result['ok'] and result['telegram_sent']==0
    assert result['jobs_run'][0]['summary']['lifecycle_counts']['UPCOMING']==1
    assert result['jobs_run'][0]['summary']['mode']=='CANONICAL_READ_ONLY'
    assert snapshot(db)==before
    with closing(sqlite3.connect(db)) as conn:
        row=conn.execute('SELECT status,summary_json FROM automation_job_runs').fetchone()
        assert row[0]=='OK' and json.loads(row[1])['source_evidence_unchanged']
