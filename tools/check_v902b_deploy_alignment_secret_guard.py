from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VERSION = "V902B_DEPLOY_ALIGNMENT_AND_AUTOMATION_SECRET_ROTATION_GUARD_FINAL"
V902 = "V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL"
V903 = "V903_TOTAL_SENTINEL_AUTO_FIX_RENDER_ALIGNMENT_AND_STABILITY_FINAL"
V904 = "V904_AUTONOMOUS_REFERENCE_GAPS_REBUILD_AND_SENTINEL_WORKFORCE_FINAL"
V905 = "V905_FINAL_REFERENCE_GAPS_BROWSER_QA_AND_BOM_FIX_FINAL"
V906 = "V906_REAL_BROWSER_QA_SCREENSHOT_REFERENCE_COMPARISON_FINAL"
V937 = "V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL"
ALLOWED_VERSIONS = {VERSION, V903, V904, V905, V906, V937}
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REPORTS = [
    "reports/V902B_DEPLOY_ALIGNMENT_AND_SECRET_ROTATION_GUARD_REPORT.md",
    "reports/V902B_RENDER_VERSION_ALIGNMENT_QA.md",
    "reports/V902B_SECRET_ROTATION_REQUIRED_QA.md",
    "reports/V902B_SAFE_DEPLOY_ROOT_QA.md",
    "reports/V902B_NEXT_DEPLOYMENT_ACTIONS.md",
]
SAFE_SECRET_VALUES = {
    "",
    "...",
    "***",
    "***hidden***",
    "***missing***",
    "AUTOMATION_SECRET",
    "[redacted]",
    "[configurado",
}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def app_version_from_source(app_py: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", app_py)
    return match.group(1) if match else ""


def scan_query_secret_values(path: Path, text: str) -> list[str]:
    findings: list[str] = []
    for key in ("secret", "token", "api_key", "apikey"):
        for match in re.finditer(rf"{key}=([^\s`'\"&<>)]+)", text, flags=re.IGNORECASE):
            value = match.group(1).strip()
            if value in SAFE_SECRET_VALUES:
                continue
            if value.startswith("{") or value.startswith("$"):
                continue
            if value.startswith("***") or "AUTOMATION_SECRET" in value or value.startswith("codex-") or value.startswith("v"):
                continue
            findings.append(f"{path}: unsafe {key}= placeholder")
    return findings


def scan_reports_for_realish_secrets(failures: list[str]) -> None:
    candidates = list((ROOT / "reports").glob("*.md")) + [ROOT / "tools" / "render_cron_telegram_tick.py"]
    for path in candidates:
        text = path.read_text(encoding="utf-8", errors="replace")
        failures.extend(scan_query_secret_values(path.relative_to(ROOT), text))
        for env_name in ("TELEGRAM_BOT_TOKEN", "STRIPE_SECRET_KEY", "OPENAI_API_KEY"):
            for match in re.finditer(rf"{env_name}=([^\s`]+)", text):
                value = match.group(1).strip()
                if value not in {"...", "***hidden***", "[configurado_en_render]"}:
                    failures.append(f"{path.relative_to(ROOT)}: unsafe {env_name} example")


def validate_release_root(root: Path, failures: list[str]) -> None:
    if not root.exists():
        return
    required = ["app.py", "VERSION.txt", "requirements.txt", "templates", "static", "engines", "tools"]
    for rel in required:
        require((root / rel).exists(), f"deploy root missing {rel}", failures)
    forbidden_names = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output", "logs", "v636work"}
    forbidden_suffixes = {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log", ".zip"}
    for item in root.rglob("*"):
        rel = item.relative_to(root).as_posix()
        parts = set(Path(rel).parts)
        if forbidden_names & parts:
            failures.append(f"deploy root forbidden path: {rel}")
        if item.is_file() and item.suffix.lower() in forbidden_suffixes:
            failures.append(f"deploy root forbidden file: {rel}")


def validate_zip(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    for rel in ["app.py", "VERSION.txt", "requirements.txt", "templates/base.html", "static/app.css"]:
        require(rel in names, f"zip missing root {rel}", failures)
    bad_tokens = ("/.git/", "/.venv/", "__pycache__/", ".pytest_cache/", "release_output/", "v636work/")
    for name in names:
        normalized = f"/{name}"
        if any(token in normalized for token in bad_tokens) or name.lower().endswith((".db", ".sqlite", ".sqlite3", ".log")):
            failures.append(f"zip forbidden entry: {name}")


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    cron = read("tools/render_cron_telegram_tick.py")

    require(read("VERSION.txt").strip().lstrip("\ufeff") in ALLOWED_VERSIONS, "VERSION.txt is not an allowed V902B+ release", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in ALLOWED_VERSIONS, "APP_VERSION file is not an allowed V902B+ release", failures)
    require(app_version_from_source(app_py) in ALLOWED_VERSIONS, "app.py APP_VERSION is not an allowed V902B+ release", failures)
    require("data-v902-shell" in base and "data-v902b-shell" in base, "V902/V902B shell markers missing", failures)
    require("NEMESIS_CACHE_V902B" in app_py or "NEMESIS_CACHE_V903" in app_py or "NEMESIS_CACHE_V904" in app_py or "NEMESIS_CACHE_V905" in app_py or "NEMESIS_CACHE_V906" in app_py, "service worker cache V902B+ missing", failures)
    require("has_v902_sentinel_full_active_issues_fix" in app_py, "V902 runtime flag missing", failures)
    require("has_v902b_deploy_alignment_secret_rotation_guard" in app_py, "V902B runtime flag missing", failures)
    require("mask_secret(" in app_py and "mask_secret_for_url" in app_py, "app.py secret masking helpers missing", failures)
    require('"X-Automation-Secret": automation_secret' in cron, "Cron runner must send secret only in protected header", failures)
    require("?runner=render_cron" in cron, "Cron runner safe URL missing runner", failures)
    require("urlencode({\"secret\"" not in cron and "?secret=" not in cron, "Cron runner still places secret in URL", failures)
    require("secret[-4" not in cron and "tail =" not in cron, "Cron runner still reveals secret tail", failures)

    for report in REPORTS:
        require((ROOT / report).exists(), f"missing report {report}", failures)

    scan_reports_for_realish_secrets(failures)
    validate_release_root(ROOT / "release_output" / "V902B_DEPLOY_ROOT_CONTENTS", failures)
    validate_zip(failures)

    os.environ.setdefault("AUTOMATION_SECRET", "codex-v902b-local-secret")
    import app as app_module

    flask_app = app_module.app
    flask_app.testing = True
    client = flask_app.test_client()
    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json() or {}
    require(runtime_resp.status_code == 200 and runtime.get("app_version") in ALLOWED_VERSIONS, "runtime local is not an allowed V902B+ release", failures)
    require(runtime.get("has_v902_sentinel_full_active_issues_fix") is True, "runtime V902 flag false", failures)
    require(runtime.get("has_v902b_deploy_alignment_secret_rotation_guard") is True, "runtime V902B flag false", failures)
    require(runtime.get("automation_secret_state") == "***configured***", "runtime automation secret state unsafe", failures)
    require(runtime.get("telegram_bot_token_state") in {"***missing***", "***configured***"}, "runtime Telegram token state unsafe", failures)

    no_secret = client.get("/api/automation/telegram/tick?dry_run=1&runner=local_check")
    require(no_secret.status_code == 403, "Telegram tick without secret must be 403", failures)
    with_secret = client.get("/api/automation/telegram/tick?secret=codex-v902b-local-secret&runner=local_check&dry_run=1")
    require(with_secret.status_code == 200 and with_secret.is_json, "Telegram tick dry_run with secret must be JSON 200", failures)
    text = with_secret.get_data(as_text=True)
    require("codex-v902b-local-secret" not in text, "Telegram dry-run leaked local secret", failures)

    if failures:
        print("V902B deploy alignment secret guard check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V902B deploy alignment secret guard check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
