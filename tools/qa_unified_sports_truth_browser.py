"""Real local HTTP + Chromium checks for Phase 3, with synthetic QA receipts."""
import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(output, chromium):
    from tools.run_visual_preview import prepare
    from engines.unified_sports_truth_store import persist_receipt
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server
    module = prepare(port=54928)
    now = datetime.now(ZoneInfo("Europe/Madrid"))
    conn = module.db()
    for index, status in enumerate(("2H", "NS", "FT", "PST", "CANC", "SUSP")):
        kickoff = now + timedelta(hours=2) if status == "NS" else now-timedelta(minutes=70)
        data = {"id": f"truth-browser-{index}", "external_id": str(99000+index), "source": "api_football_live", "home_team": "Real Madrid", "away_team": "Barcelona", "competition_id": "140", "competition_key": "laliga", "competition_name": "La Liga", "league_name": "La Liga", "country": "Spain", "kickoff_iso": kickoff.isoformat(), "match_date": kickoff.date().isoformat(), "kickoff_time": kickoff.strftime("%H:%M"), "match_time": kickoff.strftime("%H:%M"), "status": status, "minute": "67" if status == "2H" else None, "home_score": 1 if status in {"2H", "FT"} else None, "away_score": 0 if status in {"2H", "FT"} else None, "score": "1-0" if status in {"2H", "FT"} else "", "priority": 95, "last_synced_at": (now-timedelta(seconds=5)).isoformat(), "updated_at": now.isoformat()}
        conn.execute(f"INSERT INTO matches({','.join(data)}) VALUES({','.join('?' for _ in data)})", tuple(data.values()))
        persist_receipt(conn, data["id"], data, provider="api_football")
        if status == "2H":
            persist_receipt(conn, data["id"], {**data, "source": "thesportsdb", "external_id": "conflicting-db", "status": "FT", "home_score": 2, "away_score": 2, "score": "2-2", "minute": 90}, provider="thesportsdb")
    conn.commit()
    conn.close()
    server = make_server("127.0.0.1", 0, module.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=str(chromium), headless=True)
            for width, height in ((1366, 900), (390, 844)):
                context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce", service_workers="block")
                context.route("**/*", lambda route: route.continue_() if urlparse(route.request.url).hostname in {"127.0.0.1", "localhost"} else route.abort())
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base + "/local-safe/login/client?token=" + os.environ["NEMESIS_LOCAL_ACCESS_TOKEN"])
                for route in ("/app", "/calendario", "/directo", "/match/truth-browser-0", "/shark"):
                    errors.clear()
                    response = page.goto(base + route, wait_until="load", timeout=60000)
                    page.evaluate("document.fonts.ready")
                    inspection = page.evaluate("""() => ({overflow:document.documentElement.scrollWidth>innerWidth+2, width:innerWidth,
                        technicalCopy:['NO_STATISTICS','NO_VIDEO','TTL_EXPIRED','PLAN_RESTRICTED','api_football','sqlite3.'].filter(s=>document.body.innerText.includes(s)),
                        states:[...document.querySelectorAll('[data-canonical-status]')].map(e=>e.dataset.canonicalStatus),
                        mainCount:document.querySelectorAll('main').length})""")
                    name = f"{width}-{route.strip('/').replace('/', '-')}.png"
                    page.screenshot(path=str(output / name), full_page=True)
                    row = {"route": route, "status": response.status, "width": width, "js_errors": list(errors), "screenshot": name, **inspection}
                    rows.append(row)
                    print(json.dumps(row), flush=True)
                context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
    failures = [r for r in rows if r["overflow"] or r["technicalCopy"] or r["js_errors"] or r["status"] != 200 or r["mainCount"] != 1]
    report = {"environment": "SYNTHETIC_LOCAL_SAFE_QA", "transport": "REAL_FLASK_HTTP_SOCKET", "provider_calls": 0, "observations": rows, "failures": failures}
    (output / "observations.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return int(bool(failures))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chromium", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.output.resolve(), args.chromium))
