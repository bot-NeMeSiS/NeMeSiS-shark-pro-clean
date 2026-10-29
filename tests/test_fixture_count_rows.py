"""Count-only fixture cardinality without reusing mutable identity decisions.

Empty and singleton cohorts retain their original count; every singleton still
performs a fresh C3 projection. Two or more supplied occurrences follow the
unchanged full selection path. Tests use real preparation, admission, grouping
and identity checks with synthetic observations. No App import or provider call."""

from copy import deepcopy
from datetime import datetime

import pytest

from engines.fixture_snapshot_read_model import PreparedFixtureSnapshot, prepare_fixture_snapshot
from engines.v935_launch_trust_engine import match_kickoff_madrid
from tests.test_v990_native_fixture_proof import observation, pair, payload


REFERENCE = {"key": "laliga", "name": "LaLiga", "country": "Spain",
             "source": "API_FOOTBALL", "external_id": "140"}


def _resolved_row(identity="count-row"):
    row = observation(identity, competition_key="laliga", competition_name="LaLiga")
    row["raw_json"] = payload(row)
    return row


def _snapshot(rows, *, references=(REFERENCE,), kickoff_for=match_kickoff_madrid):
    reads = []

    def read(keys):
        reads.append(tuple(keys))
        return [dict(row) for row in references if row["key"] in keys]

    result = prepare_fixture_snapshot({"actual": rows}, read, kickoff_for=kickoff_for)
    return result, reads


def _same_cardinality(snapshot, rows, expected):
    # The unchanged real selector is an independent cardinality oracle. Explicit
    # expected values ensure two equally wrong results cannot satisfy the test.
    original = deepcopy(rows)
    assert snapshot.select_rows(rows).count == expected
    assert snapshot.count_rows(rows) == expected
    assert rows == original


@pytest.mark.parametrize("kind", ["none", "empty_tuple", "empty_generator"])
def test_empty_count_matches_real_selection_without_reference_reads(kind):
    snapshot, reads = _snapshot([])
    if kind == "none":
        rows = None
    elif kind == "empty_tuple":
        rows = ()
    else:
        rows = (row for row in ())
    before = list(reads)

    assert snapshot.select_rows(()).count == 0
    assert snapshot.count_rows(rows) == 0
    assert reads == before


@pytest.mark.parametrize("kind,expected_state", [
    ("resolved", "RESOLVED"),
    ("native_only", "UNKNOWN"),
    ("labels_only", "UNKNOWN_NO_REFERENCE"),
    ("canonical_conflict", "CONFLICT"),
    ("projection_overlimit", "UNKNOWN_IDENTITY_LIMIT"),
    ("non_mapping", "UNKNOWN_IDENTITY_LIMIT"),
])
def test_singleton_count_preserves_unknown_conflict_and_limit_cardinality(kind, expected_state):
    if kind in {"resolved", "canonical_conflict"}:
        row = _resolved_row()
        if kind == "canonical_conflict":
            row["country"] = "Portugal"
            row["raw_json"]["league"]["country"] = "Portugal"
    elif kind == "native_only":
        row = observation()
    elif kind == "labels_only":
        row = {"id": "unknown-count-labels", "source": "unknown-provider",
               "home_team": "Harbor", "away_team": "Ridge",
               "kickoff_iso": "2099-01-01T20:00:00+01:00"}
    elif kind == "projection_overlimit":
        row = observation()
        row["raw_json"] = "x" * 131073
    else:
        row = None
    rows = [row]
    snapshot, reads = _snapshot(rows)
    before = list(reads)

    _same_cardinality(snapshot, rows, 1)

    assert snapshot.context_for(row).state == expected_state
    assert reads == before


@pytest.mark.parametrize("valid_identifier,expected", [(True, 1), (False, 2)])
def test_two_occurrences_keep_exact_selector_admission_rule(valid_identifier, expected):
    # The selector deduplicates a repeated object only with a valid match ID.
    # Counting must not replace this with set/dict equality or object-only dedup.
    row = _resolved_row() if valid_identifier else {"id": "", "source": "unknown-provider"}
    rows = [row, row]
    snapshot, reads = _snapshot(rows)
    before = list(reads)

    _same_cardinality(snapshot, rows, expected)

    assert reads == before


