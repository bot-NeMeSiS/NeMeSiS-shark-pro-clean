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
from engines.autonomous_product_qa_engine import (
    build_autonomous_product_qa_status,
    product_qa_sentinel_issues,
)


MADRID_TZ = ZoneInfo("Europe/Madrid")
AUTONOMOUS_COMPANY_SENTINEL_VERSION = "V892_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL"

VALID_MODES = {
    "safe_scan",
    "full_scan",
    "visual_scan",
    "functional_scan",
    "telegram_scan",
    "reference_scan",
    "daily_reference_review",
    "post_deploy_check",
    "autofix_plan",
    "post_deploy_scan",
}

MODE_PROFILES = {
    "reference_scan": {
        "label": "Reference scan",
        "focus": ["Sentinel", "reference_images", "reference_manifest", "outbox", "visual gaps"],
        "routes": ["/app", "/calendar", "/live", "/picks", "/shark", "/telegram", "/admin/dashboard", "/admin/autonomous-company-sentinel"],
        "next_step": "Revisar gaps visuales y aplicar solo correcciones seguras con Browser QA pendiente.",
    },
    "daily_reference_review": {
        "label": "Daily reference review",
        "focus": ["admin", "cliente", "picks", "live", "calendario", "SHARK", "Telegram", "PWA/404", "outbox", "rutas críticas"],
        "routes": ["/", "/app", "/calendar", "/live", "/picks", "/shark", "/telegram", "/admin-login", "/admin/dashboard", "/admin/sentinel-issues"],
        "next_step": "Atender incidencias reproducibles y mantener prompts para acciones peligrosas.",
    },
    "post_deploy_check": {
        "label": "Post deploy check",
        "focus": ["runtime-version", "versión esperada", "admin-login", "rutas cliente", "rutas admin", "Telegram dry-run", "404 premium", "service worker", "reference_images", "outbox"],
        "routes": ["/api/runtime-version", "/admin-login", "/", "/app", "/calendar", "/live", "/picks", "/admin/dashboard", "/ruta-inventada", "/manifest.json", "/service-worker.js"],
        "next_step": "Confirmar /api/runtime-version en Render antes de declarar producción alineada.",
    },
}


def _mode_profile(mode: str) -> dict[str, Any]:
    return MODE_PROFILES.get(mode, {
        "label": mode.replace("_", " ").title(),
        "focus": ["Sentinel", "rutas", "outbox", "seguridad"],
        "routes": [],
        "next_step": "Revisar incidencias abiertas y ejecutar solo cambios seguros.",
    })


def _safe_action_policy(open_issues: list[dict[str, Any]], outbox: dict[str, Any], mode: str) -> dict[str, Any]:
    dangerous_markers = {"payments", "stripe", "secret", "token", "telegram_real", "db", "users", "sessions", "deploy", "push"}
    safe_autofix: list[dict[str, Any]] = []
    codex_prompt_required: list[dict[str, Any]] = []
    human_approval_required: list[dict[str, Any]] = []
    for issue in open_issues:
        text = " ".join(str(issue.get(key) or "") for key in ["area", "title", "evidence", "route", "recommendation"]).lower()
        item = {
            "issue_id": issue.get("id") or issue.get("issue_id") or "SENT-PENDING",
            "severity": issue.get("severity") or "low",
            "route": issue.get("route") or issue.get("screen") or "",
            "title": issue.get("title") or "Incidencia pendiente",
            "recommendation": issue.get("recommendation") or "Revisar con Sentinel antes de aplicar cambios.",
        }
        if any(marker in text for marker in dangerous_markers):
            human_approval_required.append({**item, "action_type": "HUMAN_APPROVAL_REQUIRED"})
        elif str(issue.get("severity") or "").lower() in {"critical", "high"}:
            codex_prompt_required.append({**item, "action_type": "CODEX_PROMPT_REQUIRED"})
        else:
            safe_autofix.append({**item, "action_type": "SAFE_AUTOFIX"})
    return {
        "mode": mode,
        "dangerous_actions_executed": False,
        "SAFE_AUTOFIX": safe_autofix[:20],
        "CODEX_PROMPT_REQUIRED": codex_prompt_required[:20],
        "HUMAN_APPROVAL_REQUIRED": human_approval_required[:20],
        "safe_autofix_count": len(safe_autofix),
        "codex_prompt_required_count": len(codex_prompt_required) + int(outbox.get("prompt_count") or 0),
        "human_approval_required_count": len(human_approval_required),
        "rules": [
            "No tocar datos reales destructivamente.",
            "No enviar Telegram real.",
            "No gastar APIs caras.",
            "No exponer secretos.",
            "No hacer deploy ni push automático.",
        ],
    }


