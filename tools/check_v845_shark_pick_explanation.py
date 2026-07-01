import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.shark_ai_product_assistant_engine import explain_pick

pick = {"home_team": "Real Madrid", "away_team": "Barcelona", "market": "Ganador", "selection": "Real Madrid", "odds": 1.85, "risk_level": "MEDIO", "reasoning": "Valor real guardado."}
text = explain_pick(pick)
ok = "Real Madrid vs Barcelona" in text and "1.85" in text and "Riesgo" in text and "Valor real" in text
print({"ok": ok, "text": text})
raise SystemExit(0 if ok else 1)
