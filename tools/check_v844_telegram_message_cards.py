import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.telegram_delivery_engine import build_daily_picks_message

pick = {
    "sport_key": "soccer_spain_la_liga",
    "competition_name": "LaLiga",
    "home_team": "Real Madrid",
    "away_team": "Barcelona",
    "kickoff_iso": "2026-06-21T21:00:00+02:00",
    "market": "Resultado final",
    "selection": "Real Madrid gana",
    "odds": 1.85,
    "confidence": 82,
    "risk_level": "Medio",
    "reasoning": "Mercado claro con cuota real y contexto suficiente.",
}
message = build_daily_picks_message([pick], force_empty=False)
bad = ["dÃ", "Â", "undefined", "None", "ROI garantizado"]
ok = bool(message) and all(term not in message for term in bad) and "Cuota" in message and "SHARK" in message
print(json.dumps({"ok": ok, "length": len(message), "preview": message[:220]}, ensure_ascii=True))
raise SystemExit(0 if ok else 1)
