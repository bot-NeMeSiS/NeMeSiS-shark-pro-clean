from datetime import date, datetime, time
from copy import deepcopy
import json
from zoneinfo import ZoneInfo


def _labels_only_fixture(app_module, identity, source, *, kickoff=None):
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


# All native IDs/observations below are synthetic test inputs. This is not a
# claim of production/provider coverage or a crosswalk supplied by a vendor.
_REFERENCE = {"key": "laliga", "name": "LaLiga", "country": "Spain",
              "source": "API_FOOTBALL", "external_id": "140"}


def _fixture(app_module, identity, source, *, kickoff=None):
    row = _labels_only_fixture(app_module, identity, source, kickoff=kickoff)
    is_sportsdb = source == "TheSportsDB"
    event_id, league_id = (9572001, 4335) if is_sportsdb else (1570389, 140)
    home_id, away_id = (99001, 99002) if is_sportsdb else (88001, 88002)
    row.update(external_id=str(event_id), competition_id=str(league_id),
               home_team_id=str(home_id), away_team_id=str(away_id),
               season=str(date.fromisoformat(row["match_date"]).year),
               sport="soccer", sport_key="soccer")
    if is_sportsdb:
        raw = {"idEvent": str(event_id), "idLeague": str(league_id),
               "idHomeTeam": str(home_id), "idAwayTeam": str(away_id),
               "strHomeTeam": row["home_team"], "strAwayTeam": row["away_team"],
               "strTimestamp": row["kickoff_iso"], "strSeason": row["season"],
               "strCountry": row["country"], "strLeague": row["competition_name"],
               "strSport": "Soccer", "strStatus": "NS"}
    else:
        raw = {"fixture": {"id": event_id, "date": row["kickoff_iso"], "status": {"short": "NS"}},
               "league": {"id": league_id, "name": row["competition_name"],
                          "country": row["country"], "season": int(row["season"])},
               "teams": {"home": {"id": home_id, "name": row["home_team"]},
                         "away": {"id": away_id, "name": row["away_team"]}}}
    row["raw_json"] = json.dumps(raw)
    return row


def _install_references(app_module, monkeypatch, records=(_REFERENCE,)):
    calls = []
    def read(database, keys):
        assert str(database) == str(app_module.DB_PATH)
        calls.append(tuple(keys))
        return [dict(record) for record in records if record["key"] in keys]
    # Only the existing PK-reader boundary is supplied in memory. The actual
    # App operation constructor, C1/C2/C3, ownership and consumers remain real.
    monkeypatch.setattr(app_module, "_v991_references", read)
    return calls


def _prepare(app_module, monkeypatch, summary, *, records=(_REFERENCE,)):
    calls = _install_references(app_module, monkeypatch, records)
    operation = app_module._v991_prepare_summary_operation(
        summary, selected_date=app_module.today_iso(),
        current=summary["all_valid_matches"], history=(),
    )
    assert operation.matches(summary, app_module.today_iso())
    assert len(calls) <= 1
    return operation


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


def test_calendar_collapses_cross_provider_copy_and_keeps_primary_row(app_module, monkeypatch):
    alternate = _fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB")
    primary = _fixture(app_module, "af-1570389", "API_FOOTBALL")
    summary = _summary([alternate, primary])

    with app_module.app.test_request_context("/calendario?lane=week"):
        _prepare(app_module, monkeypatch, summary)
        context = app_module.v940_calendar_context(summary, "week", app_module.today_iso())

    assert [match["id"] for match in context["matches"]] == ["af-1570389"]
    assert context["counts"]["all"] == context["counts"]["visible"] == 1
    assert context["counts"]["tomorrow"] == 1
    assert sum(facet["count"] for facet in context["facets"]["countries"]) == 1


def test_calendar_today_counter_uses_the_unique_display_rows(app_module, monkeypatch):
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
        _prepare(app_module, monkeypatch, summary)
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
    reference_calls = _install_references(app_module, monkeypatch)
    finalized = []
    def supplied_base(_route, _scope, selected_date, **_kwargs):
        # This source fixture enters the actual coordinator finalization inside
        # the real HTTP request. Hydration/context/metrics/calendar stay real.
        result, operation = app_module._v991_finish_summary(
            deepcopy(summary), selected_date=selected_date,
        )
        assert operation.matches(result, selected_date)
        finalized.append(operation)
        return {}, result
    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", supplied_base)

    response = client.get("/api/calendar?lane=week")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"] == app_module.APP_VERSION
    assert [match["id"] for match in payload["matches"]] == ["af-1570389"]
    assert payload["calendar"]["counts"]["visible"] == 1
    assert len(finalized) == 1
    assert reference_calls == [("laliga",)]
    assert payload["calendar"]["identity_state"] == "PREPARED"


def test_calendar_duplicate_keeps_the_row_linked_to_a_pick(app_module, monkeypatch):
    alternate = _fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB")
    primary = _fixture(app_module, "af-1570389", "API_FOOTBALL")
    summary = _summary(
        [primary, alternate],
        picks=[{"id": "pick-1", "match_id": alternate["id"]}],
    )

    with app_module.app.test_request_context("/calendario?lane=with_pick"):
        _prepare(app_module, monkeypatch, summary)
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
        _prepare(app_module, monkeypatch, summary)
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



