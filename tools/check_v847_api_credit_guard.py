from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
engine = (ROOT / "engines" / "api_sports_provider_engine.py").read_text(encoding="utf-8", errors="replace")
checks = {
    "cache_first": '"cache_first": True' in engine,
    "no_page_render_calls": '"no_page_render_calls": True' in engine,
    "dry_run_supported": '"dry_run_supported": True' in engine,
    "timeout": "API_SPORTS_TIMEOUT_SECONDS" in engine,
    "daily_budget": "API_FOOTBALL_DAILY_CALL_BUDGET" in engine or "API_SPORTS_DAILY_CALL_BUDGET" in engine,
    "no_aggressive_retry": "retry" not in engine.lower(),
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
