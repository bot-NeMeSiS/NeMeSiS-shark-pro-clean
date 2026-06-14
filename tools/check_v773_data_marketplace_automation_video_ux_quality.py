#!/usr/bin/env python3
"""V773 Data Marketplace, Automation Center and video UX quality validation."""
from __future__ import annotations

import importlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V773_DATA_MARKETPLACE_AUTOMATION_VIDEO_UX_QUALITY_POLISH"
V774_VERSION = "V774_CLIENT_SCREEN_REORGANIZATION_MADRID_TIME_TOTAL_POLISH"
V775_VERSION = "V775_MOBILE_CLIENT_APP_EXPERIENCE_TOTAL_COMPLETION"
V776_VERSION = "V776_CLIENT_INFORMATION_ARCHITECTURE_FINAL_ORDER"
V777_VERSION = "V777_CLIENT_PRODUCT_EXPERIENCE_FINAL_SYSTEM"
V778_VERSION = "V778_CLIENT_PRODUCT_ORGANIZATION_MADRID_TIME_FINAL_STABILITY"
V779_VERSION = "V779_TEAM_IDENTITY_FLAGS_CRESTS_FINAL_POLISH"
V780_VERSION = "V780_LIVE_DATA_RECOVERY_REALTIME_STABILITY_FIX"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
sys.path.insert(0, str(ROOT))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def ok(condition, message, detail=""):
    if not condition:
        raise AssertionError(f"{message}{(': ' + str(detail)) if detail else ''}")


