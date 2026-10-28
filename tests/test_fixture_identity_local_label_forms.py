"""Pure tests for one-derivation label parsing; no App, SQL or providers.

The comparison path clears only the new private parse metadata, making native
payload checks recompute names through their existing branch. It does not skip
current identity projection or substitute the fixture/grouping implementation.
"""
from copy import deepcopy
from dataclasses import replace

import pytest

from engines import fixture_identity_read_model as identity
from tests.test_v990_native_fixture_proof import observation, pair, prepare
from engines.v935_launch_trust_engine import match_kickoff_madrid


def _without_local_forms(team):
    return (replace(team, source_label=None, source_label_forms=None)
            if team is not None else None)


def _payload_args(row):
    projected = identity.project_fixture_identity(row, kickoff_for=match_kickoff_madrid)
    assert projected is not None
    view = projected[0]
    provider = identity.provider_family(view["source"])
    home, away = identity._team(view, "home", provider), identity._team(view, "away", provider)
    assert home is not None and away is not None
    return view, provider, home, away, view["_evaluated_kickoff"], str(view["external_id"])


def _payload_result(row, *, legacy_names=False):
    view, provider, home, away, kickoff, native = _payload_args(row)
    if legacy_names:
        home, away = _without_local_forms(home), _without_local_forms(away)
    return identity._payload_fixture_ids(view, provider, home, away, kickoff, native)


def _set_raw_names(row, home, away=None):
    raw = row["raw_json"]
    if row["source"] == "TheSportsDB":
        raw["strHomeTeam"] = home
        if away is not None:
            raw["strAwayTeam"] = away
    else:
        raw["teams"]["home"]["name"] = home
        if away is not None:
            raw["teams"]["away"]["name"] = away


def _change(row, kind):
    if kind == "equivalent_string":
        _set_raw_names(row, "Granada C.F.")
    elif kind == "known_alias":
        row["home_team_aliases"] = ["Nazarí FC"]
        _set_raw_names(row, "Nazarí FC")
    elif kind == "different_club":
        _set_raw_names(row, "Sevilla FC")
    elif kind == "different_category":
        _set_raw_names(row, "Granada CF Women")
    elif kind == "extra_category":
        row["home_gender"] = "women"
    elif kind == "native_id":
        if row["source"] == "TheSportsDB":
            row["raw_json"]["idEvent"] = "99999"
        else:
            row["raw_json"]["fixture"]["id"] = 99999
    elif kind == "inverted_names":
        _set_raw_names(row, row["away_team"], row["home_team"])
    elif kind != "equal":
        raise AssertionError("Unknown synthetic test change: " + kind)


def _facts(selection):
    return {
        "count": selection.count,
        "groups": [[row["id"] for row in group] for group in selection.groups],
        "chosen": [row["id"] for row in selection.rows],
        "fixture_ids": dict(selection.fixture_ids),
        "confirmed_count": selection.confirmed_count,
        "unresolved_observations": selection.unresolved_observations,
        "identity_basis": list(selection.identity_basis),
        "native_fixture_groups": selection.native_fixture_groups,
    }


@pytest.mark.parametrize("provider", ("API_FOOTBALL", "TheSportsDB"))
def test_equal_builtin_source_labels_reuse_only_this_teams_parse(provider, monkeypatch):
    args = _payload_args(observation(provider=provider))
    home, away = args[2:4]
    assert home.source_label == "Granada CF"
    assert away.source_label == "Real Valladolid"
    assert type(home.source_label_forms) is tuple
    assert type(home.source_label_forms[0]) is frozenset
    forms = identity._name_forms
    calls = []

    def observed(value):
        calls.append(value)
        return forms(value)

    monkeypatch.setattr(identity, "_name_forms", observed)
    result = identity._payload_fixture_ids(*args)
    assert result == {identity.provider_family(provider): "1001"}
    assert calls == []
    legacy = list(args)
    legacy[2:4] = [_without_local_forms(home), _without_local_forms(away)]
    assert identity._payload_fixture_ids(*legacy) == result
    assert calls == ["Granada CF", "Real Valladolid"]


@pytest.mark.parametrize("provider", ("API_FOOTBALL", "TheSportsDB"))
@pytest.mark.parametrize("kind", ("equivalent_string", "known_alias", "different_club", "different_category", "inverted_names"))
def test_different_raw_strings_use_existing_name_parse_and_side_checks(provider, kind, monkeypatch):
    row = observation(provider=provider)
    _change(row, kind)
    args = _payload_args(row)
    value = row["raw_json"]["strHomeTeam"] if provider == "TheSportsDB" else row["raw_json"]["teams"]["home"]["name"]
    assert value != args[2].source_label
    forms = identity._name_forms
    calls = []

    def observed(value):
        calls.append(value)
        return forms(value)

    monkeypatch.setattr(identity, "_name_forms", observed)
    actual = identity._payload_fixture_ids(*args)
    assert value in calls
    expected = {identity.provider_family(provider): "1001"} if kind in {"equivalent_string", "known_alias"} else None
    assert actual == expected
    legacy = list(args)
    legacy[2:4] = [_without_local_forms(args[2]), _without_local_forms(args[3])]
    assert identity._payload_fixture_ids(*legacy) == actual


