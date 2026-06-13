#!/usr/bin/env python3
"""V766 QA: calendario sin Andalucía visible, resultados/highlights, rutas y seguridad intacta."""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
CALENDAR = (ROOT / "templates" / "calendar.html").read_text(encoding="utf-8")
LIVE = (ROOT / "templates" / "live.html").read_text(encoding="utf-8")
MATCH = (ROOT / "templates" / "match_detail.html").read_text(encoding="utf-8")
HIGHLIGHTS = (ROOT / "templates" / "highlights.html").read_text(encoding="utf-8")

checks = []

def ok(name, cond):
    checks.append((name, bool(cond)))

version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
ok("version_v766", version in {"V766_CALENDAR_RESULTS_HIGHLIGHTS_ORDER_AUTOMATION", "V767_MADRID_TIME_EVERYWHERE_CERTIFICATION"})
ok("app_version_v766", ('APP_VERSION = "V766_CALENDAR_RESULTS_HIGHLIGHTS_ORDER_AUTOMATION"' in APP or 'APP_VERSION = "V767_MADRID_TIME_EVERYWHERE_CERTIFICATION"' in APP))
ok("calendar_no_andalucia_tab", '"label": "Andalucía"' not in APP and 'href="/calendar?lane=andalucia"' not in CALENDAR)
ok("calendar_results_lane", '"results": "Resultados"' in APP and '/calendar?lane=results' in CALENDAR)
ok("calendar_highlight_badge", 'calendar-highlight-strip' in CALENDAR and 'Resumen disponible' in CALENDAR)
ok("highlights_client_routes", '@app.route("/highlights")' in APP and '@app.route("/resumenes")' in APP)
ok("highlights_api", '@app.route("/api/client/highlights")' in APP)
ok("highlights_cron_endpoint", '@app.route("/api/automation/highlights/sync"' in APP and 'automation_cron_access_allowed' in APP)
ok("sportsdb_highlights_import", 'from engines.sportsdb_highlights_engine import' in APP)
ok("live_has_highlights_link", '/highlights' in LIVE and 'v766-card-note' in LIVE)
ok("match_detail_highlights", 'v766-match-highlights' in MATCH and 'No se descarga ni se rehostea' in MATCH)
ok("base_nav_highlights", '/highlights' in BASE)
ok("scheduler_highlights_task", 'task_name == "highlights"' in APP and '"highlights"' in APP)
ok("telegram_cron_preserved", 'tools/render_cron_telegram_tick.py' in (ROOT / 'tools' / 'build_clean_release.py').read_text(encoding='utf-8') or (ROOT / 'tools' / 'render_cron_telegram_tick.py').exists())
ok("automation_secret_preserved", '/api/automation/telegram/tick' in APP and 'AUTOMATION_SECRET' in APP)
ok("db_path_preserved", 'DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in APP)

failed = [name for name, passed in checks if not passed]
for name, passed in checks:
    print(f"{'OK' if passed else 'FAIL'} {name}")
if failed:
    raise SystemExit("V766 check failed: " + ", ".join(failed))
print("V766 calendar/results/highlights/order QA OK")
