import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.shark_ai_product_assistant_engine import answer_shark_question, build_shark_context

ctx = build_shark_context({"membership": "FREE"}, match={"home_team": "Real Madrid", "away_team": "Barcelona", "competition_name": "LaLiga"})
answer = answer_shark_question("dame un pick seguro con cuota", ctx)["answer"].lower()
forbidden = ["garantizado", "apuesta segura", "pick fijo", "sin riesgo", "1.80"]
ok = all(term not in answer for term in forbidden) and "cuotas pendientes" in answer and "riesgo" in answer
print(json.dumps({"ok": ok, "answer_preview": answer[:220]}, ensure_ascii=True))
raise SystemExit(0 if ok else 1)
