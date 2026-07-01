from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
engine = (ROOT / "engines" / "telegram_quality_filter_engine.py").read_text(encoding="utf-8", errors="replace")
checks = {
    "engine_exists": "telegram_match_quality_score" in engine,
    "blocks_nba": "nba" in engine.lower(),
    "blocks_youth": "youth" in engine.lower() and "reserve" in engine.lower(),
    "no_filler": "skipped_no_top_matches" in app.lower(),
    "admin_telegram": "/admin/telegram/command-center" in app,
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
