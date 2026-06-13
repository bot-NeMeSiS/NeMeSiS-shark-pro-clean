#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSION = "V758_ADAPTIVE_DESKTOP_MOBILE_TOP_APP_EXPERIENCE"
REQUIRED = {
    "VERSION.txt": [VERSION],
    "app.py": [VERSION, "build_v758_adaptive_experience", "/api/client/device-experience", "v758_adaptive_experience_page"],
    "engines/adaptive_experience_engine.py": ["infer_device", "build_v758_adaptive_experience", "build_v758_device_api_payload"],
    "templates/base.html": ["nsV758AdaptiveExperience", "v758-device-switcher", "viewport-fit=cover"],
    "templates/adaptive_experience.html": ["V758", "Modo PC", "Modo móvil"],
    "templates/partials/v758_adaptive_strip.html": ["v758-adaptive-strip", "Ajuste PC/Móvil"],
    "templates/home.html": ["partials/v758_adaptive_strip.html"],
    "templates/picks.html": ["partials/v758_adaptive_strip.html"],
    "templates/calendar.html": ["partials/v758_adaptive_strip.html"],
    "templates/live.html": ["partials/v758_adaptive_strip.html"],
    "templates/match_detail.html": ["partials/v758_adaptive_strip.html"],
    "templates/track_record.html": ["partials/v758_adaptive_strip.html"],
    "templates/client_app_center.html": ["partials/v758_adaptive_strip.html"],
    "static/app.css": ["V758_ADAPTIVE_DESKTOP_MOBILE_TOP_APP_EXPERIENCE", "ns-device-mobile", "v758-device-kpis"],
    "reports/V758_ADAPTIVE_DESKTOP_MOBILE_TOP_APP_EXPERIENCE_REPORT.md": [VERSION],
}
errors=[]
for rel, needles in REQUIRED.items():
    p=ROOT/rel
    if not p.exists():
        errors.append(f"missing:{rel}")
        continue
    text=p.read_text(encoding="utf-8-sig")
    for n in needles:
        if n not in text:
            errors.append(f"missing-token:{rel}:{n}")
# Ensure protected systems preserved
app=(ROOT/"app.py").read_text(encoding="utf-8-sig")
if not (ROOT/"tools"/"render_cron_telegram_tick.py").exists():
    errors.append("preserve-file-missing:tools/render_cron_telegram_tick.py")
for token in ["AUTOMATION_SECRET", "DB_PATH = os.getenv", "api_automation_telegram_tick"]:
    if token not in app:
        errors.append(f"preserve-token-missing:{token}")
print(json.dumps({"ok": not errors, "version": VERSION, "errors": errors}, ensure_ascii=False, indent=2))
raise SystemExit(1 if errors else 0)
