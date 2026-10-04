from datetime import datetime, timedelta, timezone
from itertools import permutations
import json
import sqlite3

import pytest

from engines.unified_sports_truth_store import bind_identity, ensure_schema, persist_receipt, persist_api_section, project_rows, rehome_receipts
from engines.unified_sports_truth_engine import CONTRACT, evidence_from_row, legacy_projection, resolve_match, refresh_payload_truth
from engines.v935_launch_trust_engine import match_status_truth

NOW = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)


def receipt(provider="api_football", age=30, **values):
    return evidence_from_row({"id": "stable", "external_id": provider + "-1",
        "source": provider, "home_team": "Local", "away_team": "Visitante",
        "competition_name": "Liga", "kickoff_iso": (NOW-timedelta(minutes=75)).isoformat(),
        "status": "2H", "home_score": 1, "away_score": 0, "minute": "67",
        "last_synced_at": (NOW-timedelta(seconds=age)).isoformat(), **values})


def resolve(*receipts):
    return resolve_match("stable", receipts, now=NOW)


def test_field_precedence_conflicting_status_score_minute_and_identity():
    af = receipt(home_team="AF Local")
    db = receipt("thesportsdb", status="FT", home_score=2, away_score=2, minute="90", home_team="DB Local")
    canonical = resolve(af, db)
    assert canonical["phase"] == "live"
    assert canonical["values"]["score"] == "1-0"
    assert canonical["values"]["minute"] == "67"
    assert canonical["values"]["home_team"] == "DB Local"
    assert canonical["resolved"]["status"]["conflict"]
    assert canonical["resolved"]["home_team"]["provider"] == "thesportsdb"


def test_stale_preferred_provider_loses_to_fresh_real_fallback():
    canonical = resolve(receipt(age=500), receipt("thesportsdb", age=10, home_score=2, minute="70"))
    assert canonical["values"]["score"] == "2-0"
    assert canonical["resolved"]["status"]["provider"] == "thesportsdb"
    assert any(a["stale_reason"] == "TTL_EXPIRED" for a in canonical["resolved"]["status"]["alternatives"])


@pytest.mark.parametrize("blocked", ["BLOCKED_BY_ACCESS", "PLAN_RESTRICTED", "TECHNICAL_ERROR"])
def test_unavailable_provider_is_never_treated_as_absence(blocked):
    af = receipt(stats={"shots": 9}, coverage={"stats": blocked})
    db = receipt("thesportsdb", stats={"shots": 3})
    canonical = resolve(af, db)
    assert canonical["values"]["stats"] == {"shots": 3}
    assert canonical["resolved"]["stats"]["provider"] == "thesportsdb"


@pytest.mark.parametrize("group,state", [("stats", "NO_STATISTICS"), ("video", "NO_VIDEO")])
def test_legitimate_absence_retains_provenance_without_false_zeros(group, state):
    canonical = resolve(receipt(coverage={group: state}))
    assert canonical["values"][group] is None
    assert canonical["resolved"][group]["availability"] == state
    assert canonical["resolved"][group]["observed_at"]


def test_legitimate_absence_does_not_hide_real_fallback_statistics():
    canonical = resolve(receipt(coverage={"stats": "NO_STATISTICS"}), receipt("thesportsdb", stats={"shots": 4}))
    assert canonical["values"]["stats"] == {"shots": 4}
    assert canonical["resolved"]["stats"]["provider"] == "thesportsdb"


def test_missing_scores_are_not_borrowed_or_zero_filled():
    canonical = resolve(receipt(home_score=None, away_score=None), receipt("thesportsdb", home_score=3, away_score=2))
    assert canonical["values"]["home_score"] is None
    assert canonical["values"]["away_score"] is None
    assert canonical["values"]["score"] is None
    assert canonical["resolved"]["home_score"]["reason"] == "STATE_COHERENCE_ANCHOR"


def test_explicit_stale_descriptor_loses_to_fresh_fallback():
    canonical = resolve(receipt(coverage={"state": {"state": "STALE", "observed_at": NOW.isoformat()}}),
                        receipt("thesportsdb", minute="70", home_score=2))
    assert canonical["values"]["score"] == "2-0"
    assert canonical["resolved"]["status"]["provider"] == "thesportsdb"
    assert any(a["stale_reason"] == "EXPLICIT_STALE_EVIDENCE" for a in canonical["resolved"]["status"]["alternatives"])


