import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.shark_ai_product_assistant_engine import build_fallback_answer, build_shark_context

ctx = build_shark_context({"membership": "FREE"}, openai_configured=False)
answer = build_fallback_answer("resumen", ctx)
ok = answer.get("fallback_mode") and "Modo análisis interno" in answer.get("answer", "")
print({"ok": ok})
raise SystemExit(0 if ok else 1)
