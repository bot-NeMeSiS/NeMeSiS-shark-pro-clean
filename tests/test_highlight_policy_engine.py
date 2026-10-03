from datetime import datetime, timedelta, timezone
import json
import sqlite3
import pytest

from engines.highlight_policy_engine import register_policy, resolve_policy, revoke_policy, attach_policies
from engines.sportsdb_highlights_engine import classify_stored_highlight

NOW = datetime.now(timezone.utc)
URL = 'https://www.youtube.com/watch?v=policy-fixture'


def values(**kwargs):
    return dict(source='TheSportsDB', scope_kind='CHANNEL', scope_value='official-channel-1',
                channels=['APP'], modality='LINK_ONLY', evidence_url='https://holder.example/licence',
                basis='Commercial APP links to all match summaries published by this channel.',
                attribution='Titular oficial', commercial_use=True, rights_status='LICENSED',
                review_at=(NOW + timedelta(days=60)).isoformat(), channel_identity_verified=True, **kwargs)


def row(**kwargs):
    result = dict(match_id='m1', source='TheSportsDB', video_url=URL, created_at=(NOW+timedelta(seconds=1)).isoformat(), raw_json=json.dumps({'idChannel':'official-channel-1'}))
    result.update(kwargs)
    return result


def setup():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    register_policy(conn, values(), actor='reviewer', now=NOW)
    return conn


def policies(conn):
    return [dict(x) for x in conn.execute('SELECT * FROM highlight_rights_policies')]


def test_equivalent_future_video_can_link_only_under_registered_channel_scope():
    conn = setup()
    rows = attach_policies(conn, [row(video_url=URL+'-future')])
    result = classify_stored_highlight(rows[0])
    assert result['show_block'] and result['can_link'] and not result['can_embed']
    assert result['attribution'] == 'Titular oficial'
    assert result['policy_id'] == 1


@pytest.mark.parametrize('change', [{'source':'OtherSource'}, {'raw_json':'{}'}, {'raw_json':json.dumps({'idChannel':'other-channel'})}])
def test_source_platform_or_other_channel_is_not_permission(change):
    conn = setup()
    assert resolve_policy(row(**change), policies(conn), now=NOW) is None
    assert not classify_stored_highlight(attach_policies(conn, [row(**change)])[0])['show_block']


def test_expiry_channel_mismatch_revocation_and_unlinked_fail_closed():
    conn = setup()
    registered = policies(conn)
    assert resolve_policy(row(), registered, now=NOW+timedelta(days=61))['decision'] == 'REVIEW_REQUIRED'
    assert resolve_policy(row(), registered, channel='TELEGRAM', now=NOW)['decision'] == 'REVIEW_REQUIRED'
    assert resolve_policy(row(match_id=''), registered, now=NOW)['decision'] == 'REVIEW_REQUIRED'
    revoke_policy(conn, 1, actor='reviewer')
    assert resolve_policy(row(), policies(conn), now=NOW)['decision'] == 'REVIEW_REQUIRED'


def test_conflicting_scope_does_not_select_arbitrary_approval():
    conn = setup()
    register_policy(conn, values(), actor='reviewer2', now=NOW)
    assert resolve_policy(row(), policies(conn), now=NOW)['decision'] == 'REVIEW_REQUIRED'


@pytest.mark.parametrize('key,value', [('evidence_url','https://www.thesportsdb.com/docs_terms_of_use.php'), ('commercial_use',False), ('channel_identity_verified',False), ('review_at',(NOW-timedelta(days=1)).isoformat()), ('channels',['TELEGRAM'])])
def test_subscription_or_missing_evidence_never_registers_approval(key,value):
    conn = sqlite3.connect(':memory:')
    candidate = values()
    candidate[key] = value
    with pytest.raises(ValueError):
        register_policy(conn, candidate, actor='reviewer', now=NOW)


def test_individual_review_cannot_be_overridden_by_channel_policy():
    conn = setup()
    for mode in ('BLOCKED','REVIEW_REQUIRED'):
        result = classify_stored_highlight(attach_policies(conn, [row(embed_policy=mode)])[0])
        assert not result['show_block']


def test_reader_without_registry_creates_nothing():
    conn = sqlite3.connect(':memory:')
    assert attach_policies(conn, [row()]) == [row()]
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0] == 0


def test_channel_policy_never_bulk_approves_previous_catalogue():
    conn = setup()
    for created in ('', (NOW-timedelta(days=1)).isoformat(), NOW.isoformat()):
        record = row(created_at=created)
        assert resolve_policy(record, policies(conn), now=NOW) is None
        assert not classify_stored_highlight(attach_policies(conn, [record])[0])['show_block']


def test_expired_exact_policy_overrides_old_authorization_flags():
    conn = setup()
    candidate = values()
    candidate.update(scope_kind='VIDEO', scope_value=URL, review_at=(NOW+timedelta(seconds=1)).isoformat())
    register_policy(conn, candidate, actor='reviewer', now=NOW)
    legacy = row(rights_status='LICENSED', commercial_use_status='ALLOWED', attribution='Titular', rights_verified_at=NOW.isoformat())
    policy = resolve_policy(legacy, policies(conn), now=NOW+timedelta(seconds=2))
    assert policy['decision'] == 'REVIEW_REQUIRED'
    assert not classify_stored_highlight({**legacy, '_rights_policy':policy})['show_block']
