from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


VERSION = "V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v862_smoke.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v862-smoke")
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
        "/admin/auto-improvement", "/admin/continuous-sentinel", "/admin/shark-sentinel", "/admin/app-inspector",
        "/admin/qa-bot", "/admin/bot-auditor", "/admin/data-center",
        "/admin/api-sports", "/admin/telegram/command-center", "/admin/shark-ai",
        "/admin/daily-automation", "/admin/users", "/admin/memberships",
        "/admin/payments", "/api/runtime-version",
    ]
    for route in routes:
        response = client.get(route)
        if response.status_code >= 500:
            failures.append(f"{route} -> {response.status_code}")

    for route in [
        "/api/admin/shark-sentinel/summary",
        "/api/admin/shark-sentinel/run",
        "/api/admin/continuous-sentinel/summary",
        "/api/admin/continuous-sentinel/run",
        "/api/admin/continuous-sentinel/issues",
    ]:
        response = client.get(route)
        if response.status_code != 403:
            failures.append(f"{route} sin sesion -> {response.status_code}")

    no_secret = client.get("/api/automation/shark-sentinel/run?dry_run=1")
    if no_secret.status_code != 403:
        failures.append(f"sentinel sin secret -> {no_secret.status_code}")
    with_secret = client.get("/api/automation/shark-sentinel/run?dry_run=1&secret=codex-v862-smoke")
    if with_secret.status_code != 200:
        failures.append(f"sentinel con secret dry_run -> {with_secret.status_code}")
    else:
        payload = with_secret.get_json() or {}
        if payload.get("no_code_writes") is not True or payload.get("no_deploy") is not True:
            failures.append("sentinel no declara limites seguros")

    no_secret_loop = client.get("/api/automation/continuous-sentinel/run?dry_run=1")
    if no_secret_loop.status_code != 403:
        failures.append(f"continuous sentinel sin secret -> {no_secret_loop.status_code}")
    loop_secret = client.get("/api/automation/continuous-sentinel/run?dry_run=1&secret=codex-v862-smoke")
    if loop_secret.status_code != 200:
        failures.append(f"continuous sentinel con secret dry_run -> {loop_secret.status_code}")

    master_no_secret = client.get("/api/automation/master-tick?dry_run=1")
    if master_no_secret.status_code != 403:
        failures.append(f"master-tick sin secret -> {master_no_secret.status_code}")
    master = client.get("/api/automation/master-tick?dry_run=1&secret=codex-v862-smoke")
    if master.status_code != 200:
        failures.append(f"master-tick con secret dry_run -> {master.status_code}")
    health = client.get("/api/automation/health-check?secret=codex-v862-smoke")
    if health.status_code != 200:
        failures.append(f"health-check con secret -> {health.status_code}")

    runtime = client.get("/api/runtime-version")
    data = runtime.get_json() if runtime.status_code == 200 else {}
    if runtime.status_code != 200:
        failures.append(f"runtime -> {runtime.status_code}")
    if data.get("app_version") != VERSION:
        failures.append("runtime app_version no es V862")
    for flag in [
        "has_v862_shark_sentinel",
        "has_v862_continuous_sentinel_loop",
        "has_v861_auto_improvement_os",
        "has_v860_project_cleanup_visual_alignment",
        "has_v859_company_audit_board",
        "has_v818_automation",
    ]:
        if not data.get(flag):
            failures.append(f"runtime flag ausente: {flag}")

    if failures:
        raise SystemExit("V862 smoke failed:\n- " + "\n- ".join(failures))
    print("V862 Flask smoke OK")


if __name__ == "__main__":
    main()
