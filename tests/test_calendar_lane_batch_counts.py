"""Calendar date/lane count batches preserve original fixture evidence.

Expected counts are independent fixture facts. Ranked display representatives,
day boundaries, history, aliases and owner validation stay on the real App path.
Ordinary cases supply only the established synthetic competition reader.
Explicit fault-injection cases delegate to the real batch/selection checks;
they do not replace identity preparation or the LOCALSAFE guard."""

from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, time, timedelta
import json
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import pytest

from engines.fixture_snapshot_read_model import PreparedFixtureSnapshot
from tests.test_v957_calendar_fixture_deduplication import (
    _REFERENCE,
    _fixture,
    _install_references,
    _labels_only_fixture,
    _summary,
)


MADRID = ZoneInfo("Europe/Madrid")


def _kickoff(app, offset=1, minute=0):
    return datetime.combine(
        date.fromisoformat(app.today_iso(offset)), time(20, minute), tzinfo=MADRID
    )


def _pair(app, number=1, *, offset=1, minute=0, status="NS", kickoff=None):
    """A known cross-provider copy; distinct numbers have distinct native IDs."""
    start = kickoff or _kickoff(app, offset, minute)
    rows = [
        _fixture(app, "af-count-" + str(number), "API_FOOTBALL", kickoff=start),
        _fixture(app, "sportsdb-count-" + str(number), "TheSportsDB", kickoff=start),
    ]
    for row in rows:
        raw = json.loads(row["raw_json"])
        native = (1570389 if row["source"] == "API_FOOTBALL" else 9572001) + number
        row.update(external_id=str(native), status=status)
        if row["source"] == "API_FOOTBALL":
            raw["fixture"].update(id=native, status={"short": status})
        else:
            raw.update(idEvent=str(native), strStatus=status)
        if status == "FT":
            row.update(home_score=2, away_score=1, score="2-1")
            if row["source"] == "API_FOOTBALL":
                raw["goals"] = {"home": 2, "away": 1}
            else:
                raw.update(intHomeScore="2", intAwayScore="1")
        row["raw_json"] = json.dumps(raw)
    return rows


def _prepare(app, monkeypatch, summary, *, selected=None, history=(), records=(_REFERENCE,)):
    selected = selected or app.today_iso()
    history = list(history)
    historical_objects = {id(row) for row in history}
    current = [row for row in summary["all_valid_matches"] if id(row) not in historical_objects]
    calls = _install_references(app, monkeypatch, records)
    operation = app._v991_prepare_summary_operation(
        summary, selected_date=selected, current=current, history=history
    )
    assert operation.matches(summary, selected)
    assert len(calls) <= 1
    return operation


def _calendar(app, summary, operation, *, lane="week", selected=None, **filters):
    selected = selected or app.today_iso()
    query = urlencode({"lane": lane, "date": selected, **filters})
    with app.app.test_request_context("/calendario?" + query):
        return app.v940_calendar_context(summary, lane, selected, fixture_operation=operation)


def _day_count(calendar, day):
    return next(chip["count"] for chip in calendar["date_chips"] if chip["date"] == day)


def _count_fields(calendar, **expected):
    assert {key: calendar["counts"][key] for key in expected} == expected


def test_materialized_date_and_all_lane_counts_keep_independent_fixture_totals(app_module, monkeypatch):
    app = app_module
    today = _pair(app, 11, offset=0, minute=59)
    tomorrow = _pair(app, 12)
    edge = _pair(app, 13, offset=7)
    outside = _pair(app, 14, offset=8)
    finished = _pair(app, 15, offset=0, minute=2, status="FT")
    pending = _pair(app, 16, offset=0, minute=4, status="RESULT_PENDING")
    now = datetime.now(MADRID)
    live_start = max((now - timedelta(minutes=20)).replace(second=0, microsecond=0),
                     now.replace(hour=0, minute=0, second=0, microsecond=0))
    live = _pair(app, 17, status="1H", kickoff=live_start)
    for row in live:
        row.update(minute=20, live_updated_at=now.isoformat(),
                   provider_updated_at=now.isoformat(), last_synced_at=now.isoformat())
    # These are ordinary source facts, not a user/authentication substitute.
    today[1]["is_favorite"] = True
    rows = today + tomorrow + edge + outside + finished + pending + live
    summary = _summary(rows, picks=[{"id": "count-pick", "match_id": tomorrow[1]["id"]}])
    summary.update(valid_matches_today=today + finished + pending + live,
                   valid_live_events=live, finished_matches=finished, incident_matches=pending)
    original = deepcopy(summary)
    operation = _prepare(app, monkeypatch, summary)

    calendar = _calendar(app, summary, operation)

    # Four today fixtures + tomorrow + inclusive day seven; day eight is outside.
    _count_fields(calendar, all=6, visible=6, today=4, tomorrow=1, week=6,
                  live=1, picks=1, favorites=1, finished=1, incidents=1)
    assert _day_count(calendar, app.today_iso()) == 4
    assert _day_count(calendar, app.today_iso(1)) == 1
    assert calendar["count_identity_state"] == "PREPARED"
    assert summary == original


