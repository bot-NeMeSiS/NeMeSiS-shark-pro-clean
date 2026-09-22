"""Reproduce retention with synthetic data, a temporary SQLite DB, no network.

Run from the repository root with: python tools/reproduce_match_record_history.py
Nothing is written to the production DB, GitHub, Render, Telegram or a provider.
"""
from contextlib import closing
import json
from pathlib import Path
import socket
import sqlite3
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

if __package__ in (None, ""):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engines.api_football_live_tracker_engine import ensure_live_tracker_schema, _upsert_statistics, _upsert_events
from tools.inspect_match_record_archive import inspect_archive


def main():
    attempts=[]
    def block(*args,**kwargs):
        attempts.append("blocked_external_connection")
        raise RuntimeError("This reproduction must not use the network")
    snapshots=[]
    with TemporaryDirectory(prefix="nemesis-stats-synthetic-") as folder:
        path=str(Path(folder)/"test.db")
        ensure_live_tracker_schema(path)
        with patch.object(socket.socket,"connect",block), patch.object(socket,"create_connection",block):
            for stamp,corners,goal in [("2026-09-22T18:00:00Z",0,False),("2026-09-22T18:10:00Z",3,True),("2026-09-22T18:12:00Z",2,False)]:
                statistics=[{"team":{"id":10,"name":"SIMULATED_QA Norte"},"statistics":[
                    {"type":"Corner Kicks","value":corners},{"type":"Throw-ins","value":None}]}]
                event_list=[{"time":{"elapsed":40,"extra":None},"team":{"id":10,"name":"SIMULATED_QA Norte"},
                    "player":{"id":9,"name":"SIMULATED_QA Jugador"},"assist":{},"type":"Goal","detail":"Normal Goal"}] if goal else []
                with patch("engines.api_football_live_tracker_engine.utc_stamp",return_value=stamp):
                    with closing(sqlite3.connect(path)) as conn:
                        with conn:
                            _upsert_statistics(conn,"123",statistics)
                            _upsert_events(conn,"123",event_list)
            # Each read reopens the persisted DB. Future corrections cannot appear at an earlier cutoff.
            for stamp in ["2026-09-22T18:00:00Z","2026-09-22T18:10:00Z","2026-09-22T18:12:00Z"]:
                data=inspect_archive(path,"123",as_of=stamp,include_payload=True)
                snapshots.append({"as_of":stamp,"observations":data["observations"],
                    "corners":data["sections"]["statistics"]["payload"][0]["statistics"][0]["value"],
                    "throw_ins":data["sections"]["statistics"]["payload"][0]["statistics"][1]["value"],
                    "events":len(data["sections"]["events"]["payload"])})
    assert [s["corners"] for s in snapshots]==[0,3,2]
    assert [s["events"] for s in snapshots]==[0,1,0]
    assert [s["observations"] for s in snapshots]==[2,4,6]
    assert not attempts
    print(json.dumps({"scope":"SIMULATED_QA_NOT_PRODUCTION","ok":True,
        "external_connection_attempts":len(attempts),"snapshots":snapshots,
        "note":"Counter corrections are not summed; missing throw-ins remain null. Final fixture coverage not inferred."},indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
