import json

import pytest
from werkzeug.datastructures import MultiDict

from engines.shark_request_contract import SharkInputError, normalize_request, encode_snapshot


@pytest.mark.parametrize("payload", [None, [], 2, True, "question", {"q": None}, {"q": []}, {"q": {}}, {"q": 2}, {}, {"q": "  "}, {"q": "a" * 1001}, {"q": " " * 1001 + "x"}, {"q": "hello\x00"}, {"q": "hello", "pick_id": []}, {"q": "hello", "match": "a b"}, {"q": "hello", "match_id": "a" * 181}])
def test_invalid_requests_are_not_questions(payload):
    with pytest.raises(SharkInputError):
        normalize_request(payload)


@pytest.mark.parametrize("payload,query", [({"q": "one", "question": "two"}, {}), ({"q": "one"}, {"q": "two"}), ({"q": "one", "match": "a", "match_id": "b"}, {}), ({"q": "one", "pick": "a"}, {"pick_id": "b"}), (MultiDict([("q", "one"), ("q", "two")]), {})])
def test_conflicting_aliases_do_not_silently_change_selection(payload, query):
    with pytest.raises(SharkInputError):
        normalize_request(payload, query)


def test_aliases_normalize_without_accepting_identity_or_plan():
    assert normalize_request({"q": "  Match?\n", "pick": "p1", "membership": "ADMIN", "user_id": "other"}, {"match": "m1"}) == {"question": "Match?", "pick_id": "p1", "match_id": "m1"}
    assert normalize_request({}, require_question=False)["question"] == ""


@pytest.mark.parametrize("payload", [{"q": " Keep my question ", "match_id": "invalid selection"}, {"q": " Keep my question ", "pick_id": []}, MultiDict([("q", " Keep my question "), ("match_id", "one"), ("match_id", "two")])])
def test_recovery_only_preserves_validated_question_and_clears_selection(payload):
    assert normalize_request(payload, require_question=False, include_selection=False) == {
        "question": "Keep my question", "match_id": "", "pick_id": ""}


@pytest.mark.parametrize("payload,query", [({"q": "a" * 1001}, {}), ({"q": []}, {}), ({"q": "unsafe\x00question"}, {}), (MultiDict([("q", "one"), ("q", "two")]), {}), ({"question": "one"}, {"q": "two"})])
def test_recovery_does_not_hide_invalid_or_conflicting_question_aliases(payload, query):
    with pytest.raises(SharkInputError):
        normalize_request(payload, query, require_question=False, include_selection=False)


@pytest.mark.parametrize("size", [20, 20000])
def test_snapshot_is_complete_valid_json_and_explicit_about_reduction(size):
    payload = {"user": {"id": "owner", "membership": "PRO"}, "pick": {"id": "p1", "reasoning": "é" * size}, "match": {"id": "m1"}}
    encoded = encode_snapshot(payload)
    assert len(encoded) <= 8000
    stored = json.loads(encoded)
    if size > 8000:
        assert stored["truncated"] and stored["selection"] == {"pick": "p1", "match": "m1"}
    else:
        assert stored == payload


def test_nonfinite_snapshot_numbers_are_unknown_not_nonstandard_json():
    assert json.loads(encode_snapshot({"facts": [float("nan"), float("inf"), 0]})) == {"facts": [None, None, 0]}
