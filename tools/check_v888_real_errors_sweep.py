#!/usr/bin/env python3
"""Validate V888 real errors sweep across Telegram, sports states, nav and safety."""
from __future__ import annotations

import importlib
import os
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V888_VERSION = "V888_REAL_ERRORS_SWEEP_TELEGRAM_MATCHES_PICKS_NAV_SENTINEL_FINAL"
V938_VERSION = "V938_COMPANY_OPERATIONS_RECOVERY_OBSERVABILITY_CENTER_FINAL"
SUPPORTED_VERSIONS = {V888_VERSION, V938_VERSION}
REPORTS = [
    "V888_PREFLIGHT_REAL_ERRORS_SWEEP.md",
    "V888_TELEGRAM_CRON_REAL_ERROR_SWEEP.md",
    "V888_RENDER_LOGS_AND_RUNTIME_ERRORS_QA.md",
    "V888_MATCHES_REAL_DATA_ERROR_SWEEP.md",
    "V888_LIVE_DIRECT_ERROR_SWEEP.md",
    "V888_PICKS_ODDS_ERROR_SWEEP.md",
    "V888_NAV_BUTTONS_ERROR_SWEEP.md",
    "V888_MOBILE_ERROR_SWEEP.md",
    "V888_ADMIN_ERROR_SWEEP.md",
    "V888_SENTINEL_VISUAL_WORKER_ERROR_SWEEP.md",
    "V888_SHARK_OPENAI_ERROR_SWEEP.md",
    "V888_LOGOS_CRESTS_ERROR_SWEEP.md",
    "V888_PAYMENTS_MEMBERSHIPS_ERROR_SWEEP.md",
    "V888_COPY_TEXT_ERRORS_SWEEP.md",
]

CLIENT_ROUTES = [
    "/",
    "/cliente-login",
    "/registro",
    "/app",
    "/partidos",
    "/calendar",
    "/live",
    "/directo",
    "/picks",
    "/shark",
    "/telegram",
    "/profile",
    "/track-record",
    "/support",
]

ADMIN_ROUTES = [
    "/admin/dashboard",
    "/admin/company-os",
    "/admin/continuous-sentinel",
    "/admin/sentinel-workflow",
    "/admin/visual-worker",
    "/admin/data-center",
    "/admin/telegram/command-center",
    "/admin/payments",
    "/admin/memberships",
    "/admin/users",
]


def fail(message: str) -> None:
    raise SystemExit(f"V888 real errors sweep check failed: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig", errors="replace")


def has_bad_visible_text(html: str) -> bool:
    compact = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", html or "")
    return any(token in compact for token in ("Ã", "Â", "�")) or bool(re.search(r">\s*(None|null|undefined)\s*<", compact, flags=re.I))


def check_static_contract() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    delivery_engine = read("engines/telegram_delivery_engine.py")
    login = read("templates/client_login.html")
    register = read("templates/register.html")
    admin_real_launch = read("templates/admin_real_launch.html")
    sentinel = read("engines/continuous_shark_sentinel_engine.py")

    current_version = read("VERSION.txt").strip()
    require(current_version in SUPPORTED_VERSIONS, "VERSION.txt is not V888 or its supported V938 successor")
    require(read("APP_VERSION").strip() == current_version, "APP_VERSION file does not match VERSION.txt")
    require(f"APP_VERSION = '{current_version}'" in app_py, "app.py APP_VERSION does not match VERSION.txt")
    require("data-v888-shell" in base, "base.html missing data-v888-shell")
    require("has_v888_real_errors_sweep" in app_py, "runtime V888 flag missing")
    require("has_v887_telegram_queue_skipped_hotfix" in app_py, "runtime V887 flag not preserved")
    require("QUEUE_SKIPPED," in app_py and "QUEUE_SKIPPED = \"skipped\"" in delivery_engine, "QUEUE_SKIPPED hotfix not preserved")
    require("@app.route(\"/favicon.ico\")" in app_py, "favicon route missing")

    require("/api/shark/ask?q=" in base, "SHARK GET fallback URL is malformed")
    require("r.ok ? r.json() : null" in base, "runtime heartbeat JS typo not fixed")
    require("?plan={{ selected }}" in login and "?plan={{ selected }}" in register, "plan continuation links missing query separator")
    require("volverás" in login and "membresías" in register, "login/register Spanish copy not cleaned")
    safe_stripe_copy = (
        "Stripe','No configurado'" in admin_real_launch
        or "Stripe','No configurado" in admin_real_launch
        or "<span>Cobros desde panel</span><strong>No</strong>" in admin_real_launch
    )
    require(safe_stripe_copy, "admin real launch still risks Stripe false operational claim")
    require("Pagos operativos" not in admin_real_launch and "Stripe','Listo'" not in admin_real_launch, "admin real launch claims Stripe operational")
    require("V888_REAL_ERRORS_SWEEP_RULES" in sentinel and "telegram_cron_nameerror_or_internal_error_must_fail" in sentinel, "Sentinel V888 rules missing")
    require("ns-client-sidebar" in base and "bottom-nav-clean" in base and "v808-admin-rail" in base, "nav contracts missing")
    require("Modo seguro activo" in read("templates/shark.html"), "SHARK safe mode copy missing")
    require("Escudo pendiente" in app_py or "Fallback premium activo" in app_py, "logo fallback state missing")
    payments_template = read("templates/admin_payments.html")
    payments_safe_state = (
        "No configurado" in payments_template
        or (
            "Esta vista no ejecuta cobros" in payments_template
            and "Stripe no ha registrado webhooks reales" in payments_template
        )
    )
    require(payments_safe_state, "payments safe state missing")
    require("Sin picks activos" in app_py or "Pick en revisión" in app_py or "Cuota pendiente" in app_py, "picks safe states missing")
    require("Sin directos reales" in app_py or "Proveedor sin datos ahora mismo" in app_py, "live safe states missing")
    require("apuesta segura" not in (app_py + base).lower() and "garantizado" not in (app_py + base).lower(), "unsafe betting promise found")
    require("TELEGRAM_BOT_TOKEN =" not in app_py and "AUTOMATION_SECRET =" not in app_py, "possible secret assignment found")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    require("Ã" not in login + register + admin_real_launch + base, "common templates still contain mojibake")
    require("Â" not in login + register + admin_real_launch + base, "common templates still contain mojibake")
    require("�" not in login + register + admin_real_launch + base, "common templates still contain replacement characters")
    require("javascript:void" not in base.lower() and "href=\"#\"" not in base.lower(), "base navigation contains dead links")
    require(".ns-client-sidebar" in css and ".bottom-nav-clean" in css, "core nav CSS missing")


