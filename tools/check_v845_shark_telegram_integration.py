import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.shark_ai_product_assistant_engine import answer_shark_question, build_shark_context
from engines.telegram_quality_filter_engine import explain_telegram_filter_decision

match = {"sport_key": "soccer_spain_la_liga", "competition_name": "LaLiga", "home_team": "Real Madrid", "away_team": "Barcelona", "kickoff_iso": "2026-06-21T21:00:00+02:00"}
quality = explain_telegram_filter_decision(match)
ctx = build_shark_context({"membership": "ELITE"}, match=match, telegram_quality=quality)
answer = answer_shark_question("telegram", ctx)["answer"].lower()
ok = quality.get("allowed") and "telegram" in answer and ("apto" in answer or "top" in answer)
print(json.dumps({"ok": ok, "quality": quality, "answer": answer[:240]}, ensure_ascii=True))
raise SystemExit(0 if ok else 1)
