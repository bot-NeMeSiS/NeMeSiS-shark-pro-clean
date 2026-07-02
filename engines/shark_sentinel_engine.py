"""SHARK Sentinel: safe real-user app inspection model.

The Sentinel behaves like a simulated QA user. It never changes code, deploys,
touches secrets, mutates payments, deletes data, sends Telegram messages, or
invents sports/business facts. Static inspection can run with Flask test client.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha1
import re
from typing import Any
from zoneinfo import ZoneInfo


MADRID_TZ = ZoneInfo("Europe/Madrid")

PROFILES = {
    "VISITOR": ["/", "/cliente-login", "/registro", "/support"],
    "FREE": ["/app", "/partidos", "/calendar", "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support", "/track-record"],
    "PRO": ["/app", "/picks", "/shark", "/telegram", "/profile", "/track-record"],
    "ELITE": ["/app", "/live", "/picks", "/shark", "/telegram", "/track-record"],
    "ADMIN": ["/admin/dashboard", "/admin/company-os", "/admin/company-audit", "/admin/auto-improvement", "/admin/data-center", "/admin/api-sports", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"],
}

EXPECTED_ROUTE_RULES = {
    "/api/admin/shark-sentinel/summary": {"status": 403, "admin_required": True},
    "/api/admin/shark-sentinel/run": {"status": 403, "admin_required": True},
    "/api/automation/shark-sentinel/run": {"status": 403, "automation_secret_required": True},
}

FORBIDDEN_AUTOMATIC_ACTIONS = [
    "Modificar app.py o templates automáticamente en producción",
    "Deploy automático",
    "Tocar secretos",
    "Borrar DB o usuarios",
    "Modificar pagos reales",
    "Enviar Telegram masivo",
    "Inventar picks, cuotas, resultados o minutos",
]

ISSUE_CATEGORIES = [
    "route", "button", "navigation", "visual", "mobile", "desktop", "admin",
    "membership", "data_reality", "picks", "live", "telegram", "shark",
    "payments", "copy", "security", "render", "automation",
]


@dataclass(frozen=True)
class SentinelIssue:
    id: str
    timestamp_madrid: str
    profile: str
    route: str
    category: str
    severity: str
    title: str
    description: str
    evidence: str
    expected_behavior: str
    actual_behavior: str
    suggested_fix: str
    safe_auto_fix_possible: bool
    requires_admin_approval: bool
    codex_prompt_suggestion: str


def madrid_now() -> str:
    return datetime.now(MADRID_TZ).isoformat(timespec="seconds")


def _issue(profile: str, route: str, category: str, severity: str, title: str, description: str, evidence: str, expected: str, actual: str, fix: str, prompt: str, safe: bool = False, approval: bool = False) -> dict[str, Any]:
    raw = f"{profile}:{route}:{category}:{severity}:{title}:{evidence}"
    issue_id = "SENT-" + sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:10].upper()
    return asdict(SentinelIssue(
        id=issue_id,
        timestamp_madrid=madrid_now(),
        profile=profile,
        route=route,
        category=category,
        severity=severity,
        title=title,
        description=description,
        evidence=evidence[:600],
        expected_behavior=expected,
        actual_behavior=actual,
        suggested_fix=fix,
        safe_auto_fix_possible=safe,
        requires_admin_approval=approval,
        codex_prompt_suggestion=prompt,
    ))


def _visible_text_from_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style|template|svg|noscript)\b.*?</\1>", " ", html or "")
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def _interactive_texts_from_html(html: str) -> list[str]:
    """Return visible CTA text inside links/buttons for static copy QA.

    Match rows are usually full-card links that contain teams, league, country
    and status. They are visible, but they are not button labels; checking them
    as CTAs creates noisy false positives such as league + country repetition.
    """
    texts: list[str] = []
    row_link_markers = (
        "match-row", "match-card", "fixture", "list-row", "v774-match-row",
        "v860-mini-row", "v855-match", "v856-match", "v858-match",
    )
    cta_markers = (
        "btn", "button", "action", "cta", "pill", "chip", "tab", "nav",
        "quick", "ghost", "primary", "secondary",
    )
    for match in re.finditer(r"(?is)<(a|button)\b([^>]*)>(.*?)</\1>", html or ""):
        tag = (match.group(1) or "").lower()
        attrs = (match.group(2) or "").lower()
        if tag == "a":
            if any(marker in attrs for marker in row_link_markers):
                continue
            if not any(marker in attrs for marker in cta_markers):
                continue
        text = _visible_text_from_html(match.group(3))
        if text:
            texts.append(text)
    return texts


def _has_duplicate_cta_text(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return False
    words = [w.strip("·:|/-").lower() for w in normalized.split() if w.strip("·:|/-")]
    if len(words) >= 2 and any(words[i] == words[i + 1] for i in range(len(words) - 1)):
        return True
    if len(words) == 2 and words[0] == words[1]:
        return True
    return False


def build_sentinel_journeys() -> list[dict[str, Any]]:
    journeys: list[dict[str, Any]] = []
    for profile, routes in PROFILES.items():
        journeys.append({
            "profile": profile,
            "routes": routes,
            "checks": [
                "route_exists",
                "status_code_expected",
                "login_required_expected",
                "admin_required_expected",
                "visible_title_expected",
                "has_primary_action",
                "has_back_or_navigation",
                "has_logout_or_account_access",
                "no_obvious_mojibake",
                "no_forbidden_betting_claims",
                "no_empty_broken_state",
                "no_fake_data_claim",
                "has_safe_empty_state_when_no_data",
                "has_plan_badge_when_user",
                "has_upgrade_cta_when_locked",
                "no_client_nav_inside_admin",
                "no_admin_link_inside_client",
                "no_duplicate_floating_shark",
                "no_duplicate_bottom_nav",
                "has_madrid_time_label_or_format",
                "has_clear_error_message",
                "has_expected_buttons",
                "has_expected_links",
            ],
        })
    return journeys


def _inspect_html(profile: str, route: str, status_code: int, html: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    lower = html.lower()
    visible_lower = _visible_text_from_html(html).lower()
    sports_routes = {"/partidos", "/calendar", "/live", "/directo", "/picks"}
    sports_safe_states = [
        "sin partidos reales",
        "esperando proveedor",
        "sin sincronización reciente",
        "requiere sincronización real",
        "proveedor sin datos",
        "sin directos reales",
        "sin picks activos",
        "cuota pendiente",
        "selección pendiente",
        "pick en revisión",
        "sin pick real publicado",
    ]
    sports_row_markers = [
        "v799-agenda-row",
        "v801-agenda-row",
        "v799-live-card",
        "v850-live-card",
        "v799-pick-card",
        "ns-match-row",
        "ns-pick-card",
    ]
    if status_code >= 500:
        issues.append(_issue(profile, route, "route", "critical", "Ruta con error 500", "La ruta devuelve error de servidor.", str(status_code), "La pantalla debe cargar o redirigir de forma segura.", f"HTTP {status_code}", f"Revisar handler de {route}.", f"Corrige el 500 detectado en {route}."))
    mojibake_tokens = [chr(195), chr(194), chr(65533)]
    if any(token in html for token in mojibake_tokens):
        issues.append(_issue(profile, route, "copy", "high", "Mojibake visible", "Hay caracteres rotos visibles en HTML.", "caracteres mojibake", "Texto limpio en español.", "Texto con mojibake.", f"Corregir encoding/textos en {route}.", f"Corrige mojibake detectado en {route}."))
    for phrase in ["apuesta segura", "garantizado", "apuesta fija", "sin riesgo"]:
        if phrase in lower:
            issues.append(_issue(profile, route, "security", "critical", "Claim de apuesta irresponsable", "La pantalla contiene una promesa prohibida.", phrase, "Lenguaje responsable, sin garantías.", f"Contiene {phrase}.", "Sustituir por copy responsable con riesgo.", f"Elimina claim irresponsable '{phrase}' en {route}."))
    if route.startswith("/admin") and ("bottom-nav" in lower or "v825-public-floating-shark" in lower):
        issues.append(_issue(profile, route, "admin", "medium", "Elemento cliente en admin", "La pantalla admin contiene señales de navegación/floating cliente.", "bottom-nav/floating shark", "Admin debe tener shell propio.", "Señal cliente encontrada.", "Revisar CSS/base para ocultar elementos cliente en admin.", f"Elimina navegación cliente visible en admin para {route}."))
    if not route.startswith("/admin") and "/admin/" in lower and profile != "ADMIN":
        issues.append(_issue(profile, route, "navigation", "medium", "Link admin en cliente", "Una ruta cliente expone enlace admin en HTML.", "/admin/", "Cliente no debe ver enlaces de operación admin.", "Link admin detectado.", "Revisar navegación y CTAs cliente.", f"Oculta links admin detectados en {route}."))
    if status_code == 200 and len(html.strip()) < 300:
        issues.append(_issue(profile, route, "visual", "medium", "Pantalla demasiado vacía", "La respuesta HTML es muy corta para una pantalla visible.", f"len={len(html)}", "Pantalla con estructura, estado o redirección clara.", "HTML muy corto.", "Añadir empty state premium o revisar template.", f"Revisa empty state pobre en {route}."))
    if status_code == 200 and route in sports_routes:
        has_sports_rows = any(marker in lower for marker in sports_row_markers)
        has_safe_explanation = any(state in visible_lower for state in sports_safe_states)
        if not has_sports_rows and not has_safe_explanation:
            issues.append(_issue(
                profile,
                route,
                "data_reality",
                "high",
                "Pantalla deportiva vacía sin explicación",
                "La ruta central no muestra partidos/picks/directos ni explica proveedor, sync, caché o filtros.",
                route,
                "Si no hay datos reales, debe mostrarse un estado seguro y una acción clara.",
                "No hay filas deportivas ni estado seguro reconocible.",
                "Añadir estado Sin partidos reales / Esperando proveedor / Requiere sincronización real y CTAs útiles.",
                f"Corrige el estado vacío deportivo de {route} sin inventar datos.",
            ))
        elif not has_sports_rows and has_safe_explanation:
            issues.append(_issue(
                profile,
                route,
                "data_reality",
                "low",
                "Pantalla deportiva sin filas reales visibles",
                "La ruta muestra un estado seguro, pero no hay partidos/picks/directos reales visibles.",
                route,
                "Si no hay datos reales, debe existir estado seguro y tarea admin de sync/filtros/cache.",
                "Estado seguro presente, sin filas deportivas reales.",
                "Mantener estado seguro y revisar proveedor, cache, filtros o temporada desde admin.",
                f"Revisa por qué {route} no muestra datos deportivos reales aunque tenga estado seguro.",
            ))
    if re.search(r"\b(none|null|undefined)\b", visible_lower):
        if route not in {"/api/runtime-version"}:
            issues.append(_issue(profile, route, "copy", "low", "Texto técnico posible", "Aparecen tokens técnicos que podrían ser visibles.", "None/null/undefined", "Cliente debe ver estados premium.", "Token técnico detectado.", "Revisar si el token es visible al usuario.", f"Revisa tokens técnicos visibles en {route}."))
    for text in _interactive_texts_from_html(html):
        if _has_duplicate_cta_text(text):
            issues.append(_issue(profile, route, "button", "medium", "Texto duplicado en botón", "Un enlace o botón contiene palabras repetidas de forma visible.", text, "Cada CTA debe tener una etiqueta limpia y una sola intención.", "CTA con texto duplicado.", "Revisar macro/template que construye el botón.", f"Corrige texto duplicado en botones de {route}."))
    return issues


def run_static_flask_inspection(client: Any, version: str = "") -> dict[str, Any]:
    """Inspect key routes with Flask test client. No browser required."""
    issues: list[dict[str, Any]] = []
    route_results: list[dict[str, Any]] = []
    total_routes = 0
    for profile, routes in PROFILES.items():
        for route in routes:
            total_routes += 1
            response = client.get(route)
            status = int(getattr(response, "status_code", 0))
            html = response.get_data(as_text=True) if hasattr(response, "get_data") else ""
            route_results.append({"profile": profile, "route": route, "status_code": status})
            if status >= 500:
                issues.extend(_inspect_html(profile, route, status, html))
            elif status in {200, 301, 302, 401, 403}:
                issues.extend(_inspect_html(profile, route, status, html))
            else:
                issues.append(_issue(profile, route, "route", "medium", "Status inesperado", "La ruta devuelve un status no esperado para smoke de usuario.", str(status), "200, redireccion o protección clara.", f"HTTP {status}", "Revisar si la ruta debe existir o redirigir.", f"Revisa status inesperado en {route}."))

    by_severity = summarize_issues_by(issues, "severity")
    by_category = summarize_issues_by(issues, "category")
    score = max(0, round(10 - (len([i for i in issues if i["severity"] in {"critical", "high"}]) * 1.5) - (len(issues) * 0.08), 1))
    return {
        "version": version,
        "sentinel_status": "static_flask_client_completed",
        "last_run": madrid_now(),
        "mode": "MODE_STATIC_FLASK_CLIENT",
        "browser_ready": False,
        "browser_note": "browser QA not available locally unless Playwright is installed and run explicitly",
        "global_score": score,
        "profiles": list(PROFILES.keys()),
        "routes_reviewed": total_routes,
        "route_results": route_results,
        "issues": issues,
        "issues_by_severity": by_severity,
        "issues_by_category": by_category,
        "recommended_actions": build_recommended_actions(issues),
        "codex_prompt_suggestions": build_codex_prompts(issues),
        "safe_actions": ["refrescar diagnostico", "generar reporte", "marcar issue como revisado", "preparar prompt Codex"],
        "approval_required_actions": ["crear prompt Codex como tarea", "ejecutar sync", "enviar Telegram test", "tocar membresías", "archivar picks", "preparar release"],
        "forbidden_automatic_actions": FORBIDDEN_AUTOMATIC_ACTIONS,
        "no_secrets": True,
        "no_code_writes": True,
        "no_deploy": True,
        "no_external_calls": True,
        "no_db_write_during_render": True,
        "no_fake_data": True,
    }


def build_static_sentinel_summary(version: str = "") -> dict[str, Any]:
    journeys = build_sentinel_journeys()
    return {
        "version": version,
        "sentinel_status": "ready_static_diagnostic",
        "last_run": None,
        "global_score": None,
        "profiles": list(PROFILES.keys()),
        "journeys": journeys,
        "issues": [],
        "issues_by_severity": {},
        "issues_by_category": {},
        "recommended_actions": [
            "Ejecutar inspección estática con Flask test client.",
            "Revisar incidencias por severidad antes de abrir cambios.",
            "Usar prompts Codex generados como tareas controladas.",
        ],
        "codex_prompt_suggestions": [
            "Corrige rutas rotas detectadas en /picks y /live.",
            "Compacta cards moviles en /app y /partidos.",
            "Elimina navegacion cliente en admin si aparece.",
            "Corrige mojibake detectado en templates.",
            "Revisa empty states sin datos reales.",
            "Corrige visual de membresía PRO/ELITE.",
            "Arregla boton que no lleva a ruta esperada.",
            "Revisa fallback de escudos en directo.",
        ],
        "safe_actions": ["diagnostico", "reporte", "prompt sugerido"],
        "approval_required_actions": ["sync", "Telegram test", "membresías", "picks", "release"],
        "forbidden_automatic_actions": FORBIDDEN_AUTOMATIC_ACTIONS,
        "browser_ready": True,
        "browser_note": "MODE_BROWSER_READY preparado como opcion, no obligatorio",
        "no_secrets": True,
        "no_code_writes": True,
        "no_deploy": True,
        "no_external_calls": True,
        "no_db_write_during_render": True,
        "no_fake_data": True,
    }


def summarize_issues_by(issues: list[dict[str, Any]], key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for issue in issues:
        value = str(issue.get(key) or "unknown")
        result[value] = result.get(value, 0) + 1
    return result


def build_recommended_actions(issues: list[dict[str, Any]]) -> list[str]:
    if not issues:
        return ["Mantener Sentinel en cron diagnostico y repetir tras cada release."]
    actions = []
    for issue in issues[:8]:
        actions.append(str(issue.get("suggested_fix") or "Revisar incidencia detectada."))
    return actions


def build_codex_prompts(issues: list[dict[str, Any]]) -> list[str]:
    if not issues:
        return [
            "Ejecuta SHARK Sentinel despues del siguiente cambio visual y compara incidencias.",
            "Audita rutas cliente/admin con modo static Flask client y corrige solo hallazgos high/critical.",
        ]
    prompts = []
    for issue in issues[:8]:
        prompt = str(issue.get("codex_prompt_suggestion") or "").strip()
        if prompt and prompt not in prompts:
            prompts.append(prompt)
    return prompts
