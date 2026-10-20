from datetime import datetime, timedelta, timezone
import sqlite3
from pathlib import Path

import pytest

from engines.data_memory_engine import cleanup_old_memory


def test_oversized_request_is_rejected_before_csrf_or_route_processing(client, app_module):
    limit = app_module.MAX_REQUEST_BODY_BYTES
    body = b'{"padding":"' + (b"x" * limit) + b'"}'

    response = client.post(
        "/api/growth/funnel-event",
        data=body,
        content_type="application/json",
    )

    assert response.status_code == 413
    assert response.get_json()["error"] == "payload_too_large"


def test_oversized_chunked_request_is_rejected_at_the_shared_boundary(client, app_module):
    body = b'{"padding":"' + (b"x" * app_module.MAX_REQUEST_BODY_BYTES) + b'"}'
    response = client.post(
        "/api/growth/funnel-event",
        data=body,
        content_type="application/json",
        environ_overrides={"CONTENT_LENGTH": "", "wsgi.input_terminated": True},
    )

    assert response.status_code == 413
    assert response.get_json()["error"] == "payload_too_large"


def test_small_json_csrf_body_token_still_works_but_large_body_token_is_not_parsed(client, app_module):
    client.get("/landing")
    with client.session_transaction() as state:
        csrf = state["csrf_token"]

    accepted = client.post(
        "/api/growth/funnel-event",
        json={"stage": "LANDING", "target_id": "qa-small-body-token", "csrf_token": csrf},
    )
    assert accepted.status_code == 202

    chunked_body = app_module.json.dumps(
        {"stage": "LANDING", "target_id": "qa-small-chunked-body-token", "csrf_token": csrf}
    )
    accepted_chunked = client.post(
        "/api/growth/funnel-event",
        data=chunked_body,
        content_type="application/json",
        environ_overrides={"CONTENT_LENGTH": "", "wsgi.input_terminated": True},
    )
    assert accepted_chunked.status_code == 202

    rejected = client.post(
        "/api/growth/funnel-event",
        json={
            "stage": "LANDING",
            "target_id": "qa-large-body-token",
            "csrf_token": csrf,
            "padding": "x" * app_module.MAX_CSRF_JSON_TOKEN_BODY_BYTES,
        },
    )
    assert rejected.status_code == 403
    assert rejected.get_json()["error"] == "csrf_required"


def test_csrf_and_rate_limit_rejections_remain_denied_when_audit_sampling_is_full(client, app_module, monkeypatch):
    writes = []
    monkeypatch.setattr(app_module, "record_security_event", lambda *_args, **kwargs: writes.append(kwargs))
    monkeypatch.setattr(app_module, "_request_rejection_audit_events", {})
    monkeypatch.setattr(app_module, "security_client_ip", lambda: "198.51.100.1")

    responses = [
        client.post("/api/growth/funnel-event", json={"stage": "LANDING"})
        for _ in range(app_module.REQUEST_REJECTION_AUDIT_MAX_PER_IP_PER_WINDOW + 5)
    ]

    assert all(response.status_code == 403 for response in responses)
    assert len(writes) == app_module.REQUEST_REJECTION_AUDIT_MAX_PER_IP_PER_WINDOW
    assert all(event["event_type"] == "csrf_block" for event in writes)
    assert app_module._allow_request_rejection_audit_write("csrf_block", "198.51.100.2") is True
    assert app_module._allow_request_rejection_audit_write("rate_limit_block", "198.51.100.1") is True


@pytest.mark.parametrize(
    ("paths", "limit", "scope"),
    [
        (["/forgot-password", "/admin-forgot-password"], 5, "recuperacion"),
        (["/reset-password/token", "/admin-reset-password/token"], 6, "cambio_password"),
    ],
)
def test_password_recovery_attempts_share_a_persisted_budget_across_aliases(
    app_module, tmp_path, monkeypatch, paths, limit, scope
):
    path = tmp_path / f"{scope}.sqlite3"
    monkeypatch.setattr(app_module, "DB_PATH", str(path))

    for index in range(limit):
        with app_module.app.test_request_context(
            paths[index % len(paths)],
            method="POST",
            environ_base={"REMOTE_ADDR": "203.0.113.77"},
        ):
            assert app_module.security_rate_limit_for_request() is None

    with app_module.app.test_request_context(
        paths[limit % len(paths)],
        method="POST",
        environ_base={"REMOTE_ADDR": "203.0.113.77"},
    ):
        response = app_module.security_rate_limit_for_request()

    assert response is not None
    assert response.status_code == 429


def test_password_recovery_fails_closed_when_attempt_store_is_unavailable(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "claim_rate_limit_slot",
        lambda *_args, **_kwargs: {"allowed": False, "reason": "rate_limit_store_unavailable"},
    )
    with app_module.app.test_request_context("/forgot-password", method="POST"):
        response = app_module.security_rate_limit_for_request()

    assert response.status_code == 503
    assert response.get_json() is None


def test_invalid_csrf_does_not_consume_password_recovery_attempt_budget(app_module, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "csrf-order.sqlite3"))
    monkeypatch.setattr(
        app_module,
        "security_rate_limit_for_request",
        lambda: calls.append("checked") or None,
    )
    with app_module.app.test_request_context(
        "/forgot-password",
        method="POST",
        data={"login": "qa@example.invalid"},
        environ_base={"REMOTE_ADDR": "203.0.113.77"},
    ):
        response = app_module.enforce_security_guards()

    assert response.status_code == 403
    assert calls == []