def test_repeated_object_and_equal_copied_native_row_are_one_fixture(app_module, monkeypatch):
    app = app_module
    primary, alternate = _pair(app, 21)
    copied = deepcopy(primary)
    summary = _summary([primary, primary, copied, alternate])
    operation = _prepare(app, monkeypatch, summary)

    calendar = _calendar(app, summary, operation)

    _count_fields(calendar, all=1, visible=1, tomorrow=1, week=1)
    assert _day_count(calendar, app.today_iso(1)) == 1
    assert calendar["count_identity_state"] == "PREPARED"
    assert copied is not primary and copied == primary


def test_equal_unknown_copies_with_same_string_id_remain_original_observations(app_module, monkeypatch):
    app = app_module
    first = _labels_only_fixture(app, "same-unknown-id", "unknown-provider")
    # Label text and an unknown provider supply no canonical/native reference.
    first.pop("competition_key")
    second = deepcopy(first)
    summary = _summary([first, first, second])
    operation = _prepare(app, monkeypatch, summary)

    calendar = _calendar(app, summary, operation)

    _count_fields(calendar, all=2, visible=2, tomorrow=2, week=2)
    assert _day_count(calendar, app.today_iso(1)) == 2
    assert calendar["count_identity_state"] == "PREPARED"
    assert operation.snapshot.context_for(first).state != "RESOLVED"


@pytest.mark.parametrize("alias", ["Athletic Club", "Athletic Bilbao"])
def test_alias_filter_changes_winner_but_not_unfiltered_date_or_lane_counts(app_module, monkeypatch, alias):
    app = app_module
    primary, alternate = _pair(app, 31)
    summary = _summary([primary, alternate])
    operation = _prepare(app, monkeypatch, summary)

    calendar = _calendar(app, summary, operation, team=alias)

    _count_fields(calendar, all=1, visible=1, tomorrow=1, week=1)
    expected_id = alternate["id"] if alias == "Athletic Club" else primary["id"]
    assert [row["id"] for row in calendar["matches"]] == [expected_id]
    assert _day_count(calendar, app.today_iso(1)) == 1
    assert calendar["count_identity_state"] == "PREPARED"


def test_same_native_event_contradicting_own_kickoff_counts_three(app_module, monkeypatch):
    app = app_module
    primary, alternate = _pair(app, 41)
    contradictory, _unused = _pair(app, 41, minute=2)
    contradictory["id"] = contradictory["match_id"] = "af-count-conflicting-claim"
    summary = _summary([alternate, primary, contradictory])
    operation = _prepare(app, monkeypatch, summary)

    calendar = _calendar(app, summary, operation)

    _count_fields(calendar, all=3, visible=3, tomorrow=3, week=3)
    assert _day_count(calendar, app.today_iso(1)) == 3
    assert calendar["count_identity_state"] == "PREPARED"


def test_canonical_country_conflict_is_retained_as_separate_observation(app_module, monkeypatch):
    app = app_module
    primary, alternate = _pair(app, 51)
    foreign = deepcopy(primary)
    foreign["id"] = foreign["match_id"] = "af-count-country-conflict"
    foreign["country"] = "Portugal"
    raw = json.loads(foreign["raw_json"])
    raw["league"]["country"] = "Portugal"
    foreign["raw_json"] = json.dumps(raw)
    summary = _summary([primary, alternate, foreign])
    operation = _prepare(app, monkeypatch, summary)

    calendar = _calendar(app, summary, operation)

    _count_fields(calendar, all=2, visible=2, tomorrow=2, week=2)
    assert foreign["id"] in {row["id"] for row in calendar["matches"]}
    assert operation.snapshot.context_for(foreign).state != "RESOLVED"
    assert calendar["count_identity_state"] == "PREPARED"


def test_missing_competition_reference_does_not_join_cross_provider_labels(app_module, monkeypatch):
    app = app_module
    rows = _pair(app, 61)
    summary = _summary(rows)
    operation = _prepare(app, monkeypatch, summary, records=())

    calendar = _calendar(app, summary, operation)

    _count_fields(calendar, all=2, visible=2, tomorrow=2, week=2)
    assert _day_count(calendar, app.today_iso(1)) == 2
    assert calendar["count_identity_state"] == "PREPARED"


