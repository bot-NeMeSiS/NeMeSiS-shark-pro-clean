#!/usr/bin/env python3
"""Verify app import, route map, templates and common static references."""
from __future__ import annotations

import ast
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "reports"
APP_PATH = ROOT / "app.py"
TEMPLATE_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
CRITICAL_ROUTES = [
    "/",
    "/login",
    "/admin-login",
    "/registro",
    "/dashboard",
    "/sports-hub",
    "/live",
    "/calendar",
    "/picks",
    "/combis",
    "/telegram",
    "/shark",
    "/admin/data-memory",
    "/admin/codex-automation",
    "/api/health",
    "/api/runtime-version",
]


def literal_template_names() -> set[str]:
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "render_template" and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                names.add(first.value)
    return names


def static_references() -> set[str]:
    refs: set[str] = set()
    for path in TEMPLATE_DIR.rglob("*.html"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in re.findall(r"""['"](/static/[^'"]+)['"]""", text):
            refs.add(match.split("?", 1)[0].lstrip("/"))
    return refs


def import_app_summary() -> dict:
    temp_db = Path(tempfile.gettempdir()) / "nemesis_v723_verify_routes.db"
    os.environ.setdefault("DB_PATH", str(temp_db))
    os.environ.setdefault("SECRET_KEY", "codex-local-validation")
    os.environ.setdefault("AUTOMATION_SECRET", "codex-secret")
    import app as app_module  # noqa: PLC0415

    routes = sorted(
        {
            rule.rule
            for rule in app_module.app.url_map.iter_rules()
            if "GET" in rule.methods
        }
    )
    return {
        "import_ok": True,
        "version": getattr(app_module, "APP_VERSION", ""),
        "route_count": len(routes),
        "routes": routes,
        "critical_routes": {
            route: route in routes or any("<" in known and known.split("<", 1)[0] and route.startswith(known.split("<", 1)[0]) for known in routes)
            for route in CRITICAL_ROUTES
        },
    }


def build_report() -> dict:
    templates = literal_template_names()
    missing_templates = sorted(name for name in templates if not (TEMPLATE_DIR / name).exists())
    static_refs = static_references()
    missing_static = sorted(ref for ref in static_refs if not (ROOT / ref).exists())
    imported = import_app_summary()
    return {
        "ok": not missing_templates and not missing_static and imported["import_ok"],
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "templates_referenced": sorted(templates),
        "missing_templates": missing_templates,
        "static_references": sorted(static_refs),
        "missing_static": missing_static,
        **imported,
    }


def write_markdown(report: dict) -> None:
    lines = [
        "# Verificación de imports, rutas y plantillas V723",
        "",
        f"- Resultado: {'OK' if report['ok'] else 'REVISAR'}",
        f"- Versión importada: `{report['version']}`",
        f"- Rutas GET: {report['route_count']}",
        f"- Templates referenciados: {len(report['templates_referenced'])}",
        f"- Templates faltantes: {len(report['missing_templates'])}",
        f"- Static faltantes: {len(report['missing_static'])}",
        "",
        "## Rutas críticas",
    ]
    for route, ok in report["critical_routes"].items():
        lines.append(f"- `{route}`: {'OK' if ok else 'NO ENCONTRADA'}")
    if report["missing_templates"]:
        lines.extend(["", "## Templates faltantes"])
        for name in report["missing_templates"]:
            lines.append(f"- `{name}`")
    if report["missing_static"]:
        lines.extend(["", "## Static faltantes"])
        for name in report["missing_static"]:
            lines.append(f"- `{name}`")
    (REPORT_DIR / "IMPORTS_ROUTES_VERIFY_V723.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORT_DIR.mkdir(exist_ok=True)
    report = build_report()
    (REPORT_DIR / "IMPORTS_ROUTES_VERIFY_V723.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(report)
    print(json.dumps({
        "ok": report["ok"],
        "version": report["version"],
        "route_count": report["route_count"],
        "missing_templates": report["missing_templates"],
        "missing_static": report["missing_static"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
