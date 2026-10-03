from datetime import datetime, timedelta, timezone
from test_postmatch_recovery import store, EVENT, NOW, MATCH
from engines.highlight_policy_engine import register_policy
from engines.postmatch_recovery import finish
from engines.highlight_read_model import read_highlights_for_match


def test_future_policy_finishes_postmatch_without_manual_rights_step(store):
    # Document permission before receipt; this test never contacts a provider.
    current = datetime.now(timezone.utc)
    with store.connection(True) as conn:
        register_policy(conn, dict(source='TheSportsDB',scope_kind='CHANNEL',scope_value='official-channel',
            channels=['APP'],modality='LINK_ONLY',evidence_url='https://holder.example/licence',
            basis='All future match summaries on this channel for commercial APP links.',
            attribution='Titular',commercial_use=True,rights_status='LICENSED',
            review_at=(current+timedelta(days=60)).isoformat(),channel_identity_verified=True),
            actor='reviewer',now=current-timedelta(seconds=2))
    store.discover(NOW)
    job = store.claim(NOW)
    assert job['kind'] == 'highlights'
    result = finish(store,job,{'event':{**EVENT,'idChannel':'official-channel'},'external_calls':0},NOW)
    assert result['state'] == 'COMPLETE'
    visible = read_highlights_for_match(store.path,MATCH['id'])['highlights']
    assert len(visible) == 1 and visible[0]['can_link'] and not visible[0]['can_embed']
