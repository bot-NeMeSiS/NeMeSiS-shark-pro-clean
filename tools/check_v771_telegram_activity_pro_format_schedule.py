#!/usr/bin/env python3
"""V771 Telegram activity, formatting and Render Cron safety check."""
from __future__ import annotations

import importlib
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V771_TELEGRAM_ACTIVITY_PRO_FORMAT_SCHEDULE_FINAL"
V772_VERSION = "V772_TELEGRAM_VISUAL_CARDS_APP_GLOBAL_POLISH_CLEANUP"
V773_VERSION = "V773_DATA_MARKETPLACE_AUTOMATION_VIDEO_UX_QUALITY_POLISH"
V774_VERSION = "V774_CLIENT_SCREEN_REORGANIZATION_MADRID_TIME_TOTAL_POLISH"
V775_VERSION = "V775_MOBILE_CLIENT_APP_EXPERIENCE_TOTAL_COMPLETION"
V776_VERSION = "V776_CLIENT_INFORMATION_ARCHITECTURE_FINAL_ORDER"
V777_VERSION = "V777_CLIENT_PRODUCT_EXPERIENCE_FINAL_SYSTEM"
V778_VERSION = "V778_CLIENT_PRODUCT_ORGANIZATION_MADRID_TIME_FINAL_STABILITY"
V779_VERSION = "V779_TEAM_IDENTITY_FLAGS_CRESTS_FINAL_POLISH"
V780_VERSION = "V780_LIVE_DATA_RECOVERY_REALTIME_STABILITY_FIX"
V781_VERSION = "V781_FULL_APP_AUDIT_STABILITY_MADRID_TIME_CLEANUP"
V782_VERSION = "V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING"
sys.path.insert(0, str(ROOT))


def fail(message):
    raise AssertionError(message)


def ok(condition, message):
    if not condition:
        fail(message)


def read(path):
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def assert_no_secret_literals():
    combined = "\n".join(read(path) for path in [
        ".env.example",
        ".env.render.clean",
        "engines/telegram_activity_engine.py",
        "engines/telegram_message_formatter.py",
        "tools/render_cron_telegram_tick.py",
    ])
    forbidden = [
        r"\d{8,}:[A-Za-z0-9_-]{20,}",
        r"sk_live_[A-Za-z0-9]+",
        r"xox[baprs]-[A-Za-z0-9-]+",
    ]
    for pattern in forbidden:
        ok(not re.search(pattern, combined), f"posible secret real en archivos V771: {pattern}")


