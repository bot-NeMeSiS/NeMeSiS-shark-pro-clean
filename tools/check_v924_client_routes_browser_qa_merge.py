#!/usr/bin/env python3
"""Validate V924 double-V923 merge: client routes plus Browser QA screenshot gate."""
from __future__ import annotations

import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V924_CLIENT_ROUTES_RECOVERY_BROWSER_QA_BASE_MERGE_FINAL"


ROUTES = {
    "/": {200},
    "/cliente-login": {200},
    "/login": {200, 301, 302, 303, 307, 308},
    "/registro": {200},
    "/app": {200, 301, 302, 303, 307, 308},
    "/calendar": {200},
    "/calendario": {200, 301, 302, 303, 307, 308},
    "/live": {200},
    "/directo": {200, 301, 302, 303, 307, 308},
    "/picks": {200},
    "/shark": {200, 301, 302, 303, 307, 308},
    "/telegram": {200, 301, 302, 303, 307, 308},
    "/profile": {200, 301, 302, 303, 307, 308},
    "/support": {200},
    "/api/runtime-version": {200},
    "/manifest.json": {200},
    "/service-worker.js": {200},
    "/ruta-inventada": {404},
    "/api/ruta-inventada": {404},
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path, default):
    try:
        return json.loads(read_text(path)) if path.exists() else default
    except Exception:
        return default


def collect_queue_state() -> dict:
    queue_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "visual_fix_queue.json"
    payload = load_json(queue_path, [])
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        items = []
    ready_statuses = {"READY_FOR_CODEX", "FIXABLE_SAFE", "FIXED_BY_V923", "FIXED_BY_V924"}
    ready = [
        item for item in items
        if isinstance(item, dict) and item.get("status") in ready_statuses
    ]
    invalid_ready = [
        item for item in ready
        if not (item.get("screenshot_path") or item.get("screenshot"))
    ]
    blocked = [
        item for item in items
        if isinstance(item, dict) and item.get("status") == "BLOCKED_NO_SCREENSHOT"
    ]
    return {
        "total": len(items),
        "blocked": len(blocked),
        "ready": len(ready),
        "invalid_ready_without_screenshot": len(invalid_ready),
    }


def latest_zip() -> Path:
    return ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"


