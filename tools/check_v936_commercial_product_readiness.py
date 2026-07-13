"""Focused release guard for V936 commercial product readiness."""
from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_VERSION = "V936_COMMERCIAL_PRODUCT_READINESS_REFERENCE_EXCELLENCE_FINAL"
CURRENT_VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
VERSION = CURRENT_VERSION if CURRENT_VERSION.startswith("V937_") else BASE_VERSION
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")


def add(checks: list[dict], name: str, ok: bool, detail: object = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)[:500]})


def session(client, role: str) -> None:
    admin = role == "ADMIN"
    with client.session_transaction() as state:
        state.update({
            "user_id": f"v936-{role.lower()}-fixture",
            "user_name": "Admin QA" if admin else "Cliente QA",
            "username": "admin_qa" if admin else "client_qa",
            "user_role": role,
            "membership": "ADMIN" if admin else "PRO",
            "user_membership": "ADMIN" if admin else "PRO",
        })


def main() -> int:
    checks: list[dict] = []
    app_text = read("app.py")
    base = read("templates/base.html")
    component = read("templates/components/v936_product.html")
    css = read("static/v936-commercial.css")
    version = read("VERSION.txt").strip()

    add(checks, "version_exact", version == VERSION, version)
    add(checks, "version_without_bom", not (ROOT / "VERSION.txt").read_bytes().startswith(b"\xef\xbb\xbf"))
    add(checks, "app_version_exact", f"APP_VERSION = '{VERSION}'" in app_text)
    add(checks, "css_cache_busting", "filename='v936-commercial.css'" in base and 'data-v936-commercial-version="{{ app_version }}"' in base)
    add(checks, "service_worker_v936", f"NEMESIS_CACHE_{VERSION.split('_', 1)[0]}" in app_text)
    add(checks, "commercial_css_present", len(css.encode("utf-8")) > 3000)

    macros = ("customer_decision", "value_ladder", "evidence_receipt", "intelligence_brief", "executive_focus")
    add(checks, "product_components", all(f"macro {name}" in component for name in macros), [name for name in macros if f"macro {name}" not in component])
    client_templates = ["home.html", "client_app_center.html", "calendar.html", "live.html", "picks.html", "track_record.html", "shark.html", "telegram.html", "profile.html", "membership.html"]
    admin_templates = ["admin_dashboard.html", "admin_telegram_command_center.html", "admin_payments.html", "admin_picks.html", "admin_users.html", "admin_automation_workforce.html", "admin_data_trust_center.html", "admin_autonomous_company_sentinel.html"]
    add(checks, "customer_decisions_used", all("v936_product.html" in read(f"templates/{name}") for name in client_templates), client_templates)
    add(checks, "executive_focus_used", all("executive_focus" in read(f"templates/{name}") for name in admin_templates), admin_templates)
    add(checks, "natural_plan_ladder", all("value_ladder" in read(f"templates/{name}") for name in ("home.html", "client_app_center.html", "profile.html", "membership.html")))
    add(checks, "shark_decision_brief", "intelligence_brief" in read("templates/shark.html") and "Por qué" in component and "Riesgo" in component)
    add(checks, "telegram_integrated", "Telegram extiende la app" in read("templates/telegram.html"))
    add(checks, "historical_transparency", "Cada cifra puede rastrearse" in read("templates/track_record.html"))
    add(checks, "legacy_guards_preserved", all(token in app_text for token in ("_v931_read_table_rows", "v932_safe_dashboard_data", "get_v934_realtime_context", "get_v935_data_trust_context")))

    with tempfile.TemporaryDirectory(prefix="nemesis_v936_", ignore_cleanup_errors=True) as temp_dir:
        os.environ.update({
            "DB_PATH": str(Path(temp_dir) / "v936-check.sqlite"),
            "RUN_STARTUP_SCHEDULER_NOW": "0",
            "ENABLE_AUTOMATED_RENDER_DEPLOY": "0",
            "TELEGRAM_BOT_TOKEN": "",
            "STRIPE_SECRET_KEY": "",
            "OPENAI_API_KEY": "",
        })
        module = importlib.reload(sys.modules["app"]) if "app" in sys.modules else importlib.import_module("app")
        module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
        public, client, admin = module.app.test_client(), module.app.test_client(), module.app.test_client()
        session(client, "PRO")
        session(admin, "ADMIN")
        public_routes = ["/", "/calendar", "/live", "/picks", "/track-record", "/shark", "/telegram", "/memberships"]
        client_routes = ["/app", "/calendar", "/live", "/picks", "/track-record", "/shark", "/telegram", "/profile", "/memberships"]
        admin_routes = ["/admin/dashboard", "/admin/telegram/command-center", "/admin/users", "/admin/payments", "/admin/picks", "/admin/automation-workforce", "/admin/autonomous-company-sentinel", "/admin/data-trust-center"]
        public_status = {route: public.get(route, follow_redirects=False).status_code for route in public_routes}
        client_responses = {route: client.get(route, follow_redirects=False) for route in client_routes}
        admin_responses = {route: admin.get(route, follow_redirects=False) for route in admin_routes}
        add(checks, "public_routes_green", all(code in {200, 302, 303} for code in public_status.values()), public_status)
        add(checks, "client_routes_green", all(response.status_code == 200 for response in client_responses.values()), {k: v.status_code for k, v in client_responses.items()})
        add(checks, "admin_routes_green", all(response.status_code == 200 for response in admin_responses.values()), {k: v.status_code for k, v in admin_responses.items()})
        add(checks, "admin_protected", public.get("/admin/dashboard", follow_redirects=False).status_code in {302, 303})
        add(checks, "client_decision_visible", all(b"v936-customer-decision" in response.data for response in client_responses.values()), [route for route, response in client_responses.items() if b"v936-customer-decision" not in response.data])
        add(checks, "admin_focus_visible", all(b"v936-executive-focus" in response.data for response in admin_responses.values()), [route for route, response in admin_responses.items() if b"v936-executive-focus" not in response.data])
        forbidden = (b"AUTOMATION_SECRET", b"TELEGRAM_BOT_TOKEN", b"STRIPE_SECRET_KEY", b"DB_PATH", b"provider exception")
        add(checks, "client_technical_details_hidden", all(not any(token in response.data for token in forbidden) for response in client_responses.values()))
        runtime_response = public.get("/api/runtime-version")
        runtime = runtime_response.get_json(silent=True) or {}
        add(checks, "runtime_200", runtime_response.status_code == 200)
        add(checks, "runtime_identity", runtime.get("version") == VERSION and runtime.get("version_files_match") is True, runtime.get("version"))
        add(checks, "runtime_css_and_sw", runtime.get("static_css_cache_busting") is True and runtime.get("service_worker_cache_name") == f"NEMESIS_CACHE_{VERSION.split('_', 1)[0]}", {"css": runtime.get("static_css_cache_busting"), "sw": runtime.get("service_worker_cache_name")})
        flags = ("has_v936_commercial_product_readiness", "has_v936_customer_decision_system", "has_v936_natural_plan_conversion", "has_v936_admin_executive_focus", "has_v936_shark_decision_brief", "has_v936_reference_excellence")
        add(checks, "runtime_flags", all(runtime.get(flag) is True for flag in flags), [flag for flag in flags if runtime.get(flag) is not True])
        add(checks, "no_fake_data_guard", runtime.get("v936_no_fake_data_guard") is True)

    failed = [item for item in checks if not item["ok"]]
    print(json.dumps({"version": VERSION, "ok": not failed, "checks": checks, "failed": failed}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
