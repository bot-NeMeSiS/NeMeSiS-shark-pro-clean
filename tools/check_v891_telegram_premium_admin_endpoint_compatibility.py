from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V891_TELEGRAM_PREMIUM_ADMIN_ENDPOINT_COMPATIBILITY_FINAL"
CURRENT_COMPATIBLE_PREFIXES = ("V891_", "V892_", "V893_")
sys.path.insert(0, str(ROOT))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    version_txt = read("VERSION.txt").strip().lstrip("\ufeff")
    app_version_file = read("APP_VERSION").strip().lstrip("\ufeff")
    app_py = read("app.py")

    require(version_txt.startswith(CURRENT_COMPATIBLE_PREFIXES), "VERSION.txt is not compatible with V891/V892/V893 lineage", failures)
    require(app_version_file == version_txt, "APP_VERSION does not match VERSION.txt", failures)
    require(f"APP_VERSION = '{version_txt}'" in app_py, "app.py APP_VERSION mismatch", failures)
    require("has_v891_telegram_premium_admin_endpoint_compatibility" in app_py, "runtime V891 flag missing", failures)
    require("has_v890_runtime_dbpath_telegram_hardening" in app_py, "V890 flag not preserved", failures)
    require("has_v889_telegram_premium_picks_intelligence" in app_py, "V889 flag not preserved", failures)
    require("has_v888_sentinel_autopilot_self_improvement" in app_py, "V888 flag not preserved", failures)
    require("has_v887_telegram_queue_skipped_hotfix" in app_py, "V887 flag not preserved", failures)

    for route in [
        "/api/admin/telegram/pick-quality",
        "/api/admin/telegram/premium-preview",
        "/api/admin/telegram/dry-run-premium-picks",
        "/api/admin/telegram/blocked-picks",
        "/api/admin/telegram/quality-status",
    ]:
        require(route in app_py, f"endpoint missing: {route}", failures)

    for report in [
        "reports/V891_TELEGRAM_PREMIUM_ADMIN_ENDPOINT_COMPATIBILITY_REPORT.md",
        "reports/V889_TELEGRAM_PICK_QUALITY_QA.md",
        "reports/V889_TELEGRAM_COMMAND_CENTER_QA.md",
        "reports/V889_AUTOPILOT_TELEGRAM_INTEGRATION_QA.md",
        "reports/V891_NEXT_STEPS.md",
    ]:
        require((ROOT / report).exists(), f"report missing: {report}", failures)

    combined = "\n".join([app_py, read("engines/telegram_pick_quality_engine.py")])
    require(not re.search(r"(TELEGRAM_BOT_TOKEN\s*=|AUTOMATION_SECRET\s*=|API_KEY\s*=|sk_live_|bot[0-9]+:)", combined), "possible secret assignment found", failures)
    require("apuesta segura" not in combined.lower(), "unsafe betting claim found", failures)

    os.environ["AUTOMATION_SECRET"] = "v891-secret"
    os.environ.pop("DB_PATH", None)
    import app  # noqa: WPS433

    client = app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, "runtime-version not 200", failures)
    runtime_json = runtime.get_json() or {}
    require(runtime_json.get("app_version") == version_txt, "runtime app_version mismatch", failures)
    require(runtime_json.get("has_v891_telegram_premium_admin_endpoint_compatibility") is True, "runtime V891 flag false", failures)
    require(runtime_json.get("has_v889_telegram_premium_picks_intelligence") is True, "runtime V889 flag false", failures)

    for route in [
        "/api/admin/telegram/pick-quality",
        "/api/admin/telegram/premium-preview",
        "/api/admin/telegram/blocked-picks",
        "/api/admin/telegram/quality-status",
    ]:
        require(client.get(route).status_code == 403, f"admin endpoint without session not 403: {route}", failures)
    require(client.post("/api/admin/telegram/dry-run-premium-picks", json={"membership": "PRO"}).status_code == 403, "dry-run premium without session not 403", failures)
    require(client.get("/api/automation/telegram/tick").status_code == 403, "Telegram cron without secret not 403", failures)

    if failures:
        print("V891 Telegram endpoint compatibility check FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V891 Telegram endpoint compatibility check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
