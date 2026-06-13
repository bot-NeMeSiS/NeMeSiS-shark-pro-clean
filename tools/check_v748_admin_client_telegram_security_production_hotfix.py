#!/usr/bin/env python3
"""V748 hotfix validation for admin, client, Telegram, security and routes."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


def main() -> int:
    app_text = read("app.py")
    base = read("templates/base.html")
    admin_data = read("templates/admin_data_center.html")
    admin_sync = read("templates/admin_matches_sync.html")
    version = read("VERSION.txt").strip()
    with tempfile.TemporaryDirectory(prefix="nemesis_v748_check_", ignore_cleanup_errors=True) as tmp:
        os.environ.setdefault("SECRET_KEY", "v748-hotfix-check")
        os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
        os.environ.setdefault("SCHEDULER_ENABLED", "false")
        os.environ["AUTOMATION_SECRET"] = "v748-secret"
        os.environ["DB_PATH"] = str(Path(tmp) / "database.db")
        import app as app_module  # noqa: WPS433

        client = app_module.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = "admin-check"
            sess["user_role"] = "ADMIN"
            sess["user_email"] = "admin@example.com"
        admin_statuses = {
            "/admin/data-center": client.get("/admin/data-center").status_code,
            "/admin/matches-sync": client.get("/admin/matches-sync").status_code,
            "/api/admin/control-center": client.get("/api/admin/control-center").status_code,
        }
        client2 = app_module.app.test_client()
        blocked = {
            "/api/diagnostics": client2.get("/api/diagnostics").status_code,
            "/api/cache/status": client2.get("/api/cache/status").status_code,
            "/api/matches/diagnostics": client2.get("/api/matches/diagnostics").status_code,
            "/api/odds/diagnostics": client2.get("/api/odds/diagnostics").status_code,
            "/api/profile": client2.get("/api/profile").status_code,
            "/api/telegram/auto-run": client2.get("/api/telegram/auto-run").status_code,
        }
        cron_with_secret = client2.get("/api/telegram/auto-run?secret=v748-secret").status_code
        partidos_rules = [str(rule.rule) for rule in app_module.app.url_map.iter_rules() if str(rule.rule) == "/partidos"]
        telegram_schema = app_module.telegram_delivery_memory_schema_status()
    checks = {
        "version_v748": version in {
            "V748_ADMIN_CLIENT_TELEGRAM_SECURITY_PRODUCTION_HOTFIX",
            "V749_TELEGRAM_AUTO_DELIVERY_MADRID_TIME_PRODUCTION_FIX",
            "V749B_RENDER_CRON_SIMPLE_RUNNER_FINAL_FIX",
            "V750_CLIENT_LIVE_DAY_RELEVANCE_MADRID_RESULT_POLISH",
            "V751_TELEGRAM_PICK_ULTRA_PRO_MESSAGE_EXPERIENCE",
            "V752_TELEGRAM_FULL_AUTO_ARTILLERY_PRODUCTION_CERTIFICATION",
            "V753_TELEGRAM_PRODUCTION_AUTOPILOT_ENVIRONMENT_AUDIT_AND_REAL_CRON_CERTIFICATION",
            "V754_TELEGRAM_AUTO_PICK_CANDIDATE_WINDOW_DELIVERY_FIX", "V755_TELEGRAM_PICK_CANDIDATE_NORMALIZATION_SCHEDULE_CERTIFICATION_FIX", "V756_CLIENT_APP_PREMIUM_EXPERIENCE_TOTAL_POLISH", "V757_GLOBAL_APP_EXPERIENCE_TRUST_NAVIGATION_POLISH", "V758_ADAPTIVE_DESKTOP_MOBILE_TOP_APP_EXPERIENCE", "V759_GLOBAL_TOP_APP_MERGED_QUALITY_EXPERIENCE_RELEASE", "V760_SALE_READY_CLIENT_ORDER_SHARK_TELEGRAM_FIX",
        },
        "partidos_not_duplicated": len(partidos_rules) == 1,
        "admin_templates_no_tilde_variable": "matches_dÃ­agnostics" not in admin_data and "matches_dÃ­agnostics" not in admin_sync,
        "shark_briefing_signature_accepts_context": "def build_daily_briefing(user=None, favorites=None, recommendations=None, picks=None, live_matches=None, upcoming=None, membership=None)" in app_text,
        "api_admin_control_center_exists": "/api/admin/control-center" in app_text,
        "admin_routes_200": all(code == 200 for code in admin_statuses.values()),
        "technical_apis_blocked": all(code in {401, 403} for code in blocked.values()),
        "telegram_auto_run_with_secret_responds": cron_with_secret == 200,
        "membership_temporary_columns": all(token in app_text for token in ["membership_started_at", "membership_expires_at", "membership_note", "membership_admin_granted"]),
        "telegram_schema_ok": bool(telegram_schema.get("ok")),
        "admin_nav_blocks": all(token in base for token in ["Control", "Clientes", "Membres", "Picks", "Telegram", "Datos", "QA/Venta", "Vista cliente", "Salir"]),
        "release_builder_excludes_forbidden": all(token in read("tools/build_clean_release.py") for token in [".git", ".venv", "__pycache__", ".db", ".zip"]),
    }
    result = {
        "ok": all(checks.values()),
        "version": version,
        "checks": checks,
        "admin_statuses": admin_statuses,
        "blocked_statuses": blocked,
        "cron_with_secret": cron_with_secret,
        "partidos_rules": len(partidos_rules),
        "telegram_schema": telegram_schema,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
