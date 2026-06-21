import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.shark_ai_product_assistant_engine import explain_match

match = {"home_team": "Real Madrid", "away_team": "Barcelona", "competition_name": "LaLiga", "client_status_label": "Próximo"}
text = explain_match(match)
ok = "Real Madrid vs Barcelona" in text and "LaLiga" in text and "Resultado pendiente" in text
print({"ok": ok, "text": text})
raise SystemExit(0 if ok else 1)
