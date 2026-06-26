from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.live_match_experience_engine import (
    build_live_card_payload,
    explain_live_data_state,
    get_live_matches_from_api_sports_safe,
    get_match_minute_label,
    get_match_status_label,
    get_score_label,
    live_cache_summary,
    normalize_live_match,
    should_refresh_live_cache,
)


def main():
    sample = {"home_team": "Real Madrid", "away_team": "Barcelona", "status": "1H", "minute": "34", "home_score": 1, "away_score": 0}
    assert get_match_status_label(sample) == "En directo"
    assert get_match_minute_label(sample) == "34'"
    assert get_score_label(sample) == "1-0"
    assert build_live_card_payload(sample)["is_live"] is True
    assert normalize_live_match({"fixture": {"id": 1, "status": {"short": "HT", "elapsed": 45}}, "teams": {"home": {"name": "A"}, "away": {"name": "B"}}, "goals": {"home": 0, "away": 0}})["v850_status_label"] == "Descanso"
    assert get_live_matches_from_api_sports_safe(dry_run=True)["dry_run"] is True
    assert live_cache_summary(None)["cache_first"] is True
    assert should_refresh_live_cache("") is True
    state = explain_live_data_state(None)
    assert state["label"] in {"Esperando proveedor", "Sin directos reales", "Directo cacheado"}
    print("check_v850_live_match_engine OK")


if __name__ == "__main__":
    main()
