"""Provider status reads use synthetic SQLite only, without network or app setup."""

from contextlib import closing
import json
import socket
import sqlite3
from threading import Event, Thread
from urllib.parse import parse_qs, urlsplit

import pytest

from engines import api_sports_provider_engine as provider


COUNT_FIELDS = ("fixtures_cached", "live_cached", "events_cached", "stats_cached")
COUNT_TABLES = (
    "api_football_fixture_index",
    "api_football_live_snapshots",
    "api_football_live_events",
    "api_football_live_stats",
)
METADATA_TABLES = ("api_football_live_sync_state", "api_exploitation_runs")
KEY_NAMES = ("API_FOOTBALL_KEY", "API_FOOTBALL_API_KEY", "API_SPORTS_KEY", "APISPORTS_KEY")
QA_KEY = "synthetic-provider-key-never-publish"
SYNC_AT = "2026-10-21T10:00:00Z"


@pytest.fixture(autouse=True)
def isolated_configuration_and_no_network(monkeypatch):
    for name in KEY_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("API_FOOTBALL_KEY", QA_KEY)
    monkeypatch.setenv("ENABLE_API_FOOTBALL_PROVIDER", "true")

    def deny(*args, **kwargs):
        raise AssertionError("Provider status tests must not use the network")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(provider.urllib.request, "urlopen", deny)


def make_db(path, counts=(5, 3, 2, 4), *, metadata=True):
    with closing(sqlite3.connect(path)) as conn, conn:
        for table, count in zip(COUNT_TABLES, counts):
            conn.execute(f"CREATE TABLE {table}(id INTEGER PRIMARY KEY)")
            conn.executemany(f"INSERT INTO {table}(id) VALUES (?)", ((n,) for n in range(count)))
        conn.execute("CREATE TABLE api_football_live_sync_state(last_sync_at TEXT, error TEXT)")
        conn.execute("CREATE TABLE api_exploitation_runs(id INTEGER PRIMARY KEY, finished_at TEXT, error_message TEXT)")
        if metadata:
            conn.executemany(
                "INSERT INTO api_football_live_sync_state VALUES (?, ?)",
                [("2026-10-20T10:00:00Z", "older sync error"), (SYNC_AT, "sync\nprovider error")],
            )
            # The latest run is newer than sync_state; source precedence remains unchanged.
            conn.executemany(
                "INSERT INTO api_exploitation_runs VALUES (?, ?, ?)",
                [(1, "2099-01-01T00:00:00Z", "older run id"), (2, "2026-10-22T10:00:00Z", "latest run error")],
            )
    return path


@pytest.fixture
def db(tmp_path):
    return make_db(tmp_path / "provider-status.db")


def assert_unknown(result, state, *, ok=False):
    assert result["ok"] is ok
    assert all(result[field] is None for field in COUNT_FIELDS)
    assert result["tables_detected"] is None
    assert result["last_sync"] == result["last_error"] == ""
    assert result["read_state"] == state
    assert isinstance(result["read_error"], str)
    if state == "NOT_REQUESTED":
        assert result["read_error"] == ""
    else:
        assert result["read_error"]
    assert QA_KEY not in json.dumps(result)