def test_selected_history_date_keeps_original_partition_and_current_day_counters(app_module, monkeypatch):
    app = app_module
    selected = app.today_iso(-2)
    current = _pair(app, 71, offset=0)
    history = _pair(app, 72, offset=-2, status="FT")
    other_history = _pair(app, 73, offset=-3, status="FT")
    summary = _summary(current + history + other_history)
    summary.update(valid_upcoming_matches=current, valid_matches_today=current,
                   finished_matches=history + other_history,
                   historical_results_date=selected, historical_results_count=2,
                   historical_results_read_state="VERIFIED")
    original = deepcopy(summary)
    operation = _prepare(app, monkeypatch, summary, selected=selected, history=history + other_history)

    calendar = _calendar(app, summary, operation, lane="finished", selected=selected)

    _count_fields(calendar, all=1, visible=1, today=1, week=1, finished=1)
    assert _day_count(calendar, selected) == 1
    assert [row["id"] for row in calendar["matches"]] == [history[0]["id"]]
    assert calendar["historical_results_read_state"] == "VERIFIED"
    assert len(operation.snapshot.cohorts["history"]) == 4
    assert calendar["count_identity_state"] == "PREPARED"
    assert summary == original


@pytest.mark.parametrize("lane,visible", [("finished", 1), ("results", 2)])
def test_finished_and_results_preserve_pending_difference_without_changing_date_total(app_module, monkeypatch, lane, visible):
    app = app_module
    selected = app.today_iso(-1)
    finished = _pair(app, 81, offset=-1, status="FT")
    pending = _pair(app, 82, offset=-1, minute=2, status="RESULT_PENDING")
    summary = _summary(finished + pending)
    summary.update(valid_upcoming_matches=[], finished_matches=finished, incident_matches=pending)
    operation = _prepare(app, monkeypatch, summary, selected=selected, history=finished + pending)

    calendar = _calendar(app, summary, operation, lane=lane, selected=selected)

    _count_fields(calendar, all=visible, visible=visible, finished=1, incidents=1, today=0, week=0)
    assert _day_count(calendar, selected) == 2
    assert calendar["count_identity_state"] == "PREPARED"


@pytest.mark.parametrize("priority", ["provider", "pick", "favorite"])
def test_count_only_batch_does_not_replace_ranked_display_winner(app_module, monkeypatch, priority):
    app = app_module
    primary, alternate = _pair(app, 91)
    picks = []
    if priority == "pick":
        picks = [{"id": "ranked-count-pick", "match_id": alternate["id"]}]
    elif priority == "favorite":
        alternate["is_favorite"] = True
    summary = _summary([alternate, primary], picks=picks)
    operation = _prepare(app, monkeypatch, summary)

    calendar = _calendar(app, summary, operation)

    winner = primary if priority == "provider" else alternate
    assert [row["id"] for row in calendar["matches"]] == [winner["id"]]
    _count_fields(calendar, all=1, visible=1, tomorrow=1, week=1,
                  picks=int(priority == "pick"), favorites=int(priority == "favorite"))
    assert calendar["count_identity_state"] == "PREPARED"


@pytest.mark.parametrize("invalid", ["foreign_owner", "other_selected_date"])
def test_count_batch_refuses_invalid_owner_or_selected_date(app_module, monkeypatch, invalid):
    app = app_module
    summary = _summary(_pair(app, 101))
    original = _prepare(app, monkeypatch, summary)
    if invalid == "foreign_owner":
        operation = replace(original, summary=dict(summary))
    else:
        selected = app.today_iso(1)
        operation = replace(original, selected_date=selected,
                            generation=app._v991_generation(original.snapshot, selected))
        assert operation.matches(summary, selected)

    calendar = _calendar(app, summary, operation)

    _count_fields(calendar, all=2, visible=2, tomorrow=2, week=2)
    assert _day_count(calendar, app.today_iso(1)) == 2
    assert calendar["identity_state"] == calendar["count_identity_state"] == "UNPREPARED"
    assert calendar["facet_identity_state"] == "UNPREPARED"


def _observe_count_batch(app, monkeypatch, operation, after_first_group):
    """FAULT INJECTION observer; delegates to both unchanged real boundaries."""
    real_batch = app._v991_count_cohorts
    real_select = PreparedFixtureSnapshot.select_rows
    probe = {"armed": False, "injected": False, "selections": [], "batches": []}

    def observed_select(snapshot, values, **kwargs):
        values = tuple(values)
        result = real_select(snapshot, values, **kwargs)
        if probe["armed"] and snapshot is operation.snapshot:
            probe["selections"].append(result.count)
            if not probe["injected"] and result.count == 1 and len({id(row) for row in values}) == 2:
                probe["injected"] = True
                after_first_group()
        return result

    def observed_batch(summary, cohorts, **kwargs):
        is_count_batch = any(isinstance(key, tuple) and len(key) == 2 and key[0] in {"date", "lane"}
                             for key in cohorts)
        probe["armed"] = is_count_batch
        try:
            result = real_batch(summary, cohorts, **kwargs)
            if is_count_batch:
                probe["batches"].append(result)
            return result
        finally:
            probe["armed"] = False

    monkeypatch.setattr(PreparedFixtureSnapshot, "select_rows", observed_select)
    monkeypatch.setattr(app, "_v991_count_cohorts", observed_batch)
    return probe


