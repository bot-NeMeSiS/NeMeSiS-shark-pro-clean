#!/usr/bin/env python3
"""V753 production autopilot validation without sending real Telegram."""
from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V753_TELEGRAM_PRODUCTION_AUTOPILOT_ENVIRONMENT_AUDIT_AND_REAL_CRON_CERTIFICATION"
CURRENT_VERSION = "V754_TELEGRAM_AUTO_PICK_CANDIDATE_WINDOW_DELIVERY_FIX"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: object = "") -> None:
    CHECKS.append((name, bool(ok), str(detail or "")))


def safe_print(value: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.write(str(value).encode(encoding, errors="replace").decode(encoding, errors="replace") + "\n")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def insert_dynamic(conn: sqlite3.Connection, table: str, values: dict) -> None:
    cols = [key for key in values if key in columns(conn, table)]
    conn.execute(
        f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})",
        [values[key] for key in cols],
    )
    conn.commit()


def static_checks() -> None:
    app_source = read("app.py")
    runner = read("tools/render_cron_telegram_tick.py")
    template = read("templates/admin_telegram_command_center.html")
    env_engine = read("engines/telegram_environment_engine.py")
    version = read("VERSION.txt").strip()

    check("version_v753_or_newer", version in {VERSION, CURRENT_VERSION}, version)
    check("app_version_v753_or_newer", f'APP_VERSION = "{VERSION}"' in app_source or f'APP_VERSION = "{CURRENT_VERSION}"' in app_source)
    check("environment_engine", "get_telegram_environment_audit" in env_engine and "is_telegram_auto_enabled" in env_engine)
    check("official_flags_required", all(token in env_engine for token in ("ENABLE_TELEGRAM_AUTO", "AUTO_SEND_TELEGRAM_PICKS", "TELEGRAM_AUTO_SEND_ENABLED", "ENABLE_TELEGRAM_AUTOMATION")))
    check("environment_endpoint", "/api/admin/telegram/environment-audit" in app_source)
    check("runner_header", "X-NeMeSiS-Cron-Runner" in runner and "runner=render_cron" not in runner)
    check("runner_query", '"runner": "render_cron"' in runner)
    check("cron_evidence_saved", all(token in app_source for token in ("last_cron_runner_at", "last_cron_http_status", "last_cron_source", "last_cron_sent_count", "last_cron_delivery_id", "last_cron_madrid_time", "last_cron_utc_time")))
    check("manual_trigger_admin_button", '"trigger_type": "admin_button"' in app_source)
    check("automatic_trigger_render_cron", '"trigger_type": "render_cron"' in app_source)
    check("command_center_explains_cron", "El Cron real no depende de entrar al admin" in template and "Cron real detectado" in template)
    check("command_center_environment", "Auditor" in template and "Environment V753" in template)


