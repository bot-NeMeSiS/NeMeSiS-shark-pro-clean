from __future__ import annotations

import copy
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engines.match_context_engine import (
    MATCH_CONTEXT_INTELLIGENCE_CONTRACT,
    build_match_context,
)


MADRID = ZoneInfo("Europe/Madrid")


def _competition_identity(competition_id: str = "140") -> dict:
    return {
        "provider_id": competition_id,
        "canonical_id": f"api-football:competition:{competition_id}",
        "group_key": f"api-football-competition-{competition_id}",
    }


def _form_side(team: str, results: list[tuple[int, int, bool]]) -> dict:
    matches = []
    for index, (home_score, away_score, team_is_home) in enumerate(results, start=1):
        home = team if team_is_home else f"Rival {index}"
        away = f"Rival {index}" if team_is_home else team
        matches.append(
            {
                "match_id": f"form-{team}-{index}",
                "home_team": home,
                "away_team": away,
                "home_score": home_score,
                "away_score": away_score,
                "status": "FT",
                "season": "2026",
                "competition_identity": _competition_identity(),
                "kickoff_iso": f"2026-08-{20 + index:02d}T20:00:00+02:00",
                "source": "canonical_match_cache",
            }
        )
    return {
        "team": team,
        "season": "2026",
        "competition_identity": _competition_identity(),
        "requested_sample_size": 5,
        "matches": matches,
        "source": "canonical_match_cache",
    }


def _detail(*, status: str = "FT", updated_at: str | None = None) -> dict:
    now = datetime.now(MADRID)
    if updated_at is None:
        updated_at = now.isoformat(timespec="seconds")
    match = {
        "id": "context-match-1",
        "external_id": "9001",
        "home_team": "Club Norte",
        "away_team": "Club Sur",
        "competition_id": "140",
        "competition_name": "Liga Real",
        "country": "España",
        "season": "2026",
        "round": "Jornada 4",
        "match_date": "2026-08-30",
        "kickoff_time": "20:30",
        "kickoff_iso": "2026-08-30T20:30:00+02:00",
        "status": status,
        "provider_status": status,
        "source": "persisted_sports_cache",
        "last_synced_at": updated_at,
        "updated_at": updated_at,
    }
    if status == "FT":
        match.update({"home_score": 2, "away_score": 1, "score": "2-1"})
    return {
        "match": match,
        "timeline": [],
        "related_picks": [],
        "lineups": [],
        "cached_statistics": {"available": False, "items": []},
        "head_to_head": {
            "available": True,
            "source": "api_football_h2h_cache",
            "updated_at": "2026-08-29T18:00:00+02:00",
            "items": [
                {
                    "fixture_id": "8001",
                    "home_team": "Club Sur",
                    "away_team": "Club Norte",
                    "home_score": 0,
                    "away_score": 1,
                    "kickoff_iso": "2026-02-10T20:00:00+01:00",
                    "status": "FT",
                    "source": "api_football_h2h_cache",
                },
                {
                    "fixture_id": "wrong-pair",
                    "home_team": "Otro Club",
                    "away_team": "Club Norte",
                    "home_score": 1,
                    "away_score": 1,
                    "kickoff_iso": "2026-01-10T20:00:00+01:00",
                    "status": "FT",
                    "source": "api_football_h2h_cache",
                },
                {
                    "fixture_id": "missing-score",
                    "home_team": "Club Norte",
                    "away_team": "Club Sur",
                    "home_score": None,
                    "away_score": None,
                    "kickoff_iso": "2025-12-10T20:00:00+01:00",
                    "status": "FT",
                    "source": "api_football_h2h_cache",
                },
            ],
        },
        "standings": {
            "available": True,
            "source": "api_football_standings_deep",
            "competition_id": "140",
            "requested_season": "2026",
            "season": "2026",
            "updated_at": "2026-08-29T18:00:00+02:00",
            "rows": [
                {
                    "rank": 1,
                    "team_id": "10",
                    "team_name": "Club Norte",
                    "played": 4,
                    "points": 10,
                    "league_id": "140",
                    "season": "2026",
                },
                {
                    "rank": 2,
                    "team_id": "20",
                    "team_name": "Club Sur",
                    "played": 4,
                    "points": 7,
                    "league_id": "140",
                    "season": "2026",
                },
            ],
        },
        "recent_form": {
            "home": _form_side("Club Norte", [(2, 0, True), (1, 1, False)]),
            "away": _form_side("Club Sur", [(0, 1, True)]),
            "external_calls": 0,
        },
    }


