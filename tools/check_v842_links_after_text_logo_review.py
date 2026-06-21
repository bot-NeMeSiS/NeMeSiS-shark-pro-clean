from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str((ROOT / "data" / "v842_links.db").resolve()))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v842-secret")

import app as nemesis  # noqa: E402

routes = [
    "/",
    "/cliente-login",
    "/registro",
    "/app",
    "/partidos",
    "/calendar",
    "/live",
    "/directo",
    "/picks",
    "/shark",
    "/profile",
    "/telegram",
    "/support",
    "/favorites",
    "/track-record",
    "/combis",
    "/mercados",
    "/highlights",
    "/admin/dashboard",
    "/admin/daily-automation",
    "/admin/automation-os",
    "/admin/data-center",
    "/admin/telegram/command-center",
    "/admin/users",
    "/admin/memberships",
    "/admin/payments",
]

client = nemesis.app.test_client()
results = []
for route in routes:
    response = client.get(route)
    results.append({"route": route, "status": response.status_code})

bad = [row for row in results if row["status"] >= 500 or row["status"] == 404]
payload = {"ok": not bad, "bad": bad, "results": results}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
