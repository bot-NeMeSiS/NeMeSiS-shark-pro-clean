"""Security helpers for NeMeSiS SHARK PRO.

V604 - Security Hardening & Production Readiness
Lightweight, dependency-free protections designed for Render + Flask + SQLite:
- CSRF tokens for HTML forms.
- login/register/admin rate limiting.
- security event audit table.
- production SECRET_KEY validation.
- admin security summary.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

SECURITY_VERSION = "V604_SECURITY_HARDENING"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def ensure_security_schema(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS security_events(
                id TEXT PRIMARY KEY,
                event_type TEXT,
                severity TEXT DEFAULT 'INFO',
                ip_address TEXT,
                user_id TEXT,
                username TEXT,
                path TEXT,
                method TEXT,
                success INTEGER DEFAULT 0,
                reason TEXT,
                payload_json TEXT,
                created_at TEXT
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_security_events_type_time ON security_events(event_type, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_security_events_ip_time ON security_events(ip_address, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_security_events_path_time ON security_events(path, created_at)")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS security_action_attempts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                subject_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_security_action_scope_subject_time ON security_action_attempts(scope, subject_hash, created_at)")
        conn.commit()
    finally:
        conn.close()


def secure_secret_key() -> str:
    """Return a safe Flask secret key.

    In production/Render, fail closed if SECRET_KEY is missing. In local development,
    use a deterministic warning fallback so developers can still run the app.
    """
    key = os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY")
    if key and len(str(key)) >= 24:
        return str(key)
    production = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or os.getenv("RENDER_EXTERNAL_HOSTNAME"))
    production = production or os.getenv("FLASK_ENV", "").lower() == "production"
    if production:
        raise RuntimeError("SECRET_KEY es obligatoria en producción. Configúrala en Render antes de arrancar NeMeSiS SHARK PRO.")
    return "dev-only-change-secret-key-" + hashlib.sha256(os.getcwd().encode("utf-8")).hexdigest()[:24]


def generate_csrf_token(session_obj: Dict[str, Any]) -> str:
    token = session_obj.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session_obj["csrf_token"] = token
    return token


def validate_csrf(session_obj: Dict[str, Any], supplied_token: str) -> bool:
    expected = str(session_obj.get("csrf_token") or "")
    supplied = str(supplied_token or "")
    return bool(expected and supplied and hmac.compare_digest(expected, supplied))


def security_event_id(prefix: str = "sec") -> str:
    return prefix + "_" + secrets.token_hex(12)


def record_security_event(
    db_path: str,
    *,
    event_type: str,
    severity: str = "INFO",
    ip_address: str = "",
    user_id: str = "",
    username: str = "",
    path: str = "",
    method: str = "",
    success: bool = False,
    reason: str = "",
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        ensure_security_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO security_events(
                id,event_type,severity,ip_address,user_id,username,path,method,success,reason,payload_json,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                security_event_id(),
                event_type,
                severity,
                ip_address,
                user_id,
                username,
                path,
                method,
                1 if success else 0,
                reason,
                json.dumps(payload or {}, ensure_ascii=False),
                utc_now_iso(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        # Never break the user flow because the audit table is unavailable.
        pass


def count_recent_failed_events(db_path: str, *, event_type: str, ip_address: str, path_like: str = "", minutes: int = 15) -> int:
    try:
        ensure_security_schema(db_path)
        since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
        conn = sqlite3.connect(db_path)
        if path_like:
            row = conn.execute(
                """SELECT COUNT(*) FROM security_events
                   WHERE event_type=? AND ip_address=? AND success=0 AND created_at>=? AND path LIKE ?""",
                (event_type, ip_address, since, path_like),
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT COUNT(*) FROM security_events
                   WHERE event_type=? AND ip_address=? AND success=0 AND created_at>=?""",
                (event_type, ip_address, since),
            ).fetchone()
        conn.close()
        return int(row[0] if row else 0)
    except Exception:
        return 0


