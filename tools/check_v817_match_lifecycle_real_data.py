from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v817_lifecycle_check.db"))
os.environ.setdefault("START_BACKGROUND_JOBS", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

import app as nemesis_app  # noqa: E402


VERSION = "V817_REFERENCE_PIXEL_POLISH_CLIENT_ADMIN_FINAL"


def main() -> None:
    now = datetime.now(nemesis_app.TZ)
    cases = {
        "futuro": ({"match_date": (now + timedelta(days=1)).date().isoformat(), "kickoff_time": "21:00", "status": "NS"}, "UPCOMING"),
        "live": ({"match_date": now.date().isoformat(), "kickoff_time": (now - timedelta(minutes=12)).strftime("%H:%M"), "status": "1H", "minute": "12", "score": "1-0"}, "LIVE"),
        "finalizado": ({"match_date": (now - timedelta(days=1)).date().isoformat(), "kickoff_time": "20:00", "status": "FT", "score": "2-1"}, "FT"),
        "empezado_sin_score": ({"kickoff_iso": (now - timedelta(minutes=35)).isoformat(), "status": "NS"}, "LIVE_PENDING"),
        "madrugada_pasada": ({"match_date": (now - timedelta(days=1)).date().isoformat(), "kickoff_time": "00:30", "status": "NS"}, "RESULT_PENDING"),
        "pasado_sin_score_api": ({"match_date": (now - timedelta(days=2)).date().isoformat(), "kickoff_time": "18:00", "status": ""}, "RESULT_PENDING"),
    }
    results = {}
    for name, (payload, expected) in cases.items():
        ctx = nemesis_app.client_match_display_context(payload)
        got = nemesis_app.canonical_match_status(payload).get("key")
        results[name] = {
            "expected": expected,
            "got": got,
            "ok": got == expected,
            "label": ctx.get("label"),
            "client_status_label": ctx.get("status_label"),
            "score": ctx.get("score_display"),
        }
    failed = [name for name, result in results.items() if not result["ok"]]
    print(json.dumps({"ok": not failed, "version": VERSION, "cases": results}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()


