"""Read-only Founder entry and existing operational journey. Temporary SQLite only."""
import sqlite3
from datetime import datetime, timedelta, timezone
import pytest
from engines import founder_os_engine as founder
from test_admin_operations_workbench import admin_post_client, sample


def seeded_database(tmp_path):
    path = tmp_path / 'founder.sqlite'
    founder.ensure_founder_os_schema(path)
    with sqlite3.connect(path) as conn:
        conn.execute("INSERT INTO founder_alerts(id,fingerprint,source,category,status,title,message,last_seen_at) VALUES (?,?,?,?,?,?,?,?)",
                     ('qa-alert','qa-fp','generated','SPORTS_DATA','OPEN','QA','Evidence', '2026-09-23T08:00:00Z'))
    return path


def dump(path):
    with sqlite3.connect(path) as conn:
        return '\n'.join(conn.iterdump())


def business_state(path):
    with sqlite3.connect(path) as conn:
        return {table:conn.execute('SELECT * FROM ' + table).fetchall() for table in
                ('founder_alerts', 'founder_obligations', 'founder_push_subscriptions')}


def initialize_test_app(app_module, monkeypatch):
    # Complete normal bootstrap before measuring a read against an initialized app.
    monkeypatch.setattr(app_module, '_SEEDED_DB_PATH', None)
    monkeypatch.setattr(app_module, 'APP_INITIALIZED', False)
    app_module.initialize_once()


def test_read_only_snapshot_never_syncs_resolves_or_creates(tmp_path, monkeypatch):
    path = seeded_database(tmp_path)
    before = dump(path)
    monkeypatch.setattr(founder, 'sync_generated_alerts', lambda *a, **k: pytest.fail('GET synchronized alerts'))
    monkeypatch.setattr(founder, 'ensure_founder_os_schema', lambda *a: pytest.fail('GET wrote schema'))
    first = founder.founder_os_snapshot(path, read_only=True)
    second = founder.founder_os_snapshot(path, read_only=True)
    assert first['available'] and second['available']
    assert first['alerts']['items'][0]['status'] == 'OPEN'
    assert first['alerts']['items'][0]['panel_url'] == '/admin/data-center'
    assert dump(path) == before


@pytest.mark.parametrize('kind', ['missing', 'schema_missing', 'schema_broken'])
def test_unavailable_is_not_zero_or_healthy(tmp_path, kind):
    path = tmp_path / 'missing.sqlite'
    if kind != 'missing':
        with sqlite3.connect(path) as conn:
            conn.execute('CREATE TABLE marker (value TEXT)')
        if kind == 'schema_broken':
            founder.ensure_founder_os_schema(path)
            with sqlite3.connect(path) as conn:
                conn.execute('ALTER TABLE founder_alerts RENAME TO broken_alerts')
    result = founder.founder_os_snapshot(path, read_only=True)
    assert result['available'] is False and result['health_state'] == 'UNAVAILABLE'
    assert 'open' not in result['alerts']
    if kind == 'missing': assert not path.exists()


def test_confirmed_empty_is_not_continuous_supervision(tmp_path):
    path = tmp_path / 'empty.sqlite'
    founder.ensure_founder_os_schema(path)
    result = founder.founder_os_snapshot(path, read_only=True)
    assert result['alerts']['open'] == 0
    assert result['health_state'] == 'NO_OPEN_ALERTS'


def test_existing_explicit_tick_generates_updates_deduplicates_and_preserves_ack(tmp_path, monkeypatch):
    path = tmp_path / 'tick.sqlite'
    monkeypatch.delenv('FOUNDER_PUSH_ENABLED', raising=False)
    due = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    saved = founder.save_obligation(path, {'label':'QA obligation', 'amount':10, 'due_date':due})
    oid = saved['obligation']['id']
    before = founder.alerts_snapshot(path, read_only=True)
    assert before['items'] == []
    founder.founder_os_snapshot(path, read_only=True)
    assert founder.alerts_snapshot(path, read_only=True)['items'] == []
    assert founder.founder_alert_tick(path)['status'] == 'NOT_CONFIGURED'
    first = founder.alerts_snapshot(path, read_only=True)['items']
    billing = next(item for item in first if item['entity_ref'] == oid)
    assert billing['status'] == 'OPEN' and '10.00' in billing['message']
    assert founder.acknowledge_alert(path, billing['id'])['acknowledged']
    founder.save_obligation(path, {'id':oid, 'label':'QA obligation', 'amount':20, 'due_date':due})
    monkeypatch.setattr(founder, 'utc_now', lambda:'2026-09-24T12:00:00+00:00')
    founder.founder_alert_tick(path)
    second = founder.alerts_snapshot(path, read_only=True)['items']
    assert {i['id'] for i in first} == {i['id'] for i in second}
    updated = next(item for item in second if item['id'] == billing['id'])
    assert updated['status'] == 'ACK' and '20.00' in updated['message']
    assert updated['last_seen_at'] == '2026-09-24T12:00:00+00:00'
    frozen = dump(path)
    founder.founder_os_snapshot(path, read_only=True)
    founder.founder_os_snapshot(path, read_only=True)
    assert dump(path) == frozen


