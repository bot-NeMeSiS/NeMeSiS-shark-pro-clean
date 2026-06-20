from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str((ROOT / "data" / "v841_links.db").resolve()))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v841-secret")

import app as nemesis  # noqa: E402

routes = {rule.rule for rule in nemesis.app.url_map.iter_rules()}
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
required_routes = [
    "/app", "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark",
    "/profile", "/telegram", "/support", "/favorites", "/track-record", "/combis",
    "/mercados", "/highlights", "/api/automation/master-tick",
    "/api/automation/health-check", "/admin/dashboard", "/admin/daily-automation",
    "/admin/automation-os", "/admin/data-center", "/admin/telegram/command-center",
    "/admin/users", "/admin/memberships", "/admin/payments",
]
missing_routes = [route for route in required_routes if route not in routes]
required_links = ["/app", "/partidos", "/live", "/picks", "/shark", "/profile", "/telegram", "/support"]
missing_links = [link for link in required_links if link not in base]

payload = {"ok": not missing_routes and not missing_links, "missing_routes": missing_routes, "missing_links": missing_links}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
