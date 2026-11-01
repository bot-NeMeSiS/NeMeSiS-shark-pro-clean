"""Bounded, query-only fixture reads without sorting opaque provider payloads.

The caller owns the connection and begins one read transaction before schema
observations. ``order_sql`` is trusted SQL assembled by the existing reader,
never a request parameter. Admission, LIMIT, full row contents and result order
are unchanged. Unsupported schemas and query plans use the original query.
"""
from __future__ import annotations

import sqlite3


def read_match_rows(conn, order_sql: str, query_params) -> list[dict]:
    """Sort physical keys, then fetch full selected rows in the same snapshot."""
    original = 'SELECT * FROM "matches"' + order_sql + ' LIMIT ?'
    params = tuple(query_params)

    def original_rows():
        return [dict(row) for row in conn.execute(original, params).fetchall()]

    if not conn.in_transaction or not order_sql or int(params[-1]) <= 0:
        return original_rows()
    getlimit = getattr(conn, "getlimit", None)
    if not callable(getlimit) or not hasattr(sqlite3, "SQLITE_LIMIT_VARIABLE_NUMBER"):
        return original_rows()
    variable_limit = getlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER)
    if variable_limit < 1:
        return original_rows()

    # Older SQLite versions can return no rows for an unknown PRAGMA. Views,
    # virtual tables and WITHOUT ROWID tables never use physical-key selection.
    tables = conn.execute('PRAGMA main.table_list("matches")').fetchall()
    if len(tables) != 1:
        return original_rows()
    table = tables[0]
    if (len(table) < 5 or table[0] != "main" or table[1] != "matches"
            or table[2] != "table" or table[4] != 0):
        return original_rows()
    # Materialization adds one result column for the physical key. A valid
    # SELECT * at SQLite's column limit must retain the original read path.
    if int(table[3]) + 1 > getlimit(sqlite3.SQLITE_LIMIT_COLUMN):
        return original_rows()
    # table_xinfo includes generated columns that could shadow a hidden alias.
    columns = {
        str(row[1]).casefold()
        for row in conn.execute('PRAGMA main.table_xinfo("matches")').fetchall()
    }
    alias = next((name for name in ("_rowid_", "rowid", "oid") if name not in columns), None)
    if not columns or alias is None:
        return original_rows()

    # Index scans can reorder equal sort keys. Require the original full scan
    # and temp sorter, then retain that scan order explicitly. Unknown EXPLAIN
    # formats fall back; real SQLite errors propagate to the caller unchanged.
    details = [str(row[3]) for row in conn.execute("EXPLAIN QUERY PLAN " + original, params)]
    if details != ["SCAN matches", "USE TEMP B-TREE FOR ORDER BY"]:
        return original_rows()
    selected = [row[0] for row in conn.execute(
        f'SELECT "{alias}" FROM "matches" NOT INDEXED{order_sql} LIMIT ?', params
    ).fetchall()]
    found = {}
    chunk_size = min(200, variable_limit)
    for offset in range(0, len(selected), chunk_size):
        chunk = selected[offset:offset + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        sql = f'SELECT "{alias}", * FROM "matches" WHERE "{alias}" IN ({placeholders})'
        for row in conn.execute(sql, tuple(chunk)).fetchall():
            key = row[0]
            if key in found:
                raise sqlite3.OperationalError("duplicate physical key in fixture read")
            found[key] = dict(zip(row.keys()[1:], tuple(row)[1:]))
    if len(found) != len(selected) or any(key not in found for key in selected):
        raise sqlite3.OperationalError("fixture snapshot changed during selected read")
    return [found[key] for key in selected]
