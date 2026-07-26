"""Admin-only Developer Center backed by the shared project operating system."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any, Callable, Mapping

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from engines.project_operating_system_engine import (
    build_dev_source_archive,
    build_developer_center_snapshot,
    clear_project_snapshot_cache,
)


def create_developer_center_blueprint(
    app_version: str,
    project_root: str | Path,
    is_admin_callback: Callable[[], bool],
    runtime_callback: Callable[[], Mapping[str, Any]],
    dashboard_callback: Callable[[], Mapping[str, Any]],
) -> Blueprint:
    bp = Blueprint("developer_center", __name__)
    root = Path(project_root).resolve()

    def admin_required() -> bool:
        try:
            return bool(is_admin_callback())
        except Exception:
            return False

    def runtime_snapshot() -> dict[str, Any]:
        try:
            return dict(runtime_callback() or {})
        except Exception:
            return {}

    def dashboard_data() -> dict[str, Any]:
        try:
            return dict(dashboard_callback() or {})
        except Exception:
            return {}

    def snapshot() -> dict[str, Any]:
        routes = [rule.rule for rule in current_app.url_map.iter_rules()]
        return build_developer_center_snapshot(
            root,
            app_version,
            runtime_snapshot(),
            registered_routes=routes,
        )

    @bp.get("/admin/developer-center")
    @bp.get("/admin/development")
    def admin_developer_center_page():
        if not admin_required():
            return redirect("/admin-login?next=/admin/developer-center")
        return render_template(
            "admin_developer_center.html",
            data=dashboard_data(),
            snapshot=snapshot(),
            build_state=request.args.get("build") or "",
        )

    @bp.get("/api/admin/developer-center/summary")
    def api_admin_developer_center_summary():
        if not admin_required():
            return jsonify({"ok": False, "error": "admin_required"}), 403
        return jsonify({"ok": True, "developer_center": snapshot()})

    @bp.post("/api/admin/developer-center/refresh")
    def api_admin_developer_center_refresh():
        if not admin_required():
            return jsonify({"ok": False, "error": "admin_required"}), 403
        clear_project_snapshot_cache()
        return jsonify({"ok": True, "developer_center": snapshot()})

    @bp.post("/admin/developer-center/build")
    def admin_developer_center_build():
        if not admin_required():
            return jsonify({"ok": False, "error": "admin_required"}), 403
        try:
            result = build_dev_source_archive(root, app_version)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:  # type: ignore[name-defined]
            if request.is_json:
                return jsonify({"ok": False, "error": "source_build_failed"}), 500
            return redirect(
                url_for(
                    "developer_center.admin_developer_center_page",
                    build="failed",
                )
            )
        if request.is_json:
            return jsonify({"ok": True, "build": result})
        return redirect(
            url_for(
                "developer_center.admin_developer_center_page",
                build="ready",
            )
        )

    @bp.get("/admin/developer-center/source")
    def admin_developer_center_source():
        if not admin_required():
            return jsonify({"ok": False, "error": "admin_required"}), 403
        path = root / "release_output" / "NeMeSiS_DEV_SOURCE.zip"
        if not path.is_file():
            return jsonify({"ok": False, "error": "source_build_missing"}), 404
        return send_file(
            path,
            as_attachment=True,
            download_name="NeMeSiS_DEV_SOURCE.zip",
            mimetype="application/zip",
            max_age=0,
        )

    return bp
