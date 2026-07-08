from __future__ import annotations

import ast
import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V918_WORKFORCE_POST_DEPLOY_BROWSER_QA_ACTIONS_AND_VISUAL_QUEUE_UNLOCK_FINAL"
LATEST_RUN = ROOT / "data" / "runtime" / "automation_workforce" / "latest_run.json"
VISUAL_QUEUE = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "visual_fix_queue.json"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
VALID_QUEUE_STATUSES = {
    "BLOCKED_NO_SCREENSHOT",
    "READY_FOR_CODEX",
    "FIXABLE_SAFE",
    "NEEDS_HUMAN_VISUAL_REVIEW",
    "DANGEROUS_REQUIRES_APPROVAL",
    "FIXED_BY_V913",
}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


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


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = [name.replace("\\", "/") for name in zf.namelist()]
    for rel in ["app.py", "VERSION.txt", "APP_VERSION", "automation_workforce/browser_qa_action_router.py", "data/runtime/automation_workforce/latest_run.json"]:
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
    version_bytes = (ROOT / "VERSION.txt").read_bytes()

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    local_version = version_bytes.decode("utf-8").strip()
    require(local_version == VERSION or local_version.startswith("V919_"), "VERSION.txt is not V918 or compatible successor", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") == local_version, "APP_VERSION mismatch", failures)
    require(app_version(app_py) == local_version, "app.py APP_VERSION mismatch", failures)
    require("NEMESIS_CACHE_V918" in app_py or "NEMESIS_CACHE_V919" in app_py, "service worker cache V918/V919 missing", failures)
    for flag in [
        "has_v918_workforce_post_deploy_actions",
        "has_v918_browser_qa_action_router",
        "has_v918_visual_queue_unlock_status",
        "has_v918_next_action_truth",
    ]:
        require(flag in app_py, f"runtime flag missing: {flag}", failures)

    require((ROOT / "automation_workforce" / "browser_qa_action_router.py").exists(), "browser_qa_action_router missing", failures)
    require(LATEST_RUN.exists(), "latest_run.json missing", failures)
    latest = load_json(LATEST_RUN, {})
    require(latest.get("next_required_action") != "deploy_v917_and_verify_runtime", "latest_run still asks to deploy V917", failures)

    queue_payload = load_json(VISUAL_QUEUE, [])
    queue = queue_payload.get("items") if isinstance(queue_payload, dict) else queue_payload
    require(isinstance(queue, list), "visual queue is not a list/items payload", failures)
    invalid = [item.get("status") for item in queue if isinstance(item, dict) and item.get("status") not in VALID_QUEUE_STATUSES]
    require(not invalid, f"visual queue invalid statuses: {invalid[:5]}", failures)

    require("v918-post-deploy-panel" in template, "admin panel missing V918 post-deploy panel", failures)
    require("Browser QA Router" in template, "admin panel missing Browser QA Router", failures)
    require("deploy_v917_and_verify_runtime" not in template, "admin panel contains stale V917 deploy action", failures)

    for text in [app_py, template, json.dumps(latest), read("automation_workforce/browser_qa_action_router.py")]:
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
    require(payload.get("version") == local_version, "runtime version mismatch", failures)
    require(payload.get("has_v918_workforce_post_deploy_actions") is True, "runtime V918 post-deploy flag false", failures)
    require(payload.get("has_v918_browser_qa_action_router") is True, "runtime V918 router flag false", failures)
    require(payload.get("has_v918_visual_queue_unlock_status") is True, "runtime V918 queue flag false", failures)
    require(payload.get("v918_pixel_perfect_claim_allowed") is False, "pixel perfect should be false", failures)
    require(payload.get("v918_next_required_action") != "deploy_v917_and_verify_runtime", "runtime still asks to deploy V917", failures)
    require(client.get("/api/admin/automation-workforce/status").status_code == 403, "admin workforce API not protected", failures)

    zip_clean(failures)
    if failures:
        print("V918 workforce post-deploy browser actions check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V918 workforce post-deploy browser actions check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
