#!/usr/bin/env python3
"""Validate V927 CSS/PWA delivery and the active real-pick gate."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V927_PC_DESKTOP_REFERENCE_PERFECTION_ADMIN_CLIENT_SPORTS_FINAL"
ZIP = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REQUIRED_ROOT = {
    "app.py", "VERSION.txt", "requirements.txt", "templates", "static", "engines",
    "tools", "reports", "reference_images", "browser_qa", "automation_workforce", ".github",
}
FORBIDDEN_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "release_output", "logs"}
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".log", ".zip", ".pyc", ".pyo"}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")


def audit_zip() -> dict:
    if not ZIP.exists():
        return {"exists": False, "forbidden_count": 0, "missing_required_root": sorted(REQUIRED_ROOT)}
    forbidden: set[str] = set()
    top_level: set[str] = set()
    with zipfile.ZipFile(ZIP) as archive:
        for name in archive.namelist():
            path = PurePosixPath(name)
            if not path.parts:
                continue
            top_level.add(path.parts[0])
            if ({part.lower() for part in path.parts} & FORBIDDEN_PARTS) or path.suffix.lower() in FORBIDDEN_SUFFIXES:
                forbidden.add(name)
            if path.name.lower() == ".env":
                forbidden.add(name)
    return {
        "exists": True,
        "forbidden_count": len(forbidden),
        "missing_required_root": sorted(REQUIRED_ROOT - top_level),
    }


def audit_local_pick_counts() -> dict:
    """Read aggregate pick truth from the local DB without allowing writes."""
    database = ROOT / "data" / "database.db"
    if not database.exists():
        return {"available": False, "open_mode": "not_found"}
    today = datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        total = int(connection.execute("SELECT COUNT(*) FROM picks").fetchone()[0])
        published = int(connection.execute(
            "SELECT COUNT(*) FROM picks WHERE lower(COALESCE(status,''))='published'"
        ).fetchone()[0])
        valid = int(connection.execute(
            """SELECT COUNT(*) FROM picks
               WHERE lower(COALESCE(status,''))='published'
                 AND lower(COALESCE(result_status,'pending')) IN ('','pending','open','active','unsettled')
                 AND COALESCE(match_date,'')>=?
                 AND trim(COALESCE(home_team,''))!=''
                 AND trim(COALESCE(away_team,''))!=''
                 AND trim(COALESCE(market,pick_type,''))!=''
                 AND lower(trim(COALESCE(market,pick_type,'')))!='principal'
                 AND trim(COALESCE(selection,''))!=''
                 AND CAST(COALESCE(odds,0) AS REAL)>1.0
                 AND lower(COALESCE(source,'')) NOT LIKE '%fake%'
                 AND lower(COALESCE(source,'')) NOT LIKE '%demo%'
                 AND lower(COALESCE(source,'')) NOT LIKE '%placeholder%'""",
            (today,),
        ).fetchone()[0])
        return {
            "available": True,
            "open_mode": "read_only",
            "today": today,
            "total_rows": total,
            "published_rows": published,
            "active_complete_current_rows": valid,
        }
    finally:
        connection.close()


def main() -> int:
    failures: list[str] = []
    source = read("app.py")
    base = read("templates/base.html")
    css_bytes = (ROOT / "static" / "app.css").read_bytes()
    css = css_bytes.decode("utf-8", errors="replace")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    version_text = version_bytes.decode("utf-8-sig", errors="replace").strip()
    app_match = re.search(r"^APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", source, re.MULTILINE)
    app_version = app_match.group(1) if app_match else ""

    if version_bytes.startswith(b"\xef\xbb\xbf"):
        failures.append("VERSION.txt contains a BOM")
    if version_text != VERSION or app_version != VERSION:
        failures.append("VERSION.txt and APP_VERSION are not aligned to V927")
    if "?v={{ app_version }}" not in base or 'data-cache-version="{{ app_version }}"' not in base:
        failures.append("base.html does not bind app.css to the runtime version")
    if f"NEMESIS_CACHE_V927" not in source:
        failures.append("service worker cache is not V927")
    for marker in ("cache:'no-store'", "cache:'reload'", "keys.map(key=>caches.delete(key))"):
        if marker not in source:
            failures.append(f"service worker missing stale-cache guard: {marker}")
    if "V927 cache delivery fingerprint" not in css:
        failures.append("V927 CSS delivery fingerprint is missing")

    temp_db = Path(tempfile.mkdtemp(prefix="nemesis-v927-css-pwa-")) / "database.sqlite"
    os.environ["DB_PATH"] = str(temp_db)
    os.environ.setdefault("FLASK_ENV", "testing")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
    http = app_module.app.test_client()
    home_response = http.get("/")
    home_html = home_response.get_data(as_text=True)
    expected_css = f"/static/app.css?v={VERSION}"
    if home_response.status_code != 200 or expected_css not in home_html:
        failures.append("rendered home does not load the V927-versioned CSS")

    runtime = http.get("/api/runtime-version").get_json() or {}
    if runtime.get("version") != VERSION or runtime.get("version_files_match") is not True:
        failures.append("local runtime identity is not aligned to V927")
    if runtime.get("static_css_cache_busting") is not True:
        failures.append("runtime reports static_css_cache_busting=false")
    if runtime.get("static_css_hash") != hashlib.sha256(css_bytes).hexdigest()[:16]:
        failures.append("runtime CSS hash does not match static/app.css")
    if runtime.get("service_worker_cache_name") != "NEMESIS_CACHE_V927":
        failures.append("runtime service worker cache name is not V927")
    if runtime.get("service_worker_no_stale_html_css") is not True:
        failures.append("runtime does not confirm the HTML/CSS stale-cache guard")

    sw_response = http.get("/service-worker.js")
    sw_text = sw_response.get_data(as_text=True)
    if sw_response.status_code != 200 or "NEMESIS_CACHE_V927" not in sw_text:
        failures.append("service-worker.js is not serving the V927 cache")
    if "no-store" not in sw_response.headers.get("Cache-Control", ""):
        failures.append("service-worker.js can be cached by the browser/proxy")

    templates = {
        "home": read("templates/home.html"),
        "admin": read("templates/admin_dashboard.html") + read("templates/admin_automation_workforce.html"),
        "client": read("templates/client_app_center.html"),
        "sports": read("templates/calendar.html") + read("templates/live.html") + read("templates/picks.html"),
    }
    for area, text in templates.items():
        if "v927-" not in text:
            failures.append(f"{area} templates do not contain V927 classes")

    future = (datetime.now(app_module.TZ) + timedelta(days=2)).date().isoformat()
    past = (datetime.now(app_module.TZ) - timedelta(days=2)).date().isoformat()
    valid = {
        "id": "valid-real-pick",
        "home_team": "Real Madrid",
        "away_team": "Sevilla",
        "match_date": future,
        "market": "Resultado final 1X2",
        "selection": "Real Madrid",
        "odds": 1.75,
        "status": "published",
        "result_status": "pending",
        "source": "admin_reviewed",
    }
    invalid_cases = [
        {**valid, "id": "expired", "match_date": past},
        {**valid, "id": "settled", "result_status": "won"},
        {**valid, "id": "closed", "status": "won"},
        {**valid, "id": "no-market", "market": ""},
        {**valid, "id": "no-selection", "selection": ""},
        {**valid, "id": "no-odds", "odds": 0},
        {**valid, "id": "finished", "match_status": "FT"},
        {**valid, "id": "placeholder", "source": "placeholder"},
    ]
    safe = app_module.get_safe_picks_context([valid, *invalid_cases])
    if [item.get("id") for item in safe.get("picks") or []] != ["valid-real-pick"]:
        failures.append("pick truth gate accepts expired, closed or incomplete picks")
    fallback_market = app_module.normalize_pick_row({**valid, "id": "fallback-market", "market": "", "pick_type": ""})
    if app_module.get_safe_picks_context([fallback_market]).get("picks"):
        failures.append("pick truth gate accepts a generated fallback market")

    zip_audit = audit_zip()
    if not zip_audit["exists"] or zip_audit["forbidden_count"] or zip_audit["missing_required_root"]:
        failures.append("V927 ZIP audit is not clean")

    result = {
        "ok": not failures,
        "version": VERSION,
        "failures": failures,
        "static_css_cache_busting": runtime.get("static_css_cache_busting"),
        "static_css_hash": runtime.get("static_css_hash"),
        "service_worker_cache_name": runtime.get("service_worker_cache_name"),
        "service_worker_no_stale_html_css": runtime.get("service_worker_no_stale_html_css"),
        "rendered_css_href": expected_css,
        "synthetic_pick_gate": {
            "input": 1 + len(invalid_cases),
            "active_complete": len(safe.get("picks") or []),
            "blocked": safe.get("blocked_count"),
            "blocked_reasons": safe.get("blocked_reasons"),
        },
        "local_pick_database_audit": audit_local_pick_counts(),
        "zip_audit": zip_audit,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
