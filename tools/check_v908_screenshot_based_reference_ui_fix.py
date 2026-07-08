from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V908_SCREENSHOT_BASED_REFERENCE_UI_FIX_PASS_FINAL"
ALLOWED_CURRENT_VERSIONS = {
    VERSION,
    "V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL",
    "V910_FULL_PROJECT_HIDDEN_AUDIT_ROUTE_NOT_FOUND_BROWSER_QA_READY_FINAL",
    "V911_REAL_BROWSER_SCREENSHOT_VISUAL_FIX_EXECUTION_FINAL",
    "V911_VIDEO_ADMIN_UI_BINDING_BROWSER_QA_QUEUE_FIX_FINAL",
    "V912_VIDEO_ADMIN_UI_COPY_POLISH_BROWSER_QA_QUEUE_FINAL",
    "V913_BROWSER_QA_EXECUTION_STATUS_TRUTH_AND_RUNTIME_CLEANUP_FINAL",
}
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "reports/V908_SCREENSHOT_BASED_REFERENCE_UI_FIX_REPORT.md",
    "reports/V908_V907_BROWSER_QA_INPUT_AUDIT.md",
    "reports/V908_ADMIN_UI_FIX_QA.md",
    "reports/V908_CLIENT_UI_FIX_QA.md",
    "reports/V908_GAP_REPORT_UPDATE_QA.md",
    "reports/V908_NEXT_STEPS.md",
]


