from __future__ import annotations

import ast
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V919_BROWSER_QA_RESULTS_IMPORT_VALIDATION_AND_VISUAL_QUEUE_GATE_FINAL"
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
    for rel in ["app.py", "VERSION.txt", "APP_VERSION", "tools/import_browser_qa_results.py", "data/runtime/autonomous_company_sentinel/visual_fix_queue.json"]:
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
    outbox = read("data/runtime/autonomous_company_sentinel/outbox/codex_outbox.md")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    local_version = version_bytes.decode("utf-8").strip()

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(local_version == VERSION, "VERSION.txt is not V919", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") == VERSION, "APP_VERSION is not V919", failures)
    require(app_version(app_py) == VERSION, "app.py APP_VERSION is not V919", failures)
    require("NEMESIS_CACHE_V919" in app_py, "service worker cache V919 missing", failures)
    for flag in ["has_v919_browser_qa_results_validation", "has_v919_visual_queue_screenshot_gate", "has_v919_outbox_evidence_gate"]:
        require(flag in app_py, f"runtime flag missing: {flag}", failures)
    require("NO_VALID_SCREENSHOTS_TO_IMPORT" in importer and "valid_image" in importer, "importer does not validate screenshots", failures)
    require("v919-browser-qa-gate-panel" in template, "admin panel missing V919 gate", failures)
    require("V919_BROWSER_QA_REQUIRED" in outbox, "outbox missing V919 Browser QA required section", failures)

    queue_payload = load_json(QUEUE, {})
    queue = queue_payload.get("items") if isinstance(queue_payload, dict) else queue_payload
    require(isinstance(queue, list), "visual queue is not list/items payload", failures)
    invalid_ready = []
    for item in queue if isinstance(queue, list) else []:
        if not isinstance(item, dict):
            continue
        if item.get("status") in {"READY_FOR_CODEX", "FIXABLE_SAFE", "FIXED_BY_V919"}:
            shot = item.get("screenshot_path") or item.get("screenshot") or ""
            if not screenshot_valid(str(shot)):
                invalid_ready.append(item.get("id") or item.get("route"))
    require(not invalid_ready, f"READY/FIXED items without valid screenshot: {invalid_ready[:5]}", failures)

    for text in [app_py, template, importer, outbox]:
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
    require(payload.get("version") == VERSION, "runtime version is not V919", failures)
    require(payload.get("has_v919_browser_qa_results_validation") is True, "runtime V919 validation flag false", failures)
    require(payload.get("has_v919_visual_queue_screenshot_gate") is True, "runtime V919 queue gate flag false", failures)
    require(payload.get("has_v919_outbox_evidence_gate") is True, "runtime V919 outbox flag false", failures)
    require(payload.get("v919_pixel_perfect_claim_allowed") is False, "pixel perfect should be false", failures)
    require(int(payload.get("v919_visual_queue_invalid_ready_without_screenshot") or 0) == 0, "runtime has invalid ready without screenshot", failures)
    if int(payload.get("v919_valid_screenshots_count") or 0) == 0:
        require(payload.get("v919_next_required_action") == "run_browser_qa_or_upload_artifacts", "runtime next action should request Browser QA/artifacts", failures)
        require(int(payload.get("v919_visual_queue_ready") or 0) == 0, "visual queue ready should be 0 without screenshots", failures)

    zip_clean(failures)
    if failures:
        print("V919 browser QA results gate check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V919 browser QA results gate check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
