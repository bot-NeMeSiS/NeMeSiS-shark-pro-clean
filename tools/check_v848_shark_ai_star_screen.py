from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
checks = {
    "v845_engine_kept": "shark_ai_product_assistant_engine" in app,
    "shark_hero_polished": ".v845-shark-hero" in css and "shark-logo.svg" in css,
    "floating_hidden_on_shark": '[data-ns-route="/shark"]' in css and '[data-ns-route="/shark-ai"]' in css,
    "admin_shark_route": "/admin/shark-ai" in app,
    "api_shark_ask": "/api/shark/ask" in app,
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