def test_calendar_labels_only_without_context_stay_two_original_observations(app_module):
    # Preserve the old positive fixture as an explicit fail-closed negative.
    rows = [_labels_only_fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB"),
            _labels_only_fixture(app_module, "af-1570389", "API_FOOTBALL")]
    with app_module.app.test_request_context("/calendario?lane=week"):
        context = app_module.v940_calendar_context(_summary(rows), "week", app_module.today_iso())
    assert len(context["matches"]) == 2
    assert {row["id"] for row in context["matches"]} == {row["id"] for row in rows}
    assert context["identity_state"] == "UNPREPARED"


def test_calendar_prepared_but_reference_missing_stays_two(app_module, monkeypatch):
    rows = [_fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB"),
            _fixture(app_module, "af-1570389", "API_FOOTBALL")]
    summary = _summary(rows)
    with app_module.app.test_request_context("/calendario?lane=week"):
        operation = _prepare(app_module, monkeypatch, summary, records=())
        context = app_module.v940_calendar_context(summary, "week", app_module.today_iso())
    assert all(operation.snapshot.context_for(row).state != "RESOLVED" for row in rows)
    assert len(context["matches"]) == 2


def test_calendar_prepared_country_conflict_does_not_borrow_other_context(app_module, monkeypatch):
    base = _fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB")
    primary = _fixture(app_module, "af-1570389", "API_FOOTBALL")
    foreign = _fixture(app_module, "af-other-country", "API_FOOTBALL")
    foreign["country"] = "Portugal"
    raw = json.loads(foreign["raw_json"])
    raw["league"]["country"] = "Portugal"
    foreign["raw_json"] = json.dumps(raw)
    rows = [base, primary, foreign]
    summary = _summary(rows)
    with app_module.app.test_request_context("/calendario?lane=week"):
        operation = _prepare(app_module, monkeypatch, summary)
        context = app_module.v940_calendar_context(summary, "week", app_module.today_iso())
    assert operation.snapshot.context_for(foreign).state != "RESOLVED"
    assert len(context["matches"]) == 2
    assert "af-other-country" in {row["id"] for row in context["matches"]}


def test_calendar_prepared_kickoff_conflict_stays_separate(app_module, monkeypatch):
    base = _fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB")
    primary = _fixture(app_module, "af-1570389", "API_FOOTBALL")
    other = _fixture(app_module, "af-other-kickoff", "API_FOOTBALL",
        kickoff=datetime.combine(date.fromisoformat(app_module.today_iso(1)), time(20, 2),
                                 tzinfo=ZoneInfo("Europe/Madrid")))
    other["external_id"] = "1570390"
    raw = json.loads(other["raw_json"])
    raw["fixture"]["id"] = 1570390
    other["raw_json"] = json.dumps(raw)
    summary = _summary([base, primary, other])
    with app_module.app.test_request_context("/calendario?lane=week"):
        _prepare(app_module, monkeypatch, summary)
        context = app_module.v940_calendar_context(summary, "week", app_module.today_iso())
    assert len(context["matches"]) == 2
    assert "af-other-kickoff" in {row["id"] for row in context["matches"]}


def test_calendar_inconsistent_native_league_cannot_authorize_grouping(app_module, monkeypatch):
    base = _fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB")
    inconsistent = _fixture(app_module, "af-inconsistent", "API_FOOTBALL")
    raw = json.loads(inconsistent["raw_json"])
    raw["league"]["id"] = 39
    inconsistent["raw_json"] = json.dumps(raw)
    summary = _summary([base, inconsistent])
    with app_module.app.test_request_context("/calendario?lane=week"):
        operation = _prepare(app_module, monkeypatch, summary)
        context = app_module.v940_calendar_context(summary, "week", app_module.today_iso())
    # A resolved competition reference is not proof of this row's native event.
    # Its explicit API140 key can resolve while its own raw league39 disagrees.
    from engines.fixture_realtime_projection import verified_api_fixture_id
    assert operation.snapshot.context_for(inconsistent).state == "RESOLVED"
    assert verified_api_fixture_id(inconsistent, app_module.match_kickoff_madrid_dt) is None
    selection = operation.snapshot.select("current")
    assert selection.count == 2
    assert any(len(group) == 1 and group[0] is inconsistent for group in selection.groups)
    assert len(context["matches"]) == 2


def test_calendar_same_native_event_with_conflicting_kickoff_blocks_native_cohort(app_module, monkeypatch):
    base = _fixture(app_module, "sportsdb-levante-athletic", "TheSportsDB")
    primary = _fixture(app_module, "af-1570389", "API_FOOTBALL")
    contradictory = _fixture(app_module, "af-conflicting-claim", "API_FOOTBALL",
        kickoff=datetime.combine(date.fromisoformat(app_module.today_iso(1)), time(20, 2),
                                 tzinfo=ZoneInfo("Europe/Madrid")))
    # Both API originals independently claim the same native event at different
    # own, internally consistent kickoffs: neither may authorize a grouped winner.
    summary = _summary([base, primary, contradictory])
    with app_module.app.test_request_context("/calendario?lane=week"):
        operation = _prepare(app_module, monkeypatch, summary)
        context = app_module.v940_calendar_context(summary, "week", app_module.today_iso())
    selected = operation.snapshot.select("current")
    assert len(context["matches"]) == 3
    assert selected.count == 3
    assert selected.identity_basis.count("CONFLICT_NATIVE_OBSERVATIONS") == 2
