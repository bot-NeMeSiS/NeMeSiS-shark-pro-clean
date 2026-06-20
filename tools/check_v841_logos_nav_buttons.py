from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")

links = ["/app", "/partidos", "/live", "/picks", "/shark", "/profile", "/telegram", "/support"]
required = {
    "logo_asset_linked": "/static/img/shark-logo.svg" in base,
    "favicon_present": 'rel="icon"' in base or "rel='icon'" in base,
    "primary_links_present": all(link in base for link in links),
    "button_touch_size": "min-height:44px" in css,
    "nav_brand_present": "NeMeSiS SHARK PRO" in base,
}

payload = {"ok": all(required.values()), "checks": required}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
