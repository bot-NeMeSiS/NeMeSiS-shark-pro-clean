import pytest


@pytest.mark.parametrize('route', ['/admin/matches', '/admin/matches-sync'])
def test_admin_matches_reads_compact_context_without_legacy_dashboard(app_module, monkeypatch, route):
    def forbidden(*args, **kwargs):
        pytest.fail('Admin match diagnostics must not build the legacy full dashboard or call a provider')

    monkeypatch.setattr(app_module, 'dashboard_data', forbidden)
    for name in ('sync_sportsdb_feed', 'sync_odds_events', 'sync_sportsdb_crests'):
        monkeypatch.setattr(app_module, name, forbidden)
    with app_module.app.test_client() as client:
        with client.session_transaction() as session:
            session.update(user_id='isolated-admin', user_role='ADMIN', membership='ADMIN')
        response = client.get(route)
    assert response.status_code == 200
    assert b'data-v933-template="admin_matches_sync"' in response.data
    assert b'name="csrf_token"' in response.data


def test_admin_matches_remains_protected(app_module):
    response = app_module.app.test_client().get('/admin/matches')
    assert response.status_code == 302
    assert '/admin-login' in response.headers['Location']
