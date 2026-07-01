from pathlib import Path
import os
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v848_api_sports.db"))
import app as nemesis  # noqa: E402
data = nemesis.app.test_client().get("/api/runtime-version").get_json() or {}
engine = (ROOT / "engines" / "api_sports_provider_engine.py").read_text(encoding="utf-8", errors="replace")
checks = {
    "v847_flag": data.get("has_v847_company_brain_api_sports_provider_qa") is True,
    "runtime_provider": all(k in data for k in ["api_sports_configured", "api_football_configured", "the_odds_configured", "usage_guard"]),
    "admin_route": "/api/admin/api-sports/status" in (ROOT / "app.py").read_text(encoding="utf-8", errors="replace"),
    "cache_first": '"cache_first": True' in engine,
    "dry_run": "dry_run" in engine,
    "no_secret": "API_FOOTBALL_KEY=" not in engine,
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
