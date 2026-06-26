from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.picks_quality_engine import enrich_pick_quality, sort_picks_by_quality


def main():
    rare = enrich_pick_quality({"competition_name": "Georgian Erovnuli Liga", "selection": "Local", "market": "1X2", "odds": 1.8, "match_date": "2099-06-01"})
    top = enrich_pick_quality({"competition_name": "Champions League", "selection": "Local", "market": "1X2", "odds": 1.8, "match_date": "2099-06-01"})
    stale = enrich_pick_quality({"competition_name": "Premier League", "selection": "Local", "market": "1X2", "odds": 1.8, "match_date": "2020-01-01"})
    pending = enrich_pick_quality({"competition_name": "Premier League", "selection": "Selección pendiente", "market": "1X2", "odds": 0, "match_date": "2099-06-01"})
    assert rare["low_relevance_competition"] is True and rare["premium_ready"] is False
    assert stale["stale_pick"] is True and stale["app_pick_state"] == "Archivado"
    assert pending["premium_ready"] is False and pending["app_pick_state"] == "Pick en revisión"
    ordered = sort_picks_by_quality([rare, top, stale, pending])
    assert ordered[0]["competition_name"] == "Champions League"
    print("V852 picks quality/stale data OK")


if __name__ == "__main__":
    main()
