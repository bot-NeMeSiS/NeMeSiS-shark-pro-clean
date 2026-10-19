import sqlite3

from engines import shark_prediction_engine as engine


def _database(path, *, matches=(), warehouse=()):
    conn = sqlite3.connect(path)
    for table in ("matches", "warehouse_match_facts"):
        conn.execute(f"""CREATE TABLE {table}(
            id TEXT PRIMARY KEY, match_id TEXT, match_date TEXT, kickoff_time TEXT,
            kickoff_iso TEXT, competition_name TEXT, league_name TEXT,
            home_team TEXT, away_team TEXT, status TEXT,
            home_score REAL, away_score REAL, score TEXT, result TEXT, snapshot_at TEXT
        )""")
    for row in matches:
        conn.execute(
            """INSERT INTO matches
               (id, match_date, kickoff_time, competition_name, home_team, away_team, status, home_score, away_score)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            row,
        )
    for row in warehouse:
        conn.execute(
            """INSERT INTO warehouse_match_facts
               (id, match_id, match_date, kickoff_iso, league_name, home_team, away_team, status, home_score, away_score, snapshot_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            row,
        )
    conn.commit()
    conn.close()


def test_score_pair_preserves_zero_and_rejects_invalid_scores():
    assert engine._score_pair({"home_score": 0, "away_score": 2}) == (0, 2)
    assert engine._score_pair({"home_score": 0, "away_score": 0}) == (0, 0)
    assert engine._score_pair({"home_score": -1, "away_score": 2}) == (None, None)
    assert engine._score_pair({"home_score": 1.5, "away_score": 2}) == (None, None)


def test_status_normalization_does_not_treat_pending_or_live_as_finished():
    assert engine.normalize_status("FT") == "finished"
    assert engine.normalize_status("Match Finished") == "finished"
    assert engine.normalize_status("Finalizado tras prórroga") == "finished"
    assert engine.normalize_status("pending") == "scheduled"
    assert engine.normalize_status("LIVE") == "live"


def test_training_uses_only_explicit_finished_matches_and_keeps_nil_scores(tmp_path):
    path = tmp_path / "sports.sqlite"
    _database(path, matches=[
        ("pending-00", "2026-10-20", "18:00", "Liga", "Home", "Away", "pending", 0, 0),
        ("live-21", "2026-10-19", "18:00", "Liga", "Home", "Away", "LIVE", 2, 1),
        ("finished-00", "2026-10-18", "18:00", "Liga", "Home", "Away", "FT", 0, 0),
    ])

    conn = engine.connect(str(path))
    try:
        result = engine._finished_matches(conn, 20)
    finally:
        conn.close()

    assert [item["id"] for item in result] == ["finished-00"]
    assert (result[0]["_home_score"], result[0]["_away_score"]) == (0, 0)


def test_warehouse_fallback_is_also_filtered_to_finished_results(tmp_path):
    path = tmp_path / "sports.sqlite"
    _database(
        path,
        matches=[("pending", "2026-10-20", "18:00", "Liga", "Home", "Away", "NS", 0, 0)],
        warehouse=[
            ("wh-pending", "pending", "2026-10-20", "2026-10-20T18:00:00", "Liga", "Home", "Away", "pending", 1, 0, "now"),
            ("wh-ft", "finished", "2026-10-18", "2026-10-18T18:00:00", "Liga", "Home", "Away", "FT", 0, 1, "now"),
        ],
    )

    conn = engine.connect(str(path))
    try:
        result = engine._finished_matches(conn, 20)
    finally:
        conn.close()

    assert [item["id"] for item in result] == ["wh-ft"]
    assert (result[0]["_home_score"], result[0]["_away_score"]) == (0, 1)


def test_empty_rebuild_preserves_existing_ratings_and_reports_insufficient_data(tmp_path):
    path = tmp_path / "sports.sqlite"
    _database(path, matches=[("pending", "2026-10-20", "18:00", "Liga", "Home", "Away", "pending", 0, 0)])
    engine.ensure_shark_prediction_schema(str(path))
    conn = engine.connect(str(path))
    conn.execute(
        """INSERT INTO shark_team_ratings(team_name,rating,matches_played,reliability_score)
           VALUES ('Existing Team',91,12,96)"""
    )
    conn.commit()
    conn.close()

    result = engine.rebuild_shark_prediction_engine(str(path))

    conn = sqlite3.connect(path)
    kept = conn.execute("SELECT rating,matches_played FROM shark_team_ratings WHERE team_name='Existing Team'").fetchone()
    conn.close()
    assert result["ok"] is False
    assert result["state"] == "INSUFFICIENT_FINISHED_RESULTS"
    assert result["preserved_existing_model"] is True
    assert kept == (91, 12)


def test_rebuild_does_not_seed_placeholder_market_scores_or_claim_accuracy(tmp_path):
    path = tmp_path / "sports.sqlite"
    _database(path, matches=[("ft", "2026-10-18", "18:00", "Liga", "Home", "Away", "FT", 1, 0)])

    result = engine.rebuild_shark_prediction_engine(str(path))

    assert result["ok"] is True
    assert result["matches_analyzed"] == 1
    assert result["summary"]["markets_rated"] == 0
    assert result["summary"]["readiness_type"] == "historical_data_coverage_not_model_accuracy"
    assert result["summary"]["historical_data_coverage"] > 0
    assert result["summary"]["prediction_readiness"] == 0
    assert result["summary"]["prediction_validation_state"] == "NOT_VALIDATED"
    conn = sqlite3.connect(path)
    market_rows = conn.execute("SELECT COUNT(*) FROM shark_prediction_market_scores").fetchone()[0]
    conn.close()
    assert market_rows == 0


def test_untrained_prediction_does_not_emit_pick_or_confidence(tmp_path):
    path = tmp_path / "sports.sqlite"
    _database(path)

    result = engine.prediction_for_match(str(path), {
        "home_team": "Home", "away_team": "Away", "competition_name": "Liga",
    })

    assert result["state"] == "INSUFFICIENT_HISTORY"
    assert result["available"] is False
    assert result["decision"] == "WAIT"
    assert result["can_publish"] is False
    assert result["recommended_market"] is None
    assert result["recommended_selection"] is None
    assert result["score_v2"] is None


def test_historical_ratings_alone_never_become_a_publishable_shark_pick(tmp_path):
    path = tmp_path / "sports.sqlite"
    _database(path, matches=[
        (f"finished-{index}", f"2026-10-{10 + index:02d}", "18:00", "Liga", "Home", "Away", "FT", index % 3, (index + 1) % 3)
        for index in range(10)
    ])
    engine.rebuild_shark_prediction_engine(str(path))

    result = engine.prediction_for_match(str(path), {
        "home_team": "Home", "away_team": "Away", "competition_name": "Liga",
    })

    assert result["state"] == "UNVALIDATED_HISTORICAL_SIGNAL"
    assert result["available"] is False
    assert result["historical_signal_available"] is True
    assert result["validated"] is False
    assert result["decision"] == "WAIT"
    assert result["can_publish"] is False
    assert result["rating_signal"] in {"LOCAL", "VISITANTE", "EQUILIBRADO"}
    assert result["recommended_market"] is None
    assert result["recommended_selection"] is None
    assert result["score_v2"] is None


def test_unvalidated_prediction_layer_never_changes_pick_score(tmp_path):
    path = tmp_path / "sports.sqlite"
    _database(path)
    original = {"home_team": "Home", "away_team": "Away", "score": 81, "confidence": 81}

    result = engine.apply_shark_prediction_adjustment(original, str(path))

    assert result["score"] == 81
    assert result["confidence"] == 81
    assert result["prediction_adjustment"] == 0
    assert result["prediction_score_v2"] is None
