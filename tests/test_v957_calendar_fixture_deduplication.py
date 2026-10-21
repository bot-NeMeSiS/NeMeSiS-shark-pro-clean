from datetime import date, datetime, time
from zoneinfo import ZoneInfo


def _fixture(app_module, identity, source, *, kickoff=None):
    kickoff = kickoff or datetime.combine(
        date.fromisoformat(app_module.today_iso(1)),
        time(20, 0),
        tzinfo=ZoneInfo("Europe/Madrid"),
    )
    return {
        "id": identity,
        "match_id": identity,
        "external_id": identity,
        "home_team": "Levante UD",
        "away_team": "Athletic Club" if "sportsdb" in identity else "Athletic Bilbao",
        "competition_name": "LaLiga",
        "competition_key": "laliga",
        "country": "Spain",
        "match_date": kickoff.date().isoformat(),
        "kickoff_iso": kickoff.isoformat(),
        "kickoff_time": kickoff.strftime("%H:%M"),
        "status": "NS",
        "source": source,
    }


def _summary(matches, *, picks=()):
    return {
        "all_valid_matches": matches,
        "valid_upcoming_matches": matches,
        "valid_matches_today": [],
        "valid_live_events": [],
        "valid_active_picks": list(picks),
        "finished_matches": [],
        "incident_matches": [],
    }


def test_calendar_collapses_cross_provider_copy_and_keeps_primary_row(app_module):
    alternate = _fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB")
    primary = _fixture(app_module, "af-1570389", "API_FOOTBALL")
    summary = _summary([alternate, primary])

    with app_module.app.test_request_context("/calendario?lane=week"):
        context = app_module.v940_calendar_context(summary, "week", app_module.today_iso())

    assert [match["id"] for match in context["matches"]] == ["af-1570389"]
    assert context["counts"]["all"] == context["counts"]["visible"] == 1
    assert context["counts"]["tomorrow"] == 1
    assert sum(facet["count"] for facet in context["facets"]["countries"]) == 1


def test_calendar_today_counter_uses_the_unique_display_rows(app_module):
    kickoff = datetime.combine(
        date.fromisoformat(app_module.today_iso()),
        time(23, 59),
        tzinfo=ZoneInfo("Europe/Madrid"),
    )
    alternate = _fixture(
        app_module, "sportsdb-today-fixture", "TheSportsDB", kickoff=kickoff
    )
    primary = _fixture(app_module, "af-today-fixture", "API_FOOTBALL", kickoff=kickoff)
    summary = _summary([alternate, primary])
    summary["valid_matches_today"] = [alternate, primary]

    with app_module.app.test_request_context("/calendario?lane=today"):
        context = app_module.v940_calendar_context(
            summary, "today", app_module.today_iso()
        )

    assert len(context["matches"]) == 1
    assert context["counts"]["today"] == 1


def test_calendar_api_emits_one_customer_card_for_cross_provider_copy(
    app_module, client, monkeypatch
):
    alternate = _fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB")
    primary = _fixture(app_module, "af-1570389", "API_FOOTBALL")
    summary = _summary([alternate, primary])
    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", lambda *_args, **_kwargs: ({}, summary))
    monkeypatch.setattr(app_module, "_v940_hydrate_selected_date_results", lambda value, _date: value)
    monkeypatch.setattr(app_module, "_v940_calendar_provider_context", lambda _summary: {})
    monkeypatch.setattr(app_module, "get_realtime_safe_matches_context", lambda _summary: {})

    response = client.get("/api/calendar?lane=week")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"] == app_module.APP_VERSION
    assert [match["id"] for match in payload["matches"]] == ["af-1570389"]
    assert payload["calendar"]["counts"]["visible"] == 1


def test_calendar_duplicate_keeps_the_row_linked_to_a_pick(app_module):
    alternate = _fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB")
    primary = _fixture(app_module, "af-1570389", "API_FOOTBALL")
    summary = _summary(
        [primary, alternate],
        picks=[{"id": "pick-1", "match_id": alternate["id"]}],
    )

    with app_module.app.test_request_context("/calendario?lane=with_pick"):
        context = app_module.v940_calendar_context(summary, "with_pick", app_module.today_iso())

    assert len(context["matches"]) == 1
    assert context["matches"][0]["id"] == alternate["id"]
    assert context["matches"][0]["has_pick"] is True
    assert context["counts"]["picks"] == 1


def test_calendar_duplicate_keeps_the_row_linked_to_a_favorite(app_module, monkeypatch):
    alternate = _fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB")
    primary = _fixture(app_module, "af-1570389", "API_FOOTBALL")
    summary = _summary([primary, alternate])
    monkeypatch.setattr(app_module, "current_session_user", lambda: {"id": "client-qa"})
    monkeypatch.setattr(
        app_module,
        "favorite_sets",
        lambda: {"team": set(), "league": set(), "match": {alternate["id"]}, "all": []},
    )

    with app_module.app.test_request_context("/calendario?lane=week"):
        context = app_module.v940_calendar_context(summary, "week", app_module.today_iso())

    assert len(context["matches"]) == 1
    assert context["matches"][0]["id"] == alternate["id"]
    assert context["matches"][0]["is_favorite"] is True
    assert context["counts"]["favorites"] == 1


def test_calendar_keeps_rows_when_country_or_kickoff_do_not_match(app_module):
    base = _fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB")
    same_fixture = _fixture(app_module, "af-1570389", "API_FOOTBALL")
    different_country = {**same_fixture, "id": "other-country", "country": "Portugal"}
    different_kickoff = _fixture(
        app_module,
        "other-kickoff",
        "API_FOOTBALL",
        kickoff=datetime.combine(
            date.fromisoformat(app_module.today_iso(1)),
            time(20, 2),
            tzinfo=ZoneInfo("Europe/Madrid"),
        ),
    )

    unique = app_module._v957_unique_calendar_fixtures(
        [base, same_fixture, different_country, different_kickoff]
    )

    assert len(unique) == 3
