"""V883 Visual Company Worker.

Permanent internal QA worker for NeMeSiS SHARK PRO. It inspects routes through
Flask's local test client, classifies visible/product/admin/data risks, and
returns safe tasks and Codex prompts. It never writes code, deploys, touches
secrets, mutates payments/users, sends Telegram, calls paid APIs, or invents
sport data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha1
import re
from typing import Any
from zoneinfo import ZoneInfo


MADRID_TZ = ZoneInfo("Europe/Madrid")

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
    "/admin/fix-pipeline",
    "/admin/data-center",
    "/admin/data-marketplace",
    "/admin/telegram/command-center",
    "/admin/shark-ai",
    "/admin/users",
    "/admin/memberships",
    "/admin/payments",
]

MODES = {
    "quick": CLIENT_ROUTES[:5] + ADMIN_ROUTES[:4],
    "visual": CLIENT_ROUTES + ADMIN_ROUTES[:6],
    "product": ["/app", "/partidos", "/calendar", "/live", "/directo", "/picks", "/track-record"],
    "admin": ADMIN_ROUTES,
    "full": CLIENT_ROUTES + ADMIN_ROUTES,
    "visual-worker": CLIENT_ROUTES + ADMIN_ROUTES,
    "company-worker": CLIENT_ROUTES + ADMIN_ROUTES,
    "full-company-qa": CLIENT_ROUTES + ADMIN_ROUTES,
}

SAFE_STATES = [
    "Sin partidos reales ahora mismo",
    "Esperando proveedor",
    "Sin sincronizacion reciente",
    "Sin sincronización reciente",
    "Requiere sincronizacion real",
    "Requiere sincronización real",
    "Proveedor sin datos ahora mismo",
    "Sin directos reales",
    "Sin picks activos",
    "Cuota pendiente",
    "Seleccion pendiente",
    "Selección pendiente",
    "Pick en revision",
    "Pick en revisión",
    "Sin pick real publicado",
    "No configurado",
    "Accion pendiente",
    "Acción pendiente",
    "Modo seguro activo",
    "Analisis limitado sin proveedor IA",
    "Análisis limitado sin proveedor IA",
    "Escudo pendiente",
    "Fallback visual activo",
]

FORBIDDEN_PROMISES = [
    "apuesta segura",
    "sin riesgo",
    "garantizado",
    "garantizada",
    "seguro al 100",
    "fijo",
]

BAD_HREFS = {"", "#", "javascript:void(0)", "javascript:void(0);", "javascript:;"}

TECHNICAL_VISIBLE_TOKENS = ["None", "undefined", "Traceback", "sqlite3.", "werkzeug."]
MOJIBAKE_TOKENS = ["Ã", "Â", "�", "EspaÁa", "Result ados"]

VISUAL_RULES = [
    "botones_repetidos",
    "ctas_duplicados",
    "textos_duplicados",
    "labels_raros",
    "ingles_tecnico_visible",
    "mojibake",
    "none_null_undefined_visible",
    "cards_gigantes",
    "huecos_negros_grandes",
    "empty_states_enormes",
    "pantalla_sin_jerarquia",
    "tablas_con_demasiado_aire",
    "mobile_overflow",
    "bottom_nav_duplicada",
    "floating_shark_duplicado",
    "nav_cliente_en_admin",
    "nav_admin_en_cliente",
    "sidebar_duplicada",
    "demasiadas_acciones_por_card",
    "endpoint_tecnico_visible",
    "sentinel_parece_json",
    "pantalla_sin_cta_principal",
]

FUNCTIONAL_FLOW_RULES = [
    "button_without_destination",
    "empty_href",
    "hash_href",
    "javascript_href",
    "duplicate_cta_label",
    "client_button_to_admin",
    "admin_button_to_client_without_context",
    "too_many_primary_actions",
    "missing_return_path",
    "missing_safe_next_action",
]

V885_NAV_RULES = [
    "client_desktop_sidebar_required",
    "client_mobile_bottom_nav_required",
    "admin_must_not_render_client_sidebar",
    "admin_must_not_render_client_bottom_nav",
    "client_must_not_render_admin_nav",
    "single_client_sidebar_instance",
    "single_bottom_nav_instance",
    "single_floating_shark_instance",
    "active_route_marker_required",
    "primary_client_links_required",
]

PRODUCT_DATA_RULES = [
    "partidos_vacio_sin_explicacion",
    "calendar_vacio_sin_explicacion",
    "live_vacio_sin_explicacion",
    "picks_vacio_sin_explicacion",
    "api_configurada_sin_estado_visible",
    "cache_partidos_0_sin_tarea",
    "live_cache_0_sin_explicacion",
    "odds_cache_0_sin_explicacion",
    "logo_cache_0_sin_fallback",
    "picks_sin_cuota_y_sin_estado",
    "seleccion_pendiente_mal_comunicada",
    "pick_en_revision_no_explicado",
    "proveedor_sin_datos_sin_cta",
    "filtros_ocultando_todo",
    "sin_relacion_partido_pick",
    "sin_estado_sync_visible",
]


@dataclass(frozen=True)
class WorkerArea:
    name: str
    area: str
    checks: list[str]


WORKERS = [
    WorkerArea("CEO/Product Owner Worker", "producto", ["claridad comercial", "pantallas demo", "CTA principal"]),
    WorkerArea("Visual QA Worker", "visual", VISUAL_RULES[:8]),
    WorkerArea("Mobile QA Worker", "mobile", ["overflow", "bottom nav", "SHARK flotante", "cards compactas"]),
    WorkerArea("Admin Operations Worker", "admin", ["proteccion admin", "command center", "tareas abiertas"]),
    WorkerArea("Data/API Worker", "datos", PRODUCT_DATA_RULES[:8]),
    WorkerArea("Picks/Odds Worker", "picks", ["cuota pendiente", "seleccion pendiente", "pick en revision"]),
    WorkerArea("Telegram Worker", "telegram", ["no filler", "dedupe", "estado real", "sin envios inventados"]),
    WorkerArea("SHARK IA Worker", "shark", ["modo seguro", "sin promesas garantizadas", "contexto real"]),
    WorkerArea("Payments/Memberships Worker", "pagos", ["Stripe honesto", "planes diferenciados", "sin cobros inventados"]),
    WorkerArea("Security Worker", "seguridad", ["sin secretos", "cron protegido", "admin 403"]),
    WorkerArea("Render/DevOps Worker", "render", ["version local", "version Render", "root GitHub"]),
    WorkerArea("Release Manager Worker", "release", ["ZIP limpio", "checks", "manifest"]),
    WorkerArea("Spanish Copy Worker", "copy", ["mojibake", "copy tecnico", "labels premium"]),
    WorkerArea("Sentinel Workflow Worker", "sentinel", ["issues", "tasks", "prompts", "revalidacion"]),
]

SAFE_ACTIONS = [
    "revisar ruta con Flask test client",
    "clasificar issue visible",
    "generar tarea de mejora",
    "generar prompt Codex",
    "revalidar en seco",
    "marcar pendiente de browser QA",
    "marcar pendiente de Render real",
]

APPROVAL_REQUIRED_ACTIONS = [
    "editar templates/CSS/app.py con Codex",
    "desplegar en Render",
    "probar Telegram real",
    "sincronizar proveedor real",
    "probar pagos reales",
    "usar credenciales admin reales",
]

BLOCKED_ACTIONS = [
    "auto-code en produccion",
    "auto-deploy",
    "tocar secretos",
    "borrar DB o usuarios",
    "enviar Telegram real sin autorizacion",
    "inventar partidos/picks/cuotas/resultados",
    "llamar APIs externas caras sin guard",
]


def madrid_now() -> str:
    return datetime.now(MADRID_TZ).isoformat(timespec="seconds")


def stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part or "") for part in parts)
    return f"{prefix}-" + sha1(raw.encode("utf-8")).hexdigest()[:12].upper()


def normalize_mode(mode: str | None) -> str:
    mode = (mode or "quick").strip().lower()
    return mode if mode in MODES else "quick"


def _visible_text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", html or "")
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def _links_from_html(html: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for match in re.finditer(r"(?is)<a\b[^>]*href=[\"']([^\"']*)[\"'][^>]*>(.*?)</a>", html or ""):
        href = (match.group(1) or "").strip()
        label = _visible_text(match.group(2) or "")
        links.append((href, label))
    return links


def _issue(route: str, profile: str, category: str, severity: str, title: str, evidence: str, fix: str) -> dict[str, Any]:
    return {
        "id": stable_id("V884", route, profile, category, title, evidence),
        "timestamp_madrid": madrid_now(),
        "profile": profile,
        "route": route,
        "category": category,
        "severity": severity,
        "title": title,
        "description": evidence,
        "evidence": evidence[:360],
        "expected_behavior": "La pantalla debe verse premium, clara, segura y sin datos inventados.",
        "actual_behavior": evidence[:360],
        "suggested_fix": fix,
        "safe_auto_fix_possible": False,
        "requires_admin_approval": True,
        "revalidation_notes": "Revisar ruta, ejecutar Sentinel y validar visual/browser si procede.",
        "codex_prompt_suggestion": build_codex_prompt(route, category, severity, evidence),
    }


def build_codex_prompt(route: str, category: str, severity: str, evidence: str) -> str:
    return (
        "Actua como equipo completo de NeMeSiS SHARK PRO. "
        f"Prioridad {severity}. Ruta afectada: {route}. Categoria: {category}. "
        f"Evidencia: {evidence[:220]}. "
        "Corrige solo el defecto real, preserva V818-V883, DB_PATH, usuarios, pagos, Telegram, SHARK, "
        "API-SPORTS y seguridad. No inventes datos, no toques secretos, no hagas deploy automatico. "
        "Valida py_compile, compileall, Sentinel, smoke local y ZIP limpio."
    )


def inspect_route(client: Any, route: str, profile: str) -> dict[str, Any]:
    response = client.get(route, follow_redirects=False)
    status = int(getattr(response, "status_code", 0) or 0)
    html = ""
    try:
        html = response.get_data(as_text=True) or ""
    except Exception:
        html = ""
    text = _visible_text(html)
    issues: list[dict[str, Any]] = []

    if status >= 500:
        issues.append(_issue(route, profile, "route", "critical", "Ruta con error 5xx", f"HTTP {status}", "Corregir error de servidor antes de avanzar."))
    if route.startswith("/admin/") and status not in {200, 302, 303, 401, 403}:
        issues.append(_issue(route, profile, "admin", "high", "Ruta admin con estado inesperado", f"HTTP {status}", "Revisar proteccion y handler admin."))
    if not route.startswith("/admin/") and status not in {200, 302, 303, 401, 403}:
        issues.append(_issue(route, profile, "client", "medium", "Ruta cliente con estado inesperado", f"HTTP {status}", "Revisar ruta o alias cliente."))

    for token in MOJIBAKE_TOKENS:
        if token in text:
            issues.append(_issue(route, profile, "copy", "high", "Mojibake visible", f"Token detectado: {token}", "Corregir encoding/copy visible."))
            break
    for token in TECHNICAL_VISIBLE_TOKENS:
        if token in text:
            issues.append(_issue(route, profile, "copy", "medium", "Texto tecnico visible", f"Token detectado: {token}", "Transformar en estado premium seguro."))
            break
    if re.search(r"\bnull\b", text, flags=re.IGNORECASE) and "newsletter" not in text.lower():
        issues.append(_issue(route, profile, "copy", "medium", "null visible", "La palabra null aparece en texto visible.", "Sustituir por estado seguro."))
    for promise in FORBIDDEN_PROMISES:
        if promise in text.lower():
            issues.append(_issue(route, profile, "responsible_gaming", "critical", "Promesa de apuesta no permitida", promise, "Eliminar promesa y usar lenguaje responsable."))
            break

    if route.startswith("/admin/") and ("bottom-nav-clean" in html or "floating-shark" in html or "v810-big-shark-decoration" in html):
        issues.append(_issue(route, profile, "admin", "high", "Elemento cliente dentro de admin", "Se detecta nav/floating cliente en HTML admin.", "Aislar layout admin."))
    if route.startswith("/admin/") and "ns-client-sidebar" in html:
        issues.append(_issue(route, profile, "admin", "high", "Sidebar cliente dentro de admin", "Se detecta ns-client-sidebar en HTML admin.", "Ocultar sidebar cliente en admin."))
    if not route.startswith("/admin/") and "v808-admin-rail" in html:
        issues.append(_issue(route, profile, "client", "high", "Navegacion admin dentro de cliente", "Se detecta rail admin en HTML cliente.", "Aislar layout cliente."))

    authenticated_client_html = "ns-authenticated" in html and "ns-admin" not in html
    if authenticated_client_html:
        sidebar_count = html.count('data-nav-zone="client-sidebar"')
        bottom_count = html.count('data-nav-zone="client-bottom"')
        shark_count = html.count('class="shark-widget"') + html.count("class='shark-widget'")
        if sidebar_count == 0:
            issues.append(_issue(route, profile, "navigation", "high", "Cliente autenticado sin sidebar principal", "No se detecta data-nav-zone=\"client-sidebar\".", "Restaurar sidebar cliente desktop sin duplicar bottom nav."))
        if sidebar_count > 1:
            issues.append(_issue(route, profile, "navigation", "high", "Sidebar cliente duplicado", f"Instancias client-sidebar: {sidebar_count}", "Dejar una sola instancia canonica."))
        if bottom_count > 1:
            issues.append(_issue(route, profile, "navigation", "medium", "Bottom nav cliente duplicada", f"Instancias client-bottom: {bottom_count}", "Dejar una sola bottom nav canonica para movil."))
        if shark_count > 1 and route not in {"/shark", "/shark-ai", "/shark-core"}:
            issues.append(_issue(route, profile, "navigation", "medium", "SHARK flotante duplicado", f"Instancias shark-widget: {shark_count}", "Dejar una sola instancia cliente y ocultarla en pantallas SHARK."))

    duplicate_buttons = re.findall(r">\s*([^<>]{3,42})\s*</a>", html)
    repeated = [label for label in set(duplicate_buttons) if duplicate_buttons.count(label) > 3 and label.strip().lower() not in {"inicio", "picks"}]
    if repeated:
        issues.append(_issue(route, profile, "visual", "medium", "CTAs repetidos", "Etiquetas repetidas: " + ", ".join(repeated[:4]), "Reducir acciones duplicadas o agruparlas."))

    links = _links_from_html(html)
    bad_links = [(href, label) for href, label in links if href.strip().lower() in BAD_HREFS]
    if bad_links:
        sample = ", ".join((label or href or "sin texto")[:36] for href, label in bad_links[:5])
        issues.append(_issue(route, profile, "flow", "medium", "Boton o enlace sin destino real", sample, "Asignar ruta real, ocultar accion o moverla a estado pendiente."))
    if route.startswith("/admin/"):
        client_links = [href for href, _label in links if href in {"/app", "/picks", "/live", "/telegram", "/profile"}]
        if len(client_links) > 2:
            issues.append(_issue(route, profile, "flow", "low", "Demasiados enlaces cliente dentro de admin", ", ".join(client_links[:5]), "Mantener solo Vista cliente/Salir como acciones secundarias."))
    else:
        admin_links = [href for href, _label in links if href.startswith("/admin/")]
        if admin_links:
            issues.append(_issue(route, profile, "flow", "high", "Enlace admin visible en cliente", ", ".join(admin_links[:5]), "Ocultar rutas admin del flujo cliente."))

    sports_route = route in {"/partidos", "/calendar", "/live", "/directo", "/picks"}
    if sports_route and status == 200:
        has_rows = any(token in html for token in ("ns-match-row", "ns-pick-card", "match-row", "pick-card", "v882-core-grid"))
        has_safe_state = any(state in text for state in SAFE_STATES)
        if not has_rows and not has_safe_state:
            issues.append(_issue(route, profile, "data", "high", "Pantalla deportiva vacia sin estado seguro", "No hay filas/cards ni estado seguro visible.", "Mostrar estado premium y tarea admin sin inventar datos."))
        elif not has_rows and has_safe_state:
            issues.append(_issue(route, profile, "data", "low", "Pantalla deportiva sin datos reales visibles", "Hay estado seguro, pero no hay filas/cards deportivas reales visibles.", "Mantener el estado seguro y crear tarea admin de sync/filtros/cache."))

    return {
        "route": route,
        "profile": profile,
        "status_code": status,
        "redirect_location": response.headers.get("Location", ""),
        "html_size": len(html),
        "text_size": len(text),
        "issues": issues,
        "safe_state_detected": any(state in text for state in SAFE_STATES),
        "admin_protected": route.startswith("/admin/") and status in {302, 303, 401, 403},
    }


def run_route_inspection(client: Any, mode: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    routes = MODES[normalize_mode(mode)]
    results = []
    issues = []
    for route in routes:
        profile = "ADMIN" if route.startswith("/admin/") else "CLIENT"
        result = inspect_route(client, route, profile)
        results.append(result)
        issues.extend(result["issues"])
    return results, issues


def bucket_issues(issues: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "critical": [issue for issue in issues if issue.get("severity") == "critical"],
        "high": [issue for issue in issues if issue.get("severity") == "high"],
        "medium": [issue for issue in issues if issue.get("severity") == "medium"],
        "low": [issue for issue in issues if issue.get("severity") == "low"],
    }


def group_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for issue in issues:
        key = f"{issue.get('category')}:{issue.get('severity')}:{issue.get('title')}"
        group = grouped.setdefault(
            key,
            {
                "group_id": stable_id("GROUP", key),
                "category": issue.get("category"),
                "severity": issue.get("severity"),
                "title": issue.get("title"),
                "routes": set(),
                "issues": [],
                "priority": 0,
            },
        )
        group["routes"].add(issue.get("route"))
        group["issues"].append(issue)
        group["priority"] += {"critical": 100, "high": 70, "medium": 40, "low": 15}.get(issue.get("severity"), 5)
    result = []
    for group in grouped.values():
        group["routes"] = sorted(route for route in group["routes"] if route)
        result.append(group)
    return sorted(result, key=lambda item: item["priority"], reverse=True)


def build_tasks(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks = []
    for group in groups:
        route = ", ".join(group["routes"][:6]) or "rutas no especificadas"
        evidence = "; ".join(issue.get("evidence", "") for issue in group["issues"][:3])
        tasks.append(
            {
                "task_id": stable_id("TASK", group["group_id"], route),
                "title": f"{group['title']} en {route}",
                "priority": group["severity"],
                "routes": group["routes"],
                "evidence": evidence,
                "status": "pendiente_revision",
                "safe_next_step": "Aplicar fix controlado con Codex y revalidar.",
                "codex_prompt": build_codex_prompt(route, group["category"], group["severity"], evidence),
                "requires_admin_approval": True,
            }
        )
    return tasks


def score_from_issues(issues: list[dict[str, Any]], category: str | None = None) -> float:
    relevant = [issue for issue in issues if not category or issue.get("category") == category]
    penalty = 0.0
    for issue in relevant:
        penalty += {"critical": 2.0, "high": 1.2, "medium": 0.45, "low": 0.15}.get(issue.get("severity"), 0.05)
    return round(max(0.0, 10.0 - penalty), 1)


def build_worker_matrix(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix = []
    for worker in WORKERS:
        area_issues = [issue for issue in issues if issue.get("category") in {worker.area, "copy" if worker.area == "copy" else worker.area}]
        if not area_issues and worker.area == "visual":
            area_issues = [issue for issue in issues if issue.get("category") in {"visual", "client"}]
        severity = "ok"
        if any(issue.get("severity") == "critical" for issue in area_issues):
            severity = "critical"
        elif any(issue.get("severity") == "high" for issue in area_issues):
            severity = "needs_attention"
        elif area_issues:
            severity = "watch"
        matrix.append(
            {
                "worker_name": worker.name,
                "area": worker.area,
                "status": severity,
                "findings": [issue.get("title") for issue in area_issues[:5]] or ["Sin incidencias reales detectadas en este ciclo local."],
                "tasks": [issue.get("suggested_fix") for issue in area_issues[:3]] or ["Mantener vigilancia y revalidar con browser/Render cuando proceda."],
                "priority": "alta" if severity in {"critical", "needs_attention"} else "normal",
                "next_action": "Resolver incidencia y revalidar." if area_issues else "Seguir monitorizando.",
            }
        )
    return matrix


def build_visual_company_worker_summary(
    version: str = "",
    runtime: dict[str, Any] | None = None,
    route_results: list[dict[str, Any]] | None = None,
    issues: list[dict[str, Any]] | None = None,
    mode: str = "quick",
    dry_run: bool = True,
) -> dict[str, Any]:
    runtime = runtime or {}
    route_results = route_results or []
    issues = issues or []
    groups = group_issues(issues)
    tasks = build_tasks(groups)
    buckets = bucket_issues(issues)
    return {
        "version": version,
        "mode": normalize_mode(mode),
        "dry_run": bool(dry_run),
        "status": "visual_company_worker_ready",
        "generated_at_madrid": madrid_now(),
        "global_score": score_from_issues(issues),
        "visual_score": score_from_issues(issues, "visual"),
        "product_score": score_from_issues(issues, "data"),
        "data_score": score_from_issues(issues, "data"),
        "admin_score": score_from_issues(issues, "admin"),
        "mobile_score": score_from_issues(issues, "mobile"),
        "critical_issues": buckets["critical"],
        "high_issues": buckets["high"],
        "medium_issues": buckets["medium"],
        "low_issues": buckets["low"],
        "recurrent_issues": [],
        "issues": issues,
        "grouped_issues": groups,
        "suggested_tasks": tasks,
        "codex_prompts": [task["codex_prompt"] for task in tasks],
        "safe_actions": SAFE_ACTIONS,
        "approval_required_actions": APPROVAL_REQUIRED_ACTIONS,
        "blocked_actions": BLOCKED_ACTIONS,
        "next_focus": [
            "Resolver primero critical/high si aparecen.",
            "Browser QA real para confirmar overflow, huecos y repeticion visual.",
            "Deploy manual pendiente si Render no sirve la version local.",
            "Mantener estados seguros cuando no haya datos reales.",
        ],
        "workers": build_worker_matrix(issues),
        "routes_reviewed": len(route_results),
        "route_results": route_results,
        "visual_rules": VISUAL_RULES,
        "functional_flow_rules": FUNCTIONAL_FLOW_RULES,
        "nav_rules_v885": V885_NAV_RULES,
        "product_data_rules": PRODUCT_DATA_RULES,
        "render_awareness": {
            "local_version": version,
            "render_version": runtime.get("render_version") or runtime.get("version") or runtime.get("app_version") or "",
            "mismatch_detected": bool(runtime.get("render_version") and runtime.get("render_version") != version),
            "note": "No se consulta Render desde render de pagina; usar reporte QA o endpoint runtime real.",
        },
        "no_auto_code": True,
        "no_auto_deploy": True,
        "no_secrets": True,
        "no_fake_data": True,
        "no_external_paid_calls": True,
        "no_db_mutation": True,
    }


def run_visual_company_worker(client: Any, version: str = "", mode: str = "quick", dry_run: bool = True, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    mode = normalize_mode(mode)
    route_results, issues = run_route_inspection(client, mode)
    runtime = runtime or {}
    render_version = runtime.get("render_version") or runtime.get("version") or runtime.get("app_version")
    if render_version and render_version != version:
        issues.append(
            _issue(
                "/api/runtime-version",
                "RENDER",
                "render",
                "critical",
                "Produccion no sirve la version local actual",
                f"Render={render_version}; Local={version}",
                "Corregir root GitHub/Render y desplegar manualmente la version actual.",
            )
        )
    return build_visual_company_worker_summary(version, runtime=runtime, route_results=route_results, issues=issues, mode=mode, dry_run=dry_run)
