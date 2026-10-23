"""Cross-provider fixture copies must produce one customer-facing match.

All examples are in-memory QA snapshots. Dates are relative to the app clock;
neither an external provider nor production data is read by these tests.
"""
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest


MADRID = ZoneInfo("Europe/Madrid")
CASES = [
    pytest.param(
        ("Granada", "Real Valladolid"), ("Granada CF", "Valladolid"),
        "Segunda División", "Spain", ("4400", "141"), id="granada-valladolid",
    ),
    pytest.param(
        ("Deportivo Alavés", "Málaga"), ("Alaves", "Malaga"),
        "LaLiga EA Sports", "Spain", ("4335", "140"), id="alaves-malaga",
    ),
    pytest.param(
        ("Valencia C.F.", "Sevilla F.C."), ("Valencia", "Sevilla"),
        "LaLiga EA Sports", "Spain", ("4335", "140"), id="punctuated-club-suffixes",
    ),
    pytest.param(
        ("FC Porto", "Braga Football Club"), ("Porto", "Braga"),
        "Primeira Liga", "Portugal", ("", ""), id="prefix-and-full-club-descriptor",
    ),
    pytest.param(
        ("Riverbank Football Club", "FC Meadowtown"), ("Riverbank", "Meadowtown"),
        "QA Championship", "England", ("", ""), id="unlisted-clubs",
    ),
]


def _pair(app_module, names_alt, names_primary, competition, country, league_ids):
    kickoff = datetime.combine(
        date.fromisoformat(app_module.today_iso(1)), time(20, 30), tzinfo=MADRID
    )
    common = {
        "competition_name": competition,
        "league_name": competition,
        "country": country,
        "match_date": kickoff.date().isoformat(),
        "kickoff_iso": kickoff.isoformat(),
        "kickoff_time": "20:30",
        "season": str(kickoff.year),
        "sport": "Soccer",
        "status": "NS",
    }
    alternate = {
        **common,
        "id": "sportsdb-qa-fixture",
        "match_id": "sportsdb-qa-fixture",
        "external_id": "sportsdb-qa-fixture",
        "source": "TheSportsDB",
        "competition_id": league_ids[0],
        "home_team": names_alt[0],
        "away_team": names_alt[1],
        "home_team_id": "sportsdb-home",
        "away_team_id": "sportsdb-away",
    }
    primary = {
        **common,
        "id": "af-qa-fixture",
        "match_id": "af-qa-fixture",
        "external_id": "af-qa-fixture",
        "source": "API_FOOTBALL",
        "competition_id": league_ids[1],
        "home_team": names_primary[0],
        "away_team": names_primary[1],
        "home_team_id": "api-home",
        "away_team_id": "api-away",
    }
    return alternate, primary


def _reported_pair(app_module):
    return _pair(
        app_module, ("Granada", "Real Valladolid"), ("Granada CF", "Valladolid"),
        "Segunda División", "Spain", ("4400", "141"),
    )


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


def _home_rows(context):
    return [
        match
        for lane in ("today", "upcoming", "live", "results")
        for group in context[lane]["groups"]
        for match in group["matches"]
    ]


def _observed_pair(app_module, status="LIVE", *, primary_status=None):
    alternate, primary = _reported_pair(app_module)
    observed_at = datetime.now(MADRID).replace(microsecond=0)
    # Keep today's fixtures on today's date, including tests run just after midnight.
    elapsed = min(30, observed_at.hour * 60 + observed_at.minute)
    kickoff = observed_at - timedelta(minutes=elapsed)
    for row, row_status in (
        (alternate, status), (primary, primary_status or status)
    ):
        row.update(
            match_date=kickoff.date().isoformat(),
            kickoff_iso=kickoff.isoformat(),
            kickoff_time=kickoff.strftime("%H:%M"),
            status=row_status,
            minute=elapsed if row_status == "LIVE" else None,
            home_score=1 if row_status in {"LIVE", "FT"} else None,
            away_score=0 if row_status in {"LIVE", "FT"} else None,
            last_synced_at=observed_at.isoformat(),
        )
    return alternate, primary


