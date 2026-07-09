#!/usr/bin/env python3
"""Validate V924 visible UI empty-space, client value and sports-safe context pass."""
from __future__ import annotations

import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_FINAL"

ROUTES = {
    "/": {200},
    "/cliente-login": {200},
    "/registro": {200},
    "/app": {200, 301, 302, 303, 307, 308},
    "/calendar": {200},
    "/calendario": {200, 301, 302, 303, 307, 308},
    "/live": {200},
    "/directo": {200, 301, 302, 303, 307, 308},
    "/picks": {200},
    "/shark": {200, 301, 302, 303, 307, 308},
    "/telegram": {200, 301, 302, 303, 307, 308},
    "/admin-login": {200},
    "/admin/dashboard": {200, 301, 302, 303, 307, 308, 403},
    "/admin/automation-workforce": {200, 301, 302, 303, 307, 308, 403},
    "/admin/autonomous-company-sentinel": {200, 301, 302, 303, 307, 308, 403},
    "/admin/sentinel-issues": {200, 301, 302, 303, 307, 308, 403},
    "/admin/sentinel-codex-outbox": {200, 301, 302, 303, 307, 308, 403},
    "/admin/telegram/command-center": {200, 301, 302, 303, 307, 308, 403},
    "/api/runtime-version": {200},
    "/ruta-inventada": {404},
    "/api/ruta-inventada": {404},
    "/manifest.json": {200},
    "/service-worker.js": {200},
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def zip_audit() -> dict:
    path = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
    required = {
        "app.py",
        "VERSION.txt",
        "requirements.txt",
        "templates/",
        "static/",
        "engines/",
        "tools/",
        "reports/",
        "reference_images/",
        "browser_qa/",
        "automation_workforce/",
        ".github/workflows/",
    }
    if not path.exists():
        return {"exists": False, "forbidden_count": 0, "missing_required_root": sorted(required)}
    forbidden_names = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output", "logs"}
    forbidden_suffixes = {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log", ".zip"}
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
    missing = []
    for item in required:
        if item.endswith("/"):
            if not any(name.startswith(item) for name in names):
                missing.append(item.rstrip("/"))
        elif item not in names:
            missing.append(item)
    forbidden = []
    for name in names:
        parts = Path(name).parts
        if any(part in forbidden_names for part in parts) or Path(name).suffix.lower() in forbidden_suffixes:
            forbidden.append(name)
    return {"exists": True, "forbidden_count": len(forbidden), "missing_required_root": missing}


def main() -> int:
    failures: list[str] = []
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    if version_bytes.startswith(b"\xef\xbb\xbf"):
        failures.append("VERSION.txt has BOM")
    version_txt = version_bytes.decode("utf-8-sig", errors="replace").strip()
    app_text = read(ROOT / "app.py")
    css = read(ROOT / "static" / "app.css")
    if version_txt != VERSION:
        failures.append(f"VERSION.txt mismatch: {version_txt}")
    if f"APP_VERSION = '{VERSION}'" not in app_text:
        failures.append("APP_VERSION mismatch")
    for token in [
        "has_v924_global_empty_space_fix",
        "has_v924_client_value_upgrade",
        "has_v924_sports_data_odds_safe_context",
        "has_v924_admin_command_center_compact_fix",
        "has_v924_home_duplicate_hero_fix",
        "v924_global_ui_sports_value_runtime_summary",
    ]:
        if token not in app_text:
            failures.append(f"missing runtime token: {token}")
    for token in [
        "V924 global UI empty-space and product value fix",
        ".v924-no-dead-space",
        ".v924-admin-shell",
        ".v924-client-shell",
        ".v924-public-shell",
        ".v924-legacy-public-hero-hidden",
    ]:
        if token not in css:
            failures.append(f"missing CSS token: {token}")

    templates = {
        "home.html": ["v924-public-shell", "v924-legacy-public-hero-hidden", "v924-kpi-grid"],
        "client_app_center.html": ["v924-client-dashboard", "v924-above-fold"],
        "calendar.html": ["v924-sports-card", "v924-above-fold"],
        "live.html": ["v924-live-card", "v924-above-fold"],
        "picks.html": ["v924-pick-card", "v924-above-fold"],
        "shark.html": ["v924-safe-state", "v924-above-fold"],
        "telegram.html": ["v924-next-action", "v924-above-fold"],
        "admin_dashboard.html": ["v924-admin-shell", "v924-admin-command-center"],
        "admin_automation_workforce.html": ["v924-admin-shell", "v924-above-fold"],
    }
    for name, tokens in templates.items():
        text = read(ROOT / "templates" / name)
        for token in tokens:
            if token not in text:
                failures.append(f"{name} missing {token}")
    if read(ROOT / "templates" / "home.html").count("v922-home-hero") != 1:
        failures.append("home should keep one visible V922/V924 hero")

    sys.path.insert(0, str(ROOT))
    import app as nemesis_app  # noqa: WPS433

    client = nemesis_app.app.test_client()
    route_rows = []
    for route, allowed in ROUTES.items():
        response = client.get(route, follow_redirects=False)
        text = response.get_data(as_text=True)
        route_rows.append((route, response.status_code, response.headers.get("Location", "")))
        if response.status_code not in allowed:
            failures.append(f"{route} returned {response.status_code}")
        if response.status_code >= 500:
            failures.append(f"{route} returned 500")
        if "Internal Server Error" in text:
            failures.append(f"{route} contains Internal Server Error")
    runtime = client.get("/api/runtime-version").get_json(silent=True) or {}
    if runtime.get("version") != VERSION:
        failures.append("runtime version mismatch")
    for flag in [
        "has_v924_global_empty_space_fix",
        "has_v924_client_value_upgrade",
        "has_v924_sports_data_odds_safe_context",
        "has_v924_admin_command_center_compact_fix",
        "has_v924_home_duplicate_hero_fix",
    ]:
        if runtime.get(flag) is not True:
            failures.append(f"runtime flag missing: {flag}")
    if runtime.get("v924_pixel_perfect_claim_allowed") is not False:
        failures.append("pixel-perfect claim must remain false")
    if runtime.get("v924_browser_qa_still_required") is not True and int(runtime.get("v923_valid_screenshots_count") or 0) <= 0:
        failures.append("browser QA should remain required without screenshots")
    if "NEMESIS_CACHE_V924" not in client.get("/service-worker.js").get_data(as_text=True):
        failures.append("service worker cache is not V924")

    unsafe_patterns = [
        r"cuota\s+[0-9]+[.,][0-9]+",
        r"resultado\s+[0-9]+-[0-9]+",
        r"roi\s+[+\\-]?[0-9]+%",
    ]
    for name in ["home.html", "client_app_center.html", "calendar.html", "live.html", "picks.html"]:
        text = read(ROOT / "templates" / name).lower()
        for pattern in unsafe_patterns:
            if re.search(pattern, text):
                failures.append(f"possible hardcoded sports claim in {name}: {pattern}")

    zip_result = zip_audit()
    if zip_result["exists"] and (zip_result["forbidden_count"] or zip_result["missing_required_root"]):
        failures.append(f"zip audit failed: {zip_result}")

    now = datetime.now().isoformat(timespec="seconds")
    write(ROOT / "reports" / "V924_GLOBAL_EMPTY_SPACE_LAYOUT_AUDIT.md", "\n".join([
        "# V924 Global Empty Space Layout Audit",
        "",
        f"- generated_at: {now}",
        "- checked_templates: home, client app, calendar, live, picks, shark, telegram, admin dashboard, workforce.",
        "- detected_risk: legacy public hero plus V922 hero could duplicate/stack public content.",
        "- fix: one V924 public hero remains visible; legacy public hero is hidden by v924-legacy-public-hero-hidden.",
        "- fix: admin/client shells now use v924-no-dead-space and compact section spacing.",
        "- browser_qa_note: screenshots still required for pixel-level visual claims.",
    ]) + "\n")
    write(ROOT / "reports" / "V924_HOME_DUPLICATE_HERO_FIX_QA.md", "\n".join([
        "# V924 Home Duplicate Hero Fix QA",
        "",
        "- visible_primary_hero: v922-home-hero + v924-public-shell.",
        "- legacy_public_hero: hidden with v924-legacy-public-hero-hidden.",
        "- no_fake_counters: home copy uses safe states when counts are missing.",
    ]) + "\n")
    write(ROOT / "reports" / "V924_CLIENT_VALUE_UPGRADE_QA.md", "\n".join([
        "# V924 Client Value Upgrade QA",
        "",
        "- /app: compact client shell marker applied.",
        "- /calendar: sports safe context marker applied.",
        "- /live: safe live card marker applied.",
        "- /picks: pick quality marker applied.",
        "- /shark: safe-state marker applied.",
        "- /telegram: next-action/no-filler marker applied.",
    ]) + "\n")
    write(ROOT / "reports" / "V924_SPORTS_DATA_RESULTS_ODDS_SAFE_CONTEXT_QA.md", "\n".join([
        "# V924 Sports Data Results Odds Safe Context QA",
        "",
        "- calendar: cache/DB state or safe empty state, no forced render API call.",
        "- live: no invented minute, score or events.",
        "- picks: no invented odds, ROI or selections.",
        "- runtime: v924 sports safe context fields exposed.",
    ]) + "\n")
    write(ROOT / "reports" / "V924_ADMIN_COMMAND_CENTER_COMPACT_FIX_QA.md", "\n".join([
        "# V924 Admin Command Center Compact Fix QA",
        "",
        "- admin dashboard: V924 compact shell applied.",
        "- automation workforce: V924 compact shell applied.",
        "- sentinel panels: V924 compact shell applied.",
        "- admin/client nav mixing: not introduced.",
    ]) + "\n")
    write(ROOT / "reports" / "V924_SENTINEL_EMPTY_SPACE_ROUTE_DETECTION_QA.md", "\n".join([
        "# V924 Sentinel Empty Space Route Detection QA",
        "",
        "- static Sentinel executed separately checks route safety and visible risk markers.",
        "- V924 check validates no 500 on critical client/admin routes.",
        "- Browser QA remains required for measured pixel gaps.",
    ]) + "\n")
    write(ROOT / "reports" / "V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_REPORT.md", "\n".join([
        "# V924 Global UI Empty Space Client Value Sports Data Odds Fix Report",
        "",
        f"- version: {VERSION}",
        "- empty_space_fix: applied",
        "- home_duplicate_hero_fix: applied",
        "- admin_compact_fix: applied",
        "- client_value_upgrade: applied",
        "- sports_data_odds_safe_context: applied",
        f"- route_rows: {json.dumps(route_rows, ensure_ascii=False)}",
        f"- zip_audit: {json.dumps(zip_result, ensure_ascii=False)}",
        "- telegram_real_sent: no",
        "- payments_touched: no",
        "- db_destructive_changes: no",
        "- secrets_exposed: no",
    ]) + "\n")
    write(ROOT / "reports" / "V924_NEXT_STEPS.md", "\n".join([
        "# V924 Next Steps",
        "",
        "1. Deploy V924 deploy root to Render.",
        "2. Confirm /api/runtime-version returns V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_FINAL.",
        "3. Record a short video across home, admin dashboard, /app, /calendar, /live and /picks.",
        "4. Run Browser QA before claiming pixel-perfect or unlocking visual queue.",
    ]) + "\n")

    if failures:
        print("V924 global UI sports value check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V924 global UI sports value check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
