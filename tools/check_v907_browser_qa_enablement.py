from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V907_BROWSER_QA_ENABLEMENT_FIRST_SCREENSHOT_GAP_FIX_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "reports/V907_BROWSER_QA_ENABLEMENT_REPORT.md",
    "reports/V907_PLAYWRIGHT_INSTALL_GUIDE.md",
    "reports/V907_BROWSER_QA_STATUS.md",
    "reports/V907_SCREENSHOT_REFERENCE_COMPARISON_QA.md",
    "reports/V907_CODEX_OUTBOX_SCREENSHOT_PROMPTS.md",
    "reports/V907_NEXT_STEPS.md",
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
        ROOT / "tools" / "check_browser_qa_environment.py",
        ROOT / "tools" / "run_browser_reference_qa.py",
        ROOT / "tools" / "check_v907_browser_qa_enablement.py",
        ROOT / "engines" / "browser_reference_comparison_engine.py",
    ] + [ROOT / report for report in REPORTS]
    unsafe = re.compile(r"(secret|token|api_key|apikey)=([^\s`'\"&<>)]+)", re.IGNORECASE)
    allowed = {"hidden", "configured", "missing", "***hidden***", "***missing***", "AUTOMATION_SECRET", "$AUTOMATION_SECRET", "..."}
    for path in scan_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in unsafe.finditer(text):
            value = match.group(2).strip()
            before = text[max(0, match.start() - 5):match.start()]
            if "?" not in before and "&" not in before and path.name == "app.py":
                continue
            if value in allowed or value.startswith("***") or value.startswith("$") or value.startswith("{"):
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

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(version_bytes.decode("utf-8").strip() == VERSION, "VERSION.txt is not V907", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") == VERSION, "APP_VERSION is not V907", failures)
    require(app_version_from_source(app_py) == VERSION, "app.py APP_VERSION is not V907", failures)
    require("data-v907-shell" in base, "base V907 shell marker missing", failures)
    require("has_v907_browser_qa_enablement" in app_py, "runtime V907 browser flag missing", failures)
    require("has_v907_first_screenshot_gap_fix" in app_py, "runtime V907 screenshot flag missing", failures)
    require("has_v907_playwright_readiness" in app_py, "runtime V907 Playwright flag missing", failures)

    require((ROOT / "tools" / "check_browser_qa_environment.py").exists(), "browser environment check missing", failures)
    runner = ROOT / "tools" / "run_browser_reference_qa.py"
    require(runner.exists(), "browser QA runner missing", failures)
    if runner.exists():
        runner_text = runner.read_text(encoding="utf-8", errors="replace")
        for flag in ["--base-url", "--output", "--mobile", "--desktop", "--admin-safe", "--timeout", "--no-login-required", "--write-json"]:
            require(flag in runner_text, f"browser QA runner missing {flag}", failures)
    require((ROOT / "engines" / "browser_reference_comparison_engine.py").exists(), "browser comparison engine missing", failures)
    require((ROOT / "requirements-browser.txt").exists(), "requirements-browser.txt missing", failures)
    require((ROOT / "reference_images").exists(), "reference_images missing", failures)
    require((ROOT / "reference_images" / "reference_manifest.json").exists(), "reference manifest missing", failures)

    status_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "browser_qa_status.json"
    comparison_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "browser_reference_comparison.json"
    outbox_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "outbox" / "codex_outbox.md"
    require(status_path.exists(), "browser_qa_status.json missing", failures)
    require(comparison_path.exists(), "browser_reference_comparison.json missing", failures)
    require(outbox_path.exists(), "codex outbox missing", failures)
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        require(status.get("version") == VERSION, "browser_qa_status version is not V907", failures)
        require("recommended_install_command" in status, "browser status missing install command", failures)
    if comparison_path.exists():
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        require(comparison.get("engine_version") == VERSION, "comparison engine version is not V907", failures)
        require(comparison.get("pixel_perfect_claim") is False, "comparison must not claim pixel-perfect", failures)
        if int(comparison.get("screenshots_captured") or 0) == 0:
            require(comparison.get("browser_qa_status") == "BROWSER_QA_UNAVAILABLE", "no screenshots must be unavailable", failures)
    if outbox_path.exists():
        outbox = outbox_path.read_text(encoding="utf-8", errors="replace")
        for section in ["V907_BROWSER_QA_FINDINGS", "SCREENSHOT_BASED_VISUAL_PROMPTS", "ADMIN_SCREENSHOT_PROMPTS", "CLIENT_MOBILE_SCREENSHOT_PROMPTS", "PICKS_LIVE_CALENDAR_SCREENSHOT_PROMPTS", "SHARK_TELEGRAM_SCREENSHOT_PROMPTS", "PENDING_BROWSER_QA", "PENDING_HUMAN_VISUAL_REVIEW", "ARCHIVED_STATIC_PROMPTS"]:
            require(section in outbox, f"outbox missing {section}", failures)
        require("pixel_perfect_claim: false" in outbox, "outbox must not claim pixel-perfect", failures)

    for report in REPORTS:
        require((ROOT / report).exists(), f"missing report {report}", failures)
    report_blob = "\n".join(read(report) for report in REPORTS if (ROOT / report).exists()).lower()
    require("pixel-perfect=true" not in report_blob and "pixel perfect aprobado" not in report_blob, "reports must not claim pixel-perfect", failures)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    app_module.app.testing = True
    runtime_resp = app_module.app.test_client().get("/api/runtime-version")
    runtime = runtime_resp.get_json(silent=True) or {}
    require(runtime_resp.status_code == 200, "runtime-version not 200", failures)
    require(runtime.get("version") == VERSION, "runtime version is not V907", failures)
    require(runtime.get("version_files_match") is True, "runtime version_files_match false", failures)
    require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime deployment alignment not aligned", failures)
    require(runtime.get("has_v906_real_browser_qa") is True, "V906 browser flag not preserved", failures)
    require(runtime.get("has_v906_screenshot_reference_comparison") is True, "V906 comparison flag not preserved", failures)
    require(runtime.get("has_v906b_public_home_html_artifact_cleanup") is True, "V906B flag not preserved", failures)
    require(runtime.get("has_v907_browser_qa_enablement") is True, "V907 browser flag false", failures)
    require(runtime.get("has_v907_first_screenshot_gap_fix") is True, "V907 screenshot flag false", failures)
    require(runtime.get("has_v907_playwright_readiness") is True, "V907 Playwright readiness flag false", failures)

    assert_no_raw_secrets(failures)
    zip_clean(failures)

    if failures:
        print("V907 browser QA enablement check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V907 browser QA enablement check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
