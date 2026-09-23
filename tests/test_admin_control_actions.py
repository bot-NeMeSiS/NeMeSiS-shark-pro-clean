"""Admin action boundary tests: isolated SQLite only, never provider calls."""
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import threading

import pytest

from engines.admin_control_engine import AdminControlStore, Rejected, SETTING_DEFAULTS, registry, validate_parameters


@pytest.fixture
def store(tmp_path):
    obj = AdminControlStore(tmp_path / "admin-test.sqlite", "V941_TEST")
    obj.initialize()
    return obj


def propose(store, action="settings.update", params=None, **kwargs):
    return store.propose("admin-1", action, params if params is not None else {"key": "highlights_enabled", "value": False}, **kwargs)


def confirm(store, proposal, **kwargs):
    return store.confirm("admin-1", proposal["id"], confirmation=True, **kwargs)


def test_readonly_defaults_do_not_create_database(tmp_path):
    path = tmp_path / "absent.sqlite"
    values = AdminControlStore(path, "v").settings()
    assert {key: value["value"] for key, value in values.items()} == SETTING_DEFAULTS
    assert not path.exists()


def test_registry_has_no_executable_metadata_and_copies_are_independent():
    records = registry()
    assert all(row["requires_confirmation"] and row["permission"] == "admin" for row in records)
    assert all("handler" not in row for row in records)
    records[0]["parameters_schema"]["file"] = "path"
    assert "file" not in registry()[0]["parameters_schema"]


@pytest.mark.parametrize("action,params", [
    ("shell", {"command": "rm -rf /"}), ("os.system", {}), ("../file", {}),
    ("settings.update", {"key": "DB_PATH", "value": "elsewhere"}),
    ("settings.update", {"key": "highlights_enabled", "value": 1}),
    ("settings.update", {"key": "banner_enabled", "value": "true"}),
    ("settings.update", {"key": "banner_text", "value": "x" * 241}),
    ("settings.update", {"key": "banner_text", "value": "safe", "handler": "exec"}),
    ("settings.rollback", {"audit_id": True}),
    ("sports.sync", {"path": "../.env"}), ("sports.sync", {"shell": "echo 1"}),
    ("sentinel.create_improvement", {"title": "Fix", "detail": "Reason", "route": "file:///etc/passwd"}),
    ("sentinel.create_improvement", {"title": "Fix", "detail": "Reason", "route": "/../../.env"}),
    ("sentinel.create_improvement", {"title": "Fix", "detail": "Reason", "route": "//evil.example"}),
])
def test_closed_registry_rejects_invalid_actions_and_parameters(action, params):
    with pytest.raises(Rejected):
        validate_parameters(action, params)


@pytest.mark.parametrize("text", [
    "OPENAI_API_KEY=privatevalue", "TELEGRAM_BOT_TOKEN = privatevalue", "password=privatevalue",
    "sk-proj-abcdefghijklmno", "sk_live_abcdefghijklmno", "123456789:abcdefghijklmnopqrstuv",
    "https://login:privatevalue@example.com", "session_id=privatevalue",
])
def test_secret_looking_free_text_never_persisted(store, text):
    with pytest.raises(Rejected):
        propose(store, params={"key": "banner_text", "value": text})
    assert store.list_proposals("admin-1") == []
    assert store.list_audit() == []


def test_proposal_does_not_apply_until_explicit_confirmation(store):
    proposal = propose(store, origin="SHARK proposal")
    assert store.settings()["highlights_enabled"]["value"] is True
    assert proposal["preview"]["before"]["value"] is True
    assert proposal["preview"]["after"]["value"] is False
    with pytest.raises(Rejected, match="confirmation_required"):
        store.confirm("admin-1", proposal["id"])
    result = confirm(store, proposal)
    assert result["ok"] and result["verification"] == "VERIFIED"
    assert store.settings()["highlights_enabled"]["value"] is False
    audit = store.list_audit()[0]
    assert audit["admin"] == "admin-1" and audit["origin"] == "SHARK proposal"
    assert audit["before"]["value"] is True and audit["after"]["value"] is False


