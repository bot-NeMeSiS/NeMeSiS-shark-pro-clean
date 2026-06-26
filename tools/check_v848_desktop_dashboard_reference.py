from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
checks = {
    "desktop_media": "@media(min-width:1024px)" in css,
    "client_rail": "v828-client-rail" in base and ".v828-client-rail" in css,
    "admin_rail": "v808-admin-rail" in base and ".v808-admin-rail" in css,
    "dashboard_depth": "box-shadow:0 18px 70px" in css,
    "admin_no_bottom_nav": ".ns-admin .bottom-nav" in css,
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
