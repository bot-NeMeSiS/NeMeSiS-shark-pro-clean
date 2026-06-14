#!/usr/bin/env python3
"""V772 Telegram visual cards and app global polish validation."""
from __future__ import annotations

import importlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V780_VERSION = "V780_LIVE_DATA_RECOVERY_REALTIME_STABILITY_FIX"
VERSION = "V772_TELEGRAM_VISUAL_CARDS_APP_GLOBAL_POLISH_CLEANUP"
COMPATIBLE_VERSION_PREFIXES = {"V772", "V773", "V774", "V775", "V776", "V777", "V778", "V779", "V780", "V781"}
ZIP_NAME = "NeMeSiS_SHARK_PRO_V772_TELEGRAM_VISUAL_CARDS_APP_GLOBAL_POLISH_CLEANUP_RENDER_READY.zip"
sys.path.insert(0, str(ROOT))


def read(path):
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def ok(condition, message, detail=""):
    if not condition:
        raise AssertionError(f"{message}{(': ' + detail) if detail else ''}")


def assert_no_secret_literals():
    combined = "\n".join(
        read(path)
        for path in [
            ".env.example",
            ".env.render.clean",
            "engines/telegram_visual_card_engine.py",
            "engines/telegram_message_formatter.py",
            "tools/check_v772_telegram_visual_cards_app_global_polish.py",
        ]
    )
    for pattern in (r"\d{8,}:[A-Za-z0-9_-]{20,}", r"sk_live_[A-Za-z0-9]+", r"xox[baprs]-[A-Za-z0-9-]+"):
        ok(not re.search(pattern, combined), "posible secret real en archivos V772", pattern)


