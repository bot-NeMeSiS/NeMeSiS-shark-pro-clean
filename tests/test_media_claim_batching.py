"""Real SQLite selection, full traversal, rollback and independent claimers."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
import json
import sqlite3
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from engines import highlight_coverage as media

NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc).timestamp()


def catalogue(tmp_path, count=260):
    path = tmp_path / 'claims.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE matches(id TEXT PRIMARY KEY,external_id TEXT,source TEXT,'
                     'home_team TEXT,away_team TEXT,match_date TEXT,kickoff_time TEXT,'
                     'competition_name TEXT,league_id TEXT,status TEXT,score TEXT,raw_json TEXT)')
        conn.executescript(media.SCHEMA)
        for i in range(count):
            row = dict(id=f'm{i:05}', external_id=f'sportsdb-{1000+i}', source='TheSportsDB',
                       home_team=f'Home {i}', away_team=f'Away {i}', match_date='2025-01-01',
                       kickoff_time='18:00', competition_name='League', league_id='42',
                       status='FT', score='2-1', raw_json=json.dumps({'source_value':i}))
            conn.execute('INSERT INTO matches VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
            conn.execute('INSERT INTO highlight_coverage(match_id,identity,state,due_at,updated_at) '
                         "VALUES(?,?,'UNSCANNED',?,?)",(row['id'],media.identity(row),NOW,NOW))
    return media.Coverage(path, NOW)


def legacy_winner(coverage, historical=True):
    """Exact pre-V995 WHERE/ordering, retained as the compatibility oracle."""
    with closing(coverage.connect()) as conn:
        expr=coverage.projection(conn)
        cutoff=datetime.fromtimestamp(NOW-7*86400,ZoneInfo('Europe/Madrid')).date().isoformat()
        row=conn.execute(f'SELECT c.*,{expr} AS payload FROM highlight_coverage c JOIN matches m ON m.id=c.match_id '
            f'WHERE coverage_eligible({expr}) AND c.identity=coverage_identity({expr}) '
            "AND c.state NOT IN ('LINKED','VIDEO_FOUND','AMBIGUOUS') AND c.due_at<=? AND c.lease_until<=? "
            +('AND substr(m.match_date,1,10)<? ' if historical else '')+
            'ORDER BY CASE WHEN c.checked_at IS NULL THEN 0 ELSE 1 END,c.priority DESC,c.due_at,m.match_date DESC,c.match_id LIMIT 1',
            (NOW,NOW,cutoff) if historical else (NOW,NOW)).fetchone()
        if row is None:return None
        result=dict(row);result['match']=json.loads(result.pop('payload'))
        result['historical']=historical
        return result


def same_job(actual, expected):
    if expected is None:assert actual is None
    else:
        assert len(actual['lease'])==32
        assert {k:v for k,v in actual.items() if k!='lease'}=={k:v for k,v in expected.items() if k!='lease'}


def stored(coverage):
    with sqlite3.connect(coverage.path) as conn:
        return {t:conn.execute('SELECT * FROM '+t+' ORDER BY 1').fetchall()
                for t in ('matches','highlight_coverage','highlight_coverage_budget')}


def test_first_valid_does_not_validate_the_whole_queue(tmp_path,monkeypatch):
    coverage=catalogue(tmp_path,1200)
    expected=legacy_winner(coverage)
    counts={'eligible':0,'identity':0}
    for name in counts:
        original=getattr(media,name)
        def wrap(*args,_name=name,_original=original):
            counts[_name]+=1
            return _original(*args)
        monkeypatch.setattr(media,name,wrap)
    before=stored(coverage)
    same_job(coverage.claim(),expected)
    assert counts=={'eligible':1,'identity':1}
    after=stored(coverage)
    assert before['matches']==after['matches'] and before['highlight_coverage_budget']==after['highlight_coverage_budget']
    assert sum(a!=b for a,b in zip(before['highlight_coverage'],after['highlight_coverage']))==1


@pytest.mark.parametrize('invalid_count',[1,63,64,65,130,259,260])
def test_invalid_identity_never_stops_at_a_batch_boundary(tmp_path,invalid_count):
    coverage=catalogue(tmp_path)
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE highlight_coverage SET identity='changed' WHERE match_id<?",(f'm{invalid_count:05}',))
    expected=legacy_winner(coverage)
    same_job(coverage.claim(),expected)
    assert (expected['match_id'] if expected else None)==(f'm{invalid_count:05}' if invalid_count<260 else None)


@pytest.mark.parametrize('historical',[True,False])
def test_preserves_checked_priority_due_date_and_id_order(tmp_path,historical):
    coverage=catalogue(tmp_path)
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE highlight_coverage SET checked_at=?,priority=99 WHERE match_id='m00000'",(NOW,))
        conn.execute("UPDATE highlight_coverage SET priority=4 WHERE match_id IN ('m00050','m00051','m00052')")
        conn.execute("UPDATE highlight_coverage SET due_at=? WHERE match_id='m00051'",(NOW-10,))
        conn.execute("UPDATE matches SET match_date='2026-10-19' WHERE id='m00051'")
        conn.row_factory=sqlite3.Row
        row=dict(conn.execute("SELECT * FROM matches WHERE id='m00051'").fetchone())
        conn.execute("UPDATE highlight_coverage SET identity=? WHERE match_id='m00051'",(media.identity(row),))
    expected=legacy_winner(coverage,historical)
    same_job(coverage.claim(historical),expected)
    assert expected['match_id']==('m00050' if historical else 'm00051')


def test_nonfinal_and_ineligible_leaders_do_not_hide_later_match(tmp_path):
    coverage=catalogue(tmp_path)
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE matches SET status='NS' WHERE id<'m00130'")
        conn.execute("UPDATE matches SET competition_name='',league_id='' WHERE id='m00130'")
    expected=legacy_winner(coverage)
    same_job(coverage.claim(),expected)
    assert expected['match_id']=='m00131'


def test_global_lease_blocks_even_an_unrelated_candidate(tmp_path):
    coverage=catalogue(tmp_path)
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE highlight_coverage SET state='LINKED',lease_until=? WHERE match_id='m00259'",(NOW+1,))
    before=stored(coverage)
    assert coverage.claim() is None
    assert stored(coverage)==before


def test_independent_connections_cannot_both_claim(tmp_path):
    coverage=catalogue(tmp_path)
    barrier=Barrier(2)
    def claim(_):
        barrier.wait(timeout=5)
        return media.Coverage(coverage.path,NOW).claim()
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=list(pool.map(claim,range(2)))
    assert sum(j is not None for j in jobs)==1
    with sqlite3.connect(coverage.path) as conn:
        assert conn.execute('SELECT count(*) FROM highlight_coverage WHERE lease_until>?',(NOW,)).fetchone()[0]==1


def test_failed_validation_rolls_back_and_releases_writer(tmp_path,monkeypatch):
    coverage=catalogue(tmp_path)
    before=stored(coverage)
    def broken(*args):raise RuntimeError('synthetic validation failure')
    monkeypatch.setattr(media,'eligible',broken)
    with pytest.raises((RuntimeError,sqlite3.OperationalError)):
        coverage.claim()
    assert stored(coverage)==before
    with sqlite3.connect(coverage.path,timeout=.1) as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.rollback()


def test_optional_payload_columns_and_nulls_keep_sqlite_projection(tmp_path):
    coverage=catalogue(tmp_path,1)
    with sqlite3.connect(coverage.path) as conn:
        conn.execute('ALTER TABLE matches DROP COLUMN raw_json')
        conn.execute('ALTER TABLE matches ADD COLUMN country TEXT')
    expected=legacy_winner(coverage)
    job=coverage.claim()
    same_job(job,expected)
    assert job['match']['country'] is None and 'raw_json' not in job['match']


def test_later_batch_validation_failure_also_rolls_back(tmp_path,monkeypatch):
    coverage=catalogue(tmp_path)
    with sqlite3.connect(coverage.path) as conn:
        conn.execute("UPDATE highlight_coverage SET identity='changed' WHERE match_id<'m00130'")
    before=stored(coverage)
    original=media.eligible
    def broken(match,now):
        if match['id']=='m00130':raise RuntimeError('later batch validation')
        return original(match,now)
    monkeypatch.setattr(media,'eligible',broken)
    with pytest.raises((RuntimeError,sqlite3.OperationalError)):
        coverage.claim()
    assert stored(coverage)==before
    with sqlite3.connect(coverage.path,timeout=.1) as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.rollback()


@pytest.mark.parametrize('state',['LINKED','VIDEO_FOUND','AMBIGUOUS'])
def test_terminal_states_and_not_due_rows_remain_excluded(tmp_path,state):
    coverage=catalogue(tmp_path,3)
    with sqlite3.connect(coverage.path) as conn:
        conn.execute('UPDATE highlight_coverage SET state=? WHERE match_id=?',(state,'m00000'))
        conn.execute('UPDATE highlight_coverage SET due_at=? WHERE match_id=?',(NOW+1,'m00001'))
    expected=legacy_winner(coverage)
    same_job(coverage.claim(),expected)
    assert expected['match_id']=='m00002'
