"""Login handlers and guards on disposable SQLite; transports stay disabled."""

from datetime import datetime
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie
import sqlite3

import pytest


CSRF = "qa-session-login-csrf"
ALIASES = ["/cliente-login", "/login", "/entrar", "/admin-login"]


@pytest.fixture
def login_store(app_module, tmp_path, monkeypatch):
    path = tmp_path / "login-http.sqlite3"
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", str(path))
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(app_module, "APP_INITIALIZED", True)
    monkeypatch.setattr(app_module, "seed_core", lambda: None)
    monkeypatch.setattr(app_module, "_request_rejection_audit_events", {})
    monkeypatch.setattr(app_module, "render_template", lambda *_a, **_kw: "local login form")
    monkeypatch.setattr(app_module, "auth_shell_data", lambda **_kw: {})
    with app_module.sqlite_connect(path) as conn:
        conn.execute("""CREATE TABLE users(
            id TEXT PRIMARY KEY,name TEXT,username TEXT,email TEXT,password_hash TEXT,
            auth_version INTEGER NOT NULL DEFAULT 0,role TEXT,membership TEXT,
            membership_source TEXT,membership_started_at TEXT,membership_expires_at TEXT,
            membership_note TEXT,membership_updated_at TEXT,membership_updated_by TEXT,
            membership_admin_granted INTEGER DEFAULT 0,created_at TEXT,last_login TEXT
        )""")
        conn.execute("""CREATE TABLE revoked_auth_sessions(
            session_id_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,
            revoked_at TEXT NOT NULL,expires_at TEXT NOT NULL
        )""")
        conn.execute("""INSERT INTO users(id,name,username,email,password_hash,role,membership,created_at)
            VALUES(?,?,?,?,?,?,?,?)""", (
            "qa-login", "QA Account", "qa-session", "qa-session@example.invalid",
            app_module.generate_password_hash("qa-valid-password"), "ADMIN", "ADMIN", app_module.now_iso(),
        ))
    return path


def _client(app_module):
    client = app_module.app.test_client()
    with client.session_transaction() as state:
        state["csrf_token"] = CSRF
        state["nemesis_local_access"] = True
    return client


def _form(**overrides):
    result = {"csrf_token": CSRF, "login": "qa-session", "password": "qa-valid-password", "remember_device": "1"}
    result.update(overrides)
    return result


def _counts(path):
    with sqlite3.connect(path) as conn:
        pending = conn.execute("SELECT COUNT(*) FROM security_action_attempts WHERE scope='auth_login'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM security_events WHERE event_type='login_attempt' AND success=0").fetchone()[0]
        passed = conn.execute("SELECT COUNT(*) FROM security_events WHERE event_type='login_attempt' AND success=1").fetchone()[0]
    return pending, failed, passed


@pytest.mark.parametrize("route", ALIASES)
def test_login_store_failure_blocks_before_password_verification(app_module, login_store, monkeypatch, route):
    calls = []
    monkeypatch.setattr(app_module, "claim_login_attempt", lambda *_a, **_kw: {"allowed": False, "reason": "rate_limit_store_unavailable"})
    monkeypatch.setattr(app_module, "authenticate_user", lambda *_a, **_kw: calls.append("user"))
    monkeypatch.setattr(app_module, "authenticate_env_admin", lambda *_a, **_kw: calls.append("admin"))
    response = _client(app_module).post(route, data=_form())
    assert response.status_code == 503
    assert calls == []


@pytest.mark.parametrize("route", ALIASES)
def test_successful_real_password_releases_reservation_and_sets_bounded_cookie(app_module, login_store, route):
    client = _client(app_module)
    response = client.post(route, data=_form())
    assert response.status_code == 302
    assert _counts(login_store) == (0, 0, 1)
    cookies = SimpleCookie()
    cookies.load(response.headers["Set-Cookie"])
    with client.session_transaction() as state:
        assert state["user_id"] == "qa-login"
        assert state.permanent is True
        assert parsedate_to_datetime(cookies["session"]["expires"]) == datetime.fromisoformat(state["auth_session_expires_at"])


