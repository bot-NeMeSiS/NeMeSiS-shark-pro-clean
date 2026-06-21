import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.shark_ai_product_assistant_engine import answer_shark_question, build_shark_context

free = answer_shark_question("plan", build_shark_context({"membership": "FREE"}))["answer"]
elite = answer_shark_question("plan", build_shark_context({"membership": "ELITE"}))["answer"]
ok = "Modo FREE" in free and "Modo ELITE" in elite and "sin inventar" in elite.lower()
print({"ok": ok})
raise SystemExit(0 if ok else 1)
