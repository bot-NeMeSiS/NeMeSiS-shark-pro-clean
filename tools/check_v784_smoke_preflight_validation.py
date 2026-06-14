#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")


def require(cond: bool, msg: str) -> None:
    if not cond:
        fail(msg)


def main() -> None:
    require(VERSION.startswith(("V784_SMOKE_PREFLIGHT_VALIDATION_FOUNDATION", "V785_MEMBERSHIP_STRIPE_FLOW_PRICE_POLISH", "V786_STRIPE_CHECKOUT_RETURN_WEBHOOK_STATUS_POLISH","V787_LEGAL_COMPLIANCE_RESPONSIBLE_SUBSCRIPTION_READY","V788_LEGAL_COMPLIANCE_LIVE_READABILITY_TOTAL_POLISH", "V789_REAL_LAUNCH_CERTIFICATION_COMMAND_CENTER", "V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH", "V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL")), f"VERSION inesperada: {VERSION}")
    app = read("app.py")
    req = read("requirements.txt")
    smoke = read("tools/smoke_flask_real_routes.py")
    preflight = read("tools/render_preflight_check.py")
    runbook = read("reports/V784_SMOKE_PREFLIGHT_VALIDATION_FOUNDATION_REPORT.md")
    continuation = read("CHATGPT_CONTINUATION_REPORT.md")

    require('APP_VERSION = "V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL"' in app or 'APP_VERSION = "V788_LEGAL_COMPLIANCE_LIVE_READABILITY_TOTAL_POLISH"' in app or 'APP_VERSION = "V787_LEGAL_COMPLIANCE_RESPONSIBLE_SUBSCRIPTION_READY"' in app or 'APP_VERSION = "V786_STRIPE_CHECKOUT_RETURN_WEBHOOK_STATUS_POLISH"' in app or 'APP_VERSION = "V785_MEMBERSHIP_STRIPE_FLOW_PRICE_POLISH"' in app or 'APP_VERSION = "V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL"' in app or 'APP_VERSION = "V783_HOME_MEMBERSHIP_CLIENT_EXPERIENCE_COMPACT_FINAL"' in app, "APP_VERSION no actualizado")
    for token in ["Flask==", "gunicorn==", "Werkzeug==", "Jinja2==", "stripe"]:
        require(token in req, f"requirements.txt no conserva dependencia: {token}")

    for token in ["app.test_client()", "PAYMENTS_ENABLED", "ENABLE_LIVE_API", "STRIPE_ROUTES", "failed_routes"]:
        require(token in smoke, f"smoke Flask real incompleto: {token}")
    require("Flask no está instalado" in smoke, "smoke no explica dependencia Flask faltante")

    for token in ["urllib.request", "/api/runtime-version", "/api/live/diagnostics", "onrender.com"]:
        require(token in preflight, f"preflight Render incompleto: {token}")

    for token in ["V784", "smoke Flask real", "preflight Render", "requirements.txt", "no toca Telegram"]:
        require(token in runbook, f"reporte V784 incompleto: {token}")
    require("V784_SMOKE_PREFLIGHT_VALIDATION_FOUNDATION" in continuation, "continuation report no actualizado")

    print("OK V784 smoke/preflight validation foundation")


if __name__ == "__main__":
    main()
