from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V906_REAL_BROWSER_QA_SCREENSHOT_REFERENCE_COMPARISON_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "reports/V906_REAL_BROWSER_QA_SCREENSHOT_REFERENCE_COMPARISON_REPORT.md",
    "reports/V906_BROWSER_QA_ENVIRONMENT.md",
    "reports/V906_BROWSER_QA_STATUS.md",
    "reports/V906_SCREENSHOT_REFERENCE_GAP_REPORT.md",
    "reports/V906_CODEX_OUTBOX_SCREENSHOT_PROMPTS.md",
    "reports/V906_NEXT_STEPS.md",
]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


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
        ROOT / "tools" / "check_v906_real_browser_qa.py",
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
            if "AUTOMATION_SECRET" in value:
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
    require(version_bytes.decode("utf-8").strip() == VERSION, "VERSION.txt is not V906", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") == VERSION, "APP_VERSION is not V906", failures)
    require(app_version_from_source(app_py) == VERSION, "app.py APP_VERSION is not V906", failures)
    require("data-v906-shell" in base, "base V906 shell marker missing", failures)
    require("NEMESIS_CACHE_V906" in app_py, "service worker V906 cache missing", failures)
    require("has_v906_real_browser_qa" in app_py, "runtime V906 browser flag missing", failures)
    require("has_v906_screenshot_reference_comparison" in app_py, "runtime V906 comparison flag missing", failures)

    require((ROOT / "tools" / "check_browser_qa_environment.py").exists(), "browser environment check missing", failures)
    require((ROOT / "tools" / "run_browser_reference_qa.py").exists(), "browser QA runner missing", failures)
    require((ROOT / "engines" / "browser_reference_comparison_engine.py").exists(), "browser comparison engine missing", failures)
    require((ROOT / "reference_images").exists(), "reference_images missing", failures)
    require((ROOT / "reference_images" / "reference_manifest.json").exists(), "reference manifest missing", failures)

    gap_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "reference_gap_report.json"
    outbox_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "outbox" / "codex_outbox.md"
    comparison_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "browser_reference_comparison.json"
    require(gap_path.exists(), "reference gap report missing", failures)
    require(outbox_path.exists(), "outbox missing", failures)
    require(comparison_path.exists(), "browser comparison json missing", failures)
    if gap_path.exists():
        gap = json.loads(gap_path.read_text(encoding="utf-8"))
        require("v906_browser_reference_status" in gap, "gap report missing V906 browser status", failures)
        require("v906_browser_gap_report" in gap, "gap report missing V906 browser gap list", failures)
    if outbox_path.exists():
        outbox = outbox_path.read_text(encoding="utf-8", errors="replace")
        for section in ["V906_BROWSER_QA_FINDINGS", "SCREENSHOT_BASED_VISUAL_PROMPTS", "ADMIN_VISUAL_PROMPTS", "CLIENT_MOBILE_PROMPTS", "PICKS_LIVE_CALENDAR_PROMPTS", "SHARK_TELEGRAM_PROMPTS", "PENDING_HUMAN_REVIEW", "ARCHIVED_STATIC_PROMPTS"]:
            require(section in outbox, f"outbox missing {section}", failures)
        require("pixel_perfect_claim: false" in outbox, "outbox must not claim pixel-perfect", failures)

    if comparison_path.exists():
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        if int(comparison.get("screenshots_captured") or 0) == 0:
            require(comparison.get("browser_qa_status") == "BROWSER_QA_UNAVAILABLE", "no screenshots must be marked unavailable", failures)
            report_blob = "\n".join(read(r) for r in REPORTS if (ROOT / r).exists()).lower()
            require("pixel-perfect" not in report_blob or "no se declara pixel-perfect" in report_blob, "reports must not claim pixel-perfect without screenshots", failures)

    for report in REPORTS:
        require((ROOT / report).exists(), f"missing report {report}", failures)

    os.environ.setdefault("AUTOMATION_SECRET", "codex-v906-local-secret")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    flask_app = app_module.app
    flask_app.testing = True
    runtime_resp = flask_app.test_client().get("/api/runtime-version")
    runtime = runtime_resp.get_json(silent=True) or {}
    require(runtime_resp.status_code == 200, "runtime-version not 200", failures)
    require(runtime.get("app_version") == VERSION, "runtime app_version is not V906", failures)
    require(runtime.get("version_txt") == VERSION, "runtime version_txt is not V906", failures)
    require(runtime.get("version_files_match") is True, "runtime version_files_match false", failures)
    require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime deployment alignment not aligned", failures)
    require(runtime.get("has_v905_bom_version_alignment_fix") is True, "V905 BOM flag not preserved", failures)
    require(runtime.get("has_v906_real_browser_qa") is True, "runtime V906 browser flag false", failures)
    require(runtime.get("has_v906_screenshot_reference_comparison") is True, "runtime V906 comparison flag false", failures)

    assert_no_raw_secrets(failures)
    zip_clean(failures)

    if failures:
        print("V906 real browser QA check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V906 real browser QA check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