@pytest.mark.parametrize("field,value", (("home_gender", "women"), ("home_age_group", "U19"), ("home_category", "B")))
def test_equal_payload_label_cannot_override_extra_category_evidence(field, value):
    row = observation()
    row[field] = value
    args = _payload_args(row)
    assert args[2].source_label == row["raw_json"]["teams"]["home"]["name"]
    assert args[2].source_label_forms[0] != args[2].category
    assert _payload_result(row) is None
    assert _payload_result(row, legacy_names=True) is None


@pytest.mark.parametrize("label", (1378, 1378.5))
def test_non_string_label_uses_existing_payload_parse(label, monkeypatch):
    row = observation(home_team=label)
    args = _payload_args(row)
    assert args[2].source_label is None and args[2].source_label_forms is None
    forms = identity._name_forms
    calls = []

    def observed(value):
        calls.append(value)
        return forms(value)

    monkeypatch.setattr(identity, "_name_forms", observed)
    actual = identity._payload_fixture_ids(*args)
    assert label in calls
    assert actual == {"api-football": "1001"}


def test_four_argument_team_construction_and_equality_remain_compatible():
    team = _payload_args(observation())[2]
    old_style = identity._Team(team.names, team.category, dict(team.ids), team.canonical)
    assert old_style.source_label is None and old_style.source_label_forms is None
    assert old_style == team
    assert "source_label" not in repr(team)


@pytest.mark.parametrize("provider", ("API_FOOTBALL", "TheSportsDB"))
@pytest.mark.parametrize("kind", ("equal", "equivalent_string", "known_alias", "different_club", "different_category", "extra_category", "native_id", "inverted_names"))
def test_group_evidence_matches_existing_payload_recomputation_path(provider, kind, monkeypatch):
    rows = pair(provider)
    _change(rows[1], kind)
    original = deepcopy(rows)
    snapshot, reference_calls = prepare(rows)
    actual = _facts(snapshot.select("actual"))
    team = identity._team

    def recompute_payload_names(*args, **kwargs):
        return _without_local_forms(team(*args, **kwargs))

    with monkeypatch.context() as context:
        context.setattr(identity, "_team", recompute_payload_names)
        expected = _facts(snapshot.select("actual"))
    assert actual == expected
    assert actual["count"] == (1 if kind in {"equal", "equivalent_string", "known_alias"} else 2)
    assert rows == original
    assert len(reference_calls) <= 1


@pytest.mark.parametrize("provider", ("API_FOOTBALL", "TheSportsDB"))
def test_same_rows_are_freshly_parsed_on_every_consumer(provider, monkeypatch):
    snapshot, _ = prepare(pair(provider))
    forms = identity._name_forms
    calls = []

    def observed(value):
        calls.append(value)
        return forms(value)

    monkeypatch.setattr(identity, "_name_forms", observed)
    assert snapshot.select("actual").count == 1
    first = list(calls)
    assert len(first) == 4
    assert snapshot.select("actual").count == 1
    assert calls == first + first


@pytest.mark.parametrize("change", ("raw_name", "alias", "canonical_id"))
def test_mutated_current_identity_is_still_rejected_between_consumers(change):
    rows = pair()
    snapshot, _ = prepare(rows)
    assert snapshot.select("actual").count == 1
    if change == "raw_name":
        _set_raw_names(rows[1], "Sevilla FC")
    elif change == "alias":
        rows[1]["home_team_aliases"] = ["A newly added current alias"]
    else:
        rows[1]["home_canonical_team_id"] = "new-current-canonical-id"
    assert snapshot.context_for(rows[1]).state == "UNKNOWN_IDENTITY_CHANGED"
    assert snapshot.select("actual").count == 2


@pytest.mark.parametrize("value", (None, False, 0, 0.0, "", [], {}, (), set(), frozenset(), " \t "))
def test_falsy_or_empty_normalized_categories_remain_empty(value):
    assert identity._category(value) == (frozenset(), "")


@pytest.mark.parametrize("value,markers,text", (
    ("Granada FC Women U19", {"gender:female", "age:19"}, "granada fc"),
    ("Harbor FC B", {"category:b"}, "harbor fc"),
    ("Male under21 reserves", {"gender:male", "age:21", "category:reserves"}, ""),
))
def test_nonempty_category_markers_are_not_skipped(value, markers, text):
    assert identity._category(value) == (frozenset(markers), text)


@pytest.mark.parametrize("truthy", (False, True))
def test_nonprimitive_category_preserves_normalizers_single_truth_test(truthy):
    class CategoryValue:
        calls = 0

        def __bool__(self):
            self.calls += 1
            return truthy

        def __str__(self):
            assert truthy
            return "Harbor Women"

    value = CategoryValue()
    expected = (frozenset({"gender:female"}), "harbor") if truthy else (frozenset(), "")
    assert identity._category(value) == expected
    assert value.calls == 1
