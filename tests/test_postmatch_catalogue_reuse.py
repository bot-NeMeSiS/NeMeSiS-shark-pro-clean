from test_postmatch_recovery import store, MATCH, EVENT, NOW
from engines.sportsdb_highlights_engine import _upsert_highlight
from engines.postmatch_recovery import reconcile_media_reviews


def test_cached_unapproved_link_stops_duplicate_recovery_without_granting_rights(store):
    store.discover(NOW)
    with store.connection(True) as conn:
        _upsert_highlight(conn, EVENT)
        original_rights=conn.execute('SELECT rights_status FROM sportsdb_match_highlights').fetchone()[0]
        conn.execute("UPDATE postmatch_jobs SET state='RETRY',reason='DAILY_BUDGET',due_at=?",(NOW+86400,))
    reconcile_media_reviews(store,NOW)
    jobs={row['kind']:row for row in store.snapshot()['jobs']}
    assert jobs['highlights']['state']=='REVIEW_REQUIRED'
    assert jobs['highlights']['attempts']==0
    assert jobs['statistics']['state']=='RETRY'
    assert store.snapshot()['budget']==[]
    with store.connection() as conn:
        assert conn.execute('SELECT rights_status FROM sportsdb_match_highlights').fetchone()[0]==original_rights


def test_ambiguous_existing_link_does_not_suppress_recovery(store):
    store.discover(NOW)
    with store.connection(True) as conn:
        _upsert_highlight(conn,EVENT)
        conn.execute("INSERT INTO matches SELECT 'duplicate',"+','.join(k for k in MATCH if k!='id')+" FROM matches WHERE id=?",(MATCH['id'],))
    reconcile_media_reviews(store,NOW)
    assert all(row['state']=='PENDING' for row in store.snapshot()['jobs'])


def test_exhausted_first_job_does_not_starve_next_ready_job(store):
    store.discover(NOW)
    with store.connection(True) as conn:
        conn.execute('UPDATE postmatch_jobs SET attempts=5 WHERE id=(SELECT MIN(id) FROM postmatch_jobs)')
    job=store.claim(NOW)
    assert job and job['kind']=='statistics'
    with store.connection() as conn:
        assert conn.execute('SELECT state FROM postmatch_jobs ORDER BY id LIMIT 1').fetchone()[0]=='FAILED'