def test_existing_notification_repeat_window_is_preserved_without_delivery(tmp_path, monkeypatch):
    path = tmp_path / 'repeat.sqlite'
    due = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    founder.save_obligation(path, {'label':'QA repeat', 'due_date':due})
    monkeypatch.setenv('FOUNDER_PUSH_REPEAT_MINUTES', '60')
    monkeypatch.setattr(founder, 'push_configuration', lambda:{'configured':True})
    sends = []
    def isolated_delivery(_path, payload):
        sends.append(payload['tag'])
        return {'sent':1, 'failed':0}
    monkeypatch.setattr(founder, '_send_push', isolated_delivery)
    assert founder.dispatch_pending_founder_push(path)['sent'] > 0
    assert founder.dispatch_pending_founder_push(path)['sent'] == 0
    prior = len(sends)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE founder_alerts SET last_notified_at=? WHERE severity='CRITICAL'",
                     ((datetime.now(timezone.utc)-timedelta(minutes=61)).isoformat(),))
    assert founder.dispatch_pending_founder_push(path)['sent'] == 1
    assert len(sends) == prior + 1


def test_existing_manifests_worker_and_private_cache_contract(app_module):
    client, _ = admin_post_client(app_module)
    for path, identity in [('/founder-manifest.json','/admin/founder-os'),('/manifest.json','/')]:
        manifest = client.get(path).get_json()
        assert manifest['id'] == identity and manifest['scope'] == '/'
    worker = client.get('/service-worker.js')
    script = worker.get_data(as_text=True)
    assert worker.headers['Service-Worker-Allowed'] == '/'
    assert "fetch(req,{cache:'no-store'})" in script
    assert 'caches.put' not in script and 'cache.put' not in script and 'caches.match' not in script
    assert 'no-store' in client.get('/api/admin/founder-os').headers.get('Cache-Control', '')


def test_untrusted_evidence_cannot_become_action_target(tmp_path):
    path = seeded_database(tmp_path)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE founder_alerts SET category=?,entity_ref=?,payload_json=?",
                     ('https://evil.invalid', 'javascript:alert(1)', '{"url":"https://evil.invalid"}'))
    item = founder.alerts_snapshot(path, read_only=True)['items'][0]
    assert item['panel_url'] == '/admin/operations-center'


@pytest.mark.parametrize('path', ['/admin/founder-os', '/api/admin/founder-os'])
def test_flask_founder_queries_preserve_persisted_state(app_module, tmp_path, monkeypatch, path):
    db = seeded_database(tmp_path)
    monkeypatch.setattr(app_module, 'DB_PATH', str(db))
    monkeypatch.setattr(app_module, 'dashboard_data', lambda: {})
    initialize_test_app(app_module, monkeypatch)
    before = dump(db)
    client, _ = admin_post_client(app_module)
    response = client.get(path)
    assert response.status_code == 200
    assert dump(db) == before


@pytest.mark.parametrize('role', [None, 'CLIENT'])
def test_visitors_and_clients_cannot_read_founder_or_ack(app_module, role):
    client, headers = admin_post_client(app_module, role)
    assert client.get('/admin/founder-os').status_code == 302
    assert client.get('/api/admin/founder-os').status_code == 403
    assert client.post('/admin/founder-os/alerts/qa-alert/ack', headers=headers).status_code == 302


def test_ack_needs_csrf_and_never_claims_unknown_id_success(app_module, tmp_path, monkeypatch):
    db = seeded_database(tmp_path)
    monkeypatch.setattr(app_module, 'DB_PATH', str(db))
    monkeypatch.setattr(app_module, 'dashboard_data', lambda: {})
    initialize_test_app(app_module, monkeypatch)
    client, headers = admin_post_client(app_module)
    before = business_state(db)
    assert client.post('/admin/founder-os/alerts/qa-alert/ack', headers={'X-CSRF-Token':'invalid'}).status_code == 403
    assert business_state(db) == before
    # A rejected CSRF may create the normal security audit event, not a business change.
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM security_events').fetchone()[0] > 0
    assert client.post('/admin/founder-os/alerts/absent/ack', headers=headers).status_code == 409
    assert business_state(db) == before
    assert client.post('/admin/founder-os/alerts/qa-alert/ack', headers=headers).status_code == 302
    row = founder.alerts_snapshot(db, read_only=True)['items'][0]
    assert row['status'] == 'ACK'  # Acknowledgement is not resolution.


def test_api_failure_and_html_do_not_claim_zero(app_module, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, 'DB_PATH', str(tmp_path / 'absent.sqlite'))
    monkeypatch.setattr(app_module, 'dashboard_data', lambda: {})
    client, _ = admin_post_client(app_module)
    assert client.get('/api/admin/founder-os').status_code == 503
    html = client.get('/admin/founder-os').get_data(as_text=True)
    assert 'No equivale a cero incidencias' in html
    assert '0 alertas abiertas' not in html


def test_operations_keeps_founder_identity_without_changing_client_pwa(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'v938_operations_snapshot', sample)
    client, _ = admin_post_client(app_module)
    html = client.get('/admin/operations-center').get_data(as_text=True)
    assert 'href="/founder-manifest.json"' in html
    assert 'href="/admin/founder-os"' in html
    manifest = client.get('/founder-manifest.json').get_json()
    assert manifest['id'] == manifest['start_url'] == '/admin/founder-os'
    assert client.get('/manifest.json').get_json()['id'] != manifest['id']
