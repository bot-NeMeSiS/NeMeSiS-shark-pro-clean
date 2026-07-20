from __future__ import annotations

import ast
import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V915_AUTOMATED_COMPANY_WORKFORCE_RENDER_DEPLOY_PIPELINE_FINAL"
CURRENT_ALLOWED = {
    VERSION,
    "V916_WORKFORCE_ACTIVATION_BROWSER_QA_AND_DEPLOY_AUTOMATION_READY_FINAL",
    "V917_WORKFORCE_FIRST_FULL_AUTOMATED_RUN_AND_REPORTING_FINAL",
    "V918_WORKFORCE_POST_DEPLOY_BROWSER_QA_ACTIONS_AND_VISUAL_QUEUE_UNLOCK_FINAL",
    "V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL",
    "V938_COMPANY_OPERATIONS_RECOVERY_OBSERVABILITY_CENTER_FINAL",
}
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
WORKERS = [
    "release_manager.py",
    "runtime_verifier.py",
    "post_deploy_sentinel.py",
    "render_deploy_guard.py",
    "security_secret_guard.py",
    "browser_qa_orchestrator.py",
    "visual_queue_manager.py",
    "telegram_dry_run_watcher.py",
    "reporting_worker.py",
]
REPORTS = [
    "V915_AUTOMATED_COMPANY_WORKFORCE_REPORT.md",
    "V915_RENDER_DEPLOY_PIPELINE_QA.md",
    "V915_GITHUB_ACTIONS_CI_QA.md",
    "V915_RUNTIME_VERIFICATION_REPORT.md",
    "V915_POST_DEPLOY_SENTINEL_REPORT.md",
    "V915_BROWSER_QA_ORCHESTRATOR_REPORT.md",
    "V915_VISUAL_QUEUE_MANAGER_REPORT.md",
    "V915_TELEGRAM_DRY_RUN_WATCHER_REPORT.md",
    "V915_SECURITY_SECRET_GUARD_REPORT.md",
    "V915_NEXT_STEPS.md",
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


def admin_session(client) -> None:
    with client.session_transaction() as sess:
        sess["user_id"] = "codex-v915-admin"
        sess["user_name"] = "Admin SHARK"
        sess["username"] = "admin"
        sess["user_email"] = "admin@example.invalid"
        sess["user_role"] = "ADMIN"
        sess["user_membership"] = "ADMIN"
        sess["membership"] = "ADMIN"


def assert_zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = [name.replace("\\", "/") for name in zf.namelist()]
    for rel in ["app.py", "VERSION.txt", "APP_VERSION", "requirements.txt", "templates/base.html", "static/app.css", "automation_workforce/README.md"]:
        require(rel in names, f"zip missing {rel}", failures)
    forbidden_bits = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", "logs/")
    for name in names:
        if name.endswith((".zip", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm")) or any(bit in name for bit in forbidden_bits):
            failures.append(f"zip forbidden entry {name}")
            break


def assert_workflow_secret_safe(failures: list[str]) -> None:
    deploy = read(".github/workflows/render-deploy.yml")
    ci = read(".github/workflows/nemesis-ci.yml")
    require("RENDER_DEPLOY_HOOK_URL: ${{ secrets.RENDER_DEPLOY_HOOK_URL }}" in deploy, "deploy workflow does not use GitHub secret placeholder", failures)
    require('curl -fsS -X POST "$RENDER_DEPLOY_HOOK_URL" >/dev/null' in deploy, "deploy workflow does not hide hook output", failures)
    require('echo "$RENDER_DEPLOY_HOOK_URL"' not in deploy, "deploy workflow prints deploy hook", failures)
    require("secrets." not in ci, "CI workflow should not require secrets", failures)


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(version_bytes.decode("utf-8").strip() in CURRENT_ALLOWED, "VERSION.txt is not V915 or a compatible successor", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in CURRENT_ALLOWED, "APP_VERSION is not V915 or a compatible successor", failures)
    require(app_version_from_source(app_py) in CURRENT_ALLOWED, "app.py APP_VERSION is not V915 or a compatible successor", failures)
    require("data-v915-workforce-shell" in base, "base V915 marker missing", failures)
    require("V915 automated company workforce render deploy pipeline" in css, "V915 CSS marker missing", failures)
    require(any(cache in app_py for cache in ["NEMESIS_CACHE_V915", "NEMESIS_CACHE_V916", "NEMESIS_CACHE_V917", "NEMESIS_CACHE_V918", "NEMESIS_CACHE_V937"]), "service worker cache V915+ missing", failures)

    for worker in WORKERS:
        require((ROOT / "automation_workforce" / worker).exists(), f"missing worker {worker}", failures)
    require((ROOT / "automation_workforce" / "README.md").exists(), "automation_workforce README missing", failures)
    require((ROOT / ".github" / "workflows" / "nemesis-ci.yml").exists(), "CI workflow missing", failures)
    require((ROOT / ".github" / "workflows" / "render-deploy.yml").exists(), "Render deploy workflow missing", failures)
    require((ROOT / "templates" / "admin_automation_workforce.html").exists(), "admin workforce template missing", failures)
    for route in ["/admin/automation-workforce", "/admin/workforce", "/admin/company-workers", "/admin/deploy-center"]:
        require(route in app_py, f"missing admin route {route}", failures)
    for endpoint in [
        "/api/admin/automation-workforce/status",
        "/api/admin/automation-workforce/run-checks",
        "/api/admin/automation-workforce/verify-runtime",
        "/api/admin/automation-workforce/post-deploy-sentinel",
        "/api/admin/automation-workforce/browser-qa-status",
        "/api/admin/automation-workforce/visual-queue-refresh",
    ]:
        require(endpoint in app_py, f"missing admin API {endpoint}", failures)

    assert_workflow_secret_safe(failures)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json(silent=True) or {}
    require(runtime_resp.status_code == 200, "runtime-version not 200", failures)
    require(runtime.get("version") in CURRENT_ALLOWED, "runtime version is not V915 or a compatible successor", failures)
    require(runtime.get("version_files_match") is True, "runtime version_files_match false", failures)
    require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime not aligned", failures)
    for flag in [
        "has_v915_automated_company_workforce",
        "has_v915_render_deploy_pipeline",
        "has_v915_post_deploy_sentinel",
        "has_v915_browser_qa_orchestrator",
        "has_v915_security_secret_guard",
    ]:
        require(runtime.get(flag) is True, f"runtime flag false: {flag}", failures)
    require(runtime.get("v915_automated_deploy_enabled") is False or isinstance(runtime.get("v915_automated_deploy_enabled"), bool), "automated deploy flag not boolean", failures)
    require(runtime.get("v915_deploy_hook_state") in {"***missing***", "***configured***"}, "deploy hook state not masked", failures)

    for endpoint in [
        "/api/admin/automation-workforce/status",
        "/api/admin/automation-workforce/run-checks",
        "/api/admin/automation-workforce/verify-runtime",
        "/api/admin/automation-workforce/post-deploy-sentinel",
        "/api/admin/automation-workforce/browser-qa-status",
        "/api/admin/automation-workforce/visual-queue-refresh",
    ]:
        method = client.post if endpoint != "/api/admin/automation-workforce/status" else client.get
        response = method(endpoint)
        require(response.status_code == 403, f"{endpoint} not protected without admin", failures)

    admin_session(client)
    page = client.get("/admin/automation-workforce")
    require(page.status_code == 200, "admin workforce page not 200 with admin session", failures)
    html = page.get_data(as_text=True)
    require("Automation Workforce" in html or "Equipo automático" in html, "admin workforce page missing title", failures)
    require("TELEGRAM_BOT_TOKEN" not in html and "RENDER_DEPLOY_HOOK_URL" not in html, "admin workforce page leaks secret names", failures)
    require('data-nav-zone="client-bottom"' not in html, "admin workforce leaks client bottom nav", failures)
    require("v825-public-floating-shark" not in html, "admin workforce leaks public floating SHARK", failures)

    from automation_workforce.security_secret_guard import run_security_secret_guard
    guard = run_security_secret_guard(dry_run=True)
    require(bool(guard.get("ok")), f"security guard findings: {guard.get('findings')}", failures)

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}", failures)

    assert_zip_clean(failures)
    if failures:
        print("V915 automated company workforce check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V915 automated company workforce check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
