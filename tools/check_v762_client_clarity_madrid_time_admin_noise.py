#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V762_CLIENT_CLARITY_MADRID_TIME_ADMIN_NOISE_POLISH"
NEXT_VERSIONS = {"V769_HIGHLIGHTS_RESULTS_CONTENT_CENTER_FINAL", "V768_PICK_RESULTS_TRACK_RECORD_TELEGRAM_PRODUCTION_CERTIFICATION", "V767_MADRID_TIME_EVERYWHERE_CERTIFICATION", "V763_WORLD_CUP_LAUNCH_CLIENT_FINALIZATION_POLISH", "V764_DYNAMIC_COMPETITION_MODE_ENGINE", "V765_MARKETS_COMBIS_CLIENT_STRUCTURE_POLISH", "V766_CALENDAR_RESULTS_HIGHLIGHTS_ORDER_AUTOMATION"}

def ok(cond, msg):
    if not cond:
        raise SystemExit(f"[V762][FAIL] {msg}")
    print(f"[V762][OK] {msg}")

version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
ok(version == VERSION or version in NEXT_VERSIONS, "VERSION.txt apunta a V762 o versión posterior compatible")
app = (ROOT / "app.py").read_text(encoding="utf-8")
ok(f'APP_VERSION = "{VERSION}"' in app or any(f'APP_VERSION = "{v}"' in app for v in NEXT_VERSIONS), "APP_VERSION actualizado o posterior compatible")
ok("client_match_display_context" in app and "match_full_datetime" in app, "filtros/labels cliente para día y hora Madrid creados")
ok("enrich_pick_client_context" in app and "client_match_label" in app, "picks enriquecidos con contexto de partido")
ok("Ejecuta Cron" not in app, "mensajes cliente sin instrucciones internas de Cron")
ok("tools/render_cron_telegram_tick.py" not in app or "/api/automation/telegram/tick" in app, "tick Telegram/Cron conservado")
home = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
ok("Partidos de hoy y próximos" in home and ("m|match_full_datetime" in home or "client_full_datetime_label" in home or "client_time_label" in home), "home muestra día/hora Madrid en partidos")
ok("Picks activos destacados" in home and "client_match_label" in home and "client_market_label" in home, "home picks con partido, mercado, cuota y riesgo")
calendar = (ROOT / "templates" / "calendar.html").read_text(encoding="utf-8")
ok("Cada tarjeta muestra fecha, hora Madrid" in calendar and "match_full_datetime" in calendar, "calendario con fecha/hora/estado claro")
ok("ejecuta Cron" not in calendar.lower() and "SportsDB" not in calendar, "calendario sin lenguaje técnico/admin para cliente")
live = (ROOT / "templates" / "live.html").read_text(encoding="utf-8")
ok("Directo, resultados y próximos partidos" in live and "match_full_datetime" in live, "live con día/hora Madrid y resultados")
picks = (ROOT / "templates" / "picks.html").read_text(encoding="utf-8")
ok("client_match_label" in picks and "client_full_datetime_label" in picks and "client_odds_label" in picks, "picks con partido completo, hora y cuota clara")
match = (ROOT / "templates" / "match_detail.html").read_text(encoding="utf-8")
ok("Día y hora Madrid" in match and "match_full_datetime" in match, "detalle partido con día/hora Madrid completa")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
ok("V762_CLIENT_CLARITY_MADRID_TIME_ADMIN_NOISE_POLISH" in css and "v762-match-row" in css, "CSS V762 aplicado")
for template in ["home.html", "calendar.html", "live.html", "picks.html", "track_record.html", "client_app_center.html", "match_detail.html", "client_menu.html"]:
    text = (ROOT / "templates" / template).read_text(encoding="utf-8")
    for bad in ["Command Center", "DB_PATH", "APP_VERSION", "Ejecuta Cron", "V759", "V760", "V761", "V762"]:
        ok(bad not in text, f"{template} no muestra ruido interno: {bad}")
ok((ROOT / "reports" / "V762_CLIENT_CLARITY_MADRID_TIME_ADMIN_NOISE_POLISH_REPORT.md").exists(), "reporte V762 creado")
print("[V762] Client clarity checks OK")
