from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERSION = "V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL"
V902B_VERSION = "V902B_DEPLOY_ALIGNMENT_AND_AUTOMATION_SECRET_ROTATION_GUARD_FINAL"
V903_VERSION = "V903_TOTAL_SENTINEL_AUTO_FIX_RENDER_ALIGNMENT_AND_STABILITY_FINAL"
ALLOWED_VERSIONS = {VERSION, V902B_VERSION, V903_VERSION}
REQUIRED_REPORTS = [
    "reports/V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_REPORT.md",
    "reports/V902_SENTINEL_ACTIVE_ISSUES_INVENTORY.md",
    "reports/V902_STALE_FALSE_POSITIVE_RECONCILIATION_QA.md",
    "reports/V902_CODEX_OUTBOX_TRUTH_QA.md",
    "reports/V902_ADMIN_AND_API_FIX_QA.md",
    "reports/V902_TELEGRAM_SENTINEL_QA.md",
    "reports/V902_REFERENCE_GAPS_STATUS.md",
    "reports/V902_NEXT_STEPS.md",
]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def app_version_from_source(app_py: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", app_py)
    return match.group(1) if match else ""


def csrf_from_html(html: str) -> str:
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    return match.group(1) if match else ""


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    outbox = read("data/runtime/autonomous_company_sentinel/codex_outbox.md")

    require(read("VERSION.txt").strip().lstrip("\ufeff") in ALLOWED_VERSIONS, "VERSION.txt is not an allowed V902+ release", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in ALLOWED_VERSIONS, "APP_VERSION file is not an allowed V902+ release", failures)
    require(app_version_from_source(app_py) in ALLOWED_VERSIONS, "app.py APP_VERSION is not an allowed V902+ release", failures)
    require("NEMESIS_CACHE_V902" in app_py or "NEMESIS_CACHE_V902B" in app_py or "NEMESIS_CACHE_V903" in app_py, "service worker cache V902+ missing", failures)
    require("has_v902_sentinel_full_active_issues_fix" in app_py, "runtime V902 flag missing", failures)
    require('data-v902-shell="true"' in base, "base V902 shell marker missing", failures)

    for report in REQUIRED_REPORTS:
        require((ROOT / report).exists(), f"missing report {report}", failures)

    for header in [
        "## ACTIVE_FIX_PROMPTS",
        "## VISUAL_REFERENCE_PROMPTS",
        "## FUNCTIONAL_PROMPTS",
        "## ADMIN_PROMPTS",
        "## TELEGRAM_PROMPTS",
        "## ARCHIVED_OBSOLETE_PROMPTS",
        "## FALSE_POSITIVE_PROMPTS",
    ]:
        require(header in outbox, f"outbox header missing: {header}", failures)

    from tools.reconcile_v902_sentinel_truth import run_reconciliation

    truth = run_reconciliation(write=True)
    require(truth.get("sentinel_active_issues_count") == 0, "active Sentinel issues remain after V902 reconciliation", failures)
    require(truth.get("sentinel_critical_active_count") == 0, "critical Sentinel issues remain", failures)
    require(truth.get("sentinel_high_active_count") == 0, "high Sentinel issues remain", failures)
    require(truth.get("sentinel_resolved_by_rescan_count", 0) >= 1, "resolved-by-rescan count missing", failures)

    import app as app_module

    flask_app = app_module.app
    flask_app.testing = True
    client = flask_app.test_client()

    runtime_resp = client.get("/api/runtime-version")
    runtime = runtime_resp.get_json() or {}
    require(runtime_resp.status_code == 200 and runtime_resp.is_json, "runtime-version not JSON 200", failures)
    require(runtime.get("app_version") in ALLOWED_VERSIONS, "runtime app_version is not an allowed V902+ release", failures)
    require(runtime.get("has_v902_sentinel_full_active_issues_fix") is True, "runtime V902 flag false", failures)
    require(runtime.get("sentinel_active_issues_count") == 0, "runtime active issues not zero", failures)
    require(runtime.get("codex_outbox_visual_prompts", 0) >= 1, "runtime visual outbox count missing", failures)

    no_session_api = client.get("/api/admin/continuous-sentinel/run?mode=client&dry_run=1")
    require(no_session_api.status_code == 403 and no_session_api.is_json, "admin continuous API without session must be JSON 403", failures)

    admin_login = client.get("/admin-login")
    admin_login_html = admin_login.get_data(as_text=True)
    require(admin_login.status_code == 200, "/admin-login not 200", failures)
    require('data-nav-zone="client-bottom"' not in admin_login_html, "client bottom nav appears on admin-login", failures)
    require('<aside class="ns-client-sidebar"' not in admin_login_html, "client sidebar appears on admin-login", failures)
    require('<div class="shark-widget"' not in admin_login_html, "floating SHARK appears on admin-login", failures)

    with client.session_transaction() as sess:
        sess["user_id"] = "admin-test"
        sess["user_name"] = "Admin Test"
        sess["user_role"] = "ADMIN"
        sess["membership"] = "ADMIN"
        sess["user_membership"] = "ADMIN"

    admin_page = client.get("/admin/continuous-sentinel")
    token = csrf_from_html(admin_page.get_data(as_text=True))
    require(admin_page.status_code == 200 and token, "admin continuous page not 200 with CSRF", failures)
    run_resp = client.post(
        "/api/admin/continuous-sentinel/run?mode=client&dry_run=1",
        json={"mode": "client", "dry_run": True, "csrf_token": token},
        headers={"X-CSRF-Token": token},
    )
    payload = run_resp.get_json() or {}
    require(run_resp.status_code == 200 and run_resp.is_json and payload.get("dry_run") is True, "admin continuous dry-run not JSON 200", failures)

    for route in ["/partidos", "/calendar", "/live", "/picks", "/shark"]:
        html = client.get(route).get_data(as_text=True)
        require("�" not in html and "Ãƒ" not in html and "ï¿½" not in html, f"mojibake visible on {route}", failures)
        require(
            any(token in html for token in ["Sin partidos reales", "Sin directos reales", "Sin picks activos", "Modo seguro activo", "Resultado pendiente", "Esperando proveedor"]),
            f"safe state missing on {route}",
            failures,
        )

    unsafe_templates = "\n".join(
        read(path) for path in [
            "templates/admin_continuous_sentinel.html",
            "templates/admin_sentinel_workflow.html",
            "templates/admin_shark_sentinel.html",
        ]
    )
    require('href="/api/admin/continuous-sentinel/run' not in unsafe_templates, "direct API navigation remains in admin Sentinel templates", failures)
    require("javascript:void" not in unsafe_templates and 'href="#"' not in unsafe_templates, "dead admin link remains", failures)

    if failures:
        print("V902 Sentinel full active issues truth cleanup check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V902 Sentinel full active issues truth cleanup check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