def test_final_fixture_does_not_rejuvenate_old_live_statistics():
    conn = sqlite3.connect(":memory:")
    live = receipt(stats={"shots": 3})
    row = {**live["values"], "source": "api_football", "external_id": "42", "last_synced_at": (NOW-timedelta(seconds=500)).isoformat(), "raw_json": json.dumps({"stats": {"shots": 3}})}
    persist_receipt(conn, "stable", row, provider="api_football")
    final = {k: v for k, v in row.items() if k != "stats"}
    final.update(status="FT", last_synced_at=NOW.isoformat())
    final["raw_json"] = "{}"
    persist_receipt(conn, "stable", final, provider="api_football")
    result = project_rows(conn, [{"id": "stable"}], now=NOW)[0]["unified_sports_truth"]
    assert result["phase"] == "finished"
    assert result["resolved"]["stats"]["stale_reason"] == "TTL_EXPIRED"
    assert result["resolved"]["stats"]["ttl_seconds"] == 120
    assert result["provider_evidence"][0]["raw"]["stats"] == {"shots": 3}


def test_refresh_same_match_keeps_distinct_section_evidence():
    first = resolve(receipt(stats={"shots": 3}))
    second = resolve(receipt(stats={"shots": 7}))
    payload = [legacy_projection({"id": "stable"}, first), legacy_projection({"id": "stable"}, second)]
    refreshed = refresh_payload_truth(payload, now=NOW+timedelta(seconds=70))
    assert [r["unified_sports_truth"]["values"]["stats"] for r in refreshed] == [{"shots": 3}, {"shots": 7}]


def test_exact_dedupe_preserves_independent_latest_groups():
    conn = sqlite3.connect(":memory:")
    persist_receipt(conn, "keeper", {"source": "api_football", "status": "2H", "home_score": 2, "away_score": 0,
        "last_synced_at": NOW.isoformat()}, provider="api_football")
    persist_receipt(conn, "alias", {"source": "api_football", "status": "2H", "home_score": 1, "away_score": 0,
        "stats": {"shots": 8}, "last_synced_at": (NOW-timedelta(seconds=20)).isoformat()}, provider="api_football")
    rehome_receipts(conn, "alias", "keeper")
    result = project_rows(conn, [{"id": "keeper"}], now=NOW)[0]["unified_sports_truth"]
    assert result["values"]["score"] == "2-0"
    assert result["values"]["stats"] == {"shots": 8}


@pytest.mark.parametrize("age,stale", [(20, ""), (500, "TTL_EXPIRED")])
def test_legacy_live_depth_uses_its_own_capture_clock(age, stale):
    from engines.unified_sports_truth_engine import canonicalize_detail
    captured = (NOW-timedelta(seconds=age)).isoformat()
    detail = {"match": legacy_projection({"id": "stable"}, resolve(receipt())), "api_football_live_tracker": {
        "provider": "api_football", "updated_at": NOW.isoformat(),
        "stats": {"teams": [{"raw": [{"captured_at": captured, "stat_value": "55%"}]}]},
        "stat_cards": [{"label": "Posesión", "home": "55%", "away": "45%", "home_numeric": 55, "away_numeric": 45}],
        "events": [{"captured_at": captured, "elapsed": 25, "event_type": "Goal", "team_name": "Local", "player_name": "Jugador"}],
    }}
    canonicalize_detail(detail, now=NOW)
    canonical = detail["unified_sports_truth"]
    assert detail["cached_statistics"]["available"]
    assert canonical["resolved"]["stats"]["observed_at"] == captured
    assert canonical["resolved"]["stats"]["stale_reason"] == stale
    assert "home_numeric" not in canonical["values"]["stats"]["items"][0]
    assert canonical["resolved"]["events"]["observed_at"] == captured


def test_expired_detail_refreshes_nested_match_and_statistics_together():
    af_stats = {"available": True, "items": [{"label": "Tiros", "home": 3, "away": 2}]}
    db_stats = {"available": True, "items": [{"label": "Tiros", "home": 4, "away": 2}]}
    canonical = resolve(receipt(stats=af_stats), receipt("thesportsdb", age=0, stats=db_stats))
    detail = {"match": legacy_projection({"id": "stable"}, canonical), "unified_sports_truth": canonical,
              "cached_statistics": af_stats, "media": {"rights_state": "BLOCKED"}}
    renewed = refresh_payload_truth(detail, now=NOW+timedelta(seconds=115))
    assert renewed["match"]["unified_sports_truth"]["resolved"]["stats"]["provider"] == "thesportsdb"
    assert renewed["cached_statistics"] == db_stats
    assert renewed["unified_sports_truth"] == renewed["match"]["unified_sports_truth"]
    assert renewed["media"] == detail["media"]


