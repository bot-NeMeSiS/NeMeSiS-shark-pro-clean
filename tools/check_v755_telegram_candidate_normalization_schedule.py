#!/usr/bin/env python3
"""V755 Telegram candidate normalization and schedule validation.

Uses a temporary SQLite DB and a fake Telegram sender. No real message is sent.
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
VERSION = "V755_TELEGRAM_PICK_CANDIDATE_NORMALIZATION_SCHEDULE_CERTIFICATION_FIX"
V759_VERSION = "V759_GLOBAL_TOP_APP_MERGED_QUALITY_EXPERIENCE_RELEASE", "V760_SALE_READY_CLIENT_ORDER_SHARK_TELEGRAM_FIX"
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
    version = read("VERSION.txt").strip()
    check("version_v755", version in {VERSION, V759_VERSION}, version)
    check("app_version_v755", f'APP_VERSION = "{VERSION}"' in app_source or f'APP_VERSION = "{V759_VERSION}"' in app_source)
    check("v754_kept_modules", '"summary"' in app_source and '"auto_picks"' in app_source and '"live_alerts"' in app_source)
    check("normalizer_exists", "def normalize_telegram_pick_candidate" in app_source and "def normalize_match_time_madrid" in app_source)
    check("slots_config_exists", "TELEGRAM_PICK_PRO_SLOTS" in app_source and "WAITING_FOR_PRO_SLOT" in app_source)
    check("command_center_v755_table", "Candidatos V755" in template and "Diagn" in template and "Crear candidato Telegram de prueba" in template)
    check("env_v755_documented", all(token in read(".env.example") for token in (
        "TELEGRAM_PICK_WINDOW_HOURS_BEFORE",
        "TELEGRAM_PICK_MIN_MINUTES_BEFORE",
        "TELEGRAM_PICK_PRO_SLOTS",
        "TELEGRAM_PICK_URGENT_MINUTES_BEFORE",
        "TELEGRAM_SUMMARY_WINDOWS",
    )))


def functional_check() -> None:
    with tempfile.TemporaryDirectory(prefix="nemesis_v755_") as tmp:
        db_path = str(Path(tmp) / "database.db")
        os.environ.update({
            "DB_PATH": db_path,
            "SECRET_KEY": "v755-test",
            "AUTOMATION_SECRET": "v755-secret",
            "TELEGRAM_BOT_TOKEN": "123456:mock-token",
            "TELEGRAM_CHAT_ID": "-1003951459919",
            "TELEGRAM_BOT_USERNAME": "nemesis_mock_bot",
            "ENABLE_TELEGRAM_AUTO": "true",
            "ENABLE_TELEGRAM_AUTOMATION": "true",
            "AUTO_SEND_TELEGRAM_PICKS": "true",
            "TELEGRAM_AUTO_SEND_ENABLED": "true",
            "AUTO_GENERATE_PICKS": "true",
            "MIN_SHARK_SCORE_FOR_AUTO_SEND": "1",
            "TELEGRAM_MIN_ODDS": "1.01",
            "TELEGRAM_MAX_ODDS": "9.99",
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

        check("cron_no_secret_403", client.get("/api/automation/telegram/tick").status_code == 403)
        first_tick = client.get(
            "/api/automation/telegram/tick?secret=v755-secret&runner=render_cron",
            headers={"X-NeMeSiS-Cron-Runner": "render-cron"},
        )
        first_payload = first_tick.get_json(silent=True) or {}
        check("cron_secret_200", first_tick.status_code == 200, first_payload)
        check("cron_runner_detected", first_payload.get("cron_runner_detected") is True, first_payload)
        check("modules_separated", all(k in (first_payload.get("modules") or {}) for k in ("summary", "auto_picks", "live_alerts")), first_payload)

        alt = app_module.normalize_telegram_pick_candidate({
            "home_team": "Alt Local",
            "away_team": "Alt Visitante",
            "match_date": datetime.now(app_module.TZ).date().isoformat(),
            "match_hour": (datetime.now(app_module.TZ) + timedelta(hours=2)).strftime("%H:%M"),
            "prediction": "Over 2.5",
            "best_odd": "1,85",
            "confidence": 82,
            "status": "published",
        })
        alt_diag = alt.get("_telegram_candidate") or {}
        check("alternate_fields_normalized", alt.get("market") == "Más de 2.5 goles" and float(alt.get("odds")) == 1.85 and bool(alt_diag.get("market_field")), alt_diag)

        no_odds = app_module.normalize_telegram_pick_candidate({
            "home_team": "No Odds Local",
            "away_team": "No Odds Visitante",
            "match_date": datetime.now(app_module.TZ).date().isoformat(),
            "match_time": (datetime.now(app_module.TZ) + timedelta(hours=2)).strftime("%H:%M"),
            "prediction": "Ambos marcan",
            "confidence": 84,
            "status": "published",
        })
        no_odds_send = app_module.telegram_pick_sendability(no_odds)
        check("missing_odds_warning_not_fatal", no_odds_send.get("sendable") is True and "MISSING_ODDS_WARNING" in (no_odds_send.get("reason_codes") or []), no_odds_send)

        no_market_send = app_module.telegram_pick_sendability({
            "home_team": "Sin Mercado Local",
            "away_team": "Sin Mercado Visitante",
            "match_date": datetime.now(app_module.TZ).date().isoformat(),
            "match_time": (datetime.now(app_module.TZ) + timedelta(hours=2)).strftime("%H:%M"),
            "odds": 1.8,
            "confidence": 85,
            "status": "published",
        })
        check("missing_market_blocks", no_market_send.get("sendable") is False and "MISSING_MARKET" in (no_market_send.get("reason_codes") or []), no_market_send)

        future = datetime.now(app_module.TZ) + timedelta(hours=2)
        old = datetime.now(app_module.TZ) - timedelta(hours=4)
        too_early = datetime.now(app_module.TZ) + timedelta(hours=30)
        conn = sqlite3.connect(db_path)
        for suffix, dt, status in (
            ("future", future, "telegram_test"),
            ("old", old, "published"),
            ("early", too_early, "published"),
        ):
            match_id = f"v755-match-{suffix}"
            pick_id = f"v755-pick-{suffix}"
            insert_dynamic(conn, "matches", {
                "id": match_id,
                "competition_name": "LaLiga",
                "home_team": f"Local {suffix}",
                "away_team": f"Visitante {suffix}",
                "match_date": dt.date().isoformat(),
                "match_time": dt.strftime("%H:%M"),
                "kickoff_time": dt.strftime("%H:%M"),
                "kickoff_iso": dt.isoformat(timespec="seconds"),
                "status": "upcoming",
                "created_at": app_module.now_iso(),
                "updated_at": app_module.now_iso(),
            })
            insert_dynamic(conn, "picks", {
                "id": pick_id,
                "match_id": match_id,
                "competition_name": "LaLiga",
                "home_team": f"Local {suffix}",
                "away_team": f"Visitante {suffix}",
                "match_date": dt.date().isoformat(),
                "kickoff_time": dt.strftime("%H:%M"),
                "kickoff_iso": dt.isoformat(timespec="seconds"),
                "market": "Más de 1.5 goles",
                "selection": "Más de 1.5 goles",
                "odds": 1.80,
                "confidence": 90,
                "shark_score": 90,
                "risk_level": "Medio",
                "membership_required": "PRO",
                "status": status,
                "source": "telegram_test_candidate" if status == "telegram_test" else "v755_check",
                "created_at": app_module.now_iso(),
                "updated_at": app_module.now_iso(),
            })
        conn.close()

        audit = app_module.find_auto_telegram_pick_candidates(limit=20)
        check("future_plus_2h_eligible", audit.get("eligible", 0) >= 1 and (audit.get("next_candidate") or {}).get("sendable_now") is True, audit)
        check("old_match_real", any(item.get("pick_id") == "v755-pick-old" and item.get("reason") in {"OLD_MATCH", "MATCH_STARTED"} for item in audit.get("discarded", [])), audit.get("discarded"))
        check("too_early_has_next_window", any(item.get("pick_id") == "v755-pick-early" and item.get("reason") == "TOO_EARLY" and item.get("next_send_window_madrid") for item in audit.get("discarded", [])), audit.get("discarded"))
        check("global_destination_used", (audit.get("next_candidate") or {}).get("destination", "").startswith("-1***"), audit.get("next_candidate"))

        sent_messages: list[dict] = []

        def fake_send(chat_id, text, message_type="manual", payload=None):
            sent_messages.append({"chat_id": chat_id, "text": text, "message_type": message_type, "payload": payload or {}})
            return {"ok": True, "sent": True, "status": "SENT", "category": "SENT", "telegram": {"result": {"message_id": 755}}}

        app_module.telegram_send_http = fake_send
        tick = client.get(
            "/api/automation/telegram/tick?secret=v755-secret&runner=render_cron",
            headers={"X-NeMeSiS-Cron-Runner": "render-cron"},
        )
        payload = tick.get_json(silent=True) or {}
        check("auto_pick_sent", payload.get("status") == "SENT" and payload.get("sent_count") == 1, payload)
        check("premium_message_no_raw_iso", sent_messages and "SHARK" in sent_messages[0]["text"] and "T" not in sent_messages[0]["text"][:260], sent_messages[0]["text"][:300] if sent_messages else "")
        second = client.get(
            "/api/automation/telegram/tick?secret=v755-secret&runner=render_cron",
            headers={"X-NeMeSiS-Cron-Runner": "render-cron"},
        ).get_json(silent=True) or {}
        check("second_tick_no_duplicate", second.get("sent_count") == 0 and "DUPLICATE_ALREADY_SENT" in (second.get("discard_reasons") or []), second)

        with client.session_transaction() as sess:
            sess["user_role"] = "ADMIN"
            sess["user_id"] = "admin"
            sess["username"] = "admin"
        candidates_endpoint = client.get("/api/admin/telegram/auto-candidates")
        candidates_json = candidates_endpoint.get_json(silent=True) or {}
        check("auto_candidates_endpoint_detail", candidates_endpoint.status_code == 200 and "reviewed_items" in (candidates_json.get("auto_candidates") or {}), candidates_json)


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
        print(f"V755 Telegram candidate normalization schedule check failed: {len(failed)}", file=sys.stderr)
        raise SystemExit(1)
    safe_print("V755 Telegram candidate normalization schedule check OK")


if __name__ == "__main__":
    main()
