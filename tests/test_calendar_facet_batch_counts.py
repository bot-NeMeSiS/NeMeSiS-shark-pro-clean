"""Count original facet cohorts without caching mutable fixture identities.

The only supplied boundary is the synthetic competition-reference reader already
used by Calendar's identity regressions. Operation ownership, grouping and C3
projection remain the real App and snapshot code. No provider/App substitutes.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, time
import json
from types import MappingProxyType
from zoneinfo import ZoneInfo

import pytest

from engines.fixture_snapshot_read_model import PreparedFixtureSnapshot
from tests.test_v957_calendar_fixture_deduplication import (
    _fixture,
    _labels_only_fixture,
    _prepare,
    _summary,
)


def _pair(app):
    return [
        _fixture(app, "af-facet-primary", "API_FOOTBALL"),
        _fixture(app, "sportsdb-facet-alternate", "TheSportsDB"),
    ]


def _unique_primary(app, number, *, home=None):
    row = _fixture(app, "af-facet-unique-" + str(number), "API_FOOTBALL")
    raw = json.loads(row["raw_json"])
    native_id = 95000000 + number
    row.update(
        external_id=str(native_id),
        home_team=home or "Synthetic home " + str(number),
        away_team="Synthetic away " + str(number),
        home_team_id=str(96000000 + number * 2),
        away_team_id=str(96000001 + number * 2),
    )
    raw["fixture"]["id"] = native_id
    raw["teams"]["home"].update(id=int(row["home_team_id"]), name=row["home_team"])
    raw["teams"]["away"].update(id=int(row["away_team_id"]), name=row["away_team"])
    row["raw_json"] = json.dumps(raw)
    return row


def test_batch_matches_individual_selection_of_original_cohorts(app_module, monkeypatch):
    app = app_module
    primary, alternate = _pair(app)
    contradictory = _fixture(
        app,
        "af-facet-conflicting-native-claim",
        "API_FOOTBALL",
        kickoff=datetime.combine(
            date.fromisoformat(app.today_iso(1)), time(20, 2), tzinfo=ZoneInfo("Europe/Madrid")
        ),
    )
    unknown = [
        _labels_only_fixture(app, "unknown-facet-a", "unknown-provider"),
        _labels_only_fixture(app, "unknown-facet-b", "unknown-provider"),
    ]
    rows = [primary, alternate, contradictory, *unknown]
    summary = _summary(rows)
    original = deepcopy(summary)
    operation = _prepare(app, monkeypatch, summary)
    cohorts = {
        ("teams", "primary alias"): [primary],
        ("teams", "secondary alias"): [alternate],
        ("teams", "shared alias"): [primary, alternate],
        ("leagues", "native kickoff conflict"): [primary, alternate, contradictory],
        ("countries", "unknown observations"): unknown,
        ("teams", "same object twice"): [primary, primary, alternate],
        ("teams", "empty"): [],
    }
    expected = {
        key: app._v991_selected(summary, values, fixture_operation=operation).count
        for key, values in cohorts.items()
    }

    actual = app._v991_count_cohorts(summary, cohorts, fixture_operation=operation)

    assert actual.identity_state == "PREPARED"
    assert actual.counts == expected
    assert actual.counts[("teams", "shared alias")] == 1
    assert actual.counts[("leagues", "native kickoff conflict")] == 3
    assert actual.counts[("countries", "unknown observations")] == 2
    assert actual.counts[("teams", "same object twice")] == 1
    assert summary == original


@pytest.mark.parametrize(
    "invalid",
    ("no_operation", "explicit_false", "foreign_owner", "generation", "date", "membership", "snapshot"),
)
def test_batch_never_borrows_invalid_operation(app_module, monkeypatch, invalid):
    app = app_module
    rows = _pair(app)
    summary = _summary(rows)
    operation = _prepare(app, monkeypatch, summary)
    candidate = operation
    if invalid == "no_operation":
        candidate = None  # No request context exists from which to borrow one.
    elif invalid == "explicit_false":
        candidate = False
    elif invalid == "foreign_owner":
        candidate = replace(operation, summary=dict(summary))
    elif invalid == "generation":
        candidate = replace(operation, generation="not-the-prepared-generation")
    elif invalid == "date":
        candidate = replace(operation, selected_date=app.today_iso(1))
    elif invalid == "membership":
        candidate = replace(operation, membership=())
    elif invalid == "snapshot":
        foreign_rows = [deepcopy(row) for row in rows]
        foreign_summary = _summary(foreign_rows)
        foreign = _prepare(app, monkeypatch, foreign_summary)
        candidate = replace(operation, snapshot=foreign.snapshot)

    actual = app._v991_count_cohorts(
        summary,
        {"pair": [rows[0], rows[0], rows[1]], "secondary": [rows[1]], "empty": []},
        fixture_operation=candidate,
    )

    assert actual.identity_state == "UNPREPARED"
    assert actual.counts == {"pair": 2, "secondary": 1, "empty": 0}


@pytest.mark.parametrize("change", ("append", "order", "lane_membership"))
def test_persistent_owner_membership_change_discards_entire_batch(app_module, monkeypatch, change):
    app = app_module
    rows = _pair(app)
    summary = _summary(rows)
    operation = _prepare(app, monkeypatch, summary)
    select_rows = PreparedFixtureSnapshot.select_rows
    calls = []

    def observed(snapshot, values, **kwargs):
        result = select_rows(snapshot, values, **kwargs)
        if snapshot is operation.snapshot:
            calls.append(result.count)
            if len(calls) == 1:
                if change == "append":
                    summary["all_valid_matches"].append(_unique_primary(app, 400))
                elif change == "order":
                    summary["all_valid_matches"].reverse()
                else:
                    summary["incident_matches"] = [rows[0]]
        return result

    monkeypatch.setattr(PreparedFixtureSnapshot, "select_rows", observed)
    actual = app._v991_count_cohorts(
        summary, {"first": list(rows), "second": list(rows)}, fixture_operation=operation
    )

    assert calls[0] == 1  # A trusted early result existed and must be discarded.
    assert actual.identity_state == "UNPREPARED"
    assert actual.counts == {"first": 2, "second": 2}
    assert not operation.matches(summary)


@pytest.mark.parametrize("changed_map", ("cohorts", "identity_at_prepare"))
def test_replaced_snapshot_with_externally_mutable_proxy_is_rechecked(app_module, monkeypatch, changed_map):
    app = app_module
    rows = _pair(app)
    summary = _summary(rows)
    original = _prepare(app, monkeypatch, summary)
    backing = dict(original.snapshot.cohorts if changed_map == "cohorts" else original.snapshot._identity_at_prepare)
    snapshot = replace(
        original.snapshot,
        **{"cohorts" if changed_map == "cohorts" else "_identity_at_prepare": MappingProxyType(backing)},
    )
    operation = replace(original, snapshot=snapshot)
    assert operation.matches(summary)
    select_rows = PreparedFixtureSnapshot.select_rows
    calls = []

    def observed(current_snapshot, values, **kwargs):
        result = select_rows(current_snapshot, values, **kwargs)
        if current_snapshot is snapshot:
            calls.append(result.count)
            if len(calls) == 1:
                if changed_map == "cohorts":
                    backing["current"] = tuple(reversed(backing["current"]))
                else:
                    entry = backing[id(rows[0])]
                    backing[id(rows[0])] = (entry[0], b"changed-preparation-digest")
        return result

    monkeypatch.setattr(PreparedFixtureSnapshot, "select_rows", observed)
    actual = app._v991_count_cohorts(
        summary, {"first": rows, "second": rows}, fixture_operation=operation
    )

    assert calls[0] == 1
    assert actual.identity_state == "UNPREPARED"
    assert actual.counts == {"first": 2, "second": 2}
    assert not operation.matches(summary)


def test_identity_is_projected_again_between_cohorts(app_module, monkeypatch):
    app = app_module
    rows = _pair(app)
    summary = _summary(rows)
    operation = _prepare(app, monkeypatch, summary)
    select_rows = PreparedFixtureSnapshot.select_rows
    calls = []

    def observed(snapshot, values, **kwargs):
        result = select_rows(snapshot, values, **kwargs)
        if snapshot is operation.snapshot:
            calls.append(result.count)
            if len(calls) == 1:
                for row in rows:
                    row["home_canonical_team_id"] = "synthetic-post-prepare-home"
                    row["away_canonical_team_id"] = "synthetic-post-prepare-away"
        return result

    monkeypatch.setattr(PreparedFixtureSnapshot, "select_rows", observed)
    actual = app._v991_count_cohorts(
        summary, {"before": rows, "after": rows}, fixture_operation=operation
    )

    # PREPARED denotes a valid operation boundary, not resolved current identity.
    assert actual.identity_state == "PREPARED"
    assert actual.counts == {"before": 1, "after": 2}
    assert calls == [1, 2]
    assert all(operation.snapshot.context_for(row).state == "UNKNOWN_IDENTITY_CHANGED" for row in rows)


def test_snapshot_replacement_during_batch_discards_early_grouped_counts(app_module, monkeypatch):
    app = app_module
    rows = _pair(app)
    summary = _summary(rows)
    operation = _prepare(app, monkeypatch, summary)
    snapshot = operation.snapshot
    replacement = replace(snapshot)
    select_rows = PreparedFixtureSnapshot.select_rows
    selected_snapshots = []

    def observed(current, values, **kwargs):
        selected_snapshots.append(current)
        result = select_rows(current, values, **kwargs)
        if len(selected_snapshots) == 1:
            # Simulate an internal replacement despite frozen dataclass fields.
            object.__setattr__(operation, "snapshot", replacement)
        return result

    monkeypatch.setattr(PreparedFixtureSnapshot, "select_rows", observed)
    actual = app._v991_count_cohorts(
        summary, {"first": rows, "second": rows}, fixture_operation=operation
    )

    assert all(current is snapshot for current in selected_snapshots)
    assert actual.identity_state == "UNPREPARED"
    assert actual.counts == {"first": 2, "second": 2}


def test_many_cohorts_share_owner_validation_but_not_current_identity_projection(app_module, monkeypatch):
    app = app_module
    rows = _pair(app)
    summary = _summary(rows)
    operation = _prepare(app, monkeypatch, summary)
    matches = app._V991Operation.matches
    checked = PreparedFixtureSnapshot._checked_identity
    observations = {"owner": 0, "identity": 0}

    def observe_owner(self, *args, **kwargs):
        if self is operation:
            observations["owner"] += 1
        return matches(self, *args, **kwargs)

    def observe_identity(self, *args, **kwargs):
        if self is operation.snapshot:
            observations["identity"] += 1
        return checked(self, *args, **kwargs)

    monkeypatch.setattr(app._V991Operation, "matches", observe_owner)
    monkeypatch.setattr(PreparedFixtureSnapshot, "_checked_identity", observe_identity)
    actual = app._v991_count_cohorts(
        summary, {"synthetic-label-" + str(i): rows for i in range(40)}, fixture_operation=operation
    )

    assert actual.identity_state == "PREPARED"
    assert set(actual.counts.values()) == {1}
    assert observations == {"owner": 2, "identity": 80}


@pytest.mark.parametrize("team_filter", ("", "Athletic%20Club"))
def test_calendar_keeps_secondary_alias_facet_and_filters_before_grouping(app_module, monkeypatch, team_filter):
    app = app_module
    primary, alternate = _pair(app)
    summary = _summary([primary, alternate])
    original = deepcopy(summary)
    with app.app.test_request_context("/calendario?lane=week&team=" + team_filter):
        operation = _prepare(app, monkeypatch, summary)
        result = app.v940_calendar_context(summary, "week", app.today_iso(), fixture_operation=operation)

    facets = {item["label"]: item["count"] for item in result["facets"]["teams"]}
    assert facets["Athletic Club"] == facets["Athletic Bilbao"] == 1
    assert result["counts"]["all"] == result["counts"]["visible"] == 1
    assert result["facet_identity_state"] == "PREPARED"
    if team_filter:
        assert [row["id"] for row in result["matches"]] == [alternate["id"]]
    assert summary == original


def test_calendar_counts_all_labels_before_limiting_visible_options(app_module, monkeypatch):
    app = app_module
    rows = [_unique_primary(app, i) for i in range(40)]
    rows.extend(_unique_primary(app, i, home="Late frequent team") for i in range(40, 45))
    summary = _summary(rows)
    with app.app.test_request_context("/calendario?lane=week"):
        operation = _prepare(app, monkeypatch, summary)
        result = app.v940_calendar_context(summary, "week", app.today_iso(), fixture_operation=operation)

    facets = result["facets"]["teams"]
    assert len(facets) == 32
    assert facets[0] == {"label": "Late frequent team", "value": "Late frequent team", "count": 5}
    assert result["counts"]["visible"] == result["counts"]["all"] == 45
    assert result["facet_identity_state"] == "PREPARED"


def test_calendar_rejects_other_selected_date_before_batching(app_module, monkeypatch):
    app = app_module
    rows = _pair(app)
    summary = _summary(rows)
    with app.app.test_request_context("/calendario?lane=week"):
        original = _prepare(app, monkeypatch, summary)
        other_date = app.today_iso(1)
        operation = replace(
            original,
            selected_date=other_date,
            generation=app._v991_generation(original.snapshot, other_date),
        )
        assert operation.matches(summary, other_date)
        result = app.v940_calendar_context(summary, "week", app.today_iso(), fixture_operation=operation)

    assert result["identity_state"] == result["facet_identity_state"] == "UNPREPARED"
    assert result["counts"]["all"] == result["counts"]["visible"] == 2
