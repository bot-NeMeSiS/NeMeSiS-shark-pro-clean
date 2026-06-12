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
