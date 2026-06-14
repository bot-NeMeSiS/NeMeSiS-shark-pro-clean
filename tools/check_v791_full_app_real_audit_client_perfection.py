#!/usr/bin/env python3
"""V791 smoke/static check for full app audit + client perfection."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def route_set() -> set[str]:
    tree = ast.parse(read("app.py"))
    routes = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "route":
                    if dec.args and isinstance(dec.args[0], ast.Constant):
                        routes.add(str(dec.args[0].value))
    return routes


def main() -> int:
    errors: list[str] = []
    version_txt = read("VERSION.txt").strip()
    app_py = read("app.py")
    css = read("static/app.css")
    if version_txt != VERSION:
        errors.append(f"VERSION.txt incorrecto: {version_txt}")
    if f'APP_VERSION = "{VERSION}"' not in app_py:
        errors.append("APP_VERSION no apunta a V791")
    if 'BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))' not in app_py:
        errors.append("BASE_DIR no está definido a nivel global")
    if 'client_screen_audit_snapshot' not in app_py:
        errors.append("No se integró client_screen_audit_snapshot")
    routes = route_set()
    for route in ["/admin/client-screen-audit", "/api/admin/client-screen-audit", "/admin/real-launch", "/membresias", "/live", "/calendar", "/picks", "/mi-cuenta"]:
        if route not in routes:
            errors.append(f"Falta ruta crítica: {route}")
    required_files = [
        "engines/client_screen_audit_engine.py",
        "templates/admin_client_screen_audit.html",
        "reports/V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL_REPORT.md",
    ]
    for rel in required_files:
        if not (ROOT / rel).exists():
            errors.append(f"Falta archivo: {rel}")
    for token in ["V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH", "V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL", "v774-match-card", "v785-price-card"]:
        if token not in css:
            errors.append(f"Falta token CSS: {token}")
    unsafe_client = []
    for rel in ["templates/base.html", "templates/shark.html", "templates/picks.html", "templates/client_menu.html", "templates/client_app_center.html"]:
        text = read(rel).lower()
        for bad in ["combi segura", "apuesta segura", "ganancia segura", "dinero garantizado", "sin riesgo"]:
            if bad in text:
                unsafe_client.append((rel, bad))
    if unsafe_client:
        errors.append("Frases de riesgo en cliente: " + ", ".join(f"{a}:{b}" for a, b in unsafe_client))
    if "/admin/real-launch" not in read("templates/base.html") or "/admin/client-screen-audit" not in read("templates/base.html"):
        errors.append("Base admin no enlaza Real Launch/Client Audit")
    if errors:
        print("V791 CHECK FAIL")
        for e in errors:
            print("-", e)
        return 1
    print("OK V791 full app real audit + client perfection final")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
