#!/usr/bin/env python3
"""V769 QA: highlights/results content center finalization."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
COMPATIBLE_VERSIONS = {
    "V769_HIGHLIGHTS_RESULTS_CONTENT_CENTER_FINAL",
    "V771_TELEGRAM_ACTIVITY_PRO_FORMAT_SCHEDULE_FINAL",
    "V772_TELEGRAM_VISUAL_CARDS_APP_GLOBAL_POLISH_CLEANUP",
}
SPORTSDB = (ROOT / "engines" / "sportsdb_highlights_engine.py").read_text(encoding="utf-8")
HIGHLIGHTS = (ROOT / "templates" / "highlights.html").read_text(encoding="utf-8")
DETAIL = (ROOT / "templates" / "highlight_detail.html").read_text(encoding="utf-8")
MATCH = (ROOT / "templates" / "match_detail.html").read_text(encoding="utf-8")
HOME = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
TRACK = (ROOT / "templates" / "track_record.html").read_text(encoding="utf-8")
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
CRON = (ROOT / "tools" / "render_cron_highlights_sync.py").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

checks = []

def ok(name: str, cond: bool):
    checks.append((name, bool(cond)))

ok("version_v769", VERSION in COMPATIBLE_VERSIONS and any(f'APP_VERSION = "{item}"' in APP for item in COMPATIBLE_VERSIONS))
ok("content_center_helpers", "def v769_highlights_content_center" in APP and "def v769_highlight_card_from_row" in APP)
ok("highlight_detail_routes", '@app.route("/resumen/<highlight_id>")' in APP and 'highlight_detail.html' in APP)
ok("client_api_center", "/api/client/highlights/content-center" in APP)
ok("admin_highlights_center", "/admin/highlights-center" in APP and "admin_highlights_center.html" in APP)
ok("cron_runner", "render_cron_highlights_sync.py" in CRON and "/api/automation/highlights/sync" in CRON)
ok("sportsdb_embed_schema", "embed_url" in SPORTSDB and "youtube-nocookie" in SPORTSDB and "rights_note" in SPORTSDB)
ok("highlights_template_embed", "v769-video-frame" in HIGHLIGHTS and "iframe" in HIGHLIGHTS and "Finalizados pendientes" in HIGHLIGHTS)
ok("highlight_detail_template", "highlight_detail" in DETAIL or "Resumen del partido" in DETAIL)
ok("match_detail_embed", "v769_match_highlights" in MATCH and "YouTube" in MATCH and "no descarga" in MATCH)
ok("home_center", "v769_highlights_center" in HOME and "Resultados y resúmenes" in HOME)
ok("track_evidence", "Evidencia visual de resultados" in TRACK and "v769_highlights_center" in TRACK)
ok("base_admin_nav", "/admin/highlights-center" in BASE)
ok("css_v769", "V769 Highlights" in CSS and ".v769-highlight-grid" in CSS)
ok("no_video_download", "descarga ni rehostea" in HIGHLIGHTS.lower())
ok("telegram_preserved", "/api/automation/telegram/tick" in APP and "render_cron_telegram_tick.py" in (ROOT / "tools" / "render_cron_telegram_tick.py").read_text(encoding="utf-8"))

failed = [name for name, value in checks if not value]
if failed:
    print("V769 highlights content center QA FAILED:", ", ".join(failed))
    raise SystemExit(1)
print("V769 highlights/results content center QA OK")
