"""Smoke checks for NeMeSiS SHARK PRO.

Run from project root:
    python tools/smoke_check.py
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app.py"
TEMPLATES_DIR = ROOT / "templates"
ENGINES_DIR = ROOT / "engines"

CRITICAL_PATHS = {
    "/",
    "/live",
    "/picks",
    "/admin-login",
    "/cliente-login",
    "/registro",
}

CRITICAL_API_PREFIXES = (
    "/api/health",
    "/api/v602/player-intelligence-check",
    "/api/v601/api-exploitation-check",
)


def _print(status: str, message: str) -> None:
    print(f"[{status}] {message}")


def compile_python_files() -> list[str]:
    errors: list[str] = []
    files = [APP_FILE, ROOT / "database_manager.py"]
    if ENGINES_DIR.exists():
        files.extend(sorted(ENGINES_DIR.glob("*.py")))
    for file in files:
        if not file.exists():
            continue
        try:
            compile(file.read_text(encoding="utf-8", errors="replace"), str(file), "exec")
        except Exception as exc:  # pragma: no cover
            errors.append(f"{file.relative_to(ROOT)} -> {exc}")
    return errors


def extract_render_templates() -> set[str]:
    if not APP_FILE.exists():
        return set()
    tree = ast.parse(APP_FILE.read_text(encoding="utf-8", errors="replace"))
    templates: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name == "render_template" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    templates.add(first.value)
    return templates


def missing_templates() -> list[str]:
    missing: list[str] = []
    for template in sorted(extract_render_templates()):
        if not (TEMPLATES_DIR / template).exists():
            missing.append(template)
    return missing


def import_app():
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-smoke-checks")
    os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
    os.environ.setdefault("ADMIN_PASSWORD", "admin-password")
    os.environ.setdefault("BACKGROUND_JOBS_ENABLED", "false")
    os.environ.setdefault("AUTO_GENERATE_PICKS", "false")
    os.environ.setdefault("AUTO_SEND_TELEGRAM_PICKS", "false")
    os.environ.setdefault("DB_PATH", str(pathlib.Path(tempfile.gettempdir()) / "nemesis_smoke_check.db"))
    sys.path.insert(0, str(ROOT))
    import app as app_module  # type: ignore
    return app_module


def route_report(app_module) -> tuple[list[str], list[str], list[str]]:
    rules = list(app_module.app.url_map.iter_rules())
    paths = [rule.rule for rule in rules]
    duplicates = sorted([path for path, count in Counter(paths).items() if count > 1])
    missing_critical = sorted(path for path in CRITICAL_PATHS if path not in paths)
    available_api = sorted(path for path in paths if path.startswith("/api/"))
    missing_api = []
    for expected in CRITICAL_API_PREFIXES:
        if expected not in paths:
            missing_api.append(expected)
    return duplicates, missing_critical, missing_api


def main() -> int:
    _print("INFO", f"Proyecto: {ROOT}")

    compile_errors = compile_python_files()
    if compile_errors:
        for error in compile_errors:
            _print("ERROR", f"Compilación: {error}")
        return 1
    _print("OK", "Compilación Python correcta")

    missing = missing_templates()
    if missing:
        for template in missing:
            _print("ERROR", f"Template faltante: {template}")
        return 1
    _print("OK", "Templates referenciados disponibles")

    try:
        app_module = import_app()
    except Exception as exc:
        _print("ERROR", f"Importación de app fallida: {exc}")
        return 1
    _print("OK", "App importada correctamente")

    duplicates, missing_critical, missing_api = route_report(app_module)
    if duplicates:
        for path in duplicates:
            _print("WARN", f"Ruta duplicada detectada: {path}")
    else:
        _print("OK", "Sin rutas duplicadas exactas")

    if missing_critical:
        for path in missing_critical:
            _print("ERROR", f"Ruta crítica faltante: {path}")
        return 1
    _print("OK", "Rutas críticas presentes")

    if missing_api:
        for path in missing_api:
            _print("WARN", f"Endpoint API esperado no encontrado: {path}")
    else:
        _print("OK", "Endpoints API recientes presentes")

    _print("OK", "Smoke check finalizado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
