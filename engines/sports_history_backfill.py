"""Explicit season backfill using the existing configured SportsDB transport.

No new scheduler, keys, plan settings or render-time provider calls. A successful
season response remains partial: provider windows/limits are not completeness.
"""
import re
import sqlite3
import time

from engines.sports_history_engine import backfill_page, ensure_schema, ingest_match
from engines.sports_history_adapters import sportsdb_event


def season_request(league_id, season):
    league_id, season = str(league_id), str(season).strip()
    if not re.fullmatch(r'[1-9][0-9]{0,9}',league_id):
        raise ValueError('A SportsDB league ID is required')
    if not re.fullmatch(r'[0-9]{4}(?:-[0-9]{4})?',season):
        raise ValueError('An explicit season label is required')
    return dict(source='thesportsdb',scope=league_id + '/' + season,page='season',endpoint='eventsseason.php',params={'id':league_id,'s':season})


def run_season_backfill(db_path, league_id, season, *, budget, timestamp=None, transport=None, configured=None, ttl=86400):
    request = season_request(league_id,season)
    if transport is None:
        from engines.sportsdb_enrichment_engine import _sportsdb_v1, _api_key
        transport = _sportsdb_v1
        configured = bool(_api_key())
    if configured is False:
        return dict(status='not_configured',calls=0,scope=request['scope'])
    def fetch(scope,page):
        payload = transport(request['endpoint'],request['params'])
        if not isinstance(payload,dict) or not isinstance(payload.get('events'),list):
            raise ValueError('Season response unavailable')
        normalized = []
        for event in payload['events']:
            if not isinstance(event,dict) or str(event.get('idLeague') or '') != str(league_id) or event.get('strSeason') != str(season).strip():
                raise ValueError('Unexpected season response scope')
            normalized.append(sportsdb_event(event))
        return normalized
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        conn.commit()
        return backfill_page(conn,request['source'],request['scope'],request['page'],fetch,ingest_match,
                             budget=budget,timestamp=time.time() if timestamp is None else timestamp,ttl=ttl)
    finally:
        conn.close()
