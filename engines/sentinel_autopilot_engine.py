"""V888 Sentinel AutoPilot self-improvement engine.

Safe internal operations layer for NeMeSiS SHARK PRO. It converts Sentinel,
Visual Worker and local route signals into issues, tasks and Codex prompts.
It never deploys, pushes, sends Telegram, mutates payments/users, touches
secrets, calls paid APIs, deletes data or invents sports data.
"""
from __future__ import annotations

import ast
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
    "sports_data_contract",
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
    "sports_data_contract",
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

SPORTS_CONTRACT_ROUTES = {
    "/",
    "/app",
    "/partidos",
    "/calendar",
    "/live",
    "/directo",
    "/picks",
    "/shark",
    "/telegram",
}

SPORTS_CONTRACT_ATTRIBUTES = {
    "sports-contract": "contract",
    "sports-snapshot": "snapshot_id",
    "sports-matches-today": "matches_today",
    "sports-matches-available": "matches_available",
    "sports-live-confirmed": "live_confirmed",
    "sports-picks-ready": "picks_ready",
    "sports-matches-with-picks": "matches_with_picks",
    "sports-finished-verified": "finished_verified",
    "sports-matches-synchronized": "matches_synchronized",
}

SPORTS_CONTRACT_CONSUMERS = {
    "app.py": [
        "shark_briefing", "_v931_legacy_home_summary", "_v931_provider_context",
        "v931_safe_dashboard_data", "v931_calendar_context", "v931_live_context",
        "v938_operations_snapshot", "v939_company_intelligence_bundle",
    ],
    "engines/company_intelligence_engine.py": [
        "collect_sports_signals", "collect_company_signals", "build_company_intelligence_snapshot",
    ],
    "engines/telegram_intelligence_engine.py": ["build_telegram_intelligence_snapshot"],
}


SAFE_STATE_TOKENS = [
    'Sin datos reales',
    'Esperando proveedor',
    'Sin sincronización reciente',
    'Sin sincronizacion reciente',
    'Sin directos reales',
    'Sin partidos reales',
    'Sin picks activos',
    'Cuota pendiente',
    'Selección pendiente',
    'Pick en revisión',
    'Sin pick real publicado',
    'Proveedor sin datos ahora mismo',
    'No configurado',
    'Acción pendiente',
    'Modo seguro activo',
    'Análisis limitado sin proveedor IA',
    'Escudo pendiente',
    'Fallback visual activo',
    'Resultado pendiente',
    'Pick pendiente',
    'Checkout pendiente de configuración',
    'Stripe no configurado',
    'SHARK IA avanzada pendiente de configuración',
]

MOJIBAKE_RE = re.compile(r"(Ãƒ|Ã‚|ï¿½|Ã¯¿Â½)")
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
    elif category == "copy" and str(issue.get("priority") or "").upper() == "P2":
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
        next_step = "Requiere aprobacion humana antes de tocar código, datos, pagos, Telegram, deploy o seguridad."
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
        "likely_files": list(issue.get("likely_files") or []),
        "suggested_fix": issue.get("suggested_fix") or plan["recommended_step"],
        "codex_prompt": prompt,
        "safe_fix_plan": plan,
    }


def _route_text(response: Any) -> str:
    try:
        return response.get_data(as_text=True)[:120000]
    except Exception:
        return ""


def _data_attribute(html: str, name: str) -> str | None:
    match = re.search(rf'\bdata-{re.escape(name)}="([^"]*)"', html or "")
    return match.group(1) if match else None


def _rendered_sports_contract_issues(
    route: str,
    status: int,
    html: str,
    expected: dict[str, Any],
    app_version: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if status != 200 or route not in SPORTS_CONTRACT_ROUTES:
        return issues
    observed = {
        contract_key: _data_attribute(html, attribute)
        for attribute, contract_key in SPORTS_CONTRACT_ATTRIBUTES.items()
    }
    if not observed.get("contract") or not observed.get("snapshot_id"):
        issues.append(_new_issue(
            "Consumidor sin Sports Data Contract",
            "sports_data_contract",
            "high",
            route,
            "La pantalla no expone contrato y snapshot canonicos.",
            app_version,
        ))
        return issues
    if expected:
        mismatches = []
        for key in SPORTS_CONTRACT_ATTRIBUTES.values():
            if str(observed.get(key)) != str(expected.get(key)):
                mismatches.append(f"{key}:{observed.get(key)}!={expected.get(key)}")
        if mismatches:
            issues.append(_new_issue(
                "Metricas deportivas fuera de contrato",
                "sports_data_contract",
                "high",
                route,
                "; ".join(mismatches[:9]),
                app_version,
            ))
    card_count = html.count('data-v934-match-card="true"')
    canonical_card_count = html.count('data-v939-match-card-spec="canonical-v1"')
    if card_count != canonical_card_count:
        issues.append(_new_issue(
            "Match card fuera de especificacion canonica",
            "sports_data_contract",
            "high",
            route,
            f"cards={card_count}; canonical={canonical_card_count}",
            app_version,
        ))
    return issues


def _independent_sports_query_issues(
    root: str | Path | None,
    app_version: str,
) -> list[dict[str, Any]]:
    if root is None:
        return []
    root_path = Path(root)
    forbidden_calls = {"get_matches", "get_upcoming_matches", "get_picks", "rows", "one"}
    official_tokens = {
        "valid_matches_today", "valid_upcoming_matches", "valid_live_events",
        "valid_active_picks", "finished_matches",
    }
    violations = []
    for relative_path, function_names in SPORTS_CONTRACT_CONSUMERS.items():
        path = root_path / relative_path
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue
        functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for function_name in function_names:
            node = functions.get(function_name)
            if node is None:
                violations.append(f"{relative_path}:{function_name}:missing")
                continue
            for call in (item for item in ast.walk(node) if isinstance(item, ast.Call)):
                called = call.func.id if isinstance(call.func, ast.Name) else ""
                if called in forbidden_calls:
                    violations.append(f"{relative_path}:{function_name}:{called}")
                if called == "len" and call.args:
                    argument = ast.unparse(call.args[0]) if hasattr(ast, "unparse") else ""
                    if any(token in argument for token in official_tokens):
                        violations.append(f"{relative_path}:{function_name}:len({argument[:48]})")
            for literal in (item for item in ast.walk(node) if isinstance(item, ast.Constant) and isinstance(item.value, str)):
                if re.search(r"\bSELECT\s+(?:COUNT|SUM)\b", literal.value, re.IGNORECASE):
                    violations.append(f"{relative_path}:{function_name}:sql_aggregate")
    if not violations:
        return []
    return [_new_issue(
        "Consumidor recalcula metricas deportivas",
        "sports_data_contract",
        "high",
        "Sports Data Contract",
        "; ".join(sorted(set(violations))[:20]),
        app_version,
    )]


def _scan_routes(
    flask_client: Any,
    app_version: str,
    sports_contract: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
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
        issues.extend(_rendered_sports_contract_issues(route, status, html, dict(sports_contract or {}), app_version))

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


def build_customer_trust_icon_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the PQV939-005 visual contract without rendering or writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    css_path = project_root / "static" / "v933-product.css"
    template_path = project_root / "templates" / "components" / "v933_ui.html"
    try:
        css = css_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        css = ""
    try:
        template = template_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        template = ""

    direct_chip = bool(re.search(r"\.v935-customer-trust-rules\s*>\s*span\s*\{", css))
    descendant_chip = bool(re.search(r"\.v935-customer-trust-rules\s+span\s*\{", css))
    direct_last_chip = bool(re.search(r"\.v935-customer-trust-rules\s*>\s*span:last-child\s*\{", css))
    icon_rule = bool(re.search(
        r"\.v935-customer-trust-rules\s+\.v933-icon\s*\{[^}]*width:\s*14px;[^}]*height:\s*14px;",
        css,
    ))
    macro_contract = (
        "{% macro customer_trust_panel(trust)" in template
        and template.count("{{ icon('target') }} Picks completos") == 1
        and template.count("{{ icon('history') }} Hist") == 1
        and template.count("{{ icon('shield') }} Sin beneficio garantizado") == 1
    )

    violations = []
    if not direct_chip or descendant_chip:
        violations.append("chip_selector_must_target_direct_children")
    if not direct_last_chip:
        violations.append("mobile_last_chip_selector_must_target_direct_child")
    if not icon_rule:
        violations.append("icon_size_rule_missing")
    if not macro_contract:
        violations.append("customer_trust_macro_contract_missing")

    passed = not violations
    return {
        "issue_id": "PQV939-005",
        "version": app_version,
        "component": "customer_trust_panel",
        "affected_routes": ["/app", "/picks", "/shark", "/track-record", "/partido/<id>"],
        "cause": "A descendant span selector applied chip padding, border and background to the nested icon span.",
        "solution": "Scope chip styles to direct children and preserve the dedicated icon rule.",
        "evidence": {
            "direct_chip_selector": direct_chip,
            "descendant_chip_selector": descendant_chip,
            "direct_mobile_last_chip_selector": direct_last_chip,
            "icon_rule": icon_rule,
            "macro_contract": macro_contract,
            "violations": violations,
        },
        "preventive_rule": "Nested trust icons must never inherit chip padding, border or background.",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }


def build_client_copy_audience_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the PQV939-006 client/admin copy boundary without writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    client_templates = (
        "templates/home.html",
        "templates/client_app_center.html",
        "templates/calendar.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/shark.html",
    )
    admin_templates = (
        "templates/admin_dashboard.html",
        "templates/admin_data_center.html",
        "templates/admin_data_trust_center.html",
        "templates/admin_realtime_center.html",
    )
    forbidden = re.compile(r"\bDB\b|\bDB/cache\b|\bcach(?:e|é)\b|\brender\b", re.IGNORECASE)
    client_hits = {
        path: sorted({match.group(0) for match in forbidden.finditer(_read(path))})
        for path in client_templates
    }
    client_hits = {path: matches for path, matches in client_hits.items() if matches}

    shared_template = _read("templates/components/v933_ui.html")
    polling_js = _read("static/v934-realtime.js")
    realtime_engine = _read("engines/v934_realtime_sports_engine.py")
    live_template = _read("templates/live.html")
    client_message = "Datos confirmados disponibles. La información se mantiene accesible entre actualizaciones."
    client_fallback = "La información confirmada sigue disponible entre actualizaciones."
    client_engine_fallback = "Actualización temporalmente no disponible. Se conserva la última información confirmada."

    snapshot_message_contract = (
        client_message in realtime_engine
        and client_engine_fallback in realtime_engine
        and "Datos reales actualizados desde DB/cache." not in realtime_engine
        and "se conserva el ultimo cache seguro" not in realtime_engine
    )
    shared_macro_contract = (
        client_fallback in shared_template
        and "technical_message if technical else client_message" in shared_template
        and "DB/caché:" in shared_template
    )
    polling_contract = (
        client_fallback in polling_js
        and "var message = technical" in polling_js
        and "DB/caché:" in polling_js
        and "La vista se mantiene operativa con DB y caché." not in polling_js
    )
    live_contract = (
        "Los últimos datos confirmados siguen accesibles" in live_template
        and "DB y caché durante render" not in live_template
    )
    admin_contract = all(
        re.search(r"realtime_state_bar\([^\n]*true\)", _read(path))
        for path in admin_templates
    )

    violations = []
    if client_hits:
        violations.append("technical_terms_visible_in_client_templates")
    if not snapshot_message_contract:
        violations.append("realtime_snapshot_client_message_not_safe")
    if not shared_macro_contract:
        violations.append("shared_realtime_macro_missing_audience_split")
    if not polling_contract:
        violations.append("polling_can_restore_technical_client_copy")
    if not live_contract:
        violations.append("live_contract_exposes_implementation_detail")
    if not admin_contract:
        violations.append("admin_realtime_diagnostics_not_explicitly_technical")

    passed = not violations
    return {
        "issue_id": "PQV939-006",
        "version": app_version,
        "component": "realtime_copy_audience_contract",
        "affected_routes": ["/", "/app", "/calendar", "/live", "/picks"],
        "cause": "A shared realtime safe_message and a fixed Live label exposed DB/cache/render details to clients.",
        "solution": "Use outcome-focused client copy while retaining explicit technical diagnostics in admin mode.",
        "evidence": {
            "client_visible_hits": client_hits,
            "snapshot_message_contract": snapshot_message_contract,
            "shared_macro_contract": shared_macro_contract,
            "polling_contract": polling_contract,
            "live_contract": live_contract,
            "admin_contract": admin_contract,
            "violations": violations,
        },
        "preventive_rule": "Client copy explains availability and freshness; DB/cache/render terminology remains admin-only.",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }


def build_madrid_timestamp_presentation_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect PQV939-007 without rendering, writing or external calls."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    madrid_engine = _read("engines/madrid_time_engine.py")
    realtime_engine = _read("engines/v934_realtime_sports_engine.py")
    application = _read("app.py")
    shared_template = _read("templates/components/v933_ui.html")
    polling_js = _read("static/v934-realtime.js")
    client_templates = (
        "templates/home.html",
        "templates/client_app_center.html",
        "templates/calendar.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/match_detail.html",
    )
    raw_iso = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})\b")
    client_literal_hits = {
        path: sorted(set(raw_iso.findall(_read(path))))
        for path in client_templates
        if raw_iso.search(_read(path))
    }

    formatter_contract = (
        "def format_madrid_sync_label" in madrid_engine
        and "MONTHS_ES_SHORT" in madrid_engine
        and "· Madrid" in madrid_engine
        and "Sin sincronización confirmada" in madrid_engine
    )
    snapshot_contract = (
        '"last_safe_sync": last_safe_sync' in realtime_engine
        and '"last_safe_sync_label": format_madrid_sync_label(last_safe_sync)' in realtime_engine
    )
    filter_and_api_contract = (
        '@app.template_filter("sync_madrid_label")' in application
        and '"last_safe_sync_label": snapshot.get("last_safe_sync_label")' in application
    )
    provider_contract = (
        "last_sync|sync_madrid_label" in shared_template
        and 'datetime="{{ last_sync }}"' in shared_template
        and 'data-v939-sync-raw="{{ last_sync }}"' in shared_template
    )
    realtime_contract = (
        "raw_sync if technical else client_sync" in shared_template
        and 'datetime="{{ raw_sync }}"' in shared_template
        and 'data-v934-last-sync-raw="{{ raw_sync }}"' in shared_template
    )
    polling_contract = (
        "function updateSyncTimestamp" in polling_js
        and "node.textContent = technical" in polling_js
        and "payload.last_safe_sync_label" in polling_js
        and "data-v934-last-sync-raw" in polling_js
        and "setText(bar, '[data-v934-last-sync]', payload.last_safe_sync" not in polling_js
    )

    violations: list[str] = []
    if client_literal_hits:
        violations.append("raw_iso_literal_visible_in_client_template")
    if not formatter_contract:
        violations.append("canonical_madrid_sync_formatter_missing")
    if not snapshot_contract:
        violations.append("realtime_snapshot_missing_client_sync_label")
    if not filter_and_api_contract:
        violations.append("jinja_or_api_sync_label_contract_missing")
    if not provider_contract:
        violations.append("provider_state_can_print_raw_iso")
    if not realtime_contract:
        violations.append("realtime_bar_can_print_raw_iso_to_client")
    if not polling_contract:
        violations.append("polling_can_restore_raw_iso_to_client")

    passed = not violations
    return {
        "issue_id": "PQV939-007",
        "version": app_version,
        "component": "madrid_sync_timestamp_presentation",
        "affected_routes": ["/", "/app", "/calendar", "/live", "/picks", "/match/<id>"],
        "cause": "Machine ISO timestamps were reused as client-facing copy by shared macros and polling.",
        "impact": "Raw technical dates reduce readability and weaken the explicit Madrid-time promise.",
        "solution": "Derive one Madrid label while preserving the original ISO in APIs, datetime attributes and technical admin mode.",
        "evidence": {
            "client_literal_hits": client_literal_hits,
            "formatter_contract": formatter_contract,
            "snapshot_contract": snapshot_contract,
            "filter_and_api_contract": filter_and_api_contract,
            "provider_contract": provider_contract,
            "realtime_contract": realtime_contract,
            "polling_contract": polling_contract,
            "violations": violations,
        },
        "preventive_rule": "Client sync dates use the canonical Madrid label; raw ISO remains machine/admin evidence only.",
        "qa_result": "PASS" if passed else "REGRESSION",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }


