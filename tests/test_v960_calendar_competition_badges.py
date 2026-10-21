import json

from test_design02_calendar_presentation import Structure


def test_calendar_group_uses_later_fixture_badge_from_saved_provider_payload(app_module):
    day = app_module.today_iso()
    base = {
        "match_date": day,
        "kickoff_time": "18:00",
        "competition_name": "LaLiga",
        "country": "Spain",
        "source": "SIMULATED_QA",
    }
    rows = [
        {**base, "id": "SIMULATED_QA-first", "home_team": "Local QA", "away_team": "Visitante QA"},
        {
            **base,
            "id": "SIMULATED_QA-second",
            "home_team": "Local QA 2",
            "away_team": "Visitante QA 2",
            "raw_json": json.dumps({"league": {"logo": "https://assets.invalid/laliga.svg"}}),
        },
    ]

    grouped = app_module._calendar_group(rows)

    assert len(grouped) == 1
    assert len(grouped[0]["leagues"]) == 1
    assert grouped[0]["leagues"][0]["logo_url"] == "https://assets.invalid/laliga.svg"
    assert [item["id"] for item in grouped[0]["leagues"][0]["matches"]] == [
        "SIMULATED_QA-first", "SIMULATED_QA-second"
    ]


def test_calendar_missing_badge_uses_country_scoped_read_only_asset_route(client, app_module, monkeypatch):
    match = {
        "id": "SIMULATED_QA-calendar-logo",
        "home_team": "Local QA",
        "away_team": "Visitante QA",
        "competition_name": "Liga QA",
        "country": "Spain",
        "match_date": app_module.today_iso(),
        "kickoff_time": "18:00",
        "source": "SIMULATED_QA",
        "status": "NS",
        "v935_lifecycle": "UPCOMING",
    }
    summary = {
        "all_valid_matches": [match],
        "valid_upcoming_matches": [match],
        "valid_matches_today": [match],
        "valid_matches_available": [match],
        "valid_live_events": [],
        "finished_matches": [],
        "valid_active_picks": [],
        "incident_matches": [],
        "incomplete_matches": [],
        "raw_matches_count": 1,
    }
    metrics = app_module.build_sports_metrics_contract(summary)
    monkeypatch.setattr(
        app_module,
        "v932_safe_dashboard_data",
        lambda *args, **kwargs: ({"sports_metrics": metrics}, summary),
    )

    response = client.get("/calendar", query_string={"lane": "week", "date": app_module.today_iso()})

    assert response.status_code == 200
    dom = Structure(response.get_data(as_text=True))
    badges = dom.with_class("v933-competition-logo")
    assert len(badges) == 1
    assert badges[0]["attrs"]["data-logo-source"] == "cache_lookup"
    image = next(node for node in dom.nodes if node["tag"] == "img" and badges[0] in node["parents"])
    assert image["attrs"]["src"].startswith("/asset/league-logo/")
    assert "country=Espa%C3%B1a" in image["attrs"]["src"]
    assert "provider=" not in image["attrs"]["src"]
    assert "league_id=" not in image["attrs"]["src"]


def test_calendar_unknown_country_keeps_fallback_without_unscoped_logo_lookup(client, app_module, monkeypatch):
    match = {
        "id": "SIMULATED_QA-global-logo",
        "home_team": "Local QA",
        "away_team": "Visitante QA",
        "competition_name": "Torneo QA",
        "match_date": app_module.today_iso(),
        "kickoff_time": "19:00",
        "source": "SIMULATED_QA",
        "status": "NS",
        "v935_lifecycle": "UPCOMING",
    }
    summary = {
        "all_valid_matches": [match], "valid_upcoming_matches": [match],
        "valid_matches_today": [match], "valid_matches_available": [match],
        "valid_live_events": [], "finished_matches": [], "valid_active_picks": [],
        "incident_matches": [], "incomplete_matches": [], "raw_matches_count": 1,
    }
    metrics = app_module.build_sports_metrics_contract(summary)
    monkeypatch.setattr(
        app_module,
        "v932_safe_dashboard_data",
        lambda *args, **kwargs: ({"sports_metrics": metrics}, summary),
    )

    response = client.get("/calendar", query_string={"lane": "week", "date": app_module.today_iso()})

    assert response.status_code == 200
    dom = Structure(response.get_data(as_text=True))
    badge, = dom.with_class("v933-competition-logo")
    assert badge["attrs"]["data-logo-source"] == "fallback"
    image = [node for node in dom.nodes if node["tag"] == "img" and badge in node["parents"]]
    assert image == []
