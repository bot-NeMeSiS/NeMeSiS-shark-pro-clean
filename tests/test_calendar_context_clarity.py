"""Calendar navigation and ordering over synthetic existing snapshots; no IO."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import pytest


def query(href):
    parsed = urlsplit(href)
    assert parsed.path == "/calendar" and not parsed.netloc
    values = parse_qs(parsed.query)
    assert all(len(value) == 1 for value in values.values())
    return {key: value[0] for key, value in values.items()}


def filters(**changes):
    return {
        "lane": "today", "date": "2026-03-29", "q": "Club QA",
        "league": "Liga QA", "country": "España", "team": "Club QA",
        "status": "Próximo", "sort": "time", "with_pick": "1", **changes,
    }


def row(app_module, identity, clock, *, competition="laliga", rank=10, qa_rank=0):
    day = app_module.today_iso(1)
    kickoff = datetime.combine(date.fromisoformat(day), time.fromisoformat(clock),
                               tzinfo=ZoneInfo("Europe/Madrid"))
    return {
        "id": identity, "home_team": "Local " + identity,
        "away_team": "Visitante " + identity, "competition_key": competition,
        "competition_name": "LaLiga" if competition == "laliga" else "Liga QA",
        "country": "Spain", "source": "SIMULATED_QA", "status": "NS",
        "match_date": day, "kickoff_time": clock, "kickoff_iso": kickoff.isoformat(),
        "calendar_rank": rank, "qa_rank": qa_rank,
        "sports_relevance": {"competition_rank": rank, "score": 100 - qa_rank},
    }


@pytest.mark.parametrize("lane", ["today", "finished", "results", "week", "live"])
def test_primary_tabs_keep_discovery_and_compatible_dates(app_module, lane):
    selected = filters(lane=lane)
    original = deepcopy(selected)
    tabs = app_module._v940_calendar_primary_tabs(selected)
    assert [item["key"] for item in tabs] == ["live", "finished", "today", "week", "with_pick"]
    assert tabs[0] == {"key": "live", "label": "Directo", "href": "/directo"}
    for tab in tabs:
        if tab["key"] == "live":
            continue
        state = query(tab["href"])
        assert state["lane"] == tab["key"]
        for key in ("q", "league", "country", "team", "sort", "with_pick"):
            assert state[key] == selected[key]
        expected_date = selected["date"] if tab["key"] in {"today", "finished"} else app_module.today_iso()
        assert state["date"] == expected_date
    assert selected == original


@pytest.mark.parametrize("lane", ["today", "week", "live", "finished", "results"])
def test_entering_results_replaces_the_previous_status_filter(app_module, lane):
    tabs = {tab["key"]: query(tab["href"])
            for tab in app_module._v940_calendar_primary_tabs(filters(lane=lane))
            if tab["key"] != "live"}
    current = "finished" if lane == "results" else lane
    assert ("status" in tabs["finished"]) == (current == "finished")
    for target in ("today", "week", "with_pick"):
        assert tabs[target]["status"] == "Próximo"


@pytest.mark.parametrize("lane,expected_lane", [
    ("finished", "finished"), ("results", "results"), ("today", "today"),
    ("tomorrow", "today"), ("week", "today"), ("live", "today"),
])
@pytest.mark.parametrize("selected_day", ["2026-03-29", "2026-10-25", "2026-12-31"])
def test_date_controls_keep_the_selected_results_view_and_filters(app_module, lane, expected_lane, selected_day):
    selected = filters(lane=lane, date=selected_day)
    navigation = app_module._design02_calendar_date_navigation(selected)
    assert navigation["lane"] == expected_lane
    assert navigation["selected"] == selected_day
    links = [(navigation["previous"], (date.fromisoformat(selected_day) - timedelta(days=1)).isoformat()),
             (navigation["next"], (date.fromisoformat(selected_day) + timedelta(days=1)).isoformat())]
    links.extend((item["href"], app_module.today_iso(offset))
                 for offset, item in zip((-1, 0, 1), navigation["shortcuts"]))
    for href, expected_date in links:
        state = query(href)
        assert state["lane"] == expected_lane and state["date"] == expected_date
        for key in ("q", "league", "country", "team", "status", "sort", "with_pick"):
            assert state[key] == selected[key]


def test_time_order_survives_grouping_without_changing_default_importance(app_module, monkeypatch):
    matches = [row(app_module, str(index), clock, qa_rank=index)
               for index, clock in enumerate(("18:30", "21:00", "14:00", "16:15"))]
    # An early final result remains early in clock order; state does not move it.
    matches[2].update(status="FT", home_score=0, away_score=0)
    # Competition grouping remains by its existing priority, not first kickoff.
    matches.append(row(app_module, "other-league", "10:00", competition="qa-local", rank=80))
    original = deepcopy(matches)
    monkeypatch.setattr(app_module, "sports_relevance_sort_tuple", lambda item, surface: (item["qa_rank"],))
    chronological = app_module._calendar_group(app_module._calendar_sort(matches, "time"), "time")
    default = app_module._calendar_group(app_module._calendar_sort(matches, "importance"))
    assert len(chronological) == 1 and len(chronological[0]["leagues"]) == 2
    assert [item["id"] for item in chronological[0]["leagues"][0]["matches"]] == ["2", "3", "0", "1"]
    assert [item["id"] for item in default[0]["leagues"][0]["matches"]] == ["0", "1", "2", "3"]
    assert chronological[0]["leagues"][1]["matches"][0]["id"] == "other-league"
    assert chronological[0]["leagues"][0]["matches"][0]["home_score"] == 0
    assert matches == original


@pytest.mark.parametrize("count", [0, 1, 2])
def test_global_context_describes_selection_not_first_league_and_adds_no_io(app_module, monkeypatch, count):
    matches = [row(app_module, "top", "18:30"),
               row(app_module, "local", "14:00", competition="qa-local", rank=80)][:count]
    summary = {"all_valid_matches": matches, "valid_upcoming_matches": matches,
               "valid_matches_today": [], "valid_live_events": [], "valid_active_picks": []}
    original = deepcopy(summary)
    monkeypatch.setattr(app_module, "current_session_user", lambda: None)

    def forbidden(*args, **kwargs):
        pytest.fail("Calendar presentation must reuse the supplied snapshot")

    for name in ("db", "rows", "one", "favorite_sets", "dashboard_data", "get_public_home_sports_summary"):
        monkeypatch.setattr(app_module, name, forbidden)
    selected_day = app_module.today_iso(1)
    with app_module.app.test_request_context("/calendar?date=" + selected_day + "&sort=time"):
        context = app_module.v940_calendar_context(summary, "today", selected_day)
    assert context["default_context"] == app_module.date_display_label(selected_day)
    assert context["default_context"] == context["selected_summary"]["title"]
    assert context["competition_count"] == context["counts"]["leagues"] == count
    assert isinstance(context["competition_count"], int)
    assert len(context["primary_tabs"]) == 5
    assert context["date_navigation"]["lane"] == "today"
    assert context["counts"]["visible"] == count
    if count:
        assert context["source_summary"] == "Partidos disponibles por día y competición. Horarios de Madrid."
        assert "LaLiga" not in context["default_context"]
    assert summary == original
