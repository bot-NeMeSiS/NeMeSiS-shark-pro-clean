"""Statistics refresh through the sports job, SQLite and the real Match Center.

All fixtures and account keys below are synthetic. Only provider transport is
replaced; persistence, fixture identity, cache readers and HTML are exercised.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import socket
import sqlite3

import pytest

from engines import api_football_live_tracker_engine as tracker
from engines import api_football_statistics_engine as statistics
from engines.api_usage_guard_engine import api_usage_snapshot
from engines.match_context_engine import build_match_context


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """An accidental unmocked provider request must fail this test suite."""
    attempts = []

    def reject(*_args, **_kwargs):
        attempts.append(True)
        raise AssertionError("Statistics integration tests must never use the network")

    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket, "create_connection", reject)
    yield
    assert attempts == []


@pytest.fixture
def statistics_db(tmp_path, app_module, monkeypatch):
    path = str(tmp_path / "statistics-integration.sqlite")
    monkeypatch.setattr(app_module, "DB_PATH", path)
    monkeypatch.setenv("API_FOOTBALL_KEY", "synthetic-statistics-key")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_PROVIDER", "true")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_LIVE_TRACKER", "true")
    monkeypatch.setenv("ENABLE_API_FOOTBALL_STATISTICS_SYNC", "true")
    monkeypatch.setenv("ENABLE_API_SPORTS_NETWORK_CALLS", "true")
    monkeypatch.setenv("API_FOOTBALL_DAILY_CALL_BUDGET", "10")
    monkeypatch.setenv("API_FOOTBALL_STATISTICS_TRANSPORT", "batch")
    app_module.init_db()
    tracker.ensure_live_tracker_schema(path)
    # Model a warmed web worker. Request rendering must not own initialization.
    monkeypatch.setattr(app_module, "APP_INITIALIZED", True)
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", path)
    return path


def fixture_payload(fixture_id, *, status="2H"):
    now = datetime.now(timezone.utc)
    return {
        "fixture": {
            "id": int(fixture_id),
            "date": (now - timedelta(hours=2 if status == "FT" else 1)).isoformat(),
            "status": {
                "short": status,
                "long": "Match Finished" if status == "FT" else "Second Half",
                "elapsed": 90 if status == "FT" else 61,
            },
        },
        "league": {"id": 140, "name": "LaLiga", "country": "Spain", "season": now.year},
        "teams": {
            "home": {"id": 10, "name": f"Club Norte {fixture_id}"},
            "away": {"id": 20, "name": f"Club Sur {fixture_id}"},
        },
        "goals": {"home": 0, "away": 0},
    }


def seed_fixtures(path, fixture_ids, *, status="2H"):
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.row_factory = sqlite3.Row
        for fixture_id in fixture_ids:
            assert tracker._upsert_fixture(conn, fixture_payload(fixture_id, status=status)) == 1
        return {
            str(row["external_id"]): dict(row)
            for row in conn.execute("SELECT * FROM matches")
        }


def provider_statistics(fixture_id):
    home_possession = 50 + int(fixture_id) % 10
    return [
        {
            "team": {"id": 10, "name": f"Club Norte {fixture_id}"},
            "statistics": [
                {"type": "Shots on Goal", "value": 0},
                {"type": "Total Shots", "value": 2},
                {"type": "Ball Possession", "value": f"{home_possession}%"},
                {"type": "Corner Kicks", "value": None},
                {"type": "expected_goals", "value": None},
            ],
        },
        {
            "team": {"id": 20, "name": f"Club Sur {fixture_id}"},
            "statistics": [
                {"type": "Shots on Goal", "value": 0},
                {"type": "Total Shots", "value": 1},
                {"type": "Ball Possession", "value": f"{100 - home_possession}%"},
                {"type": "Corner Kicks", "value": 0},
                {"type": "expected_goals", "value": None},
            ],
        },
    ]


def mock_batch_provider(monkeypatch, *, response_kind="available"):
    calls = []

    def api_get(path, params=None, timeout=18):
        assert path == "fixtures", "The normal statistics lane must use the bounded batch endpoint"
        ids = str((params or {}).get("ids") or "").split("-")
        assert ids and all(value.isdigit() for value in ids)
        calls.append(ids)
        if response_kind == "restricted":
            return {
                "ok": False,
                "http_status": 403,
                "response": [],
                "errors": {"token": "Invalid API key: secret-provider-canary"},
            }
        return {
            "ok": True,
            "http_status": 200,
            "quota": {"daily_remaining": 100, "daily_limit": 120},
            # The provider does not guarantee the order of fixtures in a batch.
            "response": [
                {
                    "fixture": {"id": int(fixture_id)},
                    "statistics": provider_statistics(fixture_id) if response_kind == "available" else [],
                }
                for fixture_id in reversed(ids)
            ],
        }

    monkeypatch.setattr(statistics, "_api_get", api_get)
    return calls


def isolate_other_sports_stages(app_module, monkeypatch):
    deep_calls = []
    monkeypatch.setattr(app_module, "sports_sync_window_state", lambda: {"live_refresh_required": True})
    monkeypatch.setattr(app_module, "sync_api_football_match_window", lambda *_a, **_k: {
        "ok": True, "status": "cache", "fixtures_count": 0, "external_calls": 0,
    })
    monkeypatch.setattr(app_module, "sync_api_football_live_tracker", lambda *_a, **_k: {
        "ok": True, "status": "cache", "fixtures_count": 0, "external_calls": 0,
    })
    monkeypatch.setattr(app_module, "_api_football_deep_enrichment_candidates", lambda limit=1: ["99001"])

    def deep_not_due(*_args, **_kwargs):
        deep_calls.append(True)
        return {"ok": True, "status": "SKIPPED_NOT_DUE", "external_calls": 0}

    monkeypatch.setattr(app_module, "run_api_exploitation_if_due", deep_not_due)
    monkeypatch.setattr(app_module, "run_pick_grading", lambda *_a, **_k: {"ok": True, "picks_checked": 0})
    monkeypatch.setattr(app_module, "invalidate_v934_realtime_cache", lambda *_a, **_k: None)
    monkeypatch.setattr(app_module, "automation_safe_set", lambda *_a, **_k: None)
    return deep_calls


def database_content(path):
    with closing(sqlite3.connect(path)) as conn:
        return "\n".join(conn.iterdump())


def test_sports_tick_refreshes_and_rotates_statistics_while_deep_enrichment_is_not_due(
    statistics_db, app_module, monkeypatch,
):
    matches = seed_fixtures(statistics_db, [99001, 99002, 99003])
    calls = mock_batch_provider(monkeypatch)
    deep_calls = isolate_other_sports_stages(app_module, monkeypatch)
    monkeypatch.setenv("API_FOOTBALL_STATISTICS_BATCH_SIZE", "2")

    first = app_module.run_sports_sync_cycle(include_odds=False)
    second = app_module.run_sports_sync_cycle(include_odds=False)
    third = app_module.run_sports_sync_cycle(force=True, include_odds=False)

    assert first["deep_status"] == second["deep_status"] == third["deep_status"] == "SKIPPED_NOT_DUE"
    assert len(deep_calls) == 3
    assert len(calls) == 2
    assert len(calls[0]) == 2 and len(calls[1]) == 1
    assert set(calls[0]).isdisjoint(calls[1])
    assert set(calls[0] + calls[1]) == set(matches)
    assert first["statistics"]["external_calls"] == first["external_calls"] == 1
    assert second["statistics"]["external_calls"] == second["external_calls"] == 1
    assert third["statistics"]["external_calls"] == third["external_calls"] == 0
    assert api_usage_snapshot(statistics_db)["used_estimated"]["api_football"] == 2
    with app_module.app.test_request_context():
        for fixture_id, match in matches.items():
            cache = app_module._cached_match_statistics(match)
            assert cache["available"], fixture_id
            possession = next(item for item in cache["items"] if item["label"] == "Ball Possession")
            assert possession["home"] == f"{50 + int(fixture_id) % 10}%"


@pytest.mark.parametrize("status", ["2H", "FT"])
def test_persisted_statistics_reach_full_match_page_with_zero_and_missing_values(
    statistics_db, app_module, client, monkeypatch, status,
):
    match = seed_fixtures(statistics_db, [99001], status=status)["99001"]
    calls = mock_batch_provider(monkeypatch)
    result = statistics.refresh_api_football_statistics_if_due(statistics_db)
    assert result["external_calls"] == 1
    with app_module.app.test_request_context():
        cached = app_module._cached_match_statistics(match)
        live = tracker.live_tracker_for_match(statistics_db, match["id"])
        context = build_match_context({"match": match, "cached_statistics": cached}, live_context=live)

    assert cached["available"] is True
    assert live["stat_cards"]
    items = {item["label"]: item for item in context["statistics"]["items"]}
    assert context["statistics"]["available"] is True
    assert items["Tiros a puerta"]["home"] == items["Tiros a puerta"]["away"] == "0"
    assert items["Córners"]["home"] == "No disponible"
    assert items["Córners"]["away"] == "0"
    assert "xG" not in items and "expected_goals" not in items
    with closing(sqlite3.connect(statistics_db)) as conn:
        observed = conn.execute("SELECT last_synced_at FROM matches WHERE id=?", (match["id"],)).fetchone()[0]
    assert observed == match["last_synced_at"], "Statistics must not advance the fixture observation clock"

    before = database_content(statistics_db)
    response = client.get(f"/match/{match['id']}?refresh=1")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'href="#match-section-stats"' in html
    assert html.count('data-match-component="StatsPanel"') == 1
    assert "Tiros a puerta" in html and "Córners" in html
    assert html.count('role="cell">0</span>') >= 3
    api_response = client.get(f"/api/matches/{match['id']}/statistics")
    assert api_response.status_code == 200
    api = api_response.get_json()
    assert "statistics" in api, "Existing consumers retain the original response field"
    assert api["statistics_context"]["available"] is True
    api_items = {item["label"]: item for item in api["statistics_context"]["items"]}
    assert api_items["Tiros a puerta"]["home"] == "0"
    assert api_items["Córners"]["home"] == "No disponible"
    assert len(calls) == 1, "GET refresh must read the committed cache, not contact the provider"
    assert database_content(statistics_db) == before


@pytest.mark.parametrize("response_kind", ["empty", "restricted"])
def test_missing_statistics_remain_visible_and_get_never_retries_the_provider(
    statistics_db, app_module, client, monkeypatch, response_kind,
):
    match = seed_fixtures(statistics_db, [99001])["99001"]
    calls = mock_batch_provider(monkeypatch, response_kind=response_kind)
    statistics.refresh_api_football_statistics_if_due(statistics_db)
    state = statistics.statistics_refresh_state_for_match(statistics_db, match)
    if response_kind == "empty":
        assert state["status"] == "NO_DATA"
    else:
        assert state["status"].startswith("PROVIDER_FAILURE_")
        assert state["failure_category"]
    assert state["last_attempt_at"] and state["next_due_at"]
    assert "secret-provider-canary" not in json.dumps(state)

    before = database_content(statistics_db)
    response = client.get(f"/match/{match['id']}?refresh=1")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'href="#match-section-stats"' in html, "The statistics section must remain discoverable when no data is available"
    assert html.count('data-match-component="StatsPanel"') == 1
    api_response = client.get(f"/api/matches/{match['id']}/statistics")
    assert api_response.status_code == 200
    context = api_response.get_json()["statistics_context"]
    assert context["available"] is False
    assert context["refresh"]["status"] == ("NO_DATA" if response_kind == "empty" else "PROVIDER_FAILURE")
    assert context["message"] and context["message"] in html
    assert "secret-provider-canary" not in html
    assert "synthetic-statistics-key" not in html
    assert len(calls) == 1
    assert database_content(statistics_db) == before


def test_unauthorized_sports_requests_cannot_execute_statistics_refresh(
    statistics_db, app_module, client, monkeypatch,
):
    seed_fixtures(statistics_db, [99001])
    monkeypatch.setenv("AUTOMATION_SECRET", "synthetic-cron-secret")
    attempted = []

    def forbidden(*_args, **_kwargs):
        attempted.append(True)
        pytest.fail("Unauthorized requests cannot execute the sports or statistics job")

    monkeypatch.setattr(app_module, "bounded_sports_sync", forbidden)
    monkeypatch.setattr(app_module, "refresh_api_football_statistics_if_due", forbidden)
    assert client.get("/api/automation/sports/sync").status_code == 405
    assert client.post("/api/automation/sports/sync", json={}).status_code == 403
    assert client.post("/api/automation/sports/sync?secret=synthetic-cron-secret", json={}).status_code == 403
    assert client.post("/api/automation/sports/sync", json={}, headers={
        "X-Automation-Secret": "incorrect", "X-CSRF-Token": "browser-token",
    }).status_code == 403
    assert attempted == []


def test_provider_id_collision_does_not_attach_another_fixtures_statistics(
    statistics_db, app_module, monkeypatch,
):
    match = seed_fixtures(statistics_db, [99001])["99001"]
    mock_batch_provider(monkeypatch)
    statistics.refresh_api_football_statistics_if_due(statistics_db)
    unrelated = {
        **match,
        "id": "sportsdb-99001",
        "source": "TheSportsDB API",
        # Provider IDs and even team names can coincide without a fixture link.
        "external_id": "99001",
    }
    with app_module.app.test_request_context():
        assert app_module._cached_match_statistics(match)["available"] is True
        assert app_module._cached_match_statistics(unrelated)["available"] is False


def test_explicit_internal_provider_link_preserves_statistics_for_canonical_match(
    statistics_db, app_module, monkeypatch,
):
    from engines import api_exploitation_engine as exploitation

    match = seed_fixtures(statistics_db, [99001])["99001"]
    mock_batch_provider(monkeypatch)
    statistics.refresh_api_football_statistics_if_due(statistics_db)
    canonical = {**match, "id": "canonical-match-1", "source": "TheSportsDB API", "external_id": "777777"}
    exploitation.ensure_api_exploitation_schema(statistics_db)
    with closing(sqlite3.connect(statistics_db)) as conn, conn:
        exploitation._index_fixture(conn, {
            "external_id": "99001",
            "internal_match_id": canonical["id"],
            "home_team_id": "10",
            "away_team_id": "20",
            "home_team": canonical["home_team"],
            "away_team": canonical["away_team"],
        })
    with app_module.app.test_request_context():
        cached = app_module._cached_match_statistics(canonical)
    assert cached["available"] is True
    assert cached["fixture_id"] == "99001"


def test_a_new_scoreboard_observation_does_not_refresh_the_statistics_clock(
    statistics_db, app_module, client, monkeypatch,
):
    now = datetime.now(timezone.utc)
    earlier = now - timedelta(minutes=10)
    monkeypatch.setattr(statistics, "_now", lambda: earlier)
    monkeypatch.setattr(tracker, "_now_iso", lambda: earlier.isoformat())
    match = seed_fixtures(statistics_db, [99001])["99001"]
    calls = mock_batch_provider(monkeypatch)
    statistics.refresh_api_football_statistics_if_due(statistics_db)

    # A later regular live tick observes the minute/score but carries no new stats.
    monkeypatch.setattr(statistics, "_now", lambda: now)
    monkeypatch.setattr(tracker, "_now_iso", lambda: now.isoformat())
    payload = json.loads(match["raw_json"])
    payload["fixture"]["status"]["elapsed"] = 71
    with closing(sqlite3.connect(statistics_db)) as conn, conn:
        conn.row_factory = sqlite3.Row
        tracker._upsert_fixture(conn, payload)
        latest_match = dict(conn.execute("SELECT * FROM matches WHERE id=?", (match["id"],)).fetchone())
    with app_module.app.test_request_context():
        cached = app_module._cached_match_statistics(latest_match)
        refresh = statistics.statistics_refresh_state_for_match(statistics_db, latest_match)
        live = tracker.live_tracker_for_match(statistics_db, latest_match["id"])
        context = build_match_context({
            "match": latest_match,
            "cached_statistics": cached,
            "statistics_refresh": refresh,
        }, live_context=live, evaluation_time=now)

    assert refresh["status"] == "STALE"
    assert live["updated_at"] != cached["updated_at"]
    assert context["statistics"]["available"] is True
    assert context["statistics"]["snapshot_kind"] == "persisted"
    assert context["statistics"]["updated_at"] == cached["updated_at"]
    assert context["statistics"]["refresh"]["status"] == "STALE"
    api = client.get(f"/api/matches/{match['id']}/statistics").get_json()
    assert api["statistics_context"]["updated_at"] == cached["updated_at"]
    assert api["statistics_context"]["refresh"]["status"] == "STALE"
    assert len(calls) == 1


def test_later_empty_deep_snapshot_does_not_hide_committed_statistics(
    statistics_db, app_module, client, monkeypatch,
):
    from engines import api_exploitation_engine as exploitation

    now = datetime.now(timezone.utc)
    earlier = now - timedelta(minutes=10)
    monkeypatch.setattr(statistics, "_now", lambda: earlier)
    monkeypatch.setattr(tracker, "_now_iso", lambda: earlier.isoformat())
    match = seed_fixtures(statistics_db, [99001])["99001"]
    batch_calls = mock_batch_provider(monkeypatch)
    statistics.refresh_api_football_statistics_if_due(statistics_db)
    with app_module.app.test_request_context():
        previous = app_module._cached_match_statistics(match)
    assert previous["available"] is True

    # The older deep lane can append a newer snapshot containing only nulls.
    empty_blocks = provider_statistics("99001")
    for block in empty_blocks:
        for item in block["statistics"]:
            item["value"] = None
    deep_calls = []

    def deep_api_get(path, params=None):
        assert path == "fixtures/statistics" and params == {"fixture": "99001"}
        deep_calls.append(True)
        return {"ok": True, "response": empty_blocks}

    monkeypatch.setattr(exploitation, "_api_get", deep_api_get)
    monkeypatch.setattr(exploitation, "_now_iso", lambda: now.isoformat())
    exploitation.ensure_api_exploitation_schema(statistics_db)
    with closing(sqlite3.connect(statistics_db)) as conn, conn:
        inserted, error, _trace = exploitation._sync_statistics(conn, "99001")
        newest_values = conn.execute(
            "SELECT stat_value FROM api_football_match_stats_history WHERE captured_at=?",
            (now.isoformat(),),
        ).fetchall()
    assert error is None and inserted > 0
    assert newest_values and all(value[0] == "" for value in newest_values)

    monkeypatch.setattr(statistics, "_now", lambda: now)
    with app_module.app.test_request_context():
        cached = app_module._cached_match_statistics(match)
        context = build_match_context({
            "match": match,
            "cached_statistics": cached,
            "statistics_refresh": statistics.statistics_refresh_state_for_match(statistics_db, match),
        }, live_context=tracker.live_tracker_for_match(statistics_db, match["id"]), evaluation_time=now)
    assert cached["available"] is True
    assert cached["items"] == previous["items"]
    assert cached["updated_at"] == previous["updated_at"]
    assert context["statistics"]["available"] is True
    assert context["statistics"]["updated_at"] == previous["updated_at"]

    before = database_content(statistics_db)
    response = client.get(f"/match/{match['id']}?refresh=1")
    assert response.status_code == 200
    assert "Tiros a puerta" in response.get_data(as_text=True)
    response = client.get(f"/api/matches/{match['id']}/statistics")
    assert response.status_code == 200
    public_stats = response.get_json()["statistics_context"]
    assert public_stats["available"] is True
    assert public_stats["updated_at"] == previous["updated_at"]
    assert len(batch_calls) == len(deep_calls) == 1
    assert database_content(statistics_db) == before


def test_statistics_snapshot_order_uses_real_time_across_utc_and_madrid_offsets(
    statistics_db, app_module, client, monkeypatch,
):
    from engines import api_exploitation_engine as exploitation

    now = datetime.now(timezone.utc)
    older = (now - timedelta(hours=1)).astimezone(timezone(timedelta(hours=2)))
    match = seed_fixtures(statistics_db, [99001])["99001"]
    old_blocks = provider_statistics("99001")
    for block in old_blocks:
        next(item for item in block["statistics"] if item["type"] == "Shots on Goal")["value"] = 9
    deep_calls = []

    def deep_api_get(path, params=None):
        assert path == "fixtures/statistics" and params == {"fixture": "99001"}
        deep_calls.append(True)
        return {"ok": True, "response": old_blocks}

    monkeypatch.setattr(exploitation, "_api_get", deep_api_get)
    monkeypatch.setattr(exploitation, "_now_iso", lambda: older.isoformat())
    exploitation.ensure_api_exploitation_schema(statistics_db)
    with closing(sqlite3.connect(statistics_db)) as conn, conn:
        inserted, error, _trace = exploitation._sync_statistics(conn, "99001")
    assert error is None and inserted > 0

    monkeypatch.setattr(statistics, "_now", lambda: now)
    batch_calls = mock_batch_provider(monkeypatch)
    statistics.refresh_api_football_statistics_if_due(statistics_db)
    with app_module.app.test_request_context():
        cached = app_module._cached_match_statistics(match)
        context = build_match_context({
            "match": match,
            "cached_statistics": cached,
            "statistics_refresh": statistics.statistics_refresh_state_for_match(statistics_db, match),
        }, live_context=tracker.live_tracker_for_match(statistics_db, match["id"]), evaluation_time=now)

    assert datetime.fromisoformat(cached["updated_at"]) == now
    assert older.isoformat() > cached["updated_at"], "Lexical MAX would choose the older Madrid snapshot"
    cached_shots = next(item for item in cached["items"] if item["label"] == "Shots on Goal")
    assert cached_shots["home"] == cached_shots["away"] == "0"
    assert context["statistics"]["updated_at"] == cached["updated_at"]
    response = client.get(f"/api/matches/{match['id']}/statistics")
    assert response.status_code == 200
    public_stats = response.get_json()["statistics_context"]
    public_shots = next(item for item in public_stats["items"] if item["label"] == "Tiros a puerta")
    assert public_shots["home"] == public_shots["away"] == "0"
    assert public_stats["updated_at"] == cached["updated_at"]
    assert len(batch_calls) == len(deep_calls) == 1


def test_upcoming_match_explains_that_statistics_start_after_kickoff(
    statistics_db, app_module, client, monkeypatch,
):
    now = datetime.now(timezone.utc)
    payload = fixture_payload("99001", status="NS")
    payload["fixture"]["date"] = (now + timedelta(hours=2)).isoformat()
    payload["fixture"]["status"] = {"short": "NS", "long": "Not Started", "elapsed": None}
    payload["goals"] = {"home": None, "away": None}
    with closing(sqlite3.connect(statistics_db)) as conn, conn:
        conn.row_factory = sqlite3.Row
        tracker._upsert_fixture(conn, payload)
        match = dict(conn.execute("SELECT * FROM matches WHERE external_id='99001'").fetchone())
    calls = mock_batch_provider(monkeypatch)
    context = build_match_context({"match": match}, evaluation_time=now)
    assert context["lifecycle"]["key"] == "UPCOMING"
    assert context["statistics"]["available"] is False
    assert "después del inicio" in context["statistics"]["message"]

    page = client.get(f"/match/{match['id']}")
    response = client.get(f"/api/matches/{match['id']}/statistics")
    assert page.status_code == response.status_code == 200
    assert response.get_json()["statistics_context"]["message"] == context["statistics"]["message"]
    assert context["statistics"]["message"] in page.get_data(as_text=True)
    assert calls == []


def test_statistics_evidence_survives_compact_runner_and_read_only_provider_health(
    app_module, monkeypatch,
):
    from tools.render_cron_master_tick import sanitized_sports_pipeline

    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stage = {
        "ok": False, "status": "PARTIAL", "configured": True, "enabled": True,
        "transport": "batch", "external_calls": 1, "refreshed_fixtures": 1,
        "fixtures_count": 1, "stats_inserted": 8, "no_data_count": 1,
        "failed_count": 1, "eligible_count": 3, "due_count": 3,
        "reason_code": "LOCAL_APPLICATION_BUDGET_EXHAUSTED",
        "budget_scope": "LOCAL_APPLICATION_GUARD", "budget_limit": 600,
        "budget_used": 600, "budget_remaining": 0, "required_calls": 1,
        "provider_quota_consulted": False,
        "data_contributed": True, "provider_observed_at": observed,
        "provider_observation_current": True,
        "failure_categories": ["PROVIDER_RESPONSE"],
        "errors": ["opaque provider detail: hidden-provider-canary"],
    }
    run = {
        "ok": True, "status": "PARTIAL", "external_calls": 1,
        "started_at": observed, "finished_at": observed,
        "fixtures": {"ok": True, "status": "cache", "external_calls": 0},
        "statistics": stage,
    }
    diagnostics = app_module._build_sports_pipeline_diagnostics(run, {})
    compact = app_module._cron_compact_payload(
        "sports_sync", {**run, "sports_pipeline": diagnostics}, observed, observed,
    )
    # Even unrecognized provider fields appended to the response cannot escape
    # the stateless runner's explicit projection.
    compact["sports_pipeline"]["current_sync"]["statistics_refresh"]["error"] = "hidden-provider-canary"
    runner_pipeline = sanitized_sports_pipeline(compact, "synthetic-cron-secret")
    expected_counts = {
        "external_calls": 1, "refreshed_fixtures": 1, "fixtures_count": 1,
        "stats_inserted": 8, "no_data_count": 1, "failed_count": 1,
        "eligible_count": 3, "due_count": 3,
    }
    for pipeline in (diagnostics, compact["sports_pipeline"], runner_pipeline):
        stats = pipeline["current_sync"]["statistics_refresh"]
        assert {key: stats[key] for key in expected_counts} == expected_counts
        assert stats["transport"] == "batch"
        assert stats["failure_categories"] == ["PROVIDER_RESPONSE"]
        assert stats["provider_observation_current"] is True
        assert stats["provider_observed_at"] == observed
        assert stats["budget_scope"] == "LOCAL_APPLICATION_GUARD"
        assert stats["budget_limit"] == stats["budget_used"] == 600
        assert stats["budget_remaining"] == 0 and stats["required_calls"] == 1
        assert stats["provider_quota_consulted"] is False
    assert "hidden-provider-canary" not in json.dumps(diagnostics)
    assert "hidden-provider-canary" not in json.dumps(runner_pipeline)

    persisted = {"compact": {"sports_pipeline": runner_pipeline}}
    monkeypatch.setattr(app_module, "automation_get_bounded", lambda key, *_a, **_k: (
        persisted if key == "telegram_tick_last_detail" else {}
    ))
    monkeypatch.setattr(app_module, "env_present", lambda name: name == "API_FOOTBALL_KEY")
    health = app_module.v945_provider_health_snapshot()
    provider = next(item for item in health["providers"] if item["key"] == "api_football")
    observation = next(item for item in provider["observations"] if item["lane_label"] == "Estadísticas")
    assert observation["failure_category"] == "PROVIDER_RESPONSE"
    assert observation["observation_scope"] == "CURRENT_CYCLE"
    assert provider["statistics_refresh"]["stats_inserted"] == 8
    assert provider["statistics_refresh"]["failed_count"] == 1
    assert provider["statistics_refresh"]["budget_limit"] == 600
    assert health["provider_calls_during_render"] == 0
    assert "hidden-provider-canary" not in json.dumps(health)


@pytest.mark.parametrize("category,stage_status,error,technical_reason", [
    ("FREE_PLAN_SEASON_RESTRICTED", "PROVIDER_FAILURE", "This season is unavailable for the plan", None),
    ("AUTH_OR_ACCESS", "PARTIAL", "Invalid API key", "AUTH_OR_ACCESS"),
    ("NETWORK_OR_TIMEOUT", "PROVIDER_FAILURE", "Connection timed out", "NETWORK_OR_TIMEOUT"),
])
def test_bounded_sports_distinguishes_statistics_coverage_limits_from_technical_failures(
    app_module, monkeypatch, category, stage_status, error, technical_reason,
):
    stage = {
        "ok": False, "status": stage_status, "configured": True, "enabled": True,
        "external_calls": 1, "failure_category": category,
        "failure_categories": [category], "errors": [error],
    }
    monkeypatch.setattr(app_module, "run_sports_sync_cycle", lambda **_k: {
        "ok": True, "status": "PARTIAL", "external_calls": 1,
        "fixtures": {"ok": True, "status": "OK"}, "statistics": stage,
        "errors": [f"statistics_{stage_status}"],
    })
    monkeypatch.setattr(app_module, "api_exploitation_summary", lambda *_a, **_k: {})
    monkeypatch.setattr(app_module, "_sports_entity_freshness_snapshot", lambda **_k: {})

    result = app_module.bounded_sports_sync()
    expected_errors = [f"statistics_{technical_reason}"] if technical_reason else []
    assert result["technical_errors"] == expected_errors
    assert result["ok"] is (technical_reason is None)
    assert result["status"] == "PARTIAL"
    assert result["controlled_deferrals"] == ([] if technical_reason else ["PROVIDER_PLAN_LIMIT"])
    compact = app_module._cron_compact_payload("sports_sync", result, "", "")
    assert compact["errors_count"] == len(expected_errors)
    assert compact["sports_pipeline"]["current_sync"]["statistics_refresh"]["failure_category"] == category
