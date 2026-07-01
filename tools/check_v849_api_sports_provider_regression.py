from pathlib import Path
import os, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir())/"nemesis_v849_api.db"))
import app as nemesis  # noqa
d=nemesis.app.test_client().get("/api/runtime-version").get_json() or {}
engine=(ROOT/"engines/api_sports_provider_engine.py").read_text(encoding="utf-8", errors="replace")
checks={
 "engine_exists":"get_api_sports_status" in engine,
 "runtime": all(k in d for k in ["api_sports_configured","api_football_configured","the_odds_configured","usage_guard"]),
 "admin_routes": all(x in (ROOT/"app.py").read_text(encoding="utf-8", errors="replace") for x in ["/admin/api-sports","/api/admin/api-sports/status"]),
 "guard": all(x in engine for x in ["cache_first","dry_run_supported","daily_call_budget","no_page_render_calls"]),
 "no_secret":"API_FOOTBALL_KEY=" not in engine,
}
failed=[k for k,v in checks.items() if not v]
print({"checks":checks,"failed":failed}); raise SystemExit(1 if failed else 0)
