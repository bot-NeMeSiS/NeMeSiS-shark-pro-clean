from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V906B_PUBLIC_HOME_HTML_ARTIFACT_CLEANUP_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "reports/V906B_PUBLIC_HOME_HTML_ARTIFACT_CLEANUP_REPORT.md",
    "reports/V906B_VISIBLE_ARTIFACTS_QA.md",
    "reports/V906B_NEXT_STEPS.md",
]


def read(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def app_version_from_source(text: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1) if match else ""


def require(ok: bool, message: str, failures: list[str]) -> None:
    if not ok:
        failures.append(message)


def zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    required = ["app.py", "VERSION.txt", "APP_VERSION", "requirements.txt", "templates/base.html", "templates/home.html", "static/app.css"]
    for rel in required:
        require(rel in names, f"zip missing {rel}", failures)
    forbidden_dirs = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output", "logs"}
    for name in names:
        parts = set(Path(name).parts)
        if parts & forbidden_dirs or name.lower().endswith((".db", ".sqlite", ".sqlite3", ".log", ".zip")):
            failures.append(f"zip forbidden entry {name}")
            return


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    home = read("templates/home.html")
    css_bytes = (ROOT / "static" / "app.css").read_bytes()
    version_bytes = (ROOT / "VERSION.txt").read_bytes()

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has UTF-8 BOM", failures)
    require(not css_bytes.startswith(b"\xef\xbb\xbf"), "static/app.css has UTF-8 BOM", failures)
    require(read("VERSION.txt").strip().lstrip("\ufeff") == VERSION, "VERSION.txt is not V906B", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") == VERSION, "APP_VERSION is not V906B", failures)
    require(app_version_from_source(app_py) == VERSION, "app.py APP_VERSION is not V906B", failures)
    require("data-v906b-shell" in base, "base V906B shell marker missing", failures)
    require("has_v906b_public_home_html_artifact_cleanup" in app_py, "runtime V906B flag missing", failures)
    require("`r`n" not in base and "rn rn" not in base.lower(), "base still contains visible newline artifact", failures)
    require(not base.startswith("\ufeff") and base.lstrip().lower().startswith("<!doctype html"), "base.html does not start cleanly", failures)
    require("NeMeSiS SHARK PRO rn" not in home and "rn rn" not in home.lower(), "home template still contains rn artifact", failures)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    app_module.app.testing = True
    client = app_module.app.test_client()
    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json(silent=True) or {}
    require(runtime_resp.status_code == 200, "runtime-version not 200", failures)
    require(runtime.get("version") == VERSION, "runtime version is not V906B", failures)
    require(runtime.get("version_txt") == VERSION, "runtime version_txt is not V906B", failures)
    require(runtime.get("app_version") == VERSION, "runtime app_version is not V906B", failures)
    require(runtime.get("version_files_match") is True, "runtime version_files_match is not true", failures)
    require(runtime.get("deployment_alignment_status") == "aligned_local_files", "runtime deployment alignment is not aligned", failures)
    require(runtime.get("has_v906b_public_home_html_artifact_cleanup") is True, "runtime V906B flag is not true", failures)

    home_resp = client.get("/")
    html = home_resp.get_data(as_text=True)
    visible = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.I | re.S)
    visible = re.sub(r"<style\b[^>]*>.*?</style>", "", visible, flags=re.I | re.S)
    visible = re.sub(r"<!--.*?-->", "", visible, flags=re.S)
    visible = re.sub(r"<[^>]+>", " ", visible)
    visible = re.sub(r"\s+", " ", visible).strip()
    require(home_resp.status_code == 200, "/ not 200", failures)
    require(html.lstrip("\ufeff\r\n\t ").lower().startswith("<!doctype html"), "/ does not start with clean doctype", failures)
    require("\ufeff" not in html[:500], "/ contains BOM near start", failures)
    require(not re.search(r"(?i)(NeMeSiS\s+SHARK\s+PRO\s+rn\b|\brn\s+rn\b|`r`n|\\\\r\\\\n)", visible[:2500]), "/ contains visible rn artifact", failures)
    require(not re.search(r"\b(None|null|undefined)\b", visible[:2500], re.I), "/ contains visible None/null/undefined near top", failures)
    for bad in ["Ã", "Â", "�", "ï¿½"]:
        require(bad not in visible[:2500], f"/ contains mojibake marker {bad!r}", failures)

    for report in REPORTS:
        require((ROOT / report).exists(), f"missing report {report}", failures)

    artifact_check = ROOT / "tools" / "check_no_visible_artifacts.py"
    require(artifact_check.exists(), "check_no_visible_artifacts.py missing", failures)
    zip_clean(failures)

    if failures:
        print("V906B public home artifact cleanup check FAILED")
        for failure in failures:
            print(f"- {failure}")
        print(json.dumps({"version": VERSION, "failures": failures}, ensure_ascii=False, indent=2))
        return 1
    print("V906B public home artifact cleanup check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
