from __future__ import annotations

import ast
import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL"
CURRENT_COMPATIBLE_VERSIONS = {
    VERSION,
    "V910_FULL_PROJECT_HIDDEN_AUDIT_ROUTE_NOT_FOUND_BROWSER_QA_READY_FINAL",
    "V911_REAL_BROWSER_SCREENSHOT_VISUAL_FIX_EXECUTION_FINAL",
    "V911_VIDEO_ADMIN_UI_BINDING_BROWSER_QA_QUEUE_FIX_FINAL",
}
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "reports/V909_BROWSER_QA_EXECUTION_PIPELINE_REPORT.md",
    "reports/V909_VISUAL_FIX_QUEUE_REPORT.md",
    "reports/V909_GITHUB_ACTION_BROWSER_QA_QA.md",
    "reports/V909_NEXT_STEPS.md",
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


def assert_no_raw_secrets(failures: list[str]) -> None:
    scan_paths = [
        ROOT / "app.py",
        ROOT / "browser_qa" / "README.md",
        ROOT / "browser_qa" / "run_local_browser_qa.ps1",
        ROOT / "browser_qa" / "run_local_browser_qa.bat",
        ROOT / "browser_qa" / "run_local_browser_qa.sh",
        ROOT / ".github" / "workflows" / "browser-qa.yml",
        ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "visual_fix_queue.json",
    ] + [ROOT / report for report in REPORTS]
    unsafe = re.compile(r"(secret|token|api_key|apikey)=([^\s`'\"&<>)]+)", re.IGNORECASE)
    allowed = {"hidden", "configured", "missing", "***hidden***", "***missing***", "AUTOMATION_SECRET", "$AUTOMATION_SECRET", "..."}
    for path in scan_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in unsafe.finditer(text):
            value = match.group(2).strip(",.;")
            if value in allowed or value.strip(",.;") in {"", "?", "token", "secret"} or value.startswith("$") or value.startswith("{") or value.startswith("***") or "AUTOMATION_SECRET" in value:
                continue
            failures.append(f"possible raw secret in {path.relative_to(ROOT)}")


def assert_zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    forbidden = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    for rel in ["app.py", "VERSION.txt", "APP_VERSION", "requirements.txt", "browser_qa/README.md", "tools/check_v909_browser_qa_pipeline.py"]:
        require(rel in names, f"zip missing {rel}", failures)
    for name in names:
        normalized = name.replace("\\", "/")
        if normalized.endswith(".zip") or normalized.endswith(".db") or normalized.endswith(".sqlite") or any(part in normalized for part in forbidden):
            failures.append(f"zip forbidden entry {normalized}")
            break


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    admin = read("templates/admin_autonomous_company_sentinel.html")
    outbox_template = read("templates/admin_sentinel_codex_outbox.html")
    runner = read("tools/run_browser_reference_qa.py")

    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(version_bytes.decode("utf-8").strip() in CURRENT_COMPATIBLE_VERSIONS, "VERSION.txt is not V909-compatible", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in CURRENT_COMPATIBLE_VERSIONS, "APP_VERSION is not V909-compatible", failures)
    require(app_version_from_source(app_py) in CURRENT_COMPATIBLE_VERSIONS, "app.py APP_VERSION is not V909-compatible", failures)

    require("data-v909-shell" in base, "base V909 shell marker missing", failures)
    require("has_v909_browser_qa_pipeline" in app_py, "runtime V909 pipeline flag missing", failures)
    require("has_v909_visual_fix_queue" in app_py, "runtime V909 visual queue flag missing", failures)
    require("v909_browser_qa_pipeline_runtime_summary" in app_py, "V909 runtime summary missing", failures)

    browser_dir = ROOT / "browser_qa"
    for rel in [
        "browser_qa/README.md",
        "browser_qa/run_local_browser_qa.ps1",
        "browser_qa/run_local_browser_qa.bat",
        "browser_qa/run_local_browser_qa.sh",
        "browser_qa/playwright_requirements.txt",
    ]:
        require((ROOT / rel).exists(), f"missing {rel}", failures)
    require("playwright" in read("browser_qa/playwright_requirements.txt"), "browser QA requirements missing playwright", failures)
    require((ROOT / ".github" / "workflows" / "browser-qa.yml").exists() or (ROOT / "docs" / "browser_qa_github_action_example.yml").exists(), "GitHub Action or example missing", failures)

    for snippet in ["browser_qa_result.json", "reference_comparison.json", "_write_visual_fix_queue", "visual_fix_queue.json"]:
        require(snippet in runner, f"runner missing {snippet}", failures)

    queue_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "visual_fix_queue.json"
    require(queue_path.exists(), "visual_fix_queue.json missing", failures)
    if queue_path.exists():
        queue = json.loads(queue_path.read_text(encoding="utf-8-sig", errors="replace"))
        require(queue.get("version") in CURRENT_COMPATIBLE_VERSIONS, "visual fix queue version is not V909-compatible", failures)
        require(isinstance(queue.get("items"), list), "visual fix queue items missing", failures)
        require(int(queue.get("blocked_no_screenshot_count") or 0) >= 1, "visual fix queue should show blocked screenshots when Browser QA unavailable", failures)
        require(queue.get("pixel_perfect_claim_allowed") is False, "visual fix queue allows pixel-perfect", failures)

    require("v909-browser-pipeline-panel" in admin and "Browser QA Pipeline V909" in admin, "admin sentinel V909 pipeline panel missing", failures)
    require("v909-visual-fix-queue-panel" in outbox_template and "Visual Fix Queue V909" in outbox_template, "outbox V909 queue panel missing", failures)
    require("pixel-perfect" in read("browser_qa/README.md").lower(), "browser QA README must mention no pixel-perfect claim", failures)

    for report in REPORTS:
        require((ROOT / report).exists(), f"missing report {report}", failures)
    report_blob = "\n".join(read(report) for report in REPORTS if (ROOT / report).exists()).lower()
    require("pixel_perfect_claim_allowed: true" not in report_blob and "pixel-perfect permitido: si" not in report_blob, "reports must not allow pixel-perfect without screenshots", failures)

    assert_no_raw_secrets(failures)

    os.environ.setdefault("AUTOMATION_SECRET", "codex-v909-local-secret")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json(silent=True) or {}
    require(runtime_resp.status_code == 200, "runtime-version not 200", failures)
    require(runtime.get("version") in CURRENT_COMPATIBLE_VERSIONS, "runtime version is not V909-compatible", failures)
    require(runtime.get("version_files_match") is True, "runtime version_files_match false", failures)
    require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime deployment alignment not aligned", failures)
    require(runtime.get("has_v907_browser_qa_enablement") is True, "V907 flag not preserved", failures)
    require(runtime.get("has_v908_screenshot_based_reference_ui_fix") is True, "V908 flag not preserved", failures)
    require(runtime.get("has_v909_browser_qa_pipeline") is True, "V909 browser QA pipeline flag false", failures)
    require(runtime.get("has_v909_visual_fix_queue") is True, "V909 visual fix queue flag false", failures)
    require(runtime.get("v909_browser_qa_pipeline_ready") is True, "runtime pipeline not ready", failures)
    require(int(runtime.get("v909_visual_fix_queue_count") or 0) >= 1, "runtime visual queue count missing", failures)

    assert_zip_clean(failures)

    if failures:
        print("V909 browser QA pipeline check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V909 browser QA pipeline check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