def _context(detail: dict) -> dict:
    return build_match_context(
        detail,
        madrid_context={
            "client_full_datetime_label": "domingo, 30 de agosto · 20:30",
            "client_date_label": "domingo, 30 de agosto",
            "client_time_label": "20:30",
        },
    )


def test_context_intelligence_is_factual_complete_pure_and_non_predictive():
    detail = _detail()
    original = copy.deepcopy(detail)

    context = _context(detail)
    intelligence = context["context_intelligence"]

    assert detail == original
    assert intelligence["contract"] == MATCH_CONTEXT_INTELLIGENCE_CONTRACT
    assert intelligence["state"] == "VERIFIED"
    assert intelligence["unsupported_claims"] == 0
    assert intelligence["predictive_claims"] == 0
    assert intelligence["betting_claims"] == 0
    assert intelligence["external_calls"] == 0
    assert intelligence["database_writes"] == 0
    assert intelligence["identity"] == {
        "competition": "Liga Real",
        "season": "2026",
        "round": "Jornada 4",
        "madrid_datetime": "domingo, 30 de agosto · 20:30",
        "lifecycle": "FINISHED",
    }
    assert {item["kind"] for item in intelligence["evidence"]} == {
        "standings",
        "recent_form",
        "head_to_head",
    }
    assert context["recent_form"]["home"]["sample_size"] == 2
    assert context["recent_form"]["away"]["sample_size"] == 1
    assert context["head_to_head"]["count"] == 1
    assert context["standings"]["season_verified"] is True
    assert context["standings"]["context_eligible"] is True
    assert context["diagnostics"]["match_context_intelligence_external_calls"] == 0
    assert context["diagnostics"]["match_context_intelligence_database_writes"] == 0


def test_context_intelligence_is_honest_when_context_is_absent():
    detail = _detail()
    detail["head_to_head"] = {"available": False, "items": []}
    detail["standings"] = {"available": False, "rows": []}
    detail["recent_form"] = {}

    context = _context(detail)
    intelligence = context["context_intelligence"]

    assert intelligence["state"] == "INSUFFICIENT_DATA"
    assert intelligence["available"] is False
    assert "Faltan clasificación, forma reciente y H2H confirmados" in intelligence["headline"]
    assert context["recent_form"]["sample_size"] == 0
    assert context["standings"]["rows"] == []
    assert context["head_to_head"]["items"] == []


def test_wrong_season_competition_and_post_match_table_do_not_explain_context():
    detail = _detail()
    detail["standings"]["competition_id"] = "999"
    detail["standings"]["season"] = "2025"
    detail["standings"]["requested_season"] = "2025"
    detail["recent_form"]["home"]["matches"][0]["season"] = "2025"
    detail["recent_form"]["home"]["matches"][1]["competition_identity"] = _competition_identity("999")
    detail["recent_form"]["away"]["matches"][0]["season"] = "2025"
    detail["head_to_head"]["items"][0]["away_team"] = "Otro Club"

    context = _context(detail)

    assert context["standings"]["available"] is False
    assert context["standings"]["season_mismatch"] is True
    assert context["standings"]["identity_mismatch"] is True
    assert context["recent_form"]["available"] is False
    assert context["head_to_head"]["available"] is False
    assert context["context_intelligence"]["state"] == "INSUFFICIENT_DATA"

    posterior = _detail()
    posterior["standings"]["updated_at"] = "2026-08-31T09:00:00+02:00"
    posterior_context = _context(posterior)
    assert posterior_context["standings"]["available"] is True
    assert posterior_context["standings"]["context_eligible"] is False
    assert posterior_context["standings"]["temporal_state"] == "post_match_snapshot"
    assert all(
        item["kind"] != "standings"
        for item in posterior_context["context_intelligence"]["evidence"]
    )


