"""V608 - Architecture and Blueprint Migration Center.

This blueprint is intentionally non-invasive: it adds architecture/route
visibility without moving legacy routes yet. That lets NeMeSiS reduce risk while
preparing app.py for a gradual Blueprint extraction.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from flask import Blueprint, jsonify, redirect, render_template, url_for, current_app

from engines.blueprint_migration_engine import build_runtime_architecture_summary, write_route_map


def create_architecture_blueprint(app_version: str, db_path: str, is_admin_callback: Callable[[], bool]) -> Blueprint:
    bp = Blueprint("architecture", __name__, url_prefix="")

    def _admin_required():
        try:
            return bool(is_admin_callback())
        except Exception:
            return False

    @bp.route("/admin/architecture")
    def admin_architecture_page():
        if not _admin_required():
            return redirect(url_for("admin_login_page"))
        summary = build_runtime_architecture_summary(current_app, app_py=Path("app.py"))
        return render_template("admin_architecture.html", summary=summary, version=app_version)

    @bp.route("/api/architecture/summary")
    def api_architecture_summary():
        if not _admin_required():
            return jsonify({"ok": False, "version": app_version, "error": "Acceso admin requerido."}), 403
        summary = build_runtime_architecture_summary(current_app, app_py=Path("app.py"))
        return jsonify({"ok": True, "version": app_version, "architecture": summary})

    @bp.route("/api/v608/blueprint-migration-check")
    def api_v608_blueprint_migration_check():
        summary = build_runtime_architecture_summary(current_app, app_py=Path("app.py"))
        return jsonify({
            "ok": True,
            "version": app_version,
            "module": "Blueprint Migration Phase 2",
            "features": [
                "arquitectura visible",
                "inventario runtime de rutas",
                "agrupación por dominios",
                "puntuación de mantenibilidad",
                "plan de extracción gradual",
            ],
            "architecture": summary,
        })

    @bp.route("/api/v608/write-route-map", methods=["GET", "POST"])
    def api_v608_write_route_map():
        if not _admin_required():
            return jsonify({"ok": False, "version": app_version, "error": "Acceso admin requerido."}), 403
        out = write_route_map("ROUTE_MAP_V608.md", app_py="app.py")
        return jsonify({"ok": True, "version": app_version, "created": str(out)})

    return bp
