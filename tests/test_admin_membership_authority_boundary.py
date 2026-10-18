"""Commercial plan editing must never grant or remove platform administration."""

import re

import pytest


def _isolated_users_db(app_module, tmp_path, monkeypatch):
    path = tmp_path / "membership-authority.sqlite3"
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", str(path))
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(app_module, "APP_INITIALIZED", True)
    conn = app_module.sqlite_connect(path)
    conn.execute(
        """CREATE TABLE users(
            id TEXT PRIMARY KEY, name TEXT, username TEXT UNIQUE, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, auth_version INTEGER NOT NULL DEFAULT 0,
            role TEXT DEFAULT 'FREE', membership TEXT DEFAULT 'FREE',
            membership_source TEXT, membership_started_at TEXT, membership_expires_at TEXT,
            membership_note TEXT, membership_updated_at TEXT, membership_updated_by TEXT,
            membership_admin_granted INTEGER DEFAULT 0, created_at TEXT, last_login TEXT
        )"""
    )
    conn.execute(
        """INSERT INTO users(
            id,name,username,email,password_hash,auth_version,role,membership,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            "qa-owner",
            "QA Owner",
            "qa-owner",
            "qa-owner@example.invalid",
            app_module.generate_password_hash("qa-owner-password"),
            0,
            "ADMIN",
            "ADMIN",
            app_module.now_iso(),
        ),
    )
    conn.execute(
        """INSERT INTO users(
            id,name,username,email,password_hash,auth_version,role,membership,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            "qa-customer",
            "QA Customer",
            "qa-customer",
            "qa-customer@example.invalid",
            app_module.generate_password_hash("qa-customer-password"),
            0,
            "PRO",
            "PRO",
            app_module.now_iso(),
        ),
    )
    conn.commit()
    conn.close()
    return path


def _owner_session(client):
    with client.session_transaction() as state:
        state.update(
            user_id="qa-owner",
            user_role="ADMIN",
            membership="ADMIN",
            user_membership="ADMIN",
            auth_version=0,
            csrf_token="qa-membership-csrf",
        )


def test_commercial_plan_update_cannot_elevate_customer_to_admin(app_module, tmp_path, monkeypatch):
    _isolated_users_db(app_module, tmp_path, monkeypatch)

    result = app_module.update_user_membership("qa-customer", "ADMIN", admin_id="qa-owner")

    assert result is None
    customer = app_module.get_user_by_id("qa-customer")
    assert customer["role"] == "PRO"
    assert customer["membership"] == "PRO"
    assert customer["auth_version"] == 0


def test_unknown_membership_value_does_not_silently_reset_customer_plan(app_module, tmp_path, monkeypatch):
    _isolated_users_db(app_module, tmp_path, monkeypatch)

    result = app_module.update_user_membership("qa-customer", "unexpected-role", admin_id="qa-owner")

    assert result is None
    customer = app_module.get_user_by_id("qa-customer")
    assert customer["role"] == "PRO"
    assert customer["membership"] == "PRO"


def test_commercial_plan_update_cannot_demote_or_change_owner(app_module, tmp_path, monkeypatch):
    _isolated_users_db(app_module, tmp_path, monkeypatch)

    result = app_module.update_user_membership("qa-owner", "PRO", admin_id="qa-owner")

    assert result is None
    owner = app_module.get_user_by_id("qa-owner")
    assert owner["role"] == "ADMIN"
    assert owner["membership"] == "ADMIN"
    assert owner["auth_version"] == 0


def test_customer_registration_cannot_request_administrative_role(app_module, tmp_path, monkeypatch):
    _isolated_users_db(app_module, tmp_path, monkeypatch)

    with pytest.raises(ValueError, match="se configura por separado"):
        app_module.create_user(
            "Injected Admin",
            "injected-admin",
            "injected-admin@example.invalid",
            "qa-password",
            role="ADMIN",
            membership="ADMIN",
        )

    assert app_module.get_user_by_email("injected-admin@example.invalid") is None


def test_admin_bootstrap_detection_ignores_membership_without_admin_role(app_module, tmp_path, monkeypatch):
    path = _isolated_users_db(app_module, tmp_path, monkeypatch)
    conn = app_module.sqlite_connect(path)
    conn.execute("UPDATE users SET role='PRO', membership='ADMIN' WHERE id='qa-owner'")
    conn.commit()
    conn.close()

    assert app_module.admin_exists() is False


def test_environment_bootstrap_remains_the_explicit_admin_creation_path(app_module, tmp_path, monkeypatch):
    _isolated_users_db(app_module, tmp_path, monkeypatch)
    monkeypatch.setenv("ADMIN_EMAIL", "configured-owner@example.invalid")
    monkeypatch.setenv("ADMIN_USERNAME", "configured-owner")
    monkeypatch.setenv("ADMIN_PASSWORD", "configured-owner-secret")
    monkeypatch.setenv("ADMIN_NAME", "Configured Owner")

    user = app_module.authenticate_env_admin("configured-owner", "configured-owner-secret")

    assert user["email"] == "configured-owner@example.invalid"
    assert user["role"] == "ADMIN"
    assert user["membership"] == "ADMIN"


def test_user_directory_does_not_offer_admin_as_a_customer_plan(app_module, tmp_path, monkeypatch):
    _isolated_users_db(app_module, tmp_path, monkeypatch)
    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", lambda *_a, **_k: ({}, None))

    def safe_context(_path, _scope, label, callback, default):
        if label == "list_users":
            return callback()
        return {"quick_days": []} if label == "membership_admin" else True

    monkeypatch.setattr(app_module, "v932_safe_context", safe_context)
    client = app_module.app.test_client()
    _owner_session(client)

    response = client.get("/admin/users")

    assert response.status_code == 200
    markup = response.get_data(as_text=True)
    assert "Cuenta administrativa protegida" in markup
    membership_selects = re.findall(r'<select name="membership">(.*?)</select>', markup, re.DOTALL)
    assert len(membership_selects) == 1
    assert 'value="ADMIN"' not in membership_selects[0]
    assert "Guardar plan" in markup


def test_admin_users_post_cannot_elevate_customer_even_with_forged_form(app_module, tmp_path, monkeypatch):
    _isolated_users_db(app_module, tmp_path, monkeypatch)
    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", lambda *_a, **_k: ({}, None))

    def safe_context(_path, _scope, label, callback, default):
        if label == "list_users":
            return callback()
        return {"quick_days": []} if label == "membership_admin" else True

    monkeypatch.setattr(app_module, "v932_safe_context", safe_context)
    client = app_module.app.test_client()
    _owner_session(client)

    response = client.post(
        "/admin/users",
        data={
            "csrf_token": "qa-membership-csrf",
            "user_id": "qa-customer",
            "membership": "ADMIN",
            "membership_days": "0",
        },
    )

    assert response.status_code == 200
    assert "No se cambió ningún permiso administrativo" in response.get_data(as_text=True)
    customer = app_module.get_user_by_id("qa-customer")
    assert customer["role"] == "PRO"
    assert customer["membership"] == "PRO"

