"""Session revocation contracts using isolated SQLite and no external services."""

import pytest


def _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-admin-v942"):
    path = tmp_path / "session-revocation.sqlite3"
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", str(path))
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(app_module, "APP_INITIALIZED", True)
    conn = app_module.sqlite_connect(path)
    conn.execute(
        """CREATE TABLE users(
            id TEXT PRIMARY KEY, name TEXT, username TEXT, email TEXT,
            password_hash TEXT, auth_version INTEGER NOT NULL DEFAULT 0,
            role TEXT DEFAULT 'FREE', membership TEXT DEFAULT 'FREE',
            membership_source TEXT, membership_started_at TEXT, membership_expires_at TEXT,
            membership_note TEXT, membership_updated_at TEXT, membership_updated_by TEXT,
            membership_admin_granted INTEGER DEFAULT 0, created_at TEXT, last_login TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE revoked_auth_sessions(
            session_id_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
            revoked_at TEXT NOT NULL, expires_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """INSERT INTO users(id,name,username,email,password_hash,auth_version,role,membership,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (user_id, "QA Owner", "qa-owner", "qa-owner@example.invalid", app_module.generate_password_hash("qa-password"), 0, "ADMIN", "ADMIN", app_module.now_iso()),
    )
    conn.commit()
    conn.close()
    return app_module.get_user_by_id(user_id)


def _sign_in_cookie(client, user, app_module):
    with app_module.app.test_request_context("/"):
        app_module.set_login_session(user)
        from flask import session

        login_state = dict(session)
    with client.session_transaction() as state:
        state.clear()
        state.update(login_state)
        state["csrf_token"] = "qa-csrf-v942"


def _copy_signed_session(source, target, app_module):
    cookie = source.get_cookie(app_module.app.config.get("SESSION_COOKIE_NAME", "session"))
    assert cookie is not None
    target.set_cookie(app_module.app.config.get("SESSION_COOKIE_NAME", "session"), cookie.value)


def test_schema_migration_adds_auth_version_to_legacy_users(app_module, tmp_path):
    path = tmp_path / "legacy-users.sqlite3"
    conn = app_module.sqlite_connect(path)
    conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY, username TEXT, email TEXT)")
    conn.execute("INSERT INTO users(id,username,email) VALUES('legacy-1','legacy','legacy@example.invalid')")
    app_module.run_schema_migrations(conn)
    columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    stored = conn.execute("SELECT auth_version FROM users WHERE id='legacy-1'").fetchone()["auth_version"]
    session_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='revoked_auth_sessions'"
    ).fetchone()
    conn.close()
    assert columns["auth_version"]["notnull"] == 1
    assert stored == 0
    assert session_table


