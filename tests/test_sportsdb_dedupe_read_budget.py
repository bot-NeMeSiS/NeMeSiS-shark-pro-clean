"""Regression coverage for bounded duplicate cleanup in sports sync."""

from pathlib import Path


class RecordingCursor:
    def __init__(self):
        self.calls = []
        self._last_query = ""

    def execute(self, query, params=()):
        self._last_query = str(query)
        self.calls.append((str(query), tuple(params or ())))
        return self

    def fetchall(self):
        if "PRAGMA table_info(matches)" in self._last_query:
            return [
                (0, "id"),
                (1, "match_date"),
                (2, "kickoff_time"),
                (3, "home_team"),
                (4, "away_team"),
                (5, "competition_name"),
                (6, "status"),
                (7, "priority"),
                (8, "source"),
                (9, "updated_at"),
            ]
        return []


def test_duplicate_cleanup_can_scope_read_to_touched_dates(app_module):
    cur = RecordingCursor()

    result = app_module.cleanup_duplicate_matches(
        cur,
        match_dates=["2026-10-01", "bad", "2026-09-30", "2026-09-30"],
    )

    assert result == {"duplicates_removed": 0, "groups": 0}
    selects = [(query, params) for query, params in cur.calls if "SELECT * FROM matches" in query]
    assert len(selects) == 1
    query, params = selects[0]
    assert "WHERE match_date IN (?,?)" in query
    assert params == ("2026-09-30", "2026-10-01")


def test_duplicate_cleanup_empty_explicit_scope_never_falls_back_to_full_scan(app_module):
    cur = RecordingCursor()

    result = app_module.cleanup_duplicate_matches(cur, match_dates=[])

    assert result == {"duplicates_removed": 0, "groups": 0}
    assert not any("SELECT * FROM matches" in query for query, _params in cur.calls)


def test_duplicate_cleanup_default_full_mode_is_preserved(app_module):
    cur = RecordingCursor()

    result = app_module.cleanup_duplicate_matches(cur)

    assert result == {"duplicates_removed": 0, "groups": 0}
    selects = [(query, params) for query, params in cur.calls if "SELECT * FROM matches" in query]
    assert len(selects) == 1
    query, params = selects[0]
    assert "WHERE match_date IN" not in query
    assert params == ()


def test_sportsdb_upsert_uses_scoped_duplicate_cleanup():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app.py").read_text(encoding="utf-8")
    start = source.index("def _upsert_sportsdb_matches_transaction")
    end = source.index("\n\ndef sportsdb_reconciliation_status", start)
    block = source[start:end]

    assert "touched_match_dates = set()" in block
    assert 'item.get("match_date") or today_iso()' in block
    assert "for offset in (-1, 0, 1)" in block
    assert "timedelta(days=offset)" in block
    assert "cleanup_duplicate_matches(cur, match_dates=touched_match_dates)" in block
    assert "cleanup_duplicate_matches(cur)" not in block
