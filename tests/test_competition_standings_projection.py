from engines.competition_center_engine import build_competition_center_context


def _match(match_id, home, away, home_score, away_score, status="FT", date="2026-10-01"):
    return {
        "id": match_id,
        "competition_id": "140",
        "competition_name": "Liga de prueba",
        "league_name": "Liga de prueba",
        "country": "Spain",
        "season": "2026",
        "home_team": home,
        "away_team": away,
        "home_score": home_score,
        "away_score": away_score,
        "status": status,
        "match_date": date,
        "kickoff_iso": f"{date}T20:00:00+02:00",
        "source": "api_football_cache",
        "updated_at": f"{date}T22:00:00+02:00",
    }


def test_competition_center_projects_provisional_table_from_confirmed_results_only():
    matches = [
        _match("m1", "Club A", "Club B", 2, 0, date="2026-10-01"),
        _match("m2", "Club C", "Club A", 1, 1, date="2026-10-04"),
        # Upcoming 0-0 placeholders must not affect played matches or points.
        _match("m3", "Club B", "Club C", 0, 0, status="NS", date="2026-10-20"),
    ]
    center = build_competition_center_context({
        "competition": {
            "key": "liga-prueba",
            "external_id": "140",
            "name": "Liga de prueba",
            "country": "Spain",
            "season": "2026",
            "source": "api_football_cache",
        },
        "matches": matches,
    }, observed_at_madrid="2026-10-15T12:00:00+02:00")

    table = center["standings"]
    assert table["available"] is True
    assert table["provisional"] is True
    assert table["state"] == "PROVISIONAL_FROM_RESULTS"
    assert table["source"] == "computed_from_confirmed_finished_results"
    by_name = {row["team_name"]: row for row in table["rows"]}
    assert by_name["Club A"]["played"] == 2
    assert by_name["Club A"]["wins"] == 1
    assert by_name["Club A"]["draws"] == 1
    assert by_name["Club A"]["points"] == 4
    assert by_name["Club A"]["goals_for"] == 3
    assert by_name["Club A"]["goals_against"] == 1
    assert by_name["Club A"]["goal_difference"] == 2
    assert by_name["Club B"]["played"] == 1
    assert by_name["Club B"]["points"] == 0
    assert all(row["state"] == "Provisional" for row in table["rows"])
    assert all(row["limitations"] for row in table["rows"])
    assert any("puede estar incompleta" in item for item in table["limitations"])


def test_official_provider_standings_take_priority_over_provisional_projection():
    center = build_competition_center_context({
        "competition": {
            "key": "liga-prueba",
            "external_id": "140",
            "name": "Liga de prueba",
            "country": "Spain",
            "season": "2026",
            "source": "api_football_cache",
        },
        "matches": [_match("m1", "Club A", "Club B", 2, 0)],
        "standings": [{
            "rank": 1,
            "team_id": "club-a",
            "team_name": "Club A",
            "played": 10,
            "wins": 8,
            "draws": 1,
            "losses": 1,
            "goals_for": 20,
            "goals_against": 5,
            "points": 25,
            "form": "VVVEV",
            "source": "api_football_standings",
        }],
    }, observed_at_madrid="2026-10-15T12:00:00+02:00")

    assert center["standings"]["provisional"] is False
    assert center["standings"]["state"] == "OFFICIAL_PROVIDER_DATA"
    assert center["standings"]["rows"][0]["played"] == 10
    assert center["standings"]["rows"][0]["points"] == 25
