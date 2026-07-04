from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = "V895_RENDER_V894_DEPLOYMENT_ALIGNMENT_FINAL"
V894_VERSION = "V894_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL"
V894_ZIP = ROOT / "release_output" / "NeMeSiS_SHARK_PRO_V894_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL_RENDER_READY.zip"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def app_version_from_source(app_py: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", app_py)
    return match.group(1) if match else ""


def assert_zip_clean(failures: list[str]) -> None:
    require(V894_ZIP.exists(), f"V894 ZIP missing: {V894_ZIP}", failures)
    if not V894_ZIP.exists():
        return
    required = {
        "app.py",
        "VERSION.txt",
        "requirements.txt",
        "templates/base.html",
        "static/app.css",
        "engines/autonomous_company_sentinel_engine.py",
        "engines/sentinel_user_admin_journey_engine.py",
        "engines/sentinel_reference_visual_engine.py",
        "engines/sentinel_codex_outbox_engine.py",
        "engines/sentinel_safe_autofix_engine.py",
        "engines/sentinel_render_alignment_engine.py",
        "engines/sentinel_telegram_quality_watch_engine.py",
        "templates/admin_autonomous_company_sentinel.html",
        "templates/admin_sentinel_codex_outbox.html",
        "tools/run_autonomous_company_sentinel.py",
        "tools/check_v892_autonomous_company_sentinel.py",
        "tools/export_sentinel_codex_outbox.py",
        "tools/run_reference_visual_scan.py",
    }
    forbidden_prefixes = (".git/", ".venv/", "release_output/", "__pycache__/", ".pytest_cache/", "v636work/")
    forbidden_suffixes = (".zip", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log")
    with zipfile.ZipFile(V894_ZIP) as archive:
        names = set(archive.namelist())
        missing = sorted(required - names)
        forbidden = sorted(
            name
            for name in names
            if name.startswith(forbidden_prefixes) or name.endswith(forbidden_suffixes)
        )
        version_txt = archive.read("VERSION.txt").decode("utf-8-sig").strip()
        app_py = archive.read("app.py").decode("utf-8", errors="replace")
    require(not missing, f"V894 ZIP missing required files: {missing}", failures)
    require(not forbidden, f"V894 ZIP contains forbidden files: {forbidden[:20]}", failures)
    require(version_txt == V894_VERSION, f"V894 ZIP VERSION.txt is {version_txt}", failures)
    require(app_version_from_source(app_py) == V894_VERSION, "V894 ZIP app.py APP_VERSION mismatch", failures)


def main() -> int:
    failures: list[str] = []
    version_txt = read_text(ROOT / "VERSION.txt").strip()
    app_version_file = read_text(ROOT / "APP_VERSION").strip()
    app_py = read_text(ROOT / "app.py")
    base_html = read_text(ROOT / "templates" / "base.html")

    require(version_txt == CURRENT_VERSION, f"VERSION.txt is {version_txt}", failures)
    require(app_version_file == CURRENT_VERSION, f"APP_VERSION file is {app_version_file}", failures)
    require(app_version_from_source(app_py) == CURRENT_VERSION, "app.py APP_VERSION is not V895", failures)
    require(CURRENT_VERSION in base_html, "base.html does not expose V895 cache/runtime marker", failures)

    for rel in [
        "engines/autonomous_company_sentinel_engine.py",
        "engines/sentinel_user_admin_journey_engine.py",
        "engines/sentinel_reference_visual_engine.py",
        "engines/sentinel_codex_outbox_engine.py",
        "engines/sentinel_safe_autofix_engine.py",
        "engines/sentinel_render_alignment_engine.py",
        "engines/sentinel_telegram_quality_watch_engine.py",
        "templates/admin_autonomous_company_sentinel.html",
        "templates/admin_sentinel_codex_outbox.html",
        "tools/run_autonomous_company_sentinel.py",
    ]:
        require((ROOT / rel).exists(), f"Missing V894 workforce artifact: {rel}", failures)

    required_routes = [
        "/admin/autonomous-company-sentinel",
        "/admin/sentinel-codex-outbox",
        "/api/admin/autonomous-company-sentinel/status",
        "/api/admin/autonomous-company-sentinel/outbox",
        "/api/automation/autonomous-company-sentinel/run",
    ]
    for route in required_routes:
        require(route in app_py, f"Missing route: {route}", failures)

    for marker in [
        "expected_version",
        "runtime_version",
        "version_files_match",
        "current_working_directory",
        "build_generated_at",
        "render_service_hint",
        "git_commit_hint",
        "deployment_alignment_status",
        "has_v895_render_v894_deployment_alignment",
        "has_v894_autonomous_company_sentinel_workforce",
        "has_v892_autonomous_company_sentinel",
    ]:
        require(marker in app_py, f"Runtime diagnostic marker missing: {marker}", failures)

    require("V892_SENTINEL_ISSUES_COMMAND_CENTER_COPY_FIX_PROMPTS_FINAL" not in version_txt, "VERSION.txt still points to V892", failures)
    require("V892_SENTINEL_ISSUES_COMMAND_CENTER_COPY_FIX_PROMPTS_FINAL" not in app_version_file, "APP_VERSION file still points to V892", failures)
    require("V892_SENTINEL_ISSUES_COMMAND_CENTER_COPY_FIX_PROMPTS_FINAL" not in app_version_from_source(app_py), "app.py APP_VERSION still points to V892", failures)

    assert_zip_clean(failures)

    sys.path.insert(0, str(ROOT))
    import app as nemesis_app  # noqa: WPS433

    client = nemesis_app.app.test_client()
    response = client.get("/api/runtime-version")
    require(response.status_code == 200, f"/api/runtime-version status {response.status_code}", failures)
    payload = response.get_json(silent=True) or {}
    require(payload.get("app_version") == CURRENT_VERSION, f"runtime app_version is {payload.get('app_version')}", failures)
    require(payload.get("runtime_version") == CURRENT_VERSION, f"runtime_version is {payload.get('runtime_version')}", failures)
    require(payload.get("version_txt") == CURRENT_VERSION, f"runtime version_txt is {payload.get('version_txt')}", failures)
    require(payload.get("version_files_match") is True, "runtime version_files_match is not true", failures)
    require(payload.get("has_v895_render_v894_deployment_alignment") is True, "runtime V895 flag false", failures)
    require(payload.get("has_v894_autonomous_company_sentinel_workforce") is True, "runtime V894 flag false", failures)
    require(payload.get("has_v892_autonomous_company_sentinel") is True, "runtime V892 company sentinel flag false", failures)

    if failures:
        print("V895 render alignment check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V895 render alignment check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
