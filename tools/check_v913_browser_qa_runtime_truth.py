from __future__ import annotations

import ast
import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V913_BROWSER_QA_EXECUTION_STATUS_TRUTH_AND_RUNTIME_CLEANUP_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
VALID_QUEUE_STATUSES = {
    "BLOCKED_NO_SCREENSHOT",
    "READY_FOR_CODEX",
    "FIXABLE_SAFE",
    "FIXED_BY_V913",
    "NEEDS_HUMAN_VISUAL_REVIEW",
    "DANGEROUS_REQUIRES_APPROVAL",
}
REPORTS = [
    "reports/V913_BROWSER_QA_EXECUTION_STATUS_TRUTH_REPORT.md",
    "reports/V913_CURRENT_RUNTIME_AND_BROWSER_QA_STATE_AUDIT.md",
    "reports/V913_RUNTIME_STATUS_TRUTH_CLEANUP_QA.md",
    "reports/V913_BROWSER_QA_EXECUTION_OR_BLOCKER_STATUS.md",
    "reports/V913_VISUAL_FIX_QUEUE_TRUTH_QA.md",
    "reports/V913_CODEX_OUTBOX_TRUTH_QA.md",
    "reports/V913_ADMIN_PANEL_CLARITY_QA.md",
    "reports/V913_PWA_ROUTE_RECHECK_QA.md",
    "reports/V913_NEXT_STEPS.md",
]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


def load_json(rel: str) -> dict:
    try:
        return json.loads(read(rel))
    except Exception:
        return {}


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
        sess["user_id"] = "codex-v913-admin"
        sess["user_name"] = "Admin SHARK"
        sess["username"] = "admin"
        sess["user_email"] = "admin@example.invalid"
        sess["user_role"] = "ADMIN"
        sess["user_membership"] = "ADMIN"
        sess["membership"] = "ADMIN"


def assert_no_raw_secrets(failures: list[str]) -> None:
    unsafe = re.compile(r"(secret|token|api_key|apikey|password)=([^\s`'\"&<>)]+)", re.IGNORECASE)
    allowed = {"", "hidden", "configured", "missing", "AUTOMATION_SECRET", "$AUTOMATION_SECRET", "...", "?", "token", "true", "false"}
    for rel in [
        "app.py",
        "tools/import_browser_qa_results.py",
        "tools/run_browser_reference_qa.py",
        "templates/base.html",
        "templates/admin_autonomous_company_sentinel.html",
        "templates/admin_sentinel_codex_outbox.html",
        "static/app.css",
    ]:
        text = read(rel)
        for match in unsafe.finditer(text):
            value = match.group(2).strip(",.;")
            if value in allowed or value.startswith("$") or "AUTOMATION_SECRET" in value or value.startswith("{{"):
                continue
            failures.append(f"possible raw secret in {rel}")


