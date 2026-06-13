#!/usr/bin/env python3
"""V754 validation: auto pick candidate window, dedupe and Cron module status.

This check never sends a real Telegram message. It replaces the HTTP sender in
the imported app with a local fake sender and uses a temporary SQLite database.
"""
from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V754_TELEGRAM_AUTO_PICK_CANDIDATE_WINDOW_DELIVERY_FIX"
V755_VERSION = "V755_TELEGRAM_PICK_CANDIDATE_NORMALIZATION_SCHEDULE_CERTIFICATION_FIX"
FUTURE_VERSION = "V756_CLIENT_APP_PREMIUM_EXPERIENCE_TOTAL_POLISH"
NEXT_VERSION = "V757_GLOBAL_APP_EXPERIENCE_TRUST_NAVIGATION_POLISH"
V758_VERSION = "V758_ADAPTIVE_DESKTOP_MOBILE_TOP_APP_EXPERIENCE"
V759_VERSION = "V759_GLOBAL_TOP_APP_MERGED_QUALITY_EXPERIENCE_RELEASE"
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
    template = read("templates/admin_telegram_command_center.html")
    runner = read("tools/render_cron_telegram_tick.py")
    version = read("VERSION.txt").strip()
    check("version_v754", version in {VERSION, V755_VERSION, FUTURE_VERSION, NEXT_VERSION, V758_VERSION, V759_VERSION}, version)
    check("app_version_v754", f'APP_VERSION = "{VERSION}"' in app_source or f'APP_VERSION = "{V755_VERSION}"' in app_source or f'APP_VERSION = "{FUTURE_VERSION}"' in app_source or f'APP_VERSION = "{NEXT_VERSION}"' in app_source or f'APP_VERSION = "{V758_VERSION}"' in app_source or f'APP_VERSION = "{V759_VERSION}"' in app_source)
    check("runner_still_v753_compatible", "X-NeMeSiS-Cron-Runner" in runner and '"runner": "render_cron"' in runner)
    check("candidate_function_exists", "def find_auto_telegram_pick_candidates" in app_source)
    check("auto_window_function_exists", "def telegram_auto_pick_window_decision" in app_source)
    check("auto_pick_quiet_hours_not_default_blocker", "TELEGRAM_AUTO_PICK_RESPECT_QUIET_HOURS" in app_source)
    check("cron_modules_split", '"summary"' in app_source and '"auto_picks"' in app_source and '"live_alerts"' in app_source)
    check("auto_candidates_endpoint", "/api/admin/telegram/auto-candidates" in app_source)
    check("command_center_candidates_block", ("Candidatos V754" in template or "Candidatos V755" in template) and "auto_picks" in template)
    check("env_defaults_documented", all(token in read(".env.example") for token in (
        "TELEGRAM_PICK_SEND_WINDOW_HOURS_BEFORE",
        "TELEGRAM_PICK_SEND_MIN_MINUTES_BEFORE",
        "TELEGRAM_SUMMARY_MORNING_WINDOW",
        "TELEGRAM_SUMMARY_EVENING_WINDOW",
    )))


