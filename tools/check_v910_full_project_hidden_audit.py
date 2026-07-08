from __future__ import annotations

import ast
import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V910_FULL_PROJECT_HIDDEN_AUDIT_ROUTE_NOT_FOUND_BROWSER_QA_READY_FINAL"
CURRENT_COMPATIBLE_VERSIONS = {
    VERSION,
    "V911_REAL_BROWSER_SCREENSHOT_VISUAL_FIX_EXECUTION_FINAL",
    "V911_VIDEO_ADMIN_UI_BINDING_BROWSER_QA_QUEUE_FIX_FINAL",
    "V912_VIDEO_ADMIN_UI_COPY_POLISH_BROWSER_QA_QUEUE_FINAL",
}
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "reports/V910_FULL_PROJECT_HIDDEN_AUDIT_REPORT.md",
    "reports/V910_FULL_PROJECT_HIDDEN_TREE_AUDIT.md",
    "reports/V910_SECRET_AND_LOG_EXPOSURE_AUDIT.md",
    "reports/V910_ROUTE_NOT_FOUND_PWA_CACHE_AUDIT.md",
    "reports/V910_ROUTES_LINKS_AND_ALIASES_AUDIT.md",
    "reports/V910_ADMIN_STABILITY_AUDIT.md",
    "reports/V910_CLIENT_STABILITY_AUDIT.md",
    "reports/V910_BROWSER_QA_PIPELINE_FULL_AUDIT.md",
    "reports/V910_REFERENCE_IMAGES_AND_VISUAL_QUEUE_AUDIT.md",
    "reports/V910_SENTINEL_OUTBOX_AND_VISUAL_QUEUE_AUDIT.md",
    "reports/V910_RELEASE_ZIP_AND_DEPLOY_ROOT_AUDIT.md",
    "reports/V910_NEXT_STEPS.md",
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


def raw_secret_findings() -> list[str]:
    findings: list[str] = []
    scan_paths = [
        ROOT / "app.py",
        ROOT / "tools" / "render_cron_telegram_tick.py",
        ROOT / "browser_qa" / "README.md",
        ROOT / ".github" / "workflows" / "browser-qa.yml",
    ] + [ROOT / rel for rel in REPORTS]
    unsafe = re.compile(r"(secret|token|api_key|apikey|password)=([^\s`'\"&<>)]+)", re.IGNORECASE)
    allowed = {"hidden", "configured", "missing", "***hidden***", "***missing***", "AUTOMATION_SECRET", "$AUTOMATION_SECRET", "..."}
    for path in scan_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in unsafe.finditer(text):
            value = match.group(2).strip(",.;")
            normalized = value.strip(" ,.;")
            if normalized in {"", "?", "...", "token", "secret"}:
                continue
            if normalized in allowed or normalized.startswith("$") or normalized.startswith("{") or normalized.startswith("***") or "AUTOMATION_SECRET" in normalized:
                continue
            findings.append(path.relative_to(ROOT).as_posix())
    return sorted(set(findings))


def zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    require(zip_path.exists(), "V910 zip missing", failures)
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    for rel in ["app.py", "VERSION.txt", "requirements.txt", "templates/base.html", "browser_qa/README.md", ".github/workflows/browser-qa.yml"]:
        require(rel in names, f"zip missing {rel}", failures)
    forbidden_parts = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", "logs/")
    for name in names:
        normalized = name.replace("\\", "/")
        if normalized.endswith((".zip", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm")) or any(part in normalized for part in forbidden_parts):
            failures.append(f"zip forbidden entry {normalized}")
            break


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    service_worker = app_py
    version_bytes = (ROOT / "VERSION.txt").read_bytes()

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(version_bytes.decode("utf-8").strip() in CURRENT_COMPATIBLE_VERSIONS, "VERSION.txt is not V910-compatible", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in CURRENT_COMPATIBLE_VERSIONS, "APP_VERSION file is not V910-compatible", failures)
    require(app_version_from_source(app_py) in CURRENT_COMPATIBLE_VERSIONS, "app.py APP_VERSION is not V910-compatible", failures)
    require("data-v910-shell" in base, "base V910 shell marker missing", failures)
    require("NEMESIS_CACHE_V910" in service_worker or "NEMESIS_CACHE_V911" in service_worker, "service worker cache is not V910-compatible", failures)
    require("v910_full_project_audit_runtime_summary" in app_py, "V910 runtime summary missing", failures)
    require("has_v910_full_hidden_project_audit" in app_py, "V910 hidden audit flag missing", failures)

    for report in REPORTS:
        require((ROOT / report).exists(), f"missing {report}", failures)

    require((ROOT / "reference_images").exists(), "reference_images missing", failures)
    require((ROOT / "reference_images" / "reference_manifest.json").exists(), "reference manifest missing", failures)
    require((ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "visual_fix_queue.json").exists(), "visual fix queue missing", failures)
    require((ROOT / "browser_qa" / "README.md").exists(), "browser_qa README missing", failures)
    require((ROOT / ".github" / "workflows" / "browser-qa.yml").exists() or (ROOT / "docs" / "browser_qa_github_action_example.yml").exists(), "browser QA workflow/example missing", failures)
    require((ROOT / "tools" / "audit_all_routes_links.py").exists(), "route/link auditor missing", failures)

    if "href=\"/api/admin/continuous-sentinel/run\"" in base:
        failures.append("direct href to continuous sentinel API found in base")
    for text in [base, read("templates/404.html")]:
        lowered = text.lower()
        require("ï¿½" not in text and "ã³" not in lowered, "mojibake marker visible in templates", failures)
        require("undefined" not in lowered, "undefined visible in templates", failures)

    secret_findings = raw_secret_findings()
    require(not secret_findings, f"possible raw secret references: {secret_findings[:5]}", failures)

    os.environ.setdefault("AUTOMATION_SECRET", "codex-v910-local-secret")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json(silent=True) or {}
    require(runtime_resp.status_code == 200, "runtime-version not 200", failures)
    require(runtime.get("version") in CURRENT_COMPATIBLE_VERSIONS, "runtime version is not V910-compatible", failures)
    require(runtime.get("version_files_match") is True, "runtime version_files_match false", failures)
    require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime not aligned", failures)
    for flag in [
        "has_v902b_deploy_alignment_secret_rotation_guard",
        "has_v905_bom_version_alignment_fix",
        "has_v906b_public_home_html_artifact_cleanup",
        "has_v907_browser_qa_enablement",
        "has_v908_screenshot_based_reference_ui_fix",
        "has_v909_browser_qa_pipeline",
        "has_v910_full_hidden_project_audit",
        "has_v910_route_not_found_pwa_audit",
        "has_v910_browser_qa_pipeline_audited",
        "has_v910_release_tree_cleanliness_audit",
    ]:
        require(runtime.get(flag) is True, f"runtime flag false: {flag}", failures)
    require(runtime.get("secret_masking_ok") is True, "secret masking runtime not OK", failures)

    html_404 = client.get("/ruta-inventada-v910")
    api_404 = client.get("/api/ruta-inventada-v910")
    require(html_404.status_code == 404 and b"Ruta no encontrada" in html_404.data, "HTML 404 premium missing", failures)
    require(api_404.status_code == 404 and api_404.is_json, "API 404 JSON missing", failures)
    require(client.get("/service-worker.js").status_code == 200, "service worker not 200", failures)
    require(client.get("/manifest.json").status_code == 200, "manifest not 200", failures)

    zip_clean(failures)
    if failures:
        print("V910 full project hidden audit check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V910 full project hidden audit check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