def assert_zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = [name.replace("\\", "/") for name in zf.namelist()]
    for rel in ["app.py", "VERSION.txt", "APP_VERSION", "requirements.txt", "templates/base.html", "static/app.css", "browser_qa/README.md"]:
        require(rel in names, f"zip missing {rel}", failures)
    forbidden_bits = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", "logs/")
    for name in names:
        if name.endswith((".zip", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm")) or any(bit in name for bit in forbidden_bits):
            failures.append(f"zip forbidden entry {name}")
            break


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    home = read("templates/home.html")
    css = read("static/app.css")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    queue = load_json("data/runtime/autonomous_company_sentinel/visual_fix_queue.json")
    status = load_json("data/runtime/autonomous_company_sentinel/browser_qa_status.json")
    comparison = load_json("data/runtime/autonomous_company_sentinel/browser_reference_comparison.json")
    outbox = read("data/runtime/autonomous_company_sentinel/outbox/codex_outbox.md")

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(version_bytes.decode("utf-8").strip() == VERSION, "VERSION.txt is not V913", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") == VERSION, "APP_VERSION is not V913", failures)
    require(app_version_from_source(app_py) == VERSION, "app.py APP_VERSION is not V913", failures)
    require("data-v913-shell" in base and "data-v913-browser-qa-truth" in base, "base V913 markers missing", failures)
    require("NEMESIS_CACHE_V913" in app_py, "service worker cache V913 missing", failures)
    require("V913 browser QA execution status truth" in css, "V913 CSS marker missing", failures)
    require((ROOT / "tools" / "import_browser_qa_results.py").exists(), "import_browser_qa_results.py missing", failures)
    require((ROOT / "browser_qa" / "run_local_browser_qa.ps1").exists(), "PowerShell browser QA runner missing", failures)
    require((ROOT / ".github" / "workflows" / "browser-qa.yml").exists(), "browser QA GitHub workflow missing", failures)

    items = queue.get("items") if isinstance(queue, dict) else []
    require(isinstance(items, list), "visual_fix_queue items not list", failures)
    if isinstance(items, list):
        invalid = [item.get("status") for item in items if isinstance(item, dict) and item.get("status") not in VALID_QUEUE_STATUSES]
        require(not invalid, f"invalid visual queue statuses: {invalid[:5]}", failures)
        screenshots = int(status.get("screenshots_captured") or comparison.get("screenshots_captured") or 0)
        blocked = len([item for item in items if isinstance(item, dict) and item.get("status") == "BLOCKED_NO_SCREENSHOT"])
        if screenshots == 0:
            require(blocked == len(items), "no screenshots should keep all visual queue items blocked", failures)
            require(queue.get("pixel_perfect_claim_allowed") is False, "queue allows pixel-perfect without screenshots", failures)

    for section in [
        "V913_BROWSER_QA_EXECUTION_REQUIRED",
        "V913_READY_FOR_CODEX_WITH_SCREENSHOTS",
        "V913_BLOCKED_NO_SCREENSHOT",
        "V913_RUNTIME_STATUS_FIXES",
        "V913_SAFE_FIXES_APPLIED",
        "V913_DANGEROUS_REQUIRES_APPROVAL",
    ]:
        require(section in outbox, f"outbox missing {section}", failures)

    for rel in REPORTS:
        require((ROOT / rel).exists(), f"missing report {rel}", failures)

    require("pixel-perfect: false" in read("templates/admin_autonomous_company_sentinel.html"), "admin Browser QA truth copy missing", failures)
    require("tools/import_browser_qa_results.py" in read("templates/admin_autonomous_company_sentinel.html"), "admin import hint missing", failures)
    require("La app guÃ­a al cliente" in home or "La app guía al cliente" in home, "home guide copy missing", failures)
    require("gua al cliente" not in home, "home has broken guia copy", failures)
    require("Informacion" not in base and "Terminos" not in base, "base has unaccented public legal copy", failures)

    assert_no_raw_secrets(failures)

    os.environ.setdefault("AUTOMATION_SECRET", "codex-v913-local-secret")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    admin_session(client)
    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json(silent=True) or {}
    require(runtime_resp.status_code == 200, "runtime-version not 200", failures)
    require(runtime.get("version") == VERSION, "runtime version is not V913", failures)
    require(runtime.get("version_files_match") is True, "runtime version_files_match false", failures)
    require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime not aligned", failures)
    for flag in [
        "has_v913_browser_qa_execution_status_truth",
        "has_v913_runtime_status_cleanup",
        "has_v913_visual_fix_queue_truth",
        "has_v913_browser_qa_result_importer",
    ]:
        require(runtime.get(flag) is True, f"runtime flag false: {flag}", failures)
    require(runtime.get("v910_reports_ready") is True, "v910_reports_ready is not true locally", failures)
    require(runtime.get("v910_secrets_audit_status") != "pending_report", "v910 secrets audit still pending locally", failures)
    require(runtime.get("v913_pixel_perfect_claim_allowed") is False, "V913 allows pixel-perfect", failures)
    require(int(runtime.get("v913_visual_queue_total") or 0) == len(items or []), "runtime queue total mismatch", failures)

    for route in ["/admin-login", "/admin/dashboard", "/admin/autonomous-company-sentinel", "/admin/sentinel-issues", "/admin/sentinel-codex-outbox", "/admin/not-found-events"]:
        response = client.get(route)
        require(response.status_code in {200, 302}, f"{route} unexpected status {response.status_code}", failures)
        html = response.get_data(as_text=True)
        require("Salir cliente" not in html, f"{route} contains Salir cliente", failures)
        require("Capturas0" not in re.sub(r"\s+", "", html), f"{route} has concatenated Capturas0", failures)
        require("Comparaciones18" not in re.sub(r"\s+", "", html), f"{route} has concatenated Comparaciones18", failures)
        require('data-nav-zone="client-bottom"' not in html, f"{route} leaks client bottom nav", failures)
        require("v825-public-floating-shark" not in html, f"{route} leaks public floating SHARK", failures)

    home_resp = client.get("/")
    home_html = home_resp.get_data(as_text=True)
    require(home_resp.status_code == 200, "home not 200", failures)
    require("`r`n" not in home_html and "\ufeff" not in home_html, "home has visible artifact", failures)
    sw = client.get("/service-worker.js")
    require(sw.status_code == 200 and "NEMESIS_CACHE_V913" in sw.get_data(as_text=True), "service worker cache V913 not served", failures)
    require("res.status===404" in sw.get_data(as_text=True), "service worker 404 guard missing", failures)
    require(client.get("/ruta-inventada-v913").status_code == 404, "HTML 404 not 404", failures)
    api_404 = client.get("/api/ruta-inventada-v913")
    require(api_404.status_code == 404 and api_404.is_json, "API 404 JSON missing", failures)

    assert_zip_clean(failures)
    if failures:
        print("V913 browser QA runtime truth check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V913 browser QA runtime truth check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