def test_password_reset_revokes_existing_client_session(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-client-v942")
    conn = app_module.db()
    conn.execute("UPDATE users SET role='PRO',membership='PRO' WHERE id=?", (user["id"],))
    conn.commit()
    conn.close()
    user = app_module.get_user_by_id(user["id"])
    client = app_module.app.test_client()
    _sign_in_cookie(client, user, app_module)

    with client.session_transaction() as state:
        assert state["auth_version"] == 0
    app_module.reset_user_password(user["id"], "replacement-password")
    with client.session_transaction() as state:
        state_data = dict(state)
    with app_module.app.test_request_context("/app"):
        from flask import session

        session.update(state_data)
        assert app_module.current_session_user() is None
        assert "user_id" not in session


def test_admin_role_demotion_revokes_previously_issued_cookie(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch)
    client = app_module.app.test_client()
    _sign_in_cookie(client, user, app_module)
    assert client.get("/api/admin/route-map").status_code == 200

    conn = app_module.db()
    conn.execute(
        "UPDATE users SET role='PRO', membership='PRO', auth_version=COALESCE(auth_version,0)+1 WHERE id=?",
        (user["id"],),
    )
    conn.commit()
    conn.close()
    response = client.get("/api/admin/route-map")

    assert response.status_code == 403
    with client.session_transaction() as state:
        assert "user_id" not in state


def test_deleted_admin_account_cannot_reuse_signed_cookie(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-admin-deleted-v942")
    client = app_module.app.test_client()
    _sign_in_cookie(client, user, app_module)
    conn = app_module.db()
    conn.execute("DELETE FROM users WHERE id=?", (user["id"],))
    conn.commit()
    conn.close()

    response = client.get("/api/admin/route-map")

    assert response.status_code == 403
    with client.session_transaction() as state:
        assert "user_id" not in state


@pytest.mark.parametrize(
    ("logout_path", "redirect_path"),
    (("/logout", "/"), ("/admin/logout", "/admin-login")),
)
def test_logout_revokes_only_the_copied_signed_session(
    app_module, tmp_path, monkeypatch, logout_path, redirect_path
):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id=f"qa-logout-{logout_path.strip('/').replace('/', '-')}")
    browser = app_module.app.test_client()
    copied = app_module.app.test_client()
    unrelated = app_module.app.test_client()
    _sign_in_cookie(browser, user, app_module)
    with browser.session_transaction() as state:
        raw_session_id = state["auth_session_id"]
    _copy_signed_session(browser, copied, app_module)
    _sign_in_cookie(unrelated, user, app_module)

    assert copied.get("/api/admin/route-map").status_code == 200
    assert unrelated.get("/api/admin/route-map").status_code == 200
    confirmation = browser.get(logout_path, headers={"Sec-Fetch-Site": "cross-site"})
    assert confirmation.status_code == 200
    assert b' name="csrf_token"' in confirmation.data
    assert copied.get("/api/admin/route-map").status_code == 200
    assert browser.post(logout_path, data={}).status_code == 403
    assert copied.get("/api/admin/route-map").status_code == 200

    response = browser.post(logout_path, data={"csrf_token": "qa-csrf-v942"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith(redirect_path)

    replay = copied.get("/api/admin/route-map")
    assert replay.status_code == 403
    with copied.session_transaction() as state:
        assert "user_id" not in state
    assert unrelated.get("/api/admin/route-map").status_code == 200
    assert app_module.get_user_by_id(user["id"])["auth_version"] == user["auth_version"]
    conn = app_module.db()
    revoked = conn.execute(
        "SELECT session_id_hash,user_id FROM revoked_auth_sessions WHERE user_id=?",
        (user["id"],),
    ).fetchall()
    conn.close()
    assert len(revoked) == 1
    assert revoked[0]["session_id_hash"] == app_module.hashlib.sha256(raw_session_id.encode("utf-8")).hexdigest()
    assert raw_session_id not in revoked[0]["session_id_hash"]


def test_stale_signed_cookie_cannot_revoke_a_newer_session(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-stale-logout-cookie")
    stale = app_module.app.test_client()
    _sign_in_cookie(stale, user, app_module)
    current = app_module.app.test_client()
    conn = app_module.db()
    conn.execute("UPDATE users SET auth_version=auth_version+1 WHERE id=?", (user["id"],))
    conn.commit()
    conn.close()
    updated_user = app_module.get_user_by_id(user["id"])
    _sign_in_cookie(current, updated_user, app_module)

    response = stale.get("/logout")

    assert response.status_code == 200
    assert current.get("/api/admin/route-map").status_code == 200
    assert app_module.get_user_by_id(user["id"])["auth_version"] == updated_user["auth_version"]


def test_current_user_id_rejects_a_revoked_session(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-revoked-current-user-id")
    client = app_module.app.test_client()
    _sign_in_cookie(client, user, app_module)
    with client.session_transaction() as state:
        session_state = dict(state)
    session_hash = app_module.hashlib.sha256(
        session_state["auth_session_id"].encode("utf-8")
    ).hexdigest()
    conn = app_module.db()
    conn.execute(
        """INSERT INTO revoked_auth_sessions
           (session_id_hash,user_id,revoked_at,expires_at) VALUES (?,?,?,?)""",
        (session_hash, user["id"], app_module.now_iso(), session_state["auth_session_expires_at"]),
    )
    conn.commit()
    conn.close()

    with app_module.app.test_request_context("/private-data"):
        from flask import session

        session.update(session_state)
        assert app_module.current_user_id() == ""
        assert "user_id" not in session


def test_legacy_cookie_is_expired_at_rollout_without_revoking_new_sessions(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-legacy-logout-cookie")
    browser = app_module.app.test_client()
    copied = app_module.app.test_client()
    _sign_in_cookie(browser, user, app_module)
    with browser.session_transaction() as state:
        state.pop("auth_session_id", None)
        state.pop("auth_session_expires_at", None)
    _copy_signed_session(browser, copied, app_module)
    current = app_module.app.test_client()
    _sign_in_cookie(current, user, app_module)

    monkeypatch.setitem(app_module.app.config, "TESTING", False)
    assert copied.get("/api/admin/route-map").status_code == 403
    assert browser.get("/logout").status_code == 200
    assert current.get("/api/admin/route-map").status_code == 200
    assert app_module.get_user_by_id(user["id"])["auth_version"] == user["auth_version"]


@pytest.mark.parametrize("expiry_value", ("invalid timestamp", "2000-01-01T00:00:00+00:00"))
def test_expired_or_malformed_session_is_rejected_and_cleared(
    app_module, tmp_path, monkeypatch, expiry_value
):
    user = _isolated_admin(
        app_module,
        tmp_path,
        monkeypatch,
        user_id=f"qa-expired-session-{expiry_value[:4].replace(' ', '-')}",
    )
    client = app_module.app.test_client()
    _sign_in_cookie(client, user, app_module)
    with client.session_transaction() as state:
        state["auth_session_expires_at"] = expiry_value

    assert client.get("/api/admin/route-map").status_code == 403
    with client.session_transaction() as state:
        assert "user_id" not in state


def test_logout_does_not_claim_revocation_when_database_write_fails(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-logout-db-failure")
    client = app_module.app.test_client()
    _sign_in_cookie(client, user, app_module)
    monkeypatch.setattr(app_module, "_revoke_session_for_logout", lambda _user_id: False)

    response = client.post("/logout", data={"csrf_token": "qa-csrf-v942"})

    assert response.status_code == 503
    assert b"No se pudo confirmar la revocaci" in response.data
    with client.session_transaction() as state:
        assert "user_id" not in state


def test_revocation_store_unavailable_fails_closed_for_protected_routes(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-revocation-read-failure")
    client = app_module.app.test_client()
    _sign_in_cookie(client, user, app_module)
    original_one = app_module.one

    def fail_revocation_read(sql, params=()):
        if "revoked_auth_sessions" in str(sql):
            raise RuntimeError("revocation store unavailable")
        return original_one(sql, params)

    monkeypatch.setattr(app_module, "one", fail_revocation_read)

    assert client.get("/api/admin/route-map").status_code == 403


def test_revocation_helper_fails_closed_when_database_is_unavailable(app_module, monkeypatch, capsys):
    monkeypatch.setattr(app_module, "db", lambda: (_ for _ in ()).throw(RuntimeError("storage unavailable")))
    raw_session_id = "qa-session-token-must-not-be-logged"

    with app_module.app.test_request_context("/logout"):
        from flask import session

        session["auth_session_id"] = raw_session_id
        session["auth_session_expires_at"] = "2030-01-01T00:00:00+00:00"
        assert app_module._revoke_session_for_logout("qa-user") is False

    output = capsys.readouterr().out
    assert "RuntimeError" in output
    assert raw_session_id not in output


def test_password_reset_revokes_legacy_admin_cookie_without_version_field(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-admin-reset-v942")
    client = app_module.app.test_client()
    _sign_in_cookie(client, user, app_module)
    with client.session_transaction() as state:
        state.pop("auth_version", None)
    assert client.get("/api/admin/route-map").status_code == 200

    app_module.reset_user_password(user["id"], "replacement-password")
    response = client.get("/api/admin/route-map")

    assert response.status_code == 403
    with client.session_transaction() as state:
        assert "user_id" not in state


def test_legacy_telegram_routes_require_csrf_for_admin_browser_but_accept_cron_header(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch)
    client = app_module.app.test_client()
    _sign_in_cookie(client, user, app_module)
    monkeypatch.setenv("AUTOMATION_SECRET", "qa-telegram-header-v942")
    monkeypatch.setattr(app_module, "telegram_config", lambda: {"enabled": True})
    calls = []
    monkeypatch.setattr(
        app_module,
        "telegram_scheduler_delivery",
        lambda force=False: calls.append(bool(force)) or {"ok": True, "status": "SIMULATED_QA"},
    )

    blocked = client.post("/api/telegram/auto-run", json={})
    assert blocked.status_code == 403
    assert blocked.get_json()["error"] == "csrf_required"
    assert calls == []

    browser_allowed = client.post(
        "/api/telegram/auto-run",
        json={},
        headers={"X-CSRF-Token": "qa-csrf-v942"},
    )
    assert browser_allowed.status_code == 200
    assert calls == [False]

    cron_allowed = client.post(
        "/api/telegram/auto-run",
        json={},
        headers={"X-Automation-Secret": "qa-telegram-header-v942"},
    )
    assert cron_allowed.status_code == 200
    assert calls == [False, False]


def test_legacy_telegram_csrf_exemption_is_not_enabled_by_a_browser_cookie_alone(app_module, monkeypatch):
    monkeypatch.setenv("AUTOMATION_SECRET", "qa-telegram-header-v942")
    for path in ("/api/telegram/auto-run", "/api/telegram/scheduler-tick", "/api/v495/telegram-auto-run"):
        with app_module.app.test_request_context(path, method="POST"):
            assert app_module.csrf_exempt_path(path) is False
        with app_module.app.test_request_context(path, method="POST", headers={"X-Automation-Secret": "qa-telegram-header-v942"}):
            assert app_module.csrf_exempt_path(path) is True