@pytest.mark.parametrize("date,hour,offset", [("2026-01-15T20:00:00Z", "21:00", "+01:00"), ("2026-07-15T20:00:00Z", "22:00", "+02:00")])
def test_kickoff_madrid_winter_summer(date, hour, offset):
    canonical = resolve(receipt(kickoff_iso=date))
    assert canonical["kickoff_madrid"].endswith(offset)
    projected = legacy_projection({"id": "stable"}, canonical)
    assert projected["kickoff_time"] == hour


@pytest.mark.parametrize("age,source,usable", [(30, "The Odds API", True), (901, "The Odds API", False), (30, "unknown", False)])
def test_odds_provenance_and_expiry(age, source, usable):
    canonical = resolve(receipt(odds_h2h_json=json.dumps({"source": source, "outcomes": [{"name": "Local", "price": 2.1}]}),
                                odds_updated_at=(NOW-timedelta(seconds=age)).isoformat(), odds_fetched_at=NOW.isoformat()))
    assert canonical["odds_snapshot"]["usable"] is usable
    assert bool(legacy_projection({}, canonical)["odds_h2h_json"]) is usable


def test_generic_write_clock_cannot_rejuvenate_missing_observation():
    canonical = resolve(receipt(last_synced_at=None, updated_at=NOW.isoformat()))
    assert canonical["phase"] == "stale"
    assert canonical["resolved"]["status"]["stale_reason"] == "MISSING_OBSERVED_AT"


def test_persistent_mapping_rejects_ambiguous_existing_alias():
    conn = sqlite3.connect(":memory:")
    assert bind_identity(conn, "team", "thesportsdb", "12", "team:first", proof="EXPLICIT")
    assert not bind_identity(conn, "team", "thesportsdb", "12", "team:other", proof="EXPLICIT")
    assert bind_identity(conn, "team", "api_football", "12", "team:other", proof="EXPLICIT")
    assert conn.execute("SELECT count(*) FROM sports_truth_mappings").fetchone()[0] == 2


def test_ties_and_input_order_are_deterministic():
    samples = [receipt(home_score=1), receipt(home_score=2), receipt("thesportsdb", minute="70")]
    snapshots = [resolve(*order) for order in permutations(samples)]
    assert len({json.dumps(s["values"], sort_keys=True) for s in snapshots}) == 1
    assert len({s["resolved"]["status"]["receipt_id"] for s in snapshots}) == 1


def test_every_resolved_field_explains_winner_and_freshness():
    canonical = resolve(receipt())
    assert canonical["contract"] == CONTRACT
    for decision in canonical["resolved"].values():
        assert {"value", "source", "provider", "observed_at", "fetched_at", "stale_reason", "reason", "alternatives", "availability"} <= decision.keys()


def test_current_snapshot_never_survives_live_deadline():
    canonical = resolve(receipt(age=119))
    projected = legacy_projection({}, canonical)
    assert match_status_truth(projected, now=NOW)["is_live"]
    assert not match_status_truth(projected, now=NOW+timedelta(seconds=3))["is_live"]


def test_database_reads_do_not_write_and_batch_queries_are_bounded():
    conn = sqlite3.connect(":memory:")
    ensure_schema(conn)
    data = [{"id": str(i), "source": "thesportsdb", "home_team": "L", "away_team": "V", "status": "FT", "home_score": 0, "away_score": 0, "last_synced_at": NOW.isoformat()} for i in range(100)]
    persist_receipt(conn, "0", data[0])
    conn.commit()
    queries = []
    conn.set_trace_callback(queries.append)
    result = project_rows(conn, data, now=NOW)
    assert len(result) == 100
    assert all(r["score"] == "0-0" for r in result)
    assert len(queries) == 2
    assert all(q.startswith("SELECT") for q in queries)