def _observed_summary(rows, *, live=(), finished=()):
    summary = _summary(rows)
    summary.update(
        valid_matches_today=rows,
        valid_upcoming_matches=[],
        valid_live_events=list(live),
        finished_matches=list(finished),
        raw_matches_count=len(rows),
    )
    return summary


def _uncached_realtime(monkeypatch, app_module, summary):
    # Exercise the real normalizer and presentation boundary while isolating cache
    # state, persisted statistics and dashboard reads from these in-memory inputs.
    monkeypatch.setattr(
        app_module, "cached_v934_realtime_snapshot",
        lambda _key, builder, **_kwargs: (deepcopy(builder()), "qa_uncached"),
    )
    monkeypatch.setattr(app_module, "get_public_home_sports_summary", lambda: summary)
    monkeypatch.setattr(
        app_module, "live_tracker_summaries_for_matches", lambda *_args, **_kwargs: {}
    )


@pytest.mark.parametrize("names_alt,names_primary,competition,country,league_ids", CASES)
@pytest.mark.parametrize("reverse", [False, True], ids=["alternate-first", "primary-first"])
def test_home_collapses_provider_name_variants_before_counting_and_grouping(
    app_module, names_alt, names_primary, competition, country, league_ids, reverse
):
    alternate, primary = _pair(
        app_module, names_alt, names_primary, competition, country, league_ids
    )
    rows = [alternate, primary]
    if reverse:
        rows.reverse()
    summary = _summary(rows)
    before = deepcopy(summary)

    context = app_module.home_matchday_context(summary)

    assert [row["id"] for row in _home_rows(context)] == [primary["id"]]
    assert context["upcoming"]["total"] == context["upcoming"]["shown"] == 1
    assert context["upcoming"]["competition_count"] == 1
    assert summary == before


@pytest.mark.parametrize("names_alt,names_primary,competition,country,league_ids", CASES)
def test_calendar_collapses_provider_name_variants_and_counts_one_fixture(
    app_module, names_alt, names_primary, competition, country, league_ids
):
    alternate, primary = _pair(
        app_module, names_alt, names_primary, competition, country, league_ids
    )
    summary = _summary([alternate, primary])
    before = deepcopy(summary)

    with app_module.app.test_request_context("/calendar?lane=week"):
        context = app_module.v940_calendar_context(summary, "week", app_module.today_iso())

    assert [row["id"] for row in context["matches"]] == [primary["id"]]
    assert context["counts"]["all"] == context["counts"]["visible"] == 1
    assert context["counts"]["tomorrow"] == 1
    assert sum(facet["count"] for facet in context["facets"]["countries"]) == 1
    assert summary == before


@pytest.mark.parametrize("names_alt,names_primary,competition,country,league_ids", CASES[:2])
def test_calendar_api_returns_one_card_for_each_reported_pair(
    app_module, client, monkeypatch,
    names_alt, names_primary, competition, country, league_ids,
):
    alternate, primary = _pair(
        app_module, names_alt, names_primary, competition, country, league_ids
    )
    summary = _summary([alternate, primary])
    before = deepcopy(summary)
    monkeypatch.setattr(
        app_module, "v932_safe_dashboard_data", lambda *_args, **_kwargs: ({}, summary)
    )
    monkeypatch.setattr(
        app_module, "_v940_hydrate_selected_date_results", lambda value, _date: value
    )
    monkeypatch.setattr(app_module, "_v940_calendar_provider_context", lambda _summary: {})
    monkeypatch.setattr(app_module, "get_realtime_safe_matches_context", lambda _summary: {})

    response = client.get("/api/calendar?lane=week")

    assert response.status_code == 200
    payload = response.get_json()
    assert [row["id"] for row in payload["matches"]] == [primary["id"]]
    assert payload["calendar"]["counts"]["visible"] == 1
    assert summary == before


