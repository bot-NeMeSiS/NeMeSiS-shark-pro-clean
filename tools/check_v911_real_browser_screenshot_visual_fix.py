from __future__ import annotations

import ast
import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V911_REAL_BROWSER_SCREENSHOT_VISUAL_FIX_EXECUTION_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "reports/V911_REAL_BROWSER_SCREENSHOT_VISUAL_FIX_EXECUTION_REPORT.md",
    "reports/V911_BROWSER_QA_ENVIRONMENT_STATUS.md",
    "reports/V911_SCREENSHOT_CAPTURE_RESULTS.md",
    "reports/V911_REFERENCE_COMPARISON_RESULTS.md",
    "reports/V911_VISUAL_FIX_QUEUE_UNBLOCK_REPORT.md",
    "reports/V911_CODEX_OUTBOX_SCREENSHOT_PROMPTS.md",
    "reports/V911_BROWSER_QA_BLOCKED_NEXT_ACTIONS.md",
    "reports/V911_NEXT_STEPS.md",
]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def app_version_from_source(source: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                    if isinstance(node.value, ast.Constant):
                        return str(node.value.value)
    return ""


def load_json(rel: str) -> dict:
    path = ROOT / rel
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def assert_no_raw_secrets(failures: list[str]) -> None:
    scan_paths = [
        ROOT / "tools" / "run_browser_reference_qa.py",
        ROOT / "tools" / "check_browser_qa_environment.py",
        ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "visual_fix_queue.json",
        ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "browser_qa_status.json",
    ] + [ROOT / report for report in REPORTS]
    unsafe = re.compile(r"(secret|token|api_key|apikey|password)=([^\s`'\"&<>)]+)", re.IGNORECASE)
    allowed = {"hidden", "configured", "missing", "***hidden***", "***missing***", "AUTOMATION_SECRET", "$AUTOMATION_SECRET", "..."}
    for path in scan_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in unsafe.finditer(text):
            value = match.group(2).strip(",.;")
            if value in allowed or value.startswith("$") or value.startswith("{") or value.startswith("***") or "AUTOMATION_SECRET" in value:
                continue
            failures.append(f"possible raw secret in {path.relative_to(ROOT)}")


def assert_zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    forbidden = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", "logs/")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    for rel in [
        "app.py",
        "VERSION.txt",
        "APP_VERSION",
        "requirements.txt",
        "tools/check_v911_real_browser_screenshot_visual_fix.py",
    ]:
        require(rel in names, f"zip missing {rel}", failures)
    for name in names:
        normalized = name.replace("\\", "/")
        if normalized.endswith((".zip", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm")) or any(part in normalized for part in forbidden):
            failures.append(f"zip forbidden entry {normalized}")
            break


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(version_bytes.decode("utf-8").strip() == VERSION, "VERSION.txt is not V911", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") == VERSION, "APP_VERSION is not V911", failures)
    require(app_version_from_source(app_py) == VERSION, "app.py APP_VERSION is not V911", failures)
    require("data-v911-shell" in base, "base V911 shell marker missing", failures)
    require("NEMESIS_CACHE_V911" in app_py, "service worker cache is not V911", failures)
    require("v911_real_browser_screenshot_runtime_summary" in app_py, "V911 runtime summary missing", failures)

    for report in REPORTS:
        require((ROOT / report).exists(), f"missing {report}", failures)
    require((ROOT / "reference_images").exists(), "reference_images missing", failures)
    require((ROOT / "reference_images" / "reference_manifest.json").exists(), "reference manifest missing", failures)

    status = load_json("data/runtime/autonomous_company_sentinel/browser_qa_status.json")
    queue = load_json("data/runtime/autonomous_company_sentinel/visual_fix_queue.json")
    comparison = load_json("data/runtime/autonomous_company_sentinel/browser_reference_comparison.json")
    require(status.get("version") == VERSION, "browser QA status version is not V911", failures)
    require(queue.get("version") == VERSION, "visual fix queue version is not V911", failures)
    require(comparison.get("version") == VERSION, "browser comparison version is not V911", failures)

    screenshots = int(status.get("screenshots_captured") or 0)
    items = queue.get("items") if isinstance(queue.get("items"), list) else []
    require(isinstance(items, list) and len(items) >= 1, "visual queue items missing", failures)
    if screenshots == 0:
        require(status.get("can_capture") is False, "screenshots zero but can_capture not false", failures)
        require(queue.get("pixel_perfect_claim_allowed") is False, "pixel-perfect allowed without screenshots", failures)
        require(int(queue.get("blocked_no_screenshot_count") or 0) >= 1, "blocked screenshots count missing", failures)
        require((ROOT / "reports" / "V911_BROWSER_QA_BLOCKED_NEXT_ACTIONS.md").exists(), "blocked next actions report missing", failures)
    else:
        for shot in status.get("screenshots") or []:
            require((ROOT / str(shot)).exists(), f"screenshot path missing: {shot}", failures)

    outbox = read("data/runtime/autonomous_company_sentinel/outbox/codex_outbox.md")
    for section in [
        "V911_SCREENSHOT_CONFIRMED_FIXES",
        "V911_READY_FOR_CODEX",
        "V911_FIXED_SAFE",
        "V911_BLOCKED_NO_SCREENSHOT",
        "V911_NEEDS_HUMAN_VISUAL_REVIEW",
        "V911_DANGEROUS_REQUIRES_APPROVAL",
    ]:
        require(section in outbox, f"outbox section missing: {section}", failures)

    assert_no_raw_secrets(failures)

    os.environ.setdefault("AUTOMATION_SECRET", "codex-v911-local-secret")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json(silent=True) or {}
    require(runtime_resp.status_code == 200, "runtime-version not 200", failures)
    require(runtime.get("version") == VERSION, "runtime version is not V911", failures)
    require(runtime.get("version_files_match") is True, "runtime version_files_match false", failures)
    require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime not aligned", failures)
    for flag in [
        "has_v909_browser_qa_pipeline",
        "has_v910_full_hidden_project_audit",
        "has_v911_real_browser_screenshot_visual_fix",
        "has_v911_browser_qa_execution",
        "has_v911_visual_queue_unblocker",
    ]:
        require(runtime.get(flag) is True, f"runtime flag false: {flag}", failures)
    require(runtime.get("v911_pixel_perfect_claim_allowed") is False, "runtime allows pixel-perfect", failures)
    require(int(runtime.get("v911_screenshots_captured") or 0) == screenshots, "runtime screenshots mismatch", failures)

    require(client.get("/ruta-inventada-v911").status_code == 404, "HTML 404 not 404", failures)
    api_404 = client.get("/api/ruta-inventada-v911")
    require(api_404.status_code == 404 and api_404.is_json, "API 404 JSON missing", failures)
    require(client.get("/service-worker.js").status_code == 200, "service worker not 200", failures)
    require(client.get("/manifest.json").status_code == 200, "manifest not 200", failures)

    assert_zip_clean(failures)
    if failures:
        print("V911 real browser screenshot visual fix check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V911 real browser screenshot visual fix check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
