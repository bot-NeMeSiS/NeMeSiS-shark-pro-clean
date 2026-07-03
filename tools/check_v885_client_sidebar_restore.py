#!/usr/bin/env python3
"""Validate V885 client sidebar restore and nav isolation."""
from __future__ import annotations

import importlib
import os
from pathlib import Path
import re
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PRESERVED_VERSION = "V885_CLIENT_SIDEBAR_RESTORE_BEST_POSITION_NAV_FINAL"
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"

REPORTS = [
    "V885_PREFLIGHT_CLIENT_SIDEBAR_RESTORE.md",
    "V885_CLIENT_NAV_CURRENT_STATE_AUDIT.md",
    "V885_CLIENT_SIDEBAR_DESIGN_DECISION.md",
    "V885_CLIENT_SIDEBAR_RESTORE_ACTIONS.md",
    "V885_NAV_FLAGS_QA.md",
    "V885_RESPONSIVE_NAV_QA.md",
    "V885_SENTINEL_NAV_RULES_QA.md",
    "V885_SCREEN_BY_SCREEN_CLIENT_NAV_QA.md",
    "V885_CLIENT_SIDEBAR_RESTORE_BEST_POSITION_NAV_REPORT.md",
    "V885_NEXT_STEPS.md",
]

CLIENT_LINKS = {
    "/app",
    "/partidos",
    "/live",
    "/picks",
    "/shark",
    "/telegram",
    "/profile",
    "/track-record",
    "/support",
}


def fail(message: str) -> None:
    raise SystemExit(f"V885 sidebar restore check failed: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def hrefs(html: str) -> list[str]:
    return re.findall(r"href=[\"']([^\"']+)[\"']", html or "")


def nav_block(html: str, zone: str) -> str:
    match = re.search(rf"(?is)<(?:nav|aside)\b[^>]*data-nav-zone=[\"']{re.escape(zone)}[\"'][^>]*>.*?</(?:nav|aside)>", html or "")
    return match.group(0) if match else ""


def check_static_files() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    worker = read("engines/visual_company_worker_engine.py")
    sentinel = read("engines/continuous_shark_sentinel_engine.py")

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt does not match current version")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION does not match current version")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION does not match current version")
    require('data-v885-shell="true"' in base, "base.html missing data-v885-shell")
    require("NEMESIS V885 CLIENT SIDEBAR RESTORE BEST POSITION NAV ACTIVE" in base, "base.html V885 comment missing")
    require(PRESERVED_VERSION in base or "data-v885-shell" in base, "base.html missing V885 preservation")
    require("has_v885_client_sidebar_restore" in app_py, "runtime V885 flag missing")
    require("V885 CLIENT SIDEBAR RESTORE BEST POSITION NAV START" in css, "CSS V885 marker missing")
    require("V885_NAV_RULES" in worker, "Visual Worker V885 nav rules missing")
    require("V885_CLIENT_SIDEBAR_RESTORE_RULES" in sentinel, "Sentinel V885 rules missing")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    require("show_client_sidebar" in base, "show_client_sidebar flag missing")
    require("show_client_topbar_nav" in base, "show_client_topbar_nav flag missing")
    require("show_mobile_bottom_nav" in base, "show_mobile_bottom_nav flag missing")
    require("show_admin_nav" in base, "show_admin_nav flag missing")
    require("show_floating_shark" in base, "show_floating_shark flag missing")

    require(base.count('data-nav-zone="client-sidebar"') == 1, "client sidebar markup is not unique")
    require(base.count('data-nav-zone="client-bottom"') == 1, "client bottom nav markup is not unique")
    require(base.count('class="v808-admin-rail"') == 1, "admin rail markup is not unique")
    require('<aside class="v828-client-rail"' not in base, "legacy v828 rail rendered")

    sidebar = nav_block(base, "client-sidebar")
    require(sidebar, "client sidebar block missing")
    sidebar_hrefs = set(hrefs(sidebar))
    missing_links = sorted(link for link in CLIENT_LINKS if link not in base)
    require(not missing_links, f"client sidebar missing links: {missing_links}")
    require(not any(h in {"#", "javascript:void(0)", "javascript:void(0);"} for h in sidebar_hrefs), "client sidebar has dead href")
    require(not any(h.startswith("/admin/") for h in sidebar_hrefs), "client sidebar has admin link")
    require('href="{{ href }}"' in sidebar, "client sidebar does not render loop hrefs")

    for token in ["has_v884_client_admin_functional_flow", "has_v883_visual_company_worker", "has_v882_core_product_recovery", "has_v881_sidebar_nav_duplication_fix", "has_v818_automation"]:
        require(token in app_py, f"preserved runtime flag missing: {token}")


