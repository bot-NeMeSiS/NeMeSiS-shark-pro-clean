"""Recorded Team Center samples, never fabricated season completeness."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from engines.team_center_engine import _form_summary, _result_for_team, _score_number, _timeline, build_team_center_context
from engines.team_result_evidence_engine import build_team_result_evidence

ROOT = Path(__file__).resolve().parents[1]


def match(n=1, **overrides):
    row = dict(id=f"m{n}", external_id=f"e{n}", source="api_football_cache", home_team="Club QA",
               away_team=f"Rival {n}", home_score=0, away_score=0, status="FT", competition_id="140",
               competition_name="Liga QA", country="Spain", season="2026-2027", match_date=f"2026-09-{n:02d}",
               kickoff_time="20:00", kickoff_iso=f"2026-09-{n:02d}T20:00:00+02:00")
    row.update(overrides)
    return row


@pytest.mark.parametrize("value,expected", [(0,0),("0",0),(0.0,0),(3,3),(" 3 ",3),(3.0,3),("007",7),(999,999)])
def test_whole_scores_preserve_zero(value, expected):
    assert _score_number(value) == expected


@pytest.mark.parametrize("value", [None,"",True,False,1.5,-1,"-1","1.5","1e2",float("nan"),float("inf"),
                                   float("-inf"),"Infinity",[],{},1000,10**400,"１２","١"])
def test_invalid_scores_never_truncate_or_crash(value):
    assert _score_number(value) is None


@pytest.mark.parametrize("status", ["NS","LIVE","HT","POSTPONED","SUSPENDED","CANCELLED","ABANDONED","RESULT_PENDING",""])
def test_non_final_score_never_becomes_a_result(status):
    result = _result_for_team(match(status=status), "Club QA")
    assert result["available"] is False
    assert result["goals_for"] is None
    assert result["outcome"] == "No disponible"


@pytest.mark.parametrize("status", ["FT","FINISHED","AET","PEN"])
def test_terminal_zero_zero_is_a_real_draw(status):
    result = _result_for_team(match(status=status), "Club QA")
    assert result["available"] is True
    assert result["outcome"] == "Empate"
    assert result["home_score"] == result["away_score"] == 0
    assert result["score_scope"] == "recorded_final_score_not_qualification"


@pytest.mark.parametrize("overrides,expected", [
    ({"home_score":None,"away_score":None,"score":"0-0"},True),
    ({"home_score":None,"away_score":2,"score":"0 : 2"},True),
    ({"home_score":0,"away_score":0,"score":"2-1"},False),
    ({"home_score":None,"away_score":2,"score":"0-1"},False),
    ({"home_score":1.5,"away_score":1,"score":"1-1"},False),
    ({"home_score":True,"away_score":1,"score":"1-1"},False),
    ({"home_score":None,"away_score":None},False),
])
def test_score_sources_must_be_consistent(overrides, expected):
    assert _result_for_team(match(**overrides),"Club QA")["available"] is expected


def test_result_for_away_team_uses_correct_side():
    result = _result_for_team(match(home_team="Other",away_team="Club QA",home_score=2,away_score=0),"Club QA")
    assert result["side"] == "away" and result["goals_for"] == 0 and result["goals_against"] == 2
    assert result["outcome"] == "Derrota"


@pytest.mark.parametrize("flag", ["is_fake","is_demo","simulated"])
def test_explicit_simulated_records_are_not_sports_evidence(flag):
    assert not build_team_result_evidence([match(**{flag:True})],"Club QA")["available"]


def test_timeline_does_not_call_provisional_zero_zero_a_draw():
    assert _timeline([match(status="NS")], "Club QA")[0]["label"] != "Empate"


def test_seven_results_are_retained_while_form_is_explicitly_five():
    rows=[match(n) for n in range(1,8)]
    history=build_team_result_evidence(rows,"Club QA")
    form=_form_summary(rows,"Club QA")
    assert history["included_count"] == 7
    assert history["groups"][0]["totals"]["draws"] == 7
    assert form["sample_size"] == 5
    assert [i["match"]["id"] for i in form["items"]] == ["m7","m6","m5","m4","m3"]
    assert history["season_complete"] is False and history["expected_played"] is None


def test_round_number_does_not_set_a_total():
    history=build_team_result_evidence([match(1,round=7),match(2,round=7)],"Club QA")
    assert history["included_count"] == 2 and history["expected_played"] is None
    assert history["coverage_state"] == "LOADED_SAMPLE_ONLY"


def test_competitions_seasons_and_providers_stay_separate():
    rows=[match(1),match(2,season="2025-2026"),match(3,competition_id="2"),match(4,source="thesportsdb")]
    history=build_team_result_evidence(rows,"Club QA")
    assert len(history["groups"]) == 4
    assert all(g["totals"]["sample_size"] == 1 for g in history["groups"])


def test_same_provider_fixture_is_not_double_counted():
    row=match()
    history=build_team_result_evidence([row,dict(row,id="other-local-id")],"Club QA")
    assert history["included_count"] == 1 and history["omission_reasons"]["duplicate_rows"] == 1


def test_conflicting_duplicates_are_not_silently_averaged_or_overwritten():
    history=build_team_result_evidence([match(),match(home_score=2)],"Club QA")
    assert not history["available"]
    assert history["omission_reasons"]["conflicting_records"] == 2


def test_terminal_duplicate_with_cancellation_does_not_reappear():
    history=build_team_result_evidence([match(),match(status="CANCELLED")],"Club QA")
    assert history["included_count"] == 0


def test_same_numeric_fixture_from_different_providers_is_not_merged():
    history=build_team_result_evidence([match(),match(id="other",source="thesportsdb")],"Club QA")
    assert history["included_count"] == 2
    assert len(history["groups"]) == 2


def test_dst_fold_is_sorted_by_absolute_time():
    earlier=match(1,kickoff_iso="2025-10-26T02:50:00+02:00")
    later=match(2,kickoff_iso="2025-10-26T02:10:00+01:00")
    history=build_team_result_evidence([earlier,later],"Club QA")
    assert [item["match"]["id"] for item in history["items"]] == ["m2","m1"]


def test_dates_are_displayed_in_madrid():
    history=build_team_result_evidence([match(kickoff_iso="2026-09-01T23:30:00Z")],"Club QA")
    assert history["items"][0]["date_label"] == "02/09/2026 01:30"


@pytest.mark.parametrize("overrides,reason", [
    ({"kickoff_iso":"invalid","match_date":"","kickoff_time":""},"date_unverified"),
    ({"id":None,"external_id":None},"identity_missing"),
    ({"away_team":"Club QA"},"team_unverified"),
    ({"home_score":None},"not_confirmed_final"),
])
def test_unusable_records_have_explicit_omission_reasons(overrides,reason):
    h=build_team_result_evidence([match(**overrides)],"Club QA")
    assert h["included_count"] == 0 and h["omission_reasons"].get(reason) == 1


def test_sample_totals_and_sides_agree():
    h=build_team_result_evidence([match(1,home_score=2),match(2,away_team="Club QA",home_team="Other",away_score=1)],"Club QA")
    g=h["groups"][0]
    assert g["totals"] == dict(sample_size=2,wins=2,draws=0,losses=0,goals_for=3,goals_against=0)
    assert g["home"]["sample_size"] == g["away"]["sample_size"] == 1


def test_builder_does_not_mutate_input_or_call_io(monkeypatch):
    import socket, sqlite3
    def forbidden(*a,**kw): raise AssertionError("external effect")
    monkeypatch.setattr(socket.socket,"connect",forbidden)
    monkeypatch.setattr(sqlite3,"connect",forbidden)
    rows=[match(1),match(2)]
    before=copy.deepcopy(rows)
    h=build_team_result_evidence(rows,"Club QA")
    assert rows == before and h["external_calls"] == h["database_writes"] == 0
    json.dumps(h)


def test_team_center_reuses_the_same_verified_evidence_for_form():
    rows=[match(n) for n in range(1,8)]
    detail={"name":"Club QA","team":{"name":"Club QA"},"recent":rows,"upcoming":[],"live":[],"picks":[]}
    center=build_team_center_context(detail,observed_at_madrid="2026-09-21T12:00:00+02:00")
    assert center["result_history"]["included_count"] == 7
    assert center["form"]["sample_size"] == 5
    assert center["diagnostics"]["external_calls"] == 0


def test_incomplete_scope_is_not_verified():
    h=build_team_result_evidence([match(competition_id=None,season=None)],"Club QA")
    assert h["groups"][0]["scope_identified"] is False
    assert h["season_complete"] is False


def test_match_href_is_local_and_encoded():
    h=build_team_result_evidence([match(id="../../admin?q=qa")],"Club QA")
    assert h["items"][0]["href"] == "/match/..%2F..%2Fadmin%3Fq%3Dqa"


def test_single_main_landmark_and_shared_match_cards_remain():
    text=(ROOT/"templates/team_detail.html").read_text()
    assert '<main class="team-center-layout"' not in text
    assert 'match_card(match, true, true)' in text
    assert 'components/team_result_history.html' in text
