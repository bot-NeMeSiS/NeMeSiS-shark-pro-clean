from __future__ import annotations

import ast
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V922_VISIBLE_PRODUCT_EXPERIENCE_CLIENT_ADMIN_SPORTS_UPGRADE_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def app_version(source: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                    return str(getattr(node.value, "value", ""))
    return ""


def zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = [name.replace("\\", "/") for name in zf.namelist()]
    required = [
        "app.py",
        "VERSION.txt",
        "APP_VERSION",
        "requirements.txt",
        "templates/home.html",
        "templates/client_app_center.html",
        "templates/admin_dashboard.html",
        "static/app.css",
        "tools/check_v922_visible_product_experience.py",
        "reports/V922_VISIBLE_PRODUCT_EXPERIENCE_REPORT.md",
    ]
    for rel in required:
        require(rel in names, f"zip missing {rel}", failures)
    forbidden_bits = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", "logs/")
    for name in names:
        if name.endswith((".zip", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm")) or any(bit in name for bit in forbidden_bits):
            failures.append(f"zip forbidden entry {name}")
            break


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    css = read("static/app.css")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    local_version = version_bytes.decode("utf-8").strip()

    require(not version_bytes.startswith(b"\xef\xbb\xbf"), "VERSION.txt has BOM", failures)
    require(local_version == VERSION, "VERSION.txt is not V922", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") == VERSION, "APP_VERSION is not V922", failures)
    require(app_version(app_py) == VERSION, "app.py APP_VERSION is not V922", failures)
    require("NEMESIS_CACHE_V922" in app_py, "service worker cache V922 missing", failures)

    expected_templates = {
        "templates/home.html": ["v922-home-hero", "v922-home-grid", "v922-home-status-card", "v922-home-plan-card", "v922-home-trust-strip"],
        "templates/client_app_center.html": ["v922-client-dashboard", "v922-client-quick-grid", "v922-client-empty-premium"],
        "templates/calendar.html": ["v922-calendar-shell", "v922-match-card", "Partido pendiente de confirmar"],
        "templates/live.html": ["v922-live-shell", "v922-live-filter-row", "v922-live-empty-state", "v922-live-match-card"],
        "templates/picks.html": ["v922-picks-shell", "v922-pick-quality-strip", "v922-no-picks-premium"],
        "templates/shark.html": ["v922-shark-safe-mode", "Modo seguro activo", "Cuota pendiente"],
        "templates/telegram.html": ["v922-telegram-premium", "No filler", "Dedupe"],
        "templates/admin_dashboard.html": ["v922-admin-command-center", "v922-admin-kpi-grid", "v922-admin-next-action"],
        "templates/admin_automation_workforce.html": ["v922-workforce-visible-status", "Browser QA", "Pixel-perfect sigue bloqueado"],
    }
    for rel, markers in expected_templates.items():
        text = read(rel)
        for marker in markers:
            require(marker in text, f"{rel} missing {marker}", failures)

    for marker in [
        "V922 visible product experience upgrade",
        ".v922-client-dashboard",
        ".v922-admin-command-center",
        ".v922-live-shell",
        ".v922-picks-shell",
        ".v922-home-hero",
    ]:
        require(marker in css, f"CSS missing {marker}", failures)

    for flag in [
        "has_v922_visible_product_experience_upgrade",
        "has_v922_home_visible_premium_upgrade",
        "has_v922_client_dashboard_visible_upgrade",
        "has_v922_admin_command_center_visible_upgrade",
        "has_v922_sports_screens_visible_upgrade",
    ]:
        require(flag in app_py, f"runtime flag missing: {flag}", failures)

    for report in [
        "reports/V922_VISIBLE_PRODUCT_EXPERIENCE_REPORT.md",
        "reports/V922_HOME_PUBLIC_VISIBLE_UPGRADE_QA.md",
        "reports/V922_CLIENT_DASHBOARD_VISIBLE_UPGRADE_QA.md",
        "reports/V922_SPORTS_SCREENS_VISIBLE_UPGRADE_QA.md",
        "reports/V922_PICKS_SHARK_TELEGRAM_VISIBLE_UPGRADE_QA.md",
        "reports/V922_ADMIN_COMMAND_CENTER_VISIBLE_UPGRADE_QA.md",
        "reports/V922_NEXT_STEPS.md",
    ]:
        require((ROOT / report).exists(), f"missing report {report}", failures)

    combined = "\n".join(read(rel) for rel in expected_templates) + "\n" + app_py + "\n" + css
    for term in ["sk_live_", "xoxb-", "ghp_", "rnd_", "TELEGRAM_BOT_TOKEN=", "RENDER_DEPLOY_HOOK_URL=https://"]:
        require(term not in combined, f"possible secret term found: {term}", failures)
    require("pixel_perfect_claim_allowed\": true" not in combined, "pixel-perfect claimed without screenshots", failures)
    require("Capturas0" not in combined and "Comparaciones18" not in combined, "raw Browser QA counters exposed as cramped copy", failures)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    runtime = client.get("/api/runtime-version")
    payload = runtime.get_json(silent=True) or {}
    require(runtime.status_code == 200, "runtime-version not 200", failures)
    require(payload.get("version") == VERSION, "runtime version is not V922", failures)
    require(payload.get("version_files_match") is True, "version_files_match is not true", failures)
    require(payload.get("deployment_alignment_status") == "aligned_local_files", "deployment alignment not local-aligned", failures)
    for flag in [
        "has_v922_visible_product_experience_upgrade",
        "has_v922_home_visible_premium_upgrade",
        "has_v922_client_dashboard_visible_upgrade",
        "has_v922_admin_command_center_visible_upgrade",
        "has_v922_sports_screens_visible_upgrade",
    ]:
        require(payload.get(flag) is True, f"runtime flag false: {flag}", failures)
    require(payload.get("v922_browser_qa_still_required") is True, "Browser QA should remain required without screenshots", failures)
    require(payload.get("v922_next_required_action") == "run_browser_qa_for_visual_evidence", "V922 next action should request Browser QA evidence", failures)

    zip_clean(failures)
    if failures:
        print("V922 visible product experience check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V922 visible product experience check OK")
    print(json.dumps({"version": VERSION, "visible_product_pass": "static_visible_product_pass"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