def claim_rate_limit_slot(
    db_path: str,
    *,
    scope: str,
    subject: str,
    limit: int,
    minutes: int,
    include_login_failures: bool = False,
) -> Dict[str, Any]:
    """Atomically reserve one sensitive-action attempt; fail closed on DB errors.

    The actor is stored only as a scoped one-way digest. This counter tracks
    attempts, not successes, so repeated failures cannot be used to probe a
    provider or external-send endpoint without bound.
    """
    safe_scope = str(scope or "").strip()[:80]
    safe_subject = str(subject or "").strip()
    try:
        max_attempts = max(1, min(int(limit), 100))
        window_minutes = max(1, min(int(minutes), 24 * 60))
    except (TypeError, ValueError):
        return {"allowed": False, "reason": "invalid_rate_limit"}
    if not safe_scope or not safe_subject or not str(db_path or "").strip():
        return {"allowed": False, "reason": "rate_limit_identity_missing"}
    if include_login_failures and safe_scope != "auth_login":
        return {"allowed": False, "reason": "invalid_rate_limit"}
    subject_hash = hashlib.sha256((safe_scope + "\0" + safe_subject).encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    now_text = now.isoformat(timespec="seconds")
    since = (now - timedelta(minutes=window_minutes)).isoformat(timespec="seconds")
    try:
        ensure_security_schema(db_path)
        conn = sqlite3.connect(db_path, timeout=2.0)
        try:
            conn.execute("PRAGMA busy_timeout=2000")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "DELETE FROM security_action_attempts WHERE created_at<?",
                ((now - timedelta(days=7)).isoformat(timespec="seconds"),),
            )
            rows = conn.execute(
                "SELECT created_at FROM security_action_attempts WHERE scope=? AND subject_hash=? AND created_at>=? ORDER BY created_at",
                (safe_scope, subject_hash, since),
            ).fetchall()
            if include_login_failures:
                # A pending verification reserves capacity. Once finalized, a
                # failure moves to security_events in the same transaction;
                # successful logins release their capacity without charging
                # other customers on the same network.
                failures = conn.execute(
                    """SELECT created_at FROM security_events
                       WHERE event_type='login_attempt' AND ip_address=?
                         AND success=0 AND created_at>=?
                       ORDER BY created_at LIMIT ?""",
                    (safe_subject, since, max_attempts),
                ).fetchall()
                rows = sorted(rows + failures, key=lambda row: str(row[0] or ""))
            if len(rows) >= max_attempts:
                first = _parse_iso(str(rows[0][0] or ""))
                retry_after = max(1, int((first + timedelta(minutes=window_minutes) - now).total_seconds())) if first else window_minutes * 60
                conn.rollback()
                return {
                    "allowed": False,
                    "reason": "rate_limited",
                    "limit": max_attempts,
                    "window_minutes": window_minutes,
                    "retry_after_seconds": retry_after,
                }
            reservation = conn.execute(
                "INSERT INTO security_action_attempts(scope,subject_hash,created_at) VALUES(?,?,?)",
                (safe_scope, subject_hash, now_text),
            )
            conn.commit()
            return {
                "allowed": True,
                "remaining": max_attempts - len(rows) - 1,
                "limit": max_attempts,
                "window_minutes": window_minutes,
                "claim_id": int(reservation.lastrowid),
            }
        finally:
            conn.close()
    except Exception:
        return {"allowed": False, "reason": "rate_limit_store_unavailable"}


def claim_login_attempt(db_path: str, *, ip_address: str) -> Dict[str, Any]:
    """Reserve the existing shared-IP failed-login budget before authentication."""
    return claim_rate_limit_slot(
        db_path,
        scope="auth_login",
        subject=ip_address,
        limit=8,
        minutes=15,
        include_login_failures=True,
    )