def test_dedupe_retains_both_providers_and_route_id():
    conn = sqlite3.connect(":memory:")
    persist_receipt(conn, "old", {"source": "thesportsdb", "external_id": "1", "last_synced_at": NOW.isoformat()})
    persist_receipt(conn, "keeper", {"source": "api_football", "external_id": "2", "last_synced_at": NOW.isoformat()})
    rehome_receipts(conn, "old", "keeper")
    assert conn.execute("SELECT count(*) FROM sports_truth_receipts WHERE match_id='keeper'").fetchone()[0] == 2
    assert conn.execute("SELECT canonical_id FROM sports_truth_mappings WHERE provider='thesportsdb'").fetchone()[0] == "keeper"


def test_cross_surface_same_match_uses_same_canonical_contract(app_module, monkeypatch, tmp_path):
    path = tmp_path / "sports.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE matches(id TEXT PRIMARY KEY, source TEXT, home_team TEXT, away_team TEXT, status TEXT, last_synced_at TEXT, home_score INTEGER, away_score INTEGER, kickoff_iso TEXT)")
    stamp = datetime.now(timezone.utc)
    raw = {"id": "same", "source": "thesportsdb", "home_team": "Local", "away_team": "Visitante", "status": "FT", "last_synced_at": stamp.isoformat(), "home_score": 1, "away_score": 0, "kickoff_iso": (stamp-timedelta(hours=3)).isoformat()}
    conn.execute("INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?)", tuple(raw.values()))
    conn.commit()
    monkeypatch.setattr(app_module, "db", lambda: sqlite3.connect(path))
    # sqlite3.Row is the production DB contract.
    def db():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c
    monkeypatch.setattr(app_module, "db", db)
    item = app_module.rows("SELECT * FROM matches")[0]
    surface = app_module.canonical_match_surface_contract(item)
    domain = app_module.canonical_match_for_domain_context(item)
    for consumer in ("home", "calendar", "live", "match_center", "shark", "picks"):
        assert app_module.canonical_match_surface_contract(domain)["score"] == surface["score"] == "1-0"
        assert surface["sports_truth_contract"] == CONTRACT
        assert domain["unified_sports_truth"]["resolved"]["status"]["provider"] == "thesportsdb"


def test_section_ingestion_cannot_rejuvenate_fixture_or_erase_other_groups():
    conn = sqlite3.connect(":memory:")
    raw = {"source": "api_football", "external_id": "42", "home_team": "Local", "away_team": "Visitante", "home_team_id": "1", "away_team_id": "2", "status": "2H", "minute": 10, "last_synced_at": (NOW-timedelta(seconds=500)).isoformat()}
    persist_receipt(conn, "match", raw, provider="api_football")
    assert persist_api_section(conn, "42", "stats", [{"team": {"id": 1, "name": "Local"}, "statistics": [{"type": "Shots", "value": None}, {"type": "Possession", "value": "55%"}]}], observed_at=NOW.isoformat())
    encoded = conn.execute("SELECT evidence_json FROM sports_truth_receipts").fetchone()[0]
    evidence = json.loads(encoded)
    assert evidence["groups"]["state"]["observed_at"] == raw["last_synced_at"]
    assert evidence["groups"]["stats"]["observed_at"] == NOW.isoformat()
    canonical = resolve(evidence)
    assert canonical["phase"] == "stale"
    assert canonical["values"]["stats"]["items"][0]["away"] is None
    assert len(canonical["values"]["stats"]["items"]) == 1
    persist_receipt(conn, "match", {**raw, "last_synced_at": NOW.isoformat()}, provider="api_football")
    evidence = json.loads(conn.execute("SELECT evidence_json FROM sports_truth_receipts").fetchone()[0])
    assert evidence["values"]["stats"]["items"][0]["home"] == "55%"


def test_persistence_rejects_conflicting_match_provider_id():
    conn = sqlite3.connect(":memory:")
    raw = {"source": "thesportsdb", "external_id": "same-provider-id", "last_synced_at": NOW.isoformat()}
    assert persist_receipt(conn, "first", raw)
    assert not persist_receipt(conn, "ambiguous", raw)
    assert conn.execute("SELECT match_id FROM sports_truth_receipts").fetchall() == [("first",)]


def test_cached_odds_expire_even_without_another_database_read():
    canonical = resolve(receipt(odds_h2h_json=json.dumps({"source": "The Odds API", "outcomes": [{"name": "Local", "price": 2.1}]}), odds_updated_at=(NOW-timedelta(seconds=899)).isoformat(), odds_fetched_at=NOW.isoformat()))
    raw = legacy_projection({"id": "stable"}, canonical)
    payload = {"home": [raw], "calendar": [raw]}
    renewed = refresh_payload_truth(payload, now=NOW+timedelta(seconds=3))
    assert not renewed["home"][0]["unified_sports_truth"]["odds_snapshot"]["usable"]
    assert renewed["home"][0]["odds_h2h_json"] is None
    assert payload["home"][0]["unified_sports_truth"]["odds_snapshot"]["usable"]