def static_checks():
    version = read("VERSION.txt").strip()
    app = read("app.py")
    formatter = read("engines/telegram_message_formatter.py")
    visual = read("engines/telegram_visual_card_engine.py")
    env_example = read(".env.example")
    env_render = read(".env.render.clean")
    ok(version == VERSION or version.split("_", 1)[0] in COMPATIBLE_VERSION_PREFIXES, "VERSION.txt no apunta a V772 compatible", version)
    ok(f'APP_VERSION = "{VERSION}"' in app or f'APP_VERSION = "{version}"' in app, "APP_VERSION no apunta a V772 compatible")
    ok('DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in app, "DB_PATH fue alterado")
    ok("telegram_post_send_photo" in app and "build_visual_card_for_message" in app, "sendPhoto visual no queda integrado")
    ok("visual_card_type" in app and "visual_card_payload" in app, "payload visual no queda trazable")
    ok("format_combi_message" in formatter, "formateador de combis no existe")
    ok("build_pick_visual_card_payload" in visual and "build_telegram_visual_card_png" in visual, "motor visual incompleto")
    for token in ("TELEGRAM_VISUAL_CARDS_ENABLED=true", "TELEGRAM_SEND_PICK_CARDS=true"):
        ok(token in env_example and token in env_render, "variable visual V772 no documentada", token)
    ok("Pillow==" in read("requirements.txt"), "Pillow no queda disponible para PNG en Render")
    ok("Â" not in formatter and "Ã" not in formatter, "formateador Telegram contiene mojibake")
    ok("TELEGRAM_SEND_LIVE_IMAGES=false" in env_example, "live images no quedan apagadas por defecto")
    ok("TELEGRAM_WORLD_CUP_OVERRIDE=true" in env_example, "World Cup override no queda activo por defecto")
    assert_no_secret_literals()


def engine_checks():
    from engines.telegram_activity_engine import build_telegram_activity_plan, telegram_activity_config
    from engines.telegram_message_formatter import format_combi_message, format_pick_message
    from engines.telegram_visual_card_engine import build_visual_card_for_message, telegram_visual_card_config

    os.environ["TELEGRAM_VISUAL_CARDS_ENABLED"] = "true"
    os.environ["TELEGRAM_SEND_PICK_CARDS"] = "true"
    cfg = telegram_activity_config()
    visual_cfg = telegram_visual_card_config()
    ok(cfg["visual_cards_enabled"] is True, "activity engine no lee TELEGRAM_VISUAL_CARDS_ENABLED")
    ok(visual_cfg["send_pick_cards"] is True, "visual engine no lee TELEGRAM_SEND_PICK_CARDS")
    pick = {
        "id": "p1",
        "match_id": "m1",
        "home_team": "España",
        "away_team": "Uruguay",
        "competition_name": "Mundial FIFA",
        "kickoff_iso": "2026-06-14T20:00:00+02:00",
        "market": "Más de 1.5 goles",
        "selection": "Más de 1.5 goles",
        "odds": 1.62,
        "confidence": 78,
        "risk_level": "Medio",
        "stake_units": 1.5,
    }
    text = format_pick_message(pick)
    ok("Por qué entrar:" in text and "Precaución:" in text, "pick Telegram no tiene análisis premium")
    ok("Hoy - 20:00 Madrid" in text, "hora Madrid limpia no aparece")
    combi_text = format_combi_message({"id": "c1", "picks": [pick], "total_odds": 2.4, "confidence": 74})
    ok("COMBI SHARK" in combi_text and "Cuota total" in combi_text, "combi Telegram no tiene formato premium")
    plan = build_telegram_activity_plan(picks=[pick], combis=[{"id": "c1", "picks": [pick], "total_odds": 2.4, "title": "Combi segura"}], current=None)
    kinds = {item.get("kind") for item in plan.get("candidates", [])}
    ok("pick_alert" in kinds, "plan V772 no genera candidato pick real")
    ok("combi_alert" in kinds, "plan V772 no genera candidato combi real")
    card = build_visual_card_for_message("pick_alert", {"pick": pick})
    ok(card.get("mode") in {"png", "text_fallback"} or card.get("ok"), "tarjeta visual no degrada correctamente", json.dumps(card, ensure_ascii=False, default=str)[:200])


def flask_checks():
    try:
        import flask  # noqa: F401
    except Exception:
        print("SKIP_FLASK_CHECKS_NO_FLASK")
        return
    with tempfile.TemporaryDirectory(prefix="nemesis_v772_", ignore_cleanup_errors=True) as tmp:
        os.environ.update(
            {
                "DB_PATH": str(Path(tmp) / "database.db"),
                "SECRET_KEY": "v772-local-secret",
                "AUTOMATION_SECRET": "v772-secret",
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
                "TELEGRAM_VISUAL_CARDS_ENABLED": "true",
                "TELEGRAM_SEND_PICK_CARDS": "true",
                "BACKGROUND_JOBS_ENABLED": "false",
                "SCHEDULER_ENABLED": "false",
            }
        )
        appmod = importlib.import_module("app")
        appmod.init_db()
        appmod.app.config.update(TESTING=True)
        client = appmod.app.test_client()
        ok(client.get("/api/automation/telegram/tick").status_code == 403, "cron sin secret no da 403")
        ok(client.get("/api/automation/telegram/tick?secret=v772-secret&runner=render_cron").status_code == 200, "cron con secret no da 200")
        with client.session_transaction() as sess:
            sess["user_id"] = "admin"
            sess["user_name"] = "Admin"
            sess["username"] = "admin"
            sess["user_email"] = "admin@local"
            sess["user_role"] = "ADMIN"
            sess["user_membership"] = "ADMIN"
            sess["membership"] = "ADMIN"
        for route in (
            "/",
            "/login",
            "/admin-login",
            "/api/health",
            "/api/runtime-version",
            "/admin/telegram/diagnostics",
            "/api/admin/telegram/activity-plan",
            "/api/admin/telegram/message-preview",
            "/api/admin/telegram/dedupe-status",
        ):
            response = client.get(route)
            ok(response.status_code < 500, f"{route} devuelve 500", str(response.status_code))


def release_zip_checks():
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return {"zip_checked": False, "reason": "zip aún no generado"}
    import zipfile

    forbidden = (".git/", ".venv/", "venv/", "__pycache__/", ".pytest_cache/", ".db", ".sqlite", ".sqlite3", ".log", ".zip")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    bad = [name for name in names if any(token in name or name.endswith(token) for token in forbidden)]
    ok(not bad, "ZIP V772 contiene archivos prohibidos", ", ".join(bad[:10]))
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
