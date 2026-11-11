"""Missing status fields are no evidence; all present signals stay observable."""
from datetime import datetime, timedelta
from copy import deepcopy
import pytest
from engines import v935_launch_trust_engine as truth


def test_missing_status_fields_do_not_enter_text_normalization(monkeypatch):
    original = truth._status_key
    observed = []
    def checked(value):
        observed.append(value)
        return original(value)
    monkeypatch.setattr(truth, "_status_key", checked)
    source = {"status": "LIVE", "fixture": {}, "raw_json": {}, "payload_json": {}}
    before = deepcopy(source)
    assert truth._status_values(source) == [("status", "live")]
    assert observed == ["LIVE"]
    assert source == before


@pytest.mark.parametrize("source,expected", [
    ({}, []),
    ({"status": None, "fixture": {"status": None}}, []),
    ({"status": "", "provider_status": False, "status_code": 0}, []),
    ({"status": {"key": "LIVE", "long": "In progress"}},
     [("status.key", "live"), ("status.long", "in progress")]),
    ({"fixture": {"status": {"short": "FT"}}, "is_live": True},
     [("is_live", "live"), ("fixture.status.short", "ft")]),
    ({"raw_json": '{"fixture":{"status":{"short":"HT"}}}'},
     [("raw_json.fixture.status.short", "ht")]),
    ({"payload_json": {"status": "POSTPONED"}, "raw_json": "invalid"},
     [("payload_json.status", "postponed")]),
    ({"status_info": {"is_finished": True, "is_live": True}},
     [("status_info.is_finished", "ft"), ("status_info.is_live", "live")]),
])
def test_present_status_signals_keep_sources_order_and_values(source, expected):
    before = deepcopy(source)
    assert truth._status_values(source) == expected
    assert source == before


def test_false_values_still_follow_existing_conversion(monkeypatch):
    original = truth._status_key
    seen = []
    def observed(value):
        seen.append(value)
        return original(value)
    monkeypatch.setattr(truth, "_status_key", observed)
    assert truth._status_values({"status": False, "provider_status": 0, "status_code": ""}) == []
    assert len(seen) == 3
    assert seen[0] == 0 and type(seen[0]) is int
    assert seen[1] == "" and type(seen[1]) is str and seen[2] is False


def test_clock_and_mutated_signals_are_evaluated_on_each_call():
    now = datetime.fromisoformat("2026-11-11T14:00:00+01:00")
    source = {"status": "LIVE", "kickoff_iso": (now-timedelta(minutes=20)).isoformat(),
              "live_updated_at": now.isoformat(), "source": "api_football"}
    assert truth.match_status_truth(source, now)["is_live"] is True
    expired = truth.match_status_truth(source, now+timedelta(seconds=121))
    assert expired["is_live"] is False and expired["is_stale"] is True
    source["fixture"] = {"status": {"short": "FT"}}
    conflict = truth.match_status_truth(source, now)
    assert conflict["status_conflict"] is True and conflict["is_live"] is False
