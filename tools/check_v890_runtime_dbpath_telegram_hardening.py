from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V890_RUNTIME_DBPATH_TELEGRAM_PREMIUM_QA_HARDENING_FINAL"
CURRENT_COMPATIBLE_PREFIXES = ("V890_", "V891_", "V892_", "V893_", "V894_")
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
    base = read("templates/base.html")

    require(version_txt.startswith(CURRENT_COMPATIBLE_PREFIXES), "VERSION.txt is not compatible with V890/V891/V892/V893/V894 lineage", failures)
    require(app_version_file == version_txt, "APP_VERSION does not match VERSION.txt", failures)
    require(f"APP_VERSION = '{version_txt}'" in app_py, "app.py APP_VERSION mismatch", failures)
    require("def resolve_default_db_path" in app_py, "resolve_default_db_path missing", failures)
    require('return "/data/database.db"' in app_py, "Render DB fallback missing", failures)
    require('BASE_DIR / "data" / "database.db"' in app_py, "local DB fallback missing", failures)
    require("has_v890_runtime_dbpath_telegram_hardening" in app_py, "runtime V890 flag missing", failures)
    require("has_v889_telegram_premium_picks_intelligence" in app_py, "V889 flag not preserved", failures)
    require("has_v888_sentinel_autopilot_self_improvement" in app_py, "V888 flag not preserved", failures)
    require("has_v887_telegram_queue_skipped_hotfix" in app_py, "V887 flag not preserved", failures)
    require(version_txt in base, "base.html current cache/version missing", failures)
    require((ROOT / "engines" / "telegram_pick_quality_engine.py").exists(), "V889 quality engine missing", failures)
    require((ROOT / "tools" / "check_v889_telegram_premium_picks.py").exists(), "V889 check missing", failures)

    for report in [
        "reports/V890_RUNTIME_DBPATH_TELEGRAM_PREMIUM_QA_HARDENING_REPORT.md",
        "reports/V890_LOCAL_RUNTIME_DBPATH_QA.md",
        "reports/V890_TELEGRAM_PREMIUM_FOLLOWUP_QA.md",
        "reports/V890_NEXT_STEPS.md",
    ]:
        require((ROOT / report).exists(), f"report missing: {report}", failures)

    combined = "\n".join([app_py, read("engines/telegram_pick_quality_engine.py")])
    require(not re.search(r"(TELEGRAM_BOT_TOKEN\s*=|AUTOMATION_SECRET\s*=|API_KEY\s*=|sk_live_|bot[0-9]+:)", combined), "possible secret assignment found", failures)
    require("apuesta segura" not in combined.lower(), "unsafe betting claim found", failures)

    os.environ["AUTOMATION_SECRET"] = "v890-secret"
    os.environ.pop("DB_PATH", None)
    os.environ.pop("RENDER", None)
    os.environ.pop("RENDER_SERVICE_NAME", None)
    os.environ.pop("RENDER_EXTERNAL_HOSTNAME", None)
    import app  # noqa: WPS433

    local_path = Path(app.DB_PATH)
    require(local_path.name == "database.db", "local fallback DB filename mismatch", failures)
    require(str(local_path).lower().endswith(str(Path("data") / "database.db").lower()), "local fallback DB path not project data/database.db", failures)

    client = app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, "runtime-version not 200", failures)
    runtime_json = runtime.get_json() or {}
    require(runtime_json.get("app_version") == version_txt, "runtime app_version mismatch", failures)
    require(runtime_json.get("has_v890_runtime_dbpath_telegram_hardening") is True, "runtime V890 flag false", failures)
    require(runtime_json.get("has_v889_telegram_premium_picks_intelligence") is True, "runtime V889 flag false", failures)
    require(client.get("/api/admin/telegram/pick-preview").status_code == 403, "Telegram preview without session not 403", failures)
    require(client.get("/api/automation/telegram/tick").status_code == 403, "Telegram cron without secret not 403", failures)

    if failures:
        print("V890 runtime DBPATH Telegram hardening check FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V890 runtime DBPATH Telegram hardening check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
