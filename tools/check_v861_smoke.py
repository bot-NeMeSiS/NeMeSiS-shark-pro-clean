from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


VERSION = "V861_SELF_IMPROVING_OPERATIONS_OS_SAFE_AUTOMATION_FINAL"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v861_smoke.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v861-smoke")
    os.environ.setdefault("DAILY_AUTOMATION_DRY_RUN", "1")
    os.environ.setdefault("ENABLE_AUTO_TELEGRAM_PRO", "0")

    import app as app_module

    client = app_module.app.test_client()
    failures: list[str] = []
    routes = [
        "/", "/cliente-login", "/registro", "/app", "/partidos", "/calendar",
        "/live", "/directo", "/picks", "/shark", "/telegram", "/profile",
        "/support", "/track-record",
        "/admin/dashboard", "/admin/company-os", "/admin/company-audit",
        "/admin/auto-improvement", "/admin/mejora-continua", "/admin/shark-ops",
        "/admin/data-center", "/admin/api-sports", "/admin/telegram/command-center",
        "/admin/shark-ai", "/admin/daily-automation", "/admin/users",
        "/admin/memberships", "/admin/payments", "/api/runtime-version",
    ]
    for route in routes:
        response = client.get(route)
        if response.status_code >= 500:
            failures.append(f"{route} -> {response.status_code}")

    for route in [
        "/api/admin/company-os/summary",
        "/api/admin/company-audit/summary",
        "/api/admin/auto-improvement/summary",
    ]:
        response = client.get(route)
        if response.status_code != 403:
            failures.append(f"{route} sin sesion -> {response.status_code}")

    no_secret = client.get("/api/automation/auto-improvement/run?dry_run=1")
    if no_secret.status_code != 403:
        failures.append(f"auto-improvement sin secret -> {no_secret.status_code}")

    with_secret = client.get("/api/automation/auto-improvement/run?dry_run=1&secret=codex-v861-smoke")
    if with_secret.status_code != 200:
        failures.append(f"auto-improvement con secret dry_run -> {with_secret.status_code}")
    else:
        payload = with_secret.get_json() or {}
        if payload.get("no_code_writes") is not True or payload.get("no_deploy") is not True:
            failures.append("auto-improvement no declara limites seguros")

    no_master_secret = client.get("/api/automation/master-tick?dry_run=1")
    if no_master_secret.status_code != 403:
        failures.append(f"master-tick sin secret -> {no_master_secret.status_code}")

    master = client.get("/api/automation/master-tick?dry_run=1&secret=codex-v861-smoke")
    if master.status_code != 200:
        failures.append(f"master-tick con secret dry_run -> {master.status_code}")

    health = client.get("/api/automation/health-check?secret=codex-v861-smoke")
    if health.status_code != 200:
        failures.append(f"health-check con secret -> {health.status_code}")

    runtime = client.get("/api/runtime-version")
    data = runtime.get_json() if runtime.status_code == 200 else {}
    if runtime.status_code != 200:
        failures.append(f"runtime -> {runtime.status_code}")
    if data.get("app_version") != VERSION:
        failures.append("runtime app_version no es V861")
    for flag in [
        "has_v861_auto_improvement_os",
        "has_v860_project_cleanup_visual_alignment",
        "has_v859_company_audit_board",
        "has_v857_company_os",
        "has_v818_automation",
    ]:
        if not data.get(flag):
            failures.append(f"runtime flag ausente: {flag}")

    if failures:
        raise SystemExit("V861 smoke failed:\n- " + "\n- ".join(failures))
    print("V861 Flask smoke OK")


if __name__ == "__main__":
    main()
