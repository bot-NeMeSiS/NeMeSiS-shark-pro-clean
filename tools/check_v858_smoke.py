from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v858_smoke.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v858-smoke")
    os.environ.setdefault("DAILY_AUTOMATION_DRY_RUN", "1")
    os.environ.setdefault("ENABLE_AUTO_TELEGRAM_PRO", "0")

    import app as app_module

    client = app_module.app.test_client()
    failures: list[str] = []
    routes = [
        "/", "/cliente-login", "/registro", "/app", "/inicio", "/panel-cliente",
        "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark",
        "/telegram", "/profile", "/support", "/track-record",
        "/admin/dashboard", "/admin/company-os", "/admin/empresa",
        "/admin/operating-system", "/admin/data-center", "/admin/api-sports",
        "/admin/api-sports-audit", "/admin/telegram/command-center",
        "/admin/shark-ai", "/admin/daily-automation", "/admin/users",
        "/admin/memberships", "/admin/payments", "/api/runtime-version",
    ]
    for route in routes:
        response = client.get(route)
        if response.status_code >= 500:
            failures.append(f"{route} -> {response.status_code}")

    api_company = client.get("/api/admin/company-os/summary")
    if api_company.status_code != 403:
        failures.append(f"company-os API sin sesión -> {api_company.status_code}")

    no_secret = client.get("/api/automation/master-tick?dry_run=1")
    if no_secret.status_code != 403:
        failures.append(f"master-tick sin secret -> {no_secret.status_code}")

    with_secret = client.get("/api/automation/master-tick?dry_run=1&secret=codex-v858-smoke")
    if with_secret.status_code != 200:
        failures.append(f"master-tick con secret dry_run -> {with_secret.status_code}")

    health = client.get("/api/automation/health-check?secret=codex-v858-smoke")
    if health.status_code != 200:
        failures.append(f"health-check con secret -> {health.status_code}")

    runtime = client.get("/api/runtime-version")
    if runtime.status_code != 200:
        failures.append(f"runtime -> {runtime.status_code}")
    else:
        data = runtime.get_json() or {}
        if data.get("app_version") != "V858_VISUAL_DIRECTION_LOCK_FULL_APP_REFERENCE_FINAL":
            failures.append("runtime app_version no es V858")
        for flag in ["has_v858_visual_direction_lock", "has_v857_company_os", "has_v856_real_app_reference_gap_second_pass", "has_v818_automation"]:
            if not data.get(flag):
                failures.append(f"runtime flag ausente: {flag}")

    if failures:
        raise SystemExit("V858 smoke failed:\n- " + "\n- ".join(failures))
    print("V858 Flask smoke OK")


if __name__ == "__main__":
    main()
