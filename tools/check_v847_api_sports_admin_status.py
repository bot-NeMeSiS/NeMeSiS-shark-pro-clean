from pathlib import Path
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v847_admin_status.db"))

import app as nemesis  # noqa: E402

client = nemesis.app.test_client()
rules = [str(rule) for rule in nemesis.app.url_map.iter_rules()]
checks = {
    "admin_page_route": "/admin/api-sports" in rules,
    "admin_audit_alias": "/admin/api-sports-audit" in rules,
    "api_status_route": "/api/admin/api-sports/status" in rules,
    "api_requires_admin": client.get("/api/admin/api-sports/status").status_code == 403,
    "template_exists": (ROOT / "templates" / "admin_api_sports_audit.html").exists(),
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
