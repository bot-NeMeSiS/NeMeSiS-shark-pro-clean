import hashlib
import sqlite3
from unittest.mock import patch

import pytest


ROUTES = ['/admin/telegram-audit', '/admin/retention-center']


@pytest.fixture
def admin_db(app_module, tmp_path, monkeypatch):
    path = tmp_path / 'admin-render.sqlite'
    monkeypatch.setattr(app_module, 'DB_PATH', str(path))
    monkeypatch.setattr(app_module, '_SEEDED_DB_PATH', None)
    monkeypatch.setattr(app_module, '_SEEDING_DB_PATH', None)
    monkeypatch.setattr(app_module, 'APP_INITIALIZED', True)
    app_module.seed_core()
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session.update(user_id='admin-render-qa', user_role='ADMIN', membership='ADMIN', user_membership='ADMIN')
    return client, path


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('scenario', ['populated', 'empty', 'partial', 'source_error'])
def test_admin_panels_render_honest_readonly_context(app_module, admin_db, monkeypatch, route, scenario):
    client, path = admin_db
    with sqlite3.connect(path) as conn:
        conn.execute('DELETE FROM picks')
        if scenario in ('populated', 'partial'):
            for i in range(3):
                conn.execute('INSERT INTO picks(id,status) VALUES(?,?)', (f'qa-pick-{i}', 'published'))
        if scenario == 'partial':
            conn.execute('DROP TABLE ' + ('telegram_settings' if 'telegram-audit' in route else 'favorites'))
    original = app_module.rows
    queries = []
    def read(query, params=()):
        queries.append(query)
        if scenario == 'source_error' and 'COUNT(*)' in query:
            raise sqlite3.OperationalError('QA_PRIVATE_ERROR_DO_NOT_RENDER')
        return original(query, params)
    monkeypatch.setattr(app_module, 'rows', read)
    def forbidden(*args, **kwargs):
        pytest.fail('Render must not build dashboard, initialize settings, or run diagnostics with writes')
    monkeypatch.setattr(app_module, 'dashboard_data', forbidden)
    monkeypatch.setattr(app_module, 'telegram_diagnostics_safe', forbidden)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    response = client.get(route)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert ('Flujo picks a Telegram' if 'telegram-audit' in route else 'Centro de retención') in text
    assert 'QA_PRIVATE_ERROR_DO_NOT_RENDER' not in text
    assert 'Traceback' not in text and 'UndefinedError' not in text
    assert '/admin/picks' in text and '/admin/telegram' in text
    if scenario == 'source_error':
        assert 'No se pudo consultar' in text
        assert 'Sin incidencias' not in text
    elif scenario == 'populated':
        assert 'data-admin-metric="published_picks">3<' in text
    elif scenario == 'empty':
        assert 'data-admin-metric="published_picks">0<' in text
    if scenario == 'partial':
        assert 'No disponible' in text
        assert 'No se pudo consultar' in text
        missing = 'telegram_settings' if 'telegram-audit' in route else 'favorites'
        with sqlite3.connect(path) as conn:
            assert conn.execute("SELECT name FROM sqlite_master WHERE name=?", (missing,)).fetchone() is None
    assert all(q.lstrip().upper().startswith(('SELECT', 'PRAGMA')) for q in queries)


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('role', [None, 'PRO'])
def test_admin_panels_preserve_auth_boundary(app_module, admin_db, route, role):
    client, _ = admin_db
    with client.session_transaction() as session:
        session.clear()
        if role:
            session.update(user_id='client-render-qa', user_role=role, membership=role)
    with patch.object(app_module, 'dashboard_data', side_effect=AssertionError('unauthorized data read')):
        response = client.get(route)
    assert response.status_code in (302, 303)
    assert '/admin-login' in response.location


@pytest.mark.parametrize('route', ROUTES)
def test_admin_panels_do_not_hide_programming_errors(app_module, admin_db, monkeypatch, route):
    client, _ = admin_db
    original = app_module.rows
    def broken(query, params=()):
        if 'COUNT(*)' in query:
            raise TypeError('controlled implementation defect')
        return original(query, params)
    monkeypatch.setattr(app_module, 'rows', broken)
    with pytest.raises(TypeError, match='controlled implementation defect'):
        client.get(route)


def test_telegram_audit_does_not_expose_message_payload(app_module, admin_db):
    client, path = admin_db
    private_marker = 'QA_PRIVATE_MESSAGE_NOT_FOR_DISPLAY'
    with sqlite3.connect(path) as conn:
        conn.execute('INSERT INTO telegram_logs(id,event_type,status,message,payload_json,created_at) VALUES(?,?,?,?,?,?)',
                     ('qa-private-log', 'picks', 'failed', private_marker, private_marker, '2026-09-07T12:00:00+00:00'))
    response = client.get('/admin/telegram-audit')
    assert response.status_code == 200
    assert private_marker not in response.get_data(as_text=True)
    assert 'Evento de Telegram' in response.get_data(as_text=True)


def test_telegram_audit_uses_persisted_counts_without_delivery(app_module, admin_db):
    from flask import template_rendered
    client, path = admin_db
    with sqlite3.connect(path) as conn:
        conn.execute('DELETE FROM telegram_queue')
        conn.execute('DELETE FROM telegram_subscribers')
        for index, status in enumerate(('PENDING', 'sent', 'FAILED')):
            conn.execute('INSERT INTO telegram_queue(id,message_type,status,sent_at,created_at) VALUES(?,?,?,?,?)',
                         (f'qa-count-{index}', 'daily_picks', status, '2026-09-07T12:00:00+00:00' if status == 'sent' else None, '2026-09-07T11:00:00+00:00'))
        conn.execute('INSERT INTO telegram_queue(id,message_type,status) VALUES(?,?,?)', ('qa-non-pick','system_test','pending'))
        conn.execute('INSERT INTO telegram_subscribers(id,is_active,membership) VALUES(?,?,?)', ('qa-pro',1,'PRO'))
        conn.execute('INSERT INTO telegram_subscribers(id,is_active,membership) VALUES(?,?,?)', ('qa-inactive',0,'PRO'))
    contexts = []
    def capture(sender, template, context, **extra):
        contexts.append(context)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    template_rendered.connect(capture, app_module.app, weak=False)
    try:
        response = client.get('/admin/telegram-audit')
    finally:
        template_rendered.disconnect(capture, app_module.app)
    assert response.status_code == 200
    audit = contexts[-1]['audit']
    assert [audit['counts'][key] for key in ('pick_queue_pending','pick_queue_sent','pick_queue_failed','subscribers_active','subscribers_pro')] == [1,1,1,1,1]
    assert audit['counts']['sendable_picks'] is None
    assert audit['last_sent'][0]['sent_at'] == '2026-09-07T12:00:00+00:00'
    assert len(audit['pick_queue']) == 3
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
