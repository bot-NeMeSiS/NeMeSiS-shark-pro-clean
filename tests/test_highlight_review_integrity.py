"""Synthetic media review: stable identity, stale forms, and read-only failure.

No provider calls, real media approvals or Flask substitutions. This suite runs
against the actual review engine and SQLite storage independently of HTTP.
"""
import copy
import sqlite3
from datetime import datetime as RealDatetime

import pytest
from engines import highlight_review_engine as review
from engines import sportsdb_highlights_engine as media
from engines.highlight_url_engine import review_fingerprint

URL = 'https://www.youtube.com/watch?v=officialQA1'


@pytest.fixture
def archive(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('No network permitted in media review tests')
    monkeypatch.setattr('urllib.request.urlopen', no_network)
    db = tmp_path / 'media.db'
    media.ensure_sportsdb_highlights_schema(str(db))
    with media._connect(str(db)) as conn:
        conn.execute('CREATE TABLE matches(id TEXT PRIMARY KEY,external_id TEXT,source TEXT,home_team TEXT,away_team TEXT,match_date TEXT)')
        conn.execute("INSERT INTO matches VALUES('match-a','123','TheSportsDB API','Norte','Sur','2026-09-20')")
        item = media._upsert_highlight(conn, {'idEvent':'123','dateEvent':'2026-09-20',
           'strHomeTeam':'Norte','strAwayTeam':'Sur','strVideo':URL})
    return db, item['id']


def form(row, **extra):
    return {'decision':'LINK_ONLY','review_token':row['review_token'],
      'evidence_url':'https://example.org/qa-only-licence','attribution':'SIMULATED_QA',
      'basis':'Synthetic permission solely for this isolated test.',
      'rights_status':'LICENSED','confirmed':'1', **extra}


def snapshot(db):
    return review.review_snapshot(str(db))['items'][0]


@pytest.mark.parametrize('field,value',[
 ('attribution','Different attribution'),('attribution_required',1),
 ('official_source_verified',1),('geo_restriction_status','BLOCKED'),
 ('thumbnail_rights_status','BLOCKED'),('thumbnail_commercial_use_status','DENIED'),
 ('thumbnail_attribution','Other source'),('rights_note','BLOCKED'),
 ('status','BLOCKED'),('client_status','BLOCKED'),('source','Other provider'),
 ('provider','Other video provider'),('updated_at','2026-09-22T00:00:00+00:00'),
])
def test_old_form_cannot_override_changed_review_metadata(archive,field,value):
    db,hid=archive
    old=snapshot(db)
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE sportsdb_match_highlights SET '+field+'=? WHERE id=?',(value,hid))
    before=db.read_bytes()
    with pytest.raises(review.ReviewError,match='cambiado'):
        review.decide_highlight(str(db),hid,form(old),actor='test-admin')
    assert db.read_bytes()==before


def test_second_review_in_same_clock_tick_invalidates_earlier_form(archive,monkeypatch):
    db,hid=archive
    class FrozenDatetime:
        @staticmethod
        def now(tz):
            return RealDatetime(2026,9,22,20,0,0,tzinfo=tz)
    monkeypatch.setattr(review,'datetime',FrozenDatetime)
    first=snapshot(db)
    review.decide_highlight(str(db),hid,form(first),actor='test-admin')
    approved=snapshot(db)
    review.decide_highlight(str(db),hid,form(approved),actor='test-admin')
    with pytest.raises(review.ReviewError,match='cambiado'):
        review.decide_highlight(str(db),hid,form(approved),actor='stale-admin')
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_highlight_reviews').fetchone()[0]==2


def test_review_missing_file_never_creates_empty_database(tmp_path):
    db=tmp_path/'missing.db'
    with pytest.raises(review.ReviewError):
        review.decide_highlight(str(db),'missing',form({'review_token':'old'}),actor='test-admin')
    assert not db.exists()


def test_wrong_existing_database_is_not_initialized(tmp_path):
    db=tmp_path/'unrelated.db'
    with sqlite3.connect(db) as conn:conn.execute('CREATE TABLE unrelated(id TEXT)')
    before=db.read_bytes()
    with pytest.raises(review.ReviewError):
        review.decide_highlight(str(db),'missing',form({'review_token':'old'}),actor='test-admin')
    assert db.read_bytes()==before


def test_missing_record_does_not_create_review_table(archive):
    db,_=archive
    before=db.read_bytes()
    with pytest.raises(review.ReviewError):
        review.decide_highlight(str(db),'missing',form({'review_token':'old'}),actor='test-admin')
    assert db.read_bytes()==before


def test_corrupt_review_ledger_must_not_be_treated_as_zero_history(archive):
    db,hid=archive
    old=snapshot(db)
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE sportsdb_highlight_reviews(unrelated TEXT)')
    before=db.read_bytes()
    state=review.review_snapshot(str(db))
    assert state['state']=='READ_UNAVAILABLE'
    assert state['counts']=={} and state['items']==[] and state['runs']==[]
    with pytest.raises((review.ReviewError,sqlite3.Error)):
        review.decide_highlight(str(db),hid,form(old),actor='test-admin')
    assert db.read_bytes()==before


def test_reading_review_token_never_writes_and_keeps_input_immutable(archive):
    db,_=archive
    before=db.read_bytes()
    first=snapshot(db);second=snapshot(db)
    assert first['review_token']==second['review_token']
    assert db.read_bytes()==before
    row={'id':'qa','attribution':'Fuente','review_revision':3}
    original=copy.deepcopy(row)
    assert review_fingerprint(row)==review_fingerprint(row) and row==original


def test_success_records_one_audit_decision_and_rejects_duplicate_form(archive):
    db,hid=archive
    old=snapshot(db)
    result=review.decide_highlight(str(db),hid,form(old),actor='test-admin')
    assert result['ok'] and snapshot(db)['can_display']
    with pytest.raises(review.ReviewError):
        review.decide_highlight(str(db),hid,form(old),actor='test-admin')
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_highlight_reviews').fetchone()[0]==1
        assert conn.execute('SELECT allowed_channels_json FROM sportsdb_match_highlights').fetchone()[0]=='["APP"]'


def test_concurrent_reviewers_cannot_both_apply_one_form(archive):
    from concurrent.futures import ThreadPoolExecutor
    db,hid=archive
    values=form(snapshot(db))
    def decide(actor):
        try:
            review.decide_highlight(str(db),hid,values,actor=actor)
            return 'applied'
        except review.ReviewError:
            return 'stale'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(decide,['admin-a','admin-b']))
    assert sorted(results)==['applied','stale']
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_highlight_reviews').fetchone()[0]==1


def test_storage_failure_rolls_back_approval_and_its_audit_row(archive):
    db,hid=archive
    values=form(snapshot(db))
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TRIGGER reject_media_change BEFORE UPDATE ON sportsdb_match_highlights BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    before=db.read_bytes()
    with pytest.raises(sqlite3.Error):
        review.decide_highlight(str(db),hid,values,actor='test-admin')
    assert db.read_bytes()==before
    assert not snapshot(db)['can_display']


def test_only_valid_review_migrates_legacy_review_columns(archive):
    db,hid=archive
    with sqlite3.connect(db) as conn:
        conn.execute('ALTER TABLE sportsdb_match_highlights DROP COLUMN embed_policy')
        conn.execute('ALTER TABLE sportsdb_match_highlights DROP COLUMN allowed_channels_json')
    old=snapshot(db)
    before=db.read_bytes()
    with pytest.raises(review.ReviewError,match='cambiado'):
        review.decide_highlight(str(db),hid,form(old,review_token='invalid'),actor='test-admin')
    assert db.read_bytes()==before
    review.decide_highlight(str(db),hid,form(old),actor='test-admin')
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT embed_policy,allowed_channels_json FROM sportsdb_match_highlights').fetchone()==('LINK_ONLY','["APP"]')
