"""Temporary SQLite and synthetic prices only; no external clients or secrets."""
import json
import sqlite3
from datetime import timedelta

import pytest

from test_combi_advisor_contract import db, NOW, ready_save, preview_values
from engines import client_combi_store as store
from engines.combi_advisor_engine import CombiError
from engines.combi_draft_review import review_draft


@pytest.fixture
def saved(db):
    return store.save_draft(db, 'a', ready_save(db), now=NOW)['id']


def test_unchanged_draft_can_be_reviewed_without_writing(db, saved):
    before = open(db, 'rb').read()
    result = review_draft(db, 'a', saved, now=NOW)
    assert result['can_prepare'] and result['original_unchanged'] and result['external_calls'] == 0
    assert result['preview']['stake'] == '0.10'
    assert result['changed_count'] == result['blocked_count'] == 0
    assert result['preview']['probability'] is None and result['not_a_bet']
    assert open(db, 'rb').read() == before


def test_quote_change_compares_then_requires_a_separate_save(db, saved):
    with sqlite3.connect(db) as conn:
        original = conn.execute('SELECT payload_json FROM client_combi_drafts WHERE id=?', (saved,)).fetchone()[0]
        conn.execute("UPDATE picks SET odds='1.8' WHERE id='p1'")
    result = review_draft(db, 'a', saved, now=NOW)
    assert result['changed_count'] == 1 and result['can_prepare']
    leg = result['comparisons'][0]
    assert (leg['previous_odds'], leg['current_odds'], leg['state']) == ('1.5', '1.8', 'PRICE_CHANGED')
    assert result['preview']['total_odds'] == '2.70'
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM client_combi_drafts').fetchone()[0] == 1
        assert conn.execute('SELECT payload_json FROM client_combi_drafts WHERE id=?', (saved,)).fetchone()[0] == original


@pytest.mark.parametrize('status', ['LIVE', 'HT', 'FT', 'PST', 'CANC', 'SUSP'])
def test_started_or_unavailable_matches_do_not_produce_another_preview(db, saved, status):
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE matches SET status=? WHERE id='m1'", (status,))
    result = review_draft(db, 'a', saved, now=NOW)
    assert not result['can_prepare'] and result['blocked_count'] == 1
    assert result['comparisons'][0]['state'] == 'BLOCKED'


def test_expired_quotes_stay_historical_not_live(db, saved):
    result = review_draft(db, 'a', saved, now=NOW + timedelta(minutes=16))
    assert not result['can_prepare'] and result['blocked_count'] == 2
    assert all(not row['current_is_eligible'] for row in result['comparisons'])


@pytest.mark.parametrize('sql', [
    "UPDATE picks SET selection='X' WHERE id='p1'",
    "UPDATE picks SET market='dnb' WHERE id='p1'",
    "UPDATE picks SET bookmaker='Other' WHERE id='p1'",
    "UPDATE picks SET match_id='m3',home_team='Local 3',away_team='Visitante 3' WHERE id='p1'",
    "UPDATE matches SET home_team='Different' WHERE id='m1'",
])
def test_reused_pick_id_cannot_replace_the_original_selection(db, saved, sql):
    with sqlite3.connect(db) as conn:
        conn.execute(sql)
    result = review_draft(db, 'a', saved, now=NOW)
    assert not result['can_prepare'] and result['comparisons'][0]['state'] == 'SELECTION_CHANGED'
    assert result['comparisons'][0]['current_odds'] is None


def test_deleted_pick_remains_unavailable_without_filler(db, saved):
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM picks WHERE id='p1'")
    result = review_draft(db, 'a', saved, now=NOW)
    assert result['comparisons'][0]['state'] == 'UNAVAILABLE' and not result['can_prepare']
    assert len(result['comparisons']) == 2


@pytest.mark.parametrize('draft_id', ['missing', 'a'*32, '../test', '', None])
def test_missing_and_foreign_drafts_have_the_same_error(db, saved, draft_id):
    with pytest.raises(CombiError) as missing:
        review_draft(db, 'b', draft_id, now=NOW)
    with pytest.raises(CombiError) as foreign:
        review_draft(db, 'b', saved, now=NOW)
    assert (missing.value.code, missing.value.message, missing.value.status) == (foreign.value.code, foreign.value.message, 404)


def test_anonymous_cannot_read_private_draft(db, saved):
    with pytest.raises(CombiError) as error:
        review_draft(db, '', saved, now=NOW)
    assert error.value.status == 401


def test_changed_entitlement_does_not_reveal_premium_saved_or_current_selection(db, saved):
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE users SET membership='PRO',role='PRO' WHERE id='a'")
        conn.execute("UPDATE picks SET membership_required='ELITE' WHERE id='p1'")
    with pytest.raises(CombiError) as error:
        review_draft(db, 'a', saved, now=NOW)
    assert error.value.code == 'PLAN_REQUIRED' and 'Local 1' not in error.value.message


@pytest.mark.parametrize('payload', ['{}', 'null', 'bad-json', '{"contract":"wrong"}', '{"contract":"NEMESIS-COMBI-ADVICE-V1","legs":[]}'])
def test_malformed_stored_draft_does_not_become_a_valid_preview(db, saved, payload):
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE client_combi_drafts SET payload_json=? WHERE id=?', (payload, saved))
    with pytest.raises(CombiError) as error:
        review_draft(db, 'a', saved, now=NOW)
    assert error.value.code == 'DRAFT_INVALID'


def test_missing_storage_is_not_created(tmp_path):
    path = tmp_path/'missing.db'
    with pytest.raises(CombiError):
        review_draft(path, 'a', 'a'*32, now=NOW)
    assert not path.exists()


def test_absent_table_is_not_created_by_review(db):
    before = open(db, 'rb').read()
    with pytest.raises(CombiError):
        review_draft(db, 'a', 'a'*32, now=NOW)
    assert open(db, 'rb').read() == before


def test_revalidated_save_uses_normal_idempotency_and_does_not_overwrite(db, saved):
    import secrets
    result = review_draft(db, 'a', saved, now=NOW)
    values = {**preview_values(), 'revision':result['preview']['revision'], 'request_id':secrets.token_hex(16)}
    first = store.save_draft(db, 'a', values, now=NOW)
    repeated = store.save_draft(db, 'a', values, now=NOW)
    assert first['id'] != saved and repeated['id'] == first['id'] and repeated['replayed']
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM client_combi_drafts').fetchone()[0] == 2
