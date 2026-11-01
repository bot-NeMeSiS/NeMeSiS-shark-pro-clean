"""The plain realtime emission must retain its own complete LIVE cohort."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
import sqlite3
from zoneinfo import ZoneInfo

import pytest

from engines import v934_realtime_sports_engine as realtime
from engines import v935_launch_trust_engine as trust


NOW = datetime(2026, 9, 22, 0, 10, tzinfo=ZoneInfo("Europe/Madrid"))


@pytest.fixture(autouse=True)
def separate_cache(monkeypatch):
    for name in ("_CACHE", "_CACHE_BUILD_LOCKS", "_CACHE_GENERATIONS"):
        monkeypatch.setattr(realtime, name, {})


def match(key="owned-night", **changes):
    kickoff = NOW - timedelta(minutes=40)
    row = {
        "id": key, "home_team": "Owned Home", "away_team": "Owned Away",
        "competition_name": "Owned League", "match_date": kickoff.date().isoformat(),
        "kickoff_time": kickoff.strftime("%H:%M"), "kickoff_iso": kickoff.isoformat(),
        "source": "TheSportsDB API", "status": "LIVE", "minute": "40",
        "home_score": 0, "away_score": 1, "last_synced_at": NOW.isoformat(),
    }
    return dict(row, **changes)


def test_snapshot_keeps_a_complete_fresh_overnight_live_with_its_own_fields():
    own = match()
    summary = {"valid_live_events": [own], "last_sync": NOW.isoformat()}
    before = deepcopy(summary)
    snapshot = realtime.build_realtime_snapshot(summary, NOW)
    assert snapshot["counts"]["live"] == len(snapshot["live"]) == 1
    frame = snapshot["live"][0]
    assert snapshot["matches"] == [frame]
    assert frame["id"] == own["id"] and frame["detail_url"] == "/match/" + own["id"]
    assert frame["match_date"] == own["match_date"] != NOW.date().isoformat()
    assert (frame["home_score"], frame["away_score"], frame["minute"]) == (0, 1, 40)
    assert frame["source"] == own["source"]
    assert frame["last_synced_at"] == frame["updated_at"] == own["last_synced_at"]
    assert frame["is_live"] is True and frame["is_stale"] is False
    assert frame["realtime_state"]["provider_observed_at"] == own["last_synced_at"]
    assert snapshot["poll_after_seconds"] == 45
    assert summary == before


@pytest.mark.parametrize("first_kind", ["invalid", "finished", "stale", "live"])
def test_appended_live_candidates_preserve_first_valid_record_and_never_borrow(first_kind):
    later = match(home_score=9, away_score=8)
    if first_kind == "invalid":
        first = match(source="")
    elif first_kind == "finished":
        first = match(status="FT", minute="", home_score=2, away_score=0)
    elif first_kind == "stale":
        first = match(last_synced_at=(NOW - timedelta(hours=3)).isoformat())
    else:
        first = match(home_score=1, away_score=0)
    summary = {"valid_matches_today": [first], "valid_live_events": [later]}
    before = deepcopy(summary)
    snapshot = realtime.build_realtime_snapshot(summary, NOW)
    if first_kind == "invalid":
        assert snapshot["live"][0]["home_score"] == 9
    elif first_kind == "finished":
        assert snapshot["live"] == [] and snapshot["finished"][0]["home_score"] == 2
    elif first_kind == "stale":
        assert snapshot["matches"] == snapshot["live"] == []
        assert snapshot["stale_live"][0]["last_synced_at"] == first["last_synced_at"]
    else:
        assert snapshot["live"][0]["home_score"] == 1
    assert snapshot["counts"]["live"] == len(snapshot["live"])
    assert snapshot["poll_after_seconds"] == (45 if snapshot["live"] else 180)
    assert summary == before


def test_four_overlapping_cohorts_evaluate_the_first_valid_observation_once(monkeypatch):
    own = match()
    source = {key: [own] for key in (
        "valid_matches_today", "valid_upcoming_matches", "finished_matches", "valid_live_events"
    )}
    original = realtime.normalize_match
    calls = []
    def observed(row, now):
        calls.append(row)
        return original(row, now)
    monkeypatch.setattr(realtime, "normalize_match", observed)
    snapshot = realtime.build_realtime_snapshot(source, NOW)
    assert calls == [own] and len(snapshot["live"]) == snapshot["counts"]["live"] == 1


@pytest.mark.parametrize("changes", [
    {"last_synced_at": "invalid"},
    {"provider_updated_at": "invalid", "last_synced_at": NOW.isoformat()},
    {"last_synced_at": (NOW - timedelta(hours=3)).isoformat()},
    {"last_synced_at": "", "updated_at": NOW.isoformat()},
    {"status": "FT", "minute": ""},
    {"status": "SUSP", "minute": ""},
    {"home_score": None},
])
def test_live_named_collection_does_not_grant_truth_or_a_new_clock(changes):
    own = match(**changes)
    # The existing today path is the independent legitimate normalization control.
    control = realtime.build_realtime_snapshot({"valid_matches_today": [own]}, NOW)
    actual = realtime.build_realtime_snapshot({"valid_live_events": [own]}, NOW)
    for key in ("matches", "live", "stale_live", "finished", "counts", "poll_after_seconds"):
        assert actual[key] == control[key]
    if changes.get("home_score", 0) is None:
        assert actual["live"][0]["home_score"] is None
        assert actual["live"][0]["away_score"] is None
    else:
        assert actual["live"] == []


def _summary(today, live):
    return {
        "valid_matches_today": today, "valid_upcoming_matches": [],
        "finished_matches": [], "valid_live_events": live,
        "valid_active_picks": [{"id": "not-normalized-advice", "match_id": "owned"}],
        "incomplete_matches": [{"id": "incomplete"}], "raw_matches_count": 99,
        "stale_live_excluded": 2, "last_sync": NOW.isoformat(),
        "metrics_generated_at_madrid": NOW.isoformat(),
        "sports_home": {"quality": {"last_sync": NOW.isoformat()}},
    }


@pytest.mark.parametrize("first_kind", ["invalid", "finished", "stale", "live"])
def test_context_metrics_and_count_use_the_same_published_live_members(
    app_module, monkeypatch, tmp_path, first_kind
):
    a = app_module
    monkeypatch.setattr(a, "DB_PATH", str(tmp_path / "OWNED_CACHE_KEY.sqlite"))
    monkeypatch.setattr(realtime, "_now", lambda now=None: now or NOW)
    monkeypatch.setattr(trust, "madrid_now", lambda now=None: now or NOW)
    later = match(home_score=9, away_score=8)
    changes = {"invalid": {"source": ""}, "finished": {"status": "FT", "minute": ""},
               "stale": {"last_synced_at": (NOW - timedelta(hours=3)).isoformat()}, "live": {}}
    summary = _summary([match(**changes[first_kind])], [later])
    before = deepcopy(summary)
    snapshot = a._v991_legacy_get_v934_realtime_context(summary)
    expected = 1 if first_kind in {"invalid", "live"} else 0
    assert snapshot["counts"]["live"] == len(snapshot["live"]) == expected
    assert snapshot["sports_metrics"]["live_confirmed"] == expected
    assert snapshot["poll_after_seconds"] == (45 if expected else 180)
    # Other metrics retain their documented source cohorts, not array lengths.
    assert snapshot["counts"]["synchronized"] == 99
    assert snapshot["counts"]["incomplete"] == 1
    assert snapshot["counts"]["stale_live"] == 2
    assert snapshot["counts"]["picks"] == 1 and snapshot["picks"] == []
    assert summary == before


def test_membership_fingerprint_changes_when_live_ids_change_at_the_same_total(
    app_module, monkeypatch, tmp_path
):
    a = app_module
    monkeypatch.setattr(a, "DB_PATH", str(tmp_path / "OWNED_MEMBER_KEY.sqlite"))
    clock = [NOW]
    monkeypatch.setattr(realtime, "_now", lambda now=None: now or clock[0])
    monkeypatch.setattr(trust, "madrid_now", lambda now=None: now or clock[0])
    first = match("owned-first")
    second = match("owned-second", last_synced_at=(NOW + timedelta(minutes=10)).isoformat())
    source = _summary([first, second], [first, second])
    before = deepcopy(source)
    early = a._v991_legacy_get_v934_realtime_context(source, force=True)
    clock[0] += timedelta(minutes=10)
    later = a._v991_legacy_get_v934_realtime_context(source, force=True)
    assert [row["id"] for row in early["live"]] == [first["id"]]
    assert [row["id"] for row in later["live"]] == [second["id"]]
    for snapshot in (early, later):
        assert snapshot["counts"]["live"] == snapshot["sports_metrics"]["live_confirmed"] == 1
    assert early["sports_metrics"]["snapshot_id"] != later["sports_metrics"]["snapshot_id"]
    assert source == before


def test_build_crossing_freshness_boundary_does_not_reclassify_its_emission(
    app_module, monkeypatch, tmp_path
):
    a = app_module
    monkeypatch.setattr(a, "DB_PATH", str(tmp_path / "OWNED_BUILD_CLOCK.sqlite"))
    clock = [NOW]
    monkeypatch.setattr(realtime, "_now", lambda now=None: now or clock[0])
    monkeypatch.setattr(trust, "madrid_now", lambda now=None: now or clock[0])
    own = match(last_synced_at=(NOW - timedelta(seconds=119)).isoformat())
    source = _summary([own], [own])
    frame_instant_metrics = a._v991_legacy_sports_metrics_contract(source)
    assert frame_instant_metrics["live_confirmed"] == 1
    original = a.build_v934_realtime_snapshot
    def finish_after_boundary(summary):
        result = original(summary)
        clock[0] += timedelta(seconds=2)
        return result
    monkeypatch.setattr(a, "build_v934_realtime_snapshot", finish_after_boundary)
    snapshot = a._v991_legacy_get_v934_realtime_context(source)
    assert snapshot["counts"]["live"] == len(snapshot["live"]) == 1
    assert snapshot["sports_metrics"]["live_confirmed"] == 1
    assert snapshot["sports_metrics"]["snapshot_id"] == frame_instant_metrics["snapshot_id"]
    assert snapshot["live"][0]["updated_at"] == own["last_synced_at"]
    assert snapshot["live"][0]["age_seconds"] == 119
    # A new, independent decision has crossed the existing 120-second boundary.
    assert a.canonical_match_status(own)["is_live"] is False
    later_metrics = a._v991_legacy_sports_metrics_contract(source)
    assert later_metrics["live_confirmed"] == 0
    assert later_metrics["snapshot_id"] != snapshot["sports_metrics"]["snapshot_id"]


def test_cached_frame_metrics_remain_together_without_renewing_provider_time(
    app_module, monkeypatch, tmp_path
):
    a = app_module
    monkeypatch.setattr(a, "DB_PATH", str(tmp_path / "OWNED_CACHE_CLOCK.sqlite"))
    clock, monotonic = [NOW], [100.0]
    monkeypatch.setattr(realtime, "_now", lambda now=None: now or clock[0])
    monkeypatch.setattr(trust, "madrid_now", lambda now=None: now or clock[0])
    monkeypatch.setattr(realtime.time, "monotonic", lambda: monotonic[0])
    own = match(last_synced_at=(NOW - timedelta(seconds=119)).isoformat())
    source = _summary([], [own])
    fresh = a._v991_legacy_get_v934_realtime_context(source)
    clock[0] += timedelta(seconds=2)
    monotonic[0] = 114.0
    hit = a._v991_legacy_get_v934_realtime_context(_summary([], []))
    assert hit["cache_state"] == "hit"
    assert hit["live"] == fresh["live"] and hit["sports_metrics"] == fresh["sports_metrics"]
    assert hit["generated_at_madrid"] == fresh["generated_at_madrid"]
    hit["live"][0]["id"] = "private-decoration"
    hit["sports_metrics"]["live_confirmed"] = 999
    later_hit = a._v991_legacy_get_v934_realtime_context(source)
    assert later_hit["live"][0]["id"] == own["id"]
    assert later_hit["sports_metrics"]["live_confirmed"] == later_hit["counts"]["live"] == 1
    monotonic[0] = 116.0
    original = a.build_v934_realtime_snapshot
    def fail(_summary):
        raise RuntimeError("owned builder unavailable")
    monkeypatch.setattr(a, "build_v934_realtime_snapshot", fail)
    fallback = a._v991_legacy_get_v934_realtime_context(source)
    assert fallback["cache_state"] == fallback["cache_status"] == "stale_fallback"
    assert fallback["live"] == fresh["live"] and fallback["sports_metrics"] == fresh["sports_metrics"]
    assert fallback["live"][0]["updated_at"] == own["last_synced_at"]
    assert next(iter(realtime._CACHE.values()))["expires_at"] == 115.0
    monkeypatch.setattr(a, "build_v934_realtime_snapshot", original)
    expired = a._v991_legacy_get_v934_realtime_context(source)
    assert expired["cache_state"] == "refreshed" and expired["live"] == []
    assert expired["sports_metrics"]["live_confirmed"] == expired["counts"]["live"] == 0


def _owned_database(a, path, count):
    a.seed_core()
    now = datetime.now(a.TZ)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    records = []
    for index in range(count):
        kickoff = midnight - timedelta(minutes=30) if index == 6 else midnight + (now - midnight) / 2
        native = 776001 + index
        item = {
            "id": "af-" + str(native), "external_id": str(native),
            "source": "api_football_live", "sport_key": "soccer", "competition_key": "laliga",
            "competition_id": "140", "competition_name": "LaLiga", "league_name": "LaLiga",
            "country": "Spain", "season": str(kickoff.year),
            "home_team": "Owned Night Home " + str(index), "away_team": "Owned Night Away " + str(index),
            "home_team_id": str(44001 + index * 2), "away_team_id": str(44002 + index * 2),
            "minute": 50, "home_score": 2, "away_score": 1, "status": "2H",
            "updated_at": now.isoformat(), "last_synced_at": now.isoformat(),
            "match_date": kickoff.date().isoformat(), "kickoff_iso": kickoff.isoformat(),
            "kickoff_time": kickoff.strftime("%H:%M"), "match_time": kickoff.strftime("%H:%M"),
        }
        item["raw_json"] = json.dumps({
            "fixture": {"id": native, "date": kickoff.isoformat(), "status": {"short": "2H", "elapsed": 50}},
            "league": {"id": 140, "name": "LaLiga", "country": "Spain", "season": kickoff.year},
            "teams": {"home": {"id": int(item["home_team_id"]), "name": item["home_team"]},
                      "away": {"id": int(item["away_team_id"]), "name": item["away_team"]}},
            "goals": {"home": 2, "away": 1},
        })
        records.append(item)
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM matches")
        conn.execute("DELETE FROM picks")
        conn.execute("DELETE FROM competitions WHERE key='laliga'")
        conn.execute("INSERT INTO competitions(key,name,country,source,external_id) VALUES(?,?,?,?,?)",
                     ("laliga", "LaLiga", "Spain", "API_FOOTBALL", "140"))
        columns = {row[1] for row in conn.execute("PRAGMA table_info(matches)")}
        for item in records:
            values = {key: value for key, value in item.items() if key in columns}
            conn.execute("INSERT INTO matches(" + ",".join(values) + ") VALUES(" +
                         ",".join("?" for _ in values) + ")", tuple(values.values()))
        before = conn.execute("SELECT * FROM matches ORDER BY id").fetchall()
    return records, before


@pytest.mark.parametrize("include_overnight", [False, True])
def test_actual_http_plain_keeps_overnight_in_matches_live_and_counter(
    app_module, monkeypatch, tmp_path, include_overnight
):
    a = app_module
    path = tmp_path / "OWNED_PLAIN_COHORT.sqlite"
    monkeypatch.setattr(a, "DB_PATH", str(path))
    records, before = _owned_database(a, path, 6 + int(include_overnight))
    a.invalidate_v934_realtime_cache()
    with a.app.test_client() as client:
        response = client.get("/api/realtime/sports")
        assert response.status_code == 200
        payload = response.get_json()
        assert len(a.g.v935_public_sports_summary["valid_live_events"]) == len(records)
        assert response.headers["ETag"] and response.headers["Last-Modified"]
        assert "private" in response.headers["Cache-Control"]
        assert {"accept", "cookie"} <= {
            value.strip().lower() for value in response.headers["Vary"].split(",")
        }
        unchanged = client.get("/api/realtime/sports", headers={"If-None-Match": response.headers["ETag"]})
        assert unchanged.status_code == 304
        assert unchanged.headers["ETag"] == response.headers["ETag"]
        for scope, fields in (
            ("matches", {"matches"}), ("live", {"live"}), ("picks", {"picks"}),
            ("odds", {"picks"}), ("unknown", {"matches", "live", "picks"}),
        ):
            scoped = client.get("/api/realtime/sports", query_string={"scope": scope}).get_json()
            assert {name for name in ("matches", "live", "picks") if name in scoped} == fields
            assert scoped["counts"]["live"] == len(records)
            if "live" in fields:
                assert {item["id"] for item in scoped["live"]} == {item["id"] for item in records}
            if "matches" in fields:
                assert {item["id"] for item in scoped["matches"]} == {item["id"] for item in records}
        detail = client.get("/api/realtime/match/" + records[-1]["id"])
        assert detail.status_code == 200 and detail.get_json()["match"]["id"] == records[-1]["id"]
    assert payload["counts"]["live"] == len(payload["live"]) == len(records)
    assert payload["poll_after_seconds"] == 45 and payload["no_external_calls"] is True
    assert "fixture_identity" not in payload and "fixture_metrics" not in payload
    for field in ("matches", "live"):
        frames = {row["id"]: row for row in payload[field]}
        assert set(frames) == {row["id"] for row in records}
        for own in records:
            frame = frames[own["id"]]
            assert frame["match_date"] == own["match_date"]
            assert frame["last_synced_at"] == frame["updated_at"] == own["last_synced_at"]
            assert frame["home_score"] == 2 and frame["away_score"] == 1
            assert frame["is_live"] is True and frame["is_stale"] is False
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT * FROM matches ORDER BY id").fetchall() == before
