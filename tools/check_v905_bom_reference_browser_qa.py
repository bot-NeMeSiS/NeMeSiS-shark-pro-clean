from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V905_FINAL_REFERENCE_GAPS_BROWSER_QA_AND_BOM_FIX_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "reports/V905_FINAL_REFERENCE_GAPS_BROWSER_QA_AND_BOM_FIX_REPORT.md",
    "reports/V905_VERSION_BOM_ALIGNMENT_QA.md",
    "reports/V905_PUBLIC_HTML_MOJIBAKE_QA.md",
    "reports/V905_REFERENCE_GAPS_FINAL_STATUS.md",
    "reports/V905_BROWSER_QA_STATUS.md",
    "reports/V905_NEXT_STEPS.md",
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
        ROOT / "tools" / "check_v905_bom_reference_browser_qa.py",
    ] + [ROOT / report for report in REPORTS]
    unsafe = re.compile(r"(secret|token|api_key|apikey)=([^\s`'\"&<>)]+)", re.IGNORECASE)
    allowed = {"hidden", "configured", "missing", "***hidden***", "***missing***", "AUTOMATION_SECRET", "..."}
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
    forbidden = ["/.git/", "/.venv/", "__pycache__/", ".pytest_cache/", "release_output/", "v636work/"]
    for name in names:
        normalized = f"/{name}"
        if any(marker in normalized for marker in forbidden) or name.lower().endswith((".db", ".sqlite", ".sqlite3", ".log", ".zip")):
            failures.append(f"zip forbidden entry {name}")
            return


def main() -> int:
    failures: list[str] = []
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    app_py = read("app.py")
    base = read("templates/base.html")
    home = read("templates/home.html")

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt still has UTF-8 BOM", failures)
    require(version_bytes.decode("utf-8").strip() == VERSION, "VERSION.txt is not exact V905", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") == VERSION, "APP_VERSION is not V905", failures)
    require(app_version_from_source(app_py) == VERSION, "app.py APP_VERSION is not V905", failures)
    require("clean_version_text" in app_py, "clean_version_text helper missing", failures)
    require("has_v905_bom_version_alignment_fix" in app_py, "V905 BOM runtime flag missing", failures)
    require("has_v905_final_reference_gaps_browser_qa" in app_py, "V905 browser QA runtime flag missing", failures)
    require("data-v905-shell" in base, "base V905 shell marker missing", failures)
    require("NEMESIS_CACHE_V905" in app_py and "res.status===404" in app_py, "service worker V905 404 safety missing", failures)
    require("experiencia nica" not in home, "home still has broken 'experiencia nica' copy", failures)
    require("Membresias" not in base, "base still has visible Membresias without accent", failures)

    require((ROOT / "reference_images").exists(), "reference_images missing", failures)
    manifest_path = ROOT / "reference_images" / "reference_manifest.json"
    require(manifest_path.exists(), "reference_manifest missing", failures)
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        require(int(manifest.get("reference_count") or 0) >= 16, "reference manifest has fewer than 16 images", failures)

    gap_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "reference_gap_report.json"
    require(gap_path.exists(), "reference gap report missing", failures)
    if gap_path.exists():
        gap = json.loads(gap_path.read_text(encoding="utf-8"))
        v905 = gap.get("v905_final_status") or {}
        require(v905.get("status") == "V905_FINAL_STATUS", "V905 gap final status missing", failures)
        require(int(v905.get("gaps_pending_before") or 0) == 6, "V905 gaps pending before must be 6 from Render V904", failures)
        require(bool(v905.get("still_pending_browser_qa")), "V905 pending browser QA list missing", failures)

    outbox = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "outbox" / "codex_outbox.md"
    require(outbox.exists(), "codex outbox missing", failures)
    if outbox.exists():
        outbox_text = outbox.read_text(encoding="utf-8", errors="replace")
        require("V905_FINAL_REFERENCE_GAPS_BROWSER_QA_STATUS" in outbox_text, "outbox V905 status section missing", failures)
        require("pixel_perfect_claim: false" in outbox_text, "outbox must keep pixel-perfect claim false", failures)

    for report in REPORTS:
        require((ROOT / report).exists(), f"missing report {report}", failures)

    os.environ.setdefault("AUTOMATION_SECRET", "codex-v905-local-secret")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    flask_app = app_module.app
    flask_app.testing = True
    client = flask_app.test_client()
    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json(silent=True) or {}
    require(runtime_resp.status_code == 200, "runtime-version not 200", failures)
    require(runtime.get("app_version") == VERSION, "runtime app_version is not V905", failures)
    require(runtime.get("version_txt") == VERSION, "runtime version_txt is not clean V905", failures)
    require(runtime.get("version_files_match") is True, "runtime version_files_match is not true", failures)
    require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime deployment alignment is not aligned", failures)
    require(runtime.get("has_v905_bom_version_alignment_fix") is True, "runtime V905 BOM flag false", failures)
    require(runtime.get("has_v905_final_reference_gaps_browser_qa") is True, "runtime V905 browser QA flag false", failures)

    home_resp = client.get("/")
    home_html = home_resp.get_data(as_text=True)
    require(home_resp.status_code == 200, "/ did not return 200", failures)
    require(not home_html.startswith("\ufeff"), "public home starts with BOM", failures)
    require(not home_html[:20].strip().lower().startswith("rn"), "public home starts with visible rn", failures)
    for bad in ["Ã", "Â", "�", "None", "undefined"]:
        require(bad not in home_html[:5000], f"public home contains visible bad marker {bad!r} near top", failures)
    report_blob = " ".join(read(report) for report in REPORTS).lower()
    require("pixel-perfect=true" not in report_blob and "pixel perfect aprobado" not in report_blob, "reports must not claim pixel-perfect", failures)

    assert_no_raw_secrets(failures)
    zip_clean(failures)

    if failures:
        print("V905 BOM/reference/browser QA check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V905 BOM/reference/browser QA check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