def check_runtime_contract() -> None:
    db_fd, db_path = tempfile.mkstemp(prefix="v888_real_errors_", suffix=".db")
    os.close(db_fd)
    previous_env = {key: os.environ.get(key) for key in [
        "DB_PATH",
        "AUTOMATION_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "ENABLE_AUTO_TELEGRAM_PRO",
        "TELEGRAM_AUTO_ENABLED",
        "OPENAI_API_KEY",
        "STRIPE_SECRET_KEY",
    ]}
    os.environ["DB_PATH"] = db_path
    os.environ["AUTOMATION_SECRET"] = "v888-local-secret"
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["TELEGRAM_CHAT_ID"] = ""
    os.environ["ENABLE_AUTO_TELEGRAM_PRO"] = "0"
    os.environ["TELEGRAM_AUTO_ENABLED"] = "0"
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["STRIPE_SECRET_KEY"] = ""
    try:
        sys.path.insert(0, str(ROOT))
        app_mod = importlib.import_module("app")
        app_mod.app.config.update(TESTING=True, SECRET_KEY="v888-test")
        client = app_mod.app.test_client()

        runtime = client.get("/api/runtime-version")
        require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
        runtime_json = runtime.get_json() or {}
        current_version = read("VERSION.txt").strip()
        require(runtime_json.get("app_version") == current_version, "runtime app_version does not match VERSION.txt")
        require(runtime_json.get("version_txt") == current_version, "runtime version_txt does not match VERSION.txt")
        require(runtime_json.get("has_v888_real_errors_sweep") is True, "runtime V888 flag false")
        require(runtime_json.get("has_v887_telegram_queue_skipped_hotfix") is True, "runtime V887 flag false")
        require(runtime_json.get("openai_state") or runtime_json.get("shark_ai_mode"), "runtime OpenAI safe state missing")
        require(runtime_json.get("logo_cache_state") or runtime_json.get("logo_cache_note"), "runtime logo fallback state missing")

        require(client.get("/favicon.ico").status_code in {200, 301, 302, 304}, "favicon route returns 404/500")
        require(client.get("/api/automation/telegram/tick").status_code == 403, "telegram tick without secret not 403")
        tick = client.get("/api/automation/telegram/tick?secret=v888-local-secret&runner=render_cron&dry_run=1")
        tick_body = tick.get_data(as_text=True) or ""
        require(tick.status_code == 200, f"telegram tick with local secret returned {tick.status_code}")
        require("NameError" not in tick_body and "not defined" not in tick_body, "telegram tick leaks NameError")
        require(client.get("/api/automation/master-tick").status_code == 403, "master tick without secret not 403")

        with client.session_transaction() as session:
            session["user_id"] = "v888-client"
            session["user_name"] = "Cliente V888"
            session["username"] = "cliente-v888"
            session["user_email"] = "fixture-v888"
            session["user_role"] = "PRO"
            session["user_membership"] = "PRO"
            session["membership"] = "PRO"

        for route in CLIENT_ROUTES:
            response = client.get(route)
            require(response.status_code in {200, 302, 403}, f"{route} unexpected status {response.status_code}")
            if response.status_code != 200:
                continue
            html = response.get_data(as_text=True) or ""
            require(not has_bad_visible_text(html), f"{route} has visible mojibake/None/null/undefined")
            require('class="v808-admin-rail"' not in html, f"{route} leaked admin rail")
            if route not in {"/", "/cliente-login", "/registro"}:
                require(html.count('data-nav-zone="client-sidebar"') <= 1, f"{route} duplicate client sidebar")
                require(html.count('data-nav-zone="client-bottom"') <= 1, f"{route} duplicate client bottom")

        anonymous = app_mod.app.test_client()
        for route in ADMIN_ROUTES:
            response = anonymous.get(route)
            require(response.status_code in {200, 302, 403}, f"{route} unexpected status {response.status_code}")
            html = response.get_data(as_text=True) or ""
            require('data-nav-zone="client-sidebar"' not in html, f"{route} leaked client sidebar")
            require('data-nav-zone="client-bottom"' not in html, f"{route} leaked client bottom nav")
            require('class="shark-widget"' not in html, f"{route} leaked client floating SHARK")
        for route in ["/api/admin/continuous-sentinel/summary", "/api/admin/visual-worker/summary", "/api/admin/company-os/summary"]:
            require(anonymous.get(route).status_code == 403, f"{route} not protected with 403")
    finally:
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main() -> None:
    check_static_contract()
    check_runtime_contract()
    print("V888 real errors sweep OK")


if __name__ == "__main__":
    main()
