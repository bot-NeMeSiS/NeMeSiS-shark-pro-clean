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
