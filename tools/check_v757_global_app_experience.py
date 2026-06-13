#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSION = "V757_GLOBAL_APP_EXPERIENCE_TRUST_NAVIGATION_POLISH"
REQUIRED = {
    "VERSION.txt": [VERSION],
    "app.py": [VERSION, "build_v757_app_center", "/api/client/app-center", "v757_client_app_center_page"],
    "engines/client_growth_engine.py": ["build_v757_app_center", "build_v757_trust_snapshot", "build_v757_next_actions"],
    "templates/client_app_center.html": ["v757-app-hero", "Siguiente mejor acción", "Transparencia"],
    "templates/home.html": ["v757-home-strip", "Centro de mando global"],
    "templates/picks.html": ["v757-picks-trust", "Lectura rápida de picks"],
    "templates/calendar.html": ["v757-calendar-strip", "Ruta rápida del día"],
    "templates/track_record.html": ["v757-track-trust", "No se inventa ROI"],
    "static/app.css": ["V757_GLOBAL_APP_EXPERIENCE_TRUST_NAVIGATION_POLISH", "v757-kpi-grid"],
    "reports/V757_GLOBAL_APP_EXPERIENCE_TRUST_NAVIGATION_POLISH_REPORT.md": [VERSION],
}
errors=[]
for rel, needles in REQUIRED.items():
    path=ROOT/rel
    if not path.exists():
        errors.append(f"missing:{rel}")
        continue
    text=path.read_text(encoding="utf-8-sig")
    for needle in needles:
        if needle not in text:
            errors.append(f"missing-token:{rel}:{needle}")
app_source=(ROOT/"app.py").read_text(encoding="utf-8-sig")
for forbidden in ("tools/render_cron_telegram_tick.py", "AUTOMATION_SECRET =", "DB_PATH = os.getenv"):
    pass
print(json.dumps({"ok": not errors, "version": VERSION, "errors": errors}, ensure_ascii=False, indent=2))
raise SystemExit(1 if errors else 0)