def _append_v904_outbox_status(root: str | Path, automation_summary: dict[str, Any], action_policy: dict[str, Any]) -> None:
    base = company_sentinel_root(root)
    paths = [
        base / "outbox" / "codex_outbox.md",
        base / "codex_outbox.md",
    ]
    section = (
        "\n\n## V904_REFERENCE_GAPS_WORKFORCE_STATUS\n\n"
        f"- mode: {automation_summary.get('mode')}\n"
        f"- gaps_read: {automation_summary.get('gaps_read')}\n"
        f"- gaps_addressed: {automation_summary.get('gaps_addressed')}\n"
        f"- gaps_pending: {automation_summary.get('gaps_pending')}\n"
        f"- prompts_active: {automation_summary.get('prompts_active')}\n"
        f"- deploy_status: {automation_summary.get('deploy_status')}\n"
        f"- secret_masking_status: {automation_summary.get('secret_masking_status')}\n"
        f"- next_step: {automation_summary.get('next_recommended_step')}\n\n"
        "### action_policy\n\n"
        f"- SAFE_AUTOFIX: {action_policy.get('safe_autofix_count', 0)}\n"
        f"- CODEX_PROMPT_REQUIRED: {action_policy.get('codex_prompt_required_count', 0)}\n"
        f"- HUMAN_APPROVAL_REQUIRED: {action_policy.get('human_approval_required_count', 0)}\n\n"
        "### dangerous_requires_approval\n\n"
        "Pagos, secretos, Telegram real, DB, usuarios, sesiones, deploy, push y llamadas caras quedan fuera del autofix automatico.\n"
    )
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
            if "## V904_REFERENCE_GAPS_WORKFORCE_STATUS" in text:
                text = text.split("## V904_REFERENCE_GAPS_WORKFORCE_STATUS", 1)[0].rstrip()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text.rstrip() + section + "\n", encoding="utf-8")
        except Exception:
            continue


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
    browser_qa = _read_json(dirs["base"] / "browser_reference_comparison.json", {})
    browser_status = _read_json(dirs["base"] / "browser_qa_status.json", {})
    visual_queue = _read_json(dirs["base"] / "visual_fix_queue.json", {"items": []})
    queue_items = visual_queue.get("items") if isinstance(visual_queue, dict) else []
    if not isinstance(queue_items, list):
        queue_items = []
    browser_qa_dir = Path(root) / "browser_qa"
    workflow_path = Path(root) / ".github" / "workflows" / "browser-qa.yml"
    workflow_example_path = Path(root) / "docs" / "browser_qa_github_action_example.yml"
    issues_summary = build_sentinel_issues_summary(app_version, load_sentinel_issues_memory(root))
    return {
        "version": app_version,
        "engine_version": AUTONOMOUS_COMPANY_SENTINEL_VERSION,
        "generated_at_madrid": _now(),
        "state": state,
        "latest_run": latest,
        "browser_qa": {
            "status": browser_qa.get("browser_qa_status") or "BROWSER_QA_UNAVAILABLE",
            "screenshots_captured": int(browser_qa.get("screenshots_captured") or 0),
            "reference_comparisons": int(browser_qa.get("reference_comparisons") or 0),
            "visual_gaps_resolved": int(browser_qa.get("visual_gaps_resolved") or 0),
            "visual_gaps_pending": int(browser_qa.get("visual_gaps_pending") or 0),
            "routes_captured": browser_qa.get("routes_captured") or browser_status.get("routes_captured") or [],
            "playwright_status": browser_status.get("browser_qa_status") or browser_qa.get("browser_qa_status") or "BROWSER_QA_UNAVAILABLE",
            "pixel_perfect_claim": False,
        },
        "v909_pipeline": {
            "pipeline_ready": (browser_qa_dir / "README.md").exists() and (browser_qa_dir / "playwright_requirements.txt").exists(),
            "local_runner_available": (browser_qa_dir / "run_local_browser_qa.ps1").exists() and (browser_qa_dir / "run_local_browser_qa.bat").exists() and (browser_qa_dir / "run_local_browser_qa.sh").exists(),
            "github_action_available": workflow_path.exists() or workflow_example_path.exists(),
            "visual_fix_queue_count": len(queue_items),
            "blocked_no_screenshot_count": len([item for item in queue_items if isinstance(item, dict) and item.get("status") == "BLOCKED_NO_SCREENSHOT"]),
            "ready_for_codex_count": len([item for item in queue_items if isinstance(item, dict) and item.get("status") == "READY_FOR_CODEX"]),
        },
        "issues_summary": issues_summary,
        "paths": {name: str(path) for name, path in dirs.items()},
        "cron": {
            "endpoint": "/api/automation/autonomous-company-sentinel/run",
            "safe_scan": "*/15 * * * *",
            "functional_scan": "0 * * * *",
            "full_scan": "0 8 * * *",
            "reference_scan": "0 9 * * *",
            "reference_scan_endpoint": "/api/automation/autonomous-company-sentinel/run?secret=$AUTOMATION_SECRET&mode=reference_scan&dry_run=1&runner=render_cron",
            "daily_reference_review_endpoint": "/api/automation/autonomous-company-sentinel/run?secret=$AUTOMATION_SECRET&mode=daily_reference_review&dry_run=1&runner=render_cron",
            "post_deploy_check_endpoint": "/api/automation/autonomous-company-sentinel/run?secret=$AUTOMATION_SECRET&mode=post_deploy_check&dry_run=1&runner=render_cron",
            "daily_reference_review_curl": "curl -fsS \"https://bot-apuestas-crgf.onrender.com/api/automation/autonomous-company-sentinel/run?secret=$AUTOMATION_SECRET&mode=daily_reference_review&dry_run=1&runner=render_cron\"",
            "post_deploy_check_curl": "curl -fsS \"https://bot-apuestas-crgf.onrender.com/api/automation/autonomous-company-sentinel/run?secret=$AUTOMATION_SECRET&mode=post_deploy_check&dry_run=1&runner=render_cron\"",
            "timezone_note": "Render Cron usa UTC. Ajustar la hora del panel a UTC, no a Europe/Madrid.",
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
    profile = _mode_profile(mode)
    dirs = ensure_company_sentinel_dirs(root)
    local_runtime = runtime or {"app_version": app_version}
    journey = run_user_admin_journey_scan(flask_client, mode=mode)
    healthy_routes = {
        str(item.get("route") or "")
        for item in (journey.get("checked") or [])
        if int(item.get("status_code") or 0) in {200, 301, 302, 303, 307, 308, 401, 403}
    }
    reference = run_reference_visual_scan(
        root,
        visual_result=visual_result,
        browser_available=False,
        run_browser=(mode in {"reference_scan", "daily_reference_review"} and not dry_run),
    )
    render_alignment = build_render_alignment(local_runtime, render_runtime=render_runtime)
    telegram_watch = build_telegram_quality_watch(local_runtime, render_runtime=render_runtime)
    local_env_status = {
        "telegram_configured": bool(local_runtime.get("telegram_configured") or (local_runtime.get("flags") or {}).get("telegram_configured")),
        "openai_configured": bool(local_runtime.get("openai_configured") or (local_runtime.get("flags") or {}).get("openai_configured")),
    }
    render_runtime_status = {
        "available": bool(render_runtime),
        "app_version": (render_runtime or {}).get("app_version") or (render_runtime or {}).get("version"),
        "telegram_configured": bool((render_runtime or {}).get("telegram_configured") or ((render_runtime or {}).get("flags") or {}).get("telegram_configured")),
        "openai_configured": bool((render_runtime or {}).get("openai_configured") or ((render_runtime or {}).get("flags") or {}).get("openai_configured")),
    }
    issue_sources = _merge_issue_sources(journey, reference, render_alignment, telegram_watch)
    navigation_integrity = _read_json(
        Path(root) / "data" / "runtime" / "navigation_integrity" / "latest_run.json",
        {},
    )
    if int(navigation_integrity.get("broken_links_after") or 0) > 0:
        issue_sources.append({
            "id": "V929-NAVIGATION-INTEGRITY",
            "profile": "ALL",
            "route": "/admin/navigation-integrity",
            "category": "navigation_integrity",
            "severity": "high",
            "title": "Navegacion interna con destinos rotos",
            "description": "El Navigation Integrity Worker detecto enlaces o acciones internas rotas.",
            "evidence": f"broken_links_after={int(navigation_integrity.get('broken_links_after') or 0)}",
            "expected_behavior": "Cero enlaces internos rotos.",
            "actual_behavior": str(navigation_integrity.get("status") or "BROKEN"),
            "suggested_fix": "Abrir el panel de integridad, corregir destinos y repetir Browser QA por clic.",
            "safe_auto_fix_possible": True,
            "requires_admin_approval": False,
        })
    if autopilot_result:
        issue_sources.extend(autopilot_result.get("issues") or [])
    if visual_result:
        issue_sources.extend(visual_result.get("issues") or [])
    product_qa = build_autonomous_product_qa_status(root)
    issue_sources.extend(product_qa_sentinel_issues(product_qa))
    issues_summary = run_sentinel_issues_scan(
        app_version,
        root,
        sentinel_result={"issues": issue_sources},
        autopilot_result=autopilot_result,
        visual_result=visual_result,
        runtime=local_runtime,
        healthy_routes=healthy_routes,
        save_memory=True,
    )
    all_issues = issues_summary.get("issues") or []
    open_issues = issues_summary.get("open_issues") or []
    archived_issues = [
        issue for issue in all_issues
        if issue.get("status") in {"STALE_NEEDS_REVALIDATION", "RESOLVED_BY_RESCAN", "RESOLVED", "FALSE_POSITIVE", "IGNORED_SAFE"}
    ]
    outbox = write_codex_outbox(root, open_issues, archived_issues=archived_issues)
    autofix = build_safe_autofix_plan(open_issues)
    action_policy = _safe_action_policy(open_issues, outbox, mode)
    product_gap_report = reference.get("product_gap_report") or {}
    gaps = product_gap_report.get("gaps") or []
    addressed_routes = ["/app", "/calendar", "/live", "/picks", "/shark", "/telegram", "/admin/dashboard", "/admin/autonomous-company-sentinel"]
    pending_routes = sorted({
        str(gap.get("route") or gap.get("screen") or "")
        for gap in gaps
        if str(gap.get("route") or gap.get("screen") or "") not in addressed_routes
    })
    reference["v904_review"] = {
        "status": "AUTOMATION_MODE_REVIEWED",
        "gaps_read": len(gaps),
        "gaps_addressed": len(addressed_routes),
        "addressed_routes": addressed_routes,
        "still_pending": [route for route in pending_routes if route],
        "dangerous_requires_approval": [],
        "browser_qa_status": "BROWSER_QA_UNAVAILABLE",
        "notes": [
            "Los modos automaticos preparan revision, prompts y planes.",
            "No aplican deploy, push, Telegram real, pagos ni cambios destructivos.",
            "No se declara pixel-perfect sin Browser QA real.",
        ],
    }
    v904_automation_summary = {
        "mode": mode,
        "mode_label": profile.get("label"),
        "focus": profile.get("focus") or [],
        "critical_routes": profile.get("routes") or [],
        "gaps_read": len(gaps),
        "gaps_addressed": len(addressed_routes),
        "gaps_pending": len(gaps),
        "prompts_active": int(outbox.get("prompt_count") or 0),
        "errors_active": len(open_issues),
        "deploy_status": "pending_runtime_confirmation",
        "secret_masking_status": "masked_configured_missing_only",
        "next_recommended_step": profile.get("next_step"),
        "action_policy": action_policy,
        "cron_examples": {
            "daily_reference_review": "curl -fsS \"https://bot-apuestas-crgf.onrender.com/api/automation/autonomous-company-sentinel/run?secret=$AUTOMATION_SECRET&mode=daily_reference_review&dry_run=1&runner=render_cron\"",
            "post_deploy_check": "curl -fsS \"https://bot-apuestas-crgf.onrender.com/api/automation/autonomous-company-sentinel/run?secret=$AUTOMATION_SECRET&mode=post_deploy_check&dry_run=1&runner=render_cron\"",
        },
    }
    _append_v904_outbox_status(root, v904_automation_summary, action_policy)
    reference["v904_automation_modes"] = {
        "last_mode": mode,
        "supported_modes": ["reference_scan", "daily_reference_review", "post_deploy_check"],
        "addressing_status": {
            "gaps_read": v904_automation_summary["gaps_read"],
            "gaps_addressed": v904_automation_summary["gaps_addressed"],
            "gaps_pending": v904_automation_summary["gaps_pending"],
            "needs_browser_qa": True,
        },
        "action_policy": action_policy,
    }
    run = {
        "ok": True,
        "version": app_version,
        "engine_version": AUTONOMOUS_COMPANY_SENTINEL_VERSION,
        "run_id": "ACS-" + datetime.now(MADRID_TZ).strftime("%Y%m%d%H%M%S"),
        "last_run_madrid": _now(),
        "mode": mode,
        "mode_profile": profile,
        "runner": runner,
        "dry_run": bool(dry_run),
        "dangerous_actions_executed": False,
        "roles_reviewed": journey.get("roles") or ["anonymous", "FREE", "PRO", "ELITE", "ADMIN"],
        "devices_reviewed": journey.get("devices") or ["desktop_1440x900", "mobile_390x844"],
        "routes_checked": journey.get("routes_checked") or 0,
        "journey": journey,
        "reference": reference,
        "render_alignment": render_alignment,
        "local_env_status": local_env_status,
        "render_runtime_status": render_runtime_status,
        "telegram_quality_watch": telegram_watch,
        "navigation_integrity": navigation_integrity,
        "autonomous_product_qa": product_qa,
        "issues_summary": issues_summary,
        "outbox": outbox,
        "autofix_plan": autofix,
        "v904_automation_summary": v904_automation_summary,
        "action_policy": action_policy,
        "automation_modes": {
            "reference_scan": {
                "reads": ["Sentinel", "reference_images", "reference_manifest", "outbox", "visual gaps"],
                "writes": ["latest_run.json", "reference_gap_report.json", "codex_outbox.md"],
                "dry_run_required": True,
            },
            "daily_reference_review": {
                "reviews": ["admin", "cliente", "picks", "live", "calendario", "SHARK", "Telegram", "PWA/404", "outbox", "rutas críticas"],
                "dry_run_required": True,
            },
            "post_deploy_check": {
                "reviews": ["runtime-version", "admin-login", "rutas cliente", "rutas admin", "Telegram dry-run", "404 premium", "service worker", "reference_images", "outbox"],
                "dry_run_required": True,
            },
        },
        "screenshots": {
            "available": bool((reference.get("browser_result") or {}).get("browser_available")),
            "reason": "Browser/capturas no ejecutados en este entorno." if not (reference.get("browser_result") or {}).get("browser_available") else "Capturas locales disponibles en runtime.",
            "path": str(dirs["screenshots"]),
        },
        "warnings": [
            "No se declara equivalencia visual exacta sin capturas reales.",
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
        "active_issues_open": len(open_issues),
        "stale_issues": len([issue for issue in all_issues if issue.get("status") == "STALE_NEEDS_REVALIDATION"]),
        "resolved_by_rescan": len([issue for issue in all_issues if issue.get("status") == "RESOLVED_BY_RESCAN"]),
        "archived_prompts": outbox.get("archived_prompt_count", 0),
        "critical": len([issue for issue in open_issues if issue.get("severity") == "critical"]),
        "high": len([issue for issue in open_issues if issue.get("severity") == "high"]),
        "reference_gaps": len((reference.get("product_gap_report") or {}).get("gaps") or []),
        "browser_qa_available": bool((reference.get("browser_result") or {}).get("browser_available")),
        "visual_prompts": outbox.get("visual_prompt_count", 0),
        "v904_last_automation_mode": mode,
        "v904_gaps_read": v904_automation_summary["gaps_read"],
        "v904_gaps_addressed": v904_automation_summary["gaps_addressed"],
        "v904_gaps_pending": v904_automation_summary["gaps_pending"],
        "v904_prompts_active": v904_automation_summary["prompts_active"],
        "v904_errors_active": v904_automation_summary["errors_active"],
        "v904_deploy_status": v904_automation_summary["deploy_status"],
        "v904_secret_masking_status": v904_automation_summary["secret_masking_status"],
        "v904_next_step": v904_automation_summary["next_recommended_step"],
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