def finalize_login_attempt(
    db_path: str,
    *,
    claim_id: int,
    ip_address: str,
    success: bool,
    username: str = "",
    user_id: str = "",
    path: str = "",
    method: str = "POST",
    reason: str = "",
) -> bool:
    """Atomically replace one pending login with its audit result.

    Never hold the reservation transaction during password verification. A
    failed finalization must prevent issuing a new signed session: its pending
    reservation stays charged until the original fifteen-minute window ends.
    This operation owns the login audit event; callers must not log it again.
    """
    if type(claim_id) is not int or claim_id <= 0 or type(success) is not bool:
        return False
    address = str(ip_address or "").strip()
    if not address or not str(db_path or "").strip():
        return False
    subject_hash = hashlib.sha256(("auth_login\0" + address).encode("utf-8")).hexdigest()
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        conn.execute("PRAGMA busy_timeout=2000")
        conn.execute("BEGIN IMMEDIATE")
        pending = conn.execute(
            """SELECT created_at FROM security_action_attempts
               WHERE id=? AND scope='auth_login' AND subject_hash=?""",
            (claim_id, subject_hash),
        ).fetchone()
        now = datetime.now(timezone.utc)
        started = _parse_iso(str(pending[0] or "")) if pending else None
        if started is None or started.tzinfo is None or not (now - timedelta(minutes=15) <= started <= now):
            conn.rollback()
            return False
        conn.execute(
            """INSERT INTO security_events(
                id,event_type,severity,ip_address,user_id,username,path,method,success,reason,payload_json,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                security_event_id(), "login_attempt", "INFO" if success else "WARN",
                address, str(user_id or "")[:120], str(username or "")[:120],
                str(path or "")[:240], str(method or "POST")[:12],
                1 if success else 0, str(reason or "")[:160], "{}",
                now.isoformat(timespec="seconds"),
            ),
        )
        deleted = conn.execute(
            "DELETE FROM security_action_attempts WHERE id=? AND scope='auth_login' AND subject_hash=?",
            (claim_id, subject_hash),
        )
        if deleted.rowcount != 1:
            conn.rollback()
            return False
        conn.commit()
        return True
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def rate_limit_status(db_path: str, *, event_type: str, ip_address: str, path_like: str, limit: int, minutes: int) -> Dict[str, Any]:
    failures = count_recent_failed_events(db_path, event_type=event_type, ip_address=ip_address, path_like=path_like, minutes=minutes)
    return {
        "blocked": failures >= limit,
        "failures": failures,
        "limit": limit,
        "window_minutes": minutes,
    }


def security_summary(db_path: str, limit: int = 20) -> Dict[str, Any]:
    ensure_security_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
        total_24h = conn.execute("SELECT COUNT(*) n FROM security_events WHERE created_at>=?", (since_24h,)).fetchone()["n"]
        failed_logins_24h = conn.execute(
            "SELECT COUNT(*) n FROM security_events WHERE event_type='login_attempt' AND success=0 AND created_at>=?",
            (since_24h,),
        ).fetchone()["n"]
        csrf_failures_24h = conn.execute(
            "SELECT COUNT(*) n FROM security_events WHERE event_type='csrf_block' AND created_at>=?",
            (since_24h,),
        ).fetchone()["n"]
        suspicious_ips = [dict(r) for r in conn.execute(
            """SELECT ip_address, COUNT(*) attempts
               FROM security_events
               WHERE success=0 AND created_at>=? AND ip_address!=''
               GROUP BY ip_address
               HAVING attempts >= 3
               ORDER BY attempts DESC
               LIMIT 10""",
            (since_24h,),
        ).fetchall()]
        recent = [dict(r) for r in conn.execute(
            """SELECT event_type,severity,ip_address,username,path,method,success,reason,created_at
               FROM security_events
               ORDER BY created_at DESC
               LIMIT ?""",
            (int(limit),),
        ).fetchall()]
        return {
            "ok": True,
            "version": SECURITY_VERSION,
            "total_24h": total_24h,
            "failed_logins_24h": failed_logins_24h,
            "csrf_failures_24h": csrf_failures_24h,
            "suspicious_ips": suspicious_ips,
            "recent": recent,
            "checks": {
                "csrf": "activo",
                "rate_limiting": "activo",
                "security_headers": "activo",
                "audit_table": "security_events",
            },
        }
    finally:
        conn.close()
