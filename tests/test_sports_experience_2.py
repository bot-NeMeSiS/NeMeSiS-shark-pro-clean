from __future__ import annotations

import sqlite3

from engines.match_context_engine import build_match_context


def _detail() -> dict:
    return {
        "match": {
            "id": "match-real-1",
            "external_id": "9001",
            "home_team": "Club Norte",
            "away_team": "Club Sur",
            "competition_id": "140",
            "competition_name": "Liga Real",
            "match_date": "2026-08-30",
            "kickoff_iso": "2026-08-30T20:30:00+02:00",
            "status": "FT",
            "home_score": 2,
            "away_score": 1,
            "source": "persisted_sports_cache",
            "updated_at": "2026-08-30T22:30:00+02:00",
            "status_info": {
                "key": "FT",
                "label": "Final",
                "is_finished": True,
                "is_live": False,
                "is_upcoming": False,
            },
        },
        "timeline": [],
        "related_picks": [],
        "lineups": [
            {
                "fixture_id": "9001",
                "team_id": "10",
                "team_name": "Club Norte",
                "formation": "4-3-3",
                "player_id": "101",
                "player_name": "Jugador Real",
                "position": "MID",
                "number": "8",
                "is_starting": 1,
                "captured_at": "2026-08-30T19:30:00+02:00",
            }
        ],
        "cached_statistics": {
            "available": True,
            "source": "api_football_stats_cache",
            "updated_at": "2026-08-30T22:30:00+02:00",
            "items": [
                {
                    "key": "ball_possession",
                    "label": "Ball Possession",
                    "home": "56%",
                    "away": "44%",
                },
                {
                    "key": "expected_goals",
                    "label": "Expected Goals",
                    "home": "1.62",
                    "away": None,
                },
            ],
        },
        "head_to_head": {
            "available": True,
            "source": "api_football_h2h_cache",
            "updated_at": "2026-08-30T18:00:00+02:00",
            "items": [
                {
                    "fixture_id": "8001",
                    "home_team": "Club Sur",
                    "away_team": "Club Norte",
                    "home_score": 0,
                    "away_score": 1,
                    "score": "0-1",
                    "competition": "Liga Real",
                    "kickoff_iso": "2026-02-10T20:00:00+01:00",
                    "status": "FT",
                    "source": "api_football_h2h_cache",
                },
                {
                    "fixture_id": "future-not-h2h",
                    "home_team": "Club Norte",
                    "away_team": "Club Sur",
                    "kickoff_iso": "2027-02-10T20:00:00+01:00",
                    "status": "NS",
                    "source": "api_football_h2h_cache",
                },
            ],
        },
        "standings": {
            "available": True,
            "source": "api_football_standings_deep",
            "updated_at": "2026-08-30",
            "rows": [
                {
                    "rank": 1,
                    "team_id": "10",
                    "team_name": "Club Norte",
                    "played": 4,
                    "wins": 3,
                    "draws": 1,
                    "losses": 0,
                    "goals_for": 8,
                    "goals_against": 3,
                    "points": 10,
                },
                {
                    "rank": 2,
                    "team_id": "20",
                    "team_name": "Club Sur",
                    "played": 4,
                    "wins": 2,
                    "draws": 1,
                    "losses": 1,
                    "goals_for": 6,
                    "goals_against": 4,
                    "points": 7,
                },
            ],
        },
    }


def _context() -> dict:
    return build_match_context(
        _detail(),
        madrid_context={
            "client_full_datetime_label": "domingo, 30 de agosto · 20:30",
            "client_date_label": "domingo, 30 de agosto",
            "client_time_label": "20:30",
            "client_score_label": "2-1",
        },
    )


def test_match_center_uses_only_persisted_real_depth():
    context = _context()

    assert context["statistics"]["available"] is True
    assert context["statistics"]["snapshot_kind"] == "persisted"
    assert context["statistics"]["items"][0]["label"] == "Posesión"
    assert context["statistics"]["items"][1]["away"] == "No disponible"
    assert context["head_to_head"]["count"] == 1
    assert context["head_to_head"]["items"][0]["fixture_id"] == "8001"
    assert context["standings"]["count"] == 2
    assert context["standings"]["rows"][0]["points"] == 10
    assert context["lineups"]["fake_players_created"] == 0
    assert context["lineups"]["teams"][0]["starters"][0]["href"] == "/player/101"
    assert context["diagnostics"]["external_calls"] == 0
    assert context["diagnostics"]["head_to_head_external_calls"] == 0
    assert context["diagnostics"]["standings_external_calls"] == 0


def test_shark_history_is_caller_supplied_and_not_a_prediction():
    intelligence = _context()["intelligence"]
    trends = intelligence["conclusions"]["tendencias"]

    assert trends["state"] == "PARTIALLY_VERIFIED"
    assert trends["value"]["sample_size"] == 1
    assert trends["method"] == "caller_supplied_history_only"
    assert trends["evidence_ids"] == ["historical-observations"]
    assert intelligence["diagnostics"]["external_calls"] == 0


