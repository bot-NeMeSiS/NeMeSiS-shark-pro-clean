"""Additional real-HTTP source-boundary probes on owned synthetic data only."""
import sqlite3

import pytest

from test_shark_featured_pick_boundary import featured_probe, _client, _get, _revoke_pick
from test_shark_selected_pick_boundary import shark_probe


@pytest.mark.parametrize('path,plan', [('/', 'ANONYMOUS'), ('/', 'FREE'), ('/', 'PRO'), ('/', 'ELITE'),
    ('/app', 'FREE'), ('/app', 'PRO'), ('/app', 'ELITE')])
def test_home_or_app_featured_advice_obeys_plan(featured_probe, path, plan):
    probe = featured_probe
    _, body = _get(probe, _client(probe, plan), path)
    assert (probe['published_canary'] in body) == (plan == 'ELITE')


@pytest.mark.parametrize('path', ['/picks', '/api/picks', '/api/realtime/sports?scope=picks'])
@pytest.mark.parametrize('mutation', ['draft', 'unknown_tier', 'deleted'])
def test_customer_pick_surfaces_recheck_raw_after_cache_hit(featured_probe, mutation, path):
    probe = featured_probe
    client = _client(probe, 'ELITE')
    _, allowed = _get(probe, client, path)
    assert probe['published_pick'] in allowed, 'Positive control must reach real published advice'
    _revoke_pick(probe, mutation)
    _, body = _get(probe, client, path)
    assert probe['published_pick'] not in body


@pytest.mark.parametrize('plan', ['ANONYMOUS', 'FREE', 'PRO', 'ELITE'])
def test_public_realtime_advice_obeys_plan(featured_probe, plan):
    probe = featured_probe
    _, body = _get(probe, _client(probe, plan), '/api/realtime/sports?scope=picks')
    assert (probe['published_pick'] in body) == (plan == 'ELITE')


@pytest.mark.parametrize('path', ['/shark', '/shark-ai'])
def test_cached_featured_row_is_not_active_after_real_settlement(featured_probe, path):
    probe = featured_probe
    client = _client(probe, 'ELITE')
    _, allowed = _get(probe, client, path)
    assert probe['published_canary'] in allowed
    with sqlite3.connect(probe['path']) as conn:
        conn.execute('UPDATE picks SET status=?,result_status=? WHERE id=?', ('won', 'won', probe['published_pick']))
    _, body = _get(probe, client, path)
    assert probe['summary_observations'][-1] == 'hit'
    assert probe['published_canary'] not in body
