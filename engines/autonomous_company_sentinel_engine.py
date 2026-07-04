"""V892 Autonomous Company Sentinel.

Company-wide QA worker for product, client, admin, Telegram, picks, real data,
reference UI, Render alignment and Codex outbox. It is diagnostic by default:
no deploy, no push, no real Telegram, no payment mutation, no secrets and no
fake sports data.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from engines.sentinel_codex_outbox_engine import write_codex_outbox
from engines.sentinel_issues_engine import build_sentinel_issues_summary, load_sentinel_issues_memory, run_sentinel_issues_scan
from engines.sentinel_reference_visual_engine import run_reference_visual_scan
from engines.sentinel_render_alignment_engine import build_render_alignment
from engines.sentinel_safe_autofix_engine import build_safe_autofix_plan
from engines.sentinel_telegram_quality_watch_engine import build_telegram_quality_watch
from engines.sentinel_user_admin_journey_engine import run_user_admin_journey_scan


MADRID_TZ = ZoneInfo("Europe/Madrid")
AUTONOMOUS_COMPANY_SENTINEL_VERSION = "V892_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL"

VALID_MODES = {
    "safe_scan",
    "full_scan",
    "visual_scan",
    "functional_scan",
    "telegram_scan",
    "reference_scan",
    "autofix_plan",
    "post_deploy_scan",
}


def _now() -> str:
    return datetime.now(MADRID_TZ).replace(microsecond=0).isoformat()


def company_sentinel_root(root: str | Path) -> Path:
    return Path(root) / "data" / "runtime" / "autonomous_company_sentinel"


def ensure_company_sentinel_dirs(root: str | Path) -> dict[str, Path]:
    base = company_sentinel_root(root)
    dirs = {
        "base": base,
        "issues": base / "issues",
        "outbox": base / "outbox",
        "history": base / "history",
        "screenshots": base / "screenshots",
        "reference": base / "reference",
        "autofix": base / "autofix",
        "reports": base / "reports",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else dict(default)
    except Exception:
        pass
    return dict(default)


def build_company_sentinel_status(app_version: str, root: str | Path) -> dict[str, Any]:
    dirs = ensure_company_sentinel_dirs(root)
    latest = _read_json(dirs["base"] / "latest_run.json", {})
    state = _read_json(dirs["base"] / "state.json", {})
    issues_summary = build_sentinel_issues_summary(app_version, load_sentinel_issues_memory(root))
    return {
        "version": app_version,
        "engine_version": AUTONOMOUS_COMPANY_SENTINEL_VERSION,
        "generated_at_madrid": _now(),
        "state": state,
        "latest_run": latest,
        "issues_summary": issues_summary,
        "paths": {name: str(path) for name, path in dirs.items()},
        "cron": {
            "endpoint": "/api/automation/autonomous-company-sentinel/run",
            "safe_scan": "*/15 * * * *",
            "functional_scan": "0 * * * *",
            "full_scan": "0 8 * * *",
        },
        "safety": {
            "no_auto_deploy": True,
            "no_auto_push": True,
            "no_real_telegram": True,
            "no_real_payments": True,
            "no_secrets": True,
            "no_fake_data": True,
        },
    }


def _merge_issue_sources(*sources: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        issues.extend(source.get("issues") or [])
    return [issue for issue in issues if isinstance(issue, dict)]


def run_autonomous_company_sentinel(
    flask_client: Any,
    app_version: str,
    root: str | Path,
    *,
    mode: str = "safe_scan",
    runner: str = "local",
    dry_run: bool = True,
    runtime: dict[str, Any] | None = None,
    render_runtime: dict[str, Any] | None = None,
    visual_result: dict[str, Any] | None = None,
    autopilot_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = mode if mode in VALID_MODES else "safe_scan"
    dirs = ensure_company_sentinel_dirs(root)
    local_runtime = runtime or {"app_version": app_version}
    journey = run_user_admin_journey_scan(flask_client, mode=mode)
    reference = run_reference_visual_scan(root, visual_result=visual_result, browser_available=False)
    render_alignment = build_render_alignment(local_runtime, render_runtime=render_runtime)
    telegram_watch = build_telegram_quality_watch(local_runtime)
    issue_sources = _merge_issue_sources(journey, reference, render_alignment, telegram_watch)
    if autopilot_result:
        issue_sources.extend(autopilot_result.get("issues") or [])
    if visual_result:
        issue_sources.extend(visual_result.get("issues") or [])
    issues_summary = run_sentinel_issues_scan(
        app_version,
        root,
        sentinel_result={"issues": issue_sources},
        autopilot_result=autopilot_result,
        visual_result=visual_result,
        runtime=local_runtime,
        save_memory=True,
    )
    open_issues = issues_summary.get("open_issues") or issues_summary.get("issues") or []
    outbox = write_codex_outbox(root, open_issues)
    autofix = build_safe_autofix_plan(open_issues)
    run = {
        "ok": True,
        "version": app_version,
        "engine_version": AUTONOMOUS_COMPANY_SENTINEL_VERSION,
        "run_id": "ACS-" + datetime.now(MADRID_TZ).strftime("%Y%m%d%H%M%S"),
        "last_run_madrid": _now(),
        "mode": mode,
        "runner": runner,
        "dry_run": bool(dry_run),
        "dangerous_actions_executed": False,
        "roles_reviewed": journey.get("roles") or ["anonymous", "FREE", "PRO", "ELITE", "ADMIN"],
        "devices_reviewed": journey.get("devices") or ["desktop_1440x900", "mobile_390x844"],
        "routes_checked": journey.get("routes_checked") or 0,
        "journey": journey,
        "reference": reference,
        "render_alignment": render_alignment,
        "telegram_quality_watch": telegram_watch,
        "issues_summary": issues_summary,
        "outbox": outbox,
        "autofix_plan": autofix,
        "screenshots": {
            "available": False,
            "reason": "Browser/capturas no ejecutados en este entorno.",
            "path": str(dirs["screenshots"]),
        },
        "warnings": [
            "No se declara pixel-perfect sin capturas reales.",
            "No se declara produccion alineada sin runtime Render real.",
        ],
        "safe_notes": [
            "No auto deploy.",
            "No auto push.",
            "No Telegram real.",
            "No pagos reales.",
            "No secretos.",
            "No datos inventados.",
        ],
    }
    state = {
        "version": app_version,
        "engine_version": AUTONOMOUS_COMPANY_SENTINEL_VERSION,
        "last_run_id": run["run_id"],
        "last_run_madrid": run["last_run_madrid"],
        "last_mode": mode,
        "last_runner": runner,
        "issues_open": (issues_summary.get("counts") or {}).get("open", 0),
        "critical": (issues_summary.get("counts") or {}).get("critical", 0),
        "high": (issues_summary.get("counts") or {}).get("high", 0),
    }
    _write_json(dirs["base"] / "latest_run.json", run)
    _write_json(dirs["base"] / "state.json", state)
    _write_json(dirs["base"] / "issues.json", {"issues": open_issues, "summary": issues_summary})
    _write_json(dirs["base"] / "autofix_plan.json", autofix)
    _write_json(dirs["base"] / "reference_gap_report.json", reference)
    _write_json(dirs["base"] / "render_alignment.json", render_alignment)
    _write_json(dirs["base"] / "telegram_quality_watch.json", telegram_watch)
    _write_json(dirs["history"] / f"{run['run_id']}.json", run)
    return run
