from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V929_NAVIGATION_INTEGRITY_ROUTE_NOT_FOUND_FULL_APP_RECOVERY_FINAL"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def prepare_app():
    os.environ["DB_PATH"] = str(Path(tempfile.gettempdir()) / "nemesis_v929_checks.db")
    os.environ.setdefault("SECRET_KEY", "v929-local-check-only")
    os.environ["ENABLE_AUTOMATED_RENDER_DEPLOY"] = "0"
    import app as app_module

    app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
    return app_module


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def finish(name: str, checks: dict[str, bool], details: dict | None = None) -> int:
    failed = sorted(key for key, value in checks.items() if not value)
    payload = {
        "check": name,
        "ok": not failed,
        "checks": checks,
        "failed": failed,
        "details": details or {},
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


def mock_session(client, role: str) -> None:
    with client.session_transaction() as session:
        if role == "admin":
            session.update({
                "user_id": "v929-admin-check",
                "user_name": "Admin QA",
                "username": "admin_qa",
                "user_email": "qa-admin@example.invalid",
                "user_role": "ADMIN",
                "membership": "ADMIN",
                "user_membership": "ADMIN",
            })
        else:
            session.update({
                "user_id": "v929-client-check",
                "user_name": "Cliente QA",
                "username": "client_qa",
                "user_email": "qa-client@example.invalid",
                "user_role": "PRO",
                "membership": "PRO",
                "user_membership": "PRO",
            })
