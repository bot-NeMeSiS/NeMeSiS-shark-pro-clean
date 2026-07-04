"""V888 Sentinel AutoPilot self-improvement engine.

Safe internal operations layer for NeMeSiS SHARK PRO. It converts Sentinel,
Visual Worker and local route signals into issues, tasks and Codex prompts.
It never deploys, pushes, sends Telegram, mutates payments/users, touches
secrets, calls paid APIs, deletes data or invents sports data.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha1
import json
import re
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


MADRID_TZ = ZoneInfo("Europe/Madrid")

AUTOPILOT_VERSION = "V888_SENTINEL_AUTOPILOT_SELF_IMPROVEMENT_ENGINE_FINAL"

CATEGORIES = [
    "production_alignment",
    "telegram",
    "telegram_premium_picks",
    "sports_data",
    "picks_odds",
    "live",
    "navigation",
    "mobile",
    "visual_layout",
    "admin_ops",
    "shark_ai",
    "payments",
    "memberships",
    "logos",
    "security",
    "performance",
    "copy",
    "release_zip",
]

SEVERITIES = ["critical", "high", "medium", "low", "info"]

SAFE_FIX_CANDIDATES = {
    "copy",
    "visual_layout",
    "logos",
    "sports_data",
    "picks_odds",
    "live",
}

REQUIRES_APPROVAL_CATEGORIES = {
    "production_alignment",
    "telegram",
    "telegram_premium_picks",
    "payments",
    "security",
    "admin_ops",
    "release_zip",
}

FORBIDDEN_ACTIONS = [
    "auto_deploy",
    "auto_push",
    "send_real_telegram",
    "touch_secrets",
    "delete_db",
    "delete_users",
    "mutate_payments",
    "call_paid_apis_without_guard",
    "edit_production_code_without_approval",
]

CLIENT_ROUTES = [
    "/",
    "/app",
    "/partidos",
    "/calendar",
    "/live",
    "/directo",
    "/picks",
    "/shark",
    "/telegram",
    "/profile",
    "/track-record",
    "/support",
]

ADMIN_ROUTES = [
    "/admin/dashboard",
    "/admin/company-os",
    "/admin/company-audit",
    "/admin/continuous-sentinel",
    "/admin/sentinel-workflow",
    "/admin/visual-worker",
    "/admin/payments",
    "/admin/memberships",
]

SAFE_STATE_TOKENS = [
    "Sin datos reales",
    "Esperando proveedor",
    "Sin sincronizacion reciente",
    "Sin sincronización reciente",
    "Sin directos reales",
    "Sin picks activos",
    "Cuota pendiente",
    "Selección pendiente",
    "Pick en revisión",
    "Sin pick real publicado",
    "Proveedor sin datos ahora mismo",
    "No configurado",
    "Acción pendiente",
    "Modo seguro activo",
    "Análisis limitado sin proveedor IA",
    "Escudo pendiente",
    "Fallback visual activo",
]

MOJIBAKE_RE = re.compile(r"(Ã|Â|�|ï¿½)")
TECHNICAL_RE = re.compile(r"\b(None|null|undefined|Traceback|sqlite3\.|werkzeug\.)\b", re.I)
BAD_HREF_RE = re.compile(r"href=[\"'](?:#|javascript:void\(0\)|javascript:;|)[\"']", re.I)


def _now() -> str:
    return datetime.now(MADRID_TZ).replace(microsecond=0).isoformat()


def _memory_path(root: str | Path | None = None) -> Path:
    base = Path(root or Path.cwd())
    return base / "data" / "runtime" / "sentinel_autopilot_memory.json"


def _issue_id(title: str, category: str, route: str = "") -> str:
    raw = f"{category}|{route}|{title}".encode("utf-8", errors="ignore")
    return "AP-" + sha1(raw).hexdigest()[:12].upper()


def classify_autopilot_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """Apply the V888 severity policy to a candidate issue."""
    category = str(issue.get("category") or "visual_layout")
    title = str(issue.get("title") or "")
    evidence = str(issue.get("evidence") or "")
    text = f"{title} {evidence}".lower()

    severity = str(issue.get("severity") or "low")
    if any(token in text for token in ["secret visible", "admin exposed", "cron without secret", "500", "traceback", "db destructive"]):
        severity = "critical"
    elif category == "production_alignment" or any(token in text for token in ["render/local", "telegram cron", "login roto", "fake pick"]):
        severity = "high"
    elif category in {"navigation", "mobile", "shark_ai", "payments", "logos"}:
        severity = "medium"
    elif category == "copy":
        severity = "low"

    if severity not in SEVERITIES:
        severity = "low"

    issue["severity"] = severity
    issue["risk_level"] = severity
    issue["safe_to_auto_fix"] = category in SAFE_FIX_CANDIDATES and severity in {"low", "info"}
    issue["requires_approval"] = (category in REQUIRES_APPROVAL_CATEGORIES) or severity in {"critical", "high", "medium"}
    issue.setdefault("status", "open")
    issue.setdefault("detected_at_madrid", _now())
    issue.setdefault("source", "sentinel_autopilot")
    return issue


def generate_codex_prompt_for_issue(issue: dict[str, Any]) -> str:
    title = issue.get("title") or "Revisar incidencia AutoPilot"
    category = issue.get("category") or "visual_layout"
    route = issue.get("route") or issue.get("screen") or "sin ruta concreta"
    evidence = issue.get("evidence") or "Sin evidencia textual adicional."
    return (
        "Estoy trabajando en NeMeSiS SHARK PRO.\n\n"
        f"Incidencia AutoPilot: {title}\n"
        f"Categoria: {category}\n"
        f"Ruta/pantalla: {route}\n"
        f"Evidencia: {evidence}\n\n"
        "Reglas sagradas: no tocar secretos, no enviar Telegram real, no inventar partidos/picks/cuotas/resultados, "
        "no tocar pagos reales, no borrar DB/usuarios, no hacer push/deploy automatico y preservar V818+.\n\n"
        "Tarea: localizar la causa real, proponer un fix seguro, aplicar solo cambios controlados si son necesarios, "
        "ejecutar checks locales y documentar resultado, bloqueadores y siguiente accion."
    )


def build_safe_fix_plan(issue: dict[str, Any]) -> dict[str, Any]:
    category = issue.get("category") or "visual_layout"
    safe = bool(issue.get("safe_to_auto_fix"))
    approval = bool(issue.get("requires_approval"))
    if safe:
        next_step = "Puede prepararse como correccion segura de copy/estado visual y revalidarse con Sentinel."
        bucket = "Seguro"
    elif approval:
        next_step = "Requiere aprobacion humana antes de tocar codigo, datos, pagos, Telegram, deploy o seguridad."
        bucket = "Requiere aprobacion"
    else:
        next_step = "Mantener como diagnostico y repetir scan."
        bucket = "Bloqueado"
    return {
        "bucket": bucket,
        "safe_to_auto_fix": safe,
        "requires_approval": approval,
        "recommended_step": next_step,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "category": category,
    }


def create_autopilot_task(issue: dict[str, Any]) -> dict[str, Any]:
    issue = classify_autopilot_issue(dict(issue))
    prompt = issue.get("codex_prompt") or generate_codex_prompt_for_issue(issue)
    plan = build_safe_fix_plan(issue)
    return {
        "task_id": "TASK-" + issue["issue_id"],
        "issue_id": issue["issue_id"],
        "title": issue["title"],
        "category": issue["category"],
        "severity": issue["severity"],
        "status": "pending_approval" if issue["requires_approval"] else "ready_for_safe_review",
        "route": issue.get("route") or "",
        "suggested_fix": issue.get("suggested_fix") or plan["recommended_step"],
        "codex_prompt": prompt,
        "safe_fix_plan": plan,
    }


def _route_text(response: Any) -> str:
    try:
        return response.get_data(as_text=True)[:120000]
    except Exception:
        return ""


def _scan_routes(flask_client: Any, app_version: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if flask_client is None:
        return issues

    for route in CLIENT_ROUTES:
        try:
            response = flask_client.get(route)
            status = int(response.status_code)
            html = _route_text(response)
        except Exception as exc:
            issues.append(_new_issue("Ruta cliente rompe en scan", "navigation", "high", route, repr(exc), app_version))
            continue
        if status >= 500:
            issues.append(_new_issue("500 en ruta cliente", "navigation", "critical", route, f"HTTP {status}", app_version))
        if MOJIBAKE_RE.search(html) or TECHNICAL_RE.search(html):
            issues.append(_new_issue("Texto tecnico o mojibake visible", "copy", "low", route, "Mojibake/None/null/undefined detectado en HTML visible.", app_version))
        if BAD_HREF_RE.search(html):
            issues.append(_new_issue("Boton o enlace muerto visible", "navigation", "medium", route, "href vacio/#/javascript detectado.", app_version))
        if route in {"/partidos", "/calendar", "/live", "/directo", "/picks"} and not any(token in html for token in SAFE_STATE_TOKENS):
            issues.append(_new_issue("Pantalla deportiva sin estado seguro claro", "sports_data", "high", route, "No se encontro estado seguro para ausencia de datos reales.", app_version))
        if "v808-admin-rail" in html:
            issues.append(_new_issue("Admin rail aparece en cliente", "navigation", "high", route, "Navegacion admin mezclada en cliente.", app_version))

    for route in ADMIN_ROUTES:
        try:
            response = flask_client.get(route)
            status = int(response.status_code)
            html = _route_text(response)
        except Exception as exc:
            issues.append(_new_issue("Ruta admin rompe en scan", "admin_ops", "high", route, repr(exc), app_version))
            continue
        if status >= 500:
            issues.append(_new_issue("500 en ruta admin", "admin_ops", "critical", route, f"HTTP {status}", app_version))
        if status == 200 and "ns-client-sidebar" in html:
            issues.append(_new_issue("Nav cliente aparece en admin", "navigation", "high", route, "Sidebar cliente visible en admin.", app_version))

    return issues


def _new_issue(title: str, category: str, severity: str, route: str, evidence: str, app_version: str) -> dict[str, Any]:
    issue = {
        "issue_id": _issue_id(title, category, route),
        "title": title,
        "category": category,
        "severity": severity,
        "screen": route,
        "route": route,
        "evidence": evidence,
        "detected_at_madrid": _now(),
        "status": "open",
        "suggested_fix": "Revisar la evidencia y aplicar solo una correccion segura.",
        "source": "sentinel_autopilot",
        "version_detected": app_version,
        "render_version": "",
    }
    issue["codex_prompt"] = generate_codex_prompt_for_issue(issue)
    return classify_autopilot_issue(issue)


def _issues_from_sentinel(sentinel_result: dict[str, Any] | None, app_version: str) -> list[dict[str, Any]]:
    if not sentinel_result:
        return []
    items = sentinel_result.get("issues") or []
    issues: list[dict[str, Any]] = []
    for raw in items[:50]:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or raw.get("issue") or raw.get("category") or "Issue Sentinel")
        category = str(raw.get("category") or "visual_layout")
        route = str(raw.get("route") or raw.get("screen") or "")
        severity = str(raw.get("severity") or raw.get("risk_level") or "low")
        evidence = str(raw.get("evidence") or raw.get("detail") or raw.get("state") or "")
        issues.append(_new_issue(title, category, severity, route, evidence, app_version))
    return issues


def _issues_from_visual(visual_result: dict[str, Any] | None, app_version: str) -> list[dict[str, Any]]:
    if not visual_result:
        return []
    raw_items = (visual_result.get("issues") or []) + (visual_result.get("grouped_issues") or [])
    issues: list[dict[str, Any]] = []
    for raw in raw_items[:50]:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or raw.get("rule") or "Issue Visual Worker")
        route = str(raw.get("route") or raw.get("screen") or "")
        evidence = str(raw.get("evidence") or raw.get("detail") or raw.get("state") or "")
        issues.append(_new_issue(title, "visual_layout", str(raw.get("severity") or "low"), route, evidence, app_version))
    return issues


def _environment_issues(runtime: dict[str, Any] | None, app_version: str, render_runtime: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    runtime = runtime or {}
    render_runtime = render_runtime or {}
    render_version = render_runtime.get("app_version") or render_runtime.get("version_txt") or ""
    if render_version and render_version != app_version:
        issues.append(_new_issue("Render/local desalineado", "production_alignment", "high", "/api/runtime-version", f"Render={render_version}; local={app_version}", app_version))
    if runtime.get("openai_configured") is False:
        issues.append(_new_issue("SHARK IA en modo seguro", "shark_ai", "medium", "/shark", "OPENAI no configurado; debe comunicarse como modo seguro.", app_version))
    if runtime.get("stripe_configured") is False or runtime.get("payments_configured") is False:
        issues.append(_new_issue("Pagos pendientes de configuracion", "payments", "medium", "/admin/payments", "Stripe/checkout no debe mostrarse como operativo.", app_version))
    if int(runtime.get("team_logo_cache_count") or 0) == 0 and int(runtime.get("league_logo_cache_count") or 0) == 0:
        issues.append(_new_issue("Cache de logos en cero", "logos", "medium", "/partidos", "Debe existir fallback visual y no imagen rota.", app_version))
    return issues


def build_priority_matrix(issues: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = {severity: [] for severity in SEVERITIES}
    for issue in issues:
        matrix.setdefault(issue.get("severity", "low"), []).append(issue)
    return {
        "counts": {key: len(value) for key, value in matrix.items()},
        "top": [issue for severity in ["critical", "high", "medium", "low", "info"] for issue in matrix.get(severity, [])][:12],
    }


def build_next_best_actions(issues: list[dict[str, Any]]) -> list[str]:
    if any(i.get("category") == "production_alignment" for i in issues):
        return ["Alinear Render con el ZIP actual antes de certificar produccion.", "Revisar GitHub root y ejecutar Clear build cache & deploy."]
    if any(i.get("severity") == "critical" for i in issues):
        return ["Resolver criticos antes de cualquier mejora visual.", "Repetir Sentinel y AutoPilot tras el fix."]
    if any(i.get("category") == "telegram" for i in issues):
        return ["Validar Cron Telegram en dry-run y revisar dedupe/no filler."]
    if any(i.get("category") == "telegram_premium_picks" for i in issues):
        return ["Revisar preview V889 y bloquear picks sin cuota, seleccion, partido real o score premium."]
    if issues:
        return ["Atender incidencias high/medium primero.", "Generar prompt Codex por issue y aplicar solo fixes aprobados."]
    return ["Mantener AutoPilot en diagnostico diario.", "Ejecutar browser QA real antes de declarar pixel-perfect."]


def build_autopilot_snapshot(app_version: str, runtime: dict[str, Any] | None = None, render_runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    render_version = (render_runtime or {}).get("app_version") or (render_runtime or {}).get("version_txt") or ""
    return {
        "version": app_version,
        "autopilot_version": AUTOPILOT_VERSION,
        "timestamp_madrid": _now(),
        "runtime": runtime or {},
        "render_runtime": render_runtime or {},
        "render_local_aligned": not render_version or render_version == app_version,
        "render_version": render_version,
        "safety_policy": {
            "no_auto_deploy": True,
            "no_auto_push": True,
            "no_real_telegram": True,
            "no_payment_mutation": True,
            "no_secret_access": True,
            "no_fake_sports_data": True,
            "forbidden_actions": FORBIDDEN_ACTIONS,
        },
        "categories": CATEGORIES,
        "severity_levels": SEVERITIES,
    }


def run_autopilot_scan(
    flask_client: Any = None,
    app_version: str = AUTOPILOT_VERSION,
    runtime: dict[str, Any] | None = None,
    sentinel_result: dict[str, Any] | None = None,
    visual_result: dict[str, Any] | None = None,
    render_runtime: dict[str, Any] | None = None,
    save_memory: bool = False,
    memory_root: str | Path | None = None,
) -> dict[str, Any]:
    issues = []
    issues.extend(_environment_issues(runtime, app_version, render_runtime))
    issues.extend(_issues_from_sentinel(sentinel_result, app_version))
    issues.extend(_issues_from_visual(visual_result, app_version))
    issues.extend(_scan_routes(flask_client, app_version))

    deduped: dict[str, dict[str, Any]] = {}
    for issue in issues:
        issue = classify_autopilot_issue(issue)
        issue["codex_prompt"] = issue.get("codex_prompt") or generate_codex_prompt_for_issue(issue)
        deduped[issue["issue_id"]] = issue

    final_issues = list(deduped.values())
    tasks = [create_autopilot_task(issue) for issue in final_issues]
    matrix = build_priority_matrix(final_issues)
    score = max(0.0, 10.0 - (matrix["counts"].get("critical", 0) * 4.0) - (matrix["counts"].get("high", 0) * 2.0) - (matrix["counts"].get("medium", 0) * 0.75) - (matrix["counts"].get("low", 0) * 0.15))
    result = {
        **build_autopilot_snapshot(app_version, runtime, render_runtime),
        "status": "completed_diagnostic_only",
        "score": round(score, 1),
        "issues": final_issues,
        "tasks": tasks,
        "priority_matrix": matrix,
        "next_best_actions": build_next_best_actions(final_issues),
        "codex_prompts": [task["codex_prompt"] for task in tasks[:8]],
        "safe_actions": [task for task in tasks if not task["safe_fix_plan"]["requires_approval"]],
        "approval_required_actions": [task for task in tasks if task["safe_fix_plan"]["requires_approval"]],
        "dangerous_actions_executed": False,
    }
    if save_memory:
        result["memory"] = save_autopilot_memory(result, root=memory_root)
    return result


def build_autopilot_daily_report(scan: dict[str, Any]) -> dict[str, Any]:
    issues = scan.get("issues") or []
    return {
        "version": scan.get("version"),
        "generated_at_madrid": _now(),
        "score": scan.get("score"),
        "open_issues": len(issues),
        "critical": sum(1 for i in issues if i.get("severity") == "critical"),
        "high": sum(1 for i in issues if i.get("severity") == "high"),
        "medium": sum(1 for i in issues if i.get("severity") == "medium"),
        "low": sum(1 for i in issues if i.get("severity") == "low"),
        "next_best_actions": scan.get("next_best_actions") or [],
        "safe_note": "Diagnostico interno; no ejecuta cambios peligrosos.",
    }


def save_autopilot_memory(scan: dict[str, Any], root: str | Path | None = None) -> dict[str, Any]:
    path = _memory_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_autopilot_memory(root)
    previous_issues = {item.get("issue_id"): item for item in existing.get("issues", []) if isinstance(item, dict)}
    for issue in scan.get("issues", []):
        previous_issues[issue.get("issue_id")] = issue
    payload = {
        "updated_at_madrid": _now(),
        "last_scan": {
            "version": scan.get("version"),
            "score": scan.get("score"),
            "status": scan.get("status"),
            "issue_count": len(scan.get("issues", [])),
        },
        "issues": list(previous_issues.values())[-300:],
        "tasks": (existing.get("tasks") or [])[-200:] + (scan.get("tasks") or [])[:50],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(path), "issues_stored": len(payload["issues"]), "tasks_stored": len(payload["tasks"])}


def load_autopilot_memory(root: str | Path | None = None) -> dict[str, Any]:
    path = _memory_path(root)
    if not path.exists():
        return {"ok": True, "path": str(path), "issues": [], "tasks": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["ok"] = True
        payload["path"] = str(path)
        return payload
    except Exception as exc:
        return {"ok": False, "path": str(path), "issues": [], "tasks": [], "error": repr(exc)}


def mark_autopilot_issue_resolved(issue_id: str, root: str | Path | None = None) -> dict[str, Any]:
    memory = load_autopilot_memory(root)
    resolved = False
    for issue in memory.get("issues", []):
        if issue.get("issue_id") == issue_id:
            issue["status"] = "resolved"
            issue["resolved_at"] = _now()
            resolved = True
    path = _memory_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: v for k, v in memory.items() if k not in {"ok", "path"}}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": resolved, "issue_id": issue_id, "status": "resolved" if resolved else "not_found"}