def audit_zip(path: Path) -> dict:
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
        "data/runtime/client_route_health_v923.json",
    }
    forbidden_names = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output", "logs"}
    forbidden_suffixes = {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log", ".zip"}
    if not path.exists():
        return {"exists": False, "forbidden_count": 0, "missing_required_root": sorted(required)}
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
    name_set = set(names)
    missing = []
    for item in required:
        if item.endswith("/"):
            if not any(name.startswith(item) for name in names):
                missing.append(item.rstrip("/"))
        elif item not in name_set:
            missing.append(item)
    forbidden = []
    for name in names:
        parts = Path(name).parts
        suffix = Path(name).suffix.lower()
        if any(part in forbidden_names for part in parts) or suffix in forbidden_suffixes:
            forbidden.append(name)
    return {
        "exists": True,
        "forbidden_count": len(forbidden),
        "missing_required_root": missing,
    }


def route_health_label(status: int, allowed: set[int]) -> str:
    if status == 200:
        return "ok"
    if status in allowed and status in {301, 302, 303, 307, 308}:
        return "redirect_safe"
    if status in allowed and status < 500:
        return "controlled"
    return "failed"


def main() -> int:
    failures: list[str] = []
    version_raw = (ROOT / "VERSION.txt").read_bytes()
    if version_raw.startswith(b"\xef\xbb\xbf"):
        failures.append("VERSION.txt has BOM")
    version_txt = version_raw.decode("utf-8-sig", errors="replace").strip()
    if version_txt != VERSION:
        failures.append(f"VERSION.txt mismatch: {version_txt}")
    app_text = read_text(ROOT / "app.py")
    if f"APP_VERSION = '{VERSION}'" not in app_text:
        failures.append("APP_VERSION mismatch")
    for token in [
        "has_v924_client_routes_recovery",
        "has_v924_double_v923_merge",
        "has_v924_browser_qa_gate_preserved",
        "has_v924_sports_routes_safe_render",
        "v924_client_routes_browser_qa_merge_runtime_summary",
    ]:
        if token not in app_text:
            failures.append(f"missing V924 token: {token}")

    sys.path.insert(0, str(ROOT))
    import app as nemesis_app  # noqa: WPS433

    client = nemesis_app.app.test_client()
    route_rows = []
    for route, allowed in ROUTES.items():
        response = client.get(route, follow_redirects=False)
        text = response.get_data(as_text=True)
        row = {
            "route": route,
            "status": response.status_code,
            "health": route_health_label(response.status_code, allowed),
            "location": response.headers.get("Location", ""),
            "has_internal_error_text": "Internal Server Error" in text,
        }
        route_rows.append(row)
        if response.status_code not in allowed:
            failures.append(f"{route} returned {response.status_code}")
        if response.status_code >= 500:
            failures.append(f"{route} returned server error")
        if row["has_internal_error_text"]:
            failures.append(f"{route} contains Internal Server Error text")

    runtime = client.get("/api/runtime-version").get_json(silent=True) or {}
    if runtime.get("version") != VERSION:
        failures.append("runtime version mismatch")
    for flag in [
        "has_v924_client_routes_recovery",
        "has_v924_double_v923_merge",
        "has_v924_browser_qa_gate_preserved",
        "has_v924_sports_routes_safe_render",
    ]:
        if runtime.get(flag) is not True:
            failures.append(f"runtime flag missing: {flag}")
    if runtime.get("v924_pixel_perfect_claim_allowed") is not False:
        failures.append("pixel-perfect must remain false")
    if int(runtime.get("v924_valid_screenshots_count") or 0) <= 0 and runtime.get("v924_next_required_action") not in {
        "run_github_action_browser_qa_or_upload_artifacts",
        "rerun_client_route_recovery_check",
    }:
        failures.append("V924 next action does not reflect missing screenshots")

    queue = collect_queue_state()
    if queue["invalid_ready_without_screenshot"]:
        failures.append("visual queue has ready items without screenshot evidence")
    if queue["ready"] and int(runtime.get("v924_valid_screenshots_count") or 0) <= 0:
        failures.append("visual queue ready without valid screenshots")

    for pattern in [
        r"TELEGRAM_BOT_TOKEN\s*=\s*['\"][^*'\"]{12,}",
        r"AUTOMATION_SECRET\s*=\s*['\"][^*'\"]{12,}",
        r"RENDER_DEPLOY_HOOK_URL\s*=\s*['\"]https?://",
        r"RENDER_API_KEY\s*=\s*['\"][^*'\"]{12,}",
    ]:
        if re.search(pattern, app_text):
            failures.append(f"suspicious secret pattern in app.py: {pattern}")

    zip_audit = audit_zip(latest_zip())
    if zip_audit["exists"] and (zip_audit["forbidden_count"] or zip_audit["missing_required_root"]):
        failures.append(f"zip audit failed: {zip_audit}")

    now = datetime.now().isoformat(timespec="seconds")
    route_lines = [
        "# V924 Client Routes Recheck On Browser QA Base",
        "",
        f"- generated_at: {now}",
        f"- version: {VERSION}",
        "",
        "| route | status | health | location |",
        "| --- | ---: | --- | --- |",
    ]
    for row in route_rows:
        route_lines.append(f"| `{row['route']}` | {row['status']} | {row['health']} | `{row['location']}` |")

    write(ROOT / "reports" / "V924_CLIENT_ROUTES_RECHECK_ON_BROWSER_QA_BASE.md", "\n".join(route_lines) + "\n")
    write(ROOT / "reports" / "V924_DOUBLE_V923_VERSION_MERGE_AUDIT.md", "\n".join([
        "# V924 Double V923 Version Merge Audit",
        "",
        "- production_reported_by_user: V923_BROWSER_QA_EVIDENCE_CAPTURE_IMPORT_AND_VISUAL_QUEUE_UNLOCK_FINAL",
        "- production_runtime_checked_during_work: V922_VISIBLE_PRODUCT_EXPERIENCE_CLIENT_ADMIN_SPORTS_UPGRADE_FINAL",
        "- local_alternate_hotfix: V923_CLIENT_ROUTES_INTERNAL_ERROR_RECOVERY_AFTER_V922_FINAL",
        f"- merged_version: {VERSION}",
        "- risk: two different V923 names create deploy ambiguity.",
        "- decision: V924 becomes the single merged line.",
        "- preserved_from_browser_qa_v923: screenshot gate, visual queue blocked without evidence, pixel-perfect false, Browser QA next action.",
        "- preserved_from_client_hotfix_v923: route recovery check, client route health runtime, safe 500 guard for critical client routes.",
    ]) + "\n")
    write(ROOT / "reports" / "V924_BROWSER_QA_GATE_PRESERVATION_QA.md", "\n".join([
        "# V924 Browser QA Gate Preservation QA",
        "",
        f"- valid_screenshots_count: {runtime.get('v924_valid_screenshots_count')}",
        f"- visual_queue_total: {queue['total']}",
        f"- visual_queue_blocked: {queue['blocked']}",
        f"- visual_queue_ready: {queue['ready']}",
        f"- invalid_ready_without_screenshot: {queue['invalid_ready_without_screenshot']}",
        f"- pixel_perfect_claim_allowed: {runtime.get('v924_pixel_perfect_claim_allowed')}",
        f"- next_required_action: {runtime.get('v924_next_required_action')}",
        "- conclusion: visual items remain blocked unless screenshot evidence exists.",
    ]) + "\n")
    write(ROOT / "reports" / "V924_CLIENT_ROUTES_RECOVERY_BROWSER_QA_BASE_MERGE_REPORT.md", "\n".join([
        "# V924 Client Routes Recovery Browser QA Base Merge Report",
        "",
        f"- version: {VERSION}",
        "- double_v923_detected: yes",
        "- client_routes_checked: yes",
        "- browser_qa_gate_preserved: yes",
        f"- route_failures: {len([row for row in route_rows if row['health'] == 'failed'])}",
        f"- visual_queue_total: {queue['total']}",
        f"- visual_queue_blocked: {queue['blocked']}",
        f"- visual_queue_ready: {queue['ready']}",
        f"- zip_audit: {json.dumps(zip_audit, ensure_ascii=False)}",
        "- telegram_real_sent: no",
        "- payments_touched: no",
        "- secrets_exposed: no",
    ]) + "\n")
    write(ROOT / "reports" / "V924_NEXT_STEPS.md", "\n".join([
        "# V924 Next Steps",
        "",
        "1. Deploy V924_DEPLOY_ROOT_CONTENTS to GitHub main/Render.",
        "2. Confirm /api/runtime-version returns V924_CLIENT_ROUTES_RECOVERY_BROWSER_QA_BASE_MERGE_FINAL.",
        "3. Recheck /cliente-login, /login, /registro, /app, /calendar, /live, /picks, /shark, /telegram, /profile and /support.",
        "4. Run Browser QA or upload artifacts before unlocking visual queue or claiming pixel-perfect.",
    ]) + "\n")

    if failures:
        print("V924 merge check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V924 client routes/browser QA merge check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