@pytest.mark.parametrize("path", [None, ""])
def test_configuration_only_does_not_connect_or_claim_known_counts(path, monkeypatch):
    calls = []

    def unexpected_connect(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("Configuration-only status must not open storage")

    monkeypatch.setattr(provider.sqlite3, "connect", unexpected_connect)
    result = provider.get_api_sports_status(path)
    assert_unknown(result, "NOT_REQUESTED", ok=True)
    assert calls == []


@pytest.mark.parametrize(
    "key_name, enabled, configured, football_configured, active",
    [
        (None, "true", False, False, "not_configured"),
        ("API_FOOTBALL_KEY", "true", True, True, "api-sports/api-football"),
        ("API_SPORTS_KEY", "true", True, False, "api-sports/api-football"),
        ("API_FOOTBALL_KEY", "false", True, True, "configured_disabled"),
    ],
)
def test_configuration_flags_remain_independent_of_storage(
    monkeypatch, key_name, enabled, configured, football_configured, active
):
    for name in KEY_NAMES:
        monkeypatch.delenv(name, raising=False)
    if key_name:
        monkeypatch.setenv(key_name, QA_KEY)
    monkeypatch.setenv("ENABLE_API_FOOTBALL_PROVIDER", enabled)
    result = provider.get_api_sports_status()
    assert_unknown(result, "NOT_REQUESTED", ok=True)
    assert result["api_sports_configured"] is configured
    assert result["api_football_configured"] is football_configured
    assert result["api_sports_provider_available"] is (configured and enabled == "true")
    assert result["provider_active"] == active
    assert result["api_sports_cache_enabled"] is True
    assert result["api_sports_credit_guard_enabled"] is True
    assert result["usage_guard"]["no_page_render_calls"] is True


@pytest.mark.parametrize("counts", [(0, 0, 0, 0), (2, 5, 3, 4), (5, 2, 3, 4)])
def test_success_preserves_zero_max_count_and_metadata_precedence(tmp_path, counts):
    path = make_db(tmp_path / "counts.db", counts)
    before = path.read_bytes()
    result = provider.get_api_sports_status(str(path))
    assert result["ok"] is True and result["read_state"] == "READY"
    assert result["read_error"] == ""
    assert tuple(result[field] for field in COUNT_FIELDS) == (max(counts[:2]), *counts[1:])
    assert all(type(result[field]) is int for field in COUNT_FIELDS)
    assert set(result["tables_detected"]) == set(COUNT_TABLES + METADATA_TABLES)
    assert result["last_sync"] == SYNC_AT
    assert result["last_error"] == "syncprovider error"
    assert path.read_bytes() == before


@pytest.mark.parametrize("sync_table_present", [True, False])
def test_metadata_falls_back_to_latest_run_id_when_sync_evidence_is_absent(tmp_path, sync_table_present):
    path = make_db(tmp_path / "fallback.db", metadata=False)
    with closing(sqlite3.connect(path)) as conn, conn:
        if sync_table_present:
            conn.execute("INSERT INTO api_football_live_sync_state VALUES ('', '')")
        else:
            conn.execute("DROP TABLE api_football_live_sync_state")
        conn.executemany(
            "INSERT INTO api_exploitation_runs VALUES (?, ?, ?)",
            [(1, "2099-01-01T00:00:00Z", "older id"), (2, SYNC_AT, "fallback error")],
        )
    result = provider.get_api_sports_status(str(path))
    assert result["ok"] is True and result["read_state"] == "READY"
    assert result["last_sync"] == SYNC_AT
    assert result["last_error"] == "fallback error"


def test_absent_table_is_a_known_zero_without_initializing_it(db):
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("DROP TABLE api_football_live_stats")
    before = db.read_bytes()
    result = provider.get_api_sports_status(str(db))
    assert result["ok"] is True and result["read_state"] == "READY"
    assert result["stats_cached"] == 0
    assert result["fixtures_cached"] == 5
    assert "api_football_live_stats" not in result["tables_detected"]
    assert db.read_bytes() == before


def test_valid_database_without_provider_tables_has_known_zero_counts(tmp_path):
    path = tmp_path / "unrelated.db"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE unrelated(id INTEGER)")
    before = path.read_bytes()
    result = provider.get_api_sports_status(str(path))
    assert result["ok"] is True and result["read_state"] == "READY"
    assert all(type(result[field]) is int and result[field] == 0 for field in COUNT_FIELDS)
    assert result["tables_detected"] == []
    assert result["last_sync"] == result["last_error"] == ""
    assert path.read_bytes() == before


@pytest.mark.parametrize("relative", ["missing-private.db", "missing-folder/private.db"])
def test_missing_database_is_unknown_and_never_created(tmp_path, relative):
    path = tmp_path / relative
    result = provider.get_api_sports_status(str(path))
    assert not path.exists()
    assert_unknown(result, "NOT_INITIALIZED")
    assert result["api_sports_configured"] is True
    assert str(path) not in json.dumps(result)
    assert "private.db" not in json.dumps(result)


@pytest.mark.parametrize("kind", ["corrupt", "directory"])
def test_unreadable_storage_is_unknown_without_exposing_path_or_provider_error(tmp_path, kind):
    path = tmp_path / "private-storage-location"
    path.mkdir() if kind == "directory" else path.write_bytes(b"not a SQLite database")
    result = provider.get_api_sports_status(str(path))
    assert_unknown(result, "READ_UNAVAILABLE")
    assert "private-storage-location" not in json.dumps(result)


def test_partial_query_failure_discards_every_storage_field_and_closes_connection(db, monkeypatch):
    original = sqlite3.connect
    connections = []
    completed_counts = []

    class FailSecondCount(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if "COUNT(" in sql.upper().replace(" ", ""):
                if completed_counts:
                    raise sqlite3.OperationalError("PRIVATE_READ_SENTINEL token=DO_NOT_ECHO")
                cursor = super().execute(sql, parameters)
                completed_counts.append(sql)
                return cursor
            return super().execute(sql, parameters)

    def watched(*args, **kwargs):
        conn = original(*args, **{**kwargs, "factory": FailSecondCount})
        connections.append(conn)
        return conn

    monkeypatch.setattr(provider.sqlite3, "connect", watched)
    result = provider.get_api_sports_status(str(db))
    assert len(completed_counts) == 1
    assert_unknown(result, "READ_UNAVAILABLE")
    assert "PRIVATE_READ_SENTINEL" not in json.dumps(result)
    assert "DO_NOT_ECHO" not in json.dumps(result)
    for conn in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            conn.execute("SELECT 1")


def test_success_uses_read_only_uri_query_only_snapshot_and_closes_connection(db, monkeypatch):
    original = sqlite3.connect
    connections, statements, opened = [], [], []

    def watched(*args, **kwargs):
        opened.append((args, kwargs))
        conn = original(*args, **kwargs)
        conn.set_trace_callback(statements.append)
        connections.append(conn)
        return conn

    monkeypatch.setattr(provider.sqlite3, "connect", watched)
    result = provider.get_api_sports_status(str(db))
    assert result["ok"] is True
    assert len(opened) == 1
    args, kwargs = opened[0]
    uri = str(args[0] if args else kwargs["database"])
    assert kwargs.get("uri") is True
    assert parse_qs(urlsplit(uri).query).get("mode") == ["ro"]
    normalized = ["".join(sql.upper().split()) for sql in statements]
    assert any(sql in {"PRAGMAQUERY_ONLY=ON", "PRAGMAQUERY_ONLY=1"} for sql in normalized)
    assert any(sql.startswith("BEGIN") for sql in normalized)
    assert not any(sql.startswith(("CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE", "REPLACE")) for sql in normalized)
    for conn in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            conn.execute("SELECT 1")


def test_sqlite_uri_handles_spaces_and_hash_without_opening_a_different_file(tmp_path):
    path = make_db(tmp_path / "provider # status with spaces.db")
    before = sorted(p.name for p in tmp_path.iterdir())
    result = provider.get_api_sports_status(str(path))
    assert result["ok"] is True and result["read_state"] == "READY"
    assert result["fixtures_cached"] == 5
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_reader_keeps_one_snapshot_when_another_writer_commits_between_counts(db, monkeypatch):
    original = sqlite3.connect
    with closing(original(db)) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    wrote = []

    def update_after_first_count():
        if wrote:
            return
        with closing(original(db)) as writer, writer:
            for table in COUNT_TABLES:
                writer.execute(f"INSERT INTO {table}(id) VALUES (9999)")
            writer.execute("UPDATE api_football_live_sync_state SET last_sync_at='2030-01-01T00:00:00Z', error='new snapshot'")
        wrote.append(True)

    class AfterCountCursor:
        def __init__(self, cursor):
            self.cursor = cursor

        def fetchone(self):
            row = self.cursor.fetchone()
            update_after_first_count()
            return row

        def fetchall(self):
            rows = self.cursor.fetchall()
            update_after_first_count()
            return rows

        def __getattr__(self, name):
            return getattr(self.cursor, name)

    class ConcurrentWriter(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            cursor = super().execute(sql, parameters)
            if "COUNT(" in sql.upper().replace(" ", "") and not wrote:
                return AfterCountCursor(cursor)
            return cursor

    monkeypatch.setattr(provider.sqlite3, "connect", lambda *a, **kw: original(*a, **{**kw, "factory": ConcurrentWriter}))
    result = provider.get_api_sports_status(str(db))
    assert wrote == [True]
    assert tuple(result[field] for field in COUNT_FIELDS) == (5, 3, 2, 4)
    assert result["ok"] is True and result["read_state"] == "READY"
    assert result["last_sync"] == SYNC_AT
    assert result["last_error"] == "syncprovider error"
    with closing(original(db)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM api_football_live_snapshots").fetchone()[0] == 4


def test_total_read_budget_uses_monotonic_elapsed_time_across_queries(db, monkeypatch):
    original = sqlite3.connect
    clock = [100.0]
    consumed = []

    class ConsumeBudget(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            cursor = super().execute(sql, parameters)
            if sql.lstrip().upper().startswith("SELECT") and not consumed:
                clock[0] += 0.301
                consumed.append(True)
            return cursor

    monkeypatch.setattr(provider.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(provider.sqlite3, "connect", lambda *a, **kw: original(*a, **{**kw, "factory": ConsumeBudget}))
    result = provider.get_api_sports_status(str(db))
    assert consumed == [True]
    assert_unknown(result, "READ_UNAVAILABLE")


def test_exclusive_lock_returns_unknown_before_the_writer_releases_it(db):
    locked, release, finished = Event(), Event(), Event()
    results, errors = [], []

    def hold_exclusive_lock():
        try:
            with closing(sqlite3.connect(db)) as conn:
                conn.execute("BEGIN EXCLUSIVE")
                locked.set()
                release.wait()
                conn.rollback()
        except BaseException as exc:
            errors.append(exc)
            locked.set()

    def read_status():
        try:
            results.append(provider.get_api_sports_status(str(db)))
        except BaseException as exc:
            errors.append(exc)
        finally:
            finished.set()

    writer = Thread(target=hold_exclusive_lock, daemon=True)
    reader = Thread(target=read_status, daemon=True)
    writer.start()
    completed_while_locked = False
    try:
        assert locked.wait(2), "SQLite lock setup did not finish"
        assert not errors
        reader.start()
        # Operational tolerance, not a millisecond performance benchmark.
        completed_while_locked = finished.wait(2)
    finally:
        release.set()
        writer.join(2)
        if reader.ident is not None:
            reader.join(2)
    assert not writer.is_alive() and not reader.is_alive()
    assert not errors
    assert completed_while_locked, "Status reader waited for lock release instead of exhausting its own budget"
    assert len(results) == 1
    assert_unknown(results[0], "READ_UNAVAILABLE")


def test_explanation_reuses_snapshot_and_distinguishes_local_read_failure(db, monkeypatch):
    ready = provider.get_api_sports_status(str(db))
    unavailable = {**ready, "ok": False, "read_state": "READ_UNAVAILABLE", "read_error": "LOCAL_READ_FAILED", "last_sync": "", "last_error": "", "tables_detected": None}
    unavailable.update({field: None for field in COUNT_FIELDS})
    historical_provider_error = {**ready, "last_error": "historical provider error"}
    original_snapshot = json.loads(json.dumps(unavailable))

    def unexpected_read(*args, **kwargs):
        raise AssertionError("Explanation must reuse the supplied status snapshot")

    monkeypatch.setattr(provider, "get_api_sports_status", unexpected_read)
    explanation = provider.explain_api_sports_provider_state(str(db), status=unavailable)
    provider_explanation = provider.explain_api_sports_provider_state(status=historical_provider_error)
    assert explanation["status"] == unavailable == original_snapshot
    assert explanation["label"] != provider_explanation["label"]
    assert explanation["message"]
    assert provider.explain_api_sports_provider_state(status={})["status"] == {}
