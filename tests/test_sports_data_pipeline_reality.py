from __future__ import annotations

import json
import sqlite3
from datetime import date

from engines import api_exploitation_engine as exploitation
from engines import api_football_live_tracker_engine as live_tracker
from engines import api_sports_provider_engine as provider
from engines.autonomous_product_qa_engine import detect_product_qa_issues


def _provider_payload(response):
    return {
        "ok": True,
        "response": response,
        "http_status": 200,
        "quota": {"daily_limit": 100, "daily_remaining": 91},
    }


def _fixture_payload():
    today = date.today().isoformat()
    return {
        "fixture": {
            "id": 9001,
            "date": f"{today}T20:00:00+02:00",
            "status": {"short": "FT", "long": "Match Finished", "elapsed": 90},
            "venue": {"name": "Estadio Real"},
        },
        "league": {
            "id": 140,
            "name": "Liga Real",
            "country": "España",
            "season": 2026,
            "round": "Jornada 1",
        },
        "teams": {
            "home": {"id": 10, "name": "Club Norte", "logo": "https://img.invalid/10.png"},
            "away": {"id": 20, "name": "Club Sur", "logo": "https://img.invalid/20.png"},
        },
        "goals": {"home": 2, "away": 1},
    }


def _fake_api_get(path, params=None, timeout=18):
    if path == "status":
        return _provider_payload(
            {
                "subscription": {"plan": "Pro", "active": True, "end": "2026-12-31"},
                "requests": {"current": 9, "limit_day": 100},
            }
        )
    if path == "fixtures/lineups":
        return _provider_payload(
            [
                {
                    "team": {"id": 10, "name": "Club Norte"},
                    "formation": "4-3-3",
                    "startXI": [{"player": {"id": 101, "name": "Jugador Real", "number": 8, "pos": "M", "grid": "2:2"}}],
                    "substitutes": [],
                }
            ]
        )
    if path == "fixtures/events":
        return _provider_payload(
            [
                {
                    "time": {"elapsed": 32, "extra": None},
                    "team": {"id": 10, "name": "Club Norte"},
                    "player": {"id": 101, "name": "Jugador Real"},
                    "assist": {"id": 102, "name": "Asistente Real"},
                    "type": "Goal",
                    "detail": "Normal Goal",
                }
            ]
        )
    if path == "fixtures/statistics":
        return _provider_payload(
            [
                {
                    "team": {"id": 10, "name": "Club Norte"},
                    "statistics": [{"type": "Ball Possession", "value": "56%"}],
                },
                {
                    "team": {"id": 20, "name": "Club Sur"},
                    "statistics": [{"type": "Ball Possession", "value": "44%"}],
                },
            ]
        )
    if path == "injuries":
        return _provider_payload(
            [
                {
                    "player": {"id": 103, "name": "Jugador Lesionado", "type": "Missing Fixture", "reason": "Muscle"},
                    "team": {"id": 10, "name": "Club Norte"},
                    "fixture": {"id": 9001, "date": date.today().isoformat()},
                    "league": {"id": 140, "season": 2026},
                }
            ]
        )
    if path == "fixtures/headtohead":
        return _provider_payload([_fixture_payload()])
    if path == "standings":
        return _provider_payload(
            [
                {
                    "league": {
                        "id": 140,
                        "name": "Liga Real",
                        "season": 2026,
                        "standings": [
                            [
                                {
                                    "rank": 1,
                                    "team": {"id": 10, "name": "Club Norte"},
                                    "points": 3,
                                    "all": {"played": 1, "win": 1, "draw": 0, "lose": 0, "goals": {"for": 2, "against": 1}},
                                }
                            ]
                        ],
                    }
                }
            ]
        )
    raise AssertionError(f"unexpected provider path: {path}")


