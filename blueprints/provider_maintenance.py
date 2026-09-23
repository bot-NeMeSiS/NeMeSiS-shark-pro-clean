"""Admin provider maintenance routes. Page reads are network-free."""
from __future__ import annotations

from typing import Callable
from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from engines.provider_maintenance_engine import PROVIDERS, provider_maintenance_snapshot, test_provider_connection


def create_provider_maintenance_blueprint(app_version: str, db_path: str, is_admin: Callable[[], bool]) -> Blueprint:
    bp = Blueprint("provider_maintenance", __name__)

    def allowed() -> bool:
        try:
            return bool(is_admin())
        except Exception:
            return False

    @bp.app_context_processor
    def inject_provider_maintenance():
        if request.path in {"/admin/system", "/admin/settings", "/admin/data-center"}:
            return {"provider_maintenance": provider_maintenance_snapshot(db_path)}
        return {}

    @bp.get("/admin/provider-maintenance")
    @bp.get("/admin/api-maintenance")
    @bp.get("/admin/platform-maintenance")
    @bp.get("/admin/mantenimiento")
    def provider_maintenance_page():
        if not allowed():
            return redirect(url_for("admin_login_page", next="/admin/provider-maintenance"))
        return render_template(
            "admin_provider_maintenance.html",
            provider_maintenance=provider_maintenance_snapshot(db_path),
            version=app_version,
        )

    @bp.get("/api/admin/provider-maintenance")
    def provider_maintenance_api():
        if not allowed():
            return jsonify({"ok": False, "error": "admin_required"}), 403
        return jsonify({"version": app_version, **provider_maintenance_snapshot(db_path)})

    @bp.post("/api/admin/provider-maintenance/test/<provider>")
    def provider_maintenance_test(provider: str):
        if not allowed():
            return jsonify({"ok": False, "error": "admin_required"}), 403
        if provider not in PROVIDERS:
            return jsonify({"ok": False, "error": "unsupported_provider", "external_calls": 0}), 404
        result = test_provider_connection(provider, db_path)
        return jsonify({"version": app_version, **result}), 200 if result.get("ok") else 422

    @bp.after_app_request
    def private_provider_surfaces(response):
        if request.path.startswith("/admin/provider-maintenance") or request.path.startswith("/admin/api-maintenance") or request.path.startswith("/admin/platform-maintenance") or request.path.startswith("/admin/mantenimiento") or request.path.startswith("/api/admin/provider-maintenance"):
            response.headers["Cache-Control"] = "private, no-store"
            response.vary.add("Cookie")
        return response

    return bp