def test_all_aliases_share_eight_failures_without_double_audit(app_module, login_store):
    client = _client(app_module)
    for index in range(8):
        response = client.post(ALIASES[index % len(ALIASES)], data=_form(password="qa-invalid-password"))
        assert response.status_code == 200
    assert _counts(login_store) == (0, 8, 0)
    assert client.post("/login", data=_form()).status_code == 429
    assert _counts(login_store) == (0, 8, 0)


@pytest.mark.parametrize("route", ALIASES)
def test_invalid_csrf_cannot_consume_login_capacity(app_module, login_store, monkeypatch, route):
    calls = []
    monkeypatch.setattr(app_module, "claim_login_attempt", lambda *_a, **_kw: calls.append("claimed"))
    response = _client(app_module).post(route, data=_form(csrf_token="bad-token"))
    assert response.status_code == 403
    assert calls == []


@pytest.mark.parametrize("route", ["/login", "/admin-login"])
def test_unconfirmed_finalization_does_not_issue_authenticated_session(app_module, login_store, monkeypatch, route):
    monkeypatch.setattr(app_module, "finalize_login_attempt", lambda *_a, **_kw: False)
    client = _client(app_module)
    response = client.post(route, data=_form())
    assert response.status_code == 503
    with client.session_transaction() as state:
        assert "user_id" not in state
    assert _counts(login_store) == (1, 0, 0)


def test_browser_session_opt_out_and_logged_in_post_release_their_claim(app_module, login_store):
    client = _client(app_module)
    response = client.post("/login", data=_form(remember_device="0"))
    assert response.status_code == 302
    cookies = SimpleCookie()
    cookies.load(response.headers["Set-Cookie"])
    assert not cookies["session"]["expires"]
    with client.session_transaction() as state:
        state["csrf_token"] = CSRF
        state["nemesis_local_access"] = True
        identity = state["auth_session_id"]
    response = client.post("/login", data=_form())
    assert response.status_code == 302
    assert _counts(login_store) == (0, 0, 2)
    with client.session_transaction() as state:
        assert state["auth_session_id"] == identity


@pytest.mark.parametrize("route", ALIASES)
@pytest.mark.parametrize("operation", ["PUT", "PATCH", "DELETE", "child_post"])
def test_requests_without_a_login_handler_preserve_the_login_budget(
    app_module, login_store, monkeypatch, route, operation,
):
    client = _client(app_module)
    verifications = []
    original = app_module.authenticate_user

    def verify(*args, **kwargs):
        verifications.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(app_module, "authenticate_user", verify)
    path = route + "/not-a-login-route" if operation == "child_post" else route
    method = "POST" if operation == "child_post" else operation
    expected = 404 if operation == "child_post" else 405
    for _ in range(8):
        response = client.open(path, method=method, data=_form())
        assert response.status_code == expected
    assert verifications == []

    response = client.post("/login", data=_form())
    assert response.status_code == 302
    assert verifications == [True]
    assert _counts(login_store) == (0, 0, 1)


def test_registration_without_remember_option_keeps_browser_cookie(app_module, login_store, monkeypatch):
    monkeypatch.setattr(app_module, "_growth_record_registration_journey", lambda *_a, **_kw: None)
    client = _client(app_module)
    response = client.post("/registro", data={
        "name": "Registration QA", "username": "qa-registration",
        "email": "qa-registration@example.invalid",
        "password": "qa-registration-password", "csrf_token": CSRF,
    })
    assert response.status_code == 302
    user = app_module.get_user_by_username("qa-registration")
    assert user is not None
    jar = SimpleCookie()
    jar.load(response.headers["Set-Cookie"])
    assert not jar["session"]["expires"]
    assert not jar["session"]["max-age"]
    with client.session_transaction() as state:
        assert state["user_id"] == user["id"]
        assert state.permanent is False
        assert state["auth_session_id"]
        assert state["auth_session_expires_at"]
