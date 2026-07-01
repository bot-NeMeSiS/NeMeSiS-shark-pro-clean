from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
app = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
checks = {
    "admin_links": all(h in base for h in ["/admin/data-center", "/admin/api-sports", "/admin/telegram/command-center", "/admin/daily-automation"]),
    "admin_routes": all(h in app for h in ["/admin/api-sports", "/admin/shark-ai", "/admin/data-center"]),
    "admin_sober_bg": "body[data-v848-shell=\"true\"].ns-admin::before" in css,
    "admin_no_client_floating": "body[data-v848-shell=\"true\"].ns-admin .v825-public-floating-shark" in css,
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
