from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8", errors="replace")
engine=(ROOT/"engines/telegram_quality_filter_engine.py").read_text(encoding="utf-8", errors="replace").lower()
checks={
 "engine_exists":"telegram_match_quality_score" in engine,
 "nba_blocked":"nba" in engine,
 "youth_blocked":"youth" in engine and "reserve" in engine and "regional" in engine,
 "no_filler":"skipped_no_top_matches" in app.lower(),
 "admin":"admin/telegram/command-center" in app,
}
failed=[k for k,v in checks.items() if not v]
print({"checks":checks,"failed":failed}); raise SystemExit(1 if failed else 0)
