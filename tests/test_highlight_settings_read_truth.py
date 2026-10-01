"""Unmocked settings reads through all public detail aliases, offline SQLite only."""
import json
import sqlite3

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    def forbidden(*_a, **_k):
        raise AssertionError('No external calls in media/settings QA')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)


def configure(app_module, monkeypatch, path):
    monkeypatch.setattr(app_module, 'DB_PATH', str(path))
    monkeypatch.setattr(app_module, 'APP_INITIALIZED', False)
    monkeypatch.setattr(app_module, '_SEEDED_DB_PATH', '')
    def forbidden(*_a, **_k):
        raise AssertionError('Media GET must not initialize, seed or build a dashboard')
    for name in ('initialize_once', 'seed_core', 'dashboard_data'):
        monkeypatch.setattr(app_module, name, forbidden)
    return app_module.app.test_client()


def setting_db(path, value):
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE automation_state(key TEXT PRIMARY KEY, value_json TEXT, updated_at TEXT)')
        conn.execute('INSERT INTO automation_state VALUES(?,?,?)',
            ('admin_control.settings.highlights_enabled', value, '2026-10-01T00:00:00Z'))


@pytest.mark.parametrize('prefix', ['/highlight/', '/resumen/', '/resumenes/'])
@pytest.mark.parametrize('role', [None, 'PRO'])
@pytest.mark.parametrize('storage', ['absent', 'corrupt', 'invalid_setting'])
def test_unreadable_settings_never_claim_admin_paused(app_module, monkeypatch, tmp_path, prefix, role, storage):
    path = tmp_path / 'media.sqlite'
    if storage == 'corrupt':
        path.write_bytes(b'NOT SQLITE')
    elif storage == 'invalid_setting':
        setting_db(path, '{invalid-json')
    before = path.read_bytes() if path.exists() else None
    client = configure(app_module, monkeypatch, path)
    if role:
        with client.session_transaction() as session:
            session.update(user_id='synthetic', user_role=role, membership=role)
    response = client.get(prefix + 'synthetic')
    assert response.status_code == 503
    html = response.get_data(as_text=True)
    assert 'No se pudo comprobar' in html
    assert 'La sección de resúmenes está temporalmente pausada' not in html
    assert '<iframe' not in html
    assert (path.read_bytes() if path.exists() else None) == before


@pytest.mark.parametrize('prefix', ['/highlight/', '/resumen/', '/resumenes/'])
@pytest.mark.parametrize('enabled,expected', [(False, 200), (True, 404)])
def test_real_settings_distinguish_pause_from_missing_resource(app_module, monkeypatch, tmp_path, prefix, enabled, expected):
    path = tmp_path / 'media.sqlite'
    setting_db(path, json.dumps({'revision':1, 'value':enabled}))
    before = path.read_bytes()
    client = configure(app_module, monkeypatch, path)
    response = client.get(prefix + 'synthetic')
    assert response.status_code == expected
    assert path.read_bytes() == before
    assert '<iframe' not in response.get_data(as_text=True)


def test_settings_cached_once_per_request_with_read_state(app_module, monkeypatch, tmp_path):
    from blueprints import admin_master_control as master
    path = tmp_path / 'media.sqlite'
    setting_db(path, json.dumps({'revision':1, 'value':True}))
    configure(app_module, monkeypatch, path)
    original = master._settings_snapshot
    calls = []
    def counted(a):
        calls.append(1)
        return original(a)
    monkeypatch.setattr(master, '_settings_snapshot', counted)
    with app_module.app.test_request_context('/highlight/synthetic'):
        first = app_module.admin_operational_settings()
        assert first['settings_readable'] is True
        assert app_module.admin_operational_settings() is first
        assert calls == [1]


def test_values_only_legacy_contract_remains_unchanged(tmp_path):
    from blueprints.admin_master_control import settings_values
    from types import SimpleNamespace
    a = SimpleNamespace(DB_PATH=str(tmp_path/'absent.sqlite'), APP_VERSION='QA')
    assert settings_values(a) == {'highlights_enabled':True, 'banner_enabled':False, 'banner_text':''}
