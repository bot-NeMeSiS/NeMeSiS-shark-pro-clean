from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_TEXT = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
BASE_TEXT = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")


def test_v729_version_is_declared():
    active_version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    assert active_version.startswith("V")
    assert f"APP_VERSION = '{active_version}'" in APP_TEXT or f'APP_VERSION = "{active_version}"' in APP_TEXT


def test_secret_key_uses_secure_helper_not_random_restart_fallback():
    secret_section = APP_TEXT.split("app = Flask", 1)[-1].split("SEED_LOCK", 1)[0]
    assert "app.secret_key = secure_secret_key()" in secret_section
    assert "secrets.token_hex(32)" not in secret_section


def test_csrf_is_available_in_base_and_enforced():
    assert 'meta name="csrf-token"' in BASE_TEXT
    assert "def enforce_security_guards" in APP_TEXT
    assert "validate_csrf(session" in APP_TEXT


def test_rate_limiting_is_applied_to_sensitive_flows():
    assert "security_rate_limit_for_request" in APP_TEXT
    assert "login_attempt" in APP_TEXT
    assert "registration_attempt" in APP_TEXT
    assert "password_reset_request" in APP_TEXT