def functional_check() -> None:
    with tempfile.TemporaryDirectory(prefix="nemesis_v753_") as tmp:
        db_path = str(Path(tmp) / "database.db")
        os.environ.update({
            "DB_PATH": db_path,
            "AUTOMATION_SECRET": "v753-secret",
            "TELEGRAM_BOT_TOKEN": "123456:mock-token",
            "TELEGRAM_CHAT_ID": "-1003951459919",
            "TELEGRAM_BOT_USERNAME": "nemesis_mock_bot",
            "ENABLE_TELEGRAM_AUTO": "true",
            "AUTO_SEND_TELEGRAM_PICKS": "true",
            "TELEGRAM_AUTO_SEND_ENABLED": "true",
            "ENABLE_TELEGRAM_AUTOMATION": "true",
            "AUTO_GENERATE_PICKS": "true",
            "MIN_SHARK_SCORE_FOR_AUTO_SEND": "1",
            "TELEGRAM_MIN_ODDS": "1.01",
            "TELEGRAM_MAX_ODDS": "9.99",
            "TELEGRAM_QUIET_START": "23:59",
            "TELEGRAM_QUIET_END": "00:01",
            "TELEGRAM_PICK_SEND_WINDOW_HOURS_BEFORE": "48",
            "TZ": "Europe/Madrid",
            "APP_TIMEZONE": "Europe/Madrid",
            "PUBLIC_BASE_URL": "https://bot-apuestas-crgf.onrender.com",
        })
        if "app" in sys.modules:
            del sys.modules["app"]
        app_module = importlib.import_module("app")
        app_module.seed_core()

        client = app_module.app.test_client()
        check("tick_no_secret_403", client.get("/api/automation/telegram/tick").status_code == 403)
        tick = client.get(
            "/api/automation/telegram/tick?secret=v753-secret&runner=render_cron",
            headers={"X-NeMeSiS-Cron-Runner": "render-cron"},
        )
        payload = tick.get_json(silent=True) or {}
        check("tick_secret_200", tick.status_code == 200, payload)
        check("cron_runner_detected", payload.get("cron_runner_detected") is True, payload)
        check("cron_source_automatic", payload.get("last_cron_source") == "automatic_cron", payload)

        env_audit = get_env_audit(app_module)
        check("environment_audit_ok", env_audit.get("auto_flags_ok") is True and not env_audit.get("missing"), env_audit)

        future = datetime.now(app_module.TZ) + timedelta(hours=4)
        match_id = "v753-match-001"
        pick_id = "v753-pick-001"
        conn = sqlite3.connect(db_path)
        insert_dynamic(conn, "matches", {
            "id": match_id,
            "competition_name": "LaLiga",
            "league_name": "LaLiga",
            "home_team": "Equipo Local V753",
            "away_team": "Equipo Visitante V753",
            "match_date": future.date().isoformat(),
            "match_time": future.strftime("%H:%M"),
            "kickoff_time": future.strftime("%H:%M"),
            "kickoff_iso": future.isoformat(timespec="seconds"),
            "status": "upcoming",
            "created_at": app_module.now_iso(),
            "updated_at": app_module.now_iso(),
        })
        insert_dynamic(conn, "picks", {
            "id": pick_id,
            "match_id": match_id,
            "competition_name": "LaLiga",
            "league_name": "LaLiga",
            "home_team": "Equipo Local V753",
            "away_team": "Equipo Visitante V753",
            "match_date": future.date().isoformat(),
            "kickoff_time": future.strftime("%H:%M"),
            "kickoff_iso": future.isoformat(timespec="seconds"),
            "market": "1X2",
            "selection": "Equipo Local V753 gana",
            "recommendation": "Equipo Local V753 gana",
            "odds": 1.90,
            "confidence": 90,
            "shark_score": 90,
            "risk_level": "Medio",
            "stake": 2,
            "value_percent": 7.1,
            "membership_required": "PRO",
            "status": "published",
            "created_at": app_module.now_iso(),
            "updated_at": app_module.now_iso(),
        })
        conn.close()

        sent_messages: list[dict] = []

        def fake_send(chat_id, text, message_type="manual", payload=None):
            sent_messages.append({"chat_id": chat_id, "text": text, "message_type": message_type, "payload": payload or {}})
            return {"ok": True, "sent": True, "status": "SENT", "category": "SENT", "telegram": {"result": {"message_id": 753}}}

        app_module.telegram_send_http = fake_send
        queued = app_module.enqueue_auto_pick_alerts(force=False, limit=1)
        processed = app_module.process_premium_telegram_queue(limit=3, force=True)
        queue_item = app_module.one("SELECT * FROM telegram_queue WHERE message_type='auto_pick' ORDER BY created_at DESC LIMIT 1") or {}
        delivery = app_module.one("SELECT * FROM telegram_deliveries ORDER BY created_at DESC LIMIT 1") or {}
        text = sent_messages[0]["text"] if sent_messages else ""

        check("auto_pick_sent_mock", processed.get("sent") == 1 and queued.get("inserted", 0) >= 1, {"queued": queued, "processed": processed})
        check("source_automatic_cron", queue_item.get("source") == "automatic_cron", queue_item)
        check("trigger_render_cron", queue_item.get("trigger_type") == "render_cron", queue_item)
        check("delivery_id_exists", bool(delivery.get("id")), delivery)
        check("ultra_message_madrid", "PICK" in text and "PREMIUM" in text and "SHARK" in text and "Madrid" in text, text[:300])

        second = app_module.enqueue_auto_pick_alerts(force=False, limit=1)
        check("dedupe_second_tick", second.get("status") == "DUPLICATE_ALREADY_SENT" and second.get("inserted", 0) == 0, second)

        manual = app_module.enqueue_telegram_message(
            "admin_connectivity_test",
            "Test manual",
            "Manual admin test",
            chat_id=os.environ["TELEGRAM_CHAT_ID"],
            payload={"source": "manual_admin", "trigger_type": "admin_button", "target_key": "manual-v753"},
            dedupe_key=app_module.telegram_dedupe_key("admin_connectivity_test", app_module.now_iso(), os.environ["TELEGRAM_CHAT_ID"], source="manual_admin"),
            force=True,
        )
        manual_item = app_module.one("SELECT * FROM telegram_queue WHERE message_type='admin_connectivity_test' ORDER BY created_at DESC LIMIT 1") or {}
        check("manual_source_separate", manual.get("queued") and manual_item.get("source") == "manual_admin" and manual_item.get("trigger_type") == "admin_button", manual_item)


def get_env_audit(app_module) -> dict:
    return app_module.get_telegram_environment_audit()


def main() -> None:
    static_checks()
    try:
        functional_check()
    except Exception as exc:
        check("functional_exception", False, f"{type(exc).__name__}: {exc}")

    for name, ok, detail in CHECKS:
        safe_print(f"{'OK' if ok else 'FAIL'} {name} {detail}".rstrip())
    failed = [item for item in CHECKS if not item[1]]
    if failed:
        print(f"V753 Telegram production autopilot check failed: {len(failed)}", file=sys.stderr)
        raise SystemExit(1)
    safe_print("V753 Telegram production autopilot check OK")


if __name__ == "__main__":
    main()
