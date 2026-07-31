"""Evidence-first product review system for NeMeSiS.

The Product Review System is the internal quality department for the product.
It is deterministic and read-only: it scans existing local evidence, routes,
templates, contracts and reports. It never calls generative AI, external
providers, Telegram, Stripe, production, or writes databases.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from engines.experience_platform_engine import build_experience_platform_snapshot
from engines.sports_platform_contracts import build_sports_platform_contract_registry

MADRID = ZoneInfo("Europe/Madrid")
PRODUCT_REVIEW_SYSTEM_CONTRACT = "NEMESIS-PRODUCT-REVIEW-SYSTEM-V1"
PRODUCT_REVIEW_CENTER_CONTRACT = "NEMESIS-PRODUCT-REVIEW-CENTER-V1"
QUALITY_TEAM_CONTRACT = "NEMESIS-WORLD-CLASS-PRODUCT-TEAM-V1"

REVIEWER_DEFINITIONS: tuple[dict[str, str], ...] = (
    {"key": "product_director", "name": "Product Director", "module": "Producto", "responsibility": "Valida valor, integracion y complejidad del producto."},
    {"key": "ux_reviewer", "name": "UX Reviewer", "module": "UX", "responsibility": "Revisa navegacion, onboarding, claridad, jerarquia y accesibilidad."},
    {"key": "mobile_reviewer", "name": "Mobile Reviewer", "module": "Mobile", "responsibility": "Revisa una mano, scroll, targets tactiles, safe areas y responsive."},
    {"key": "sports_reviewer", "name": "Sports Reviewer", "module": "Sports Core", "responsibility": "Valida coherencia deportiva y consumo del Sports Core."},
    {"key": "shark_reviewer", "name": "SHARK Reviewer", "module": "SHARK", "responsibility": "Comprueba evidencia, frescura, procedencia y limitaciones."},
    {"key": "security_reviewer", "name": "Security Reviewer", "module": "Seguridad", "responsibility": "Audita privacidad, permisos, secretos, sesiones y almacenamiento."},
    {"key": "performance_reviewer", "name": "Performance Reviewer", "module": "Rendimiento", "responsibility": "Analiza tiempos, assets, cache, consultas y rendimiento movil/escritorio."},
    {"key": "commercial_reviewer", "name": "Commercial Reviewer", "module": "Comercial", "responsibility": "Evalua FREE, PRO, ELITE, conversion, paywall y retencion."},
    {"key": "marketing_reviewer", "name": "Marketing Reviewer", "module": "Marketing", "responsibility": "Revisa propuesta de valor, mensajes, CTA, diferenciacion y posicionamiento."},
    {"key": "beta_reviewer", "name": "Beta Reviewer", "module": "Beta", "responsibility": "Simula recorridos reales y detecta friccion antes de beta cerrada."},
    {"key": "visual_reviewer", "name": "Visual Reviewer", "module": "Visual", "responsibility": "Detecta espacios vacios, iconografia, color, tipografia y consistencia."},
    {"key": "operations_reviewer", "name": "Operations Reviewer", "module": "Operaciones", "responsibility": "Audita Render, cron, master tick, gateway, logs, backups y restore."},
)

PRIORITY_PENALTY = {"P0": 35, "P1": 18, "P2": 8, "P3": 3}
REQUIRED_FINDING_FIELDS = (
    "module",
    "screen",
    "route",
    "component",
    "evidence",
    "priority",
    "user_impact",
    "business_impact",
    "proposal",
)

GUARDRAILS = {
    "generative_ai_calls": 0,
    "chatbot_created": False,
    "external_calls": 0,
    "database_writes": 0,
    "telegram_sends": 0,
    "stripe_calls": 0,
    "production_modified": False,
    "automatic_improvements": False,
    "automatic_commits": False,
    "automatic_push": False,
    "automatic_deploy": False,
}

ROUTE_RE = re.compile(r"@(?:app|[A-Za-z_][A-Za-z0-9_]*)\.route\(\s*['\"]([^'\"]+)")
TEMPLATE_ROUTE_HINTS = {
    "home.html": "/",
    "calendar.html": "/calendar",
    "live.html": "/live",
    "picks.html": "/picks",
    "track_record.html": "/track-record",
    "telegram.html": "/telegram",
    "membership.html": "/memberships",
    "profile.html": "/profile",
    "favorites.html": "/favorites",
    "match_detail.html": "/match/<match_id>",
    "team_detail.html": "/team/<team_id>",
    "competition_detail.html": "/competition/<competition_id>",
    "player_detail.html": "/player/<player_id>",
    "shark.html": "/shark",
    "shark_intelligence_center.html": "/shark-intelligence",
    "action_platform.html": "/smart-home",
    "user_intelligence_center.html": "/user-intelligence",
    "admin_operations_center.html": "/admin/operations-center",
    "admin_founder_dashboard.html": "/admin/founder-dashboard",
    "admin_developer_center.html": "/admin/developer-center",
    "admin_company_audit.html": "/admin/company-board",
    "admin_product_review_center.html": "/admin/product-review-center",
}


def _root(project_root: str | Path | None = None) -> Path:
    return Path(project_root).resolve() if project_root else Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(MADRID).isoformat(timespec="seconds")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _exists(root: Path, relative: str) -> bool:
    return (root / relative).is_file()


def _text(value: Any, limit: int = 420) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _routes(root: Path) -> set[str]:
    routes: set[str] = set()
    routes.update(ROUTE_RE.findall(_read(root / "app.py")))
    return routes


def _route_for_screen(screen: str) -> str:
    name = Path(screen).name
    if name in TEMPLATE_ROUTE_HINTS:
        return TEMPLATE_ROUTE_HINTS[name]
    if name.startswith("admin_"):
        return "/admin/" + name.removeprefix("admin_").removesuffix(".html").replace("_", "-")
    return "No inferida"


def _finding(
    *,
    reviewer: str,
    module: str,
    screen: str,
    route: str,
    component: str,
    evidence: str,
    priority: str,
    user_impact: str,
    business_impact: str,
    proposal: str,
    source: str,
    state: str = "REQUIRES_REVIEW",
) -> dict[str, Any]:
    return {
        "reviewer": reviewer,
        "module": _text(module, 80),
        "screen": _text(screen, 180),
        "route": _text(route, 120),
        "component": _text(component, 120),
        "evidence": _text(evidence, 620),
        "priority": priority if priority in PRIORITY_PENALTY else "P3",
        "impact_user": _text(user_impact, 360),
        "user_impact": _text(user_impact, 360),
        "impact_business": _text(business_impact, 360),
        "business_impact": _text(business_impact, 360),
        "proposal": _text(proposal, 420),
        "source": _text(source, 160),
        "certification_state": state,
        "candidate_improvement_ready": True,
        "approved_for_execution": False,
        "automatic_execution_allowed": False,
    }


def _missing_file_findings(root: Path, reviewer: str, module: str, requirements: Iterable[tuple[str, str, str]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for relative, label, priority in requirements:
        if not _exists(root, relative):
            findings.append(
                _finding(
                    reviewer=reviewer,
                    module=module,
                    screen=relative,
                    route="No aplica",
                    component="evidencia documental",
                    evidence=f"Archivo requerido no encontrado: {relative}",
                    priority=priority,
                    user_impact=f"La revision {label} queda incompleta por falta de evidencia.",
                    business_impact="La direccion no puede convertir esta conclusion en decision de lanzamiento.",
                    proposal=f"Crear o recuperar evidencia fuente para {label} antes de declarar PASS.",
                    source="filesystem",
                    state="INSUFFICIENT_DATA",
                )
            )
    return findings


def _score(findings: list[dict[str, Any]], evidence_checks: list[dict[str, Any]]) -> tuple[int, list[str]]:
    counts = Counter(item.get("priority", "P3") for item in findings)
    missing = [item for item in evidence_checks if not item.get("ok")]
    penalty = sum(PRIORITY_PENALTY.get(priority, 3) * count for priority, count in counts.items())
    penalty += len(missing) * 5
    score = max(0, min(100, 100 - penalty))
    explanation = ["Base 100."]
    for priority in ("P0", "P1", "P2", "P3"):
        if counts.get(priority):
            explanation.append(f"{priority}={counts[priority]} x -{PRIORITY_PENALTY[priority]}.")
    if missing:
        explanation.append(f"Evidencia obligatoria ausente={len(missing)} x -5.")
    if len(explanation) == 1:
        explanation.append("Sin hallazgos bloqueantes ni evidencia obligatoria ausente.")
    return score, explanation


def _build_reviewer(definition: dict[str, str], findings: list[dict[str, Any]], evidence_checks: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    score, explanation = _score(findings, evidence_checks)
    counts = Counter(item.get("priority", "P3") for item in findings)
    state = "PASS" if not counts.get("P0") and not counts.get("P1") else "REQUIRES_REVIEW"
    if any(not item.get("ok") for item in evidence_checks):
        state = "PARTIAL" if state == "PASS" else state
    return {
        **definition,
        "contract": f"NEMESIS-{definition['key'].upper().replace('_', '-')}-REVIEWER-V1",
        "state": state,
        "last_review_madrid": generated_at,
        "score": score,
        "score_explanation": explanation,
        "findings_count": len(findings),
        "p0": counts.get("P0", 0),
        "p1": counts.get("P1", 0),
        "p2": counts.get("P2", 0),
        "p3": counts.get("P3", 0),
        "evidence_checks": evidence_checks,
        "findings": findings,
        "autofix_allowed": False,
        "human_approval_required": True,
    }


def _capability(registry: dict[str, Any], key: str) -> dict[str, Any]:
    for item in registry.get("capabilities") or []:
        if item.get("key") == key:
            return item
    return {"key": key, "state": "NOT_REGISTERED", "implementation": "No registrada"}


def _capability_checks(registry: dict[str, Any], keys: Iterable[str]) -> list[dict[str, Any]]:
    checks = []
    for key in keys:
        cap = _capability(registry, key)
        checks.append({"key": key, "ok": cap.get("state") == "INTEGRATED", "state": cap.get("state"), "source": cap.get("implementation")})
    return checks


def _findings_from_capabilities(checks: list[dict[str, Any]], reviewer: str, module: str, priority: str = "P2") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for check in checks:
        if check.get("ok"):
            continue
        findings.append(
            _finding(
                reviewer=reviewer,
                module=module,
                screen=str(check.get("source") or "Registro de contratos"),
                route="No aplica",
                component=str(check.get("key")),
                evidence=f"Capacidad {check.get('key')} en estado {check.get('state')}; se esperaba INTEGRATED.",
                priority=priority,
                user_impact="El producto puede mostrar una experiencia incompleta o no trazable.",
                business_impact="La capacidad no puede usarse como evidencia de readiness comercial completa.",
                proposal="Completar la integracion o mantener la capacidad como no certificada.",
                source="sports_platform_contracts",
                state="PARTIALLY_VERIFIED",
            )
        )
    return findings



def _experience_findings(experience: dict[str, Any], reviewer: str, categories: set[str], limit: int = 10) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    for item in ((experience.get("findings") or {}).get("top") or []):
        if item.get("category") not in categories:
            continue
        screen = str(item.get("screen") or "No disponible")
        mapped.append(
            _finding(
                reviewer=reviewer,
                module=str(item.get("category") or "UX"),
                screen=screen,
                route=_route_for_screen(screen),
                component=str(item.get("check") or item.get("code") or "auditoria"),
                evidence=str(item.get("evidence") or item.get("title") or "Hallazgo de Experience Platform"),
                priority=str(item.get("severity") or "P3"),
                user_impact="Puede aumentar friccion, ruido visual o confusion si se confirma en Browser QA.",
                business_impact="Puede reducir percepcion premium, conversion o confianza operativa.",
                proposal=str(item.get("recommendation") or "Validar con evidencia visual y aplicar correccion minima."),
                source="experience_platform_engine",
            )
        )
        if len(mapped) >= limit:
            break
    return mapped


def _text_contains(root: Path, relative: str, fragments: Iterable[str]) -> dict[str, Any]:
    text = _read(root / relative)
    missing = [fragment for fragment in fragments if fragment not in text]
    return {"key": relative, "ok": not missing, "missing": missing, "source": relative}


def _route_checks(root: Path) -> list[dict[str, Any]]:
    routes = _routes(root)
    required = {
        "registro": "/registro",
        "login": "/login",
        "home": "/",
        "match": "/match/<match_id>",
        "team": "/team/<team_id>",
        "competition": "/competition/<competition_id>",
        "player": "/player/<player_id>",
        "shark": "/shark",
        "telegram": "/telegram",
        "perfil": "/profile",
        "logout": "/logout",
    }
    return [{"key": key, "ok": route in routes, "state": "FOUND" if route in routes else "MISSING", "source": route} for key, route in required.items()]


def _route_findings(checks: list[dict[str, Any]], reviewer: str) -> list[dict[str, Any]]:
    return [
        _finding(
            reviewer=reviewer,
            module="Beta",
            screen="app.py",
            route=str(item.get("source")),
            component="recorrido beta",
            evidence=f"Ruta {item.get('key')} no encontrada: {item.get('source')}",
            priority="P1",
            user_impact="El primer usuario podria quedar bloqueado durante el recorrido base.",
            business_impact="Impide considerar el flujo beta como completo.",
            proposal="Restaurar la ruta o documentar el alias canonico antes de beta.",
            source="app.py routes",
            state="NOT_CERTIFIED",
        )
        for item in checks
        if not item.get("ok")
    ]


def _review_product_director(root: Path, generated_at: str) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[0]
    reqs = [
        ("NEMESIS_PRODUCT_BIBLE.md", "Product Bible", "P1"),
        ("NEMESIS_SPORTS_UX_BIBLE.md", "Sports UX Bible", "P2"),
        ("NEMESIS_LIVING_ROADMAP.md", "Living Roadmap", "P1"),
        ("reports/TOP_100_IMPROVEMENTS.md", "TOP 100", "P2"),
        ("reports/RELEASE_READINESS_REPORT.md", "Release readiness", "P2"),
    ]
    checks = [{"key": label, "ok": _exists(root, path), "source": path} for path, label, _ in reqs]
    findings = _missing_file_findings(root, definition["name"], definition["module"], reqs)
    return _build_reviewer(definition, findings, checks, generated_at)


def _review_ux(root: Path, generated_at: str, experience: dict[str, Any]) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[1]
    checks = [
        {"key": "experience_platform", "ok": _exists(root, "engines/experience_platform_engine.py"), "source": "engines/experience_platform_engine.py"},
        {"key": "browser_qa", "ok": _exists(root, "tools/run_product_finalization_browser_qa.py"), "source": "tools/run_product_finalization_browser_qa.py"},
    ]
    findings = _experience_findings(experience, definition["name"], {"navigation", "copy", "component", "visual_system"}, limit=12)
    return _build_reviewer(definition, findings, checks, generated_at)


def _review_mobile(root: Path, generated_at: str, experience: dict[str, Any]) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[2]
    checks = [
        _text_contains(root, "static/v933-product.css", ["min-height: 44px", ":focus-visible"]),
        _text_contains(root, "templates/base.html", ["bottom-nav", "viewport"]),
        {"key": "mobile_browser_qa", "ok": _exists(root, "tools/run_product_finalization_browser_qa.py"), "source": "tools/run_product_finalization_browser_qa.py"},
    ]
    findings = _experience_findings(experience, definition["name"], {"density", "component"}, limit=8)
    for check in checks:
        if not check.get("ok"):
            findings.append(
                _finding(
                    reviewer=definition["name"],
                    module=definition["module"],
                    screen=str(check.get("source")),
                    route="No aplica",
                    component=str(check.get("key")),
                    evidence=f"Falta evidencia de mobile readiness: {check.get('missing') or check.get('state')}",
                    priority="P2",
                    user_impact="La experiencia movil puede perder accesibilidad tactil o contexto.",
                    business_impact="Riesgo directo para conversion movil y retencion diaria.",
                    proposal="Validar con Browser QA movil y restaurar el contrato mobile faltante.",
                    source="filesystem",
                    state="INSUFFICIENT_DATA",
                )
            )
    return _build_reviewer(definition, findings, checks, generated_at)


def _review_sports(root: Path, generated_at: str, registry: dict[str, Any]) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[3]
    keys = ["sports_domain_model", "sports_metrics", "match_context", "match_intelligence_core", "sports_graph", "team_center", "competition_center", "player_center"]
    checks = _capability_checks(registry, keys)
    findings = _findings_from_capabilities(checks, definition["name"], definition["module"])
    return _build_reviewer(definition, findings, checks, generated_at)


def _review_shark(root: Path, generated_at: str, registry: dict[str, Any]) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[4]
    keys = ["shark_intelligence_platform", "decision_engine", "match_intelligence_core", "sports_intelligence_gateway"]
    checks = _capability_checks(registry, keys)
    checks.append(_text_contains(root, "templates/shark_intelligence_center.html", ["evidencia", "limitaciones"]))
    findings = _findings_from_capabilities(checks, definition["name"], definition["module"])
    return _build_reviewer(definition, findings, checks, generated_at)


def _review_security(root: Path, generated_at: str) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[5]
    checks = [
        {"key": "security_engine", "ok": _exists(root, "engines/security_engine.py"), "source": "engines/security_engine.py"},
        {"key": "privacy_secret_guard", "ok": _exists(root, "tools/check_repository_privacy_and_secrets.py"), "source": "tools/check_repository_privacy_and_secrets.py"},
        {"key": "privacy_report", "ok": _exists(root, "reports/V938_REPOSITORY_PRIVACY_SECRET_CLASSIFICATION.md"), "source": "reports/V938_REPOSITORY_PRIVACY_SECRET_CLASSIFICATION.md"},
        _text_contains(root, "app.py", ["validate_csrf", "admin_json_forbidden", "is_admin_session"]),
    ]
    findings: list[dict[str, Any]] = []
    template_root = root / "templates"
    secret_value_pattern = re.compile(r"(?:sk_live_[A-Za-z0-9]{12,}|xox[baprs]-[A-Za-z0-9-]{20,}|[0-9]{8,}:[A-Za-z0-9_-]{30,})")
    env_name_pattern = re.compile(r"(?:SECRET_KEY|TELEGRAM_BOT_TOKEN|STRIPE_SECRET|TELEGRAM_CHAT_ID)")
    if template_root.exists():
        for path in template_root.glob("*.html"):
            body = _read(path)
            value_match = secret_value_pattern.search(body)
            env_match = env_name_pattern.search(body)
            if value_match:
                findings.append(
                    _finding(
                        reviewer=definition["name"],
                        module=definition["module"],
                        screen=path.relative_to(root).as_posix(),
                        route=_route_for_screen(path.name),
                        component="texto visible",
                        evidence="Patron compatible con valor secreto real en plantilla visible.",
                        priority="P1",
                        user_impact="Podria exponer detalles internos o secretos al usuario.",
                        business_impact="Riesgo reputacional y de seguridad.",
                        proposal="Retirar el valor, rotar credencial si procede y ejecutar Secret Guard.",
                        source="template_scan",
                        state="REQUIRES_REVIEW",
                    )
                )
            elif env_match:
                findings.append(
                    _finding(
                        reviewer=definition["name"],
                        module=definition["module"],
                        screen=path.relative_to(root).as_posix(),
                        route=_route_for_screen(path.name),
                        component="copy admin",
                        evidence=f"Nombre de variable visible: {env_match.group(0)}; no se detecto valor secreto.",
                        priority="P3",
                        user_impact="Puede sonar tecnico en una pantalla admin, pero no expone credenciales.",
                        business_impact="Conviene mantenerlo como texto de diagnostico admin, nunca como informacion cliente.",
                        proposal="Mantener solo en admin o sustituir por descripcion funcional si aparece en superficie cliente.",
                        source="template_scan",
                        state="PARTIALLY_VERIFIED",
                    )
                )
    findings.extend(
        _missing_file_findings(
            root,
            definition["name"],
            definition["module"],
            [(str(c["source"]), str(c["key"]), "P2") for c in checks if not c.get("ok") and isinstance(c.get("source"), str)],
        )
    )
    return _build_reviewer(definition, findings, checks, generated_at)


def _review_performance(root: Path, generated_at: str, experience: dict[str, Any]) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[6]
    checks = [
        {"key": "performance_budget", "ok": _exists(root, "tools/check_v933_performance.py"), "source": "tools/check_v933_performance.py"},
        {"key": "browser_qa", "ok": _exists(root, "tools/run_product_finalization_browser_qa.py"), "source": "tools/run_product_finalization_browser_qa.py"},
        {"key": "scalability_report", "ok": _exists(root, "reports/SCALABILITY_REPORT.md"), "source": "reports/SCALABILITY_REPORT.md"},
        {"key": "cache_engine", "ok": _exists(root, "engines/cache_engine.py"), "source": "engines/cache_engine.py"},
    ]
    findings = _experience_findings(experience, definition["name"], {"density"}, limit=8)
    findings.extend(
        _missing_file_findings(
            root,
            definition["name"],
            definition["module"],
            [(str(c["source"]), str(c["key"]), "P2") for c in checks if not c.get("ok") and isinstance(c.get("source"), str)],
        )
    )
    return _build_reviewer(definition, findings, checks, generated_at)


def _review_commercial(root: Path, generated_at: str) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[7]
    checks = [
        _text_contains(root, "templates/membership.html", ["FREE", "PRO", "ELITE"]),
        {"key": "membership_engine", "ok": _exists(root, "engines/membership_engine.py"), "source": "engines/membership_engine.py"},
        {"key": "stripe_engine", "ok": _exists(root, "engines/stripe_payments_engine.py"), "source": "engines/stripe_payments_engine.py"},
        {"key": "responsible_legal", "ok": _exists(root, "reports/V939_RESPONSIBLE_GAMBLING_AND_ETHICS_QA.md") or _exists(root, "reports/RESPONSIBLE_GAMBLING_AND_ETHICS_QA.md"), "source": "responsible_gambling_report"},
    ]
    findings = _missing_file_findings(root, definition["name"], definition["module"], [(str(c["source"]), str(c["key"]), "P2") for c in checks if not c.get("ok") and "/" in str(c.get("source"))])
    return _build_reviewer(definition, findings, checks, generated_at)


def _review_marketing(root: Path, generated_at: str) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[8]
    checks = [
        _text_contains(root, "templates/home.html", ["NeMeSiS", "SHARK"]),
        {"key": "product_strategy", "ok": _exists(root, "PRODUCT_STRATEGY.md") or _exists(root, "NEMESIS_PRODUCT_BIBLE.md"), "source": "PRODUCT_STRATEGY.md / NEMESIS_PRODUCT_BIBLE.md"},
        {"key": "commercial_readiness", "ok": _exists(root, "reports/COMMERCIAL_READINESS_REPORT.md") or _exists(root, "COMMERCIAL_RELEASE_PLAN.md"), "source": "commercial readiness docs"},
    ]
    findings: list[dict[str, Any]] = []
    for check in checks:
        if not check.get("ok"):
            findings.append(
                _finding(
                    reviewer=definition["name"],
                    module=definition["module"],
                    screen=str(check.get("source")),
                    route="/",
                    component=str(check.get("key")),
                    evidence="No se encontro evidencia documental o visible para esta pieza de posicionamiento.",
                    priority="P2",
                    user_impact="El usuario podria no entender por que NeMeSiS es diferente.",
                    business_impact="Debilita conversion y recomendacion organica.",
                    proposal="Completar la evidencia de posicionamiento antes del lanzamiento comercial.",
                    source="filesystem",
                    state="INSUFFICIENT_DATA",
                )
            )
    return _build_reviewer(definition, findings, checks, generated_at)


def _review_beta(root: Path, generated_at: str) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[9]
    checks = _route_checks(root)
    findings = _route_findings(checks, definition["name"])
    return _build_reviewer(definition, findings, checks, generated_at)


def _review_visual(root: Path, generated_at: str, experience: dict[str, Any]) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[10]
    checks = [
        {"key": "visual_density_auditor", "ok": _exists(root, "engines/experience_platform_engine.py"), "source": "engines/experience_platform_engine.py"},
        {"key": "visual_browser_qa", "ok": _exists(root, "tools/run_product_finalization_browser_qa.py"), "source": "tools/run_product_finalization_browser_qa.py"},
    ]
    findings = _experience_findings(experience, definition["name"], {"density", "visual_system"}, limit=12)
    return _build_reviewer(definition, findings, checks, generated_at)


def _review_operations(root: Path, generated_at: str) -> dict[str, Any]:
    definition = REVIEWER_DEFINITIONS[11]
    checks = [
        {"key": "operations_center", "ok": _exists(root, "engines/company_operations_center_engine.py"), "source": "engines/company_operations_center_engine.py"},
        {"key": "operations_panel", "ok": _exists(root, "templates/admin_operations_center.html"), "source": "templates/admin_operations_center.html"},
        {"key": "observability", "ok": _exists(root, "engines/observability_engine.py"), "source": "engines/observability_engine.py"},
        {"key": "scheduler", "ok": _exists(root, "engines/scheduler_engine.py"), "source": "engines/scheduler_engine.py"},
        {"key": "backup_restore", "ok": _exists(root, "engines/data_vault_engine.py") or _exists(root, "engines/disaster_recovery_engine.py"), "source": "backup/restore engines"},
        {"key": "release_gate", "ok": _exists(root, "reports/FINAL_RELEASE_GATE.md") or _exists(root, "reports/RELEASE_GATE_STATUS.md"), "source": "release gate reports"},
    ]
    findings: list[dict[str, Any]] = []
    for check in checks:
        if not check.get("ok"):
            findings.append(
                _finding(
                    reviewer=definition["name"],
                    module=definition["module"],
                    screen=str(check.get("source")),
                    route="/admin/operations-center",
                    component=str(check.get("key")),
                    evidence="Evidencia operacional requerida no encontrada localmente.",
                    priority="P2",
                    user_impact="La beta podria operar con un punto ciego no visible para administracion.",
                    business_impact="Riesgo de soporte, downtime o respuesta lenta ante incidentes.",
                    proposal="Completar la evidencia operacional o mantener el gate como PARTIAL.",
                    source="filesystem",
                    state="INSUFFICIENT_DATA",
                )
            )
    return _build_reviewer(definition, findings, checks, generated_at)


def build_product_review_system_snapshot(project_root: str | Path | None = None, app_version: str = "LOCAL") -> dict[str, Any]:
    root = _root(project_root)
    generated_at = _now()
    experience = build_experience_platform_snapshot(root)
    registry = build_sports_platform_contract_registry(root)
    reviewers = [
        _review_product_director(root, generated_at),
        _review_ux(root, generated_at, experience),
        _review_mobile(root, generated_at, experience),
        _review_sports(root, generated_at, registry),
        _review_shark(root, generated_at, registry),
        _review_security(root, generated_at),
        _review_performance(root, generated_at, experience),
        _review_commercial(root, generated_at),
        _review_marketing(root, generated_at),
        _review_beta(root, generated_at),
        _review_visual(root, generated_at, experience),
        _review_operations(root, generated_at),
    ]
    all_findings = [finding for reviewer in reviewers for finding in reviewer["findings"]]
    counts = Counter(item.get("priority", "P3") for item in all_findings)
    average_score = round(sum(item["score"] for item in reviewers) / max(len(reviewers), 1), 1)
    score_explanation = [f"Media de {len(reviewers)} revisores especializados.", "Cada revisor parte de 100 y descuenta penalizaciones fijas por P0/P1/P2/P3 y evidencia obligatoria ausente."]
    blockers = counts.get("P0", 0) + counts.get("P1", 0)
    status = "PASS" if blockers == 0 and len(reviewers) == len(REVIEWER_DEFINITIONS) else "REQUIRES_REVIEW"
    if status == "PASS" and all_findings:
        status = "PASS_WITH_REVIEW_ITEMS"
    roadmap_candidates = [
        {
            "id": f"PRS-{index:03d}",
            "reviewer": item["reviewer"],
            "priority": item["priority"],
            "module": item["module"],
            "screen": item["screen"],
            "route": item["route"],
            "proposal": item["proposal"],
            "evidence": item["evidence"],
            "approved": False,
            "automatic_execution_allowed": False,
            "requires_human_approval": True,
        }
        for index, item in enumerate(all_findings, start=1)
    ]
    return {
        "contract": PRODUCT_REVIEW_SYSTEM_CONTRACT,
        "center_contract": PRODUCT_REVIEW_CENTER_CONTRACT,
        "quality_team_contract": QUALITY_TEAM_CONTRACT,
        "version": app_version,
        "generated_at_madrid": generated_at,
        "environment": "local_filesystem_read_only",
        "status": status,
        "score": average_score,
        "score_explanation": score_explanation,
        "reviewer_count": len(reviewers),
        "reviewers_expected": len(REVIEWER_DEFINITIONS),
        "reviewers": reviewers,
        "findings": all_findings,
        "findings_summary": {"P0": counts.get("P0", 0), "P1": counts.get("P1", 0), "P2": counts.get("P2", 0), "P3": counts.get("P3", 0), "total": len(all_findings)},
        "roadmap_candidates": roadmap_candidates[:50],
        "source_contracts": {
            "experience_platform": experience.get("contract"),
            "sports_platform": registry.get("contract"),
        },
        "guardrails": dict(GUARDRAILS),
        "no_generative_ai": True,
        "no_chatbot": True,
        "no_fictitious_assistants": True,
        "production_modified": False,
        "deploy_executed": False,
        "push_executed": False,
        "next_action": "Revisar hallazgos P0/P1 si existen; convertir solo hallazgos aprobados en mejoras candidatas.",
    }


def product_review_system_snapshot(project_root: str | Path | None = None, app_version: str = "LOCAL") -> dict[str, Any]:
    return build_product_review_system_snapshot(project_root, app_version)
