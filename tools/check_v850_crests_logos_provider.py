from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.crest_logo_experience_engine import (
    build_league_logo_payload,
    build_team_crest_payload,
    cache_logo_reference,
    explain_logo_state,
    get_league_logo,
    get_logo_fallback,
    get_team_logo,
    normalize_logo_url,
)


def main():
    assert normalize_logo_url("http://example.com/logo.png").startswith("https://")
    assert normalize_logo_url("javascript:alert(1)") == ""
    team = build_team_crest_payload({"name": "Sevilla FC", "logo_url": "https://media.api-sports.io/football/teams/536.png"})
    assert team["has_real_logo"] is True
    fallback = build_team_crest_payload("Equipo sin logo")
    assert fallback["is_fallback"] is True and "/team-crest.svg" in fallback["crest_url"]
    league = build_league_logo_payload("LaLiga")
    assert league["is_fallback"] is True
    assert get_team_logo(team_name="Betis")["is_fallback"] is True
    assert get_league_logo(league_name="Champions League")["is_fallback"] is True
    assert get_logo_fallback("Betis").startswith("/team-crest.svg")
    assert cache_logo_reference("Betis", "https://example.com/logo.png")["write_performed"] is False
    assert "Fallback" in explain_logo_state("Betis")["label"]
    print("check_v850_crests_logos_provider OK")


if __name__ == "__main__":
    main()