def static_checks():
    app = read("app.py")
    version = read("VERSION.txt").strip()
    css = read("static/app.css")
    env_example = read(".env.example")
    env_render = read(".env.render.clean")
    ok(version in {VERSION, V774_VERSION, V775_VERSION, V776_VERSION, V777_VERSION, V778_VERSION, V779_VERSION, V780_VERSION}, "VERSION.txt no apunta a V773/V774/V775/V776/V777/V778/V779/V780 compatible", version)
    ok(f'APP_VERSION = "{VERSION}"' in app or f'APP_VERSION = "{V774_VERSION}"' in app or f'APP_VERSION = "{V775_VERSION}"' in app or f'APP_VERSION = "{V776_VERSION}"' in app or f'APP_VERSION = "{V777_VERSION}"' in app or f'APP_VERSION = "{V778_VERSION}"' in app or f'APP_VERSION = "{V779_VERSION}"' in app or f'APP_VERSION = "{V780_VERSION}"' in app, "APP_VERSION no apunta a V773/V774/V775/V776/V777/V778/V779/V780 compatible")
    ok('DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in app, "DB_PATH fue alterado")
    for path in (
        "engines/data_marketplace_engine.py",
        "engines/automation_orchestrator_engine.py",
        "engines/app_experience_quality_engine.py",
        "templates/admin_data_marketplace.html",
        "templates/admin_automation_center.html",
        "templates/admin_app_experience_quality.html",
    ):
        ok((ROOT / path).exists(), "archivo V773 faltante", path)
    for route in (
        "/admin/data-marketplace",
        "/api/admin/data-marketplace/export/<export_key>",
        "/admin/automation-center",
        "/api/admin/automation-center/summary",
        "/admin/app-experience-quality",
    ):
        ok(route in app, "ruta V773 no registrada", route)
    for token in (
        "DATA_MARKETPLACE_ENABLED=true",
        "DATA_MARKETPLACE_EXPORT_MAX_ROWS=5000",
        "AUTOMATION_CENTER_ENABLED=true",
        "APP_EXPERIENCE_QUALITY_CENTER=true",
    ):
        ok(token in env_example and token in env_render, "variable V773 no documentada", token)
    for token in (".v773-quality-hero", ".v773-admin-rail", ".nav-clean", ".shark-widget"):
        ok(token in css, "CSS V773 incompleto", token)
    bad_templates = []
    for p in (ROOT / "templates").glob("*.html"):
        text = p.read_text(encoding="utf-8", errors="replace")
        if any(marker in text for marker in ("Ã", "Â", "â€™", "â€œ", "â€", "â†")):
            bad_templates.append(p.name)
    ok(not bad_templates, "templates con mojibake", bad_templates[:10])
    combined = "\n".join(read(p) for p in [".env.example", ".env.render.clean", "engines/data_marketplace_engine.py", "engines/automation_orchestrator_engine.py"])
    for pattern in (r"\d{8,}:[A-Za-z0-9_-]{20,}", r"sk_live_[A-Za-z0-9]+", r"xox[baprs]-[A-Za-z0-9-]+"):
        ok(not re.search(pattern, combined), "posible secret real en archivos V773", pattern)


def engine_checks():
    from engines.app_experience_quality_engine import build_v773_app_experience_quality_snapshot
    from engines.automation_orchestrator_engine import build_automation_center_summary
    from engines.data_marketplace_engine import privacy_guard_export, run_data_marketplace_export, build_data_marketplace_summary

    guard = privacy_guard_export(["id", "market", "email", "telegram_chat_id", "token"])
    ok(not guard["ok"], "privacy guard no bloquea columnas sensibles")
    ok("email" in guard["blocked_columns"], "email no queda bloqueado")
    with tempfile.TemporaryDirectory(prefix="nemesis_v773_engine_", ignore_cleanup_errors=True) as tmp:
        db_path = str(Path(tmp) / "database.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE picks (id TEXT, home_team TEXT, away_team TEXT, competition_name TEXT, market TEXT, selection TEXT, odds REAL, status TEXT, result_status TEXT, profit REAL, created_at TEXT)")
        conn.execute("INSERT INTO picks VALUES ('p1','España','Portugal','Mundial','1X2','España',1.85,'closed','won',8.5,'2026-06-14T10:00:00+02:00')")
        conn.execute("CREATE TABLE sportsdb_highlights (id TEXT, match_id TEXT, home_team TEXT, away_team TEXT, title TEXT, source TEXT, original_url TEXT, created_at TEXT)")
        conn.execute("INSERT INTO sportsdb_highlights VALUES ('h1','m1','España','Portugal','Resumen','TheSportsDB','https://example.invalid','2026-06-14T10:00:00+02:00')")
        conn.commit(); conn.close()
        summary = build_data_marketplace_summary(db_path, VERSION)
        ok(summary["readiness_score"] >= 70, "summary Data Marketplace bajo", summary)
        export = run_data_marketplace_export(db_path, "market-performance", actor="test", app_version=VERSION)
        ok(export.get("ok") and "segmento" in export.get("content", ""), "export market-performance falla", export)
        report = run_data_marketplace_export(db_path, "monthly-report", fmt="json", actor="test", app_version=VERSION)
        ok(report.get("ok") and report.get("format") == "json", "monthly-report JSON falla", report)
        automation = build_automation_center_summary(db_path, VERSION, env={"AUTOMATION_SECRET": "x", "PUBLIC_BASE_URL": "https://example.invalid", "TELEGRAM_BOT_TOKEN": "123456:mock-token", "TELEGRAM_CHAT_ID": "-100123", "TZ": "Europe/Madrid", "APP_TIMEZONE": "Europe/Madrid"}, state={})
        ok(automation["jobs_total"] >= 5 and automation["readiness_score"] >= 80, "automation center no queda listo", automation)
    registered_for_quality = [
        "/", "/app", "/calendar", "/partidos", "/live", "/picks", "/combis",
        "/mercados", "/highlights", "/track-record", "/shark", "/menu",
        "/admin/control-center", "/admin/telegram/command-center", "/admin/data-marketplace",
        "/admin/automation-center", "/admin/app-experience-quality",
        "/admin/final-certification", "/admin/highlights-center",
    ]
    quality = build_v773_app_experience_quality_snapshot(VERSION, registered_for_quality, str(ROOT / "templates"), str(ROOT / "static/app.css"))
    ok(quality["score"] >= 88, "quality snapshot demasiado bajo", quality)


def flask_checks():
    try:
        import flask  # noqa: F401
    except Exception:
        print("SKIP_FLASK_CHECKS_NO_FLASK")
        return
    with tempfile.TemporaryDirectory(prefix="nemesis_v773_flask_", ignore_cleanup_errors=True) as tmp:
        os.environ.update({
            "DB_PATH": str(Path(tmp) / "database.db"),
            "SECRET_KEY": "v773-local-secret",
            "AUTOMATION_SECRET": "v773-secret",
            "PUBLIC_BASE_URL": "https://example.invalid",
            "TELEGRAM_BOT_TOKEN": "123456:mock-token",
            "TELEGRAM_CHAT_ID": "-1003951459919",
            "TELEGRAM_BOT_USERNAME": "nemesis_mock_bot",
            "ENABLE_TELEGRAM_AUTO": "true",
            "ENABLE_TELEGRAM_AUTOMATION": "true",
            "AUTO_SEND_TELEGRAM_PICKS": "true",
            "TELEGRAM_AUTO_SEND_ENABLED": "true",
            "TELEGRAM_QUIET_HOURS_ENABLED": "false",
            "TELEGRAM_WORLD_CUP_OVERRIDE": "true",
            "TELEGRAM_VISUAL_CARDS_ENABLED": "true",
            "DATA_MARKETPLACE_ENABLED": "true",
            "AUTOMATION_CENTER_ENABLED": "true",
            "BACKGROUND_JOBS_ENABLED": "false",
            "SCHEDULER_ENABLED": "false",
            "TZ": "Europe/Madrid",
            "APP_TIMEZONE": "Europe/Madrid",
        })
        appmod = importlib.import_module("app")
        appmod.init_db()
        appmod.app.config.update(TESTING=True)
        client = appmod.app.test_client()
        registered = {str(rule.rule) for rule in appmod.app.url_map.iter_rules()}
        for route in (
            "/admin/data-marketplace",
            "/admin/export-center",
            "/admin/business-intelligence",
            "/admin/automation-center",
            "/admin/app-experience-quality",
            "/api/admin/data-marketplace/export/<export_key>",
        ):
            ok(route in registered, "ruta Flask V773 faltante", route)
        ok(client.get("/api/automation/telegram/tick").status_code == 403, "cron Telegram sin secret no da 403")
        ok(client.get("/api/automation/telegram/tick?secret=v773-secret&runner=render_cron").status_code == 200, "cron Telegram con secret no da 200")
        with client.session_transaction() as sess:
            sess["user_id"] = "admin"
            sess["user_name"] = "Admin"
            sess["username"] = "admin"
            sess["user_email"] = "admin@local"
            sess["user_role"] = "ADMIN"
            sess["user_membership"] = "ADMIN"
            sess["membership"] = "ADMIN"
        for route in (
            "/admin/data-marketplace",
            "/admin/automation-center",
            "/admin/app-experience-quality",
            "/api/admin/data-marketplace/summary",
            "/api/admin/automation-center/summary",
            "/api/admin/app-experience-quality",
            "/api/admin/data-marketplace/export/closed-picks",
        ):
            response = client.get(route)
            ok(response.status_code < 500, f"{route} devuelve 500", response.status_code)


def release_zip_checks():
    zip_path = ROOT.parent / "releases" / ZIP_NAME
    if not zip_path.exists():
        zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return {"zip_checked": False, "reason": "zip aún no generado"}
    import zipfile
    forbidden_parts = (".git/", ".venv/", "venv/", "__pycache__/", ".pytest_cache/", "logs/", "backups/")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    bad = [name for name in names if any(part in name for part in forbidden_parts) or name.endswith((".db", ".sqlite", ".sqlite3", ".log", ".mp4", ".zip"))]
    ok(not bad, "ZIP V773 contiene archivos prohibidos", bad[:10])
    return {"zip_checked": True, "files": len(names)}


def main():
    static_checks()
    engine_checks()
    flask_checks()
    zip_result = release_zip_checks()
    print(json.dumps({"ok": True, "version": VERSION, "zip": zip_result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