def test_recent_team_form_never_infers_final_or_fills_a_missing_score(
    app_module,
    monkeypatch,
):
    expected = app_module.canonical_competition_surface_contract(
        {
            "competition_id": "140",
            "competition_name": "Liga Real",
            "country": "España",
            "season": "2026",
            "source": "api-football",
        }
    )
    candidates = [
        {
            "id": "valid-win",
            "home_team": "Club Norte",
            "away_team": "Rival Uno",
            "home_score": "2",
            "away_score": "0",
            "status": "FT",
            "competition_id": "140",
            "competition_name": "Liga Real",
            "country": "España",
            "season": "2026",
            "source": "api-football",
            "kickoff_iso": "2026-08-20T20:00:00+02:00",
        },
        {
            "id": "future-finished",
            "home_team": "Club Norte",
            "away_team": "Rival Futuro",
            "home_score": "5",
            "away_score": "0",
            "status": "FT",
            "competition_id": "140",
            "competition_name": "Liga Real",
            "country": "España",
            "season": "2026",
            "source": "api-football",
            "kickoff_iso": "2026-09-01T20:00:00+02:00",
        },
        {
            "id": "past-but-not-final",
            "home_team": "Club Norte",
            "away_team": "Rival Dos",
            "score": "4-0",
            "status": "NS",
            "match_date": "2020-01-01",
            "competition_id": "140",
            "competition_name": "Liga Real",
            "country": "España",
            "season": "2026",
            "source": "api-football",
        },
        {
            "id": "missing-score",
            "home_team": "Club Norte",
            "away_team": "Rival Tres",
            "status": "FT",
            "competition_id": "140",
            "competition_name": "Liga Real",
            "country": "España",
            "season": "2026",
            "source": "api-football",
        },
        {
            "id": "wrong-season",
            "home_team": "Rival Cuatro",
            "away_team": "Club Norte",
            "home_score": "0",
            "away_score": "3",
            "status": "FT",
            "competition_id": "140",
            "competition_name": "Liga Real",
            "country": "España",
            "season": "2025",
            "source": "api-football",
        },
        {
            "id": "wrong-competition",
            "home_team": "Rival Cinco",
            "away_team": "Club Norte",
            "home_score": "1",
            "away_score": "1",
            "status": "FT",
            "competition_id": "999",
            "competition_name": "Otra Liga",
            "country": "España",
            "season": "2026",
            "source": "api-football",
        },
    ]
    monkeypatch.setattr(app_module, "rows", lambda *_args, **_kwargs: candidates)
    monkeypatch.setattr(app_module, "is_fake_match", lambda _match: False)

    form = app_module.recent_team_form(
        "Club Norte",
        competition_identity=expected,
        season="2026",
        exclude_match_id="current",
        before_kickoff="2026-08-30T20:30:00+02:00",
    )

    assert form["sample_size"] == 1
    assert form["form"] == ["W"]
    assert form["summary"] == "1 victoria · 0 empates · 0 derrotas"
    assert form["external_calls"] == 0
    assert form["confirmed_results_only"] is True