@pytest.mark.parametrize("resolved,expected", [(True, 1), (False, 2)])
def test_equal_distinct_copies_with_same_id_still_require_actual_fixture_proof(resolved, expected):
    row = _resolved_row() if resolved else {
        "id": "same-unknown-id", "source": "unknown-provider",
        "home_team": "Harbor", "away_team": "Ridge",
        "kickoff_iso": "2099-01-01T20:00:00+01:00",
    }
    copied = deepcopy(row)
    rows = [row, copied]
    snapshot, _reads = _snapshot(rows)

    _same_cardinality(snapshot, rows, expected)

    assert row == copied and row is not copied


def test_two_native_claimants_with_conflicting_own_kickoffs_remain_two():
    rows = pair()
    rows[1]["kickoff_iso"] = "2099-01-01T20:02:00+01:00"
    rows[1]["raw_json"] = payload(rows[1])
    snapshot, _reads = _snapshot(rows)

    _same_cardinality(snapshot, rows, 2)

    assert snapshot.select_rows(rows).identity_basis == (
        "CONFLICT_NATIVE_OBSERVATIONS", "CONFLICT_NATIVE_OBSERVATIONS"
    )


def test_unprepared_equal_clones_cannot_borrow_prepared_native_evidence():
    originals = pair()
    snapshot, _reads = _snapshot(originals)
    clones = deepcopy(originals)
    assert snapshot.select_rows(originals).count == 1

    _same_cardinality(snapshot, clones, 2)

    assert all(snapshot.context_for(row).state != "RESOLVED" for row in clones)


def test_excessive_native_claimants_preserve_overload_fail_closed_count():
    rows = [observation("count-overload-" + str(index)) for index in range(65)]
    snapshot, _reads = _snapshot(rows)

    _same_cardinality(snapshot, rows, 65)

    assert set(snapshot.select_rows(rows).identity_basis) == {"UNRESOLVED_NATIVE_OVERLOAD"}


def test_singleton_rechecks_real_c3_after_nested_mutation_overlimit_and_restore(monkeypatch):
    row = _resolved_row()
    rows = [row]
    snapshot, reads = _snapshot(rows)
    original_raw = deepcopy(row["raw_json"])
    original_checked = PreparedFixtureSnapshot._checked_identity
    observed = []

    def observe(self, current_row):
        result = original_checked(self, current_row)
        if self is snapshot:
            observed.append((current_row is row, result[0].state))
        return result

    # Observation only: the original C3 projection always decides the result.
    monkeypatch.setattr(PreparedFixtureSnapshot, "_checked_identity", observe)
    before = list(reads)

    def assert_fresh(expected_state):
        assert snapshot.select_rows(rows).count == 1
        observed_before_count = len(observed)
        assert snapshot.count_rows(rows) == 1
        assert observed[observed_before_count:] == [(True, expected_state)]

    assert_fresh("RESOLVED")
    row["raw_json"]["teams"]["home"]["id"] = 99999
    assert_fresh("UNKNOWN_IDENTITY_CHANGED")
    row["raw_json"] = "x" * 131073
    assert_fresh("UNKNOWN_IDENTITY_LIMIT")
    row["raw_json"] = original_raw
    assert_fresh("RESOLVED")
    assert reads == before


def test_multiple_rows_reproject_changed_nested_identity_on_each_call():
    rows = pair()
    snapshot, reads = _snapshot(rows)
    before_reads = list(reads)
    before_raw = deepcopy(rows[0]["raw_json"])
    _same_cardinality(snapshot, rows, 1)

    rows[0]["raw_json"]["fixture"]["id"] = 99999
    _same_cardinality(snapshot, rows, 2)
    assert snapshot.context_for(rows[0]).state == "UNKNOWN_IDENTITY_CHANGED"

    rows[0]["raw_json"] = before_raw
    _same_cardinality(snapshot, rows, 1)
    assert reads == before_reads


