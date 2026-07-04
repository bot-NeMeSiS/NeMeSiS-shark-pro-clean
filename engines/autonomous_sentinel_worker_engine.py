"""V893 Autonomous Sentinel Worker.

Autonomous, safe QA worker for NeMeSiS SHARK PRO. It performs local route
journeys, reference QA, Visual Worker/AutoPilot aggregation, issue creation and
Codex outbox generation. It never deploys, pushes, sends Telegram, mutates
payments/users, touches secrets, calls paid APIs or invents sports data.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from engines.sentinel_autofix_planner_engine import build_autofix_plan
from engines.sentinel_issues_engine import (
    build_sentinel_issues_summary,
    load_sentinel_issues_memory,
    run_sentinel_issues_scan,
)
from engines.sentinel_reference_qa_engine import build_reference_gap_report
from engines.sentinel_user_journey_engine import run_user_journey_checks


MADRID_TZ = ZoneInfo("Europe/Madrid")
AUTONOMOUS_SENTINEL_VERSION = "V893_AUTONOMOUS_SENTINEL_USER_ADMIN_REFERENCE_QA_WORKER_FINAL"

VALID_MODES = {
    "safe_scan",
    "full_scan",
    "visual_scan",
    "functional_scan",
    "telegram_scan",
    "autofix_plan",
}


def _now() -> str:
    return datetime.now(MADRID_TZ).replace(microsecond=0).isoformat()


def autonomous_root(root: str | Path) -> Path:
    return Path(root) / "data" / "runtime" / "autonomous_sentinel"


def ensure_autonomous_dirs(root: str | Path) -> dict[str, Path]:
    base = autonomous_root(root)
    dirs = {
        "base": base,
        "screenshots": base / "screenshots",
        "issues": base / "issues",
        "outbox": base / "outbox",
        "history": base / "history",
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


def _write_outbox(root: str | Path, issues: list[dict[str, Any]]) -> dict[str, Any]:
    dirs = ensure_autonomous_dirs(root)
    outbox = dirs["outbox"]
    prompts = []
    files = []
    for issue in issues:
        prompt = str(issue.get("codex_prompt") or "").strip()
        if not prompt:
            continue
        issue_id = str(issue.get("id") or "SENT-ISSUE").replace("/", "-")
        filename = f"{issue_id}_codex_prompt.md"
        path = outbox / filename
        path.write_text(prompt, encoding="utf-8")
        prompts.append(f"# {issue_id}\n\n{prompt}")
        files.append(str(path))
    combined = "\n\n---\n\n".join(prompts) if prompts else "Sin prompts Codex pendientes en esta ejecucion."
    combined_path = outbox / "codex_prompts.md"
    combined_path.write_text(combined, encoding="utf-8")
    return {"prompt_count": len(prompts), "files": files, "combined_path": str(combined_path)}


def build_autonomous_status(app_version: str, root: str | Path) -> dict[str, Any]:
    dirs = ensure_autonomous_dirs(root)
    latest = _read_json(dirs["base"] / "latest_run.json", {})
    state = _read_json(dirs["base"] / "state.json", {})
    issues_memory = load_sentinel_issues_memory(root)
    issues_summary = build_sentinel_issues_summary(app_version, issues_memory)
    return {
        "version": app_version,
        "engine_version": AUTONOMOUS_SENTINEL_VERSION,
        "generated_at_madrid": _now(),
        "state": state,
        "latest_run": latest,
        "issues_summary": issues_summary,
        "paths": {name: str(path) for name, path in dirs.items()},
        "cron": {
            "endpoint": "/api/automation/autonomous-sentinel/run",
            "safe_scan": "*/15 * * * *",
            "functional_scan": "0 * * * *",
            "visual_scan": "0 6 * * *",
        },
    }


def run_autonomous_sentinel_worker(
    flask_client: Any,
    app_version: str,
    root: str | Path,
    *,
    mode: str = "safe_scan",
    runner: str = "local",
    dry_run: bool = True,
    runtime: dict[str, Any] | None = None,
    visual_result: dict[str, Any] | None = None,
    autopilot_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = mode if mode in VALID_MODES else "safe_scan"
    dirs = ensure_autonomous_dirs(root)
    journey = run_user_journey_checks(flask_client, mode=mode)
    reference = build_reference_gap_report(root, visual_result=visual_result, browser_available=False)
    sentinel_summary = run_sentinel_issues_scan(
        app_version,
        root,
        sentinel_result={"issues": journey.get("issues") or []},
        autopilot_result=autopilot_result,
        visual_result=visual_result,
        runtime=runtime or {},
        save_memory=True,
    )
    issues = sentinel_summary.get("open_issues") or sentinel_summary.get("issues") or []
    reference_issues = reference.get("issues") or []
    if reference_issues:
        sentinel_summary = run_sentinel_issues_scan(
            app_version,
            root,
            sentinel_result={"issues": reference_issues},
            runtime=runtime or {},
            save_memory=True,
        )
        issues = sentinel_summary.get("open_issues") or sentinel_summary.get("issues") or []
    autofix = build_autofix_plan(issues)
    outbox = _write_outbox(root, issues)
    run = {
        "ok": True,
        "version": app_version,
        "engine_version": AUTONOMOUS_SENTINEL_VERSION,
        "run_id": "ASW-" + datetime.now(MADRID_TZ).strftime("%Y%m%d%H%M%S"),
        "generated_at_madrid": _now(),
        "mode": mode,
        "runner": runner,
        "dry_run": bool(dry_run),
        "dangerous_actions_executed": False,
        "routes_checked": journey.get("routes_checked"),
        "roles_reviewed": journey.get("roles"),
        "devices_reviewed": journey.get("devices"),
        "journey": journey,
        "reference": reference,
        "issues_summary": sentinel_summary,
        "autofix_plan": autofix,
        "outbox": outbox,
        "screenshots": {
            "available": False,
            "reason": "Playwright/browser capture no ejecutado en este entorno.",
            "path": str(dirs["screenshots"]),
        },
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
        "engine_version": AUTONOMOUS_SENTINEL_VERSION,
        "last_run_id": run["run_id"],
        "last_run_madrid": run["generated_at_madrid"],
        "last_mode": mode,
        "last_runner": runner,
        "last_issue_count": sentinel_summary.get("counts", {}).get("open", 0),
        "next_recommended_mode": "functional_scan" if mode == "safe_scan" else "safe_scan",
    }
    _write_json(dirs["base"] / "latest_run.json", run)
    _write_json(dirs["base"] / "state.json", state)
    _write_json(dirs["base"] / "issues.json", {"issues": issues, "summary": sentinel_summary})
    _write_json(dirs["base"] / "autofix_plan.json", autofix)
    _write_json(dirs["base"] / "reference_gap_report.json", reference)
    _write_json(dirs["history"] / f"{run['run_id']}.json", run)
    return run
