#!/usr/bin/env python3
"""Smoke real de Flask para NeMeSiS SHARK PRO.

Objetivo:
- Importar la app real con una DB temporal segura.
- Ejecutar rutas críticas con app.test_client().
- Fallar si alguna ruta devuelve 500 o si faltan dependencias.

Uso local:
    python tools/smoke_flask_real_routes.py

Uso con JSON:
    python tools/smoke_flask_real_routes.py --json

Nota:
Este check necesita las dependencias instaladas con:
    python -m pip install -r requirements.txt
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"

PUBLIC_ROUTES = [
    "/",
    "/login",
    "/cliente-login",
    "/registro",
    "/membresias",
    "/live",
    "/calendar",
    "/picks",
    "/combis",
    "/mercados",
    "/highlights",
    "/track-record",
    "/telegram",
    "/shark",
    "/api/health",
    "/api/runtime-version",
    "/api/live",
]

PROTECTED_ROUTES = [
    "/app",
    "/mi-cuenta",
    "/todo",
    "/mapa",
    "/admin-login",
    "/admin/dashboard",
    "/admin/payments",
    "/admin/telegram/command-center",
    "/admin/final-certification",
]

STRIPE_ROUTES = [
    "/pagos/checkout/PRO",
    "/pagos/checkout/ELITE",
    "/pagos/portal",
]

ALLOWED_NON_500 = {200, 201, 202, 204, 301, 302, 303, 307, 308, 400, 401, 403, 404, 405}


@dataclass
class RouteResult:
    path: str
    status_code: int | None
    ok: bool
    note: str = ""


def dependency_status() -> dict[str, bool]:
    deps = ["flask", "werkzeug", "jinja2", "stripe"]
    return {dep: importlib.util.find_spec(dep) is not None for dep in deps}


def prepare_environment() -> Path:
    temp_db = Path(tempfile.gettempdir()) / "nemesis_smoke_flask_real_routes.db"
    os.environ.setdefault("DB_PATH", str(temp_db))
    os.environ.setdefault("SECRET_KEY", "smoke-local-secret-key")
    os.environ.setdefault("AUTOMATION_SECRET", "smoke-automation-secret")
    os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
    os.environ.setdefault("ADMIN_PASSWORD", "admin-password")
    os.environ.setdefault("APP_TIMEZONE", "Europe/Madrid")
    os.environ.setdefault("TZ", "Europe/Madrid")
    os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
    os.environ.setdefault("AUTO_GENERATE_PICKS", "false")
    os.environ.setdefault("AUTO_SEND_TELEGRAM_PICKS", "false")
    os.environ.setdefault("ENABLE_TELEGRAM_AUTO", "false")
    os.environ.setdefault("PAYMENTS_ENABLED", "false")
    os.environ.setdefault("STRIPE_SECRET_KEY", "")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "")
    os.environ.setdefault("ENABLE_LIVE_API", "false")
    return temp_db


def import_app_module():
    sys.path.insert(0, str(ROOT))
    prepare_environment()
    import app as app_module  # noqa: PLC0415
    return app_module


def check_routes(client, routes: Iterable[str], method: str = "GET") -> list[RouteResult]:
    results: list[RouteResult] = []
    for path in routes:
        try:
            if method == "POST":
                response = client.post(path, data={}, follow_redirects=False)
            else:
                response = client.get(path, follow_redirects=False)
            status = int(response.status_code)
            ok = status < 500 and status in ALLOWED_NON_500
            note = "OK" if ok else "status inesperado"
            results.append(RouteResult(path=path, status_code=status, ok=ok, note=note))
        except Exception as exc:  # pragma: no cover
            results.append(RouteResult(path=path, status_code=None, ok=False, note=f"exception: {exc}"))
    return results


def build_report() -> dict:
    deps = dependency_status()
    if not deps.get("flask"):
        return {
            "ok": False,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
            "stage": "dependencies",
            "message": "Flask no está instalado. Ejecuta: python -m pip install -r requirements.txt",
            "dependencies": deps,
            "routes": [],
        }
    try:
        app_module = import_app_module()
        flask_app = app_module.app
        flask_app.config.update(TESTING=True)
        client = flask_app.test_client()
        route_results = []
        route_results.extend(check_routes(client, PUBLIC_ROUTES))
        route_results.extend(check_routes(client, PROTECTED_ROUTES))
        # POST routes should not 500 even if they reject CSRF/config with 400/403.
        route_results.extend(check_routes(client, STRIPE_ROUTES, method="POST"))
        failed = [r for r in route_results if not r.ok]
        return {
            "ok": not failed,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
            "stage": "flask_routes",
            "version": getattr(app_module, "APP_VERSION", "unknown"),
            "dependencies": deps,
            "route_count": len(list(flask_app.url_map.iter_rules())),
            "tested_routes": len(route_results),
            "failed_routes": [asdict(item) for item in failed],
            "routes": [asdict(item) for item in route_results],
        }
    except Exception as exc:  # pragma: no cover
        return {
            "ok": False,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
            "stage": "import_or_client",
            "message": str(exc),
            "traceback": traceback.format_exc(limit=12),
            "dependencies": deps,
            "routes": [],
        }


def write_report(report: dict) -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    version = str(report.get("version") or "V784").split("_", 1)[0]
    (REPORT_DIR / f"{version}_FLASK_SMOKE_ROUTES_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        f"# Smoke Flask real {version}",
        "",
        f"- Resultado: {'OK' if report.get('ok') else 'REVISAR'}",
        f"- Fase: `{report.get('stage')}`",
        f"- Versión: `{report.get('version', 'unknown')}`",
        f"- Rutas probadas: {report.get('tested_routes', 0)}",
        "",
    ]
    if report.get("message"):
        lines.append(f"Mensaje: {report['message']}")
        lines.append("")
    failed = report.get("failed_routes") or []
    if failed:
        lines.append("## Rutas fallidas")
        for item in failed:
            lines.append(f"- `{item['path']}` -> {item['status_code']} / {item['note']}")
    else:
        lines.append("Sin rutas fallidas con 500.")
    (REPORT_DIR / f"{version}_FLASK_SMOKE_ROUTES_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Imprime el informe completo en JSON")
    args = parser.parse_args()
    report = build_report()
    write_report(report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "ok": report.get("ok"),
            "stage": report.get("stage"),
            "version": report.get("version"),
            "tested_routes": report.get("tested_routes", 0),
            "failed_routes": report.get("failed_routes", []),
            "message": report.get("message", ""),
        }, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
