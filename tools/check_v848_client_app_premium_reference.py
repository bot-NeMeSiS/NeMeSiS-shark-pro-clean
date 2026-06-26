from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
checks = {
    "glass_cards": ".match-card" in css and ".pick-card" in css and ".live-card" in css,
    "premium_buttons": ".btn.primary" in css and "linear-gradient(135deg" in css,
    "client_nav": all(h in base for h in ["/app", "/partidos", "/live", "/picks", "/shark", "/telegram", "/support"]),
    "empty_states": "premium-empty" in css or "empty-state" in css,
    "safe_labels": all(t in (ROOT / "engines" / "api_sports_provider_engine.py").read_text(encoding="utf-8") for t in ["Sin datos reales", "Esperando proveedor", "Cuotas pendientes"]),
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
