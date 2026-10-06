"""Isolated before/after HTTP benchmark, never connects to production.

Run the same script with --repo pointing to the baseline and candidate worktrees.
Fixtures are synthetic QA receipts in disposable local-safe SQLite databases.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sqlite3
import statistics
import sys
import time
import uuid
from zoneinfo import ZoneInfo


def run(repo, output, samples):
    sys.path.insert(0, str(repo))
    os.chdir(repo)
    from tools.run_visual_preview import prepare
    app = prepare(port=54929)
    now = datetime.now(ZoneInfo("Europe/Madrid"))
    conn = app.db()
    for i in range(30):
        kickoff = now - timedelta(minutes=70) if i < 5 else now + timedelta(hours=3, minutes=i)
        conn.execute("""INSERT INTO matches
            (id,external_id,match_date,kickoff_time,match_time,kickoff_iso,competition_id,competition_key,competition_name,league_name,country,home_team,away_team,status,minute,home_score,away_score,score,priority,source,last_synced_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f"phase3-qa-{i}", str(100000+i), kickoff.date().isoformat(), kickoff.strftime("%H:%M"), kickoff.strftime("%H:%M"), kickoff.isoformat(), "140", "laliga", "La Liga", "La Liga", "Spain", "Real Madrid", "Barcelona", "2H" if i < 5 else "NS", "67" if i < 5 else None, 1 if i < 5 else None, 0 if i < 5 else None, "1-0" if i < 5 else None, 95, "api_football_live", (now-timedelta(seconds=15)).isoformat(), now.isoformat()))
    conn.commit()
    conn.close()
    client = app.app.test_client()
    client.get("/local-safe/login/client?token=" + os.environ["NEMESIS_LOCAL_ACCESS_TOKEN"])
    statements = []
    original = sqlite3.connect
    def traced(*args, **kwargs):
        c = original(*args, **kwargs)
        c.set_trace_callback(statements.append)
        return c
    sqlite3.connect = traced
    routes = ("/app", "/calendario", "/directo", "/match/phase3-qa-0", "/shark")
    observations = []
    for route in routes:
        statements.clear()
        start = time.perf_counter()
        response = client.get(route)
        cold_ms = (time.perf_counter()-start)*1000
        cold_queries = len([s for s in statements if s.lstrip().upper().startswith(("SELECT", "PRAGMA"))])
        timings, counts, statuses = [], [], []
        for _ in range(samples):
            statements.clear()
            start = time.perf_counter()
            response = client.get(route)
            timings.append((time.perf_counter()-start)*1000)
            counts.append(len([s for s in statements if s.lstrip().upper().startswith(("SELECT", "PRAGMA"))]))
            statuses.append(response.status_code)
        observations.append({"route": route, "cold_ms": round(cold_ms,2), "cold_queries": cold_queries,
                             "median_ms": round(statistics.median(timings),2), "max_ms": round(max(timings),2),
                             "median_queries": statistics.median(counts), "statuses": sorted(set(statuses))})
    report = {"environment": "SYNTHETIC_LOCAL_SAFE_QA", "fixtures": 30, "samples_per_route": samples,
              "sqlite_trace": "all Python sqlite3 connections; SELECT and PRAGMA", "production_measurement": False,
              "provider_calls": 0, "routes": observations}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=5)
    args = parser.parse_args()
    run(args.repo.resolve(), args.output.resolve(), args.samples)