def test_fault_injection_owner_mutation_discards_all_early_trusted_count_results(app_module, monkeypatch):
    app = app_module
    rows = _pair(app, 111)
    summary = _summary(rows)
    operation = _prepare(app, monkeypatch, summary)
    probe = _observe_count_batch(app, monkeypatch, operation,
                                lambda: summary["valid_matches_today"].append(rows[0]))

    calendar = _calendar(app, summary, operation)

    assert probe["injected"] and len(probe["batches"]) == 1
    batch = probe["batches"][0]
    assert probe["selections"][0] == 1  # A trusted early result must be discarded.
    assert batch.identity_state == calendar["count_identity_state"] == "UNPREPARED"
    assert _day_count(calendar, app.today_iso(1)) == 2
    _count_fields(calendar, week=2, tomorrow=2)
    # Source/filtered selection completed before this deliberately injected fault.
    _count_fields(calendar, all=1, visible=1)
    assert not operation.matches(summary)
    assert calendar["facet_identity_state"] == "UNPREPARED"


def test_fault_injection_identity_mutation_reprojects_later_count_subsets(app_module, monkeypatch):
    app = app_module
    rows = _pair(app, 121)
    summary = _summary(rows)
    operation = _prepare(app, monkeypatch, summary)

    def mutate_identity():
        for row in rows:
            row.update(home_canonical_team_id="synthetic-changed-count-home",
                       away_canonical_team_id="synthetic-changed-count-away")

    probe = _observe_count_batch(app, monkeypatch, operation, mutate_identity)
    calendar = _calendar(app, summary, operation)

    assert probe["injected"] and len(probe["batches"]) == 1
    assert 1 in probe["selections"] and 2 in probe["selections"]
    assert operation.matches(summary)  # Ownership can survive a rejected C3 projection.
    assert all(operation.snapshot.context_for(row).state == "UNKNOWN_IDENTITY_CHANGED" for row in rows)
    assert calendar["count_identity_state"] == "PREPARED"
    # The first date/week subset was observed before mutation; the later one
    # must project the changed originals afresh. No atomicity is asserted.
    assert {_day_count(calendar, app.today_iso(1)), calendar["counts"]["week"]} == {1, 2}
    _count_fields(calendar, all=1, visible=1)
    assert calendar["facet_identity_state"] == "PREPARED"


def test_singleton_count_fault_invalidates_owner_at_batch_exit(app_module, monkeypatch):
    app = app_module
    row = _pair(app, 131)[0]
    summary = _summary([row])
    operation = _prepare(app, monkeypatch, summary)
    original_checked = PreparedFixtureSnapshot._checked_identity
    observed = []

    def change_membership_after_real_check(snapshot, current):
        result = original_checked(snapshot, current)
        if snapshot is operation.snapshot:
            observed.append((current is row, result[0].state))
            if len(observed) == 1:
                summary["valid_matches_today"].append(row)
        return result

    monkeypatch.setattr(PreparedFixtureSnapshot, "_checked_identity", change_membership_after_real_check)
    result = app._v991_count_cohorts(
        summary, {"first": [row], "second": [row]}, fixture_operation=operation
    )
    assert observed == [(True, "RESOLVED"), (True, "RESOLVED")]
    assert result.identity_state == "UNPREPARED"
    assert result.counts == {"first": 1, "second": 1}
    assert not operation.matches(summary)


def test_equal_copies_with_verified_canonical_reference_have_one_fixture(app_module, monkeypatch):
    app = app_module
    first = _labels_only_fixture(app, "same-canonically-scoped-id", "unknown-provider")
    second = deepcopy(first)
    summary = _summary([first, first, second])
    operation = _prepare(app, monkeypatch, summary)
    # This is the unchanged original selector, independent of count_rows.
    original = app._v991_selected(summary, [first, second], fixture_operation=operation)
    assert operation.snapshot.context_for(first).state == "RESOLVED"
    assert original.count == 1
    assert original.identity_basis == ("CANONICAL_COMPETITION",)
    calendar = _calendar(app, summary, operation)
    _count_fields(calendar, all=1, visible=1, tomorrow=1, week=1)
    assert _day_count(calendar, app.today_iso(1)) == 1
    assert calendar["count_identity_state"] == "PREPARED"
