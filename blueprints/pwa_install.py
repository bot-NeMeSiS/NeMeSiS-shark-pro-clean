"""Public install guide for the existing NeMeSiS PWA."""
from __future__ import annotations
import json
from pathlib import Path
from flask import Blueprint, current_app, jsonify, render_template


def _fingerprint() -> str:
    try:
        path=Path(current_app.root_path)/"static"/"img"/"app-icons"/"icons.json"
        payload=json.loads(path.read_text(encoding="utf-8"))
        return str(payload.get("fingerprint") or "")
    except Exception:
        return ""


def create_pwa_install_blueprint(app_version: str) -> Blueprint:
    bp=Blueprint("pwa_install",__name__)

    @bp.get("/instalar")
    @bp.get("/install-app")
    @bp.get("/anadir-a-inicio")
    def install_page():
        return render_template("install_app.html",version=app_version,icon_fingerprint=_fingerprint())

    @bp.get("/api/app-install-info")
    def install_info():
        return jsonify({
            "ok":True,
            "version":app_version,
            "name":"NeMeSiS SHARK PRO",
            "manifest":"/manifest.json",
            "icon_fingerprint":_fingerprint(),
            "same_icon_family_as_admin":True,
            "provider_calls":0,
            "writes":0,
        })

    return bp
