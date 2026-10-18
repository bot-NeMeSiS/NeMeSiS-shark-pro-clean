"""Session revocation contracts using isolated SQLite and no external services."""

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
        """INSERT INTO users(id,name,username,email,password_hash,auth_version,role,membership,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (user_id, "QA Owner", "qa-owner", "qa-owner@example.invalid", app_module.generate_password_hash("qa-password"), 0, "ADMIN", "ADMIN", app_module.now_iso()),
    )
    conn.commit()
    conn.close()
    return app_module.get_user_by_id(user_id)


def _sign_in_cookie(client, user):
    with client.session_transaction() as state:
        state.update(
            user_id=user["id"],
            user_name=user.get("name") or "QA Owner",
            user_role=user.get("role") or "ADMIN",
            membership=user.get("membership") or "ADMIN",
            user_membership=user.get("membership") or "ADMIN",
            auth_version=int(user.get("auth_version") or 0),
            csrf_token="qa-csrf-v942",
        )


def test_schema_migration_adds_auth_version_to_legacy_users(app_module, tmp_path):
    path = tmp_path / "legacy-users.sqlite3"
    conn = app_module.sqlite_connect(path)
    conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY, username TEXT, email TEXT)")
    conn.execute("INSERT INTO users(id,username,email) VALUES('legacy-1','legacy','legacy@example.invalid')")
    app_module.run_schema_migrations(conn)
    columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    stored = conn.execute("SELECT auth_version FROM users WHERE id='legacy-1'").fetchone()["auth_version"]
    conn.close()
    assert columns["auth_version"]["notnull"] == 1
    assert stored == 0


def test_password_reset_revokes_existing_client_session(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-client-v942")
    conn = app_module.db()
    conn.execute("UPDATE users SET role='PRO',membership='PRO' WHERE id=?", (user["id"],))
    conn.commit()
    conn.close()
    user = app_module.get_user_by_id(user["id"])
    client = app_module.app.test_client()
    _sign_in_cookie(client, user)

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
    _sign_in_cookie(client, user)
    assert client.get("/api/admin/route-map").status_code == 200

    app_module.update_user_membership(user["id"], "FREE", admin_id="qa-owner")
    response = client.get("/api/admin/route-map")

    assert response.status_code == 403
    with client.session_transaction() as state:
        assert "user_id" not in state


def test_deleted_admin_account_cannot_reuse_signed_cookie(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-admin-deleted-v942")
    client = app_module.app.test_client()
    _sign_in_cookie(client, user)
    conn = app_module.db()
    conn.execute("DELETE FROM users WHERE id=?", (user["id"],))
    conn.commit()
    conn.close()

    response = client.get("/api/admin/route-map")

    assert response.status_code == 403
    with client.session_transaction() as state:
        assert "user_id" not in state


def test_password_reset_revokes_legacy_admin_cookie_without_version_field(app_module, tmp_path, monkeypatch):
    user = _isolated_admin(app_module, tmp_path, monkeypatch, user_id="qa-admin-reset-v942")
    client = app_module.app.test_client()
    _sign_in_cookie(client, user)
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
    _sign_in_cookie(client, user)
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
