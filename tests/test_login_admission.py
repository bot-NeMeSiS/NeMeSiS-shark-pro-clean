"""Synthetic SQLite contracts for shared-IP login admission; no application import."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import sqlite3
import threading

import pytest

from engines import security_engine as security


IP = "203.0.113.18"


def _finalize(path, slot, success, **kwargs):
    return security.finalize_login_attempt(
        str(path), claim_id=slot["claim_id"], ip_address=IP, success=success,
        path="/cliente-login", username="qa@example.invalid", **kwargs,
    )


def _counts(path):
    with sqlite3.connect(path) as conn:
        pending = conn.execute("SELECT COUNT(*) FROM security_action_attempts WHERE scope='auth_login'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM security_events WHERE event_type='login_attempt' AND success=0").fetchone()[0]
        passed = conn.execute("SELECT COUNT(*) FROM security_events WHERE event_type='login_attempt' AND success=1").fetchone()[0]
    return pending, failed, passed


def test_failed_login_moves_one_reservation_to_one_audited_failure(tmp_path):
    path = tmp_path / "failed.sqlite3"
    slot = security.claim_login_attempt(str(path), ip_address=IP)
    assert slot["allowed"] is True
    assert _counts(path) == (1, 0, 0)
    assert _finalize(path, slot, False)
    assert _counts(path) == (0, 1, 0)
    assert _finalize(path, slot, False) is False
    assert _counts(path) == (0, 1, 0)


def test_more_than_eight_successes_on_shared_network_do_not_consume_failed_budget(tmp_path):
    path = tmp_path / "shared-network.sqlite3"
    for _ in range(32):
        slot = security.claim_login_attempt(str(path), ip_address=IP)
        assert slot["allowed"] is True
        assert _finalize(path, slot, True)
    assert _counts(path) == (0, 0, 32)


def test_historical_failed_events_and_pending_verifications_share_exact_budget(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    for index in range(7):
        security.record_security_event(
            str(path), event_type="login_attempt", ip_address=IP,
            path="/admin-login" if index % 2 else "/login", success=False,
        )
    slot = security.claim_login_attempt(str(path), ip_address=IP)
    assert slot["allowed"] is True
    blocked = security.claim_login_attempt(str(path), ip_address=IP)
    assert blocked["allowed"] is False
    assert blocked["reason"] == "rate_limited"
    assert _finalize(path, slot, False)
    assert _counts(path) == (0, 8, 0)
    assert security.claim_login_attempt(str(path), ip_address=IP)["reason"] == "rate_limited"
    assert security.claim_login_attempt(str(path), ip_address="203.0.113.19")["allowed"] is True


@pytest.mark.parametrize("workers", [1, 8, 32])
def test_concurrent_pending_verifications_never_exceed_eight(tmp_path, workers):
    path = tmp_path / f"concurrent-{workers}.sqlite3"
    security.ensure_security_schema(str(path))
    barrier = threading.Barrier(workers)

    def claim(_):
        barrier.wait(timeout=10)
        return security.claim_login_attempt(str(path), ip_address=IP)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(claim, range(workers)))
    admitted = [result for result in results if result.get("allowed")]
    assert len(admitted) == min(8, workers)
    assert all(result.get("allowed") or result.get("reason") == "rate_limited" for result in results)
    assert len({result["claim_id"] for result in admitted}) == len(admitted)
    for slot in admitted:
        assert _finalize(path, slot, False)
    assert _counts(path) == (0, min(8, workers), 0)


def test_wrong_ip_or_scope_cannot_finalize_another_reservation(tmp_path):
    path = tmp_path / "isolation.sqlite3"
    slot = security.claim_login_attempt(str(path), ip_address=IP)
    assert security.finalize_login_attempt(
        str(path), claim_id=slot["claim_id"], ip_address="203.0.113.20", success=True,
    ) is False
    assert _counts(path) == (1, 0, 0)
    recovery = security.claim_rate_limit_slot(str(path), scope="auth_recuperacion", subject=IP, limit=5, minutes=30)
    assert _finalize(path, recovery, True) is False
    assert _counts(path) == (1, 0, 0)


def test_store_unavailable_never_allows_admission_or_finalization(tmp_path, monkeypatch):
    path = tmp_path / "unavailable.sqlite3"
    slot = security.claim_login_attempt(str(path), ip_address=IP)
    monkeypatch.setattr(security.sqlite3, "connect", lambda *_a, **_k: (_ for _ in ()).throw(sqlite3.OperationalError("qa unavailable")))
    result = security.claim_login_attempt(str(path), ip_address=IP)
    assert result["allowed"] is False
    assert result["reason"] == "rate_limit_store_unavailable"
    assert _finalize(path, slot, True) is False


def test_failed_audit_write_rolls_back_and_keeps_reservation_charged(tmp_path):
    path = tmp_path / "rollback.sqlite3"
    slot = security.claim_login_attempt(str(path), ip_address=IP)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TRIGGER deny_login_audit BEFORE INSERT ON security_events BEGIN SELECT RAISE(ABORT, 'qa deny write'); END")
    assert _finalize(path, slot, True) is False
    assert _counts(path) == (1, 0, 0)


def test_expired_pending_verification_cannot_be_finalized_as_success(tmp_path):
    path = tmp_path / "expired.sqlite3"
    slot = security.claim_login_attempt(str(path), ip_address=IP)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE security_action_attempts SET created_at=? WHERE id=?", (
            (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat(timespec="seconds"), slot["claim_id"],
        ))
    assert _finalize(path, slot, True) is False
    assert _counts(path) == (1, 0, 0)
    assert security.claim_login_attempt(str(path), ip_address=IP)["allowed"] is True


@pytest.mark.parametrize("claim_id,success", [(True, True), (0, True), (-1, True), ("1", True), (1, "false")])
def test_malformed_finalization_is_rejected_without_creating_a_database(tmp_path, claim_id, success):
    path = tmp_path / "invalid.sqlite3"
    assert security.finalize_login_attempt(str(path), claim_id=claim_id, ip_address=IP, success=success) is False
    assert not path.exists()


def test_reservation_contains_only_scoped_digest_not_raw_account_or_ip(tmp_path):
    path = tmp_path / "privacy.sqlite3"
    slot = security.claim_login_attempt(str(path), ip_address=IP)
    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT scope,subject_hash FROM security_action_attempts WHERE id=?", (slot["claim_id"],)).fetchone()
    assert row == ("auth_login", hashlib.sha256(("auth_login\0" + IP).encode()).hexdigest())
    assert IP not in row[1]
