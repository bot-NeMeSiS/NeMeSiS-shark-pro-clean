from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
live = (ROOT / "templates" / "live.html").read_text(encoding="utf-8", errors="replace")
detail = (ROOT / "templates" / "match_detail.html").read_text(encoding="utf-8", errors="replace")

checks = {
    "calendar_live_api_endpoint": "def api_calendar" in app and "sync_api_football_live_tracker" in app,
    "live_page_provider_context": "api_football_live_tracker" in live and "api_football_live_quality" in live,
    "match_detail_provider_context": "api_football_live_tracker" in detail and "API-Football" in detail,
    "data_center_provider_summary": '"api_sports_provider"' in app,
    "safe_empty_states": all(text in app + live + detail + (ROOT / "engines" / "api_sports_provider_engine.py").read_text(encoding="utf-8", errors="replace") for text in ["Esperando proveedor", "Sin datos reales", "Resultado pendiente"]),
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