@pytest.mark.parametrize("lane", ["week", "with_pick"])
def test_calendar_keeps_existing_pick_link_while_collapsing_provider_alias(app_module, lane):
    alternate, primary = _reported_pair(app_module)
    summary = _summary(
        [primary, alternate], picks=[{"id": "pick-qa", "match_id": alternate["id"]}]
    )
    before = deepcopy(summary)

    with app_module.app.test_request_context(f"/calendar?lane={lane}"):
        context = app_module.v940_calendar_context(summary, lane, app_module.today_iso())

    assert [row["id"] for row in context["matches"]] == [alternate["id"]]
    assert context["counts"]["all"] == 1
    assert context["counts"]["picks"] == 1
    assert context["matches"][0]["has_pick"] is True
    assert summary == before


def test_calendar_keeps_existing_favorite_link_while_collapsing_provider_alias(
    app_module, monkeypatch
):
    alternate, primary = _reported_pair(app_module)
    summary = _summary([primary, alternate])
    before = deepcopy(summary)
    monkeypatch.setattr(app_module, "current_session_user", lambda: {"id": "client-qa"})
    monkeypatch.setattr(
        app_module, "favorite_sets",
        lambda: {"team": set(), "league": set(), "match": {alternate["id"]}, "all": []},
    )

    with app_module.app.test_request_context("/calendar?lane=week"):
        context = app_module.v940_calendar_context(summary, "week", app_module.today_iso())

    assert [row["id"] for row in context["matches"]] == [alternate["id"]]
    assert context["counts"]["all"] == 1
    assert context["counts"]["favorites"] == 1
    assert context["matches"][0]["is_favorite"] is True
    assert summary == before


@pytest.mark.parametrize(
    "change",
    [{"country": "Portugal"}, {"home_team": "Granada CF B"}],
    ids=["different-country", "reserve-team"],
)
def test_home_and_calendar_preserve_distinct_teams_and_countries(app_module, change):
    alternate, primary = _reported_pair(app_module)
    primary.update(change)
    summary = _summary([alternate, primary])
    before = deepcopy(summary)

    home = app_module.home_matchday_context(summary)
    with app_module.app.test_request_context("/calendar?lane=week"):
        calendar = app_module.v940_calendar_context(summary, "week", app_module.today_iso())

    assert {row["id"] for row in _home_rows(home)} == {alternate["id"], primary["id"]}
    assert {row["id"] for row in calendar["matches"]} == {alternate["id"], primary["id"]}
    assert home["upcoming"]["total"] == calendar["counts"]["all"] == 2
    assert summary == before


def test_shared_available_counter_agrees_with_home_and_calendar(app_module):
    alternate, primary = _reported_pair(app_module)
    summary = _summary([alternate, primary])

    metrics = app_module.build_sports_metrics_contract(summary)
    home = app_module.home_matchday_context(summary)
    with app_module.app.test_request_context("/calendar?lane=week"):
        calendar = app_module.v940_calendar_context(summary, "week", app_module.today_iso())

    assert metrics["matches_available"] == home["upcoming"]["total"] == 1
    assert calendar["counts"]["all"] == 1


def test_home_keeps_existing_match_favorite_link_without_mutating_snapshot(app_module):
    alternate, primary = _reported_pair(app_module)
    summary = _summary([primary, alternate])
    favorites = {"team": set(), "league": set(), "match": {alternate["id"]}}
    before = deepcopy((summary, favorites))

    context = app_module.home_matchday_context(summary, favorites=favorites)

    assert [row["id"] for row in _home_rows(context)] == [alternate["id"]]
    assert _home_rows(context)[0]["is_favorite"] is True
    assert context["upcoming"]["total"] == 1
    assert (summary, favorites) == before


def test_home_keeps_existing_pick_match_link_without_mutating_snapshot(app_module):
    alternate, primary = _reported_pair(app_module)
    summary = _summary(
        [primary, alternate], picks=[{"id": "pick-qa", "match_id": alternate["id"]}]
    )
    before = deepcopy(summary)

    context = app_module.home_matchday_context(summary)

    assert [row["id"] for row in _home_rows(context)] == [alternate["id"]]
    assert context["upcoming"]["total"] == 1
    assert summary == before


