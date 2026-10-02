"""Keep actual dedupe reads bounded on a large isolated SQLite queue."""
import ast
import sqlite3
from pathlib import Path

import pytest


def actual_queries():
    tree = ast.parse((Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8'))
    queries = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)
               and isinstance(node.value, str)
               and 'FROM telegram_queue WHERE dedupe_key=?' in node.value]
    assert len(queries) == 3
    return queries


@pytest.mark.parametrize('query', actual_queries())
def test_generated_nonempty_dedupe_key_uses_existing_partial_index(query):
    conn = sqlite3.connect(':memory:')
    try:
        conn.execute('CREATE TABLE telegram_queue(id TEXT, dedupe_key TEXT, status TEXT, sent_at TEXT, created_at TEXT, error_message TEXT)')
        conn.execute("CREATE UNIQUE INDEX idx_telegram_queue_dedupe ON telegram_queue(dedupe_key) WHERE dedupe_key IS NOT NULL AND dedupe_key!=''")
        conn.executemany('INSERT INTO telegram_queue(id,dedupe_key,status,created_at) VALUES(?,?,?,?)',
                         ((str(i), f'SYNTHETIC-{i}', 'sent', '2026-10-02') for i in range(100000)))
        conn.execute("INSERT INTO telegram_queue(id,dedupe_key) VALUES('legacy-empty','')")
        conn.execute("INSERT INTO telegram_queue(id,dedupe_key) VALUES('legacy-null',NULL)")
        plan = ' '.join(str(row) for row in conn.execute('EXPLAIN QUERY PLAN '+query, ('SYNTHETIC-99999',)))
        assert 'SEARCH' in plan and 'idx_telegram_queue_dedupe' in plan
        # A full scan cannot finish within this opcode allowance. No wall-clock assertion.
        def abort_unbounded_scan():
            return 1
        conn.set_progress_handler(abort_unbounded_scan, 500)
        hit = conn.execute(query, ('SYNTHETIC-99999',)).fetchone()
        assert hit[0] == '99999'
        assert conn.execute(query, ('SYNTHETIC-MISSING',)).fetchone() is None
        conn.set_progress_handler(None, 0)
        assert conn.execute('SELECT count(*) FROM telegram_queue').fetchone()[0] == 100002
    finally:
        conn.close()
