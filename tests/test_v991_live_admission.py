"""Real coordinator/consumer admission tests over coherent synthetic originals.

No provider, getter, finalizer, context, normalizer or C2/C3 is replaced. Unit
references enter only their exact PK-reader boundary. HTTP input is supplied at
the public cache source boundary before the real getter/finalization, not grafted
onto a prepared getter result. Run under the established guarded App harness.
"""
from copy import deepcopy
from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo

import pytest


_REFERENCE = {"key": "laliga", "name": "LaLiga", "country": "Spain",
              "source": "API_FOOTBALL", "external_id": "140"}


def _rows():
    now = datetime.now(ZoneInfo("Europe/Madrid"))
    start = now - timedelta(minutes=20)
    rows = []
    for index in range(2):
        native = 800001 + index
        row = {
            "id": "af-" + str(native), "match_id": "af-" + str(native),
            "external_id": str(native), "source": "api_football_live",
            "sport": "soccer", "sport_key": "soccer",
            "competition_key": "laliga", "competition_id": "140",
            "competition_name": "LaLiga", "league_name": "LaLiga", "country": "Spain",
            "season": str(start.year), "home_team": "Real Madrid", "away_team": "Atletico Madrid",
            "home_team_id": "88001", "away_team_id": "88002",
            "match_date": start.date().isoformat(), "kickoff_iso": start.isoformat(),
            "kickoff_time": start.strftime("%H:%M"), "match_time": start.strftime("%H:%M"),
            "status": "LIVE", "minute": 20, "home_score": index + 1, "away_score": 0,
            "updated_at": now.isoformat(), "last_synced_at": now.isoformat(),
        }
        row["raw_json"] = json.dumps({
            "fixture": {"id": native, "date": start.isoformat(), "status": {"short": "1H", "elapsed": 20}},
            "league": {"id": 140, "name": "LaLiga", "country": "Spain", "season": start.year},
            "teams": {"home": {"id": 88001, "name": row["home_team"]},
                      "away": {"id": 88002, "name": row["away_team"]}},
            "goals": {"home": index + 1, "away": 0},
        })
        rows.append(row)
    return rows, now


def _summary(rows, approved):
    return {
        "all_valid_matches": rows, "valid_matches_today": rows,
        "valid_matches_available": rows, "valid_upcoming_matches": rows,
        "valid_live_events": list(approved), "valid_active_picks": [],
        "finished_matches": [], "incident_matches": [], "incomplete_matches": [],
        "raw_matches_count": len(rows), "storage_status": "ok",
        "safe_message": "Synthetic LIVE admission contract",
    }


@pytest.fixture
def live_references(app_module, monkeypatch):
    calls = []
    def reader(database, keys):
        assert str(database) == str(app_module.DB_PATH)
        calls.append(tuple(keys))
        return [dict(_REFERENCE)] if "laliga" in keys else []
    monkeypatch.setattr(app_module, "_v991_references", reader)
    return calls


def _own_frame(app_module, row, now):
    return app_module._v991_normalize_frame(
        app_module._v991_own_realtime_source(row, app_module.match_kickoff_madrid_dt), now)


def _finish_surfaces(app_module, summary):
    finished, operation = app_module._v991_finish_summary(summary, selected_date=app_module.today_iso())
    assert finished is summary
    assert operation.matches(finished, app_module.today_iso())
    projection = app_module._v991_realtime_projection(finished, lane="live", query="")
    live = app_module.v931_live_context(finished, lane="live", query="", fixture_projection=projection)
    home = app_module.home_matchday_context(finished)
    return finished, operation, projection, live, home


