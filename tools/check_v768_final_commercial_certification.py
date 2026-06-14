#!/usr/bin/env python3
"""Static QA for V768 pick results, Telegram certification and commercial launch layer."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V768_PICK_RESULTS_TRACK_RECORD_TELEGRAM_PRODUCTION_CERTIFICATION"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    app = read("app.py")
    grading = read("engines/pick_grading_engine.py")
    scheduler = read("engines/scheduler_engine.py")
    css = read("static/app.css")

    require((ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip() == VERSION, "VERSION.txt no está en V768", errors)
    require(f'APP_VERSION = "{VERSION}"' in app, "APP_VERSION no está en V768", errors)
    require("commercial_launch_snapshot" in app and "final_launch_certification_engine" in app, "No se importa certificación final", errors)
    require('/api/automation/picks/grade' in app, "Falta endpoint cron /api/automation/picks/grade", errors)
    require('automation_cron_access_allowed()' in app and 'automation_json_forbidden()' in app, "El endpoint de grading no está protegido por AUTOMATION_SECRET", errors)
    require('/admin/final-certification' in app and 'admin_final_certification.html' in app, "Falta panel admin de certificación", errors)
    require('"pick_grading"' in app and 'run_pick_grading(DB_PATH' in app, "Scheduler no ejecuta pick_grading", errors)
    require('"pick_grading"' in scheduler and 'PICK_GRADING_REFRESH_HOURS' in scheduler, "scheduler_engine no declara pick_grading", errors)

    for token in ("_settle_total_goals", "_settle_btts", "_settle_dnb", "_settle_double_chance"):
        require(token in grading, f"pick_grading_engine no soporta {token}", errors)
    require('UPDATE picks SET status=?, result_status=?' in grading, "El grading aplicado no actualiza result_status correctamente", errors)
    require('V768 final launch certification' in read('engines/final_launch_certification_engine.py'), "Motor V768 no tiene cabecera esperada", errors)
    require((ROOT / 'templates/admin_final_certification.html').exists(), "Falta template admin_final_certification.html", errors)
    require('v768-cert' in css and 'status-won' in css, "Falta CSS V768", errors)

    # No raw secret leaks in the new template/engine.
    combo = read('templates/admin_final_certification.html') + read('engines/final_launch_certification_engine.py')
    require('TELEGRAM_BOT_TOKEN' not in combo or '_env_present("TELEGRAM_BOT_TOKEN")' in combo, "Posible exposición de token en V768", errors)

    if errors:
        print("V768_CHECK_FAIL")
        for e in errors:
            print("-", e)
        return 1
    print("V768_CHECK_OK")
    print("- Version:", VERSION)
    print("- Certificación final, grading automático y Telegram readiness presentes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
