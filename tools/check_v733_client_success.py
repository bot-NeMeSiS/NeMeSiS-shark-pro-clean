#!/usr/bin/env python3
"""Validate V733 client success/onboarding support additions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.client_success_engine import client_success_snapshot

REPORT_MD = ROOT / "V733_CLIENT_SUCCESS_ONBOARDING_SUPPORT_POLISH_REPORT.md"
REPORT_JSON = ROOT / "reports" / "CLIENT_SUCCESS_QA_V733.json"

REQUIRED_FILES = [
    "engines/client_success_engine.py",
    "templates/client_success.html",
    "templates/admin_client_success.html",
]
REQUIRED_ROUTES = [
    "/guia",
    "/ayuda",
    "/api/client/success",
    "/admin/client-success",
    "/api/admin/client-success",
]


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except Exception:
        return ""


def main() -> int:
    snapshot = client_success_snapshot(stats={
        "membership": "PRO",
        "favorites_count": 2,
        "picks_visible": 3,
        "live_count": 1,
        "upcoming_count": 18,
        "telegram_configured": True,
        "telegram_football_only": True,
        "madrid_time_ready": True,
        "support_ready": True,
    }, root=ROOT)
    app_text = read(ROOT / "app.py")
    css_text = read(ROOT / "static" / "app.css")
    missing_files = [item for item in REQUIRED_FILES if not (ROOT / item).exists()]
    missing_routes = [route for route in REQUIRED_ROUTES if route not in app_text]
    checks = {
        "version": read(ROOT / "VERSION.txt").strip(),
        "app_version_updated": any(marker in app_text for marker in ["V733_CLIENT_SUCCESS_ONBOARDING_SUPPORT_POLISH", "V734_PUBLIC_LAUNCH_TRACK_RECORD_PAYMENTS_FOUNDATION", "V735_GO_LIVE_PRODUCTION_TELEGRAM_DATA_CERTIFICATION", "V736_GLOBAL_CLIENT_VISUAL_MEMBERSHIP_EXPERIENCE", "V737_NATIVE_APP_FEEL_MICROINTERACTIONS_NAVIGATION_POLISH"]),
        "engine_imported": "client_success_snapshot" in app_text,
        "routes_present": not missing_routes,
        "files_present": not missing_files,
        "support_accepts_post": '@app.route("/contact", methods=["GET", "POST"])' in app_text,
        "menu_has_guide": '"href": "/guia"' in app_text,
        "css_layer": "V733 Client Success" in css_text,
        "snapshot_score": snapshot["score"],
        "snapshot_status": snapshot["status"],
        "missing_files": missing_files,
        "missing_routes": missing_routes,
    }
    ok = all([
        checks["app_version_updated"],
        checks["engine_imported"],
        checks["routes_present"],
        checks["files_present"],
        checks["support_accepts_post"],
        checks["menu_has_guide"],
        checks["css_layer"],
        snapshot["score"] >= 80,
    ])
    result = {"ok": ok, "checks": checks, "snapshot": snapshot}
    REPORT_JSON.parent.mkdir(exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# V733 Client Success Onboarding Support Polish Report",
        "",
        f"- Estado: **{'OK' if ok else 'REVISAR'}**",
        f"- Versión: `{checks['version']}`",
        f"- Score snapshot cliente: **{snapshot['score']}/100**",
        f"- Rutas nuevas presentes: {'sí' if checks['routes_present'] else 'no'}",
        f"- Soporte POST activo: {'sí' if checks['support_accepts_post'] else 'no'}",
        f"- Capa CSS V733: {'sí' if checks['css_layer'] else 'no'}",
        "",
        "## Rutas añadidas",
    ]
    for route in REQUIRED_ROUTES:
        lines.append(f"- `{route}`")
    lines.extend(["", "## Pilares cliente"])
    for pillar in snapshot["pillars"]:
        lines.append(f"- **{pillar['title']}**: {pillar['status']} · {pillar['body']}")
    lines.extend([
        "",
        "## Notas",
        "- V733 no envía Telegram, no toca secrets y no cambia Cron/Render/DB_PATH.",
        "- Añade una guía cliente y un centro admin de éxito/soporte para reducir confusión y acelerar QA real.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