def read(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def require(ok: bool, message: str, failures: list[str]) -> None:
    if not ok:
        failures.append(message)


def app_version_from_source(text: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1) if match else ""


def assert_no_raw_secrets(failures: list[str]) -> None:
    scan_paths = [
        ROOT / "app.py",
        ROOT / "static" / "app.css",
        ROOT / "tools" / "check_v908_screenshot_based_reference_ui_fix.py",
        ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "outbox" / "codex_outbox.md",
    ] + [ROOT / report for report in REPORTS]
    unsafe = re.compile(r"(secret|token|api_key|apikey)=([^\s`'\"&<>)]+)", re.IGNORECASE)
    allowed = {"hidden", "configured", "missing", "***hidden***", "***missing***", "AUTOMATION_SECRET", "$AUTOMATION_SECRET", "..."}
    for path in scan_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in unsafe.finditer(text):
            value = match.group(2).strip()
            normalized = value.strip(",.;")
            if value in allowed or normalized in allowed or normalized in {"?", "token", "secret"} or value.startswith("***") or value.startswith("$") or value.startswith("{") or "AUTOMATION_SECRET" in value:
                continue
            failures.append(f"possible raw secret in {path.relative_to(ROOT)}")
            return


def zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    for rel in ["app.py", "VERSION.txt", "APP_VERSION", "requirements.txt", "templates/base.html", "static/app.css", "reference_images/reference_manifest.json"]:
        require(rel in names, f"zip missing {rel}", failures)
    for name in names:
        normalized = f"/{name}"
        if any(marker in normalized for marker in ["/.git/", "/.venv/", "__pycache__/", ".pytest_cache/", "release_output/", "v636work/"]):
            failures.append(f"zip forbidden entry {name}")
            return
        if name.lower().endswith((".db", ".sqlite", ".sqlite3", ".log", ".zip")):
            failures.append(f"zip forbidden file {name}")
            return


def main() -> int:
    failures: list[str] = []
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    outbox = read("data/runtime/autonomous_company_sentinel/outbox/codex_outbox.md")

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(version_bytes.decode("utf-8").strip() in ALLOWED_CURRENT_VERSIONS, "VERSION.txt is not V908+ compatible", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in ALLOWED_CURRENT_VERSIONS, "APP_VERSION is not V908+ compatible", failures)
    require(app_version_from_source(app_py) in ALLOWED_CURRENT_VERSIONS, "app.py APP_VERSION is not V908+ compatible", failures)
    require("data-v908-shell" in base, "base V908 shell marker missing", failures)
    require("has_v908_screenshot_based_reference_ui_fix" in app_py, "runtime V908 screenshot fix flag missing", failures)
    require("has_v908_reference_ui_safe_fix_pass" in app_py, "runtime V908 safe pass flag missing", failures)

    require("V908 screenshot/reference UI fix" in css, "CSS V908 marker missing", failures)
    for marker in [
        ".v908-admin-shell",
        ".v908-command-grid",
        ".v908-status-chip",
        ".v908-client-dashboard",
        ".v908-match-card",
        ".v908-pick-card",
        ".v908-live-card",
        ".v908-reference-gap-fixed",
        ".v908-mobile-polish",
    ]:
        require(marker in css, f"CSS marker missing {marker}", failures)

    for rel in [
        "templates/admin_dashboard.html",
        "templates/admin_autonomous_company_sentinel.html",
        "templates/admin_sentinel_issues.html",
        "templates/admin_sentinel_codex_outbox.html",
        "templates/client_app_center.html",
        "templates/calendar.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/shark.html",
        "templates/telegram.html",
    ]:
        require("data-v908-template" in read(rel) or "v908-" in read(rel), f"{rel} missing V908 screen marker", failures)

    status_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "browser_qa_status.json"
    comparison_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "browser_reference_comparison.json"
    gap_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "reference_gap_report.json"
    require(status_path.exists(), "browser_qa_status missing", failures)
    require(comparison_path.exists(), "browser_reference_comparison missing", failures)
    require(gap_path.exists(), "reference_gap_report missing", failures)
    if comparison_path.exists():
        comparison = json.loads(comparison_path.read_text(encoding="utf-8-sig", errors="replace"))
        screenshots = int(comparison.get("screenshots_captured") or 0)
        comparison_status_ok = (
            comparison.get("v908_status")
            or comparison.get("v909_browser_qa_pipeline")
            or comparison.get("engine_version") in ALLOWED_CURRENT_VERSIONS
            or comparison.get("version") in ALLOWED_CURRENT_VERSIONS
        )
        require(comparison_status_ok, "comparison missing V908+ visual status", failures)
        if screenshots <= 0:
            visual_status = comparison.get("v908_status") or comparison.get("v909_browser_qa_pipeline") or {}
            pixel_claim = visual_status.get("pixel_perfect_claim_allowed") if isinstance(visual_status, dict) else None
            require(pixel_claim is False or comparison.get("pixel_perfect_claim") is False, "pixel-perfect cannot be allowed without screenshots", failures)
    if gap_path.exists():
        gap = json.loads(gap_path.read_text(encoding="utf-8-sig", errors="replace"))
        gap_status_ok = gap.get("v908_status") or gap.get("v909_browser_qa_pipeline") or gap.get("v913_browser_qa_import_status")
        gap_updates_ok = gap.get("v908_gap_updates") or gap.get("v909_visual_fix_queue") or gap.get("v913_reference_gap_items")
        require(gap_status_ok, "gap report missing V908+ status", failures)
        require(gap_updates_ok, "gap report missing V908+ updates", failures)
        visual_status = gap.get("v908_status") or gap.get("v909_browser_qa_pipeline") or {}
        v913_status = gap.get("v913_browser_qa_import_status") or {}
        require(
            visual_status.get("pixel_perfect_claim_allowed") is False
            or v913_status.get("pixel_perfect_claim_allowed") is False,
            "gap report claims pixel-perfect",
            failures,
        )

    v908_sections_ok = all(section in outbox for section in ["V908_APPLIED_STATIC_FIXES", "V908_SCREENSHOT_BASED_FIXES", "V908_NEEDS_BROWSER_QA", "V908_PENDING_HUMAN_VISUAL_REVIEW", "V908_DANGEROUS_REQUIRES_APPROVAL"])
    v909_sections_ok = "V909_VISUAL_FIX_QUEUE" in outbox and "V909_BLOCKED_NO_SCREENSHOT" in outbox
    v913_sections_ok = "V913_BROWSER_QA_EXECUTION_REQUIRED" in outbox and "V913_BLOCKED_NO_SCREENSHOT" in outbox
    require(v908_sections_ok or v909_sections_ok or v913_sections_ok, "outbox missing V908+ visual sections", failures)
    require("pixel_perfect_claim_allowed: false" in outbox or "pixel_perfect_claim: false" in outbox, "outbox must not allow pixel-perfect", failures)

    for report in REPORTS:
        require((ROOT / report).exists(), f"missing report {report}", failures)
    report_blob = "\n".join(read(report) for report in REPORTS if (ROOT / report).exists()).lower()
    require("pixel-perfect allowed: true" not in report_blob and "pixel_perfect_claim_allowed: true" not in report_blob, "reports must not allow pixel-perfect", failures)

    require('href="/api/admin/continuous-sentinel/run' not in read("templates/admin_continuous_sentinel.html"), "direct admin API href detected", failures)
    require("javascript:void(0)" not in "\n".join(read(path) for path in ["templates/admin_dashboard.html", "templates/client_app_center.html", "templates/picks.html", "templates/live.html"]), "javascript:void(0) visible in key templates", failures)
    require("Ã" not in base and "Â" not in base, "mojibake in base", failures)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    app_module.app.testing = True
    runtime_resp = app_module.app.test_client().get("/api/runtime-version")
    runtime = runtime_resp.get_json(silent=True) or {}
    require(runtime_resp.status_code == 200, "runtime-version not 200", failures)
    require(runtime.get("version") in ALLOWED_CURRENT_VERSIONS, "runtime version is not V908+ compatible", failures)
    require(runtime.get("version_files_match") is True, "runtime version_files_match false", failures)
    require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime deployment alignment not aligned", failures)
    require(runtime.get("has_v907_browser_qa_enablement") is True, "V907 flag not preserved", failures)
    require(runtime.get("has_v908_screenshot_based_reference_ui_fix") is True, "V908 screenshot flag false", failures)
    require(runtime.get("has_v908_reference_ui_safe_fix_pass") is True, "V908 safe pass flag false", failures)
    require(runtime.get("v908_pixel_perfect_claim_allowed") is False, "runtime allows pixel-perfect", failures)

    assert_no_raw_secrets(failures)
    zip_clean(failures)

    if failures:
        print("V908 screenshot reference UI fix check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V908 screenshot reference UI fix check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