def build_v940_calendar_experience_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the V940 Calendar contract without rendering, writes or calls."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    application = _read("app.py")
    template = _read("templates/calendar.html")
    css = _read("static/v933-product.css")
    javascript = _read("static/v940-calendar.js")

    call_names: dict[str, set[str]] = {}
    context_source = ""
    try:
        tree = ast.parse(application)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name in {"calendar_page", "api_calendar"}:
                call_names[node.name] = {
                    call.func.id
                    for call in ast.walk(node)
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                }
            elif node.name == "v940_calendar_context":
                context_source = ast.get_source_segment(application, node) or ""
    except (SyntaxError, ValueError):
        pass

    page_calls = call_names.get("calendar_page", set())
    api_calls = call_names.get("api_calendar", set())
    shared_snapshot_contract = (
        {"v932_safe_dashboard_data", "v940_calendar_context"} <= page_calls
        and {"v932_safe_dashboard_data", "v940_calendar_context"} <= api_calls
        and "calendar_experience_data" not in api_calls
        and "get_sports_metrics_contract" in context_source
    )
    source_safety_contract = (
        '"database_written": False' in context_source
        and '"external_calls": 0' in context_source
        and not re.search(
            r"\b(?:requests|get_db|execute|executemany|commit|provider|sync_api|ensure_client_live_fresh)\s*\(",
            context_source,
        )
    )
    state_contract = all(
        marker in application
        for marker in (
            "V940_CALENDAR_STATE_KEYS",
            "def _v940_calendar_href",
            "def _v940_calendar_active_filters",
            "def _v940_calendar_group_navigation",
            '"contract": "v940-calendar-history-layers-v1"',
        )
    )
    template_contract = all(
        marker in template
        for marker in (
            'data-v940-calendar-experience="history-layers-v1"',
            "data-v940-calendar-command",
            "data-v940-calendar-context",
            "data-v940-calendar-index",
            "data-v940-calendar-collection",
            "data-v940-calendar-filters-active",
            'name="date"',
            "Limpiar capas",
        )
    )
    canonical_card_contract = (
        template.count("{{ match_card(match, false, true) }}") == 1
        and template.count("v933-match-grid") == 1
        and "data-v934-match-card" not in template
    )
    responsive_contract = all(
        marker in css
        for marker in (
            ".v940-calendar-context {",
            "position: sticky;",
            ".v940-calendar-index",
            ".v940-calendar-day",
            ".v940-calendar-league > .v933-match-grid",
            "@media (max-width: 800px)",
            "@media (prefers-reduced-motion: reduce)",
        )
    )
    local_navigation_contract = all(
        marker in javascript
        for marker in (
            "window.sessionStorage",
            'navigationType() !== "back_forward"',
            "IntersectionObserver",
            'window.addEventListener("pagehide", savePosition)',
            'event.key !== "/"',
        )
    )
    no_client_network = not re.search(
        r"\b(?:fetch|XMLHttpRequest|WebSocket|sendBeacon)\s*\(",
        javascript,
    )

    checks = {
        "shared_snapshot_contract": shared_snapshot_contract,
        "source_safety_contract": source_safety_contract,
        "state_contract": state_contract,
        "template_contract": template_contract,
        "canonical_card_contract": canonical_card_contract,
        "responsive_contract": responsive_contract,
        "local_navigation_contract": local_navigation_contract,
        "no_client_network": no_client_network,
    }
    violations = [name for name, passed in checks.items() if not passed]
    passed = not violations
    return {
        "issue_id": "V940-CALENDAR-EXPERIENCE-CONTRACT",
        "version": app_version,
        "component": "calendar_discovery_experience",
        "affected_routes": ["/calendar", "/calendario", "/partidos", "/api/calendar"],
        "cause": "Calendar context can regress when a consumer recalculates data or drops persistent navigation layers.",
        "impact": "Users lose date, filter or scroll context and need more effort to locate a match.",
        "solution": "Keep page and API on one V940 snapshot, one canonical match card and local-only context restoration.",
        "evidence": {**checks, "violations": violations},
        "preventive_rule": (
            "Calendar consumers use v940_calendar_context over sports-metrics-v1; "
            "navigation layers and the canonical match card remain present."
        ),
        "qa_result": "PASS" if passed else "REGRESSION",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }

