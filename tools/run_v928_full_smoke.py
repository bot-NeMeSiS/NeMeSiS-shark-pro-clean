from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V928_CANONICAL_REFERENCE_FULL_APP_ADMIN_CLIENT_MOBILE_REBUILD_FINAL"
MADRID = ZoneInfo("Europe/Madrid")


def now_madrid() -> str:
    return datetime.now(MADRID).replace(microsecond=0).isoformat()


def session_values(role: str) -> dict[str, str]:
    is_admin = role == "ADMIN"
    return {
        "user_id": f"v928-smoke-{role.lower()}",
        "user_name": "V928 Smoke Admin" if is_admin else "V928 Smoke Client",
        "username": f"v928_smoke_{role.lower()}",
        "user_email": f"v928-{role.lower()}@example.invalid",
        "user_role": role,
        "membership": role,
        "user_membership": role,
    }


def set_session(client, role: str) -> None:
    with client.session_transaction() as session:
        session.clear()
        session.update(session_values(role))


def clear_session(client) -> None:
    with client.session_transaction() as session:
        session.clear()


def record(client, method: str, path: str, allowed: set[int], **kwargs) -> dict:
    response = client.open(path, method=method, **kwargs)
    body = response.get_data(as_text=True)
    content_type = response.headers.get("content-type", "")
    return {
        "method": method,
        "route": path,
        "status": response.status_code,
        "content_type": content_type,
        "location": response.headers.get("Location", ""),
        "ok": response.status_code in allowed,
        "traceback_visible": "Traceback (most recent call last)" in body,
        "internal_server_default": "Internal Server Error" in body,
    }


def write_report(rows: list[dict], db_path: str) -> None:
    report_dir = ROOT / "reports"
    report_dir.mkdir(exist_ok=True)
    payload = {
        "ok": all(row["ok"] and not row["traceback_visible"] for row in rows),
        "version": VERSION,
        "generated_at_madrid": now_madrid(),
        "database": "temporary_empty_database",
        "database_path_exposed": False,
        "telegram_sent": False,
        "payments_executed": False,
        "rows": rows,
    }
    (report_dir / "V928_FULL_SMOKE_QA.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# V928 Full Smoke QA",
        "",
        f"- Version: `{VERSION}`.",
        f"- Resultado: `{'OK' if payload['ok'] else 'FAIL'}`.",
        "- DB: temporal y vacia; la ruta local no se publica.",
        "- Telegram enviado: no.",
        "- Pagos ejecutados: no.",
        "",
        "| Sesion/metodo | Ruta | Estado | OK |",
        "|---|---|---:|---|",
    ]
    for row in rows:
        lines.append(f"| {row.get('scope', '')} {row['method']} | `{row['route']}` | {row['status']} | {row['ok']} |")
    (report_dir / "V928_FULL_SMOKE_QA.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nemesis_v928_smoke_") as temp_dir:
        os.environ["DB_PATH"] = str(Path(temp_dir) / "smoke.db")
        os.environ["V928_SMOKE_MODE"] = "1"
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))

        import app as app_module

        flask_app = app_module.app
        flask_app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)

        def forced_safe_error():
            raise RuntimeError("v928 controlled smoke error")

        flask_app.add_url_rule(
            "/__v928_controlled_500",
            endpoint="v928_controlled_500",
            view_func=forced_safe_error,
        )
        client = flask_app.test_client()
        rows: list[dict] = []

        public = [
            "/", "/cliente-login", "/login", "/registro", "/support",
            "/manifest.json", "/service-worker.js", "/api/runtime-version",
        ]
        for path in public:
            row = record(client, "GET", path, {200, 301, 302, 303, 307, 308})
            row["scope"] = "public"
            rows.append(row)

        for path in ["/app", "/profile", "/admin/dashboard", "/admin/automation-workforce"]:
            row = record(client, "GET", path, {200, 301, 302, 303, 307, 308, 401, 403})
            row["scope"] = "anonymous-protected"
            rows.append(row)

        api_row = record(client, "GET", "/api/admin/automation-workforce/status", {403})
        api_row["scope"] = "anonymous-admin-api"
        rows.append(api_row)

        set_session(client, "FREE")
        client_routes = [
            "/app", "/calendar", "/calendario", "/live", "/directo", "/picks",
            "/track-record", "/shark", "/telegram", "/profile", "/memberships",
        ]
        for path in client_routes:
            row = record(client, "GET", path, {200, 301, 302, 303, 307, 308})
            row["scope"] = "client"
            rows.append(row)

        set_session(client, "ADMIN")
        admin_routes = [
            "/admin-login", "/admin/dashboard", "/admin/telegram/command-center",
            "/admin/users", "/admin/payments", "/admin/picks", "/admin/data-center",
            "/admin/automation-workforce", "/admin/autonomous-company-sentinel",
            "/admin/sentinel-issues", "/admin/sentinel-codex-outbox",
            "/admin/launch-certification",
        ]
        for path in admin_routes:
            allowed = {200, 301, 302, 303, 307, 308} if path == "/admin-login" else {200}
            row = record(client, "GET", path, allowed)
            row["scope"] = "admin"
            rows.append(row)

        clear_session(client)
        for path, form in {
            "/cliente-login": {"identifier": "v928-missing", "password": "wrong"},
            "/login": {"identifier": "v928-missing", "password": "wrong"},
            "/registro": {"name": "", "username": "", "email": "invalid", "password": "x"},
        }.items():
            row = record(client, "POST", path, set(range(200, 500)), data=form)
            row["scope"] = "invalid-form"
            rows.append(row)

        html_404 = record(client, "GET", "/ruta-inventada-v928", {404})
        html_404["scope"] = "404-html"
        html_404["ok"] = html_404["ok"] and "text/html" in html_404["content_type"]
        rows.append(html_404)

        api_404 = record(client, "GET", "/api/ruta-inventada-v928", {404})
        api_404["scope"] = "404-api"
        api_404["ok"] = api_404["ok"] and "application/json" in api_404["content_type"]
        rows.append(api_404)

        logging.disable(logging.CRITICAL)
        try:
            safe_500 = record(client, "GET", "/__v928_controlled_500", {500})
        finally:
            logging.disable(logging.NOTSET)
        safe_500["scope"] = "controlled-500"
        safe_500["ok"] = safe_500["ok"] and not safe_500["traceback_visible"]
        rows.append(safe_500)

        write_report(rows, os.environ["DB_PATH"])
        failed = [row for row in rows if not row["ok"] or row["traceback_visible"]]
        print(json.dumps({
            "ok": not failed,
            "version": VERSION,
            "checks": len(rows),
            "failures": failed,
            "temporary_database": True,
            "telegram_sent": False,
            "payments_executed": False,
        }, ensure_ascii=False, indent=2))
        return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
