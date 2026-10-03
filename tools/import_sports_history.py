"""Explicit offline, append-only import of existing normalized/provider caches.

No environment secrets, production database discovery, network or plan changes.
The database and input cache must both be explicitly selected by the operator.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.sports_history_engine import ensure_schema, ingest_match, sync_existing_details
from engines.sports_history_adapters import sportsdb_event, odds_event


def import_cache(db_path, input_path, provider):
    payload = json.loads(Path(input_path).read_text(encoding='utf-8'))
    items = payload if isinstance(payload, list) else payload.get('events') or payload.get('matches') or []
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        count = 0
        with conn:
            for raw in items:
                item = sportsdb_event(raw) if provider == 'sportsdb' else odds_event(raw) if provider == 'odds' else raw
                ingest_match(conn, item)
                count += 1
        return {'processed': count, 'external_calls': 0}
    finally:
        conn.close()


def import_existing(db_path):
    """Replay existing warehouse before current fixtures, without deleting rows."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    processed = skipped = 0
    try:
        ensure_schema(conn)
        conn.commit()
        for table in ('football_matches_history', 'matches'):
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                continue
            for row in conn.execute('SELECT * FROM ' + table):
                item = dict(row)
                item.update(provider=item.get('provider') or item.get('source') or 'local',
                            external_id=item.get('external_id') or item.get('id'),
                            internal_match_id=item.get('internal_match_id') or (item.get('id') if table == 'matches' else ''),
                            league_id=item.get('league_id') or item.get('competition_id'),
                            league_name=item.get('league_name') or item.get('competition_name'))
                try:
                    with conn:
                        ingest_match(conn,item)
                    processed += 1
                except ValueError:
                    skipped += 1
        with conn:
            details = sync_existing_details(conn)
        return {'processed': processed, 'requires_review': skipped, 'details': details, 'external_calls': 0}
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--input')
    selection.add_argument('--import-existing', action='store_true')
    parser.add_argument('--provider', choices=['normalized', 'sportsdb', 'odds'], default='normalized')
    args = parser.parse_args()
    print(json.dumps(import_existing(args.database) if args.import_existing else import_cache(args.database, args.input, args.provider)))