def test_login_aliases_share_one_failed_attempt_budget(app_module, tmp_path, monkeypatch):
    path = tmp_path / "security-rate-limit.sqlite3"
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    client_ip = "203.0.113.45"
    for index in range(8):
        app_module.record_security_event(
            str(path),
            event_type="login_attempt",
            severity="WARN",
            ip_address=client_ip,
            path="/cliente-login" if index < 4 else "/admin-login",
            method="POST",
            success=False,
            reason="qa_invalid_password",
        )

    with app_module.app.test_request_context(
        "/entrar",
        method="POST",
        headers={"X-Forwarded-For": f"{client_ip}, 198.51.100.20"},
    ):
        response = app_module.security_rate_limit_for_request()

    assert response is not None
    assert response.status_code == 429
    assert "Demasiados intentos" in response.get_data(as_text=True)


def test_render_forwarded_client_ip_is_validated_and_malformed_value_falls_back(app_module):
    with app_module.app.test_request_context(
        "/",
        headers={"X-Forwarded-For": "203.0.113.9, 10.0.0.4"},
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    ):
        assert app_module.security_client_ip() == "203.0.113.9"

    with app_module.app.test_request_context(
        "/",
        headers={"X-Forwarded-For": "not-an-ip, 10.0.0.4"},
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    ):
        assert app_module.security_client_ip() == "127.0.0.1"


def test_signup_and_admin_bootstrap_require_the_same_minimum_password_length(app_module, tmp_path, monkeypatch):
    path = tmp_path / "signup-password.sqlite3"
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    monkeypatch.setattr(app_module, "seed_core", lambda: None)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE users(
                id TEXT PRIMARY KEY, name TEXT, username TEXT UNIQUE, email TEXT UNIQUE,
                password_hash TEXT, role TEXT, membership TEXT, created_at TEXT, last_login TEXT
            )"""
        )

    with pytest.raises(ValueError, match="al menos 8 caracteres"):
        app_module.create_user("QA", "qa-short", "short@example.invalid", "1234567")

    user = app_module.create_user("QA", "qa-eight", "eight@example.invalid", "12345678")
    assert user["email"] == "eight@example.invalid"
    assert app_module.check_password_hash(user["password_hash"], "12345678")

    with sqlite3.connect(":memory:") as conn:
        with pytest.raises(ValueError, match="al menos 8 caracteres"):
            app_module.create_admin_record(conn, "QA", "qa-admin", "admin@example.invalid", "1234567")
    with pytest.raises(ValueError, match="al menos 8 caracteres"):
        app_module.reset_user_password("missing-user", "1234567")
    template = Path(__file__).resolve().parents[1] / "templates" / "register.html"
    assert 'minlength="8"' in template.read_text(encoding="utf-8")


def test_environment_admin_rejects_short_password_even_for_existing_account(app_module, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.invalid")
    monkeypatch.setenv("ADMIN_USERNAME", "qa-admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "short")
    monkeypatch.setattr(
        app_module,
        "get_user_by_email",
        lambda _email: pytest.fail("short environment password must be rejected before account lookup"),
    )

    assert app_module.authenticate_env_admin("admin@example.invalid", "short") is None


def test_memory_cleanup_applies_configured_telegram_and_security_log_retention(tmp_path, monkeypatch):
    path = tmp_path / "retention.sqlite3"
    monkeypatch.setenv("DATA_MEMORY_KEEP_DAYS", "180")
    monkeypatch.setenv("TELEGRAM_LOG_KEEP_DAYS", "30")
    monkeypatch.setenv("SECURITY_EVENT_KEEP_DAYS", "90")
    cleanup_old_memory(str(path))

    old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat(timespec="seconds")
    telegram_recent = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(timespec="seconds")
    security_recent = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat(timespec="seconds")
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE telegram_logs(id TEXT PRIMARY KEY, created_at TEXT)")
        conn.execute("CREATE TABLE security_events(id TEXT PRIMARY KEY, created_at TEXT)")
        conn.executemany("INSERT INTO telegram_logs(id,created_at) VALUES(?,?)", [("old", old), ("recent", telegram_recent)])
        conn.executemany("INSERT INTO security_events(id,created_at) VALUES(?,?)", [("old", old), ("recent", security_recent)])
        conn.commit()

    result = cleanup_old_memory(str(path))

    assert result["ok"] is True
    assert result["retention_by_table"]["telegram_logs"]["deleted_rows"] == 1
    assert result["retention_by_table"]["telegram_logs"]["keep_days"] == 30
    assert result["retention_by_table"]["security_events"]["deleted_rows"] == 1
    assert result["retention_by_table"]["security_events"]["keep_days"] == 90
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT id FROM telegram_logs").fetchall() == [("recent",)]
        assert conn.execute("SELECT id FROM security_events").fetchall() == [("recent",)]


def test_memory_cleanup_reports_and_preserves_invalid_log_timestamps(tmp_path, monkeypatch):
    path = tmp_path / "invalid-retention.sqlite3"
    monkeypatch.setenv("TELEGRAM_LOG_KEEP_DAYS", "30")
    monkeypatch.setenv("SECURITY_EVENT_KEEP_DAYS", "90")
    cleanup_old_memory(str(path))
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE telegram_logs(id TEXT PRIMARY KEY, created_at TEXT)")
        conn.execute("INSERT INTO telegram_logs(id,created_at) VALUES('unknown-date','not-a-date')")
        conn.commit()

    result = cleanup_old_memory(str(path))

    assert result["ok"] is False
    assert "telegram_logs" in result["failed_tables"]
    assert result["retention_by_table"]["telegram_logs"]["status"] == "invalid_timestamps"
    assert result["retention_by_table"]["telegram_logs"]["invalid_timestamp_rows"] == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT id FROM telegram_logs").fetchall() == [("unknown-date",)]