def test_raw_evidence_redacts_credentials():
    evidence = receipt(raw_json=json.dumps({"api_key": "must-not-leak", "headers": {"token": "hidden"}, "fixture": {"id": 42}}))
    assert evidence["raw"] == {"fixture": {"id": 42}}


def test_odds_without_a_real_fetch_receipt_are_unusable():
    canonical = resolve(receipt(odds_h2h_json=json.dumps({"source": "The Odds API", "outcomes": [{"name": "Local", "price": 2.1}]}), odds_updated_at=NOW.isoformat()))
    assert not canonical["odds_snapshot"]["usable"]
    assert canonical["resolved"]["odds_h2h_json"]["fetched_at"] is None
    assert canonical["resolved"]["odds_h2h_json"]["stale_reason"] == "MISSING_FETCHED_AT"


def test_domain_identity_and_score_survive_provider_fallback_at_expiry():
    from engines.sports_domain_model_engine import normalize_match_entity
    canonical = resolve(receipt(age=119), receipt("thesportsdb", age=0, status="FT", home_score=3, away_score=2, score="3-2"))
    row = legacy_projection({"id": "stable"}, canonical)
    current = normalize_match_entity(row, now_madrid=NOW.isoformat())
    expired = normalize_match_entity(row, now_madrid=(NOW+timedelta(seconds=3)).isoformat())
    assert current["canonical_match_id"] == expired["canonical_match_id"] == "stable"
    assert expired["score"]["home"] == 3
    assert expired["score"]["away"] == 2
    assert len(expired["provider_match_ids"]) == 2


def test_entity_reads_apply_only_explicit_persisted_mapping():
    conn = sqlite3.connect(":memory:")
    assert bind_identity(conn, "team", "api_football", "1", "team:confirmed", proof="EXPLICIT_VERIFIED_PAIR")
    assert bind_identity(conn, "team", "thesportsdb", "100", "team:confirmed", proof="EXPLICIT_VERIFIED_PAIR")
    af = {"id": "stable", "source": "api_football", "home_team": "Local", "away_team": "Visitante", "home_team_id": "1", "status": "FT", "home_score": 1, "away_score": 0, "last_synced_at": NOW.isoformat()}
    persist_receipt(conn, "stable", {**af, "source": "thesportsdb", "home_team_id": "100"})
    canonical = project_rows(conn, [af], now=NOW)[0]["unified_sports_truth"]
    assert canonical["teams"]["home"]["canonical_team_id"] == "team:confirmed"


def test_committed_receipt_invalidates_another_connection_cache(tmp_path):
    from engines.unified_sports_truth_store import invalidate_changed_store
    from engines.v934_realtime_sports_engine import cached_realtime_snapshot, invalidate_realtime_cache
    path = tmp_path / "workers.sqlite"
    first = sqlite3.connect(path)
    second = sqlite3.connect(path)
    ensure_schema(first)
    first.commit()
    key = "phase3:isolated-workers"
    invalidate_realtime_cache(key)
    builds = []
    def build():
        builds.append(1)
        return {"count": len(builds)}
    invalidate_changed_store(first, key)
    assert cached_realtime_snapshot(key, build)[0]["count"] == 1
    assert cached_realtime_snapshot(key, build)[0]["count"] == 1
    persist_receipt(second, "stable", {"source": "api_football", "status": "FT", "last_synced_at": NOW.isoformat()})
    second.commit()
    invalidate_changed_store(first, key)
    assert cached_realtime_snapshot(key, build)[0]["count"] == 2
    invalidate_realtime_cache(key)
    first.close()
    second.close()


def test_deduplicated_route_alias_preserves_legacy_link():
    from services.sports_service import read_match_record
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE matches(id TEXT PRIMARY KEY, score TEXT)")
    conn.execute("INSERT INTO matches VALUES('keeper','1-0')")
    rehome_receipts(conn, "old-route", "keeper")
    def read_one(query, params):
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None
    assert read_match_record(read_one, "old-route") == {"id": "keeper", "score": "1-0"}