def test_settings_atomic_idempotency_and_optimistic_rollback(store):
    proposal = propose(store, request_key="repeat_request_001")
    same = propose(store, request_key="repeat_request_001")
    assert same["id"] == proposal["id"]
    with pytest.raises(Rejected, match="idempotency_conflict"):
        propose(store, params={"key": "banner_enabled", "value": True}, request_key="repeat_request_001")
    first = confirm(store, proposal)
    repeated = confirm(store, proposal)
    assert repeated["reused"] and first["audit_id"] == repeated["audit_id"]
    rollback = propose(store, "settings.rollback", {"audit_id": first["audit_id"]})
    result = confirm(store, rollback)
    assert result["ok"]
    assert store.settings()["highlights_enabled"]["value"] is True
    assert store.settings()["highlights_enabled"]["revision"] == 2
    assert len(store.list_audit()) == 2
    with pytest.raises(Rejected, match="setting_changed_since_action"):
        propose(store, "settings.rollback", {"audit_id": first["audit_id"]})


def test_newer_setting_change_invalidates_pending_proposal(store):
    first = propose(store)
    second = propose(store)
    confirm(store, first)
    with pytest.raises(Rejected, match="proposal_state_changed"):
        confirm(store, second)
    assert len(store.list_audit()) == 1


def test_owner_version_and_expiry_bind_confirmation(store):
    now = [1000.0]
    store.clock = lambda: now[0]
    proposal = propose(store)
    with pytest.raises(Rejected, match="proposal_not_found"):
        store.confirm("other-admin", proposal["id"], confirmation=True)
    with pytest.raises(Rejected, match="proposal_version_changed"):
        AdminControlStore(store.path, "V942", clock=lambda: now[0]).confirm("admin-1", proposal["id"], confirmation=True)
    now[0] = 2000
    with pytest.raises(Rejected, match="proposal_expired"):
        confirm(store, proposal)
    assert store.settings()["highlights_enabled"]["value"] is True


def test_cancel_preserves_audit_and_prevents_execution(store):
    proposal = propose(store)
    cancelled = store.cancel("admin-1", proposal["id"])
    assert cancelled["ok"] and store.cancel("admin-1", proposal["id"])["reused"]
    with pytest.raises(Rejected, match="proposal_not_pending"):
        confirm(store, proposal)
    assert store.list_audit()[0]["verification"] == "NOT_EXECUTED"


def test_audit_is_append_only(store):
    confirm(store, propose(store))
    with sqlite3.connect(store.path) as conn:
        with pytest.raises(sqlite3.IntegrityError, match="append_only"):
            conn.execute("DELETE FROM admin_action_audit")
        with pytest.raises(sqlite3.IntegrityError, match="append_only"):
            conn.execute("UPDATE admin_action_audit SET admin='someone'")


def test_callback_executes_only_after_confirmation_and_verifies(store):
    calls = []
    proposal = propose(store, "sports.sync", {})
    assert not calls
    def handler(parameters):
        calls.append(parameters)
        return {"ok": True, "processed": 3, "secret": "SENSITIVE_RAW", "message": "token=SENSITIVE_RAW"}
    result = confirm(store, proposal, handlers={"sports.sync": handler}, verifiers={"sports.sync": lambda p, r: {"verified": r["processed"] == 3}})
    assert result["ok"] and result["result"]["processed"] == 3 and calls == [{}]
    assert "SENSITIVE_RAW" not in json.dumps(store.list_audit())
    assert confirm(store, proposal)["reused"]
    assert calls == [{}]


def test_verification_failure_is_not_reported_as_success(store):
    proposal = propose(store, "sentinel.scan", {})
    result = confirm(store, proposal, handlers={"sentinel.scan": lambda p: {"ok": True}}, verifiers={"sentinel.scan": lambda p, r: False})
    assert not result["ok"] and result["verification"] == "VERIFICATION_FAILED"
    assert store.list_proposals("admin-1")[0]["state"] == "FAILED"


def test_callback_exception_is_sanitized_and_not_retried(store):
    calls = []
    def handler(parameters):
        calls.append(1)
        raise RuntimeError("OPENAI_API_KEY=DO_NOT_KEEP")
    proposal = propose(store, "telegram.dry_run", {})
    result = confirm(store, proposal, handlers={"telegram.dry_run": handler}, verifiers={"telegram.dry_run": lambda p, r: True})
    assert not result["ok"] and result["result"]["code"] == "action_failed"
    assert "DO_NOT_KEEP" not in json.dumps(store.list_audit())
    assert confirm(store, proposal)["reused"] and calls == [1]


def test_missing_handler_is_unavailable_without_claim(store):
    proposal = propose(store, "sports.sync", {})
    with pytest.raises(Rejected, match="action_not_connected"):
        confirm(store, proposal)
    assert store.list_proposals("admin-1")[0]["state"] == "PENDING"


