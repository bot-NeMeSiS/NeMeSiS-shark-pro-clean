from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V889_TELEGRAM_PREMIUM_PICKS_INTELLIGENCE_DELIVERY_FINAL"
CURRENT_COMPATIBLE_PREFIXES = ("V889_", "V890_")
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
    formatter = read("engines/telegram_message_formatter.py")
    quality = read("engines/telegram_pick_quality_engine.py")

    require(version_txt.startswith(CURRENT_COMPATIBLE_PREFIXES), "VERSION.txt is not compatible with V889/V890 lineage", failures)
    require(app_version_file == version_txt, "APP_VERSION does not match VERSION.txt", failures)
    require(f"APP_VERSION = '{version_txt}'" in app_py, "app.py APP_VERSION mismatch", failures)
    require("has_v889_telegram_premium_picks_intelligence" in app_py, "runtime V889 flag missing", failures)
    require("has_v887_telegram_queue_skipped_hotfix" in app_py, "V887 flag not preserved", failures)
    require("has_v888_sentinel_autopilot_self_improvement" in app_py, "V888 flag not preserved", failures)

    for token in [
        "PREMIUM_SEND",
        "REVIEW_REQUIRED",
        "SKIP_LOW_QUALITY",
        "SKIP_MISSING_ODDS",
        "SKIP_MISSING_SELECTION",
        "SKIP_DUPLICATE",
        "SKIP_UNSUPPORTED_LEAGUE",
        "SKIP_TOO_LATE",
        "SKIP_TOO_EARLY",
        "SKIP_NO_REAL_DATA",
        "filter_premium_telegram_picks",
        "build_telegram_pick_dedupe_key",
        "build_membership_message_variant",
        "build_combi_quality",
        "build_pick_result_payload",
    ]:
        require(token in quality, f"quality engine token missing: {token}", failures)

    for token in [
        "format_premium_pick_message",
        "format_membership_pick_message",
        "format_premium_combi_message",
        "format_pick_result_tracking_message",
    ]:
        require(token in formatter, f"premium formatter missing: {token}", failures)

    for route in [
        "/api/admin/telegram/pick-candidates",
        "/api/admin/telegram/pick-preview",
        "/api/admin/telegram/pick-dry-run",
        "/api/admin/telegram/pick-quality-summary",
    ]:
        require(route in app_py, f"admin preview API missing: {route}", failures)

    combined = "\n".join([app_py, formatter, quality])
    require("QUEUE_SKIPPED" in app_py, "QUEUE_SKIPPED preservation missing", failures)
    require("telegram_premium_pick_rules_v889" in read("engines/continuous_shark_sentinel_engine.py"), "Sentinel V889 rules missing", failures)
    require("telegram_premium_picks" in read("engines/sentinel_autopilot_engine.py"), "AutoPilot V889 integration missing", failures)
    require(not re.search(r"(TELEGRAM_BOT_TOKEN\s*=|AUTOMATION_SECRET\s*=|API_KEY\s*=|sk_live_|bot[0-9]+:)", combined), "possible secret assignment found", failures)
    require("apuesta segura" not in combined.lower(), "unsafe betting claim found", failures)

    from engines.telegram_pick_quality_engine import (
        PREMIUM_SEND,
        SKIP_MISSING_ODDS,
        SKIP_MISSING_SELECTION,
        classify_telegram_pick,
    )

    base_pick = {
        "id": "P-V889",
        "match_id": "M-V889",
        "home_team": "Real Madrid",
        "away_team": "Sevilla",
        "competition_name": "LaLiga",
        "market": "Ganador",
        "selection": "Real Madrid",
        "odds": 1.82,
        "stake_units": 2,
        "risk_level": "Medio",
        "confidence": 78,
        "reason": "Ventaja detectada por datos reales guardados.",
        "counterargument": "La cuota puede caer antes del partido.",
        "kickoff_iso": "2026-07-04T21:00:00+02:00",
    }
    from datetime import datetime
    from zoneinfo import ZoneInfo

    fixed_now = datetime(2026, 7, 4, 12, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    require(classify_telegram_pick(base_pick, now=fixed_now)["status"] == PREMIUM_SEND, "complete pick is not premium send", failures)
    missing_odds = dict(base_pick)
    missing_odds["odds"] = ""
    require(classify_telegram_pick(missing_odds, now=fixed_now)["status"] == SKIP_MISSING_ODDS, "missing odds not blocked", failures)
    missing_selection = dict(base_pick)
    missing_selection["selection"] = ""
    require(classify_telegram_pick(missing_selection, now=fixed_now)["status"] == SKIP_MISSING_SELECTION, "missing selection not blocked", failures)

    os.environ["DB_PATH"] = ":memory:"
    os.environ["AUTOMATION_SECRET"] = "v889-secret"
    os.environ["DISABLE_TELEGRAM_REAL_SEND"] = "1"
    import app  # noqa: WPS433

    client = app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, "runtime-version not 200", failures)
    runtime_json = runtime.get_json() or {}
    require(runtime_json.get("app_version") == version_txt, "runtime app_version mismatch", failures)
    require(runtime_json.get("has_v889_telegram_premium_picks_intelligence") is True, "runtime V889 flag false", failures)
    require(runtime_json.get("has_v887_telegram_queue_skipped_hotfix") is True, "runtime V887 flag false", failures)
    require(runtime_json.get("has_v888_sentinel_autopilot_self_improvement") is True, "runtime V888 flag false", failures)

    for route in [
        "/api/admin/telegram/pick-candidates",
        "/api/admin/telegram/pick-preview",
        "/api/admin/telegram/pick-quality-summary",
    ]:
        require(client.get(route).status_code == 403, f"admin API without session not 403: {route}", failures)
    require(client.post("/api/admin/telegram/pick-dry-run", json={"membership": "PRO"}).status_code == 403, "pick dry-run without session not 403", failures)
    require(client.get("/api/automation/telegram/tick").status_code == 403, "Telegram cron without secret not 403", failures)
    cron = client.get("/api/automation/telegram/tick?secret=v889-secret&runner=local_check&dry_run=1")
    require(cron.status_code == 200, "Telegram cron with secret dry_run not 200", failures)
    cron_json = cron.get_json() or {}
    require(not cron_json.get("real_telegram_sent", False), "dry-run claims real Telegram send", failures)

    for report in [
        "reports/V889_TELEGRAM_PREMIUM_PICKS_INTELLIGENCE_DELIVERY_REPORT.md",
        "reports/V889_TELEGRAM_PREMIUM_PICKS_PREFLIGHT.md",
        "reports/V889_TELEGRAM_CURRENT_SYSTEM_AUDIT.md",
        "reports/V889_TELEGRAM_PICK_QUALITY_ENGINE_QA.md",
        "reports/V889_TELEGRAM_PREMIUM_MESSAGE_FORMAT_QA.md",
        "reports/V889_TELEGRAM_MEMBERSHIP_DELIVERY_QA.md",
        "reports/V889_TELEGRAM_NO_FILLER_POLICY_QA.md",
        "reports/V889_TELEGRAM_COMBI_PICKS_QA.md",
        "reports/V889_TELEGRAM_PICK_RESULTS_TRACKING_QA.md",
        "reports/V889_TELEGRAM_DEDUPE_LIMITS_QA.md",
        "reports/V889_TELEGRAM_VISUAL_CARDS_PICK_QA.md",
        "reports/V889_TELEGRAM_ADMIN_COMMAND_CENTER_QA.md",
        "reports/V889_TELEGRAM_AUTOPILOT_INTEGRATION_QA.md",
        "reports/V889_TELEGRAM_PICK_PREVIEW_API_QA.md",
        "reports/V889_TELEGRAM_SECURITY_QA.md",
        "reports/V889_NEXT_STEPS.md",
    ]:
        require((ROOT / report).exists(), f"report missing: {report}", failures)

    if failures:
        print("V889 Telegram premium picks check FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V889 Telegram premium picks check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
