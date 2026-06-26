from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.shark_ai_product_assistant_engine import build_shark_context, explain_match
from engines.live_match_experience_engine import build_live_card_payload


def main():
    match = {"id": "m1", "home_team": "A", "away_team": "B", "status": "LIVE", "minute": "", "score": ""}
    ctx = build_shark_context(None, match=match, page="match")
    answer = explain_match(match)
    live = build_live_card_payload(match)
    assert isinstance(ctx, dict)
    assert "No hay datos" in answer or "datos" in answer.lower() or "partido" in answer.lower()
    assert live["minute_label"] == "Minuto no disponible"
    print("check_v850_shark_live_crests_context OK")


if __name__ == "__main__":
    main()
