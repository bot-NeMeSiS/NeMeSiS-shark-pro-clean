from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")

required = {
    "v841_css_marker": "V841 REFERENCE PRODUCT TEAM FINAL POLISH START" in css,
    "v841_shell": "data-v841-shell" in base,
    "client_rail_width": "--v841-rail-width" in css,
    "admin_rail_width": "--v841-admin-rail-width" in css,
    "desktop_client_margin": "margin-left:calc(var(--v841-rail-width)" in css,
    "desktop_admin_margin": "margin-left:calc(var(--v841-admin-rail-width)" in css,
    "desktop_bottom_nav_hidden": "display:none!important" in css and ".bottom-nav-clean" in css,
}

payload = {"ok": all(required.values()), "checks": required}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
