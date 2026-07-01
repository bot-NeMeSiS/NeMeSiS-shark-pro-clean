from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
engine = (ROOT / "engines" / "api_sports_provider_engine.py").read_text(encoding="utf-8", errors="replace")
live_engine = (ROOT / "engines" / "api_football_live_tracker_engine.py").read_text(encoding="utf-8", errors="replace")

checks = {
    "engine_exists": "def get_api_sports_status" in engine,
    "uses_apisports_header": "x-apisports-key" in engine and "x-apisports-key" in live_engine,
    "runtime_imports_engine": "api_sports_provider_engine" in app,
    "live_uses_api_football": "sync_api_football_live_tracker(DB_PATH" in app,
    "match_detail_uses_fixture_detail": "sync_api_football_fixture_detail(DB_PATH" in app,
    "master_tick_window_sync": "sync_api_football_match_window" in app,
    "admin_status_endpoint": "/api/admin/api-sports/status" in app,
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