def test_empty_depth_never_becomes_zero_or_fake_data():
    detail = _detail()
    detail["cached_statistics"] = {"available": False, "items": []}
    detail["head_to_head"] = {"available": False, "items": []}
    detail["standings"] = {"available": False, "rows": []}
    detail["lineups"] = []

    context = build_match_context(detail)

    assert context["statistics"]["items"] == []
    assert context["head_to_head"]["items"] == []
    assert context["standings"]["rows"] == []
    assert context["lineups"]["player_count"] == 0
    assert context["summaries"]["unsupported_claims"] == 0


def test_cached_fixture_identity_connects_internal_match_to_real_rows(
    app_module,
    monkeypatch,
    tmp_path,
):
    db_path = tmp_path / "sports-experience-2.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE api_football_fixture_index (
            id TEXT PRIMARY KEY,
            fixture_id TEXT,
            internal_match_id TEXT,
            league_id TEXT,
            league_name TEXT,
            home_team_id TEXT,
            away_team_id TEXT,
            last_seen_at TEXT
        );
        CREATE TABLE api_football_lineups_deep (
            id TEXT PRIMARY KEY,
            fixture_id TEXT,
            team_id TEXT,
            team_name TEXT,
            formation TEXT,
            player_id TEXT,
            player_name TEXT,
            number TEXT,
            position TEXT,
            is_starting INTEGER,
            captured_at TEXT
        );
        CREATE TABLE api_football_match_stats_history (
            id TEXT PRIMARY KEY,
            fixture_id TEXT,
            team_id TEXT,
            team_name TEXT,
            stat_name TEXT,
            stat_value TEXT,
            numeric_value REAL,
            captured_at TEXT
        );
        CREATE TABLE api_football_h2h_history (
            id TEXT PRIMARY KEY,
            team_a_id TEXT,
            team_b_id TEXT,
            fixture_id TEXT,
            league_name TEXT,
            kickoff_iso TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            status TEXT,
            captured_at TEXT
        );
        """
    )
    conn.execute(
        "INSERT INTO api_football_fixture_index VALUES (?,?,?,?,?,?,?,?)",
        ("idx-1", "9001", "match-real-1", "140", "Liga Real", "10", "20", "2026-08-30T22:30:00+02:00"),
    )
    conn.execute(
        "INSERT INTO api_football_lineups_deep VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("lineup-1", "9001", "10", "Club Norte", "4-3-3", "101", "Jugador Real", "8", "MID", 1, "2026-08-30T19:30:00+02:00"),
    )
    conn.executemany(
        "INSERT INTO api_football_match_stats_history VALUES (?,?,?,?,?,?,?,?)",
        [
            ("stat-1", "9001", "10", "Club Norte", "Ball Possession", "56%", 56, "2026-08-30T22:30:00+02:00"),
            ("stat-2", "9001", "20", "Club Sur", "Ball Possession", "44%", 44, "2026-08-30T22:30:00+02:00"),
            ("stat-empty", "9001", "20", "Club Sur", "Expected Goals", "", 0, "2026-08-30T22:30:00+02:00"),
        ],
    )
    conn.execute(
        "INSERT INTO api_football_h2h_history VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("h2h-1", "10", "20", "8001", "Liga Real", "2026-02-10T20:00:00+01:00", "Club Sur", "Club Norte", 0, 1, "FT", "2026-08-30T18:00:00+02:00"),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(app_module, "DB_PATH", str(db_path), raising=False)
    match = {
        "id": "match-real-1",
        "home_team": "Club Norte",
        "away_team": "Club Sur",
    }
    lineups = app_module._cached_lineups_for_match(match)
    statistics = app_module._cached_match_statistics(match)
    h2h = app_module._cached_h2h_for_match(match, limit=1)

    assert lineups[0]["fixture_id"] == "9001"
    assert lineups[0]["player_id"] == "101"
    assert statistics["items"] == [
        {
            "key": "ball_possession",
            "label": "Ball Possession",
            "home": "56%",
            "away": "44%",
            "leader": "even",
        }
    ]
    assert h2h["items"][0]["score"] == "0-1"
    assert h2h["external_calls"] == 0


def test_match_template_exposes_only_available_real_sections(
    client,
    app_module,
    monkeypatch,
):
    detail = _detail()
    monkeypatch.setattr(app_module, "match_detail", lambda *_args, **_kwargs: detail)
    monkeypatch.setattr(
        app_module,
        "v935_enrich_match_lifecycle",
        lambda match: match,
    )
    monkeypatch.setattr(
        app_module,
        "live_tracker_for_match",
        lambda *_args, **_kwargs: {"available": False},
    )
    monkeypatch.setattr(
        app_module,
        "_cached_lineups_for_match",
        lambda _match: detail["lineups"],
    )
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

    response = client.get("/match/match-real-1")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'data-match-section-link="h2h"' in html
    assert 'data-match-section-link="standings"' in html
    assert 'data-h2h-fixture="8001"' in html
    assert 'data-standings-contract="NEMESIS-MATCH-STANDINGS-CACHE-V1"' in html
    assert "Jugador Real" in html
    assert "Resumen en vídeo no disponible" not in html
