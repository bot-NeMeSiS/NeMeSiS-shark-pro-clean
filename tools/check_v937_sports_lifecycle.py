from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import sys
import tempfile

from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as app_module
from engines.v934_realtime_sports_engine import build_realtime_snapshot, normalize_match
from engines.v935_launch_trust_engine import normalize_match_lifecycle

VERSION = "V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL"
errors = []


def text(relative):
    path = ROOT / relative
    if not path.exists():
        errors.append(f"missing:{relative}")
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


if (ROOT / "VERSION.txt").read_bytes().startswith(b"\xef\xbb\xbf"):
    errors.append("VERSION.txt:BOM")
if text("VERSION.txt").strip() != VERSION or text("APP_VERSION").strip() != VERSION:
    errors.append("version_identity")

app_source = text("app.py")
base_source = text("templates/base.html")
component = text("templates/components/v937_sports_lifecycle.html")
ui = text("templates/components/v933_ui.html")

for marker in (
    "get_v937_nemesis_data_confidence",
    "get_v937_attention_priority",
    "get_v937_pick_learning",
    "Mide calidad del dato, no probabilidad de ganar",
    "NEMESIS_CACHE_V937",
):
    if marker not in app_source:
        errors.append(f"app:{marker}")

for marker in (
    "data_confidence_badge",
    "data_confidence_panel",
    "attention_priority",
    "lifecycle_story",
    "professional_pick_brief",
    "learning_receipt",
):
    if marker not in component:
        errors.append(f"component:{marker}")

for marker in ("data_confidence_badge(match", "data_confidence_badge(pick", "attention_priority(match"):
    if marker not in ui:
        errors.append(f"cards:{marker}")

for asset in ("v937-sports-lifecycle.css", "v937-sports-lifecycle.js"):
    if base_source.count(asset) != 1:
        errors.append(f"base_asset:{asset}")

template_markers = {
    "templates/calendar.html": "lifecycle_story",
    "templates/live.html": "lifecycle_story",
    "templates/picks.html": "data_confidence_panel",
    "templates/match_detail.html": "data_confidence_panel",
    "templates/track_record.html": "learning_receipt",
    "templates/shark.html": "no recomiendo una selección hoy",
    "templates/admin_data_trust_center.html": "Índice de Confianza NeMeSiS",
}
for path, marker in template_markers.items():
    if marker not in text(path):
        errors.append(f"template:{path}:{marker}")

if "pixel_perfect_claim_allowed\": True" in app_source:
    errors.append("unsafe_pixel_perfect_claim")

status_cases = (
    ({"strStatus": "Match Finished"}, "FINALIZADO"),
    ({"strStatus": "Not Started"}, "PROGRAMADO"),
    ({"strStatus": "Match Not Started"}, "PROGRAMADO"),
    ({"strStatus": "1H"}, "LIVE"),
    ({"strProgress": "63"}, "LIVE"),
    ({"strStatus": "Match Postponed"}, "SUSPENDIDO"),
    ({}, "PROGRAMADO"),
)
for event, expected in status_cases:
    actual = app_module.sportsdb_match_status(event)
    if actual != expected:
        errors.append(f"sportsdb_status:{event}:{actual}!={expected}")

if app_module.sportsdb_score(0, 1) != "0-1":
    errors.append("sportsdb_zero_score_lost")

generic_live = {
    "id": "v937-generic-live",
    "home_team": "Regression Home",
    "away_team": "Regression Away",
    "competition_name": "Regression League",
    "match_date": app_module.today_iso(),
    "kickoff_time": "20:00",
    "source": "isolated_test_fixture",
    "updated_at": app_module.now_iso(),
    "status": "LIVE",
}
if app_module.canonical_match_status(generic_live).get("is_live"):
    errors.append("generic_live_without_evidence_exposed")
if app_module.canonical_match_status({**generic_live, "home_score": 0, "away_score": 0}).get("key") != "LIVE":
    errors.append("confirmed_zero_zero_live_rejected")
if normalize_match_lifecycle(generic_live) != "INCOMPLETE":
    errors.append("v935_generic_live_without_evidence_exposed")
if normalize_match_lifecycle({**generic_live, "home_score": 0, "away_score": 0}) != "LIVE":
    errors.append("v935_confirmed_zero_zero_live_rejected")
normalized_generic = normalize_match(generic_live)
if not normalized_generic or normalized_generic.get("is_live") or normalized_generic.get("status") != "pending":
    errors.append("v934_generic_live_without_evidence_exposed")
forced_snapshot = build_realtime_snapshot({
    "valid_matches_today": [{**generic_live, "status": "NS"}],
    "valid_live_events": [generic_live],
})
if int((forced_snapshot.get("counts") or {}).get("live") or 0) != 0:
    errors.append("v934_summary_force_live_without_evidence")