def test_telegram_high_risk_requires_exact_phrase_and_only_stub_runs(store):
    proposal = propose(store, "telegram.retry_failed", {})
    with pytest.raises(Rejected, match="reinforced_confirmation_required"):
        confirm(store, proposal)
    calls = []
    result = store.confirm("admin-1", proposal["id"], confirmation="REINTENTAR TELEGRAM",
        handlers={"telegram.retry_failed": lambda p: calls.append(p) or {"ok": True, "sent": 0}},
        verifiers={"telegram.retry_failed": lambda p, r: True})
    assert result["ok"] and calls == [{}]


def test_concurrent_confirmations_do_not_invoke_callback_twice(store):
    proposal = propose(store, "sports.sync", {})
    started, release = threading.Event(), threading.Event()
    calls = []
    def handler(parameters):
        calls.append(1)
        started.set()
        assert release.wait(5)
        return {"ok": True}
    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(confirm, store, proposal, handlers={"sports.sync": handler}, verifiers={"sports.sync": lambda p, r: True})
        assert started.wait(5)
        try:
            with pytest.raises(Rejected, match="proposal_not_pending"):
                confirm(store, proposal, handlers={"sports.sync": handler}, verifiers={"sports.sync": lambda p, r: True})
        finally:
            release.set()
        assert future.result()["ok"]
    assert calls == [1]


def test_setting_changes_reuse_existing_storage_and_do_not_touch_other_keys(store):
    with sqlite3.connect(store.path) as conn:
        conn.execute("INSERT INTO automation_state VALUES ('unrelated', '{\"enabled\":true}', 'before')")
    confirm(store, propose(store, params={"key": "banner_text", "value": "Aviso real"}))
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("SELECT value_json FROM automation_state WHERE key='unrelated'").fetchone()[0] == '{"enabled":true}'
        assert conn.execute("SELECT COUNT(*) FROM automation_state WHERE key LIKE 'admin_control.settings.%'").fetchone()[0] == 1

def test_callback_cannot_smuggle_arbitrary_values_through_status_or_identifiers(store):
    proposal = propose(store, "sports.sync", {})
    result = confirm(store, proposal,
        handlers={"sports.sync": lambda p: {"ok": True, "status": "SENSITIVE_VALUE", "code": "SENSITIVE_VALUE", "issue_id": "SENSITIVE_VALUE", "task_id": "SENSITIVE_VALUE"}},
        verifiers={"sports.sync": lambda p, r: True})
    assert result["result"] == {"ok": True}
    assert "SENSITIVE_VALUE" not in json.dumps(store.list_audit())


def test_external_verifier_cannot_turn_failed_handler_result_into_success(store):
    proposal = propose(store, "sports.sync", {})
    result = confirm(store, proposal, handlers={"sports.sync": lambda p: {"ok": False}}, verifiers={"sports.sync": lambda p, r: True})
    assert not result["ok"] and result["verification"] == "VERIFICATION_FAILED"


def test_interrupted_external_claim_is_never_reinvoked(store):
    proposal = propose(store, "sports.sync", {})
    calls = []
    def interrupted(parameters):
        calls.append(1)
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        confirm(store, proposal, handlers={"sports.sync": interrupted}, verifiers={"sports.sync": lambda p, r: True})
    with pytest.raises(Rejected, match="proposal_not_pending"):
        confirm(store, proposal, handlers={"sports.sync": interrupted}, verifiers={"sports.sync": lambda p, r: True})
    assert calls == [1] and store.list_proposals("admin-1")[0]["state"] == "EXECUTING"
    assert store.list_audit()[0]["verification"] == "PENDING"

@pytest.mark.parametrize("text", [
    '{"OPENAI_API_KEY":"never_store_this"}', '{"api_key": "never_store_this"}',
    "API_FOOTBALL_KEY=never_store_this", "Authorization: Bearer never_store_this",
    "Bearer never_store_this", " ".join(("-----BEGIN", "PRIVATE", "KEY-----")),
])
def test_quoted_credentials_and_provider_key_names_are_rejected(store, text):
    with pytest.raises(Rejected, match="unsafe_parameters"):
        propose(store, params={"key": "banner_text", "value": text})
    assert store.list_proposals("admin-1") == []

def test_existing_database_lock_does_not_silently_enable_default_settings(store, monkeypatch):
    from contextlib import contextmanager
    @contextmanager
    def locked_connection(**kwargs):
        raise sqlite3.OperationalError("database is locked")
        yield
    monkeypatch.setattr(store,"connection",locked_connection)
    with pytest.raises(sqlite3.OperationalError,match="locked"):
        store.settings()