def build_v944_match_center_foundation_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the V944 Match Center foundation without rendering or writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    application = _read("app.py")
    engine = _read("engines/match_context_engine.py")
    template = _read("templates/match_detail.html")
    components = _read("templates/components/v944_match_center.html")
    css = _read("static/v933-product.css")
    tracker = _read("engines/api_football_live_tracker_engine.py")
    intelligence_engine = _read("engines/match_intelligence_engine.py")
    shark_adapter = _read("engines/shark_context_presentation_engine.py")
    telegram_adapter = _read("engines/telegram_intelligence_engine.py")
    platform_contracts = _read("engines/sports_platform_contracts.py")
    domain_model_engine = _read("engines/sports_domain_model_engine.py")
    knowledge_layer = _read("engines/sports_knowledge_layer_engine.py")

    route_source = ""
    detail_source = ""
    api_detail_source = ""
    try:
        tree = ast.parse(application)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name == "match_detail_page":
                route_source = ast.get_source_segment(application, node) or ""
            elif node.name == "match_detail":
                detail_source = ast.get_source_segment(application, node) or ""
            elif node.name == "api_match_detail":
                api_detail_source = ast.get_source_segment(application, node) or ""
    except (SyntaxError, ValueError):
        pass

    expected_components = (
        "MatchHeader", "ScoreWidget", "MatchStory", "Timeline", "StatsPanel",
        "SharkPanel", "TelegramPanel", "BankrollPanel", "CompetitionPanel", "QuickActions",
    )
    expected_states = (
        "loading", "ready", "partial", "finished", "error", "offline", "unknown",
    )
    source_contract = all(marker in engine for marker in (
        'MATCH_CENTER_CONTRACT = "MATCH-CENTER-LIFECYCLE-STORY-V1"',
        "class MatchContext:",
        "def build_match_context(",
        '"builder_database_queries": 0',
        '"builder_database_writes": 0',
        '"external_calls": 0',
        '"single_snapshot": True',
        "def _real_statistics(",
        "build_match_intelligence(",
        "build_shark_match_intelligence_state(",
        "intelligence: dict[str, Any]",
        '"SPORTS-ENTITY-CENTER-CONTEXT-V1"',
    ))
    pure_builder_contract = not re.search(
        r"\b(?:sqlite3|requests|urllib\.request|flask|commit|execute|executemany)\b",
        engine,
        flags=re.IGNORECASE,
    )
    single_load_contract = all((
        detail_source.count("annotate_match(") == 1,
        detail_source.count("related_picks_for_match(") == 1,
        "include_depth=False" in route_source,
        "build_match_context(" in route_source,
        "dashboard_data(" not in route_source,
        "get_public_home_sports_summary(" not in route_source,
    ))
    get_side_effect_contract = not re.search(
        r"\b(?:record_user_activity|commit|execute|save_|insert_|update_|delete_)\s*\(",
        route_source,
        flags=re.IGNORECASE,
    )
    tracker_reader_source = ""
    if "def live_tracker_for_match" in tracker and "def sync_api_football_fixture_detail" in tracker:
        tracker_reader_source = tracker.split("def live_tracker_for_match", 1)[1].split(
            "def sync_api_football_fixture_detail", 1
        )[0]
    read_only_tracker_contract = all((
        "def _connect_readonly" in tracker,
        "mode=ro" in tracker,
        "_connect_readonly" in tracker_reader_source,
        "ensure_live_tracker_schema" not in tracker_reader_source,
        "_api_get(" not in tracker_reader_source,
    ))
    api_get_side_effect_contract = bool(api_detail_source) and "save_shark_context(" not in api_detail_source
    state_contract = all(f'"{state}"' in engine for state in expected_states)
    component_contract = all(
        name in engine
        and (
            f'data-match-component="{name}"' in components
            or f"panel_start('{name}'" in components
        )
        for name in expected_components
    )
    shell_contract = all(marker in template for marker in (
        'data-v944-match-center-foundation="phase-1"',
        "data-match-contract=",
        "match_header(match_context)",
        "score_widget(match_context)",
        "match_story(match_context)",
        "timeline(match_context)",
        "stats_panel(match_context)",
        "shark_panel(match_context)",
        "telegram_panel(match_context)",
        "bankroll_panel(match_context)",
        "competition_panel(match_context)",
        "quick_actions(match_context)",
        "data_quality_panel(match_context)",
        "data-sports-domain-model=",
        'data-sports-core-match-center="intelligence-phase-1"',
    ))
    safe_fallback_contract = (
        "No disponible." in components
        and "El marcador aparecerá únicamente" in components
        and "datos confirmados" in engine
    )
    intelligence_contract = all((
        'data-stat-source=' in components,
        'data-shark-evidence=' in components,
        'data-entity-contract=' in components,
        'data-match-intelligence-consumer="shark"' in components,
        'data-match-intelligence-contract=' in template,
        "tracker=live" in engine,
        "statistics=statistics" in engine,
        "timeline=timeline" in engine,
        '"field_state": field_state' in tracker,
        '"broken_links_allowed": False' in engine,
    ))
    match_intelligence_core_contract = all((
        'MATCH_INTELLIGENCE_CONTRACT = "MATCH-INTELLIGENCE-EVIDENCE-V1"'
        in intelligence_engine,
        "def build_match_intelligence(" in intelligence_engine,
        "def build_match_intelligence_consumer_view(" in intelligence_engine,
        "def build_shark_match_intelligence_state(" in intelligence_engine,
        '"database_writes": 0' in intelligence_engine,
        '"external_calls": 0' in intelligence_engine,
        '"generative_ai_calls": 0' in intelligence_engine,
        '"numeric_confidence_score": None' in intelligence_engine,
        '"sports_graph_write_authorized": False' in intelligence_engine,
        "match_intelligence=context.get(" in shark_adapter,
        "match_intelligence=match_intelligence" in telegram_adapter,
        "match_intelligence: dict[str, Any]" in platform_contracts,
    ))
    unified_domain_model_contract = all((
        "SPORTS_DOMAIN_MODEL_CONTRACT" in domain_model_engine,
        "def normalize_match_entity(" in domain_model_engine,
        "def normalize_team_entity(" in domain_model_engine,
        "def normalize_competition_entity(" in domain_model_engine,
        "def normalize_player_entity(" in domain_model_engine,
        "def normalize_timeline_event_entity(" in domain_model_engine,
        "def normalize_evidence_entity(" in domain_model_engine,
        "def build_freshness_entity(" in domain_model_engine,
        "def build_sports_graph_foundation(" in domain_model_engine,
        "def build_telegram_readonly_contract(" in domain_model_engine,
        '"database_writes": 0' in domain_model_engine,
        '"external_calls": 0' in domain_model_engine,
        '"send_executed": False' in domain_model_engine,
        "domain_model: dict[str, Any]" in engine,
        "canonical_match=canonical_match" in engine,
        "canonical_timeline=canonical_timeline" in engine,
        "telegram_readonly_contract" in engine,
        "sports_domain_model" in platform_contracts,
        "build_telegram_readonly_contract" in telegram_adapter,
    ))
    sports_knowledge_layer_contract = all((
        'SPORTS_KNOWLEDGE_LAYER_CONTRACT = "SPORTS-KNOWLEDGE-LAYER-V1"'
        in knowledge_layer,
        "def build_sports_knowledge_snapshot(" in knowledge_layer,
        "def build_team_knowledge(" in knowledge_layer,
        "def build_competition_knowledge(" in knowledge_layer,
        "def build_match_knowledge(" in knowledge_layer,
        "def build_season_knowledge(" in knowledge_layer,
        '"database_writes": 0' in knowledge_layer,
        '"external_calls": 0' in knowledge_layer,
        '"telegram_sends": 0' in knowledge_layer,
        '"stripe_calls": 0' in knowledge_layer,
        "build_sports_knowledge_snapshot(" in engine,
        "sports_knowledge: dict[str, Any]" in engine,
        '"sports_knowledge_contract": sports_knowledge.get("contract")'
        in engine,
        '"sports_knowledge_database_writes":' in engine,
        '"sports_knowledge_external_calls":' in engine,
        '"name": "Sports Knowledge"' in engine,
    )) and not re.search(
        r"\b(?:sqlite3|requests|urllib\.request|flask|commit|execute|executemany)\b",
        knowledge_layer,
        flags=re.IGNORECASE,
    )

    match_center_2_contract = all((
        "legacy_event_from_entity" in engine,
        "legacy_match_from_entity" in engine,
        "def _timeline_from_domain(" in engine,
        "transparency: dict[str, dict[str, Any]]" in engine,
        "experience_blocks: list[dict[str, Any]]" in engine,
        '"timeline_event_contract": event_summary.get("contract")' in engine,
        '"match_center_2_transparency": True' in engine,
        'data-match-transparency="{{ key }}"' in components,
        'data-canonical-timeline-event=' in components,
        'data-timeline-event-contract=' in components,
        'data-sports-domain-model="unified-v1"' in components,
        "data_quality_panel(match_context)" in template,
        ".v944-transparency {" in css,
        ".v944-domain-quality" in css,
    ))
    entity_route_contract = all(marker in application for marker in (
        '@app.route("/team/<team_id>")',
        '@app.route("/competition/<competition_id>")',
        '@app.route("/player/<player_id>")',
    ))
    responsive_contract = all(marker in css for marker in (
        "V944 MATCH CENTER FOUNDATION",
        ".v944-match-anchor {",
        ".v944-match-layout {",
        ".v944-stats {",
        ".v944-shark-context {",
        "@media (max-width: 1080px)",
        "@media (max-width: 800px)",
        "@media (prefers-reduced-motion: reduce)",
    ))
    no_foundation_javascript = not (project_root / "static/v944-match-center.js").exists()

    checks = {
        "source_contract": source_contract,
        "pure_builder_contract": pure_builder_contract,
        "single_load_contract": single_load_contract,
        "get_side_effect_contract": get_side_effect_contract,
        "api_get_side_effect_contract": api_get_side_effect_contract,
        "read_only_tracker_contract": read_only_tracker_contract,
        "intelligence_contract": intelligence_contract,
        "match_intelligence_core_contract": match_intelligence_core_contract,
        "unified_domain_model_contract": unified_domain_model_contract,
        "sports_knowledge_layer_contract": sports_knowledge_layer_contract,
        "match_center_2_contract": match_center_2_contract,
        "entity_route_contract": entity_route_contract,
        "state_contract": state_contract,
        "component_contract": component_contract,
        "shell_contract": shell_contract,
        "safe_fallback_contract": safe_fallback_contract,
        "responsive_contract": responsive_contract,
        "no_foundation_javascript": no_foundation_javascript,
    }
    violations = [name for name, passed in checks.items() if not passed]
    passed = not violations
    return {
        "issue_id": "V944-MATCH-CENTER-FOUNDATION-CONTRACT",
        "version": app_version,
        "component": "match_center_foundation",
        "affected_routes": ["/match/<id>", "/partido/<id>"],
        "cause": "The Match Center can regress if a component reloads facts, loses a canonical state, bypasses SPORTS-CORE-UNIFIED-DOMAIN-MODEL-V1 or hides evidence/freshness from the user.",
        "impact": "Users can see contradictory match facts, unstable fallbacks, duplicated sports identities, hidden data limitations or a broken responsive shell.",
        "solution": "Keep every region on one pure MatchContext, one SPORTS-CORE-UNIFIED-DOMAIN-MODEL-V1 entity graph, one SPORTS-CORE-TIMELINE-EVENT-V1 timeline and one transparent MATCH-INTELLIGENCE-EVIDENCE-V1 snapshot.",
        "evidence": {**checks, "violations": violations},
        "preventive_rule": (
            "All Match Center regions consume MATCH-CENTER-LIFECYCLE-STORY-V1 through one MatchContext; "
            "provider facts remain cached, all consumers reuse MATCH-INTELLIGENCE-EVIDENCE-V1, "
            "timeline events stay canonical, every block exposes evidence/freshness, "
            "and GET rendering has no writes or external calls."
        ),
        "qa_result": "PASS" if passed else "REGRESSION",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }

