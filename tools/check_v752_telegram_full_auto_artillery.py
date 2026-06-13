#!/usr/bin/env python3
"""Validate V752 Telegram automatic artillery without sending real Telegram."""
from __future__ import annotations

import importlib
import os
import re
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V753_TELEGRAM_PRODUCTION_AUTOPILOT_ENVIRONMENT_AUDIT_AND_REAL_CRON_CERTIFICATION"
CHECKS: list[tuple[str, bool, str]] = []

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(ok), str(detail or "")))


def safe_print(value: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.write(str(value).encode(encoding, errors="replace").decode(encoding, errors="replace") + "\n")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def insert_dynamic(conn: sqlite3.Connection, table: str, values: dict) -> None:
    cols = [key for key in values if key in table_columns(conn, table)]
    placeholders = ",".join("?" for _ in cols)
    conn.execute(
        f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
        [values[key] for key in cols],
    )
    conn.commit()


def static_checks() -> None:
    version = read("VERSION.txt").strip()
    app_source = read("app.py")
    engine = read("engines/telegram_delivery_engine.py")
    runner = read("tools/render_cron_telegram_tick.py")
    command_template = read("templates/admin_telegram_command_center.html")
    env_example = read(".env.example")
    env_render = read(".env.render.clean")

    check("version_v752_or_v753", version in {"V752_TELEGRAM_FULL_AUTO_ARTILLERY_PRODUCTION_CERTIFICATION", VERSION}, version)
    check("app_version_v752_or_v753", f'APP_VERSION = "{version}"' in app_source)
    check("endpoint_exists", '@app.route("/api/automation/telegram/tick"' in app_source)
    check("secret_protected", "automation_cron_result" in app_source and "AUTOMATION_SECRET" in app_source)
    check("source_automatic_cron", "source\": \"automatic_cron\"" in app_source or "'source': 'automatic_cron'" in app_source)
    check("source_manual_admin", "manual_admin" in app_source)
    check("cron_statuses", all(token in app_source for token in ("NO_DUE_JOBS", "NO_ELIGIBLE_PICKS", "OUTSIDE_PRO_WINDOW", "NO_LIVE_ALERTS", "DUPLICATE_ALREADY_SENT", "CRON_OK")))
    check("dedupe_specific", "pick_id=" in app_source and "match_id=" in app_source and "market=" in app_source and "source=\"automatic_cron\"" in app_source)
    check("dedupe_engine_specific", "telegram:{source}:{message_type}:{pick_id or date_key}:{match_id}:{market}:{target_key}:{date_key}" in engine)
    check("ultra_builder_kept", all(token in engine for token in ("_TELEGRAM_PICK_PRO_MARKER", "_premium_pick_card", "build_single_pick_message", "format_telegram_match_time_madrid")))
    check("no_raw_utc_in_builder", "kickoff_time" not in engine or "format_telegram_match_time_madrid" in engine)
    check("runner_exists", (ROOT / "tools" / "render_cron_telegram_tick.py").exists())
    check("runner_env", "PUBLIC_BASE_URL" in runner and "AUTOMATION_SECRET" in runner)
    check("runner_masks_secret", "mask_secret" in runner and "print(url" not in runner)
    check("runner_command_documented", "python tools/render_cron_telegram_tick.py" in env_example and "python tools/render_cron_telegram_tick.py" in env_render)
    check("command_center_ticks", "Resultado del" in command_template and "last_delivery_id" in command_template)
    check("command_center_discards", "discard_reasons" in command_template and "NO_DUE_JOBS" in command_template)
    check("env_docs_present", (ROOT / "reports" / "V752_TELEGRAM_RENDER_ENVIRONMENT_FINAL_RUNBOOK.md").exists())
    check("zip_builder_includes_v752", 'rel_posix.startswith("reports/V752_")' in read("tools/build_clean_release.py"))


def functional_mock_check() -> None:
    with tempfile.TemporaryDirectory(prefix="nemesis_v752_") as tmp:
        db_path = str(Path(tmp) / "database.db")
        os.environ.update({
            "DB_PATH": db_path,
            "AUTOMATION_SECRET": "v752-secret",
            "TELEGRAM_BOT_TOKEN": "123456:mock-token",
            "TELEGRAM_CHAT_ID": "-1003951459919",
            "ENABLE_TELEGRAM_AUTO": "true",
            "ENABLE_TELEGRAM_AUTOMATION": "true",
            "AUTO_SEND_TELEGRAM_PICKS": "true",
            "TELEGRAM_AUTO_SEND_ENABLED": "true",
            "MIN_SHARK_SCORE_FOR_AUTO_SEND": "1",
            "TELEGRAM_MIN_ODDS": "1.01",
            "TELEGRAM_MAX_ODDS": "9.99",
            "TELEGRAM_QUIET_START": "23:59",
            "TELEGRAM_QUIET_END": "00:01",
            "TZ": "Europe/Madrid",
            "APP_TIMEZONE": "Europe/Madrid",
            "PUBLIC_BASE_URL": "https://bot-apuestas-crgf.onrender.com",
        })
        if "app" in sys.modules:
            del sys.modules["app"]
        app_module = importlib.import_module("app")
        app_module.seed_core()

        client = app_module.app.test_client()
        check("endpoint_no_secret_403", client.get("/api/automation/telegram/tick").status_code == 403)
        response = client.get("/api/automation/telegram/tick?secret=v752-secret")
        check("endpoint_with_secret_200", response.status_code == 200, response.get_data(as_text=True)[:300])

        future = datetime.now(app_module.TZ) + timedelta(days=1, hours=3)
        match_id = "v752-match-001"
        pick_id = "v752-pick-001"
        conn = sqlite3.connect(db_path)
        insert_dynamic(conn, "matches", {
            "id": match_id,
            "competition_name": "LaLiga",
            "league_name": "LaLiga",
            "home_team": "Equipo Local V752",
            "away_team": "Equipo Visitante V752",
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
            "home_team": "Equipo Local V752",
            "away_team": "Equipo Visitante V752",
            "match_date": future.date().isoformat(),
            "kickoff_time": future.strftime("%H:%M"),
            "kickoff_iso": future.isoformat(timespec="seconds"),
            "market": "1X2",
            "selection": "Equipo Local V752 gana",
            "recommendation": "Equipo Local V752 gana",
            "odds": 1.85,
            "confidence": 88,
            "shark_score": 88,
            "risk_level": "Medio",
            "stake": 2,
            "value_percent": 6.4,
            "membership_required": "PRO",
            "status": "published",
            "created_at": app_module.now_iso(),
            "updated_at": app_module.now_iso(),
        })
        conn.close()

        sent_messages: list[dict] = []

        def fake_send(chat_id, text, message_type="manual", payload=None):
            sent_messages.append({"chat_id": chat_id, "text": text, "message_type": message_type, "payload": payload or {}})
            return {"ok": True, "sent": True, "status": "SENT", "category": "SENT", "telegram": {"result": {"message_id": 752}}}

        app_module.telegram_send_http = fake_send
        queued = app_module.enqueue_auto_pick_alerts(force=False, limit=1)
        processed = app_module.process_premium_telegram_queue(limit=3, force=True)
        check("mock_pick_queued", queued.get("inserted", 0) >= 1, queued)
        check("mock_pick_sent", processed.get("sent", 0) == 1, processed)
        queue_item = app_module.one("SELECT * FROM telegram_queue WHERE message_type='auto_pick' ORDER BY created_at DESC LIMIT 1") or {}
        check("source_automatic_cron_functional", queue_item.get("source") == "automatic_cron", queue_item)
        text = sent_messages[0]["text"] if sent_messages else ""
        check("ultra_message_functional", "PICK" in text and "PREMIUM" in text and "SHARK" in text and "Madrid" in text, text[:300])
        second = app_module.enqueue_auto_pick_alerts(force=False, limit=1)
        check("dedupe_second_tick", second.get("inserted", 0) == 0 and second.get("skipped", 0) >= 1, second)


def main() -> None:
    static_checks()
    try:
        functional_mock_check()
    except Exception as exc:
        check("functional_mock_exception", False, f"{type(exc).__name__}: {exc}")

    for name, ok, detail in CHECKS:
        safe_print(f"{'OK' if ok else 'FAIL'} {name} {detail}".rstrip())
    failed = [item for item in CHECKS if not item[1]]
    if failed:
        print(f"V752 Telegram full auto artillery check failed: {len(failed)}", file=sys.stderr)
        raise SystemExit(1)
    safe_print("V752 Telegram full auto artillery check OK")


if __name__ == "__main__":
    main()
