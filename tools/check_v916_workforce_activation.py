from __future__ import annotations

import ast
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V916_WORKFORCE_ACTIVATION_BROWSER_QA_AND_DEPLOY_AUTOMATION_READY_FINAL"
CURRENT_ALLOWED = {
    VERSION,
    "V917_WORKFORCE_FIRST_FULL_AUTOMATED_RUN_AND_REPORTING_FINAL",
    "V918_WORKFORCE_POST_DEPLOY_BROWSER_QA_ACTIONS_AND_VISUAL_QUEUE_UNLOCK_FINAL",
    "V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL",
}
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "V916_WORKFORCE_ACTIVATION_REPORT.md",
    "V916_WORKFORCE_ACTIVATION_AUDIT.md",
    "V916_RENDER_DEPLOY_HOOK_ACTIVATION_GUIDE.md",
    "V916_RENDER_DEPLOY_GUARD_DRY_RUN_QA.md",
    "V916_GITHUB_ACTIONS_WORKFLOW_QA.md",
    "V916_BROWSER_QA_ACTIVATION_GUIDE.md",
    "V916_BROWSER_QA_ORCHESTRATOR_STATUS_QA.md",
    "V916_VISUAL_QUEUE_MANAGER_STATUS_QA.md",
    "V916_NEXT_STEPS.md",
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


def assert_zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = [name.replace("\\", "/") for name in zf.namelist()]
    for rel in ["app.py", "VERSION.txt", "APP_VERSION", "requirements.txt", "automation_workforce/render_deploy_guard.py", ".github/workflows/render-deploy.yml"]:
        require(rel in names, f"zip missing {rel}", failures)
    forbidden_bits = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", "logs/")
    for name in names:
        if name.endswith((".zip", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm")) or any(bit in name for bit in forbidden_bits):
            failures.append(f"zip forbidden entry {name}")
            break


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    css = read("static/app.css")
    template = read("templates/admin_automation_workforce.html")
    render_guard = read("automation_workforce/render_deploy_guard.py")
    browser_orchestrator = read("automation_workforce/browser_qa_orchestrator.py")
    visual_manager = read("automation_workforce/visual_queue_manager.py")
    render_workflow = read(".github/workflows/render-deploy.yml")
    browser_workflow = read(".github/workflows/browser-qa.yml")
    ci_workflow = read(".github/workflows/nemesis-ci.yml")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(version_bytes.decode("utf-8").strip() in CURRENT_ALLOWED, "VERSION.txt is not V916 or compatible successor", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in CURRENT_ALLOWED, "APP_VERSION is not V916 or compatible successor", failures)
    require(app_version(app_py) in CURRENT_ALLOWED, "app.py APP_VERSION is not V916 or compatible successor", failures)
    require(any(cache in app_py for cache in ["NEMESIS_CACHE_V916", "NEMESIS_CACHE_V917", "NEMESIS_CACHE_V918", "NEMESIS_CACHE_V937"]), "service worker cache is not V916+", failures)

    for flag in [
        "has_v916_workforce_activation",
        "has_v916_deploy_hook_activation_guide",
        "has_v916_browser_qa_activation_guide",
        "has_v916_workforce_status_truth",
        "v916_workforce_core_ready",
        "v916_automated_deploy_configured",
        "v916_browser_qa_github_action_ready",
    ]:
        require(flag in app_py, f"missing runtime flag/status {flag}", failures)

    require("--check-config" in render_guard and "--trigger-deploy" in render_guard, "render_deploy_guard missing V916 modes", failures)
    require("mask_secret(hook)" in render_guard, "render deploy guard does not mask hook", failures)
    require("github_action_available" in browser_orchestrator and "visual_queue_blocked" in browser_orchestrator, "browser orchestrator missing V916 status fields", failures)
    require("blocked_no_screenshot" in visual_manager and "next_action" in visual_manager, "visual queue manager missing V916 status fields", failures)
    require("v916-workforce-activation" in template or "v933-admin-workforce" in template, "admin panel missing workforce shell", failures)
    lowered_template = template.lower()
    require(all(label in lowered_template for label in ("core workforce", "deploy hook", "browser qa", "secret guard")), "admin panel missing separated status cards", failures)
    require("V916 workforce activation browser QA and deploy automation ready" in css, "CSS V916 marker missing", failures)

    require("workflow_dispatch" in render_workflow and "RENDER_DEPLOY_HOOK_URL" in render_workflow, "render deploy workflow missing manual hook flow", failures)
    require('echo "$RENDER_DEPLOY_HOOK_URL"' not in render_workflow, "render deploy workflow prints hook", failures)
    require("playwright" in browser_workflow.lower(), "browser QA workflow does not install/use Playwright", failures)
    require("run_continuous_sentinel_static.py" in ci_workflow, "CI workflow missing Sentinel", failures)

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}", failures)

    bad_terms = ["sk_live_", "sk_test_", "xoxb-", "rnd_", "ghp_", "TELEGRAM_BOT_TOKEN="]
    for rel in ["app.py", "automation_workforce/render_deploy_guard.py", ".github/workflows/render-deploy.yml", "templates/admin_automation_workforce.html"]:
        text = read(rel)
        for term in bad_terms:
            require(term not in text, f"possible secret token in {rel}", failures)
    require("pixel-perfect" not in " ".join(read(f"reports/{r}") for r in REPORTS).lower(), "pixel-perfect claim found in V916 reports", failures)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    runtime = client.get("/api/runtime-version")
    payload = runtime.get_json(silent=True) or {}
    require(runtime.status_code == 200, "runtime-version not 200", failures)
    require(payload.get("version") in CURRENT_ALLOWED, "runtime version is not V916 or compatible successor", failures)
    require(payload.get("version_files_match") is True, "runtime version_files_match false", failures)
    require(payload.get("deployment_alignment_status") == "aligned_local_files", "runtime not aligned", failures)
    require(payload.get("has_v916_workforce_activation") is True, "V916 workforce activation flag false", failures)
    require(payload.get("has_v916_workforce_status_truth") is True, "V916 status truth flag false", failures)
    require(payload.get("v916_workforce_core_ready") is True, "V916 core not ready", failures)
    require(payload.get("v916_deploy_hook_configured") in {True, False}, "deploy hook state not boolean", failures)

    admin_api = client.get("/api/admin/automation-workforce/status")
    require(admin_api.status_code == 403, "admin workforce API not protected", failures)

    assert_zip_clean(failures)
    if failures:
        print("V916 workforce activation check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V916 workforce activation check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