def test_finish_admission_aligns_home_directo_descriptor_and_own_state(app_module, live_references):
    rows, now = _rows()
    originals = deepcopy(rows)
    assert [_own_frame(app_module, row, now)["is_live"] for row in rows] == [True, True]
    summary = _summary(rows, [rows[0]])
    with app_module.app.test_request_context("/live?f=live"):
        finished, operation, projection, live, home = _finish_surfaces(app_module, summary)
    expected = [rows[0]["id"]]
    assert [row["id"] for row in finished["all_valid_matches"]] == expected
    assert [row["id"] for row in finished["valid_live_events"]] == expected
    assert [row["id"] for row in live["matches"]] == expected
    assert [row["id"] for group in home["live"]["groups"] for row in group["matches"]] == expected
    assert projection["counts"]["live"] == live["counts"]["live"] == 1
    assert projection["fixture_identity"]["view"]["groups_before_limit"] == 1
    assert projection["fixture_identity"]["state"] == "ESTABLISHED_FOR_EMITTED_COHORT"
    approved = finished["all_valid_matches"][0]
    assert approved["raw_json"] == originals[0]["raw_json"]
    assert approved["home_score"] == originals[0]["home_score"]
    assert approved["minute"] == originals[0]["minute"]
    assert approved["last_synced_at"] == originals[0]["last_synced_at"]
    assert rows == originals
    assert operation.snapshot.cohorts["current"] == (approved,)
    assert live_references == [("laliga",)]


def test_finish_preserves_summary_owner_and_cross_lane_original_aliases(app_module, live_references):
    rows, _ = _rows()
    summary = _summary(rows, [rows[0]])
    with app_module.app.test_request_context("/live"):
        finished, operation, _, _, _ = _finish_surfaces(app_module, summary)
    approved = finished["all_valid_matches"][0]
    assert finished is summary
    assert approved is finished["valid_live_events"][0]
    assert approved is finished["valid_matches_today"][0]
    assert approved is finished["valid_matches_available"][0]
    assert approved is finished["valid_upcoming_matches"][0]
    assert approved is operation.snapshot.cohorts["current"][0]
    assert approved is not rows[0]


def test_distinct_object_with_same_local_id_cannot_borrow_live_admission(app_module, live_references):
    rows, now = _rows()
    rows[0]["id"] = rows[0]["match_id"] = "opaque-shared-id"
    rows[1]["id"] = rows[1]["match_id"] = "opaque-shared-id"
    assert rows[0] is not rows[1]
    assert [_own_frame(app_module, row, now)["is_live"] for row in rows] == [True, True]
    with app_module.app.test_request_context("/live"):
        finished, _, projection, live, _ = _finish_surfaces(app_module, _summary(rows, [rows[0]]))
    assert len(finished["all_valid_matches"]) == len(live["matches"]) == 1
    assert finished["all_valid_matches"][0]["external_id"] == rows[0]["external_id"]
    assert projection["counts"]["live"] == 1
    assert projection["matches"][0]["realtime_state"]["score_home"] == 1


def test_both_approved_distinct_native_events_remain_two(app_module, live_references):
    rows, _ = _rows()
    with app_module.app.test_request_context("/live"):
        finished, _, projection, live, home = _finish_surfaces(app_module, _summary(rows, rows))
    assert len(finished["all_valid_matches"]) == len(live["matches"]) == 2
    assert projection["counts"]["live"] == 2
    assert len(home["live"]["groups"][0]["matches"]) == 2
    assert [frame["realtime_state"]["score_home"] for frame in projection["matches"]] == [1, 2]


def test_both_approved_with_duplicate_local_id_fail_descriptor_closed(app_module, live_references):
    rows, _ = _rows()
    for row in rows:
        row["id"] = row["match_id"] = "opaque-shared-id"
    with app_module.app.test_request_context("/live"):
        finished, _, projection, _, _ = _finish_surfaces(app_module, _summary(rows, rows))
    assert len(finished["all_valid_matches"]) == 2
    assert [row["external_id"] for row in finished["all_valid_matches"]] == ["800001", "800002"]
    assert projection["fixture_identity"]["state"] == "NOT_ESTABLISHED"
    assert "DUPLICATE_ID" in projection["fixture_identity"]["coverage"]["reasons"]
    assert projection["counts"]["live"] is None


def test_no_approved_live_original_does_not_promote_nominal_status(app_module, live_references):
    rows, now = _rows()
    assert all(_own_frame(app_module, row, now)["is_live"] for row in rows)
    with app_module.app.test_request_context("/live"):
        finished, _, projection, live, home = _finish_surfaces(app_module, _summary(rows, []))
    assert finished["all_valid_matches"] == []
    assert finished["valid_live_events"] == []
    assert live["matches"] == []
    assert projection["counts"]["live"] == 0
    assert home["live"]["groups"] == []


