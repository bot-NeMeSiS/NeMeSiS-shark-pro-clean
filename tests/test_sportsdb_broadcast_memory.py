from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engines import sports_history_engine as history
from engines.sportsdb_broadcast_engine import (
    normalize_event_tv,
    sync_upcoming_broadcasts,
)

ROOT = Path(__file__).resolve().parents[1]


def _seed_match(db_path, kickoff):
    with sqlite3.connect(db_path) as conn:
        history.ensure_schema(conn)
        match_id = history.ingest_match(
            conn,
            {
                "provider": "thesportsdb",
                "external_id": "900001",
                "league_id": "4335",
                "league_name": "Spanish La Liga",
                "season": "2026-2027",
                "home_team_id": "133602",
                "away_team_id": "133739",
                "home_team": "Real Madrid",
                "away_team": "Athletic Club",
                "kickoff_iso": kickoff.isoformat(),
                "status": "not started",
            },
        )
        conn.commit()
    return match_id


def test_tv_payload_is_normalized_deduped_and_spain_first():
    payload = {
        "tvevents": [
            {
                "id": "2",
                "idEvent": "900001",
                "idChannel": "44",
                "strCountry": "United Kingdom",
                "strChannel": "Channel B",
            },
            {
                "id": "1",
                "idEvent": "900001",
                "idChannel": "22",
                "strCountry": "Spain",
                "strChannel": "Canal España",
            },
            {
                "id": "duplicate",
                "idEvent": "900001",
                "idChannel": "22",
                "strCountry": "Spain",
                "strChannel": "Canal España",
            },
            {
                "idEvent": "other",
                "idChannel": "99",
                "strCountry": "Spain",
                "strChannel": "Otro partido",
            },
        ]
    }
    rows = normalize_event_tv(payload, "900001")
    assert [row["channel"] for row in rows] == ["Canal España", "Channel B"]
    assert rows[0]["country"] == "Spain"
    assert all(row["source"] == "thesportsdb" for row in rows)


def test_automatic_tv_sync_persists_snapshot_and_reuses_cache(tmp_path):
    db_path = tmp_path / "sports.sqlite"
    observed = datetime.now(timezone.utc).replace(microsecond=0)
    match_id = _seed_match(str(db_path), observed + timedelta(hours=24))
    calls = []

    def fetcher(event_id, key):
        calls.append((event_id, key))
        return {
            "tvevents": [
                {
                    "id": "tv-1",
                    "idEvent": event_id,
                    "idChannel": "2997",
                    "strCountry": "Spain",
                    "strChannel": "Canal confirmado",
                    "strTime": "21:00:00",
                }
            ]
        }

    first = sync_upcoming_broadcasts(
        str(db_path),
        env={"THESPORTSDB_API_KEY": "premium-test-key"},
        now=observed,
        fetcher=fetcher,
    )
    assert first["ok"] is True
    assert first["external_calls"] == 1
    assert first["updated"] == 1
    assert calls == [("900001", "premium-test-key")]

    details = history.cached_match_details(str(db_path), match_id)
    rows = details["broadcasts"]
    assert len(rows) == 1
    payload = rows[0]["payload"]
    assert payload["available"] is True
    assert payload["channels"][0]["channel"] == "Canal confirmado"
    assert payload["no_invented_availability"] is True

    second = sync_upcoming_broadcasts(
        str(db_path),
        env={"THESPORTSDB_API_KEY": "premium-test-key"},
        now=observed + timedelta(minutes=5),
        fetcher=fetcher,
    )
    assert second["ok"] is True
    assert second["external_calls"] == 0
    assert second["cached"] == 1
    assert len(calls) == 1


def test_empty_provider_schedule_is_persisted_without_inventing_channel(tmp_path):
    db_path = tmp_path / "sports.sqlite"
    observed = datetime.now(timezone.utc).replace(microsecond=0)
    match_id = _seed_match(str(db_path), observed + timedelta(hours=12))

    result = sync_upcoming_broadcasts(
        str(db_path),
        env={"THESPORTSDB_KEY": "premium-test-key"},
        now=observed,
        fetcher=lambda event_id, key: {"tvevents": []},
    )
    assert result["ok"] is True
    details = history.cached_match_details(str(db_path), match_id)
    payload = details["broadcasts"][0]["payload"]
    assert payload["available"] is False
    assert payload["channels"] == []
    assert payload["no_invented_availability"] is True