def check_runtime_html() -> None:
    db_fd, db_path = tempfile.mkstemp(prefix="v885_sidebar_", suffix=".db")
    os.close(db_fd)
    os.environ["DB_PATH"] = db_path
    os.environ["AUTOMATION_SECRET"] = "v885-sidebar-secret"
    try:
        sys.path.insert(0, str(ROOT))
        app = importlib.import_module("app")
        app.app.config.update(TESTING=True, SECRET_KEY="v885-test")
        client = app.app.test_client()

        runtime = client.get("/api/runtime-version")
        require(runtime.status_code == 200, f"runtime returned {runtime.status_code}")
        payload = runtime.get_json() or {}
        require(payload.get("app_version") == VERSION, "runtime app_version does not match current version")
        require(payload.get("version_txt") == VERSION, "runtime version_txt does not match current version")
        require(payload.get("has_v885_client_sidebar_restore") is True, "runtime V885 flag false")
        require(payload.get("has_v884_client_admin_functional_flow") is True, "runtime V884 flag false")

        with client.session_transaction() as session:
            session["user_id"] = "v885-client"
            session["user_name"] = "Cliente V885"
            session["username"] = "cliente_v885"
            session["user_email"] = "cliente-v885@example.test"
            session["user_role"] = "PRO"
            session["user_membership"] = "PRO"
            session["membership"] = "PRO"

        client_html = client.get("/app").get_data(as_text=True) or ""
        require('data-nav-zone="client-sidebar"' in client_html, "authenticated client missing sidebar")
        require(client_html.count('data-nav-zone="client-sidebar"') == 1, "authenticated client has duplicate sidebar")
        require(client_html.count('data-nav-zone="client-bottom"') == 1, "authenticated client bottom nav not unique")
        require('class="v808-admin-rail"' not in client_html, "client received admin rail")
        require("/admin/" not in nav_block(client_html, "client-sidebar"), "client sidebar contains admin route")
        require("is-active" in nav_block(client_html, "client-sidebar"), "client sidebar active route marker missing")

        admin_client = app.app.test_client()
        with admin_client.session_transaction() as session:
            session["user_id"] = "v885-admin"
            session["user_name"] = "Admin V885"
            session["username"] = "admin_v885"
            session["user_email"] = "admin-v885@example.test"
            session["user_role"] = "ADMIN"
            session["user_membership"] = "ADMIN"
            session["membership"] = "ADMIN"

        admin_response = admin_client.get("/admin/dashboard", follow_redirects=False)
        require(admin_response.status_code in {200, 302, 303}, f"admin dashboard unexpected status {admin_response.status_code}")
        admin_html = admin_response.get_data(as_text=True) or ""
        if admin_response.status_code == 200:
            require('data-nav-zone="client-sidebar"' not in admin_html, "admin rendered client sidebar")
            require('data-nav-zone="client-bottom"' not in admin_html, "admin rendered client bottom nav")
            require('class="shark-widget"' not in admin_html, "admin rendered client floating SHARK")

        for route in ["/api/admin/visual-worker/summary", "/api/admin/continuous-sentinel/summary"]:
            require(client.get(route).status_code == 403, f"{route} not protected with 403")
        require(client.get("/api/automation/master-tick").status_code == 403, "master tick without secret not 403")
    finally:
        for suffix in ("", "-wal", "-shm"):
            try:
                Path(f"{db_path}{suffix}").unlink(missing_ok=True)
            except Exception:
                pass


def check_no_secret_or_bad_links() -> None:
    corpus = "\n".join(
        read(path)
        for path in [
            "app.py",
            "templates/base.html",
            "static/app.css",
            "engines/visual_company_worker_engine.py",
            "engines/continuous_shark_sentinel_engine.py",
        ]
    ).lower()
    for token in ["stripe_live_", "telegram_bot_token=", "api_key="]:
        require(token not in corpus, f"possible secret marker found: {token}")
    require(not re.search(r"\bsk-[a-z0-9_-]{20,}", corpus), "possible OpenAI secret key found")


def check_zip_if_present() -> None:
    zip_path = ROOT / "release_output" / ZIP_NAME
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    required = {
        "app.py",
        "VERSION.txt",
        "APP_VERSION",
        "requirements.txt",
        "templates/base.html",
        "static/app.css",
        "tools/check_v885_client_sidebar_restore.py",
    }
    missing = sorted(required - names)
    require(not missing, f"zip missing root files: {missing}")
    forbidden = [
        name
        for name in names
        if name.startswith((".git/", ".venv/", "release_output/", "__pycache__/", ".pytest_cache/"))
        or name.endswith((".db", ".db-wal", ".db-shm", ".sqlite", ".zip", ".log", ".pyc"))
    ]
    require(not forbidden, f"zip forbidden entries: {forbidden[:10]}")


def main() -> None:
    check_static_files()
    check_runtime_html()
    check_no_secret_or_bad_links()
    check_zip_if_present()
    print("V885 client sidebar restore OK")


if __name__ == "__main__":
    main()
