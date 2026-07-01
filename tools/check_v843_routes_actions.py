from pathlib import Path
import json
import os
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str((ROOT / "data" / "v843_routes.db").resolve()))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v843-secret")

import app as nemesis  # noqa: E402

client = nemesis.app.test_client()
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
    "/api/runtime-version",
    "/admin/dashboard",
    "/admin/daily-automation",
    "/admin/automation-os",
    "/admin/data-center",
    "/admin/telegram/command-center",
    "/admin/users",
    "/admin/memberships",
    "/admin/payments",
]

route_results = []
for route in routes:
    response = client.get(route)
    route_results.append({"route": route, "status": response.status_code, "ok": response.status_code < 500 and response.status_code != 404})

bad_hrefs = []
malformed_prefixes = ("/sharkpick", "/sharkmatch", "/apprefresh", "/calendarfilter", "/livefilter")
for path in (ROOT / "templates").glob("*.html"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    for match in re.finditer(r'href=["\']([^"\']*)["\']', text):
        href = match.group(1).strip()
        if href in {"", "#", "javascript:void(0)"}:
            bad_hrefs.append({"file": str(path.relative_to(ROOT)), "href": href})
        if href.startswith(malformed_prefixes):
            bad_hrefs.append({"file": str(path.relative_to(ROOT)), "href": href, "reason": "malformed_internal_link"})

required_text = {
    "support_visible": "Soporte",
    "telegram_visible": "Telegram",
    "shark_visible": "SHARK",
    "logout_visible": "Cerrar sesión",
}
base_text = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="ignore")
text_checks = {key: value in base_text or any(value in p.read_text(encoding="utf-8", errors="ignore") for p in (ROOT / "templates").glob("*.html")) for key, value in required_text.items()}

payload = {
    "ok": all(row["ok"] for row in route_results) and not bad_hrefs and all(text_checks.values()),
    "route_results": route_results,
    "bad_hrefs": bad_hrefs,
    "text_checks": text_checks,
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
