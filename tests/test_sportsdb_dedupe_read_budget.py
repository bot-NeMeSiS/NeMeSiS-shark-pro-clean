"""Regression coverage for bounded duplicate cleanup in sports sync."""

from pathlib import Path
import sqlite3


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


def test_duplicate_cleanup_scope_removes_only_duplicates_inside_scope(app_module, monkeypatch):
    import engines.realtime_state_engine as realtime_state_engine

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE matches(
            id TEXT PRIMARY KEY,
            match_date TEXT,
            kickoff_time TEXT,
            competition_name TEXT,
            home_team TEXT,
            away_team TEXT,
            status TEXT,
            source TEXT,
            updated_at TEXT
        )"""
    )
    conn.execute("CREATE TABLE picks(id TEXT PRIMARY KEY, match_id TEXT)")
    conn.execute(
        """CREATE TABLE live_matches(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            status TEXT,
            minute TEXT,
            home_score TEXT,
            away_score TEXT,
            payload_json TEXT,
            source TEXT,
            updated_at TEXT
        )"""
    )
    rows = [
        ("scope-a", "2026-09-30", "20:00", "Liga QA", "Local", "Visitante", "PROGRAMADO", "qa", "2026-09-30T10:00:00+02:00"),
        ("scope-b", "2026-09-30", "20:00", "Liga QA", "Local", "Visitante", "PROGRAMADO", "qa", "2026-09-30T10:01:00+02:00"),
        ("outside-a", "2026-09-27", "21:00", "Liga QA", "Otro", "Rival", "PROGRAMADO", "qa", "2026-09-27T10:00:00+02:00"),
        ("outside-b", "2026-09-27", "21:00", "Liga QA", "Otro", "Rival", "PROGRAMADO", "qa", "2026-09-27T10:01:00+02:00"),
    ]
    conn.executemany(
        """INSERT INTO matches(
            id,match_date,kickoff_time,competition_name,home_team,away_team,status,source,updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()

    monkeypatch.setattr(app_module, "is_fake_match", lambda _item: False)
    monkeypatch.setattr(
        app_module,
        "match_quality_score",
        lambda item: 2 if item.get("id") == "scope-b" else 1,
    )
    monkeypatch.setattr(
        app_module,
        "merge_match_payload",
        lambda primary, duplicate: {**dict(duplicate), **dict(primary)},
    )
    monkeypatch.setattr(
        app_module,
        "canonical_match_status",
        lambda _item: {"is_live": False},
    )
    monkeypatch.setattr(
        realtime_state_engine,
        "_provider_clock",
        lambda _item: ("", "", None),
    )

    try:
        result = app_module.cleanup_duplicate_matches(
            conn.cursor(),
            match_dates=["2026-09-30"],
        )
        conn.commit()
        remaining = {
            row["id"]
            for row in conn.execute("SELECT id FROM matches ORDER BY id").fetchall()
        }
    finally:
        conn.close()

    assert result["duplicates_removed"] == 1
    assert result["groups"] == 1
    assert len({"scope-a", "scope-b"} & remaining) == 1
    assert {"outside-a", "outside-b"} <= remaining
