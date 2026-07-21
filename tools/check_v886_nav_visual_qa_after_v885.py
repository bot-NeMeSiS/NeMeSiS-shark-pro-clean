#!/usr/bin/env python3
"""Validate V886 navigation visual QA after the V885 client sidebar restore."""
from __future__ import annotations

import importlib
import os
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885_FINAL"

CLIENT_ROUTES = [
    "/app",
    "/partidos",
    "/calendar",
    "/live",
    "/picks",
    "/shark",
    "/telegram",
    "/profile",
    "/track-record",
    "/support",
]

ADMIN_ROUTES = [
    "/admin/dashboard",
    "/admin/continuous-sentinel",
    "/admin/visual-worker",
    "/admin/payments",
]

REPORTS = [
    "V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885.md",
    "V886_CLIENT_SIDEBAR_SCREEN_QA.md",
    "V886_ADMIN_NAV_ISOLATION_QA.md",
    "V886_MOBILE_BOTTOM_NAV_QA.md",
]


def fail(message: str) -> None:
    raise SystemExit(f"V886 nav visual QA check failed: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig", errors="replace")


def labels_from_zone(html: str, zone: str) -> list[str]:
    match = re.search(rf'(?is)<(?:aside|nav)\b[^>]*data-nav-zone="{re.escape(zone)}"[^>]*>.*?</(?:aside|nav)>', html or "")
    if not match:
        return []
    block = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", match.group(0))
    labels: list[str] = []
    for anchor in re.finditer(r"(?is)<a\b[^>]*>(.*?)</a>", block):
        text = re.sub(r"(?is)<[^>]+>", " ", anchor.group(1))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            labels.append(text)
    return labels


def duplicate_values(values: list[str]) -> set[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for value in values:
        if value in seen:
            dupes.add(value)
        seen.add(value)
    return dupes


def check_static_contract() -> None:
    version_txt = read("VERSION.txt").strip()
    app_version = read("APP_VERSION").strip()
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")

    require(version_txt == VERSION, "VERSION.txt is not V886")
    require(app_version == VERSION, "APP_VERSION is not V886")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION is not V886")
    require("data-v886-shell" in base, "base.html missing data-v886-shell")
    require("has_v886_real_browser_nav_visual_qa" in app_py, "runtime V886 flag missing")
    require("has_v885_client_sidebar_restore" in app_py, "V885 sidebar flag not preserved")
    require('data-nav-zone="client-sidebar"' in base, "client sidebar zone missing")
    require('data-nav-zone="client-bottom"' in base, "client bottom zone missing")
    require('class="v808-admin-rail"' in base, "admin rail missing")

    require("min-width: 1024px" in css and ".ns-client-sidebar" in css, "desktop sidebar CSS contract missing")
    require("max-width: 1023px" in css and "display: none" in css and ".ns-client-sidebar" in css, "mobile sidebar hide CSS contract missing")
    require(".bottom-nav-clean[data-nav-zone=\"client-bottom\"]" in css, "bottom nav CSS contract missing")
    require(".ns-admin :is(.ns-client-sidebar" in css or ".ns-admin .ns-client-sidebar" in css, "admin/client nav isolation CSS missing")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")


def check_runtime_navigation() -> None:
    db_fd, db_path = tempfile.mkstemp(prefix="v886_nav_", suffix=".db")
    os.close(db_fd)
    os.environ["DB_PATH"] = db_path
    os.environ["AUTOMATION_SECRET"] = "v886-nav-secret"
    try:
        import sys

        sys.path.insert(0, str(ROOT))
        app = importlib.import_module("app")
        app.app.config.update(TESTING=True, SECRET_KEY="v886-test")
        client = app.app.test_client()

        runtime = client.get("/api/runtime-version")
        require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
        payload = runtime.get_json() or {}
        require(payload.get("app_version") == VERSION, "runtime app_version is not V886")
        require(payload.get("version_txt") == VERSION, "runtime version_txt is not V886")
        require(payload.get("has_v886_real_browser_nav_visual_qa") is True, "runtime V886 flag false")
        require(payload.get("has_v885_client_sidebar_restore") is True, "runtime V885 flag false")

        with client.session_transaction() as session:
            session["user_id"] = "v886-client"
            session["user_name"] = "Cliente V886"
            session["username"] = "cliente-v886"
            session["user_email"] = "fixture-v886"
            session["user_role"] = "PRO"
            session["user_membership"] = "PRO"
            session["membership"] = "PRO"

        for route in CLIENT_ROUTES:
            response = client.get(route)
            require(response.status_code in {200, 302}, f"{route} unexpected status {response.status_code}")
            if response.status_code != 200:
                continue
            html = response.get_data(as_text=True) or ""
            require(html.count('data-nav-zone="client-sidebar"') == 1, f"{route} client sidebar count not 1")
            require(html.count('data-nav-zone="client-bottom"') == 1, f"{route} client bottom count not 1")
            require('class="v808-admin-rail"' not in html, f"{route} rendered admin rail")
            require("/admin/" not in re.sub(r"(?is)<main.*", "", html), f"{route} leaked admin nav before main")
            sidebar_labels = labels_from_zone(html, "client-sidebar")
            require(not duplicate_values(sidebar_labels), f"{route} duplicate sidebar labels: {sorted(duplicate_values(sidebar_labels))}")
            require("is-active" in html, f"{route} missing active route marker")
            if route != "/shark":
                require(html.count('class="shark-widget"') <= 1, f"{route} duplicate floating SHARK")

        admin_client = app.app.test_client()
        for route in ADMIN_ROUTES:
            response = admin_client.get(route)
            require(response.status_code in {200, 302, 403}, f"{route} unexpected status {response.status_code}")
            html = response.get_data(as_text=True) or ""
            require('data-nav-zone="client-sidebar"' not in html, f"{route} leaked client sidebar")
            require('data-nav-zone="client-bottom"' not in html, f"{route} leaked client bottom nav")
            require('class="shark-widget"' not in html, f"{route} leaked client floating SHARK")

        for route in ["/api/admin/visual-worker/summary", "/api/admin/continuous-sentinel/summary"]:
            require(admin_client.get(route).status_code == 403, f"{route} not protected with 403")
        require(admin_client.get("/api/automation/master-tick").status_code == 403, "master tick without secret not 403")
    finally:
        for suffix in ("", "-wal", "-shm"):
            try:
                Path(f"{db_path}{suffix}").unlink(missing_ok=True)
            except OSError:
                pass


def main() -> None:
    check_static_contract()
    check_runtime_navigation()
    print("V886 nav visual QA after V885 OK")


if __name__ == "__main__":
    main()
