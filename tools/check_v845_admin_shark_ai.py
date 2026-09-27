from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = (ROOT / "app.py").read_text(encoding="utf-8")
dashboard = (ROOT / "templates" / "admin_dashboard.html").read_text(encoding="utf-8")
master = (ROOT / "blueprints" / "admin_master_control.py").read_text(encoding="utf-8")
checks = [
    "/admin/shark-ai" in app,
    "v845_shark_admin_summary" in app,
    "OPENAI" in app + master,
    "data-admin-master-control" in dashboard,
    'id="master-ai-title"' in dashboard,
    "SHARK Admin AI" in dashboard,
    "data-master-ai-state" in dashboard,
    "data-master-ai-note" in dashboard,
]
ok = all(checks)
print({"ok": ok})
raise SystemExit(0 if ok else 1)
