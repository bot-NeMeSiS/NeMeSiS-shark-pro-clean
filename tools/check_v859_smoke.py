from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v859_smoke.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v859-smoke")
    os.environ.setdefault("DAILY_AUTOMATION_DRY_RUN", "1")
    os.environ.setdefault("ENABLE_AUTO_TELEGRAM_PRO", "0")

    import app as app_module

    client = app_module.app.test_client()
    failures: list[str] = []
    routes = [
        "/", "/cliente-login", "/registro", "/app", "/inicio", "/panel-cliente",
        "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark",
        "/telegram", "/profile", "/support", "/track-record",
        "/admin/dashboard", "/admin/company-os", "/admin/company-audit",
        "/admin/auditoria-empresa", "/admin/product-board", "/admin/data-center",
        "/admin/api-sports", "/admin/api-sports-audit",
        "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation",
        "/admin/users", "/admin/memberships", "/admin/payments", "/api/runtime-version",
    ]
    for route in routes:
        response = client.get(route)
        if response.status_code >= 500:
            failures.append(f"{route} -> {response.status_code}")

    for route in ["/api/admin/company-os/summary", "/api/admin/company-audit/summary"]:
        response = client.get(route)
        if response.status_code != 403:
            failures.append(f"{route} sin sesión -> {response.status_code}")

    no_secret = client.get("/api/automation/master-tick?dry_run=1")
    if no_secret.status_code != 403:
        failures.append(f"master-tick sin secret -> {no_secret.status_code}")

    with_secret = client.get("/api/automation/master-tick?dry_run=1&secret=codex-v859-smoke")
    if with_secret.status_code != 200:
        failures.append(f"master-tick con secret dry_run -> {with_secret.status_code}")

    health = client.get("/api/automation/health-check?secret=codex-v859-smoke")
    if health.status_code != 200:
        failures.append(f"health-check con secret -> {health.status_code}")

    runtime = client.get("/api/runtime-version")
    data = runtime.get_json() if runtime.status_code == 200 else {}
    if runtime.status_code != 200:
        failures.append(f"runtime -> {runtime.status_code}")
    if data.get("app_version") != "V859_COMPANY_WIDE_ECOSYSTEM_AUDIT_AND_PRODUCT_BOARD_FINAL":
        failures.append("runtime app_version no es V859")
    for flag in ["has_v859_company_audit_board", "has_v858_visual_direction_lock", "has_v857_company_os", "has_v818_automation"]:
        if not data.get(flag):
            failures.append(f"runtime flag ausente: {flag}")

    if failures:
        raise SystemExit("V859 smoke failed:\n- " + "\n- ".join(failures))
    print("V859 Flask smoke OK")


if __name__ == "__main__":
    main()