def functional_check() -> None:
    with tempfile.TemporaryDirectory(prefix="nemesis_v754_") as tmp:
        db_path = str(Path(tmp) / "database.db")
        os.environ.update({
            "DB_PATH": db_path,
            "AUTOMATION_SECRET": "v754-secret",
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
            "TELEGRAM_QUIET_START": "00:00",
            "TELEGRAM_QUIET_END": "23:59",
            "TELEGRAM_AUTO_PICK_RESPECT_QUIET_HOURS": "false",
            "TELEGRAM_PICK_SEND_WINDOW_HOURS_BEFORE": "24",
            "TELEGRAM_PICK_SEND_MIN_MINUTES_BEFORE": "15",
            "TELEGRAM_PICK_WINDOW_HOURS_BEFORE": "24",
            "TELEGRAM_PICK_MIN_MINUTES_BEFORE": "15",
            "TELEGRAM_PICK_PRO_SLOTS": "00:00-23:59",
            "TELEGRAM_PICK_URGENT_MINUTES_BEFORE": "90",
            "TZ": "Europe/Madrid",
            "APP_TIMEZONE": "Europe/Madrid",
            "PUBLIC_BASE_URL": "https://bot-apuestas-crgf.onrender.com",
        })
        sys.modules.pop("app", None)
        app_module = importlib.import_module("app")
        app_module.seed_core()
        client = app_module.app.test_client()

        check("tick_no_secret_403", client.get("/api/automation/telegram/tick").status_code == 403)
        initial = client.get(
            "/api/automation/telegram/tick?secret=v754-secret&runner=render_cron",
            headers={"X-NeMeSiS-Cron-Runner": "render-cron"},
        )
        initial_payload = initial.get_json(silent=True) or {}
        check("tick_secret_200", initial.status_code == 200, initial_payload)
        check("cron_runner_detected", initial_payload.get("cron_runner_detected") is True, initial_payload)
        check("modules_present", all(k in (initial_payload.get("modules") or {}) for k in ("summary", "auto_picks", "live_alerts")), initial_payload)

        future = datetime.now(app_module.TZ) + timedelta(hours=2)
        old = datetime.now(app_module.TZ) - timedelta(hours=3)
        conn = sqlite3.connect(db_path)
        insert_dynamic(conn, "matches", {
            "id": "v754-match-future",
            "competition_name": "LaLiga",
            "league_name": "LaLiga",
            "home_team": "Local V754",
            "away_team": "Visitante V754",
            "match_date": future.date().isoformat(),
            "match_time": future.strftime("%H:%M"),
            "kickoff_time": future.strftime("%H:%M"),
            "kickoff_iso": future.isoformat(timespec="seconds"),
            "status": "upcoming",
            "created_at": app_module.now_iso(),
            "updated_at": app_module.now_iso(),
        })
        insert_dynamic(conn, "picks", {
            "id": "v754-pick-future",
            "match_id": "v754-match-future",
            "competition_name": "LaLiga",
            "league_name": "LaLiga",
            "home_team": "Local V754",
            "away_team": "Visitante V754",
            "match_date": future.date().isoformat(),
            "kickoff_time": future.strftime("%H:%M"),
            "kickoff_iso": future.isoformat(timespec="seconds"),
            "market": "1X2",
            "selection": "Local V754 gana",
            "recommendation": "Local V754 gana",
            "odds": 1.90,
            "confidence": 90,
            "shark_score": 90,
            "risk_level": "Medio",
            "stake": 2,
            "membership_required": "PRO",
            "status": "published",
            "created_at": app_module.now_iso(),
            "updated_at": app_module.now_iso(),
        })
        insert_dynamic(conn, "matches", {
            "id": "v754-match-old",
            "competition_name": "LaLiga",
            "home_team": "Old Local",
            "away_team": "Old Visitante",
            "match_date": old.date().isoformat(),
            "match_time": old.strftime("%H:%M"),
            "kickoff_time": old.strftime("%H:%M"),
            "kickoff_iso": old.isoformat(timespec="seconds"),
            "status": "upcoming",
            "created_at": app_module.now_iso(),
            "updated_at": app_module.now_iso(),
        })
        insert_dynamic(conn, "picks", {
            "id": "v754-pick-old",
            "match_id": "v754-match-old",
            "home_team": "Old Local",
            "away_team": "Old Visitante",
            "match_date": old.date().isoformat(),
            "kickoff_time": old.strftime("%H:%M"),
            "kickoff_iso": old.isoformat(timespec="seconds"),
            "market": "1X2",
            "selection": "Old Local gana",
            "odds": 1.80,
            "confidence": 90,
            "shark_score": 90,
            "risk_level": "Medio",
            "membership_required": "PRO",
            "status": "published",
            "created_at": app_module.now_iso(),
            "updated_at": app_module.now_iso(),
        })
        conn.close()

        sent_messages: list[dict] = []

        def fake_send(chat_id, text, message_type="manual", payload=None):
            sent_messages.append({"chat_id": chat_id, "text": text, "message_type": message_type, "payload": payload or {}})
            return {"ok": True, "sent": True, "status": "SENT", "category": "SENT", "telegram": {"result": {"message_id": 754}}}

        app_module.telegram_send_http = fake_send
        candidates = app_module.find_auto_telegram_pick_candidates(limit=20)
        check("future_candidate_eligible", candidates.get("eligible", 0) >= 1 and (candidates.get("next_candidate") or {}).get("sendable_now") is True, candidates)
        check("future_not_old_match", app_module.telegram_auto_pick_window_decision(app_module.one("SELECT * FROM picks WHERE id='v754-pick-future'")).get("reason") != "OLD_MATCH")
        check("old_match_detected", any(item.get("pick_id") == "v754-pick-old" and item.get("reason") == "OLD_MATCH" for item in candidates.get("discarded", [])), candidates.get("discarded"))

        tick = client.get(
            "/api/automation/telegram/tick?secret=v754-secret&runner=render_cron",
            headers={"X-NeMeSiS-Cron-Runner": "render-cron"},
        )
        payload = tick.get_json(silent=True) or {}
        modules = payload.get("modules") or {}
        check("mock_auto_pick_sent", tick.status_code == 200 and payload.get("status") == "SENT" and payload.get("sent_count") == 1, payload)
        check("auto_module_sent", (modules.get("auto_picks") or {}).get("status") == "SENT" and (modules.get("auto_picks") or {}).get("sent") == 1, modules)
        check("summary_outside_not_blocking", payload.get("status") == "SENT", payload)
        check("global_channel_received", sent_messages and sent_messages[0]["chat_id"] == os.environ["TELEGRAM_CHAT_ID"], sent_messages)
        check("premium_message_generated", sent_messages and "SHARK" in sent_messages[0]["text"] and "Madrid" in sent_messages[0]["text"], sent_messages[0]["text"][:250] if sent_messages else "")

        second = client.get(
            "/api/automation/telegram/tick?secret=v754-secret&runner=render_cron",
            headers={"X-NeMeSiS-Cron-Runner": "render-cron"},
        ).get_json(silent=True) or {}
        check("second_tick_dedupe", "DUPLICATE_ALREADY_SENT" in (second.get("discard_reasons") or []) or (second.get("modules", {}).get("auto_picks", {}).get("status") == "DUPLICATE_ALREADY_SENT"), second)

        with client.session_transaction() as sess:
            sess["user_role"] = "ADMIN"
            sess["user_id"] = "admin"
            sess["username"] = "admin"
        auto_endpoint = client.get("/api/admin/telegram/auto-candidates")
        check("auto_candidates_endpoint_admin_200", auto_endpoint.status_code == 200, auto_endpoint.get_json(silent=True))


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
        print(f"V754 Telegram auto pick candidate window delivery check failed: {len(failed)}", file=sys.stderr)
        raise SystemExit(1)
    safe_print("V754 Telegram auto pick candidate window delivery check OK")


if __name__ == "__main__":
    main()