@pytest.mark.parametrize("primary_status", ["LIVE", "NS"])
def test_live_selects_one_fixture_after_filtering_provider_states(app_module, primary_status):
    alternate, primary = _observed_pair(app_module, primary_status=primary_status)
    rows = [primary, alternate]
    # The live lane still applies its own status gate to candidate observations.
    summary = _observed_summary(rows, live=rows)
    before = deepcopy(summary)

    context = app_module.v931_live_context(summary, lane="live")

    expected_id = primary["id"] if primary_status == "LIVE" else alternate["id"]
    assert [row["id"] for row in context["matches"]] == [expected_id]
    assert context["counts"]["live"] == 1
    assert app_module.canonical_match_status(context["matches"][0])["is_live"] is True
    assert summary == before


@pytest.mark.parametrize("status", ["NS", "LIVE", "FT"])
def test_today_live_and_finished_metrics_count_fixtures_not_provider_records(app_module, status):
    rows = list(_observed_pair(app_module, status))
    summary = _observed_summary(
        rows, live=rows if status == "LIVE" else (),
        finished=rows if status == "FT" else (),
    )
    before = deepcopy(summary)

    metrics = app_module.build_sports_metrics_contract(summary)

    assert metrics["matches_today"] == metrics["matches_available"] == 1
    assert metrics["live_confirmed"] == int(status == "LIVE")
    assert metrics["finished_verified"] == int(status == "FT")
    assert metrics["matches_synchronized"] == 2
    assert summary == before


def test_realtime_keeps_original_observations_but_safe_contexts_show_one_fixture(
    app_module, monkeypatch
):
    alternate, primary = _observed_pair(app_module)
    rows = [alternate, primary]
    summary = _observed_summary(rows, live=rows)
    before = deepcopy(summary)
    _uncached_realtime(monkeypatch, app_module, summary)

    snapshot = app_module.get_v934_realtime_context(summary, force=True)
    safe_matches = app_module.get_realtime_safe_matches_context(summary)
    safe_live = app_module.get_realtime_safe_live_context(summary)

    assert {row["id"] for row in snapshot["matches"]} == {alternate["id"], primary["id"]}
    assert {row["id"] for row in snapshot["live"]} == {alternate["id"], primary["id"]}
    assert [row["id"] for row in safe_matches["items"]] == [primary["id"]]
    assert [row["id"] for row in safe_live["items"]] == [primary["id"]]
    assert safe_matches["counts"]["matches"] == safe_live["counts"]["live"] == 1
    assert summary == before


def test_realtime_api_lists_one_fixture_and_keeps_original_match_url_accessible(
    app_module, client, monkeypatch
):
    alternate, primary = _observed_pair(app_module)
    rows = [alternate, primary]
    summary = _observed_summary(rows, live=rows)
    before = deepcopy(summary)
    _uncached_realtime(monkeypatch, app_module, summary)

    response = client.get("/api/realtime/sports?scope=all")
    original_response = client.get(f"/api/realtime/match/{alternate['id']}")

    assert response.status_code == original_response.status_code == 200
    payload = response.get_json()
    assert [row["id"] for row in payload["matches"]] == [primary["id"]]
    assert [row["id"] for row in payload["live"]] == [primary["id"]]
    assert {row["id"] for row in payload["provider_matches"]} == {
        alternate["id"], primary["id"]
    }
    assert all(row["is_live"] for row in payload["provider_matches"])
    assert payload["fixture_ids"][alternate["id"]] == primary["id"]
    assert payload["fixture_ids"][primary["id"]] == primary["id"]
    assert payload["counts"]["matches"] == payload["counts"]["live"] == 1
    original = original_response.get_json()
    assert original["ok"] is True
    assert original["match"]["id"] == alternate["id"]
    assert original["match"]["detail_url"] == f"/match/{alternate['id']}"
    assert original["match"]["is_live"] is True
    assert summary == before


def test_picks_on_both_provider_aliases_keep_two_picks_but_count_one_match(app_module):
    alternate, primary = _reported_pair(app_module)
    summary = _summary(
        [alternate, primary],
        picks=[
            {"id": "pick-sportsdb-qa", "match_id": alternate["id"]},
            {"id": "pick-api-qa", "match_id": primary["id"]},
        ],
    )
    before = deepcopy(summary)

    metrics = app_module.build_sports_metrics_contract(summary)
    with app_module.app.test_request_context("/calendar?lane=with_pick"):
        calendar = app_module.v940_calendar_context(summary, "with_pick", app_module.today_iso())

    assert metrics["picks_ready"] == 2
    assert metrics["matches_with_picks"] == 1
    assert len(calendar["matches"]) == calendar["counts"]["picks"] == 1
    assert calendar["matches"][0]["has_pick"] is True
    assert summary == before