def test_missing_sportsdb_key_fails_closed_without_provider_call(tmp_path):
    db_path = tmp_path / "sports.sqlite"
    observed = datetime.now(timezone.utc).replace(microsecond=0)
    _seed_match(str(db_path), observed + timedelta(hours=12))
    touched = []

    result = sync_upcoming_broadcasts(
        str(db_path),
        env={},
        now=observed,
        fetcher=lambda event_id, key: touched.append(event_id),
    )
    assert result["ok"] is False
    assert result["reason"] == "SPORTSDB_KEY_MISSING"
    assert result["external_calls"] == 0
    assert touched == []


def test_broadcast_refresh_is_cron_owned_and_product_read_is_local_only():
    automation = (ROOT / "engines" / "daily_automation_engine.py").read_text(encoding="utf-8")
    engine = (ROOT / "engines" / "sportsdb_broadcast_engine.py").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "match_detail.html").read_text(encoding="utf-8")

    assert '"sports_broadcasts_sync": "07:20"' in automation
    assert '"sports_broadcasts_sync": ("thesportsdb", 6)' in automation
    assert '"sports_broadcasts_sync": lambda: sync_upcoming_broadcasts(DB_PATH, env=os.environ)' in (ROOT / 'app.py').read_text(encoding='utf-8')
    assert "urllib.request.urlopen" in engine
    assert "data-sportsdb-broadcasts" in template
    assert "urlopen" not in template
    assert "La programación de este partido todavía no está disponible." in template
    assert "consulta automática guardada en memoria local" not in template


def test_upcoming_tv_not_starved_by_large_archived_history(tmp_path):
    from engines.sportsdb_broadcast_engine import _candidates
    db = tmp_path / 'history.sqlite'
    now = datetime.now(timezone.utc)
    target = _seed_match(db, now + timedelta(hours=2))
    with sqlite3.connect(db) as conn:
        for n in range(300):
            identity = 'old-' + str(n)
            conn.execute('INSERT INTO sports_history_matches SELECT ?,competition,season,home,away,?,status,home_score,away_score,NULL,updated_at FROM sports_history_matches WHERE id=?', (identity, (now-timedelta(days=400)).isoformat(), target))
            conn.execute("INSERT INTO sports_history_ids VALUES('match','thesportsdb',?,?)", (str(800000+n), identity))
        rows = _candidates(conn, now=now, horizon_hours=72, limit=6)
    assert [r['match_id'] for r in rows] == [target]


def test_future_snapshot_is_not_fresh_and_failed_attempt_is_counted(tmp_path):
    from engines.sportsdb_broadcast_engine import _fresh
    now = datetime.now(timezone.utc)
    assert not _fresh((now+timedelta(hours=1)).isoformat(), now, 12)
    db = tmp_path / 'history.sqlite'
    _seed_match(db, now+timedelta(hours=1))
    def failure(*args):
        raise RuntimeError('SPORTSDB_NETWORK_ERROR')
    result = sync_upcoming_broadcasts(str(db), env={'THESPORTSDB_KEY': 'test'}, now=now, fetcher=failure)
    assert result['external_calls'] == 1
    assert not result['ok']
    assert result['updated'] == 0


def test_time_budget_defers_without_provider_call(tmp_path, monkeypatch):
    from engines import cron_request_budget
    db = tmp_path / 'history.sqlite'
    now = datetime.now(timezone.utc)
    _seed_match(db, now+timedelta(hours=1))
    monkeypatch.setattr(cron_request_budget, 'exhausted', lambda: True)
    result = sync_upcoming_broadcasts(str(db), env={'THESPORTSDB_KEY': 'test'}, now=now, fetcher=lambda *args: (_ for _ in ()).throw(AssertionError('must not call')))
    assert result['external_calls'] == 0
    assert result['controlled_deferral'] == 'TIME_BUDGET'
    assert result['result'] == 'PARTIAL'


def test_provider_diagnostic_never_returns_arbitrary_exception_text(tmp_path):
    db = tmp_path / 'history.sqlite'
    now = datetime.now(timezone.utc)
    _seed_match(db, now+timedelta(hours=1))
    def failure(*args):
        raise RuntimeError('SPORTSDB_HTTP_private123')
    result = sync_upcoming_broadcasts(str(db), env={'THESPORTSDB_KEY': 'test'}, now=now, fetcher=failure)
    assert result['errors'][0]['code'] == 'SPORTSDB_BROADCAST_ERROR'
    assert 'private' not in str(result)