snapshot_now = datetime(2026, 7, 14, 20, 0, tzinfo=timezone.utc)
fresh_confirmed_live = {
    **generic_live,
    "id": "v937-fresh-confirmed-live",
    "home_score": 0,
    "away_score": 0,
    "updated_at": (snapshot_now - timedelta(seconds=30)).isoformat(),
}
stale_confirmed_live = {
    **generic_live,
    "id": "v937-stale-confirmed-live",
    "home_score": 1,
    "away_score": 0,
    "updated_at": (snapshot_now - timedelta(seconds=121)).isoformat(),
}
evidence_snapshot = build_realtime_snapshot({
    "valid_matches_today": [fresh_confirmed_live, stale_confirmed_live],
}, now=snapshot_now)
public_ids = {item.get("id") for item in evidence_snapshot.get("matches") or []}
if public_ids != {fresh_confirmed_live["id"]}:
    errors.append(f"v934_public_matches_stale_live_leak:{sorted(public_ids)}")
if int((evidence_snapshot.get("counts") or {}).get("live") or 0) != 1:
    errors.append("v934_fresh_confirmed_live_missing")
if int((evidence_snapshot.get("counts") or {}).get("stale_live") or 0) != 1:
    errors.append("v934_stale_live_diagnostic_count_missing")
if evidence_snapshot.get("poll_after_seconds") != 45:
    errors.append("v934_fresh_live_polling_interval")

stale_only_snapshot = build_realtime_snapshot({
    "valid_matches_today": [stale_confirmed_live],
}, now=snapshot_now)
if stale_only_snapshot.get("matches") or stale_only_snapshot.get("live"):
    errors.append("v934_stale_only_snapshot_public_leak")
if stale_only_snapshot.get("poll_after_seconds") != 180:
    errors.append("v934_stale_only_snapshot_polling_interval")

if "Force a live status" in app_source:
    errors.append("sportsdb_live_endpoint_forced_status")
if "DELETE FROM live_matches WHERE match_id=? OR id=?" not in app_source:
    errors.append("sportsdb_live_state_cleanup_missing")

original_db_path = app_module.DB_PATH
original_seeded_path = app_module._SEEDED_DB_PATH
try:
    with tempfile.TemporaryDirectory(prefix="nemesis_v937_live_state_") as temp_dir:
        app_module.DB_PATH = str(Path(temp_dir) / "sports.sqlite")
        app_module._SEEDED_DB_PATH = ""
        app_module.init_db()
        match = {
            "id": "sportsdb-regression-live",
            "external_id": "regression-live",
            "match_date": app_module.today_iso(),
            "kickoff_time": "20:00",
            "match_time": "20:00",
            "competition_name": "Regression League",
            "league_name": "Regression League",
            "home_team": "Regression Home",
            "away_team": "Regression Away",
            "status": "LIVE",
            "minute": "63",
            "source": "TheSportsDB API",
        }
        app_module.upsert_sportsdb_matches([match])
        with closing(sqlite3.connect(app_module.DB_PATH)) as conn:
            live_rows = conn.execute(
                "SELECT COUNT(*) FROM live_matches WHERE match_id=?",
                (match["id"],),
            ).fetchone()[0]
        if live_rows != 1:
            errors.append("sportsdb_confirmed_live_not_persisted")

        match.update({"status": "FINALIZADO", "minute": ""})
        app_module.upsert_sportsdb_matches([match])
        with closing(sqlite3.connect(app_module.DB_PATH)) as conn:
            live_rows = conn.execute(
                "SELECT COUNT(*) FROM live_matches WHERE match_id=?",
                (match["id"],),
            ).fetchone()[0]
        if live_rows != 0:
            errors.append("sportsdb_finished_match_left_in_live_table")

        match.update({"status": "LIVE", "minute": "", "home_score": "", "away_score": "", "score": ""})
        app_module.upsert_sportsdb_matches([match])
        with closing(sqlite3.connect(app_module.DB_PATH)) as conn:
            live_rows = conn.execute(
                "SELECT COUNT(*) FROM live_matches WHERE match_id=?",
                (match["id"],),
            ).fetchone()[0]
        if live_rows != 0:
            errors.append("sportsdb_generic_live_without_evidence_persisted")
finally:
    app_module.DB_PATH = original_db_path
    app_module._SEEDED_DB_PATH = original_seeded_path

environment = Environment()
for path in sorted((ROOT / "templates").rglob("*.html")):
    try:
        environment.parse(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"jinja:{path.relative_to(ROOT)}:{type(exc).__name__}")

if errors:
    print("V937 SPORTS LIFECYCLE CHECK: FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("V937 SPORTS LIFECYCLE CHECK: OK")