def test_cached_standings_select_exact_season_and_latest_snapshot(
    app_module,
    monkeypatch,
    tmp_path,
):
    db_path = tmp_path / "match-context-standings.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE api_football_standings_deep (
            id TEXT PRIMARY KEY,
            league_id TEXT,
            league_name TEXT,
            season TEXT,
            team_id TEXT,
            team_name TEXT,
            rank INTEGER,
            points INTEGER,
            played INTEGER,
            wins INTEGER,
            draws INTEGER,
            losses INTEGER,
            goals_for INTEGER,
            goals_against INTEGER,
            form TEXT,
            description TEXT,
            snapshot_at TEXT
        )"""
    )
    conn.executemany(
        "INSERT INTO api_football_standings_deep VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("old-1", "140", "Liga Real", "2026", "10", "Club Norte", 3, 4, 2, 1, 1, 0, 3, 2, "WD", "", "2026-08-20T10:00:00+02:00"),
            ("new-1", "140", "Liga Real", "2026", "10", "Club Norte", 1, 10, 4, 3, 1, 0, 8, 3, "WWDW", "", "2026-08-29T18:00:00+02:00"),
            ("new-2", "140", "Liga Real", "2026", "20", "Club Sur", 2, 7, 4, 2, 1, 1, 6, 4, "WLWD", "", "2026-08-29T18:00:00+02:00"),
            ("other-season", "140", "Liga Real", "2025", "10", "Club Norte", 9, 1, 4, 0, 1, 3, 2, 9, "LLLD", "", "2026-08-30T18:00:00+02:00"),
            ("other-league", "999", "Liga Real", "2026", "10", "Club Norte", 8, 2, 4, 0, 2, 2, 2, 8, "LLDD", "", "2026-08-30T18:00:00+02:00"),
        ],
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(app_module, "DB_PATH", str(db_path), raising=False)
    monkeypatch.setattr(
        app_module,
        "_cached_fixture_identifiers",
        lambda _match: ({"league_id": "140"}, []),
    )
    monkeypatch.setattr(
        app_module,
        "competition_lookup",
        lambda _value: {"external_id": "140", "name": "Liga Real", "key": "liga-real"},
    )

    snapshot = app_module._cached_match_standings(
        {
            "id": "context-match-1",
            "competition_id": "140",
            "competition_name": "Liga Real",
            "season": "2026",
        }
    )

    assert [row["id"] for row in snapshot["rows"]] == ["new-1", "new-2"]
    assert snapshot["season_verified"] is True
    assert snapshot["identity_verified"] is True
    assert snapshot["updated_at"] == "2026-08-29T18:00:00+02:00"
    assert snapshot["external_calls"] == 0


def test_cached_standings_fail_closed_with_historical_schema(
    app_module,
    monkeypatch,
    tmp_path,
):
    db_path = tmp_path / "match-context-legacy-standings.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE api_football_standings_deep (
            league_id TEXT,
            league_name TEXT,
            team_id TEXT,
            team_name TEXT,
            rank INTEGER,
            points INTEGER,
            updated_at TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO api_football_standings_deep VALUES (?,?,?,?,?,?,?)",
        ("140", "Liga Real", "10", "Club Norte", 1, 10, "2026-08-29T18:00:00+02:00"),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(app_module, "DB_PATH", str(db_path), raising=False)
    monkeypatch.setattr(
        app_module,
        "_cached_fixture_identifiers",
        lambda _match: ({"league_id": "140"}, []),
    )
    monkeypatch.setattr(
        app_module,
        "competition_lookup",
        lambda _value: {"external_id": "140", "name": "Liga Real", "key": "liga-real"},
    )

    snapshot = app_module._cached_match_standings(
        {
            "id": "context-match-legacy",
            "competition_id": "140",
            "competition_name": "Liga Real",
            "season": "2026",
        }
    )

    assert snapshot["available"] is False
    assert snapshot["rows"] == []
    assert snapshot["season_verified"] is False
    assert snapshot["external_calls"] == 0


@pytest.mark.parametrize(
    ("status", "age", "expected_live", "expected_finished"),
    [
        ("NS", timedelta(seconds=0), False, False),
        ("LIVE", timedelta(seconds=0), True, False),
        ("LIVE", timedelta(hours=2), False, False),
        ("SUSP", timedelta(seconds=0), False, False),
        ("FT", timedelta(seconds=0), False, True),
    ],
)
def test_context_preserves_canonical_status_truth(
    status,
    age,
    expected_live,
    expected_finished,
):
    updated_at = (datetime.now(MADRID) - age).isoformat(timespec="seconds")
    detail = _detail(status=status, updated_at=updated_at)
    if status == "NS":
        future = datetime.now(MADRID) + timedelta(days=2)
        detail["match"]["match_date"] = future.date().isoformat()
        detail["match"]["kickoff_time"] = future.strftime("%H:%M")
        detail["match"]["kickoff_iso"] = future.isoformat(timespec="seconds")
    context = _context(detail)

    assert context["lifecycle"]["is_live"] is expected_live
    assert context["lifecycle"]["is_finished"] is expected_finished
    if not expected_live:
        assert context["lifecycle"]["minute"] is None


def test_match_context_reuses_domain_truth_and_ignores_generic_tracker_timestamp():
    from engines.match_context_engine import _lifecycle_from_domain

    lifecycle = _lifecycle_from_domain(
        {
            "source": "api_football",
            "minute": 67,
            "data_quality": "STALE",
            "status_truth": {
                "contract": "MATCH-STATUS-TRUTH-V2",
                "lifecycle": "STALE",
                "is_live": False,
                "is_finished": False,
                "is_stale": True,
                "stale_reason": "LIVE_TIMESTAMP_MISSING",
            },
        },
        raw_match={"status": "LIVE"},
        live={
            "available": True,
            "status": "LIVE",
            "updated_at": datetime.now(MADRID).isoformat(timespec="seconds"),
        },
    )

    assert lifecycle["key"] == "STALE"
    assert lifecycle["is_live"] is False
    assert lifecycle["minute"] is None


def test_unconfirmed_score_is_not_displayed_or_promoted_to_evidence():
    detail = _detail(status="LIVE")
    detail["match"]["home_score"] = 1
    detail["match"]["away_score"] = None
    detail["match"]["score"] = "1-"
    context = build_match_context(
        detail,
        madrid_context={
            "client_full_datetime_label": "domingo, 30 de agosto · 20:30",
            "client_score_label": "1-0",
        },
    )

    assert context["score"] == {
        "home": None,
        "away": None,
        "label": "VS",
        "confirmed": False,
    }
    assert all(
        item.get("kind") != "score"
        for item in context["intelligence"]["evidence"]
    )


@pytest.mark.parametrize(
    ("status", "expected_word"),
    [
        ("CANCELLED", "cancelado"),
        ("POSTPONED", "aplazado"),
        ("SUSPENDED", "suspendido"),
        ("ABANDONED", "abandonado"),
    ],
)
def test_terminal_nonplayed_state_is_never_narrated_as_scheduled(
    status,
    expected_word,
):
    context = _context(_detail(status=status))
    factual = context["summaries"]["items"][0]["text"].lower()
    story = context["story"]["summary"].lower()

    assert expected_word in factual
    assert expected_word in story
    assert "programado" not in factual
    assert "programado" not in story


def test_future_context_evidence_and_one_sided_table_are_rejected():
    detail = _detail()
    detail["head_to_head"]["items"].append(
        {
            "fixture_id": "future-h2h",
            "home_team": "Club Norte",
            "away_team": "Club Sur",
            "home_score": 4,
            "away_score": 0,
            "kickoff_iso": "2026-09-02T20:00:00+02:00",
            "status": "FT",
            "source": "api_football_h2h_cache",
        }
    )
    detail["recent_form"]["home"]["matches"].append(
        {
            "match_id": "future-form",
            "home_team": "Club Norte",
            "away_team": "Rival Futuro",
            "home_score": 3,
            "away_score": 0,
            "status": "FT",
            "season": "2026",
            "competition_identity": _competition_identity(),
            "kickoff_iso": "2026-09-03T20:00:00+02:00",
            "source": "canonical_match_cache",
        }
    )
    detail["standings"]["rows"] = detail["standings"]["rows"][:1]

    context = _context(detail)

    assert context["head_to_head"]["count"] == 1
    assert context["recent_form"]["home"]["sample_size"] == 2
    assert all(
        item["kind"] != "standings"
        for item in context["context_intelligence"]["evidence"]
    )


def test_match_center_template_exposes_context_without_generic_shark_copy(
    client,
    app_module,
    monkeypatch,
):
    detail = _detail()
    monkeypatch.setattr(app_module, "match_detail", lambda *_args, **_kwargs: detail)
    monkeypatch.setattr(app_module, "v935_enrich_match_lifecycle", lambda match: match)
    monkeypatch.setattr(
        app_module,
        "live_tracker_for_match",
        lambda *_args, **_kwargs: {"available": False},
    )
    monkeypatch.setattr(app_module, "_cached_lineups_for_match", lambda _match: [])
    monkeypatch.setattr(
        app_module,
        "_cached_match_media",
        lambda _match: {"visible_count": 0, "visible_videos": []},
    )
    monkeypatch.setattr(
        app_module,
        "_cached_match_statistics",
        lambda _match: detail["cached_statistics"],
    )
    monkeypatch.setattr(
        app_module,
        "_cached_h2h_for_match",
        lambda _match: detail["head_to_head"],
    )
    monkeypatch.setattr(
        app_module,
        "_cached_match_standings",
        lambda _match: detail["standings"],
    )
    forms = {
        "Club Norte": detail["recent_form"]["home"],
        "Club Sur": detail["recent_form"]["away"],
    }
    monkeypatch.setattr(
        app_module,
        "recent_team_form",
        lambda team, **_kwargs: forms[team],
    )

    response = client.get("/match/context-match-1")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Por qué importa este partido" in html
    assert MATCH_CONTEXT_INTELLIGENCE_CONTRACT in html
    assert "muestra 2" in html
    assert "muestra 1" in html
    assert 'data-standings-season="2026"' in html
    assert "No se utiliza para explicar retrospectivamente" not in html
