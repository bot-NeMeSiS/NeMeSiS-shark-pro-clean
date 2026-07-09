from __future__ import annotations

import ast
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V921_AUTOMATED_BROWSER_QA_ARTIFACT_RUN_IMPORT_AND_VISUAL_QUEUE_UNLOCK_FINAL"
COMPATIBLE_VERSION_PREFIXES = ("V921_", "V922_")
QUEUE = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "visual_fix_queue.json"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return default


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def app_version(source: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                    return str(getattr(node.value, "value", ""))
    return ""


def screenshot_valid(value: str) -> bool:
    if not value:
        return False
    path = (ROOT / value).resolve()
    try:
        return ROOT.resolve() in path.parents and path.exists() and path.is_file() and path.stat().st_size > 0
    except Exception:
        return False


def zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = [name.replace("\\", "/") for name in zf.namelist()]
    for rel in [
        "app.py",
        "VERSION.txt",
        "APP_VERSION",
        "tools/import_browser_qa_results.py",
        "tools/run_browser_reference_qa.py",
        "tools/check_v921_browser_qa_artifact_run.py",
        ".github/workflows/browser-qa.yml",
        "data/runtime/autonomous_company_sentinel/visual_fix_queue.json",
    ]:
        require(rel in names, f"zip missing {rel}", failures)
    forbidden_bits = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", "logs/")
    for name in names:
        if name.endswith((".zip", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm")) or any(bit in name for bit in forbidden_bits):
            failures.append(f"zip forbidden entry {name}")
            break


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    template = read("templates/admin_automation_workforce.html")
    importer = read("tools/import_browser_qa_results.py")
    workflow = read(".github/workflows/browser-qa.yml")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    local_version = version_bytes.decode("utf-8").strip()

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(local_version.startswith(COMPATIBLE_VERSION_PREFIXES), "VERSION.txt is not V921/V922 compatible", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff").startswith(COMPATIBLE_VERSION_PREFIXES), "APP_VERSION is not V921/V922 compatible", failures)
    require(app_version(app_py).startswith(COMPATIBLE_VERSION_PREFIXES), "app.py APP_VERSION is not V921/V922 compatible", failures)
    require("NEMESIS_CACHE_V921" in app_py or "NEMESIS_CACHE_V922" in app_py, "service worker cache V921/V922 missing", failures)
    for flag in [
        "has_v921_automated_browser_qa_artifact_run",
        "has_v921_browser_qa_import_execution",
        "has_v921_visual_queue_evidence_unlock",
        "has_v921_screenshot_evidence_gate",
    ]:
        require(flag in app_py, f"runtime flag missing: {flag}", failures)

    for report in [
        "reports/V921_AUTOMATED_BROWSER_QA_ARTIFACT_RUN_REPORT.md",
        "reports/V921_BROWSER_QA_ENVIRONMENT_DECISION.md",
        "reports/V921_PLAYWRIGHT_INSTALL_ATTEMPT.md",
        "reports/V921_LOCAL_BROWSER_QA_RUN_REPORT.md",
        "reports/V921_GITHUB_ACTION_BROWSER_QA_RUN_OR_INSTRUCTIONS.md",
        "reports/V921_BROWSER_QA_ARTIFACT_IMPORT_REPORT.md",
        "reports/V921_VISUAL_QUEUE_UNLOCK_WITH_EVIDENCE_QA.md",
        "reports/V921_CODEX_OUTBOX_SCREENSHOT_EVIDENCE_QA.md",
        "reports/V921_ADMIN_BROWSER_QA_STATUS_QA.md",
        "reports/V921_NEXT_STEPS.md",
    ]:
        require((ROOT / report).exists(), f"missing report {report}", failures)

    require("workflow_dispatch" in workflow, "Browser QA workflow is not manual-ready", failures)
    require("playwright install chromium" in workflow, "Browser QA workflow does not install Chromium", failures)
    require("reports/browser_qa_render" in workflow, "Browser QA workflow does not upload render artifacts", failures)
    require("v921_import_status" in importer and "valid_image" in importer, "importer does not expose V921 screenshot validation", failures)
    require("v921-browser-qa-artifact-run-panel" in template, "admin panel missing V921 artifact run panel", failures)

    queue_payload = load_json(QUEUE, {})
    queue = queue_payload.get("items") if isinstance(queue_payload, dict) else queue_payload
    require(isinstance(queue, list), "visual queue is not list/items payload", failures)
    invalid_ready = []
    invalid_fixed = []
    for item in queue if isinstance(queue, list) else []:
        if not isinstance(item, dict):
            continue
        shot = str(item.get("screenshot_path") or item.get("screenshot") or "")
        status = item.get("status")
        if status in {"READY_FOR_CODEX", "FIXABLE_SAFE"} and not screenshot_valid(shot):
            invalid_ready.append(item.get("id") or item.get("route"))
        if status == "FIXED_BY_V921" and (not screenshot_valid(shot) or not item.get("v921_evidence")):
            invalid_fixed.append(item.get("id") or item.get("route"))
    require(not invalid_ready, f"READY/FIXABLE items without valid screenshot: {invalid_ready[:5]}", failures)
    require(not invalid_fixed, f"FIXED_BY_V921 items without evidence: {invalid_fixed[:5]}", failures)

    for text in [app_py, template, importer, workflow]:
        for term in ["sk_live_", "xoxb-", "ghp_", "rnd_", "TELEGRAM_BOT_TOKEN=", "RENDER_DEPLOY_HOOK_URL=https://"]:
            require(term not in text, f"possible secret term found: {term}", failures)
        require("pixel_perfect_claim_allowed\": true" not in text and "pixel-perfect aprobado" not in text.lower(), "pixel-perfect claimed without screenshots", failures)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    runtime = client.get("/api/runtime-version")
    payload = runtime.get_json(silent=True) or {}
    require(runtime.status_code == 200, "runtime-version not 200", failures)
    require(str(payload.get("version") or "").startswith(COMPATIBLE_VERSION_PREFIXES), "runtime version is not V921/V922 compatible", failures)
    require(payload.get("has_v921_automated_browser_qa_artifact_run") is True, "runtime V921 run flag false", failures)
    require(payload.get("has_v921_browser_qa_import_execution") is True, "runtime V921 import flag false", failures)
    require(payload.get("has_v921_visual_queue_evidence_unlock") is True, "runtime V921 unlock flag false", failures)
    require(payload.get("has_v921_screenshot_evidence_gate") is True, "runtime V921 evidence flag false", failures)
    require(payload.get("v921_pixel_perfect_claim_allowed") is False, "pixel-perfect should be false", failures)
    if int(payload.get("v921_valid_screenshots_count") or 0) == 0:
        require(payload.get("v921_next_required_action") == "run_github_action_browser_qa_or_upload_artifacts", "runtime next action should request GitHub Action/artifacts", failures)
        require(int(payload.get("v921_visual_queue_ready") or 0) == 0, "visual queue ready should be 0 without screenshots", failures)

    zip_clean(failures)
    if failures:
        print("V921 Browser QA artifact run check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V921 Browser QA artifact run check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