def static_checks():
    version = read("VERSION.txt").strip()
    app = read("app.py")
    ok(version in {VERSION, V772_VERSION, V773_VERSION, V774_VERSION, V775_VERSION, V776_VERSION, V777_VERSION, V778_VERSION, V779_VERSION, V780_VERSION, V781_VERSION, V782_VERSION}, "VERSION.txt no apunta a V771/V772/V773/V774/V775/V776/V777/V778/V779/V780/V781/V782/V782 compatible")
    ok(f'APP_VERSION = "{VERSION}"' in app or f'APP_VERSION = "{V772_VERSION}"' in app or f'APP_VERSION = "{V773_VERSION}"' in app or f'APP_VERSION = "{V774_VERSION}"' in app or f'APP_VERSION = "{V775_VERSION}"' in app or f'APP_VERSION = "{V776_VERSION}"' in app or f'APP_VERSION = "{V777_VERSION}"' in app or f'APP_VERSION = "{V778_VERSION}"' in app or f'APP_VERSION = "{V779_VERSION}"' in app or f'APP_VERSION = "{V780_VERSION}"' in app or f'APP_VERSION = "{V781_VERSION}"' in app or 'APP_VERSION = "V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING"' in app, "APP_VERSION no apunta a V771/V772/V773/V774/V775/V776/V777/V778/V779/V780/V781/V782/V782 compatible")
    ok('DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in app, "DB_PATH fue alterado")
    ok("/api/automation/telegram/tick" in app, "tick Telegram no existe")
    ok("AUTOMATION_SECRET" in app, "AUTOMATION_SECRET no protegido")
    ok((ROOT / "tools" / "render_cron_telegram_tick.py").exists(), "runner Render Cron no existe")
    ok((ROOT / "engines" / "telegram_activity_engine.py").exists(), "motor de actividad no existe")
    ok((ROOT / "engines" / "telegram_message_formatter.py").exists(), "formateador Telegram no existe")
    ok((ROOT / "engines" / "telegram_visual_card_engine.py").exists(), "motor visual V772 no existe")
    ok("TELEGRAM_QUIET_HOURS_ENABLED=false" in read(".env.example"), "quiet hours no queda desactivable en env example")
    ok("TELEGRAM_WORLD_CUP_OVERRIDE=true" in read(".env.example"), "World Cup override no esta en env example")
    ok("TELEGRAM_SEND_LIVE_IMAGES=false" in read(".env.example"), "live images no quedan apagadas por defecto")
    ok("TELEGRAM_VISUAL_CARDS_ENABLED=true" in read(".env.example"), "tarjetas visuales V772 no estan en env example")
    ok("/api/admin/telegram/activity-plan" in app, "endpoint activity-plan falta")
    ok("/api/admin/telegram/schedule-status" in app, "endpoint schedule-status falta")
    ok("/api/admin/telegram/message-preview" in app, "endpoint message-preview falta")
    ok("/api/admin/telegram/dedupe-status" in app, "endpoint dedupe-status falta")
    ok("v771_telegram_activity" in app, "payload V771 no queda trazable")
    ok("run_pick_grading" in app and "pick_grading" in app, "V768 pick grading no sigue conectado")
    ok("v769_highlights_content_center" in app and "/api/automation/highlights/sync" in app, "V769 highlights no siguen conectados")
    ok("/admin/automation" in app or "run_daily_autonomous_system" in app, "Automation Center/automatizacion no sigue conectado")
    assert_no_secret_literals()


def formatter_checks():
    from engines.telegram_activity_engine import (
        build_dedupe_key,
        is_quiet_hours_blocked,
        is_world_cup_override_allowed,
        telegram_activity_config,
    )
    from engines.telegram_message_formatter import (
        format_daily_summary_message,
        format_live_alert_message,
        format_pick_message,
    )

    os.environ["TELEGRAM_QUIET_HOURS_ENABLED"] = "false"
    os.environ["TELEGRAM_WORLD_CUP_OVERRIDE"] = "true"
    cfg = telegram_activity_config()
    ok(cfg["quiet_hours_enabled"] is False, "quiet hours no se puede desactivar")
    ok(cfg["world_cup_override"] is True, "World Cup override no queda activo")
    ok(is_quiet_hours_blocked("daily_summary") is False, "quiet hours bloquea aunque esta desactivado")
    ok(is_world_cup_override_allowed({"competition_name": "Mundial FIFA"}) is True, "override Mundial no detecta Mundial")

    match = {
        "id": "m1",
        "home_team": "Espana",
        "away_team": "Uruguay",
        "competition_name": "Mundial FIFA",
        "kickoff_iso": "2026-06-14T20:00:00+02:00",
        "status": "upcoming",
    }
    daily = format_daily_summary_message([match])
    live = format_live_alert_message({**match, "status": "live", "home_score": 0, "away_score": 1})
    pick = format_pick_message({**match, "market": "Mas de 1.5 goles", "selection": "Mas de 1.5 goles", "odds": 1.62, "confidence": 78, "risk_level": "Medio", "stake_units": 1.5})
    for text in (daily, live, pick):
        ok("00:00" not in text, "mensaje usa 00:00 de forma no real")
        ok("Madrid - Próximo -" not in text and "Madrid · Próximo ·" not in text, "mensaje duplica Madrid/estado/hora")
        ok("UTC" not in text, "mensaje muestra UTC")
    ok("Hoy - 20:00 Madrid" in daily, "resumen no muestra hora Madrid limpia")
    ok("ALERTA LIVE SHARK" in live and "Abrir directo" in live, "alerta live no tiene formato premium")
    ok("PICK PREMIUM SHARK" in pick and "Cuota: 1.62" in pick, "pick premium no tiene campos clave")
    keys = {
        build_dedupe_key("daily_summary", madrid_date="2026-06-14"),
        build_dedupe_key("live_alert", match_id="m1", status="10", madrid_date="2026-06-14"),
        build_dedupe_key("pick_alert", match_id="m1", pick_id="p1", market="Mas de 1.5", madrid_date="2026-06-14"),
        build_dedupe_key("result_final", match_id="m1", status="final", madrid_date="2026-06-14"),
        build_dedupe_key("highlight_available", match_id="m1", status="h1", madrid_date="2026-06-14"),
        build_dedupe_key("prematch_reminder", match_id="m1", status="60min", madrid_date="2026-06-14"),
        build_dedupe_key("evening_recap", madrid_date="2026-06-14"),
    }
    keys.add(build_dedupe_key("combi_alert", pick_id="c1", market="Combi", madrid_date="2026-06-14"))
    ok(len(keys) == 8, "dedupe no separa tipos de mensaje")


def flask_checks():
    try:
        import flask  # noqa: F401
    except Exception:
        print("SKIP_FLASK_CHECKS_NO_FLASK")
        return
    with tempfile.TemporaryDirectory(prefix="nemesis_v771_", ignore_cleanup_errors=True) as tmp:
        os.environ.update({
            "DB_PATH": str(Path(tmp) / "database.db"),
            "SECRET_KEY": "v771-local-secret",
            "AUTOMATION_SECRET": "v771-secret",
            "TELEGRAM_BOT_TOKEN": "123456:mock-token",
            "TELEGRAM_CHAT_ID": "-1003951459919",
            "TELEGRAM_BOT_USERNAME": "nemesis_mock_bot",
            "ENABLE_TELEGRAM_AUTO": "true",
            "ENABLE_TELEGRAM_AUTOMATION": "true",
            "AUTO_SEND_TELEGRAM_PICKS": "true",
            "TELEGRAM_AUTO_SEND_ENABLED": "true",
            "TELEGRAM_QUIET_HOURS_ENABLED": "false",
            "TELEGRAM_WORLD_CUP_OVERRIDE": "true",
            "TELEGRAM_SEND_LIVE_IMAGES": "false",
            "BACKGROUND_JOBS_ENABLED": "false",
            "SCHEDULER_ENABLED": "false",
        })
        appmod = importlib.import_module("app")
        appmod.init_db()
        appmod.app.config.update(TESTING=True)
        client = appmod.app.test_client()
        ok(client.get("/api/automation/telegram/tick").status_code == 403, "cron sin secret no da 403")
        cron = client.get("/api/automation/telegram/tick?secret=v771-secret&runner=render_cron")
        ok(cron.status_code == 200, f"cron con secret no da 200: {cron.status_code}")
        with client.session_transaction() as sess:
            sess["user_id"] = "admin"
            sess["user_name"] = "Admin"
            sess["username"] = "admin"
            sess["user_email"] = "admin@local"
            sess["user_role"] = "ADMIN"
            sess["user_membership"] = "ADMIN"
            sess["membership"] = "ADMIN"
        for route in (
            "/admin/telegram/command-center",
            "/api/admin/telegram/activity-plan",
            "/api/admin/telegram/schedule-status",
            "/api/admin/telegram/message-preview",
            "/api/admin/telegram/dedupe-status",
            "/api/runtime-version",
        ):
            response = client.get(route)
            ok(response.status_code == 200, f"{route} devuelve {response.status_code}")


def main():
    static_checks()
    formatter_checks()
    flask_checks()
    print("V771 Telegram activity pro format schedule check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
