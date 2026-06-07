"""Optional system blueprint for future migration.

Not auto-registered to avoid changing behaviour when copied over the app.
Register manually only after verifying no route conflict exists:

    from blueprints.system_blueprint import system_bp
    app.register_blueprint(system_bp)
"""
from __future__ import annotations

from flask import Blueprint, jsonify

system_bp = Blueprint("system_v606", __name__)


@system_bp.get("/api/v606/blueprint-check")
def blueprint_check():
    return jsonify({
        "ok": True,
        "version": "V606_BLUEPRINT_MIGRATION_PHASE_1",
        "message": "Blueprint scaffold disponible. Migración gradual preparada.",
    })