def test_raw_video_evidence_cannot_bypass_highlight_rights_policy():
    from engines.unified_sports_truth_engine import canonicalize_detail
    canonical = resolve(receipt(video="https://example.invalid/unreviewed.mp4"))
    restricted = {"available": False, "rights_state": "BLOCKED"}
    detail = {"match": legacy_projection({"id": "stable"}, canonical), "media": restricted}
    canonicalize_detail(detail, now=NOW)
    assert detail["media"] == restricted


def test_request_projection_reuses_bulk_reads_without_mutable_aliases():
    conn = sqlite3.connect(":memory:")
    ensure_schema(conn)
    row = {"id": "stable", "source": "api_football", "status": "FT", "home_score": 1, "away_score": 0, "last_synced_at": NOW.isoformat()}
    cache, queries = {}, []
    conn.set_trace_callback(queries.append)
    first = project_rows(conn, [row], now=NOW, tables={"sports_truth_receipts"}, cache=cache)[0]
    first["unified_sports_truth"]["resolved"]["status"]["value"] = "BAD"
    second = project_rows(conn, [row], now=NOW, tables={"sports_truth_receipts"}, cache=cache)[0]
    assert len(queries) == 1
    assert second["unified_sports_truth"]["resolved"]["status"]["value"] == "FT"


def test_real_route_contexts_share_winners(app_module, monkeypatch, tmp_path):
    """Exercise real handlers and templates; no substitute sports summaries."""
    from flask import template_rendered
    from engines.v934_realtime_sports_engine import invalidate_realtime_cache
    path = tmp_path / "http.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    app_module.init_db()
    monkeypatch.setattr(app_module, "APP_INITIALIZED", True)
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", str(path))
    stamp = datetime.now(timezone.utc)
    kickoff = stamp-timedelta(minutes=75)
    row = {"id": "truth-http", "external_id": "42", "source": "api_football", "home_team": "Real Madrid", "away_team": "Barcelona", "competition_name": "La Liga", "league_name": "La Liga", "competition_key": "laliga", "competition_id": "140", "country": "Spain", "status": "2H", "minute": "67", "score": "1-0", "home_score": 1, "away_score": 0, "kickoff_iso": kickoff.isoformat(), "match_date": kickoff.astimezone(app_module.TZ).date().isoformat(), "kickoff_time": kickoff.astimezone(app_module.TZ).strftime("%H:%M"), "last_synced_at": stamp.isoformat(), "updated_at": stamp.isoformat(), "priority": 95}
    conn = app_module.db()
    conn.execute(f"INSERT INTO matches ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values()))
    persist_receipt(conn, "truth-http", row, provider="api_football")
    persist_receipt(conn, "truth-http", {**row, "external_id": "99", "source": "thesportsdb", "status": "FT", "home_score": 3, "away_score": 2, "score": "3-2", "minute": 90}, provider="thesportsdb")
    conn.execute("INSERT INTO users(id,name,username,email,password_hash,role,membership,created_at) VALUES(?,?,?,?,?,?,?,?)", ("truth-client", "QA", "truth-client", "truth@example.invalid", "unusable-local-qa", "FREE", "FREE", stamp.isoformat()))
    conn.commit()
    conn.close()
    invalidate_realtime_cache()
    contexts = []
    def capture(sender, template, context, **extra):
        contexts.append(context)
    template_rendered.connect(capture, app_module.app)
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session.update(user_id="truth-client", user_role="FREE", membership="FREE")
    def canonical_rows(value):
        if isinstance(value, list):
            return [r for item in value for r in canonical_rows(item)]
        if not isinstance(value, dict):
            return []
        c = value.get("unified_sports_truth")
        if isinstance(c, dict) and c.get("canonical_match_id") == "truth-http":
            return [c]
        return [r for key, item in value.items() if key not in {"provider_evidence", "resolved"} for r in canonical_rows(item)]
    try:
        for route in ("/app", "/calendario", "/directo", "/match/truth-http", "/shark"):
            contexts.clear()
            response = client.get(route)
            assert response.status_code == 200, route
            snapshots = canonical_rows(contexts)
            assert snapshots, route
            for canonical in snapshots:
                assert canonical["values"]["score"] == "1-0", route
                assert canonical["phase"] == "live", route
                assert canonical["resolved"]["status"]["provider"] == "api_football", route
    finally:
        template_rendered.disconnect(capture, app_module.app)
        invalidate_realtime_cache()