def build_team_center_experience_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the Team Center premium experience contract without writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    application = _read("app.py")
    engine = _read("engines/team_center_engine.py")
    graph_engine = _read("engines/sports_graph_foundation_engine.py")
    template = _read("templates/team_detail.html")
    css = _read("static/v933-product.css")
    platform_contracts = _read("engines/sports_platform_contracts.py")

    engine_contract = all(marker in engine for marker in (
        'TEAM_CENTER_CONTRACT = "TEAM-CENTER-PREMIUM-CLUB-EXPERIENCE-V1"',
        "build_unified_domain_snapshot(",
        "normalize_team_entity(",
        "build_team_knowledge(",
        "build_sports_knowledge_snapshot(",
        "build_sports_graph_relationships(",
        '"database_writes": 0',
        '"external_calls": 0',
        '"telegram_sends": 0',
        '"stripe_calls": 0',
        '"no_fake_data": True',
    ))
    graph_contract = all(marker in graph_engine for marker in (
        'SPORTS_GRAPH_FOUNDATION_CONTRACT = "SPORTS-GRAPH-FOUNDATION-RELATIONSHIPS-V1"',
        "match_has_team",
        "team_has_match",
        "match_belongs_to_competition",
        "team_competes_in_competition",
        "match_belongs_to_season",
        "match_has_timeline_event",
        "pick_references_match",
        "odds_prices_match",
        "telegram_context_mentions_match",
        "shark_context_analyzes_match",
        '"database_writes": 0',
        '"external_calls": 0',
    ))
    pure_engine_contract = not re.search(
        r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe)\b|\b(?:commit|execute|executemany)\s*\(",
        engine + graph_engine,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    app_contract = all(marker in application for marker in (
        "from engines.team_center_engine import build_team_center_context",
        'detail["team_center"] = build_team_center_context(',
        '@app.route("/team/<team_id>")',
        '@app.route("/equipo/<team_id>")',
        '@app.route("/api/teams/<team_id>/detail")',
    ))
    template_contract = all(marker in template for marker in (
        'data-team-center-contract=',
        'data-sports-domain-model=',
        'data-sports-knowledge-contract=',
        'data-sports-graph-contract=',
        'data-team-center-section="header"',
        'data-team-center-section="recent-form"',
        'data-team-center-section="upcoming-matches"',
        'data-team-center-section="recent-results"',
        'data-team-center-section="data-quality"',
        'data-team-center-section="sports-graph"',
        'match_card(match, true, true)',
        'No disponible',
        'Ninguna fuente lo confirma',
        'Información pendiente',
    ))
    visual_contract = all(marker in css for marker in (
        "TEAM CENTER PREMIUM CLUB EXPERIENCE V1",
        ".team-center-v1",
        ".team-center-hero",
        ".team-center-layout",
        ".team-center-match-grid",
        "@media (max-width: 1080px)",
        "@media (max-width: 760px)",
    ))
    registry_contract = all(marker in platform_contracts for marker in (
        '"key": "team_center"',
        '"contract": "TEAM-CENTER-PREMIUM-CLUB-EXPERIENCE-V1"',
        '"key": "sports_graph"',
        '"contract": "SPORTS-GRAPH-FOUNDATION-RELATIONSHIPS-V1"',
    ))

    violations: list[str] = []
    if not engine_contract:
        violations.append("team_center_engine_not_using_sports_core_contracts")
    if not graph_contract:
        violations.append("sports_graph_foundation_relationships_missing")
    if not pure_engine_contract:
        violations.append("team_center_or_graph_engine_has_side_effect_imports")
    if not app_contract:
        violations.append("team_center_route_or_api_not_integrated")
    if not template_contract:
        violations.append("team_center_template_contract_missing")
    if not visual_contract:
        violations.append("team_center_responsive_visual_contract_missing")
    if not registry_contract:
        violations.append("sports_platform_registry_not_updated")

    passed = not violations
    return {
        "issue_id": "TEAM-CENTER-PREMIUM-EXPERIENCE",
        "version": app_version,
        "component": "team_center_premium_club_experience",
        "affected_routes": ["/team/<id>", "/equipo/<id>", "/api/teams/<id>/detail"],
        "cause": "Team Center must remain a Sports Core consumer, not an isolated team page.",
        "solution": "Use Team Center context, Sports Knowledge Layer, Sports Graph and canonical match_card() with honest fallbacks.",
        "evidence": {
            "engine_contract": engine_contract,
            "graph_contract": graph_contract,
            "pure_engine_contract": pure_engine_contract,
            "app_contract": app_contract,
            "template_contract": template_contract,
            "visual_contract": visual_contract,
            "registry_contract": registry_contract,
            "violations": violations,
        },
        "preventive_rule": "Team Center cannot calculate a parallel model or render custom match cards; it consumes Sports Core contracts only.",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }


def build_competition_center_experience_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the Competition Center premium experience contract without writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    application = _read("app.py")
    engine = _read("engines/competition_center_engine.py")
    graph_engine = _read("engines/sports_graph_foundation_engine.py")
    template = _read("templates/competition_detail.html")
    css = _read("static/v933-product.css")
    platform_contracts = _read("engines/sports_platform_contracts.py")

    engine_contract = all(marker in engine for marker in (
        'COMPETITION_CENTER_CONTRACT = "COMPETITION-CENTER-LEAGUE-INTELLIGENCE-PLATFORM-V1"',
        "build_unified_domain_snapshot(",
        "normalize_competition_entity(",
        "normalize_team_entity(",
        "build_competition_knowledge(",
        "build_season_knowledge(",
        "build_sports_knowledge_snapshot(",
        "build_sports_graph_relationships(",
        '"database_writes": 0',
        '"external_calls": 0',
        '"telegram_sends": 0',
        '"stripe_calls": 0',
        '"no_fake_data": True',
    ))
    graph_contract = all(marker in graph_engine for marker in (
        'SPORTS_GRAPH_FOUNDATION_CONTRACT = "SPORTS-GRAPH-FOUNDATION-RELATIONSHIPS-V1"',
        "match_has_team",
        "team_has_match",
        "match_belongs_to_competition",
        "team_competes_in_competition",
        "competition_has_team",
        "pick_references_match",
        "odds_prices_match",
        "telegram_context_mentions_match",
        "shark_context_analyzes_match",
        '"database_writes": 0',
        '"external_calls": 0',
    ))
    pure_engine_contract = not re.search(
        r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe)\b|\b(?:commit|execute|executemany)\s*\(",
        engine + graph_engine,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    app_contract = all(marker in application for marker in (
        "from engines.competition_center_engine import build_competition_center_context",
        'detail["competition_center"] = build_competition_center_context(',
        '@app.route("/competition/<competition_id>")',
        '@app.route("/competicion/<competition_id>")',
        '@app.route("/api/competitions/<competition_id>/detail")',
    ))
    template_contract = all(marker in template for marker in (
        'data-competition-center-contract=',
        'data-sports-domain-model=',
        'data-sports-knowledge-contract=',
        'data-sports-graph-contract=',
        'data-competition-center-section="header"',
        'data-competition-center-section="standings"',
        'data-competition-center-section="calendar"',
        'data-competition-center-section="teams"',
        'data-competition-center-section="data-quality"',
        'data-competition-center-section="sports-graph"',
        'match_card(match, true, true)',
        'No disponible',
        'Ninguna fuente confirma',
        'No crea clasificaciones',
    ))
    visual_contract = all(marker in css for marker in (
        "COMPETITION CENTER PREMIUM LEAGUE INTELLIGENCE V1",
        ".competition-center-v1",
        ".competition-center-hero",
        ".competition-center-layout",
        ".competition-center-team-grid",
        ".competition-center-table",
        "@media (max-width: 980px)",
        "@media (max-width: 640px)",
    ))
    registry_contract = all(marker in platform_contracts for marker in (
        '"key": "competition_center"',
        '"contract": "COMPETITION-CENTER-LEAGUE-INTELLIGENCE-PLATFORM-V1"',
        '"key": "sports_graph"',
        '"contract": "SPORTS-GRAPH-FOUNDATION-RELATIONSHIPS-V1"',
    ))

    violations: list[str] = []
    if not engine_contract:
        violations.append("competition_center_engine_not_using_sports_core_contracts")
    if not graph_contract:
        violations.append("sports_graph_foundation_competition_relationships_missing")
    if not pure_engine_contract:
        violations.append("competition_center_or_graph_engine_has_side_effect_imports")
    if not app_contract:
        violations.append("competition_center_route_or_api_not_integrated")
    if not template_contract:
        violations.append("competition_center_template_contract_missing")
    if not visual_contract:
        violations.append("competition_center_responsive_visual_contract_missing")
    if not registry_contract:
        violations.append("sports_platform_registry_not_updated_for_competition_center")

    passed = not violations
    return {
        "issue_id": "COMPETITION-CENTER-PREMIUM-EXPERIENCE",
        "version": app_version,
        "component": "competition_center_premium_league_intelligence",
        "affected_routes": ["/competition/<id>", "/competicion/<id>", "/api/competitions/<id>/detail"],
        "cause": "Competition Center must remain a Sports Core consumer, not an isolated league page.",
        "solution": "Use Competition Center context, Sports Knowledge Layer, Sports Graph and canonical match_card() with honest fallbacks.",
        "evidence": {
            "engine_contract": engine_contract,
            "graph_contract": graph_contract,
            "pure_engine_contract": pure_engine_contract,
            "app_contract": app_contract,
            "template_contract": template_contract,
            "visual_contract": visual_contract,
            "registry_contract": registry_contract,
            "violations": violations,
        },
        "preventive_rule": "Competition Center cannot calculate a parallel model or render custom match cards; it consumes Sports Core contracts only.",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }

def build_player_center_experience_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the Player Center premium experience contract without writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    application = _read("app.py")
    engine = _read("engines/player_center_engine.py")
    graph_engine = _read("engines/sports_graph_foundation_engine.py")
    knowledge_engine = _read("engines/sports_knowledge_layer_engine.py")
    template = _read("templates/player_detail.html")
    css = _read("static/v933-product.css")
    platform_contracts = _read("engines/sports_platform_contracts.py")

    engine_contract = all(marker in engine for marker in (
        'PLAYER_CENTER_CONTRACT = "PLAYER-CENTER-PREMIUM-SPORTS-IDENTITY-PLATFORM-V1"',
        "build_unified_domain_snapshot(",
        "normalize_player_entity(",
        "build_player_knowledge(",
        "build_sports_knowledge_snapshot(",
        "build_sports_graph_relationships(",
        "SHARK_INTELLIGENCE_PLATFORM_CONTRACT",
        "USER_INTELLIGENCE_PLATFORM_CONTRACT",
        '"database_writes": 0',
        '"external_calls": 0',
        '"telegram_sends": 0',
        '"stripe_calls": 0',
        '"generative_ai_calls": 0',
        '"no_fake_data": True',
    ))
    graph_contract = all(marker in graph_engine for marker in (
        'SPORTS_GRAPH_FOUNDATION_CONTRACT = "SPORTS-GRAPH-FOUNDATION-RELATIONSHIPS-V1"',
        "player_has_match",
        "match_has_player",
        "player_appears_in_event",
        "event_has_player",
        "player_linked_to_team",
        "team_has_player",
        "player_competes_in_competition",
        "shark_context_mentions_player",
        "user_intelligence_observes_player",
        '"database_writes": 0',
        '"external_calls": 0',
    ))
    knowledge_contract = all(marker in knowledge_engine for marker in (
        'PLAYER_KNOWLEDGE_CONTRACT = "SPORTS-KNOWLEDGE-PLAYER-V1"',
        "def build_player_knowledge(",
        "canonical_player_identity",
        "canonical_timeline_events_for_player",
    ))
    pure_engine_contract = not re.search(
        r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe|openai)\b|\b(?:commit|execute|executemany)\s*\(",
        engine + graph_engine,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    app_contract = all(marker in application for marker in (
        "from engines.player_center_engine import build_player_center_context",
        'detail["player_center"] = build_player_center_context(',
        '@app.route("/player/<player_id>")',
        '@app.route("/jugador/<player_id>")',
        '@app.route("/api/players/<player_id>/detail")',
    ))
    template_contract = all(marker in template for marker in (
        'data-player-center-contract=',
        'data-sports-domain-model=',
        'data-sports-knowledge-contract=',
        'data-player-knowledge-contract=',
        'data-sports-graph-contract=',
        'data-shark-intelligence-contract=',
        'data-user-intelligence-contract=',
        'data-player-center-section="header"',
        'data-player-center-section="participation"',
        'data-player-center-section="timeline"',
        'data-player-center-section="data-quality"',
        'data-player-center-section="sports-graph"',
        'match_card(match, true, true)',
        'No disponible',
        'Ninguna fuente confirma',
    ))
    visual_contract = all(marker in css for marker in (
        "PLAYER CENTER PREMIUM SPORTS IDENTITY PLATFORM V1",
        ".player-center-v1",
        ".player-center-hero",
        ".player-center-layout",
        ".player-center-match-grid",
        "@media (max-width: 980px)",
        "@media (max-width: 640px)",
    ))
    registry_contract = all(marker in platform_contracts for marker in (
        '"key": "player_center"',
        '"contract": "PLAYER-CENTER-PREMIUM-SPORTS-IDENTITY-PLATFORM-V1"',
        '"key": "sports_graph"',
        '"contract": "SPORTS-GRAPH-FOUNDATION-RELATIONSHIPS-V1"',
    ))

    violations: list[str] = []
    if not engine_contract:
        violations.append("player_center_engine_not_using_sports_core_contracts")
    if not graph_contract:
        violations.append("sports_graph_foundation_player_relationships_missing")
    if not knowledge_contract:
        violations.append("player_knowledge_contract_missing")
    if not pure_engine_contract:
        violations.append("player_center_or_graph_engine_has_side_effect_imports")
    if not app_contract:
        violations.append("player_center_route_or_api_not_integrated")
    if not template_contract:
        violations.append("player_center_template_contract_missing")
    if not visual_contract:
        violations.append("player_center_responsive_visual_contract_missing")
    if not registry_contract:
        violations.append("sports_platform_registry_not_updated_for_player_center")

    passed = not violations
    return {
        "issue_id": "PLAYER-CENTER-PREMIUM-EXPERIENCE",
        "version": app_version,
        "component": "player_center_premium_sports_identity",
        "affected_routes": ["/player/<id>", "/jugador/<id>", "/api/players/<id>/detail"],
        "cause": "Player Center must remain a Sports Core consumer, not an isolated player profile.",
        "solution": "Use Player Center context, Player Knowledge, Sports Graph, SHARK Intelligence and User Intelligence with honest fallbacks.",
        "evidence": {
            "engine_contract": engine_contract,
            "graph_contract": graph_contract,
            "knowledge_contract": knowledge_contract,
            "pure_engine_contract": pure_engine_contract,
            "app_contract": app_contract,
            "template_contract": template_contract,
            "visual_contract": visual_contract,
            "registry_contract": registry_contract,
            "violations": violations,
        },
        "preventive_rule": "Player Center cannot calculate a parallel model, use generative AI or invent player facts; it consumes Sports Core contracts only.",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }
def build_shark_intelligence_platform_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the SHARK Intelligence Platform contract without writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    application = _read("app.py")
    engine = _read("engines/shark_intelligence_platform_engine.py")
    template = _read("templates/shark_intelligence_center.html")
    css = _read("static/v933-product.css")
    platform_contracts = _read("engines/sports_platform_contracts.py")

    engine_contract = all(marker in engine for marker in (
        'SHARK_INTELLIGENCE_PLATFORM_CONTRACT = "SHARK-INTELLIGENCE-PLATFORM-V1"',
        "build_match_intelligence_consumer_view(",
        "SPORTS_DOMAIN_MODEL_CONTRACT",
        "SPORTS_KNOWLEDGE_LAYER_CONTRACT",
        "SPORTS_GRAPH_FOUNDATION_CONTRACT",
        '"database_writes": 0',
        '"external_calls": 0',
        '"telegram_sends": 0',
        '"stripe_calls": 0',
        '"generative_ai_calls": 0',
        '"no_fake_data": True',
        '"no_predictions": True',
    ))
    pure_engine_contract = not re.search(
        r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe)\b|\b(?:commit|execute|executemany)\s*\(",
        engine,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    app_contract = all(marker in application for marker in (
        "from engines.shark_intelligence_platform_engine import build_shark_intelligence_platform_snapshot",
        "def build_shark_intelligence_page_context(",
        "build_shark_intelligence_platform_snapshot(",
        '@app.route("/shark-intelligence")',
        '@app.route("/shark-intelligence-center")',
        '@app.route("/api/shark/intelligence")',
    ))
    template_contract = all(marker in template for marker in (
        'data-shark-intelligence-contract=',
        'data-sports-domain-model=',
        'data-sports-knowledge-contract=',
        'data-sports-graph-contract=',
        'data-match-intelligence-contract=',
        'data-shark-intelligence-section="claims"',
        'data-shark-intelligence-section="modules"',
        'data-shark-intelligence-section="sports-graph"',
        'data-shark-intelligence-section="transparency"',
        'No hay conversacion IA',
        'No disponible',
    ))
    visual_contract = all(marker in css for marker in (
        "SHARK INTELLIGENCE PLATFORM V1",
        ".shark-intelligence-v1",
        ".shark-intelligence-hero",
        ".shark-intelligence-layout",
        ".shark-intelligence-claim-grid",
        ".shark-intelligence-module-list",
        "@media (max-width: 980px)",
        "@media (max-width: 640px)",
    ))
    registry_contract = all(marker in platform_contracts for marker in (
        '"key": "shark_intelligence_platform"',
        '"contract": "SHARK-INTELLIGENCE-PLATFORM-V1"',
        '"key": "sports_graph"',
        '"contract": "SPORTS-GRAPH-FOUNDATION-RELATIONSHIPS-V1"',
    ))

    violations: list[str] = []
    if not engine_contract:
        violations.append("shark_intelligence_engine_not_using_sports_core_contracts")
    if not pure_engine_contract:
        violations.append("shark_intelligence_engine_has_side_effect_imports")
    if not app_contract:
        violations.append("shark_intelligence_route_or_api_not_integrated")
    if not template_contract:
        violations.append("shark_intelligence_template_contract_missing")
    if not visual_contract:
        violations.append("shark_intelligence_responsive_visual_contract_missing")
    if not registry_contract:
        violations.append("sports_platform_registry_not_updated_for_shark_intelligence")

    passed = not violations
    return {
        "issue_id": "SHARK-INTELLIGENCE-PLATFORM-CONTRACT",
        "version": app_version,
        "component": "shark_intelligence_platform",
        "affected_routes": ["/shark-intelligence", "/shark-intelligence-center", "/api/shark/intelligence"],
        "cause": "SHARK Intelligence must remain a Sports Core consumer, not a chatbot or an isolated analysis page.",
        "solution": "Use Sports Core, Sports Knowledge, Sports Graph and Match Intelligence with traceable claims and no generative actions.",
        "evidence": {
            "engine_contract": engine_contract,
            "pure_engine_contract": pure_engine_contract,
            "app_contract": app_contract,
            "template_contract": template_contract,
            "visual_contract": visual_contract,
            "registry_contract": registry_contract,
            "violations": violations,
        },
        "preventive_rule": "SHARK Intelligence cannot invent facts, predict without evidence or recalculate Sports Core context; every claim must expose source, evidence, freshness, quality and limitations.",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }
def build_user_intelligence_platform_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the User Intelligence Platform contract without writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    application = _read("app.py")
    engine = _read("engines/user_intelligence_platform_engine.py")
    template = _read("templates/user_intelligence_center.html")
    css = _read("static/v933-product.css")
    platform_contracts = _read("engines/sports_platform_contracts.py")

    engine_contract = all(marker in engine for marker in (
        'USER_INTELLIGENCE_PLATFORM_CONTRACT = "USER-INTELLIGENCE-PLATFORM-V1"',
        'USER_INTELLIGENCE_PRIVACY_CONTRACT = "USER-PRIVACY-CONTROLS-V1"',
        "sanitize_user_intelligence_preferences(",
        "build_user_privacy_state(",
        "build_user_intelligence_platform_snapshot(",
        "SPORTS_DOMAIN_MODEL_CONTRACT",
        "SPORTS_KNOWLEDGE_LAYER_CONTRACT",
        "SPORTS_GRAPH_FOUNDATION_CONTRACT",
        "MATCH_INTELLIGENCE_CONTRACT",
        "SHARK_INTELLIGENCE_PLATFORM_CONTRACT",
        '"database_writes_by_get": 0',
        '"external_calls": 0',
        '"telegram_sends": 0',
        '"stripe_calls": 0',
        '"generative_ai_calls": 0',
        '"third_party_exports": 0',
        '"fake_data_created": 0',
        '"no_generative_ai": True',
        '"user_controlled": True',
    ))
    pure_engine_contract = not re.search(
        r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe|openai)\b|\b(?:commit|execute|executemany)\s*\(",
        engine,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    app_contract = all(marker in application for marker in (
        "from engines.user_intelligence_platform_engine import (",
        "def build_user_intelligence_page_context(",
        "_load_user_intelligence_preferences(",
        "_save_user_intelligence_preferences(",
        "_delete_user_intelligence_profile(",
        "build_user_intelligence_platform_snapshot(",
        '@app.route("/user-intelligence")',
        '@app.route("/api/user-intelligence/summary")',
        '@app.route("/api/user-intelligence/export")',
        '@app.route("/api/user-intelligence/preferences", methods=["POST"])',
        '@app.route("/api/user-intelligence/profile", methods=["DELETE", "POST"])',
    ))
    template_contract = all(marker in template for marker in (
        'data-user-intelligence-contract=',
        'data-user-privacy-contract=',
        'data-sports-domain-model=',
        'data-sports-knowledge-contract=',
        'data-sports-graph-contract=',
        'data-shark-intelligence-contract=',
        'data-user-intelligence-section="privacy"',
        'data-user-intelligence-section="profile"',
        'data-user-intelligence-section="future-personalization"',
        'Activar',
        'Desactivar',
        'Resetear preferencias',
        'Borrar perfil',
        'data-user-privacy-control="enable"',
        'data-user-privacy-control="disable"',
        'data-user-privacy-control="reset"',
        'data-user-privacy-control="delete"',
        'No cambia la Home automaticamente',
    ))
    visual_contract = all(marker in css for marker in (
        "USER INTELLIGENCE PLATFORM V1",
        ".user-intelligence-v1",
        ".user-intelligence-hero",
        ".user-intelligence-layout",
        ".user-intelligence-signal-grid",
        ".user-intelligence-form-grid",
        "@media (max-width: 980px)",
        "@media (max-width: 640px)",
    ))
    registry_contract = all(marker in platform_contracts for marker in (
        '"key": "user_intelligence_platform"',
        '"contract": "USER-INTELLIGENCE-PLATFORM-V1"',
        '"key": "shark_intelligence_platform"',
        '"contract": "SHARK-INTELLIGENCE-PLATFORM-V1"',
    ))

    violations: list[str] = []
    if not engine_contract:
        violations.append("user_intelligence_engine_contract_missing")
    if not pure_engine_contract:
        violations.append("user_intelligence_engine_has_side_effect_imports")
    if not app_contract:
        violations.append("user_intelligence_routes_or_privacy_actions_missing")
    if not template_contract:
        violations.append("user_intelligence_template_privacy_contract_missing")
    if not visual_contract:
        violations.append("user_intelligence_responsive_visual_contract_missing")
    if not registry_contract:
        violations.append("sports_platform_registry_not_updated_for_user_intelligence")

    passed = not violations
    return {
        "issue_id": "USER-INTELLIGENCE-PLATFORM-CONTRACT",
        "version": app_version,
        "component": "user_intelligence_platform",
        "affected_routes": [
            "/user-intelligence",
            "/inteligencia-usuario",
            "/api/user-intelligence/summary",
            "/api/user-intelligence/export",
            "/api/user-intelligence/preferences",
            "/api/user-intelligence/profile",
        ],
        "cause": "User Intelligence must remain transparent, consent-based and first-party only.",
        "solution": "Consume existing sports contracts and user-owned activity/favorites, expose privacy controls, and avoid generative AI, third-party exports or automatic product changes.",
        "evidence": {
            "engine_contract": engine_contract,
            "pure_engine_contract": pure_engine_contract,
            "app_contract": app_contract,
            "template_contract": template_contract,
            "visual_contract": visual_contract,
            "registry_contract": registry_contract,
            "violations": violations,
        },
        "preventive_rule": "User Intelligence cannot infer unsupported preferences, export data to third parties, use generative AI, personalize automatically without consent, or hide disable/reset/delete/export controls.",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }

def build_sports_intelligence_gateway_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the Sports Intelligence Gateway contract without writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    engine = _read("engines/sports_intelligence_gateway_engine.py")
    platform_contracts = _read("engines/sports_platform_contracts.py")
    operating_system = _read("engines/project_operating_system_engine.py")

    engine_contract = all(marker in engine for marker in (
        'SPORTS_INTELLIGENCE_GATEWAY_CONTRACT = "SPORTS-INTELLIGENCE-GATEWAY-V1"',
        'SOURCE_REGISTRY_CONTRACT = "SOURCE-REGISTRY-V1"',
        'SOURCE_COMPLIANCE_CONTRACT = "SOURCE-COMPLIANCE-SYSTEM-V1"',
        'SOURCE_HEALTH_CONTRACT = "SOURCE-HEALTH-MONITOR-V1"',
        'SOURCE_EVIDENCE_CONTRACT = "SOURCE-EVIDENCE-REGISTRY-V1"',
        "register_source(",
        "evaluate_source_compliance(",
        "build_source_health(",
        "build_source_evidence_record(",
        "build_sports_intelligence_gateway_snapshot(",
        '"must_register_before_use": True',
        '"must_approve_before_use": True',
        '"mass_scraping_allowed": False',
        '"robots_bypass_allowed": False',
        '"paywall_bypass_allowed": False',
        '"article_copying_allowed": False',
        '"protected_image_reuse_allowed": False',
        '"unlicensed_content_reuse_allowed": False',
        '"provenance_required": True',
        '"freshness_required": True',
        '"evidence_required": True',
        '"quality_required": True',
        '"limitations_required": True',
        '"external_calls": 0',
        '"database_writes": 0',
        '"telegram_sends": 0',
        '"stripe_calls": 0',
        '"provider_connections_enabled": 0',
        '"automatic_source_approval": 0',
    ))
    pure_engine_contract = not re.search(
        r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe|openai|bs4|selenium|playwright)\b|\b(?:commit|execute|executemany|urlopen|Session)\s*\(",
        engine,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    registry_contract = all(marker in platform_contracts for marker in (
        '"key": "sports_intelligence_gateway"',
        '"contract": "SPORTS-INTELLIGENCE-GATEWAY-V1"',
        '"implementation": "engines/sports_intelligence_gateway_engine.py"',
    ))
    roadmap_contract = all(marker in operating_system for marker in (
        '"name": "Sports Intelligence Gateway"',
        '"engines/sports_intelligence_gateway_engine.py"',
        '"tools/check_sports_intelligence_gateway.py"',
    ))

    violations: list[str] = []
    if not engine_contract:
        violations.append("sports_intelligence_gateway_contract_missing")
    if not pure_engine_contract:
        violations.append("sports_intelligence_gateway_has_side_effect_imports_or_calls")
    if not registry_contract:
        violations.append("sports_platform_registry_not_updated_for_gateway")
    if not roadmap_contract:
        violations.append("company_roadmap_not_updated_for_gateway")

    passed = not violations
    return {
        "issue_id": "SPORTS-INTELLIGENCE-GATEWAY-CONTRACT",
        "version": app_version,
        "component": "sports_intelligence_gateway",
        "affected_routes": ["/admin/developer-center", "/admin/company-board", "/admin/company-os"],
        "cause": "Sports data sources must enter NeMeSiS through a legal registry, compliance review, health state and evidence envelope before any use.",
        "solution": "Keep the Gateway read-only, require registration and approval before connection, and block scraping, paywall bypasses, article copying and protected image reuse.",
        "evidence": {
            "engine_contract": engine_contract,
            "pure_engine_contract": pure_engine_contract,
            "registry_contract": registry_contract,
            "roadmap_contract": roadmap_contract,
            "violations": violations,
        },
        "preventive_rule": "No sports source may be connected, scraped or commercially reused until registered, compliance-approved, attribution-reviewed and wrapped with provenance, freshness, evidence, quality and limitations.",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }
def build_decision_engine_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the Decision Engine evidence-first contract without writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    engine = _read("engines/decision_engine.py")
    platform_contracts = _read("engines/sports_platform_contracts.py")
    operating_system = _read("engines/project_operating_system_engine.py")

    engine_contract = all(marker in engine for marker in (
        'DECISION_ENGINE_CONTRACT = "NEMESIS-DECISION-ENGINE-EVIDENCE-FIRST-V1"',
        'DECISION_EVIDENCE_CONTRACT = "NEMESIS-DECISION-EVIDENCE-ITEM-V1"',
        'DECISION_QUESTION_CONTRACT = "NEMESIS-DECISION-QUESTION-ANSWER-V1"',
        "SPORTS_DOMAIN_MODEL_CONTRACT",
        "SPORTS_KNOWLEDGE_LAYER_CONTRACT",
        "SPORTS_GRAPH_FOUNDATION_CONTRACT",
        "MATCH_INTELLIGENCE_CONTRACT",
        "SHARK_INTELLIGENCE_PLATFORM_CONTRACT",
        "SPORTS_INTELLIGENCE_GATEWAY_CONTRACT",
        "USER_INTELLIGENCE_PLATFORM_CONTRACT",
        "build_decision_engine_snapshot(",
        "collect_decision_evidence(",
        "compare_source_claims(",
        '"what_we_know"',
        '"what_we_do_not_know"',
        '"what_evidence_exists"',
        '"what_evidence_is_missing"',
        '"what_changed"',
        '"which_sources_align"',
        '"which_sources_disagree"',
        '"data_quality"',
        '"confidence"',
        '"external_calls": 0',
        '"database_writes": 0',
        '"telegram_sends": 0',
        '"stripe_calls": 0',
        '"generative_ai_calls": 0',
        '"picks_created": 0',
        '"predictions_created": 0',
        '"automatic_actions": 0',
        '"fake_data_created": 0',
    ))
    pure_engine_contract = not re.search(
        r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe|openai|bs4|selenium|playwright)\b|\b(?:commit|execute|executemany|urlopen|Session)\s*\(",
        engine,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    registry_contract = all(marker in platform_contracts for marker in (
        '"key": "decision_engine"',
        '"contract": "NEMESIS-DECISION-ENGINE-EVIDENCE-FIRST-V1"',
        '"implementation": "engines/decision_engine.py"',
    ))
    roadmap_contract = all(marker in operating_system for marker in (
        '"name": "Decision Engine"',
        '"engines/decision_engine.py"',
        '"tools/check_decision_engine.py"',
    ))

    violations: list[str] = []
    if not engine_contract:
        violations.append("decision_engine_contract_missing")
    if not pure_engine_contract:
        violations.append("decision_engine_has_side_effect_imports_or_calls")
    if not registry_contract:
        violations.append("sports_platform_registry_not_updated_for_decision_engine")
    if not roadmap_contract:
        violations.append("company_roadmap_not_updated_for_decision_engine")

    passed = not violations
    return {
        "issue_id": "NEMESIS-DECISION-ENGINE-CONTRACT",
        "version": app_version,
        "component": "decision_engine",
        "affected_routes": ["/admin/developer-center", "/admin/company-board", "/admin/company-os"],
        "cause": "Decision Engine must organize evidence from canonical NeMeSiS contracts without becoming AI, a pick engine or a parallel data source.",
        "solution": "Consume Sports Core, Sports Knowledge, Sports Graph, Match Intelligence, SHARK, Gateway and User Intelligence, preserving provenance, evidence, freshness, quality and limitations for every answer.",
        "evidence": {
            "engine_contract": engine_contract,
            "pure_engine_contract": pure_engine_contract,
            "registry_contract": registry_contract,
            "roadmap_contract": roadmap_contract,
            "violations": violations,
        },
        "preventive_rule": "Decision Engine cannot invent facts, create picks, predict outcomes, call AI/providers or hide uncertainty; every answer must remain evidence-backed and approval-gated for future consumers.",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }
def build_experience_platform_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the Experience Platform contract without writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    engine = _read("engines/experience_platform_engine.py")
    platform_contracts = _read("engines/sports_platform_contracts.py")
    operating_system = _read("engines/project_operating_system_engine.py")
    tool = _read("tools/check_experience_platform.py")

    engine_contract = all(marker in engine for marker in (
        'EXPERIENCE_PLATFORM_CONTRACT = "NEMESIS-EXPERIENCE-PLATFORM-V1"',
        'EXPERIENCE_AUDITOR_CONTRACT = "NEMESIS-EXPERIENCE-AUDITOR-V1"',
        'PRODUCT_POLISH_CONTRACT = "NEMESIS-PRODUCT-POLISH-ENGINE-V1"',
        'UX_CONSISTENCY_CONTRACT = "NEMESIS-UX-CONSISTENCY-CHECKER-V1"',
        'NAVIGATION_INTEGRITY_CONTRACT = "NEMESIS-NAVIGATION-INTEGRITY-CHECKER-V1"',
        'VISUAL_DENSITY_CONTRACT = "NEMESIS-VISUAL-DENSITY-AUDITOR-V1"',
        "collect_screen_inventory(",
        "run_navigation_integrity_checker(",
        "run_ux_consistency_checker(",
        "run_visual_density_auditor(",
        "build_product_polish_portfolio(",
        "build_experience_platform_snapshot(",
        '"external_calls": 0',
        '"database_writes": 0',
        '"telegram_sends": 0',
        '"stripe_calls": 0',
        '"generative_ai_calls": 0',
        '"automatic_ui_changes": 0',
        '"sports_core_changes": 0',
        '"shark_logic_changes": 0',
        '"new_api_routes": 0',
    ))
    pure_engine_contract = not re.search(
        r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe|openai|bs4|selenium|playwright|subprocess)\b|\b(?:commit|execute|executemany|urlopen|Session)\s*\(",
        engine,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    registry_contract = all(marker in platform_contracts for marker in (
        '"key": "experience_platform"',
        '"contract": "NEMESIS-EXPERIENCE-PLATFORM-V1"',
        '"implementation": "engines/experience_platform_engine.py + tools/check_experience_platform.py"',
    ))
    roadmap_contract = all(marker in operating_system for marker in (
        '"name": "Experience Platform"',
        '"engines/experience_platform_engine.py"',
        '"tools/check_experience_platform.py"',
    ))
    report_contract = all(marker in tool for marker in (
        "EXPERIENCE_PLATFORM_REPORT.md",
        "PRODUCT_POLISH_REPORT.md",
        "UX_CONSISTENCY_REPORT.md",
        "VISUAL_AUDIT_REPORT.md",
    ))

    violations: list[str] = []
    if not engine_contract:
        violations.append("experience_platform_contract_missing")
    if not pure_engine_contract:
        violations.append("experience_platform_has_side_effect_imports_or_calls")
    if not registry_contract:
        violations.append("sports_platform_registry_not_updated_for_experience_platform")
    if not roadmap_contract:
        violations.append("company_roadmap_not_updated_for_experience_platform")
    if not report_contract:
        violations.append("experience_reports_not_declared")

    passed = not violations
    return {
        "issue_id": "NEMESIS-EXPERIENCE-PLATFORM-CONTRACT",
        "version": app_version,
        "component": "experience_platform",
        "affected_routes": ["/admin/developer-center", "/admin/company-board", "/app", "/calendario", "/shark-intelligence", "/user-intelligence"],
        "cause": "NeMeSiS needs a permanent product-experience audit layer that improves UX without creating new product logic, APIs, AI or data sources.",
        "solution": "Keep Experience Auditor, Product Polish, UX Consistency, Navigation Integrity and Visual Density checks read-only, evidence-based and approval-gated before any UI change.",
        "evidence": {
            "engine_contract": engine_contract,
            "pure_engine_contract": pure_engine_contract,
            "registry_contract": registry_contract,
            "roadmap_contract": roadmap_contract,
            "report_contract": report_contract,
            "violations": violations,
        },
        "preventive_rule": "No polish change may bypass Browser QA, Sentinel and human approval; the Experience Platform cannot mutate Sports Core, SHARK, DB, Telegram, Stripe, routes or APIs.",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }

def build_action_platform_contract_snapshot(
    root: str | Path | None = None,
    app_version: str = "",
) -> dict[str, Any]:
    """Inspect the Action Platform personal sports experience contract without writes."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _read(relative_path: str) -> str:
        try:
            return (project_root / relative_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    app_text = _read("app.py")
    template = _read("templates/action_platform.html")
    platform_contracts = _read("engines/sports_platform_contracts.py")
    operating_system = _read("engines/project_operating_system_engine.py")
    tool = _read("tools/check_action_platform.py")
    legacy_engine_exists = (project_root / "engines/action_platform_engine.py").exists()

    app_contract = all(marker in app_text for marker in (
        'ACTION_PLATFORM_CONTRACT = "NEMESIS-ACTION-PLATFORM-PERSONAL-SPORTS-EXPERIENCE-V1"',
        "build_action_platform_snapshot(",
        "build_decision_engine_snapshot(",
        "build_user_intelligence_platform_snapshot(",
        "build_sports_intelligence_gateway_snapshot(",
        "build_shark_intelligence_platform_snapshot(",
        '"/smart-home"',
        '"/smart-favorites"',
        '"/watchlist"',
        '"/alert-center"',
        '"/daily-briefing"',
        '"/evening-recap"',
        '"/activity-center"',
        '"/decision-history"',
        '"external_calls": 0',
        '"database_writes_by_get": 0',
        '"telegram_sends": 0',
        '"stripe_calls": 0',
        '"generative_ai_calls": 0',
        '"predictions_created": 0',
        '"betting_recommendations_created": 0',
        '"automatic_user_decisions": 0',
    ))
    template_contract = all(marker in template for marker in (
        "data-action-platform-contract",
        "Smart Home",
        "Smart Favorites",
        "Watchlist",
        "Alert Center",
        "Daily Briefing",
        "Evening Recap",
        "Activity Center",
        "Decision History",
        "Procedencia",
        "Evidencia",
        "Frescura",
        "Calidad",
        "Limitaciones",
        "No hay recomendaciones de apuestas ni predicciones nuevas.",
    ))
    registry_contract = all(marker in platform_contracts for marker in (
        '"key": "action_platform"',
        '"contract": "NEMESIS-ACTION-PLATFORM-PERSONAL-SPORTS-EXPERIENCE-V1"',
        '"implementation": "app.py + templates/action_platform.html + tools/check_action_platform.py"',
    ))
    roadmap_contract = all(marker in operating_system for marker in (
        '"name": "Action Platform"',
        '"templates/action_platform.html"',
        '"tools/check_action_platform.py"',
    ))
    tool_contract = all(marker in tool for marker in (
        "ACTION_PLATFORM_REPORT.md",
        "NEMESIS-ACTION-PLATFORM-PERSONAL-SPORTS-EXPERIENCE-V1",
        "engines/action_platform_engine.py",
        "database_writes_by_get",
        "betting_recommendations_created",
    ))

    violations: list[str] = []
    if legacy_engine_exists:
        violations.append("action_platform_engine_created_instead_of_reusing_existing_engines")
    if not app_contract:
        violations.append("action_platform_app_contract_missing")
    if not template_contract:
        violations.append("action_platform_template_transparency_missing")
    if not registry_contract:
        violations.append("sports_platform_registry_not_updated_for_action_platform")
    if not roadmap_contract:
        violations.append("company_roadmap_not_updated_for_action_platform")
    if not tool_contract:
        violations.append("action_platform_check_missing")

    passed = not violations
    return {
        "issue_id": "NEMESIS-ACTION-PLATFORM-CONTRACT",
        "version": app_version,
        "component": "action_platform",
        "affected_routes": ["/smart-home", "/smart-favorites", "/watchlist", "/alert-center", "/daily-briefing", "/evening-recap", "/activity-center", "/decision-history"],
        "cause": "Action Platform must personalize the sports experience by composing existing NeMeSiS engines without becoming AI, a betting recommender or a parallel data source.",
        "solution": "Keep Smart Home, Smart Favorites, Watchlist, Alert Center, Daily Briefing, Evening Recap, Activity Center and Decision History evidence-first, read-only on GET and transparent about source, evidence, freshness, quality and limitations.",
        "evidence": {
            "legacy_engine_absent": not legacy_engine_exists,
            "app_contract": app_contract,
            "template_contract": template_contract,
            "registry_contract": registry_contract,
            "roadmap_contract": roadmap_contract,
            "tool_contract": tool_contract,
            "violations": violations,
        },
        "preventive_rule": "Action Platform cannot create an action_platform_engine, invent facts, create picks, predict outcomes, send Telegram, call Stripe/providers, write DB on GET or hide provenance/evidence/freshness/quality/limitations.",
        "validation_result": "PASS" if passed else "REGRESSION",
        "certification_state": "VERIFIED" if passed else "REQUIRES_REVIEW",
        "status": "RESOLVED_LOCALLY" if passed else "OPEN",
        "evaluated_at_madrid": _now(),
        "autofix_allowed": False,
        "approval_required": True,
        "production_certified": False,
    }

def detect_product_quality_contract_issues(
    root: str | Path | None = None,
    app_version: str = "",
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    snapshot = build_customer_trust_icon_contract_snapshot(root, app_version)
    if snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "Iconos de confianza heredan la caja del chip",
            "visual_layout",
            "medium",
            "/app",
            "PQV939-005; rutas=/app,/picks,/shark,/track-record,/partido/<id>; "
            + ",".join(snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "PQV939-005-CUSTOMER-TRUST-ICON-CONTRACT",
            "profile": "CLIENT",
            "description": "Los iconos internos reciben estilos de chip y pueden mostrarse como cajas vacias.",
            "expected_behavior": "Cada SVG conserva 14 x 14 px sin padding, borde ni fondo heredados.",
            "actual_behavior": "El contrato CSS del componente no aisla correctamente el icono interno.",
            "suggested_fix": "Limitar los estilos del chip a .v935-customer-trust-rules > span y repetir Browser QA.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "static/v933-product.css",
                "templates/components/v933_ui.html",
            ],
            "codex_prompt_suggestion": (
                "Revisar PQV939-005 en el panel de confianza, corregir solo el selector compartido y "
                "validar desktop/movil. No autoaplicar CSS ni DOM."
            ),
            "product_quality_contract": snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))

    copy_snapshot = build_client_copy_audience_contract_snapshot(root, app_version)
    if copy_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "Lenguaje tecnico interno visible al cliente",
            "copy",
            "medium",
            "/live",
            "PQV939-006; rutas=/,/app,/calendar,/live,/picks; "
            + ",".join(copy_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "PQV939-006-CLIENT-COPY-AUDIENCE-CONTRACT",
            "priority": "P2",
            "profile": "CLIENT",
            "description": "El cliente recibe terminos de implementacion en mensajes de disponibilidad deportiva.",
            "expected_behavior": "El cliente entiende disponibilidad y frescura; el diagnostico tecnico permanece en admin.",
            "actual_behavior": "El contrato de audiencia permite mostrar DB, cache o render en copy cliente.",
            "suggested_fix": "Separar copy cliente/admin en el macro compartido y repetir Browser QA con polling.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "engines/v934_realtime_sports_engine.py",
                "templates/components/v933_ui.html",
                "static/v934-realtime.js",
                "templates/live.html",
            ],
            "codex_prompt_suggestion": (
                "Revisar PQV939-006, mantener diagnostico tecnico solo en admin y validar render inicial "
                "y polling cliente. No cambiar datos, APIs externas ni arquitectura."
            ),
            "product_quality_contract": copy_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))

    timestamp_snapshot = build_madrid_timestamp_presentation_contract_snapshot(root, app_version)
    if timestamp_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "Fecha de sincronización ISO visible al cliente",
            "copy",
            "medium",
            "/",
            "PQV939-007; rutas=/,/app,/calendar,/live,/picks,/match/<id>; "
            + ",".join(timestamp_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "PQV939-007-MADRID-TIMESTAMP-PRESENTATION-CONTRACT",
            "priority": "P2",
            "profile": "CLIENT",
            "component": "madrid_sync_timestamp_presentation",
            "description": "Una marca ISO de máquina puede volver a mostrarse como texto visible al cliente.",
            "expected_behavior": "El cliente ve una fecha Madrid legible y el ISO permanece disponible solo como evidencia técnica.",
            "actual_behavior": "El contrato de presentación de fecha Madrid está incompleto o fue modificado.",
            "suggested_fix": "Restaurar el formateador compartido y validar render inicial, polling y modo admin técnico.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "engines/madrid_time_engine.py",
                "engines/v934_realtime_sports_engine.py",
                "app.py",
                "templates/components/v933_ui.html",
                "static/v934-realtime.js",
            ],
            "codex_prompt_suggestion": (
                "Revisar PQV939-007, mantener el ISO solo como evidencia de máquina/admin y restaurar "
                "la etiqueta Madrid cliente. Validar desktop, móvil y polling. No autoaplicar código."
            ),
            "product_quality_contract": timestamp_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    version_match = re.match(r"^V(\d+)", str(app_version or ""))
    calendar_contract_required = bool(version_match and int(version_match.group(1)) >= 940)
    calendar_snapshot = (
        build_v940_calendar_experience_contract_snapshot(root, app_version)
        if calendar_contract_required
        else None
    )
    if calendar_snapshot and calendar_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "El Calendario pierde su contrato de descubrimiento",
            "navigation",
            "medium",
            "/calendar",
            "V940 Calendar; " + ",".join(calendar_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "V940-CALENDAR-EXPERIENCE-CONTRACT",
            "priority": "P1",
            "profile": "CLIENT",
            "component": "calendar_discovery_experience",
            "description": "El Calendario deja de conservar una fuente, capas o contexto canonicos.",
            "expected_behavior": (
                "Pagina y API comparten snapshot, filtros reversibles, indices y match_card canonica."
            ),
            "actual_behavior": "Una o mas garantias del contrato V940 no se pueden demostrar.",
            "suggested_fix": (
                "Restaurar solo el contrato incumplido y repetir tests y Browser QA desktop/movil."
            ),
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "app.py",
                "templates/calendar.html",
                "static/v933-product.css",
                "static/v940-calendar.js",
            ],
            "codex_prompt_suggestion": (
                "Revisar el contrato V940 del Calendario con la evidencia indicada. "
                "No autoaplicar DOM, CSS, datos ni rutas; preservar sports-metrics-v1 y match_card()."
            ),
            "product_quality_contract": calendar_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    match_center_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    match_center_present = (
        (match_center_root / "engines/match_context_engine.py").exists()
        or (match_center_root / "templates/components/v944_match_center.html").exists()
    )
    match_center_snapshot = (
        build_v944_match_center_foundation_contract_snapshot(root, app_version)
        if match_center_present
        else None
    )
    if match_center_snapshot and match_center_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "El Match Center pierde su contrato de contexto único",
            "sports_data_contract",
            "high",
            "/match/<id>",
            "V944 Match Center; " + ",".join(match_center_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "V944-MATCH-CENTER-FOUNDATION-CONTRACT",
            "priority": "P1",
            "profile": "CLIENT",
            "component": "match_center_foundation",
            "description": "Una región del partido ha dejado de compartir contexto, estado o fallback canónico.",
            "expected_behavior": "Diez componentes consumen un MatchContext puro, responsive y sin efectos laterales.",
            "actual_behavior": "Una o más garantías de MATCH-CENTER-LIFECYCLE-STORY-V1 no se pueden demostrar.",
            "suggested_fix": "Restaurar solo el contrato incumplido y repetir tests y Browser QA en tres viewports.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "engines/match_context_engine.py",
                "engines/match_intelligence_engine.py",
                "engines/shark_context_presentation_engine.py",
                "engines/telegram_intelligence_engine.py",
                "app.py",
                "templates/match_detail.html",
                "templates/components/v944_match_center.html",
                "static/v933-product.css",
            ],
            "codex_prompt_suggestion": (
                "Revisar el contrato V944 del Match Center usando la evidencia indicada. "
                "No autoaplicar Python, Jinja, CSS, datos ni rutas; conservar la API y MATCH-CENTER-LIFECYCLE-STORY-V1."
            ),
            "product_quality_contract": match_center_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    team_center_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    team_center_present = (
        (team_center_root / "engines/team_center_engine.py").exists()
        or (team_center_root / "templates/team_detail.html").exists()
    )
    team_center_snapshot = (
        build_team_center_experience_contract_snapshot(root, app_version)
        if team_center_present
        else None
    )
    if team_center_snapshot and team_center_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "El Team Center pierde su contrato Sports Core",
            "sports_data_contract",
            "high",
            "/team/<id>",
            "Team Center; " + ",".join(team_center_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "TEAM-CENTER-PREMIUM-EXPERIENCE-CONTRACT",
            "priority": "P1",
            "profile": "CLIENT",
            "component": "team_center_premium_club_experience",
            "description": "El Team Center deja de consumir Sports Core, Sports Knowledge, Sports Graph o match_card canonica.",
            "expected_behavior": "Una unica experiencia premium del club basada en contratos canonicos, datos reales y fallbacks honestos.",
            "actual_behavior": "Una o mas garantias del contrato Team Center no se pueden demostrar.",
            "suggested_fix": "Restaurar solo el contrato incumplido y repetir Browser QA desktop/tablet/mobile.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "engines/team_center_engine.py",
                "engines/sports_graph_foundation_engine.py",
                "app.py",
                "templates/team_detail.html",
                "static/v933-product.css",
                "engines/sports_platform_contracts.py",
            ],
            "codex_prompt_suggestion": (
                "Revisar Team Center con la evidencia indicada. No autoaplicar Python, Jinja, CSS, datos ni rutas; "
                "preservar Sports Core, Sports Knowledge Layer, Sports Graph y match_card()."
            ),
            "product_quality_contract": team_center_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    competition_center_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    competition_center_present = (
        (competition_center_root / "engines/competition_center_engine.py").exists()
        or (competition_center_root / "templates/competition_detail.html").exists()
    )
    competition_center_snapshot = (
        build_competition_center_experience_contract_snapshot(root, app_version)
        if competition_center_present
        else None
    )
    if competition_center_snapshot and competition_center_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "El Competition Center pierde su contrato Sports Core",
            "sports_data_contract",
            "high",
            "/competition/<id>",
            "Competition Center; " + ",".join(competition_center_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "COMPETITION-CENTER-PREMIUM-EXPERIENCE-CONTRACT",
            "priority": "P1",
            "profile": "CLIENT",
            "component": "competition_center_premium_league_intelligence",
            "description": "El Competition Center deja de consumir Sports Core, Sports Knowledge, Sports Graph o match_card canonica.",
            "expected_behavior": "Una unica experiencia premium de competicion basada en contratos canonicos, datos reales y fallbacks honestos.",
            "actual_behavior": "Una o mas garantias del contrato Competition Center no se pueden demostrar.",
            "suggested_fix": "Restaurar solo el contrato incumplido y repetir Browser QA desktop/tablet/mobile.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "engines/competition_center_engine.py",
                "engines/sports_graph_foundation_engine.py",
                "app.py",
                "templates/competition_detail.html",
                "static/v933-product.css",
                "engines/sports_platform_contracts.py",
            ],
            "codex_prompt_suggestion": (
                "Revisar Competition Center con la evidencia indicada. No autoaplicar Python, Jinja, CSS, datos ni rutas; "
                "preservar Sports Core, Sports Knowledge Layer, Sports Graph y match_card()."
            ),
            "product_quality_contract": competition_center_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    player_center_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    player_center_present = (
        (player_center_root / "engines/player_center_engine.py").exists()
        or (player_center_root / "templates/player_detail.html").exists()
    )
    player_center_snapshot = (
        build_player_center_experience_contract_snapshot(root, app_version)
        if player_center_present
        else None
    )
    if player_center_snapshot and player_center_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "El Player Center pierde su contrato Sports Core",
            "sports_data_contract",
            "high",
            "/player/<id>",
            "Player Center; " + ",".join(player_center_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "PLAYER-CENTER-PREMIUM-EXPERIENCE-CONTRACT",
            "priority": "P1",
            "profile": "CLIENT",
            "component": "player_center_premium_sports_identity",
            "description": "El Player Center deja de consumir Sports Core, Sports Knowledge, Sports Graph, SHARK Intelligence o User Intelligence.",
            "expected_behavior": "Una unica experiencia premium del jugador basada en contratos canonicos, datos reales y fallbacks honestos.",
            "actual_behavior": "Una o mas garantias del contrato Player Center no se pueden demostrar.",
            "suggested_fix": "Restaurar solo el contrato incumplido y repetir Browser QA desktop/tablet/mobile.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "engines/player_center_engine.py",
                "engines/sports_knowledge_layer_engine.py",
                "engines/sports_graph_foundation_engine.py",
                "app.py",
                "templates/player_detail.html",
                "static/v933-product.css",
                "engines/sports_platform_contracts.py",
            ],
            "codex_prompt_suggestion": (
                "Revisar Player Center con la evidencia indicada. No autoaplicar Python, Jinja, CSS, datos ni rutas; "
                "preservar Sports Core, Sports Knowledge Layer, Sports Graph, SHARK Intelligence y User Intelligence."
            ),
            "product_quality_contract": player_center_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    shark_intelligence_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    shark_intelligence_present = (
        (shark_intelligence_root / "engines/shark_intelligence_platform_engine.py").exists()
        or (shark_intelligence_root / "templates/shark_intelligence_center.html").exists()
    )
    shark_intelligence_snapshot = (
        build_shark_intelligence_platform_contract_snapshot(root, app_version)
        if shark_intelligence_present
        else None
    )
    if shark_intelligence_snapshot and shark_intelligence_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "SHARK Intelligence pierde su contrato Sports Core",
            "sports_data_contract",
            "medium",
            "/shark-intelligence",
            "SHARK Intelligence; " + ",".join(shark_intelligence_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "SHARK-INTELLIGENCE-PLATFORM-CONTRACT",
            "priority": "P2",
            "profile": "CLIENT",
            "component": "shark_intelligence_platform",
            "description": "SHARK Intelligence deja de consumir contratos canonicos o pierde trazabilidad por afirmacion.",
            "expected_behavior": "Centro de inteligencia deportiva basado en Sports Core, Sports Knowledge, Sports Graph y Match Intelligence, sin IA generativa ni datos inventados.",
            "actual_behavior": "Una o mas garantias del contrato SHARK Intelligence no se pueden demostrar.",
            "suggested_fix": "Restaurar solo el contrato incumplido y repetir Browser QA desktop/tablet/mobile.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "engines/shark_intelligence_platform_engine.py",
                "app.py",
                "templates/shark_intelligence_center.html",
                "static/v933-product.css",
                "engines/sports_platform_contracts.py",
            ],
            "codex_prompt_suggestion": (
                "Revisar SHARK Intelligence Platform con la evidencia indicada. No autoaplicar Python, Jinja, CSS, datos ni rutas; "
                "preservar Sports Core, Sports Knowledge, Sports Graph y Match Intelligence sin IA generativa."
            ),
            "product_quality_contract": shark_intelligence_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    user_intelligence_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    user_intelligence_present = (
        (user_intelligence_root / "engines/user_intelligence_platform_engine.py").exists()
        or (user_intelligence_root / "templates/user_intelligence_center.html").exists()
    )
    user_intelligence_snapshot = (
        build_user_intelligence_platform_contract_snapshot(root, app_version)
        if user_intelligence_present
        else None
    )
    if user_intelligence_snapshot and user_intelligence_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "User Intelligence pierde controles de privacidad",
            "privacy_contract",
            "medium",
            "/user-intelligence",
            "User Intelligence; " + ",".join(user_intelligence_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "USER-INTELLIGENCE-PLATFORM-CONTRACT",
            "priority": "P2",
            "profile": "CLIENT",
            "component": "user_intelligence_platform",
            "description": "User Intelligence deja de ser transparente, consent-based o first-party only.",
            "expected_behavior": "Perfil deportivo interno con consentimiento, exportacion, reset, borrado, desactivacion y cero terceros/IA generativa.",
            "actual_behavior": "Una o mas garantias del contrato User Intelligence no se pueden demostrar.",
            "suggested_fix": "Restaurar solo el contrato incumplido y repetir Privacy Guard y Browser QA desktop/tablet/mobile.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "engines/user_intelligence_platform_engine.py",
                "app.py",
                "templates/user_intelligence_center.html",
                "static/v933-product.css",
                "engines/sports_platform_contracts.py",
            ],
            "codex_prompt_suggestion": (
                "Revisar User Intelligence Platform con la evidencia indicada. No autoaplicar Python, Jinja, CSS, datos ni rutas; "
                "preservar consentimiento, exportacion, reset, borrado, desactivacion y cero terceros/IA generativa."
            ),
            "product_quality_contract": user_intelligence_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    gateway_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    gateway_present = (gateway_root / "engines/sports_intelligence_gateway_engine.py").exists()
    gateway_snapshot = (
        build_sports_intelligence_gateway_contract_snapshot(root, app_version)
        if gateway_present
        else None
    )
    if gateway_snapshot and gateway_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "Sports Intelligence Gateway pierde su contrato legal de fuentes",
            "sports_data_contract",
            "high",
            "/admin/developer-center",
            "Sports Intelligence Gateway; " + ",".join(gateway_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "SPORTS-INTELLIGENCE-GATEWAY-CONTRACT",
            "priority": "P1",
            "profile": "ADMIN",
            "component": "sports_intelligence_gateway",
            "description": "Una fuente deportiva podria usarse sin registro, compliance, salud o evidencia legal suficiente.",
            "expected_behavior": "Toda fuente se registra, revisa legalmente, permanece desconectada hasta aprobacion y expone procedencia, frescura, evidencia, calidad y limitaciones.",
            "actual_behavior": "Una o mas garantias del contrato Gateway no se pueden demostrar.",
            "suggested_fix": "Restaurar solo el contrato incumplido y repetir Source Compliance, Secret/Privacy Guard y Sentinel.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "engines/sports_intelligence_gateway_engine.py",
                "engines/sports_platform_contracts.py",
                "engines/project_operating_system_engine.py",
                "tools/check_sports_intelligence_gateway.py",
            ],
            "codex_prompt_suggestion": (
                "Revisar Sports Intelligence Gateway con la evidencia indicada. No conectar fuentes, no hacer scraping, "
                "no llamar APIs, no copiar articulos ni imagenes protegidas y conservar aprobacion humana obligatoria."
            ),
            "product_quality_contract": gateway_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    decision_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    decision_present = (decision_root / "engines/decision_engine.py").exists()
    decision_snapshot = (
        build_decision_engine_contract_snapshot(root, app_version)
        if decision_present
        else None
    )
    if decision_snapshot and decision_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "Decision Engine pierde su contrato evidence-first",
            "sports_data_contract",
            "high",
            "/admin/developer-center",
            "Decision Engine; " + ",".join(decision_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "NEMESIS-DECISION-ENGINE-CONTRACT",
            "priority": "P1",
            "profile": "ADMIN",
            "component": "decision_engine",
            "description": "El motor de decisiones podria inventar datos, ocultar incertidumbre, crear picks o convertirse en fuente paralela.",
            "expected_behavior": "Organiza evidencia canonica y responde que se sabe, que falta, cambios, coincidencias, discrepancias, calidad y confianza sin IA ni predicciones.",
            "actual_behavior": "Una o mas garantias del contrato Decision Engine no se pueden demostrar.",
            "suggested_fix": "Restaurar solo el contrato incumplido y repetir Decision Engine check, Sentinel y Privacy Guard.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "engines/decision_engine.py",
                "engines/sports_platform_contracts.py",
                "engines/project_operating_system_engine.py",
                "tools/check_decision_engine.py",
            ],
            "codex_prompt_suggestion": (
                "Revisar Decision Engine con la evidencia indicada. No crear IA, predicciones, picks, llamadas externas "
                "ni datos nuevos; conservar procedencia, evidencia, frescura, calidad y limitaciones en cada respuesta."
            ),
            "product_quality_contract": decision_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    experience_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    experience_present = (experience_root / "engines/experience_platform_engine.py").exists()
    experience_snapshot = (
        build_experience_platform_contract_snapshot(root, app_version)
        if experience_present
        else None
    )
    if experience_snapshot and experience_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "Experience Platform pierde su contrato de pulido UX seguro",
            "visual_layout",
            "medium",
            "/admin/developer-center",
            "Experience Platform; " + ",".join(experience_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "NEMESIS-EXPERIENCE-PLATFORM-CONTRACT",
            "priority": "P2",
            "profile": "CLIENT_ADMIN",
            "component": "experience_platform",
            "description": "La capa de experiencia podria dejar de auditar UX, navegacion o densidad de forma segura y read-only.",
            "expected_behavior": "Auditoria de pantallas, consistencia UX, navegacion y densidad visual sin cambiar logica, Sports Core, SHARK, DB, Telegram, Stripe, rutas ni APIs.",
            "actual_behavior": "Una o mas garantias del contrato Experience Platform no se pueden demostrar.",
            "suggested_fix": "Restaurar solo el contrato incumplido y repetir Experience Platform check, Browser QA, Sentinel y Privacy Guard.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "engines/experience_platform_engine.py",
                "engines/sports_platform_contracts.py",
                "engines/project_operating_system_engine.py",
                "tools/check_experience_platform.py",
            ],
            "codex_prompt_suggestion": (
                "Revisar Experience Platform con la evidencia indicada. No crear nuevas APIs, IA ni motores deportivos; "
                "no modificar Sports Core, SHARK, DB, Telegram, Stripe o produccion; conservar Browser QA y aprobacion humana."
            ),
            "product_quality_contract": experience_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    action_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    action_present = (action_root / "templates/action_platform.html").exists()
    action_snapshot = (
        build_action_platform_contract_snapshot(root, app_version)
        if action_present
        else None
    )
    if action_snapshot and action_snapshot["validation_result"] != "PASS":
        issue = _new_issue(
            "Action Platform pierde su contrato personal evidence-first",
            "personal_sports_experience",
            "high",
            "/smart-home",
            "Action Platform; " + ",".join(action_snapshot["evidence"]["violations"]),
            app_version,
        )
        issue.update({
            "id": "NEMESIS-ACTION-PLATFORM-CONTRACT",
            "priority": "P1",
            "profile": "CLIENT",
            "component": "action_platform",
            "description": "La experiencia personalizada podria inventar datos, decidir por el usuario, crear recomendaciones de apuestas o duplicar motores.",
            "expected_behavior": "Smart Home, favoritos, watchlist, alertas, briefing, recap, actividad e historial de decision reutilizan motores existentes y exponen procedencia, evidencia, frescura, calidad y limitaciones.",
            "actual_behavior": "Una o mas garantias del contrato Action Platform no se pueden demostrar.",
            "suggested_fix": "Restaurar solo el contrato incumplido y repetir Action Platform check, Browser QA, Sentinel y Privacy Guard.",
            "safe_auto_fix_possible": False,
            "requires_admin_approval": True,
            "requires_approval": True,
            "likely_files": [
                "app.py",
                "templates/action_platform.html",
                "static/v933-product.css",
                "engines/sports_platform_contracts.py",
                "engines/project_operating_system_engine.py",
                "tools/check_action_platform.py",
            ],
            "codex_prompt_suggestion": (
                "Revisar Action Platform con la evidencia indicada. No crear motores nuevos, IA, predicciones, picks, "
                "llamadas externas, Telegram, Stripe ni escrituras GET; conservar fuente, evidencia, frescura, calidad y limitaciones."
            ),
            "product_quality_contract": action_snapshot,
        })
        issue["codex_prompt"] = issue["codex_prompt_suggestion"]
        issues.append(classify_autopilot_issue(issue))
    return issues

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
    # V902: these are safe operational states when the UI exposes them honestly.
    # They should remain visible in runtime/admin, but they are not active
    # incidents unless a page promises a real provider, payment, or logo that is
    # not actually configured.
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
    sports_contract: dict[str, Any] | None = None,
    save_memory: bool = False,
    memory_root: str | Path | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    issues = []
    issues.extend(_environment_issues(runtime, app_version, render_runtime))
    issues.extend(_issues_from_sentinel(sentinel_result, app_version))
    issues.extend(_issues_from_visual(visual_result, app_version))
    issues.extend(_scan_routes(flask_client, app_version, sports_contract))
    issues.extend(_independent_sports_query_issues(memory_root, app_version))
    issues.extend(detect_product_quality_contract_issues(project_root, app_version))

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
        "sports_data_contract_policy": {
            "contract": (sports_contract or {}).get("contract") or "sports-metrics-v1",
            "snapshot_id": (sports_contract or {}).get("snapshot_id") or "",
            "independent_queries_forbidden": True,
            "canonical_match_card": "canonical-v1",
            "violation_priority": "P1",
            "autofix_allowed": False,
        },
        "product_quality_contract": build_customer_trust_icon_contract_snapshot(project_root, app_version),
        "client_copy_audience_contract": build_client_copy_audience_contract_snapshot(project_root, app_version),
        "madrid_timestamp_presentation_contract": build_madrid_timestamp_presentation_contract_snapshot(project_root, app_version),
        "team_center_experience_contract": build_team_center_experience_contract_snapshot(project_root, app_version),
        "competition_center_experience_contract": build_competition_center_experience_contract_snapshot(project_root, app_version),
        "player_center_experience_contract": build_player_center_experience_contract_snapshot(project_root, app_version),
        "shark_intelligence_platform_contract": build_shark_intelligence_platform_contract_snapshot(project_root, app_version),
        "user_intelligence_platform_contract": build_user_intelligence_platform_contract_snapshot(project_root, app_version),
        "sports_intelligence_gateway_contract": build_sports_intelligence_gateway_contract_snapshot(project_root, app_version),
        "decision_engine_contract": build_decision_engine_contract_snapshot(project_root, app_version),
        "experience_platform_contract": build_experience_platform_contract_snapshot(project_root, app_version),
        "action_platform_contract": build_action_platform_contract_snapshot(project_root, app_version),
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
