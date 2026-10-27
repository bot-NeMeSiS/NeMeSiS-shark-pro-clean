"""Tipster ROI uses exactly the decided, fully verified cohort, read-only."""
import hashlib
import sqlite3

from engines.tipster_evidence_engine import audited_tipster_kpis


def _db(path, picks=(), grades=()):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE picks(id TEXT PRIMARY KEY, status TEXT)")
    conn.execute("""CREATE TABLE pick_grading_results(
        id TEXT PRIMARY KEY, pick_id TEXT, graded_at TEXT,
        result_status TEXT, odds REAL, stake REAL, profit REAL, auto_validated INTEGER
    )""")
    conn.executemany("INSERT INTO picks VALUES (?,?)", picks)
    conn.executemany("INSERT INTO pick_grading_results VALUES (?,?,?,?,?,?,?,?)", grades)
    conn.commit()
    conn.close()


def _grade(label, pick, result, odds, stake, profit, validated=1, when="2026-01-01"):
    return (label, pick, when, result, odds, stake, profit, validated)


def test_missing_database_does_not_create_it(tmp_path):
    path = tmp_path / "missing.sqlite"
    result = audited_tipster_kpis(str(path))
    assert result["roi"] is None
    assert result["state"] == "DATABASE_NOT_FOUND"
    assert not path.exists()


def test_win_loss_only_excludes_pending_void_and_draft(tmp_path):
    path = tmp_path / "settled.sqlite"
    _db(path, [
        ("a", "published"), ("b", "won"), ("v", "void"),
        ("p", "pending"), ("draft", "draft")
    ], [
        _grade("w", "a", "won", 2.0, 2.0, 2.0),
        _grade("l", "b", "lost", 3.0, 2.0, -2.0),
        _grade("v", "v", "void", 1.9, 9.0, 0.0),
        _grade("p", "p", "pending", 2.0, 9.0, None),
        _grade("d", "draft", "lost", 2.0, 10.0, -10.0),
    ])
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    result = audited_tipster_kpis(str(path))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert result["state"] == "CERTIFIED_SETTLEMENT_SAMPLE"
    assert result["decided_count"] == result["certified_count"] == 2
    assert result["stake_units"] == 4.0
    assert result["profit_units"] == 0.0
    assert result["roi"] == 0.0
    assert result["winrate"] == 50.0


def test_missing_or_inconsistent_profit_fails_closed(tmp_path):
    path = tmp_path / "partial.sqlite"
    _db(path, [("a", "published"), ("b", "published")], [
        _grade("w", "a", "won", 2.0, 1.0, 1.0),
        _grade("bad", "b", "lost", 2.0, 2.0, None),
    ])
    result = audited_tipster_kpis(str(path))
    assert result["state"] == "INCOMPLETE_SETTLEMENT_EVIDENCE"
    assert result["certified_count"] == 1
    assert result["decided_count"] == 2
    assert result["roi"] is None
    assert result["winrate"] is None


def test_uncertified_or_contradictory_grade_cannot_certify_roi(tmp_path):
    path = tmp_path / "manual.sqlite"
    _db(path, [("a", "published"), ("b", "published")], [
        _grade("a", "a", "won", 2.0, 1.0, -1.0),
        _grade("b", "b", "lost", 2.0, 1.0, -1.0, validated=0),
    ])
    result = audited_tipster_kpis(str(path))
    assert result["state"] == "INCOMPLETE_SETTLEMENT_EVIDENCE"
    assert result["roi"] is None


def test_latest_evaluation_wins_and_negative_roi_is_real(tmp_path):
    path = tmp_path / "latest.sqlite"
    _db(path, [("a", "published")], [
        _grade("older", "a", "won", 2.0, 1.0, 1.0, when="2026-01-01"),
        _grade("newer", "a", "lost", 2.0, 1.0, -1.0, when="2026-01-02"),
    ])
    result = audited_tipster_kpis(str(path))
    assert result["decided_count"] == 1
    assert result["roi"] == -100.0
    assert result["winrate"] == 0.0


def test_corrupt_numeric_fields_are_not_silently_coerced(tmp_path):
    path = tmp_path / "corrupt.sqlite"
    _db(path, [("a", "published")], [
        _grade("bad", "a", "won", "nan", -2, 50),
    ])
    result = audited_tipster_kpis(str(path))
    assert result["roi"] is None
    assert result["state"] == "INCOMPLETE_SETTLEMENT_EVIDENCE"

def test_decided_pick_without_grade_blocks_the_roi_cohort(tmp_path):
    path = tmp_path / "ungraded-loss.sqlite"
    _db(path, [("win", "won"), ("lost", "lost")], [
        _grade("w", "win", "won", 2.0, 1.0, 1.0),
    ])
    result = audited_tipster_kpis(str(path))
    assert result["state"] == "INCOMPLETE_SETTLEMENT_EVIDENCE"
    assert result["decided_count"] == 2
    assert result["certified_count"] == 1
    assert result["roi"] is None
    assert result["winrate"] is None


def test_terminal_status_disagreement_is_not_automatically_certified(tmp_path):
    path = tmp_path / "contradictory.sqlite"
    _db(path, [("pick", "perdido")], [
        _grade("graded", "pick", "won", 2.0, 1.0, 1.0),
    ])
    result = audited_tipster_kpis(str(path))
    assert result["decided_count"] == 1
    assert result["certified_count"] == 0
    assert result["roi"] is None


def test_voided_pick_with_stale_win_grade_does_not_inflate_roi(tmp_path):
    path = tmp_path / "voided.sqlite"
    _db(path, [("pick", "void")], [
        _grade("outdated", "pick", "won", 2.0, 1.0, 1.0),
    ])
    result = audited_tipster_kpis(str(path))
    assert result["state"] == "INCOMPLETE_SETTLEMENT_EVIDENCE"
    assert result["roi"] is None


def test_grade_without_timestamp_cannot_certify_history(tmp_path):
    path = tmp_path / "undated.sqlite"
    _db(path, [("pick", "won")], [
        _grade("undated", "pick", "won", 2.0, 1.0, 1.0, when=None),
    ])
    result = audited_tipster_kpis(str(path))
    assert result["decided_count"] == 1
    assert result["certified_count"] == 0
    assert result["roi"] is None


def test_pending_pick_without_grade_does_not_block_settled_cohort(tmp_path):
    path = tmp_path / "pending.sqlite"
    _db(path, [("pick", "won"), ("other", "pending")], [
        _grade("settled", "pick", "won", 2.0, 1.0, 1.0),
    ])
    result = audited_tipster_kpis(str(path))
    assert result["state"] == "CERTIFIED_SETTLEMENT_SAMPLE"
    assert result["decided_count"] == result["certified_count"] == 1
    assert result["roi"] == 100.0
