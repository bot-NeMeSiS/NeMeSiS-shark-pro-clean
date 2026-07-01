from __future__ import annotations

import json
import os
import pathlib
import sys
from datetime import timedelta


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERSION = "V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL"


def fail(message: str, details=None) -> None:
    print(json.dumps({"ok": False, "error": message, "details": details or {}}, ensure_ascii=False, indent=2))
    raise SystemExit(1)


def main() -> None:
    os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v816_lifecycle_check.db"))
    os.environ.setdefault("START_BACKGROUND_JOBS", "false")
    os.environ.setdefault("SCHEDULER_ENABLED", "false")

    import app as nemesis_app  # noqa: WPS433

    now = nemesis_app.datetime.now(nemesis_app.TZ)
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
        info = nemesis_app.canonical_match_status(payload)
        display = nemesis_app.client_match_display_context(dict(payload))
        got = info.get("key")
        results[name] = {
            "expected": expected,
            "got": got,
            "ok": got == expected,
            "label": info.get("label"),
            "client_status_label": display.get("client_status_label"),
            "score": display.get("client_score_label") or "",
        }
    failed = [name for name, result in results.items() if not result["ok"]]
    if failed:
        fail("Fallan casos de ciclo de vida V816: " + ", ".join(failed), results)
    print(json.dumps({"ok": True, "version": VERSION, "cases": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


