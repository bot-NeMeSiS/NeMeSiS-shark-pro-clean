from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V932_AUTHENTICATED_PRODUCTION_CLIENT_ADMIN_AND_REAL_SPORTS_VALUE_FINAL"
SUCCESSOR_VERSION = "V933_REFERENCE_PARITY_PRODUCT_DESIGN_SPRINT_SYSTEM_FINAL"
V934_VERSION = "V934_REFERENCE_EXACTNESS_REALTIME_SPORTS_PRODUCTION_PERFECTION_FINAL"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def create_sports_db(path: Path, app_module) -> None:
    today = app_module.today_iso()
    tomorrow = app_module.today_iso(1)
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE matches(
            id TEXT PRIMARY KEY, match_date TEXT, kickoff_time TEXT, match_time TEXT,
            kickoff_iso TEXT, competition_key TEXT, competition_name TEXT, league_name TEXT,
            country TEXT, home_team TEXT, away_team TEXT, status TEXT, minute TEXT, score TEXT,
            home_score TEXT, away_score TEXT, source TEXT, updated_at TEXT
        )"""
    )
    matches = [
        ("today", today, "23:30", "", "", "liga-real", "Liga verificada", "", "ES", "Club Norte", "Club Sur", "scheduled", "", "", "", "", "api-sports", "2026-07-11T08:00:00Z"),
        ("live", today, "22:30", "", "", "liga-real", "Liga verificada", "", "ES", "Club Este", "Club Oeste", "LIVE", "12", "0-0", "0", "0", "api-sports", "2026-07-11T08:01:00Z"),
        ("future", tomorrow, "20:45", "", "", "liga-real", "Liga verificada", "", "ES", "Club Sierra", "Club Costa", "scheduled", "", "", "", "", "api-sports", "2026-07-11T08:02:00Z"),
        ("incomplete", today, "", "", "", "", "", "", "ES", "Club Vega", "Club Prado", "scheduled", "", "", "", "", "api-sports", "2026-07-11T08:03:00Z"),
    ]
    conn.executemany("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", matches)
    conn.execute(
        """CREATE TABLE picks(
            id TEXT PRIMARY KEY, match_id TEXT, match_date TEXT, kickoff_time TEXT,
            home_team TEXT, away_team TEXT, market TEXT, selection TEXT, odds REAL,
            status TEXT, result_status TEXT, match_status TEXT, source TEXT, updated_at TEXT
        )"""
    )
    picks = [
        ("pick-valid", "future", tomorrow, "20:45", "Club Sierra", "Club Costa", "Total goles", "Mas de 2.5", 1.72, "published", "pending", "scheduled", "api-sports", "2026-07-11T08:04:00Z"),
        ("pick-no-odds", "future", tomorrow, "20:45", "Club Sierra", "Club Costa", "Total goles", "Mas de 2.5", None, "published", "pending", "scheduled", "api-sports", "2026-07-11T08:05:00Z"),
        ("pick-fake", "future", tomorrow, "20:45", "Club Sierra", "Club Costa", "Total goles", "Mas de 2.5", 1.80, "published", "pending", "scheduled", "placeholder", "2026-07-11T08:06:00Z"),
    ]
    conn.executemany("INSERT INTO picks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", picks)
    conn.commit()
    conn.close()


def main() -> int:
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    os.environ["ENABLE_AUTOMATED_RENDER_DEPLOY"] = "0"
    with tempfile.TemporaryDirectory(prefix="nemesis_v932_sports_", ignore_cleanup_errors=True) as temp_dir:
        db_path = Path(temp_dir) / "sports.sqlite"
        os.environ["DB_PATH"] = str(db_path)
        import app as app_module

        app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
        app_module.app.logger.disabled = True
        logging.disable(logging.CRITICAL)
        create_sports_db(db_path, app_module)
        original_path = app_module.DB_PATH
        original_init = app_module.initialize_once
        original_fetch = app_module.fetch_json_url
        app_module.DB_PATH = str(db_path)
        app_module._SEEDED_DB_PATH = str(db_path)
        app_module.APP_INITIALIZED = True
        app_module.initialize_once = lambda: True
        external_calls = {"count": 0}

        def blocked_external(*args, **kwargs):
            external_calls["count"] += 1
            raise AssertionError("external sports call during render")

        app_module.fetch_json_url = blocked_external
        try:
            with app_module.app.test_request_context("/"):
                summary = app_module.get_public_home_sports_summary()
                value = app_module.get_v932_real_sports_value_context(summary)
            home = app_module.app.test_client().get("/")
            runtime = app_module.app.test_client().get("/api/runtime-version").get_json(silent=True) or {}
        finally:
            app_module.fetch_json_url = original_fetch
            app_module.DB_PATH = original_path
            app_module.initialize_once = original_init

    valid_today = summary.get("valid_matches_today") or []
    valid_picks = summary.get("valid_active_picks") or []
    incomplete = summary.get("incomplete_matches") or []
    checks = {
        "version_v932_or_successor": app_module.APP_VERSION in {VERSION, SUCCESSOR_VERSION, V934_VERSION},
        "home_200": home.status_code == 200,
        "today_count_matches_list": summary.get("valid_matches_today_count") == len(valid_today) == 2,
        "complete_matches_only": all(app_module._v931_match_essentials(item).get("complete") for item in valid_today),
        "incomplete_separated": len(incomplete) == 1 and incomplete[0].get("id") == "incomplete",
        "live_real_only": len(summary.get("valid_live_events") or []) == 1,
        "pick_truth_gate": len(valid_picks) == 1 and valid_picks[0].get("id") == "pick-valid",
        "real_value_truth": value.get("real_matches_available") is True and value.get("real_live_available") is True and value.get("real_picks_available") is True,
        "last_safe_sync_present": value.get("last_safe_sync") == "2026-07-11T08:06:00Z",
        "no_external_render_call": external_calls["count"] == 0 and value.get("no_render_api_call") is True,
        "runtime_fields_safe": all(key in runtime for key in (
            "v932_real_matches_available", "v932_real_live_available",
            "v932_real_picks_available", "v932_last_safe_sync", "v932_next_required_action",
        )),
        "no_fake_data": not any("placeholder" in str(item.get("source") or "").lower() for item in valid_today + valid_picks),
    }
    failed = [name for name, ok in checks.items() if not ok]
    payload = {
        "version": VERSION,
        "ok": not failed,
        "checks": checks,
        "failed": failed,
        "valid_today": len(valid_today),
        "valid_live": len(summary.get("valid_live_events") or []),
        "valid_picks": len(valid_picks),
        "incomplete": len(incomplete),
        "external_calls": external_calls["count"],
        "production_data_written": False,
        "synthetic_test_data_isolated": True,
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
