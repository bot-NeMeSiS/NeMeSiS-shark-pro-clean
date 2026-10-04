def read_match_record(read_one, match_id):
    """Shared parameterized store lookup; the caller owns its read connection."""
    record = read_one("SELECT * FROM matches WHERE id=?", (match_id,))
    if record is not None:
        return record
    # Existing links to a deduplicated route retain their canonical match.
    import sqlite3
    try:
        alias = read_one("SELECT canonical_id FROM sports_truth_mappings WHERE entity_type='match' AND provider='local_cache' AND provider_id=?", (str(match_id),))
    except sqlite3.OperationalError:
        alias = None  # Existing databases are valid without the additive tables.
    if alias and str(alias.get("canonical_id")) != str(match_id):
        return read_one("SELECT * FROM matches WHERE id=?", (alias["canonical_id"],))
    return None


def observe_persisted_match(db_path, match_id, *, evaluation_time):
    """Internal observer, not an HTTP route or a user-session substitute.

    Reads the existing sports store and the real Match Center projector only.
    Other surface payloads and rendered HTML remain NOT_OBSERVED.
    """
    import sqlite3
    from contextlib import closing
    from pathlib import Path

    from engines.match_context_engine import build_match_context

    result = {
        "state": "NOT_OBSERVED", "reason": "STORE_UNAVAILABLE",
        "match_id": match_id, "store": None, "match_context": None,
        "html": "NOT_OBSERVED",
        "other_surface_payloads": "NOT_OBSERVED",
    }
    path = Path(db_path)
    if not path.is_file():
        return result
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "matches" not in tables:
            return {**result, "reason": "SCHEMA_UNAVAILABLE"}

        def read_one(query, params):
            row = conn.execute(query, params).fetchone()
            return dict(row) if row is not None else None

        record = read_match_record(read_one, match_id)
        canonical_record = record
        if record is not None:
            from engines.unified_sports_truth_store import project_rows
            canonical_record = project_rows(conn, [record], now=evaluation_time, tables=tables)[0]
    if record is None:
        return {**result, "reason": "MATCH_UNAVAILABLE"}
    context = build_match_context({"match": canonical_record}, evaluation_time=evaluation_time)
    return {**result, "state": "OBSERVED_PROJECTOR", "reason": "",
            "store": record, "match_context": context}


def build_sports_hub_payload(date, hub, matches, picks, recommendations, favorites, competitions):
    hub = hub or {}
    return {
        "date": date,
        "today": hub.get("today") or list(matches or [])[:14],
        "live": (hub.get("live") or [])[:10],
        "picks": list(picks or [])[:6],
        "recommendations": list(recommendations or [])[:6],
        "favorites": list(favorites or [])[:8],
        "top_leagues": (hub.get("top_leagues") or list(competitions or []))[:8],
        "counts": hub.get("counts") or {},
    }