@pytest.mark.parametrize("kind", ["stale", "terminal", "terminal_conflict"])
def test_approval_never_overrides_own_stale_or_terminal_evidence(app_module, live_references, kind):
    rows, now = _rows()
    row = rows[0]
    if kind == "stale":
        row["updated_at"] = row["last_synced_at"] = (now - timedelta(hours=2)).isoformat()
    else:
        row["status"] = "FT" if kind == "terminal" else "LIVE"
        raw = json.loads(row["raw_json"])
        raw["fixture"]["status"] = {"short": "FT", "elapsed": 90}
        row["raw_json"] = json.dumps(raw)
    own = _own_frame(app_module, row, now)
    assert own["is_stale"] if kind == "stale" else not own["is_live"]
    before = deepcopy(row)
    with app_module.app.test_request_context("/live"):
        finished, _, projection, live, home = _finish_surfaces(app_module, _summary([row], [row]))
    assert finished["valid_live_events"] == []
    assert projection["counts"]["live"] == 0
    assert live["matches"] == []
    assert home["live"]["groups"] == []
    assert row == before


@pytest.mark.parametrize("consumer", ["directo-v2", "fixture-metrics-v1"])
def test_modern_http_uses_real_getter_and_single_finalized_admission(app_module, monkeypatch, live_references, consumer):
    rows, now = _rows()
    assert [_own_frame(app_module, row, now)["is_live"] for row in rows] == [True, True]
    base = _summary(rows, [rows[0]])
    feeds = []
    original_cache = app_module.cached_v934_realtime_snapshot
    def source_cache(key, builder, **kwargs):
        if key == app_module._public_sports_cache_key():
            feeds.append(key)
            return deepcopy(base), "SYNTHETIC_PRE_GETTER_SOURCE"
        return original_cache(key, builder, **kwargs)
    monkeypatch.setattr(app_module, "cached_v934_realtime_snapshot", source_cache)
    response = app_module.app.test_client().get(
        "/api/realtime/sports", query_string={"scope": "matches", "consumer": consumer, "f": "live"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["counts"]["live"] == 1
    assert [row["id"] for row in payload["matches"]] == [rows[0]["id"]]
    assert payload["matches"][0]["realtime_state"]["score_home"] == 1
    assert len(feeds) == 1
    assert live_references == [("laliga",)]
    if consumer == "directo-v2":
        assert payload["fixture_identity"]["state"] == "ESTABLISHED_FOR_EMITTED_COHORT"
        assert payload["fixture_identity"]["view"]["groups_before_limit"] == 1
    else:
        assert payload["fixture_metrics"]["state"] == "ESTABLISHED_FOR_CURRENT_COHORT"
        assert payload["fixture_metrics"]["counts"]["live"] == 1


@pytest.mark.parametrize("mutate_identity", [False, True])
def test_repeated_getter_preserves_prepared_owner_without_readmitting_mutation(
    app_module, monkeypatch, live_references, mutate_identity,
):
    rows, _ = _rows()
    base = _summary(rows, [rows[0]])
    feeds = []
    original_cache = app_module.cached_v934_realtime_snapshot

    def source_cache(key, builder, **kwargs):
        if key == app_module._public_sports_cache_key():
            feeds.append(key)
            return deepcopy(base), "SYNTHETIC_PRE_GETTER_SOURCE"
        return original_cache(key, builder, **kwargs)

    monkeypatch.setattr(app_module, "cached_v934_realtime_snapshot", source_cache)
    with app_module.app.test_request_context("/live"):
        first = app_module.get_public_home_sports_summary()
        operation = app_module._v991_operation_for(first)
        approved = first["all_valid_matches"][0]
        assert operation.snapshot.context_for(approved).state == "RESOLVED"
        if mutate_identity:
            approved["external_id"] = "800099"
        second = app_module.get_public_home_sports_summary()
        assert second is first
        assert app_module._v991_operation_for(second) is operation
        assert second["all_valid_matches"][0] is approved
        assert second["valid_live_events"][0] is approved
        expected = "UNKNOWN_IDENTITY_CHANGED" if mutate_identity else "RESOLVED"
        assert operation.snapshot.context_for(approved).state == expected
    assert len(feeds) == 1
    assert live_references == [("laliga",)]
