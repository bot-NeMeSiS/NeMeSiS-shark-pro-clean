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


def test_catalogue_reconciliation_does_not_rescan_media_for_unlinked_backlog(store, monkeypatch):
    from contextlib import contextmanager

    store.discover(NOW)
    with store.connection(True) as conn:
        _upsert_highlight(conn, EVENT)
        conn.executemany(
            "INSERT INTO postmatch_jobs(match_id,kind,identity,due_at,created_at,updated_at) "
            "VALUES(?,'highlights',?,?,?,?)",
            ((f'unlinked-{i}',f'identity-{i}',NOW,NOW,NOW) for i in range(10000)))
        conn.executemany('INSERT INTO sportsdb_match_highlights(id,match_id) VALUES(?,?)',
                         ((f'catalogue-{i}',f'catalogue-only-{i}') for i in range(100)))
        # Duplicate catalogue links still represent one recovery job.
        conn.execute('INSERT INTO sportsdb_match_highlights(id,match_id) VALUES(?,?)',
                     ('duplicate-link',MATCH['id']))
    original_connection = store.connection
    batches = [0]
    def progress():
        batches[0] += 1
        return 0
    @contextmanager
    def counted_connection(write=False):
        with original_connection(write) as conn:
            conn.set_progress_handler(progress,100)
            try:
                yield conn
            finally:
                conn.set_progress_handler(None,0)
    monkeypatch.setattr(store,'connection',counted_connection)
    reconcile_media_reviews(store,NOW)
    assert batches[0]*100 < 300000, 'unlinked backlog repeatedly scans the media catalogue'
    with original_connection() as conn:
        row=conn.execute("SELECT state,attempts FROM postmatch_jobs WHERE match_id=? AND kind='highlights'",
                         (MATCH['id'],)).fetchone()
        assert tuple(row)==('REVIEW_REQUIRED',0)
        assert conn.execute("SELECT COUNT(*) FROM postmatch_audit WHERE action='CATALOGUE_LINK_REUSED'").fetchone()[0]==1
        assert conn.execute('SELECT COUNT(*) FROM postmatch_source_budget').fetchone()[0]==0
        assert conn.execute("SELECT COUNT(*) FROM postmatch_jobs WHERE match_id LIKE 'unlinked-%' AND state='PENDING'").fetchone()[0]==10000


def test_catalogue_candidate_order_limit_and_duplicates_preserve_rights_rotation(store, monkeypatch):
    from engines.postmatch_store import identity
    candidates=[]
    states=('PENDING','RETRY','REVIEW_REQUIRED','COMPLETE','CANCELLED')
    with store.connection(True) as conn:
        for i in range(220):
            match={**MATCH,'id':f'rotation-{i}'}
            conn.execute('INSERT INTO matches VALUES('+','.join('?' for _ in match)+')',tuple(match.values()))
            state=states[i%len(states)]
            kind='statistics' if i%11==0 else 'highlights'
            due=NOW+(i%7)*30
            job=conn.execute('INSERT INTO postmatch_jobs(match_id,kind,identity,state,due_at,created_at,updated_at) '
                             'VALUES(?,?,?,?,?,?,?)',
                             (match['id'],kind,identity(match),state,due,NOW,NOW))
            conn.execute('INSERT INTO sportsdb_match_highlights(id,match_id) VALUES(?,?)',
                         (f'rotation-media-{i}',match['id']))
            if i%3==0:
                conn.execute('INSERT INTO sportsdb_match_highlights(id,match_id) VALUES(?,?)',
                             (f'rotation-duplicate-{i}',match['id']))
            if kind=='highlights' and state in ('PENDING','RETRY','REVIEW_REQUIRED'):
                candidates.append((state=='REVIEW_REQUIRED',due,job.lastrowid,match['id']))
        conn.execute('INSERT INTO sportsdb_match_highlights(id,match_id) VALUES(?,NULL)',('unlinked-null',))
    assert len(candidates)>100
    observed=[]
    def observe_and_stop_before_rights(match, now):
        observed.append(match['id'])
        return False
    monkeypatch.setattr('engines.postmatch_recovery.is_final',observe_and_stop_before_rights)
    reconcile_media_reviews(store,NOW)
    expected=[item[3] for item in sorted(candidates)[:100]]
    assert observed==expected
    assert len(observed)==len(set(observed))==100
