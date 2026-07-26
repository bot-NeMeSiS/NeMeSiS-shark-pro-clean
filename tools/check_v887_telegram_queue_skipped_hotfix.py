#!/usr/bin/env python3
"""Validate V887 Telegram QUEUE_SKIPPED runtime hotfix."""
from __future__ import annotations

import importlib
import os
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V887_TELEGRAM_QUEUE_SKIPPED_RUNTIME_HOTFIX_FINAL"
CURRENT_VERSION = "V888_REAL_ERRORS_SWEEP_TELEGRAM_MATCHES_PICKS_NAV_SENTINEL_FINAL"
REPORTS = [
    "V887_TELEGRAM_QUEUE_SKIPPED_RUNTIME_HOTFIX_REPORT.md",
    "V887_TELEGRAM_QUEUE_SKIPPED_ERROR_AUDIT.md",
    "V887_TELEGRAM_CRON_TICK_QA.md",
    "V887_NEXT_STEPS.md",
]


def fail(message: str) -> None:
    raise SystemExit(f"V887 Telegram queue skipped hotfix check failed: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig", errors="replace")


def check_static_contract() -> None:
    app_py = read("app.py")
    delivery_engine = read("engines/telegram_delivery_engine.py")
    base = read("templates/base.html")

    version_txt = read("VERSION.txt").strip()
    app_version_file = read("APP_VERSION").strip()
    require(version_txt in {VERSION, CURRENT_VERSION} or version_txt.startswith(("V88", "V89", "V9")), "VERSION.txt does not preserve V887+ lineage")
    require(app_version_file == version_txt, "APP_VERSION file does not match VERSION.txt")
    require(f"APP_VERSION = '{version_txt}'" in app_py, "app.py APP_VERSION does not match VERSION.txt")
    require("data-v887-shell" in base, "base.html missing data-v887-shell")
    require("has_v887_telegram_queue_skipped_hotfix" in app_py, "runtime V887 flag missing")

    require(re.search(r"\bQUEUE_SKIPPED\s*=\s*['\"]skipped['\"]", delivery_engine), "QUEUE_SKIPPED is not defined as skipped")
    require("QUEUE_SKIPPED," in app_py and "from engines.telegram_delivery_engine import" in app_py, "QUEUE_SKIPPED is not imported in app.py")
    require("UPDATE telegram_queue SET status=?, error_message=?, updated_at=? WHERE id=?" in app_py, "skipped queue update branch missing")
    require("(QUEUE_SKIPPED," in app_py, "skipped queue branch does not use QUEUE_SKIPPED")

    require("should_skip_duplicate" in app_py and "telegram_dedupe_key" in app_py, "Telegram dedupe contract not preserved")
    require("filter_telegram_candidates" in app_py and "telegram_quality_filter" in app_py, "Telegram no-filler quality filter not preserved")
    require("TELEGRAM_BOT_TOKEN =" not in app_py and "AUTOMATION_SECRET =" not in app_py, "possible secret assignment found in app.py")
    require("apuesta segura" not in app_py.lower() and "garantizado" not in app_py.lower(), "unsafe betting promise found")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")


def check_runtime_cron_endpoint() -> None:
    db_fd, db_path = tempfile.mkstemp(prefix="v887_telegram_", suffix=".db")
    os.close(db_fd)

    previous_env = {key: os.environ.get(key) for key in [
        "DB_PATH",
        "AUTOMATION_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "ENABLE_AUTO_TELEGRAM_PRO",
        "TELEGRAM_AUTO_ENABLED",
    ]}
    os.environ["DB_PATH"] = db_path
    os.environ["AUTOMATION_SECRET"] = "v887-local-secret"
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["TELEGRAM_CHAT_ID"] = ""
    os.environ["ENABLE_AUTO_TELEGRAM_PRO"] = "0"
    os.environ["TELEGRAM_AUTO_ENABLED"] = "0"

    try:
        sys.path.insert(0, str(ROOT))
        app_mod = importlib.import_module("app")
        app_mod.app.config.update(TESTING=True, SECRET_KEY="v887-test")
        client = app_mod.app.test_client()

        runtime = client.get("/api/runtime-version")
        require(runtime.status_code == 200, f"runtime status {runtime.status_code}")
        runtime_json = runtime.get_json() or {}
        require(str(runtime_json.get("app_version") or "").startswith(("V88", "V89", "V9")), "runtime app_version is not V887+")
        require(runtime_json.get("version_txt") == runtime_json.get("app_version"), "runtime version_txt mismatch")
        require(runtime_json.get("has_v887_telegram_queue_skipped_hotfix") is True, "runtime V887 flag is false")

        no_secret = client.get("/api/automation/telegram/tick")
        require(no_secret.status_code == 403, f"telegram tick without secret returned {no_secret.status_code}")

        response = client.get("/api/automation/telegram/tick?secret=v887-local-secret&runner=render_cron&dry_run=1")
        body = response.get_data(as_text=True) or ""
        require(response.status_code == 200, f"telegram tick with local secret returned {response.status_code}: {body[:200]}")
        require("QUEUE_SKIPPED" not in body or "not defined" not in body, "QUEUE_SKIPPED NameError leaked in response")
        require("NameError" not in body and "not defined" not in body, "NameError leaked in telegram tick response")
        payload = response.get_json() or {}
        require(payload.get("sent_count", payload.get("sent", 0)) in {0, "0", None}, "local dry cron reported a real send")
        require(payload.get("cron_runner_detected") is True, "render_cron runner was not detected")
    finally:
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        for suffix in ("", "-wal", "-shm"):
            try:
                Path(f"{db_path}{suffix}").unlink(missing_ok=True)
            except OSError:
                pass


def main() -> None:
    check_static_contract()
    check_runtime_cron_endpoint()
    print("V887 Telegram QUEUE_SKIPPED runtime hotfix OK")


if __name__ == "__main__":
    main()
