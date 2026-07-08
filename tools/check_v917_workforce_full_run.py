from __future__ import annotations

import ast
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V917_WORKFORCE_FIRST_FULL_AUTOMATED_RUN_AND_REPORTING_FINAL"
LATEST_RUN = ROOT / "data" / "runtime" / "automation_workforce" / "latest_run.json"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "V917_WORKFORCE_FIRST_FULL_AUTOMATED_RUN_REPORT.md",
    "V917_WORKER_STATUS_SUMMARY.md",
    "V917_RUNTIME_VERIFIER_RUN_QA.md",
    "V917_POST_DEPLOY_SENTINEL_RUN_QA.md",
    "V917_SECRET_GUARD_RUN_QA.md",
    "V917_BROWSER_QA_ORCHESTRATOR_RUN_QA.md",
    "V917_VISUAL_QUEUE_MANAGER_RUN_QA.md",
    "V917_TELEGRAM_DRY_RUN_WATCHER_QA.md",
    "V917_NEXT_STEPS.md",
]


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


def zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = [name.replace("\\", "/") for name in zf.namelist()]
    for rel in ["app.py", "VERSION.txt", "APP_VERSION", "automation_workforce/reporting_worker.py", "data/runtime/automation_workforce/latest_run.json"]:
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
    require(local_version == VERSION or local_version.startswith("V918_"), "VERSION.txt is not V917 or compatible successor", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") == local_version, "APP_VERSION mismatch", failures)
    require(app_version(app_py) == local_version, "app.py APP_VERSION mismatch", failures)
    require("NEMESIS_CACHE_V917" in app_py or "NEMESIS_CACHE_V918" in app_py, "service worker cache V917/V918 missing", failures)
    require("v917_workforce_full_run_runtime_summary" in app_py, "runtime V917 summary missing", failures)
    for flag in ["has_v917_workforce_first_full_run", "has_v917_workforce_reporting", "has_v917_worker_status_runtime"]:
        require(flag in app_py, f"runtime flag missing: {flag}", failures)

    for worker in [
        "release_manager.py",
        "runtime_verifier.py",
        "post_deploy_sentinel.py",
        "security_secret_guard.py",
        "browser_qa_orchestrator.py",
        "visual_queue_manager.py",
        "telegram_dry_run_watcher.py",
        "reporting_worker.py",
    ]:
        require((ROOT / "automation_workforce" / worker).exists(), f"missing worker {worker}", failures)

    require(LATEST_RUN.exists(), "latest_run.json missing", failures)
    latest = json.loads(LATEST_RUN.read_text(encoding="utf-8-sig")) if LATEST_RUN.exists() else {}
    for key in [
        "release_manager_status",
        "runtime_verifier_status",
        "post_deploy_sentinel_status",
        "secret_guard_status",
        "browser_qa_orchestrator_status",
        "visual_queue_manager_status",
        "telegram_dry_run_watcher_status",
        "reporting_worker_status",
        "overall_status",
        "next_required_action",
        "generated_at_madrid",
    ]:
        require(bool(latest.get(key)), f"latest_run missing {key}", failures)

    require("v917-full-run-panel" in template, "admin panel missing V917 full run panel", failures)
    require("Ultimo full run" in template and "Telegram Dry-run" in template, "admin panel missing worker statuses", failures)
    browser_text = read("automation_workforce/browser_qa_orchestrator.py").lower()
    require("pixel_perfect_claim_allowed\": true" not in browser_text and "pixel-perfect aprobado" not in browser_text, "browser QA claims pixel-perfect", failures)
    require((latest.get("workers") or {}).get("telegram_dry_run_watcher", {}).get("no_real_telegram") is True, "telegram watcher not marked no_real_telegram", failures)
    require((latest.get("workers") or {}).get("secret_guard", {}).get("findings_count") == 0, "secret guard findings present", failures)

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}", failures)
    for term in ["sk_live_", "xoxb-", "ghp_", "rnd_", "TELEGRAM_BOT_TOKEN="]:
        require(term not in app_py + template + json.dumps(latest), f"possible secret term found: {term}", failures)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    runtime = client.get("/api/runtime-version")
    payload = runtime.get_json(silent=True) or {}
    require(runtime.status_code == 200, "runtime-version not 200", failures)
    require(payload.get("version") == local_version, "runtime version mismatch", failures)
    require(payload.get("has_v917_workforce_first_full_run") is True, "runtime V917 full run flag false", failures)
    require(payload.get("has_v917_workforce_reporting") is True, "runtime V917 reporting flag false", failures)
    require(payload.get("v917_secret_guard_status") in {"ok", "not_run"}, "runtime secret guard unexpected", failures)
    require(client.get("/api/admin/automation-workforce/status").status_code == 403, "admin workforce API not protected", failures)

    zip_clean(failures)
    if failures:
        print("V917 workforce full run check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V917 workforce full run check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
