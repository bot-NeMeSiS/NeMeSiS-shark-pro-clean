"""Directo filters must keep active play and halftime truthful and separate."""

import engines.live_experience_engine as live_experience


def _match(match_id, lifecycle, *, conflict=False):
    return {
        "id": match_id,
        "home_team": f"Local {match_id}",
        "away_team": f"Visitante {match_id}",
        "competition_name": "Liga QA",
        "match_date": "2026-09-20",
        "kickoff_time": "12:00",
        "source": "qa-persisted-cache",
        "qa_lifecycle": lifecycle,
        "qa_conflict": conflict,
    }


def _truth(match):
    return {
        "lifecycle": match.get("qa_lifecycle"),
        "status_conflict": bool(match.get("qa_conflict")),
        "is_live": match.get("qa_lifecycle") in {"LIVE", "HALFTIME"} and not bool(match.get("qa_conflict")),
        "is_finished": match.get("qa_lifecycle") == "FINISHED",
    }


def test_directo_live_and_break_lanes_are_distinct(monkeypatch):
    monkeypatch.setattr(live_experience, "match_status_truth", _truth)
    rows = [
        _match("live", "LIVE"),
        _match("break", "HALFTIME"),
        _match("finished", "FINISHED"),
        _match("upcoming", "UPCOMING"),
    ]

    active = live_experience.build_live_experience(rows, lane="live")
    halftime = live_experience.build_live_experience(rows, lane="break")

    assert [m["id"] for m in active["matches"]] == ["live"]
    assert [m["id"] for m in halftime["matches"]] == ["break"]
    assert active["counts"]["live"] == 1
    assert active["counts"]["halftime"] == 1
    assert active["counts"]["finished"] == 1
    assert active["counts"]["upcoming"] == 1


def test_conflicting_halftime_signal_is_not_presented_as_break(monkeypatch):
    monkeypatch.setattr(live_experience, "match_status_truth", _truth)
    rows = [
        _match("break-ok", "HALFTIME"),
        _match("break-conflict", "HALFTIME", conflict=True),
    ]

    halftime = live_experience.build_live_experience(rows, lane="break")

    assert [m["id"] for m in halftime["matches"]] == ["break-ok"]
    assert halftime["counts"]["halftime"] == 1