def test_calendar_live_lane_keeps_live_alias_when_primary_is_still_scheduled(app_module):
    alternate, primary = _observed_pair(app_module, primary_status="NS")
    summary = _observed_summary([primary, alternate], live=[alternate])
    before = deepcopy(summary)

    with app_module.app.test_request_context("/calendar?lane=live"):
        calendar = app_module.v940_calendar_context(summary, "live", app_module.today_iso())

    assert [row["id"] for row in calendar["matches"]] == [alternate["id"]]
    assert calendar["counts"]["live"] == calendar["counts"]["visible"] == 1
    assert calendar["matches"][0]["status_info"]["is_live"] is True
    assert summary == before


def test_calendar_favorites_lane_keeps_favorite_alias_even_when_other_alias_has_pick(
    app_module, monkeypatch
):
    alternate, primary = _reported_pair(app_module)
    summary = _summary(
        [primary, alternate], picks=[{"id": "pick-api-qa", "match_id": primary["id"]}]
    )
    favorites = {"team": set(), "league": set(), "match": {alternate["id"]}, "all": []}
    before = deepcopy((summary, favorites))
    monkeypatch.setattr(app_module, "current_session_user", lambda: {"id": "client-qa"})
    monkeypatch.setattr(app_module, "favorite_sets", lambda: favorites)

    with app_module.app.test_request_context("/calendar?lane=favorites"):
        calendar = app_module.v940_calendar_context(summary, "favorites", app_module.today_iso())

    assert [row["id"] for row in calendar["matches"]] == [alternate["id"]]
    assert calendar["counts"]["favorites"] == calendar["counts"]["visible"] == 1
    assert calendar["matches"][0]["is_favorite"] is True
    assert (summary, favorites) == before


def test_calendar_search_finds_provider_alias_before_selecting_one_fixture(app_module):
    alternate, primary = _reported_pair(app_module)
    summary = _summary([primary, alternate])
    before = deepcopy(summary)

    with app_module.app.test_request_context("/calendar?lane=week"):
        default = app_module.v940_calendar_context(summary, "week", app_module.today_iso())
    with app_module.app.test_request_context("/calendar?lane=week&q=Real+Valladolid"):
        searched = app_module.v940_calendar_context(summary, "week", app_module.today_iso())

    assert [row["id"] for row in default["matches"]] == [primary["id"]]
    assert [row["id"] for row in searched["matches"]] == [alternate["id"]]
    assert searched["counts"]["visible"] == 1
    assert summary == before


def test_home_live_lane_counts_two_fresh_provider_observations_as_one_fixture(app_module):
    alternate, primary = _observed_pair(app_module)
    summary = _observed_summary([alternate, primary], live=[alternate, primary])
    before = deepcopy(summary)

    home = app_module.home_matchday_context(summary)

    assert [row["id"] for row in _home_rows(home)] == [primary["id"]]
    assert home["live"]["total"] == home["live"]["shown"] == 1
    assert summary == before


def test_home_live_lane_survives_scheduled_provider_alias_with_pick_after_kickoff(app_module):
    alternate, primary = _observed_pair(app_module, primary_status="NS")
    summary = _observed_summary([primary, alternate], live=[alternate])
    summary["valid_active_picks"] = [{"id": "pick-api-qa", "match_id": primary["id"]}]
    before = deepcopy(summary)

    home = app_module.home_matchday_context(summary)

    assert [row["id"] for row in _home_rows(home)] == [alternate["id"]]
    assert home["live"]["total"] == home["live"]["shown"] == 1
    assert home["today"]["total"] == home["upcoming"]["total"] == 0
    assert summary == before