def test_provider_keys_are_stripped(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_KEY", " secret-with-space \r\n")
    assert exploitation._api_football_key() == "secret-with-space"
    assert live_tracker._api_key() == "secret-with-space"
    assert provider._provider_key() == "secret-with-space"


def test_fixture_selection_rejects_foreign_provider_ids(tmp_path):
    db_path = tmp_path / "fixture-provenance.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE matches(
            id TEXT, external_id TEXT, source TEXT, league_id TEXT, competition_id TEXT,
            league_name TEXT, competition_name TEXT, season TEXT, kickoff_iso TEXT,
            match_date TEXT, status TEXT, home_team_id TEXT, away_team_id TEXT,
            home_team TEXT, away_team TEXT
        )
        """
    )
    today = date.today().isoformat()
    conn.executemany(
        "INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("af-9001", "9001", "api_football_live", "140", "140", "Liga Real", "Liga Real", "2026", f"{today}T20:00:00+02:00", today, "FT", "10", "20", "Club Norte", "Club Sur"),
            ("sportsdb-9001", "9001", "TheSportsDB API", "4335", "4335", "Liga distinta", "Liga distinta", "2026", f"{today}T19:00:00+02:00", today, "FT", "", "", "Otro Norte", "Otro Sur"),
            ("odds-777", "777", "The Odds API", "", "", "Otra liga", "Otra liga", "", f"{today}T18:00:00+02:00", today, "NS", "", "", "Equipo A", "Equipo B"),
        ],
    )
    conn.commit()
    conn.row_factory = sqlite3.Row

    rows = exploitation._recent_fixture_rows(conn, limit=20, days_back=1, days_ahead=1)

    assert [row["external_id"] for row in rows] == ["9001"]
    assert rows[0]["internal_match_id"] == "af-9001"
    conn.close()


def test_real_provider_payload_reaches_cache_players_and_continuity(tmp_path, monkeypatch):
    db_path = str(tmp_path / "pipeline.db")
    live_tracker.ensure_live_tracker_schema(db_path)
    exploitation.ensure_api_exploitation_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    live_tracker._upsert_fixture(conn, _fixture_payload())
    conn.commit()
    conn.close()
    monkeypatch.setenv("API_FOOTBALL_KEY", "configured-test-key")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_PROVIDER", "true")
    monkeypatch.setattr(exploitation, "_api_get", _fake_api_get)

    result = exploitation.run_api_exploitation_cycle(
        db_path,
        limit=10,
        deep_limit=1,
        fixture_ids=["9001"],
        max_external_calls=7,
    )

    assert result["status"] == "OK"
    assert result["metrics"]["external_calls"] == 7
    assert result["selected_fixture_ids"] == ["9001"]
    assert result["capabilities"]["lineups"]["player_ids"] == 1
    assert result["capabilities"]["events"]["event_types"] == {"goal": 1}
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM api_football_lineups_deep WHERE fixture_id='9001'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM api_football_live_events WHERE fixture_id='9001'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM api_football_match_stats_history WHERE fixture_id='9001'").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM api_football_h2h_history").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM api_football_standings_deep").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM player_profiles WHERE player_id='101'").fetchone()[0] == 1
    persisted_payload = json.loads(
        conn.execute("SELECT payload_json FROM api_exploitation_runs ORDER BY id DESC LIMIT 1").fetchone()[0]
    )
    assert persisted_payload["selected_fixture_ids"] == ["9001"]
    conn.close()
    summary = exploitation.api_exploitation_summary(db_path)
    continuity = {item["capability"]: item for item in summary["continuity"]}
    assert continuity["lineups"]["gap"] == "NO_GAP"
    assert continuity["events"]["gap"] == "NO_GAP"
    assert continuity["players"]["gap"] == "NO_GAP"
    assert "configured-test-key" not in json.dumps(result)


def test_free_plan_uses_supported_h2h_shape_and_skips_unavailable_season(tmp_path, monkeypatch):
    db_path = str(tmp_path / "free-plan.db")
    live_tracker.ensure_live_tracker_schema(db_path)
    exploitation.ensure_api_exploitation_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    live_tracker._upsert_fixture(conn, _fixture_payload())
    conn.commit()
    conn.close()
    calls = []

    def fake_get(path, params=None, timeout=18):
        calls.append((path, dict(params or {})))
        if path == "status":
            return _provider_payload(
                {
                    "subscription": {"plan": "Free", "active": True},
                    "requests": {"current": 9, "limit_day": 100},
                }
            )
        return _provider_payload([])

    monkeypatch.setenv("API_FOOTBALL_KEY", "configured-test-key")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_PROVIDER", "true")
    monkeypatch.setattr(exploitation, "_api_get", fake_get)

    result = exploitation.run_api_exploitation_cycle(
        db_path,
        deep_limit=1,
        fixture_ids=["9001"],
        max_external_calls=7,
    )

    h2h_params = next(params for path, params in calls if path == "fixtures/headtohead")
    assert "last" not in h2h_params
    assert not any(path == "standings" for path, _params in calls)
    assert result["capabilities"]["standings"]["reason"] == "account_plan_season_unavailable"
    assert result["metrics"]["external_calls"] == 6


def test_deep_enrichment_is_due_gated_after_success(tmp_path, monkeypatch):
    db_path = str(tmp_path / "due-gate.db")
    live_tracker.ensure_live_tracker_schema(db_path)
    exploitation.ensure_api_exploitation_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    live_tracker._upsert_fixture(conn, _fixture_payload())
    conn.commit()
    conn.close()
    monkeypatch.setenv("API_FOOTBALL_KEY", "configured-test-key")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_PROVIDER", "true")
    monkeypatch.setattr(exploitation, "_api_get", _fake_api_get)
    first = exploitation.run_api_exploitation_cycle(db_path, deep_limit=1, fixture_ids=["9001"], max_external_calls=7)
    assert first["status"] == "OK"
    monkeypatch.setattr(exploitation, "_api_get", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("provider called")))

    second = exploitation.run_api_exploitation_if_due(db_path, refresh_hours=24, fixture_ids=["9001"])

    assert second["status"] == "SKIPPED_NOT_DUE"
    assert second["external_calls"] == 0


def test_sports_scheduler_invokes_due_gated_deep_cycle(app_module, monkeypatch):
    deep_calls = []
    monkeypatch.setattr(app_module, "sports_sync_window_state", lambda: {"live_refresh_required": False})
    monkeypatch.setattr(app_module, "has_request_context", lambda: False)
    monkeypatch.setattr(app_module, "sync_api_football_match_window", lambda *_args, **_kwargs: {"ok": True, "fixtures_count": 1, "external_calls": 1})
    monkeypatch.setattr(app_module, "_api_football_deep_enrichment_candidates", lambda limit=1: ["9001"])
    monkeypatch.setattr(app_module, "run_api_exploitation_if_due", lambda *_args, **kwargs: deep_calls.append(kwargs) or {"ok": True, "status": "SKIPPED_NOT_DUE", "external_calls": 0})
    monkeypatch.setattr(app_module, "sync_odds_events", lambda **_kwargs: {"ok": True, "skipped": True})
    monkeypatch.setattr(app_module, "run_pick_grading", lambda *_args, **_kwargs: {"ok": True, "picks_checked": 0})
    monkeypatch.setattr(app_module, "invalidate_v934_realtime_cache", lambda *_args: None)
    monkeypatch.setattr(app_module, "automation_safe_set", lambda *_args: {"ok": True})

    result = app_module.run_sports_sync_cycle()

    assert result["deep_status"] == "SKIPPED_NOT_DUE"
    assert deep_calls == [{"fixture_ids": ["9001"], "deep_limit": 1}]


def test_shared_cron_exposes_only_sanitized_pipeline_evidence(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "run_sports_sync_cycle",
        lambda **_kwargs: {
            "status": "OK",
            "deep_status": "OK",
            "deep_external_calls": 7,
            "deep_enrichment": {
                "account": {"ok": True, "plan": "Free", "quota": {"daily_remaining": 91}},
                "capabilities": {"lineups": {"requested": True, "received": 2, "persisted": 2}},
            },
        },
    )
    monkeypatch.setattr(app_module, "telegram_scheduler_tick", lambda **_kwargs: {"ok": True, "status": "PASS"})

    result = app_module.telegram_cron_with_sports_sync()

    assert result["sports_pipeline"]["provider_authenticated"] is True
    assert result["sports_pipeline"]["provider_plan"] == "Free"
    assert result["sports_pipeline"]["capabilities"]["lineups"]["persisted"] == 2
    assert "secret" not in json.dumps(result).lower()


def test_shared_cron_reuses_persisted_pipeline_evidence_when_deep_sample_is_not_due(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "run_sports_sync_cycle",
        lambda **_kwargs: {
            "status": "OK",
            "deep_status": "SKIPPED_NOT_DUE",
            "deep_external_calls": 0,
            "deep_enrichment": {"status": "SKIPPED_NOT_DUE"},
        },
    )
    monkeypatch.setattr(
        app_module,
        "api_exploitation_summary",
        lambda _db_path: {
            "latest_account": {
                "ok": True,
                "plan": "Free",
                "quota": {"daily_limit": 100, "daily_used": 7, "daily_remaining": 93},
            },
            "latest_run": {
                "status": "OK",
                "finished_at": "2026-09-01T15:20:00+00:00",
                "external_calls": 7,
                "payload_json": json.dumps({"selected_fixture_ids": ["9001"]}),
            },
            "continuity": [
                {
                    "capability": "lineups",
                    "requested": True,
                    "received": 2,
                    "persisted": 2,
                }
            ],
        },
    )
    monkeypatch.setattr(app_module, "telegram_scheduler_tick", lambda **_kwargs: {"ok": True, "status": "PASS"})

    result = app_module.telegram_cron_with_sports_sync()
    pipeline = result["sports_pipeline"]

    assert pipeline["provider_authenticated"] is True
    assert pipeline["quota"]["daily_remaining"] == 93
    assert pipeline["capabilities"]["lineups"]["persisted"] == 2
    assert pipeline["last_sample"]["fixture_ids"] == ["9001"]
    assert pipeline["deep_external_calls"] == 0


def test_render_cron_endpoint_preserves_sanitized_pipeline_evidence(client, app_module, monkeypatch):
    secret = "pytest-automation-secret"
    monkeypatch.setenv("AUTOMATION_SECRET", secret)
    monkeypatch.setattr(
        app_module,
        "run_sports_sync_cycle",
        lambda **_kwargs: {
            "status": "OK",
            "deep_status": "SKIPPED_NOT_DUE",
            "deep_external_calls": 0,
            "deep_enrichment": {"status": "SKIPPED_NOT_DUE"},
        },
    )
    monkeypatch.setattr(
        app_module,
        "api_exploitation_summary",
        lambda _db_path: {
            "latest_account": {
                "ok": True,
                "plan": "Free",
                "quota": {"daily_limit": 100, "daily_used": 7, "daily_remaining": 93},
            },
            "latest_run": {
                "status": "OK",
                "finished_at": "2026-09-01T15:20:00+00:00",
                "external_calls": 7,
                "payload_json": json.dumps({"selected_fixture_ids": ["9001"]}),
            },
            "continuity": [
                {
                    "capability": "lineups",
                    "requested": True,
                    "received": 2,
                    "persisted": 2,
                }
            ],
        },
    )
    monkeypatch.setattr(app_module, "telegram_scheduler_tick", lambda **_kwargs: {"ok": True, "status": "PASS"})

    response = client.get(
        "/api/automation/telegram/tick?runner=render_cron",
        headers={"X-Automation-Secret": secret, "X-NeMeSiS-Cron-Runner": "render-cron"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    pipeline = payload["sports_pipeline"]
    assert pipeline["provider_authenticated"] is True
    assert pipeline["provider_plan"] == "Free"
    assert pipeline["quota"]["daily_remaining"] == 93
    assert pipeline["capabilities"]["lineups"]["persisted"] == 2
    assert pipeline["last_sample"]["fixture_ids"] == ["9001"]
    assert secret not in json.dumps(payload)


def test_quality_worker_detects_provider_to_ui_break():
    issues = detect_product_qa_issues(
        {
            "production_sha": "qa-sha",
            "provider_continuity": [
                {
                    "capability": "events",
                    "provider": "API-Football",
                    "requested": True,
                    "received": 3,
                    "persisted": 0,
                    "ui_contract": True,
                    "rendered": False,
                }
            ],
        }
    )

    matches = [item for item in issues if item.get("element") == "provider-to-ui:events"]
    assert len(matches) == 1
    assert matches[0]["category"] == "DATA_QUALITY"
    assert "break=persistence" in matches[0]["actual"]


def test_existing_odds_calls_capture_quota_without_extra_probe(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "odds_competitions", lambda: [{"odds_key": "soccer_test", "name": "Liga Test"}])
    monkeypatch.setattr(
        app_module,
        "odds_api_request",
        lambda *_args, **_kwargs: {
            "ok": True,
            "payload": [{"id": "event-1"}],
            "http_status": 200,
            "quota": {"requests_last": 2, "requests_used": 42, "requests_remaining": 58},
        },
    )

    events, errors, quota = app_module.fetch_odds_events(limit=10)

    assert len(events) == 1
    assert errors == []
    assert quota == {
        "observed_calls": 1,
        "requests_last_total": 2,
        "requests_used": 42,
        "requests_remaining": 58,
        "http_status": 200,
    }
