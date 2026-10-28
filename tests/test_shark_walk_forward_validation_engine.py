import hashlib
import sqlite3

from engines.shark_walk_forward_validation_engine import evaluate_shark_walk_forward


def _database(path, rows=()):
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE matches(
        id TEXT PRIMARY KEY, external_id TEXT, sport_key TEXT, match_date TEXT,
        kickoff_time TEXT, kickoff_iso TEXT, competition_id TEXT,
        competition_key TEXT, competition_name TEXT, league_name TEXT,
        home_team TEXT, away_team TEXT, home_team_id TEXT, away_team_id TEXT,
        status TEXT, home_score REAL, away_score REAL, score TEXT
    )""")
    conn.executemany(
        """INSERT INTO matches
        (id, match_date, competition_name, home_team, away_team, status, home_score, away_score)
        VALUES (?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    conn.close()


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "missing.sqlite"

    result = evaluate_shark_walk_forward(str(path))

    assert result["state"] == "DATABASE_NOT_FOUND"
    assert result["read_only"] is True
    assert result["validated_for_customer"] is False
    assert path.exists() is False


def test_no_final_results_returns_explicit_empty_state(tmp_path):
    path = tmp_path / "empty.sqlite"
    _database(path, [
        ("pending", "2026-10-20", "Liga", "Home", "Away", "pending", 0, 0),
        ("live", "2026-10-19", "Liga", "Home", "Away", "LIVE", 1, 0),
    ])

    result = evaluate_shark_walk_forward(str(path))

    assert result["state"] == "NO_FINISHED_MATCHES"
    assert result["matches_read"] == 0
    assert result["model_reference"] is None
    assert result["validated_for_customer"] is False


def test_walk_forward_uses_only_prior_days_and_is_read_only(tmp_path):
    path = tmp_path / "history.sqlite"
    _database(path, [
        ("d1-a", "2026-01-01", "Liga", "A", "D", "FT", 1, 0),
        ("d1-b", "2026-01-01", "Liga", "B", "E", "FT", 0, 0),
        ("d2-a", "2026-01-02", "Liga", "A", "B", "FT", 0, 1),
        ("d2-b", "2026-01-02", "Liga", "A", "C", "FT", 3, 0),
        ("d3-a", "2026-01-03", "Liga", "A", "C", "FT", 2, 1),
    ])
    before = _sha256(path)

    result = evaluate_shark_walk_forward(
        str(path), min_history_matches_per_team=1, min_review_sample=1,
    )

    assert _sha256(path) == before
    assert result["state"] == "REVIEWABLE_DIAGNOSTIC"
    assert result["read_only"] is True
    assert result["validated_for_customer"] is False
    assert result["dated_unique_matches"] == 5
    # d2-a is eligible from d1 only. d2-b cannot use A's d2-a result,
    # and becomes eligible only on d3.
    assert result["eligible_model_evaluations"] == 2
    assert result["model_reference"]["sample_size"] == 2
    assert result["competition_frequency_baseline"]["sample_size"] == 2
    assert result["competition_baseline_evaluations"] == result["eligible_model_evaluations"]
    assert result["comparison_basis"] == "SAME_ELIGIBLE_FIXTURES"
    # D2: 0.20 for an away win; D3: 3/7 for a home win.
    # The warmup days must not be scored in the benchmark.
    import math
    expected_log_loss = round((-math.log(0.2) - math.log(3.0 / 7.0)) / 2, 6)
    assert result["competition_frequency_baseline"]["log_loss"] == expected_log_loss
    assert result["model_reference"]["brier_score"] >= 0
    assert "not a calibrated SHARK forecast" in result["limitations"][0]


def test_duplicate_provider_rows_do_not_inflate_evaluation_sample(tmp_path):
    path = tmp_path / "duplicates.sqlite"
    _database(path, [
        ("copy-a", "2026-01-01", "Liga", "A", "B", "FT", 1, 0),
        ("copy-b", "2026-01-01", "Liga", "A", "B", "FT", 1, 0),
    ])

    result = evaluate_shark_walk_forward(str(path), min_history_matches_per_team=1)

    assert result["matches_read"] == 2
    assert result["dated_unique_matches"] == 1
    assert result["duplicate_rows_collapsed"] == 1
    assert result["incomplete_or_conflicting_rows_excluded"] == 0
    assert result["competition_baseline_evaluations"] == 0
    assert result["competition_frequency_baseline"] is None
    assert result["comparison_basis"] == "SAME_ELIGIBLE_FIXTURES"
    assert result["eligible_model_evaluations"] == 0
    assert result["state"] == "INSUFFICIENT_EVALUATION_SAMPLE"


def test_conflicting_same_fixture_rows_are_excluded(tmp_path):
    path = tmp_path / "conflicts.sqlite"
    _database(path, [
        ("copy-a", "2026-01-01", "Liga", "A", "B", "FT", 1, 0),
        ("copy-b", "2026-01-01", "Liga", "A", "B", "FT", 0, 2),
    ])

    result = evaluate_shark_walk_forward(str(path), min_history_matches_per_team=1)

    assert result["matches_read"] == 2
    assert result["dated_unique_matches"] == 0
    assert result["duplicate_rows_collapsed"] == 0
    assert result["incomplete_or_conflicting_rows_excluded"] == 2
    assert result["state"] == "NO_VALID_DATED_MATCHES"


def test_insufficient_sample_never_marks_forecast_validated(tmp_path):
    path = tmp_path / "small.sqlite"
    _database(path, [
        ("a", "2026-01-01", "Liga", "A", "B", "FT", 0, 0),
        ("b", "2026-01-02", "Liga", "A", "B", "FT", 1, 0),
    ])

    result = evaluate_shark_walk_forward(
        str(path), min_history_matches_per_team=1, min_review_sample=100,
    )

    assert result["state"] == "INSUFFICIENT_EVALUATION_SAMPLE"
    assert result["eligible_model_evaluations"] == 1
    assert result["validated_for_customer"] is False
    assert result["diagnostic_only"] is True