def test_personal_agenda_deduplicates_before_filling_three_saved_fixture_slots(
    app_module, monkeypatch
):
    alternate, primary = _reported_pair(app_module)
    others = []
    for index, names in enumerate(
        [("Northbank", "Westfield"), ("Southbank", "Eastfield")], start=1
    ):
        kickoff = datetime.fromisoformat(primary["kickoff_iso"]) + timedelta(hours=index)
        match_id = f"af-qa-other-{index}"
        others.append({
            **primary,
            "id": match_id,
            "match_id": match_id,
            "external_id": match_id,
            "home_team": names[0],
            "away_team": names[1],
            "home_team_id": f"api-other-home-{index}",
            "away_team_id": f"api-other-away-{index}",
            "kickoff_iso": kickoff.isoformat(),
            "kickoff_time": kickoff.strftime("%H:%M"),
        })
    summary = _summary([alternate, primary, *others])
    summary["storage_status"] = "ok"
    favorites = [{"kind": "league", "value": "Segunda División"}]
    before = deepcopy((summary, favorites))
    monkeypatch.setattr(app_module, "current_user_id", lambda: "client-qa")
    monkeypatch.setattr(app_module, "get_favorites", lambda **_kwargs: favorites)

    agenda = app_module.personal_home_agenda(summary)

    assert agenda["state"] == "READY"
    assert agenda["saved_count"] == 1
    assert [row["id"] for row in agenda["matches"]] == [
        primary["id"], others[0]["id"], others[1]["id"]
    ]
    assert all(row["is_favorite"] for row in agenda["matches"])
    assert (summary, favorites) == before


def test_sports_hub_selects_one_fixture_after_attaching_pick_to_provider_alias(app_module):
    alternate, primary = _reported_pair(app_module)
    rows = [primary, alternate]
    picks = [{
        "id": "pick-sportsdb-qa", "match_id": alternate["id"],
        "selection": "QA selection", "confidence": 75,
    }]
    before = deepcopy((rows, picks))

    annotated = app_module.annotate_sports_hub_matches(rows, picks=picks)

    assert [row["id"] for row in annotated] == [alternate["id"]]
    assert annotated[0]["has_pick"] is True
    assert annotated[0]["pick_label"] == "QA selection"
    assert (rows, picks) == before


def test_match_hub_deduplicates_sections_and_counts_after_selecting_saved_aliases(
    app_module, monkeypatch
):
    alternate, primary = _observed_pair(app_module)
    matches = [alternate, primary]
    favorites = [{"kind": "match", "value": alternate["id"]}]
    picks = [{"id": "pick-api-qa", "match_id": primary["id"]}]
    before = deepcopy((matches, favorites, picks))
    monkeypatch.setattr(app_module, "cache_get", lambda _key: None)
    monkeypatch.setattr(app_module, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_module, "current_session_user", lambda: None)
    monkeypatch.setattr(app_module, "get_favorites", lambda *_args, **_kwargs: favorites)
    monkeypatch.setattr(app_module, "get_picks", lambda **_kwargs: picks)
    monkeypatch.setattr(
        app_module, "get_matches", lambda *_args, **_kwargs: deepcopy(matches)
    )
    monkeypatch.setattr(app_module, "get_upcoming_matches", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(app_module, "get_results_matches", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(app_module, "competitions", lambda: [])
    monkeypatch.setattr(app_module, "rows", lambda *_args, **_kwargs: [])

    with app_module.app.test_request_context("/match-hub?lane=live"):
        hub = app_module.match_hub(app_module.today_iso(), "live")

    assert [row["id"] for row in hub["live"]] == [primary["id"]]
    assert [row["id"] for row in hub["favorites"]] == [alternate["id"]]
    assert [row["id"] for row in hub["with_picks"]] == [primary["id"]]
    assert hub["counts"]["live"] == hub["counts"]["popular"] == 1
    assert hub["counts"]["favorites"] == hub["counts"]["with_picks"] == 1
    assert sum(hub["by_country"].values()) == 1
    assert sum(day["total"] for day in hub["calendar_grouped"]) == 1
    assert sum(group["count"] for group in hub["live_grouped"]) == 1
    assert (matches, favorites, picks) == before