def test_one_pass_iterable_is_frozen_once_and_keeps_all_original_occurrences():
    rows = pair()
    snapshot, reads = _snapshot(rows)
    expected = snapshot.select_rows(rows).count
    assert expected == 1

    class OnePass:
        def __init__(self):
            self.iterations = 0

        def __iter__(self):
            self.iterations += 1
            assert self.iterations == 1, "caller input was iterated more than once"
            yield from rows

    supplied = OnePass()
    before = list(reads)
    assert snapshot.count_rows(supplied) == expected
    assert supplied.iterations == 1
    assert reads == before


def test_presentation_and_quote_mutation_do_not_invalidate_identity_or_count():
    rows = pair()
    snapshot, reads = _snapshot(rows)
    original_raw = [deepcopy(row["raw_json"]) for row in rows]
    before_reads = list(reads)
    _same_cardinality(snapshot, rows, 1)

    rows[0].update(is_favorite=True, has_pick=True, home_logo="/static/count-logo.svg")
    rows[0]["quote"]["price"] = 9.5
    _same_cardinality(snapshot, rows, 1)

    assert all(snapshot.context_for(row).state != "UNKNOWN_IDENTITY_CHANGED" for row in rows)
    assert [row["raw_json"] for row in rows] == original_raw
    assert rows[0]["quote"]["price"] == 9.5  # Count owns no mutable source data.
    assert reads == before_reads


def test_cardinality_only_singleton_does_not_promise_full_metadata_parser_error_parity():
    """Deliberate error-surface distinction, not a selector-equivalence claim.

    This supported aware datetime projects to a bounded digest, but converting
    year1 midnight +01:00 to UTC requires year0. Full metadata selection reaches
    the unguarded UTC conversion in _payload_fixture_ids (line351 in baseline).
    A singleton count needs no native/canonical metadata and can still count one
    original observation after its real fresh identity check. Two supplied
    occurrences retain the full selector path, even when admission dedups them.
    This test intentionally documents that narrow API boundary without changing
    the original parser, its guard or its exception handling.
    """
    row = _resolved_row()
    row.update(kickoff_iso="0001-01-01T00:00:00+01:00", season="1")
    row["raw_json"] = payload(row)
    snapshot, reads = _snapshot([row], kickoff_for=lambda view: datetime.fromisoformat(view["kickoff_iso"]))
    before = list(reads)

    assert snapshot.context_for(row).state == "RESOLVED"
    with pytest.raises(OverflowError):
        snapshot.select_rows([row])
    assert snapshot.count_rows([row]) == 1
    assert snapshot.context_for(row).state == "RESOLVED"
    with pytest.raises(OverflowError):
        snapshot.count_rows([row, row])
    assert reads == before


def test_singleton_propagates_original_fresh_identity_error(monkeypatch):
    row = _resolved_row()
    snapshot, _reads = _snapshot([row])
    original = PreparedFixtureSnapshot._checked_identity
    marker = RuntimeError("synthetic fresh identity failure")
    calls = []

    def fails_after_real_check(self, current):
        result = original(self, current)
        if self is snapshot:
            calls.append((current is row, result[0].state))
            raise marker
        return result

    monkeypatch.setattr(PreparedFixtureSnapshot, "_checked_identity", fails_after_real_check)
    with pytest.raises(RuntimeError) as captured:
        snapshot.count_rows([row])
    assert captured.value is marker
    assert calls == [(True, "RESOLVED")]


def test_singleton_retains_original_initial_id_read_failure():
    marker = RuntimeError("synthetic initial ID read failure")

    class RejectIdRead(dict):
        reject = False

        def get(self, key, default=None):
            if self.reject and key == "id":
                raise marker
            return super().get(key, default)

    row = RejectIdRead(_resolved_row())
    snapshot, _reads = _snapshot([row])
    row.reject = True
    for operation in (snapshot.select_rows, snapshot.count_rows):
        with pytest.raises(RuntimeError) as captured:
            operation([row])
        assert captured.value is marker
