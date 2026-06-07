from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_TEXT = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")


def test_secret_key_has_no_obvious_demo_fallback():
    forbidden = [
        "secret123",
        "change-me",
        "dev-secret",
        "default-secret",
        "nemesis-shark-pro-local-session-key",
    ]
    found = [token for token in forbidden if token in APP_TEXT]
    assert not found, f"Fallback inseguro de SECRET_KEY detectado: {found}"


def test_security_events_table_or_security_endpoint_exists():
    assert "security_events" in APP_TEXT or "/api/security/summary" in APP_TEXT
