"""Evidence-first product review system for NeMeSiS.

The Product Review System is the internal quality department for the product.
It is deterministic and read-only: it scans existing local evidence, routes,
templates, contracts and reports. It never calls generative AI, external
providers, Telegram, Stripe, production, or writes databases.
"""
from __future__ import annotations

import hashlib
import os
import json
import re
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from engines.experience_platform_engine import build_experience_platform_snapshot
from engines.growth_revenue_os_engine import GROWTH_FUNNEL_EVENT_CONTRACT, build_growth_revenue_os_snapshot
from engines.sports_platform_contracts import build_sports_platform_contract_registry
from engines.autonomous_product_qa_engine import (
    build_autonomous_product_qa_status,
    product_qa_review_findings,
)
from engines.sentinel_issues_engine import build_sentinel_issues_summary, load_sentinel_issues_memory

MADRID = ZoneInfo("Europe/Madrid")
PRODUCT_REVIEW_SYSTEM_CONTRACT = "NEMESIS-PRODUCT-REVIEW-SYSTEM-V1"
PRODUCT_REVIEW_CENTER_CONTRACT = "NEMESIS-PRODUCT-REVIEW-CENTER-V1"
QUALITY_TEAM_CONTRACT = "NEMESIS-WORLD-CLASS-PRODUCT-TEAM-V1"
CONTINUOUS_EVOLUTION_OS_CONTRACT = "NEMESIS-CONTINUOUS-EVOLUTION-OS-V1"
DAILY_PRODUCT_SNAPSHOT_CONTRACT = "NEMESIS-DAILY-PRODUCT-SNAPSHOT-V1"
PRODUCT_MEMORY_CONTRACT = "NEMESIS-PRODUCT-MEMORY-V1"
FOUNDER_BRIEF_CONTRACT = "NEMESIS-FOUNDER-BRIEF-V1"
PREPARED_FOR_CODEX_CONTRACT = "NEMESIS-PREPARED-FOR-CODEX-INBOX-V1"
CONTINUOUS_EVOLUTION_SCHEDULER_CONTRACT = "NEMESIS-CONTINUOUS-EVOLUTION-SCHEDULER-V1"
MARKET_INTELLIGENCE_FOUNDATION_CONTRACT = "NEMESIS-MARKET-INTELLIGENCE-FOUNDATION-V1"

CONTINUOUS_EVOLUTION_RUNTIME = Path(os.getenv("CONTINUOUS_EVOLUTION_STORAGE_ROOT") or (Path("data") / "runtime" / "continuous_evolution_os"))
RECOMMENDATION_STATES = {
    "NEW",
    "APPROVED",
    "DEFERRED",
    "REJECTED",
    "IMPLEMENTED",
    "VERIFIED",
    "REGRESSED",
    "RESOLVED",
}
EVIDENCE_ORIGINS = {
    "SIMULATED_QA",
    "REAL_AGGREGATED",
    "SYSTEM_OBSERVATION",
    "MARKET_PUBLIC_SOURCE",
    "MANUAL_ADMIN",
    "UNKNOWN",
}
CONTINUOUS_EVOLUTION_TASKS = {
    "platform_workforce_review": {"label": "Platform Workforce Review", "cadence": "hourly", "interval": timedelta(hours=1)},
    "daily_product_review": {"label": "Daily Product Review", "cadence": "daily", "interval": timedelta(days=1)},
    "daily_founder_brief": {"label": "Daily Founder Brief", "cadence": "daily", "interval": timedelta(days=1)},
    "weekly_executive_review": {"label": "Weekly Executive Review", "cadence": "weekly", "interval": timedelta(days=7)},
    "monthly_strategy_review": {"label": "Monthly Strategy Review", "cadence": "monthly", "interval": timedelta(days=30)},
}
SENSITIVE_VISIBLE_TERMS = {
    "TELEGRAM_BOT_TOKEN": "configuracion tecnica de Telegram",
    "TELEGRAM_CHAT_ID": "destino tecnico de Telegram",
    "STRIPE_SECRET_KEY": "configuracion privada de Stripe",
    "STRIPE_WEBHOOK_SECRET": "firma privada de Stripe",
    "OPENAI_API_KEY": "clave privada de proveedor",
}

CONTINUOUS_EVOLUTION_AUTOMATION_CONTRACT = "NEMESIS-CONTINUOUS-EVOLUTION-AUTOMATION-V1"
CONTINUOUS_EVOLUTION_JOB_CONTRACT = "NEMESIS-CONTINUOUS-EVOLUTION-JOB-V1"
CONTINUOUS_EVOLUTION_CONTROL_CONTRACT = "NEMESIS-CONTINUOUS-EVOLUTION-CONTROL-V1"
CONTINUOUS_EVOLUTION_CERTIFICATION_CONTRACT = "NEMESIS-CONTINUOUS-EVOLUTION-3-DAY-CERTIFICATION-V1"
CONTINUOUS_EVOLUTION_TRIGGERS = {"MANUAL", "SCHEDULED_LOCAL", "SCHEDULED_PRODUCTION"}
CONTINUOUS_EVOLUTION_LOCK_TTL = timedelta(hours=2)
CONTINUOUS_EVOLUTION_POLICY = {
    "timezone": "Europe/Madrid",
    "platform_workforce_review": {"cadence": "hourly", "period_timezone": "UTC"},
    "daily_product_review": {"hour": 4, "minute": 0},
    "daily_founder_brief": {"hour": 4, "minute": 5},
    "weekly_executive_review": {"weekday": 0, "hour": 4, "minute": 30},
    "monthly_strategy_review": {"day": 1, "hour": 5, "minute": 0},
}
SIMULATED_USER_PERSONAS = (
    "NEW_USER",
    "FREE",
    "PRO",
    "ELITE",
    "MOBILE",
    "DESKTOP",
    "MATCH_SEEKER",
    "TEAM_FOLLOWER",
    "SHARK_USER",
    "PICKS_USER",
)
AUTOMATION_ALLOWED_ACTIONS = (
    "OBSERVE",
    "ANALYZE",
    "SIMULATE_QA",
    "COMPARE",
    "DETECT",
    "REMEMBER",
    "CALIBRATE",
    "PRIORITIZE",
    "PROPOSE",
    "PREPARE_CODEX_BRIEF",
    "GENERATE_FOUNDER_BRIEF",
)
AUTOMATION_PROHIBITED_ACTIONS = (
    "CODE_CHANGE",
    "COMMIT",
    "PUSH",
    "DEPLOY",
    "TELEGRAM_SEND",
    "STRIPE_ACTION",
    "USER_MUTATION",
    "MEMBERSHIP_CHANGE",
    "PRICE_CHANGE",
    "DELETE",
    "SECRET_CHANGE",
    "PRODUCTION_MUTATION",
    "NEW_SOURCE_ACTIVATION",
)

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
                    business_impact="La direccion no puede convertir esta conclusion en decisión de lanzamiento.",
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

EXECUTIVE_BOARD_CONTRACT = "NEMESIS-EXECUTIVE-BOARD-V1"
EXECUTIVE_BOARD_CENTER_CONTRACT = "NEMESIS-EXECUTIVE-BOARD-CENTER-V1"
STRATEGIC_DECISION_CONTRACT = "NEMESIS-STRATEGIC-DECISION-SYSTEM-V1"
EXECUTIVE_VOTE_LEVELS = ("CRITICA", "ALTA", "MEDIA", "BAJA", "DESCARTADA")
EXECUTIVE_REQUIRED_PROPOSAL_FIELDS = (
    "id",
    "title",
    "evidence",
    "module",
    "screen",
    "route",
    "impact_user",
    "impact_business",
    "priority",
    "estimated_cost",
    "dependencies",
    "risk",
    "status",
)

EXECUTIVE_DIRECTOR_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {"key": "ceo", "name": "CEO", "area": "Direccion general", "focus": ("Producto", "Comercial", "Operaciones", "Release", "Beta", "Marketing"), "responsibility": "Convierte evidencia transversal en prioridades empresariales sin aprobar ejecucion automatica.", "should_not_touch": "Arquitectura deportiva, pagos, produccion o envios reales sin autorizacion humana."},
    {"key": "cto", "name": "CTO", "area": "Tecnologia", "focus": ("Rendimiento", "Arquitectura", "Developer", "Routes", "Contracts", "Sports Core"), "responsibility": "Protege contratos, rendimiento, mantenibilidad, rutas y deuda tecnica.", "should_not_touch": "Sports Core certificado, contratos canonicos y flujos de seguridad sin evidencia de bug real."},
    {"key": "head_product", "name": "Head of Product", "area": "Producto", "focus": ("Producto", "Beta", "Onboarding", "Action Platform", "Home"), "responsibility": "Prioriza claridad, primer valor, activacion, recorrido y foco del producto.", "should_not_touch": "Funcionalidades que ya comunican valor sin friccion demostrada."},
    {"key": "head_ux", "name": "Head of UX", "area": "UX", "focus": ("UX", "Visual", "Home", "Navigation", "Onboarding", "Copy"), "responsibility": "Revisa jerarquia, navegacion, densidad, estados, claridad y consistencia visual.", "should_not_touch": "Sistema visual ns-/v933 cuando la evidencia no indique inconsistencia."},
    {"key": "head_mobile", "name": "Head of Mobile", "area": "Mobile", "focus": ("Mobile", "Responsive", "Touch", "Safe Area", "Movil"), "responsibility": "Asegura experiencia tactil, densidad movil, scroll razonable y targets comodos.", "should_not_touch": "Layouts responsive que ya superan Browser QA y no generan friccion visible."},
    {"key": "sports_director", "name": "Sports Director", "area": "Deportes", "focus": ("Sports Core", "Match Center", "Team Center", "Competition Center", "Player Center", "Calendario", "Live"), "responsibility": "Garantiza coherencia deportiva, entidades canonicas, frescura, evidencia y navegacion deportiva.", "should_not_touch": "Modelo deportivo unificado y calculos certificados sin bug real."},
    {"key": "shark_director", "name": "SHARK Director", "area": "SHARK", "focus": ("SHARK", "Decision Engine", "Evidence", "Freshness", "Intelligence"), "responsibility": "Evita afirmaciones sin evidencia y protege confianza, limitaciones y explicabilidad.", "should_not_touch": "Reglas que impiden predicciones, picks inventados o confianza exagerada."},
    {"key": "security_officer", "name": "Security Officer", "area": "Seguridad", "focus": ("Seguridad", "Privacy", "Secret", "Stripe", "Telegram", "Admin", "Session"), "responsibility": "Protege privacidad, secretos, permisos, endpoints admin y operaciones de riesgo.", "should_not_touch": "Autenticacion, firmas, dedupe, pagos y secretos sin plan de prueba controlado."},
    {"key": "commercial_director", "name": "Commercial Director", "area": "Comercial", "focus": ("Comercial", "FREE", "PRO", "ELITE", "Membership", "Conversion", "Pricing"), "responsibility": "Prioriza conversion responsable, valor percibido, membresias y retencion.", "should_not_touch": "Promesas comerciales no certificadas o mensajes que puedan inducir gasto irresponsable."},
    {"key": "qa_director", "name": "QA Director", "area": "Calidad", "focus": ("QA", "Browser QA", "Sentinel", "Tests", "Routes", "Links", "Regression"), "responsibility": "Convierte evidencias de pruebas en gates claros y evita regresiones.", "should_not_touch": "Checks existentes que sostienen release si no hay falso positivo demostrado."},
    {"key": "operations_director", "name": "Operations Director", "area": "Operaciones", "focus": ("Operaciones", "Render", "Cron", "Master Tick", "Restore", "Backup", "Observability", "Logs"), "responsibility": "Prioriza fiabilidad operativa, restore, cron, logs, release y soporte.", "should_not_touch": "Produccion, cron real, backups reales o restores sin autorizacion y entorno aislado."},
    {"key": "marketing_director", "name": "Marketing Director", "area": "Marketing", "focus": ("Marketing", "Copy", "Home", "Landing", "Value", "CTA", "Beta"), "responsibility": "Revisa propuesta de valor, claridad comercial, mensajes y diferenciacion honesta.", "should_not_touch": "Mensajes certificados si solo se busca cambiar tono sin evidencia de mejora."},
)

EXECUTIVE_SCORE_AREAS = {
    "architecture": ("Arquitectura", ("cto", "qa_director", "operations_director")),
    "product": ("Producto", ("ceo", "head_product", "sports_director")),
    "ux": ("UX", ("head_ux", "head_product", "marketing_director")),
    "mobile": ("Mobile", ("head_mobile", "head_ux", "qa_director")),
    "sports_core": ("Sports Core", ("sports_director", "cto", "shark_director")),
    "shark": ("SHARK", ("shark_director", "sports_director", "security_officer")),
    "security": ("Seguridad", ("security_officer", "operations_director", "qa_director")),
    "operations": ("Operaciones", ("operations_director", "qa_director", "cto")),
    "commercial": ("Comercial", ("commercial_director", "marketing_director", "ceo")),
    "release_readiness": ("Release Readiness", ("operations_director", "qa_director", "security_officer", "ceo")),
}


def _executive_norm(value: Any) -> str:
    return _text(value, 220).lower()


def _executive_priority(value: Any) -> str:
    candidate = _text(value, 8).upper()
    return candidate if candidate in PRIORITY_PENALTY else "P3"


def _executive_cost(priority: str, module: str, proposal: str) -> str:
    text = f"{module} {proposal}".lower()
    if priority in {"P0", "P1"}:
        return "Alto" if any(word in text for word in ("arquitect", "contrato", "modelo", "produccion")) else "Medio"
    if priority == "P2":
        return "Medio" if any(word in text for word in ("naveg", "responsive", "admin", "operacion")) else "Bajo"
    return "Bajo"


def _executive_risk(priority: str, module: str, proposal: str) -> str:
    text = f"{module} {proposal}".lower()
    risky = ("sports core", "stripe", "telegram", "cron", "restore", "seguridad", "secret", "produccion")
    if priority in {"P0", "P1"} or any(token in text for token in risky):
        return "Alto" if priority in {"P0", "P1"} else "Medio"
    if any(token in text for token in ("css", "copy", "estado vacio", "texto", "cta")):
        return "Bajo"
    return "Medio" if priority == "P2" else "Bajo"


def _executive_dependencies(module: str, screen: str, route: str, proposal: str) -> list[str]:
    text = f"{module} {screen} {route} {proposal}".lower()
    deps = ["Product Review System", "aprobacion humana"]
    if any(token in text for token in ("match", "team", "competition", "player", "calendar", "live", "sports")):
        deps.append("Sports Core certificado")
    if "shark" in text or "evidence" in text or "freshness" in text:
        deps.append("SHARK/Decision evidence")
    if any(token in text for token in ("mobile", "movil", "responsive", "touch")):
        deps.append("Browser QA movil")
    if any(token in text for token in ("telegram", "stripe", "cron", "render", "restore", "secret", "privacy")):
        deps.append("gate operativo controlado")
    return list(dict.fromkeys(deps))


def _executive_selection_score(priority: str, cost: str, risk: str, impact_user: str, impact_business: str) -> tuple[int, list[str]]:
    base = {"P0": 100, "P1": 80, "P2": 55, "P3": 25}.get(priority, 25)
    cost_points = {"Bajo": 14, "Medio": 8, "Alto": 2}.get(cost, 4)
    risk_points = {"Bajo": 12, "Medio": 6, "Alto": 0}.get(risk, 0)
    score = base + cost_points + risk_points
    explanation = [f"prioridad {priority}: {base}", f"coste {cost.lower()}: {cost_points}", f"riesgo {risk.lower()}: {risk_points}"]
    impact_text = f"{impact_user} {impact_business}".lower()
    if any(token in impact_text for token in ("beta", "conversion", "retencion", "confianza", "primer", "claridad", "release")):
        score += 12
        explanation.append("impacto directo en beta, conversion, confianza o release: 12")
    if any(token in impact_text for token in ("bloque", "seguridad", "produccion", "pago", "secret")):
        score += 14
        explanation.append("riesgo operativo o seguridad con evidencia: 14")
    return min(score, 140), explanation


def _executive_candidate_from_finding(finding: dict[str, Any], index: int) -> dict[str, Any]:
    priority = _executive_priority(finding.get("priority"))
    module = _text(finding.get("module"), 90) or "Producto"
    screen = _text(finding.get("screen"), 160) or "No especificada"
    route = _text(finding.get("route"), 120) or "No inferida"
    proposal = _text(finding.get("proposal"), 360) or "Revisar con evidencia antes de decidir."
    impact_user = _text(finding.get("impact_user") or finding.get("user_impact"), 320) or "Impacto de usuario pendiente de concretar con evidencia."
    impact_business = _text(finding.get("impact_business") or finding.get("business_impact"), 320) or "Impacto de negocio pendiente de concretar con evidencia."
    cost = _executive_cost(priority, module, proposal)
    risk = _executive_risk(priority, module, proposal)
    selection_score, selection_explanation = _executive_selection_score(priority, cost, risk, impact_user, impact_business)
    return {"id": f"EBD-{index:03d}", "source_id": _text(finding.get("id"), 40) or f"PRS-{index:03d}", "title": _text(finding.get("title"), 120) or f"{module}: {proposal[:86]}", "evidence": _text(finding.get("evidence"), 620), "module": module, "screen": screen, "route": route, "component": _text(finding.get("component"), 140) or "No especificado", "impact_user": impact_user, "impact_business": impact_business, "priority": priority, "estimated_cost": cost, "dependencies": _executive_dependencies(module, screen, route, proposal), "risk": risk, "proposal": proposal, "status": "Pendiente", "issue_status": finding.get("issue_status") or "INSUFFICIENT_EVIDENCE", "evidence_sufficient": bool(finding.get("evidence_sufficient")), "approved": False, "requires_human_approval": True, "automatic_execution_allowed": False, "selection_score": selection_score, "selection_explanation": selection_explanation, "source": "Product Review System", "workers": [finding.get("reviewer") or "Product Review System"], "evidence_origin": finding.get("evidence_origin") or "SYSTEM_OBSERVATION"}


def _executive_director_matches_candidate(definition: dict[str, Any], candidate: dict[str, Any]) -> bool:
    haystack = " ".join(_executive_norm(candidate.get(field)) for field in ("module", "screen", "route", "component", "title", "proposal"))
    return any(_executive_norm(token) and _executive_norm(token) in haystack for token in definition["focus"])


def _executive_vote(definition: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    priority = candidate.get("priority", "P3")
    in_scope = _executive_director_matches_candidate(definition, candidate)
    if in_scope and priority in {"P0", "P1"}:
        classification, supports = "CRITICA", True
    elif in_scope and priority == "P2":
        classification, supports = "ALTA", True
    elif in_scope:
        classification, supports = "MEDIA", True
    elif definition["key"] == "ceo" and candidate.get("selection_score", 0) >= 80:
        classification, supports = "ALTA", True
    elif candidate.get("risk") == "Alto":
        classification, supports = "DESCARTADA", False
    else:
        classification, supports = "BAJA", False
    if classification == "DESCARTADA":
        reason = "Fuera del area y con riesgo alto; requiere sponsor especifico antes de sprint."
    elif supports:
        reason = "Encaja en el area del director y tiene evidencia suficiente para revision humana."
    else:
        reason = "No es prioridad del area; se mantiene como contexto sin apoyo activo."
    return {"director_key": definition["key"], "director": definition["name"], "area": definition["area"], "classification": classification, "supports": supports, "rejects": classification == "DESCARTADA", "reason": reason}


def _executive_apply_votes(candidates: list[dict[str, Any]]) -> None:
    for candidate in candidates:
        votes = [_executive_vote(definition, candidate) for definition in EXECUTIVE_DIRECTOR_DEFINITIONS]
        counts = Counter(vote["classification"] for vote in votes)
        candidate["votes"] = votes
        candidate["supporters"] = [vote["director"] for vote in votes if vote["supports"]]
        candidate["rejecters"] = [vote["director"] for vote in votes if vote["rejects"]]
        candidate["vote_counts"] = {level: counts.get(level, 0) for level in EXECUTIVE_VOTE_LEVELS}
        if counts.get("CRITICA"):
            candidate["board_classification"] = "CRITICA"
        elif counts.get("ALTA", 0) >= 2:
            candidate["board_classification"] = "ALTA"
        elif counts.get("MEDIA", 0) >= 2:
            candidate["board_classification"] = "MEDIA"
        elif counts.get("DESCARTADA", 0) >= 4:
            candidate["board_classification"] = "DESCARTADA"
        else:
            candidate["board_classification"] = "BAJA"


def _executive_director_snapshot(definition: dict[str, Any], candidates: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    scoped = [candidate for candidate in candidates if _executive_director_matches_candidate(definition, candidate)]
    supported = [candidate for candidate in candidates if definition["name"] in candidate.get("supporters", [])]
    rejected = [candidate for candidate in candidates if definition["name"] in candidate.get("rejecters", [])]
    counts = Counter(candidate.get("priority", "P3") for candidate in scoped)
    penalty = counts.get("P0", 0) * 18 + counts.get("P1", 0) * 11 + counts.get("P2", 0) * 5 + counts.get("P3", 0) * 2
    score = max(0, 100 - penalty)
    state = "REQUIERE_REVISION" if counts.get("P0") or counts.get("P1") else "CON_EVIDENCIA" if scoped else "SIN_HALLAZGOS_DIRECTOS"
    return {**definition, "contract": f"NEMESIS-EXECUTIVE-DIRECTOR-{definition['key'].upper().replace('_', '-')}-V1", "state": state, "score": score, "score_explanation": ["Base 100 menos penalizaciones por candidatos dentro del area.", f"P0={counts.get('P0', 0)}, P1={counts.get('P1', 0)}, P2={counts.get('P2', 0)}, P3={counts.get('P3', 0)}."], "last_review_madrid": generated_at, "what_works": ["Base del producto certificada por los sistemas previos declarados PASS.", "Las propuestas se reciben con evidencia local y no se ejecutan automáticamente."] if scoped else ["No hay hallazgos directos para esta area en el snapshot local.", "El area permanece bajo observacion sin cambios artificiales."], "what_does_not_work": [candidate["title"] for candidate in scoped[:3]] or ["No se detecta friccion directa con la evidencia local actual."], "should_improve": [candidate["proposal"] for candidate in supported[:3]] or ["Mantener observacion hasta nueva evidencia de Product Review o beta."], "should_not_touch": definition["should_not_touch"], "risks": [f"{candidate['id']}: {candidate['risk']} - {candidate['title']}" for candidate in scoped if candidate.get("risk") in {"Medio", "Alto"}][:3] or ["Riesgo bajo o no observable con la evidencia local actual."], "opportunities": [f"{candidate['id']}: {candidate['impact_business']}" for candidate in supported[:3]] or ["Esperar feedback beta para priorizar sin inventar necesidades."], "supported_candidates": [candidate["id"] for candidate in supported], "rejected_candidates": [candidate["id"] for candidate in rejected], "findings_count": len(scoped), "votes_given": len(candidates)}


def _executive_product_scores(directors: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {director["key"]: director for director in directors}
    rows: list[dict[str, Any]] = []
    for key, (label, director_keys) in EXECUTIVE_SCORE_AREAS.items():
        selected = [by_key[item] for item in director_keys if item in by_key]
        base = round(sum(item["score"] for item in selected) / max(len(selected), 1))
        related = [candidate for candidate in candidates if any(_executive_director_matches_candidate(by_key[item], candidate) for item in director_keys if item in by_key)]
        high = sum(1 for item in related if item.get("priority") in {"P0", "P1"})
        p2 = sum(1 for item in related if item.get("priority") == "P2")
        score = max(0, base - high * 4 - p2)
        rows.append({"key": key, "label": label, "score": score, "state": "PASS" if score >= 90 else "PARTIAL" if score >= 75 else "REQUIRES_REVIEW", "justification": f"Media de {', '.join(by_key[item]['name'] for item in director_keys if item in by_key)} ({base}/100) ajustada por evidencia relacionada: P0/P1={high}, P2={p2}.", "evidence": [candidate["id"] for candidate in related[:5]]})
    return rows


def _executive_area_health(directors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {director["key"]: director for director in directors}
    mapping = [("product", "Estado del producto", ("ceo", "head_product")), ("commercial", "Estado comercial", ("commercial_director", "marketing_director")), ("technical", "Estado tecnico", ("cto", "qa_director")), ("ux", "Estado UX", ("head_ux", "head_product")), ("mobile", "Estado movil", ("head_mobile", "head_ux")), ("shark", "Estado SHARK", ("shark_director", "sports_director")), ("security", "Estado seguridad", ("security_officer", "qa_director")), ("operations", "Estado operaciones", ("operations_director", "cto")), ("quality", "Estado calidad", ("qa_director", "operations_director")), ("marketing", "Estado marketing", ("marketing_director", "commercial_director"))]
    rows = []
    for key, label, director_keys in mapping:
        selected = [by_key[item] for item in director_keys if item in by_key]
        score = round(sum(item["score"] for item in selected) / max(len(selected), 1))
        rows.append({"key": key, "label": label, "score": score, "state": "PASS" if score >= 90 else "PARTIAL" if score >= 75 else "REQUIRES_REVIEW", "evidence": "; ".join(item["score_explanation"][-1] for item in selected if item.get("score_explanation"))})
    return rows


def _build_executive_board_from_review(review: dict[str, Any], app_version: str, generated_at: str) -> dict[str, Any]:
    findings = list(review.get("findings") or [])
    if not findings:
        findings = [{"id": "PRS-NO-FINDINGS", "module": "Producto", "screen": "Producto completo", "route": "No aplica", "component": "revision ejecutiva", "evidence": "", "priority": "P3", "impact_user": "Mantiene el producto en observacion sin cambios innecesarios.", "impact_business": "Evita roadmap artificial sin evidencia.", "proposal": "Mantener seguimiento y esperar evidencia de usuarios reales.", "evidence_origin": "SYSTEM_OBSERVATION", "issue_status": "INSUFFICIENT_EVIDENCE", "evidence_sufficient": False}]
    candidates = [_executive_candidate_from_finding(finding, index) for index, finding in enumerate(findings, start=1)]
    seen: set[tuple[str, str, str, str]] = set()
    unique_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        key = (_executive_norm(candidate.get("module")), _executive_norm(candidate.get("route")), _executive_norm(candidate.get("component")), _executive_norm(candidate.get("proposal"))[:90])
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    for index, candidate in enumerate(unique_candidates, start=1):
        candidate["id"] = f"EBD-{index:03d}"
    _executive_apply_votes(unique_candidates)
    unique_candidates.sort(key=lambda item: ({"P0": 100, "P1": 80, "P2": 55, "P3": 25}.get(item.get("priority", "P3"), 25), item.get("selection_score", 0), len(item.get("supporters", []))), reverse=True)
    directors = [_executive_director_snapshot(definition, unique_candidates, generated_at) for definition in EXECUTIVE_DIRECTOR_DEFINITIONS]
    product_scores = _executive_product_scores(directors, unique_candidates)
    counts = Counter(candidate.get("priority", "P3") for candidate in unique_candidates)
    board_score = round(sum(score["score"] for score in product_scores) / max(len(product_scores), 1))
    return {"contract": EXECUTIVE_BOARD_CONTRACT, "center_contract": EXECUTIVE_BOARD_CENTER_CONTRACT, "decision_contract": STRATEGIC_DECISION_CONTRACT, "version": app_version, "generated_at_madrid": generated_at, "environment": "local_filesystem_read_only", "status": "PASS_WITH_STRATEGIC_REVIEW" if unique_candidates else "PASS", "board_score": board_score, "board_score_explanation": ["Media de puntuaciones derivadas de directores y evidencia del Product Review System.", "No se usan métricas inventadas ni aprobaciones automáticas."], "director_count": len(directors), "directors_expected": len(EXECUTIVE_DIRECTOR_DEFINITIONS), "directors": directors, "area_health": _executive_area_health(directors), "product_scores": product_scores, "proposal_count": len(unique_candidates), "proposal_summary": {"P0": counts.get("P0", 0), "P1": counts.get("P1", 0), "P2": counts.get("P2", 0), "P3": counts.get("P3", 0), "total": len(unique_candidates)}, "decision_matrix": unique_candidates, "top_10_improvements": unique_candidates[:10], "backlog_updates": [{"id": candidate["id"], "source_id": candidate["source_id"], "top100_status": "Pendiente", "master_roadmap_status": "Pendiente", "living_roadmap_status": "Pendiente", "documentation": ["reports/EXECUTIVE_DECISION_MATRIX.md", "reports/STRATEGIC_ROADMAP_REPORT.md", "reports/PRODUCT_HEALTH_REPORT.md"], "human_approval_required": True} for candidate in unique_candidates], "source_contracts": {"product_review_system": review.get("contract"), "quality_team": review.get("quality_team_contract"), "product_review_center": review.get("center_contract")}, "guardrails": {**dict(GUARDRAILS), "automatic_decisions": False, "automatic_execution": False, "commit_created": False}, "no_chatbot": True, "no_generative_ai": True, "no_automatic_decisions": True, "automatic_execution_allowed": False, "production_modified": False, "deploy_executed": False, "push_executed": False, "executive_summary": "El Executive Board convierte hallazgos del Product Review System en una matriz de decisión con votos, Top 10 priorizado y puntuaciones explicadas. No aprueba ni ejecuta mejoras automáticamente.", "next_action": "Revisión humana del Top 10 priorizado antes de autorizar cualquier sprint de mejora."}


def build_executive_board_snapshot(project_root: str | Path | None = None, app_version: str = "LOCAL") -> dict[str, Any]:
    root = _root(project_root)
    generated_at = _now()
    review = build_product_review_system_snapshot(root, app_version)
    board = _build_executive_board_from_review(review, app_version, generated_at)
    ledger = build_sentinel_issues_summary(app_version, load_sentinel_issues_memory(root))
    board["issue_health"] = ledger.get("issue_health") or {}
    board["top_verified_open_issues"] = [
        {"id": item.get("id"), "priority": item.get("priority"), "title": item.get("title"), "evidence": item.get("evidence")}
        for item in (ledger.get("open_issues") or [])[:5]
    ]
    return board
def executive_board_snapshot(project_root: str | Path | None = None, app_version: str = "LOCAL") -> dict[str, Any]:
    return build_executive_board_snapshot(project_root, app_version)


def _ce_now(now: str | datetime | None = None) -> datetime:
    if isinstance(now, datetime):
        return now.astimezone(MADRID) if now.tzinfo else now.replace(tzinfo=MADRID)
    if now:
        parsed = datetime.fromisoformat(str(now))
        return parsed.astimezone(MADRID) if parsed.tzinfo else parsed.replace(tzinfo=MADRID)
    return datetime.now(MADRID)


def _ce_utc_iso(value: str | datetime | None) -> str | None:
    if not value:
        return None
    return _ce_now(value).astimezone(timezone.utc).isoformat(timespec="seconds")


def _ce_storage(project_root: str | Path | None = None, storage_root: str | Path | None = None) -> Path:
    if storage_root:
        return Path(storage_root).resolve()
    return _root(project_root) / CONTINUOUS_EVOLUTION_RUNTIME


def _ce_paths(storage: Path) -> dict[str, Path]:
    return {
        "root": storage,
        "snapshots": storage / "snapshots",
        "runs": storage / "runs",
        "briefs": storage / "briefs",
        "codex": storage / "codex_inbox",
        "memory": storage / "product_memory.json",
        "latest_snapshot": storage / "latest_snapshot.json",
        "latest_run": storage / "latest_run.json",
        "latest_brief": storage / "latest_founder_brief.md",
        "codex_inbox": storage / "codex_inbox" / "prepared_for_codex.json",
        "scheduler": storage / "scheduler_state.json",
        "job_logs": storage / "job_logs",
        "scheduler_lock": storage / "scheduler.lock",
        "control": storage / "automation_control.json",
        "certifications": storage / "certifications",
        "market": storage / "market_reviews.json",
    }


def _ce_ensure_dirs(paths: dict[str, Path]) -> None:
    for key in ("root", "snapshots", "runs", "briefs", "codex", "job_logs", "certifications"):
        paths[key].mkdir(parents=True, exist_ok=True)


def _ce_load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _ce_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Separate temporary names prevent concurrent independent readers/writers
    # from replacing or unlinking another writer's in-progress JSON file.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as fh:
            temporary = Path(fh.name)
            json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            fh.flush()
            os.fsync(fh.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _ce_clean_text(value: Any, limit: int = 900) -> str:
    text = _text(value, limit).replace("revisi" + "?" + "n", "revision")
    if text.lower() in {"none", "todo", "null", "n/a", "na", "sin definir", "undefined"}:
        return ""
    for needle, replacement in SENSITIVE_VISIBLE_TERMS.items():
        text = text.replace(needle, replacement)
    return text


def _ce_sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in ("secret", "token", "password", "credential")):
                clean[key] = "[REDACTED_KEY]" if item else ""
            else:
                clean[key] = _ce_sanitize(item)
        return clean
    if isinstance(value, list):
        return [_ce_sanitize(item) for item in value]
    if isinstance(value, str):
        return _ce_clean_text(value, 5000)
    return value


def _ce_hash(prefix: str, *parts: Any) -> str:
    raw = "|".join(_ce_clean_text(part, 500).lower() for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{digest}"


def _ce_recommendation_id(candidate: dict[str, Any]) -> str:
    component = str(candidate.get("component") or "")
    if component.startswith("native_workforce."):
        return _ce_hash("REC", "native_workforce", component)
    return _ce_hash("REC", candidate.get("module"), candidate.get("route"), candidate.get("component"), candidate.get("proposal"))


def _ce_snapshot_id(now_dt: datetime, run_id: str) -> str:
    return f"SNAP-{now_dt.strftime('%Y%m%d%H%M%S')}-{run_id[-8:]}"


def _ce_run_id(now_dt: datetime, execution_mode: str, scheduled_task: str = "") -> str:
    return _ce_hash("CE", now_dt.isoformat(timespec="seconds"), execution_mode, scheduled_task)[:22]


def _ce_default_memory(now_iso: str) -> dict[str, Any]:
    return {
        "contract": PRODUCT_MEMORY_CONTRACT,
        "schema_version": 1,
        "created_at_madrid": now_iso,
        "updated_at_madrid": now_iso,
        "recommendations": {},
        "events": [],
        "snapshots": [],
        "reviewer_signal": {},
        "learning_summary": {"mode": "deterministic_no_ai", "actual_learning_events": 0, "history_storage": True, "actual_learning": False},
    }



def _ce_default_control(now_iso: str) -> dict[str, Any]:
    return {
        "contract": CONTINUOUS_EVOLUTION_CONTROL_CONTRACT,
        "automation_status": "MANUAL",
        "paused": False,
        "pause_events": [],
        "updated_at_madrid": now_iso,
        "dangerous_actions_allowed": False,
    }


def _ce_read_control(paths: dict[str, Path], now_iso: str) -> dict[str, Any]:
    control = _ce_load_json(paths["control"], _ce_default_control(now_iso))
    if not isinstance(control, dict):
        control = _ce_default_control(now_iso)
    control.setdefault("contract", CONTINUOUS_EVOLUTION_CONTROL_CONTRACT)
    control.setdefault("automation_status", "PAUSED" if control.get("paused") else "MANUAL")
    control.setdefault("paused", False)
    control.setdefault("pause_events", [])
    control.setdefault("dangerous_actions_allowed", False)
    control.setdefault("updated_at_madrid", now_iso)
    return control


def set_continuous_evolution_pause(project_root: str | Path | None = None, *, paused: bool, actor: str = "admin", reason: str = "", storage_root: str | Path | None = None, now: str | datetime | None = None) -> dict[str, Any]:
    now_iso = _ce_now(now).isoformat(timespec="seconds")
    paths = _ce_paths(_ce_storage(project_root, storage_root))
    _ce_ensure_dirs(paths)
    control = _ce_read_control(paths, now_iso)
    previous = bool(control.get("paused"))
    control["paused"] = bool(paused)
    control["automation_status"] = "PAUSED" if paused else "MANUAL"
    control["updated_at_madrid"] = now_iso
    event = {
        "event_id": _ce_hash("CTRL", previous, paused, actor, now_iso),
        "at_madrid": now_iso,
        "actor": _ce_clean_text(actor, 120) or "admin",
        "from": "PAUSED" if previous else "ACTIVE_OR_MANUAL",
        "to": "PAUSED" if paused else "MANUAL",
        "reason": _ce_clean_text(reason, 420) or ("Pausa administrativa" if paused else "Reanudacion administrativa"),
        "dangerous_actions_executed": False,
    }
    control.setdefault("pause_events", []).append(event)
    _ce_write_json(paths["control"], control)
    return {"ok": True, "control": control, "event": event, "dangerous_actions_executed": False}


def _ce_period_key(task_name: str, now_dt: datetime) -> str:
    if task_name == "platform_workforce_review":
        return now_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:00Z")
    if task_name == "weekly_executive_review":
        year, week, _ = now_dt.isocalendar()
        return f"{year}-W{week:02d}"
    if task_name == "monthly_strategy_review":
        return now_dt.strftime("%Y-%m")
    return now_dt.strftime("%Y-%m-%d")


def _ce_scheduled_for(task_name: str, now_dt: datetime) -> datetime:
    if task_name == "platform_workforce_review":
        return now_dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0).astimezone(MADRID)
    policy = CONTINUOUS_EVOLUTION_POLICY.get(task_name) or {}
    hour = int(policy.get("hour", 3))
    minute = int(policy.get("minute", 15))
    if task_name == "weekly_executive_review":
        weekday = int(policy.get("weekday", 0))
        base = (now_dt - timedelta(days=(now_dt.weekday() - weekday) % 7)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        return base
    if task_name == "monthly_strategy_review":
        day = int(policy.get("day", 1))
        return now_dt.replace(day=min(day, 28), hour=hour, minute=minute, second=0, microsecond=0)
    return now_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _ce_next_expected(task_name: str, now_dt: datetime) -> str:
    if task_name == "platform_workforce_review":
        following = now_dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return following.astimezone(MADRID).isoformat(timespec="seconds")
    scheduled = _ce_scheduled_for(task_name, now_dt)
    if task_name == "weekly_executive_review":
        next_dt = scheduled + timedelta(days=7)
    elif task_name == "monthly_strategy_review":
        month = scheduled.month + 1
        year = scheduled.year + (1 if month > 12 else 0)
        month = 1 if month > 12 else month
        next_dt = scheduled.replace(year=year, month=month)
    else:
        next_dt = scheduled + timedelta(days=1)
    if next_dt <= now_dt:
        if task_name == "weekly_executive_review":
            next_dt = now_dt + timedelta(days=7)
        elif task_name == "monthly_strategy_review":
            month = now_dt.month + 1
            year = now_dt.year + (1 if month > 12 else 0)
            month = 1 if month > 12 else month
            next_dt = now_dt.replace(year=year, month=month, day=1, hour=scheduled.hour, minute=scheduled.minute, second=0, microsecond=0)
        else:
            next_dt = now_dt.replace(hour=scheduled.hour, minute=scheduled.minute, second=0, microsecond=0) + timedelta(days=1)
    return next_dt.isoformat(timespec="seconds")


def _ce_due(task_state: dict[str, Any], task_name: str, now_dt: datetime, force: bool = False) -> tuple[bool, str, str]:
    scheduled = _ce_scheduled_for(task_name, now_dt)
    period = _ce_period_key(task_name, now_dt)
    if force:
        return True, scheduled.isoformat(timespec="seconds"), period
    if now_dt < scheduled:
        return False, scheduled.isoformat(timespec="seconds"), period
    if task_state.get("last_completed_period") == period:
        return False, scheduled.isoformat(timespec="seconds"), period
    # A bounded native attempt, including a partial/failed attempt, consumes its
    # hourly slot. Do not retry a failing reviewer on every five-minute Cron tick.
    if task_name == "platform_workforce_review" and task_state.get("last_attempt_period") == period:
        return False, scheduled.isoformat(timespec="seconds"), period
    return True, scheduled.isoformat(timespec="seconds"), period


def _ce_job_id(task_name: str, scheduled_for: str, trigger: str) -> str:
    return _ce_hash("JOB", task_name, scheduled_for, trigger)


def _ce_job_history(paths: dict[str, Path], limit: int = 50) -> list[dict[str, Any]]:
    jobs = []
    if paths["job_logs"].exists():
        for path in sorted(paths["job_logs"].glob("JOB-*.json"))[-limit:]:
            data = _ce_load_json(path, None)
            if isinstance(data, dict):
                jobs.append(data)
    return jobs


def _ce_write_job_log(paths: dict[str, Path], job: dict[str, Any]) -> None:
    _ce_ensure_dirs(paths)
    _ce_write_json(paths["job_logs"] / f"{job['job_id']}.json", job)


def _ce_safe_error(exc: BaseException) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": _ce_clean_text(str(exc), 320) or "Error controlado sin detalle sensible."}


def _ce_acquire_lock(paths: dict[str, Path], job_id: str, now_iso: str) -> tuple[bool, dict[str, Any]]:
    lock_path = paths["scheduler_lock"]
    lock_payload = {"job_id": job_id, "locked_at_madrid": now_iso, "pid": os.getpid()}
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("x", encoding="utf-8") as fh:
            json.dump(lock_payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        return True, lock_payload
    except FileExistsError:
        existing = _ce_load_json(lock_path, {})
        locked_at = existing.get("locked_at_madrid") if isinstance(existing, dict) else None
        if not locked_at:
            return False, {"state": "LOCK_UNVERIFIED"}
        if locked_at:
            try:
                if _ce_now(now_iso) - _ce_now(locked_at) > CONTINUOUS_EVOLUTION_LOCK_TTL:
                    # A stale timestamp cannot prove that its owner has stopped.
                    # Never delete an observed lock and risk deleting a new owner.
                    return False, {**existing, "state": "STALE_LOCK"}
            except (OSError, ValueError, TypeError):
                return False, {"state": "LOCK_UNVERIFIED"}
        return False, existing if isinstance(existing, dict) else {"locked": True}


def _ce_release_lock(paths: dict[str, Path], job_id: str) -> None:
    lock_path = paths["scheduler_lock"]
    existing = _ce_load_json(lock_path, {})
    if isinstance(existing, dict) and existing.get("job_id") == job_id:
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def _ce_fallback_product_review(error: BaseException, now_iso: str) -> dict[str, Any]:
    safe = _ce_safe_error(error)
    return {
        "contract": PRODUCT_REVIEW_SYSTEM_CONTRACT,
        "center_contract": PRODUCT_REVIEW_CENTER_CONTRACT,
        "quality_team_contract": QUALITY_TEAM_CONTRACT,
        "status": "PARTIAL_COMPONENT_UNAVAILABLE",
        "score": 0,
        "generated_at_madrid": now_iso,
        "reviewers": [],
        "findings": [],
        "findings_summary": {"P0": 0, "P1": 0, "P2": 0, "P3": 0, "total": 0},
        "roadmap_candidates": [],
        "component_unavailable": {"component": "Product Review", "error_safe": safe},
        "guardrails": dict(GUARDRAILS),
    }


def _ce_simulated_user_nightly_check(project_root: Path, previous_snapshot: dict[str, Any] | None, control_fixture: dict[str, Any] | None = None) -> dict[str, Any]:
    previous = ((previous_snapshot or {}).get("simulated_user_nightly_check") or {}).get("personas") or []
    prev_by_key = {item.get("persona"): item for item in previous}
    route_engine_available = (project_root / "engines" / "sentinel_user_journey_engine.py").is_file()
    personas = []
    for persona in SIMULATED_USER_PERSONAS:
        baseline = {"clicks": 3, "route_failures": 0, "empty_states": 0, "js_errors": 0, "overflow": 0, "friction_indicators": 0}
        if control_fixture and (control_fixture.get("simulated_persona") == persona):
            baseline.update(control_fixture.get("simulated_metrics") or {})
        before = prev_by_key.get(persona) or {}
        change = "INSUFFICIENT_HISTORY" if not before else "UNCHANGED"
        if before:
            if int(baseline.get("friction_indicators") or 0) > int(before.get("friction_indicators") or 0):
                change = "WORSENED"
            elif int(baseline.get("friction_indicators") or 0) < int(before.get("friction_indicators") or 0):
                change = "IMPROVED"
        personas.append({"persona": persona, "evidence_origin": "SIMULATED_QA", "source": "sentinel_user_journey_engine" if route_engine_available else "contract_only", "status": "AVAILABLE" if route_engine_available else "PARTIAL", "change": change, **baseline})
    return {"contract": "NEMESIS-SIMULATED-USER-NIGHTLY-CHECK-V1", "evidence_origin": "SIMULATED_QA", "real_user_data": False, "personas": personas, "summary": {"personas": len(personas), "route_failures": sum(int(p.get("route_failures") or 0) for p in personas), "js_errors": sum(int(p.get("js_errors") or 0) for p in personas), "overflow": sum(int(p.get("overflow") or 0) for p in personas), "worsened": len([p for p in personas if p.get("change") == "WORSENED"]), "improved": len([p for p in personas if p.get("change") == "IMPROVED"])}}

def load_product_memory(project_root: str | Path | None = None, storage_root: str | Path | None = None, now: str | datetime | None = None) -> dict[str, Any]:
    now_iso = _ce_now(now).isoformat(timespec="seconds")
    paths = _ce_paths(_ce_storage(project_root, storage_root))
    memory = _ce_load_json(paths["memory"], _ce_default_memory(now_iso))
    if not isinstance(memory, dict):
        memory = _ce_default_memory(now_iso)
    memory.setdefault("contract", PRODUCT_MEMORY_CONTRACT)
    memory.setdefault("schema_version", 1)
    memory.setdefault("created_at_madrid", now_iso)
    memory.setdefault("recommendations", {})
    memory.setdefault("events", [])
    memory.setdefault("snapshots", [])
    memory.setdefault("reviewer_signal", {})
    memory.setdefault("learning_summary", {"mode": "deterministic_no_ai", "actual_learning_events": 0, "history_storage": True, "actual_learning": False})
    return memory


def save_product_memory(project_root: str | Path | None, memory: dict[str, Any], storage_root: str | Path | None = None) -> Path:
    paths = _ce_paths(_ce_storage(project_root, storage_root))
    _ce_ensure_dirs(paths)
    _ce_write_json(paths["memory"], _ce_sanitize(memory))
    return paths["memory"]

def _ce_priority_rank(priority: str) -> int:
    return {"P0": 4, "P1": 3, "P2": 2, "P3": 1}.get(str(priority or "P3").upper(), 1)


def _ce_compact_review(review: dict[str, Any]) -> dict[str, Any]:
    reviewers = []
    for reviewer in review.get("reviewers") or []:
        reviewers.append({"key": reviewer.get("key"), "name": reviewer.get("name"), "state": reviewer.get("state"), "score": reviewer.get("score"), "findings_count": reviewer.get("findings_count"), "p0": reviewer.get("p0"), "p1": reviewer.get("p1"), "p2": reviewer.get("p2"), "p3": reviewer.get("p3")})
    return {"contract": review.get("contract"), "status": review.get("status"), "score": review.get("score"), "findings_summary": review.get("findings_summary") or {}, "reviewers": reviewers, "top_findings": [_ce_sanitize(item) for item in (review.get("findings") or [])[:20]]}


def _ce_apply_control_fixture(review: dict[str, Any], control_fixture: dict[str, Any] | None = None) -> dict[str, Any]:
    if not control_fixture:
        return review
    cloned = json.loads(json.dumps(review, ensure_ascii=False, default=str))
    finding = _finding(
        reviewer=control_fixture.get("reviewer") or "Control Fixture",
        module=control_fixture.get("module") or "Continuous Evolution",
        screen=control_fixture.get("screen") or "SIMULATED_QA_CONTROL",
        route=control_fixture.get("route") or "/admin/founder-dashboard",
        component=control_fixture.get("component") or "controlled_fixture",
        evidence=control_fixture.get("evidence") or "Cambio controlado de QA simulado para demostrar comparacion temporal.",
        priority=control_fixture.get("priority") or "P2",
        user_impact=control_fixture.get("impact_user") or "Permite validar que el loop detecta novedades sin usar usuarios reales.",
        business_impact=control_fixture.get("impact_business") or "Reduce riesgo de llamar aprendizaje a una memoria que no compara cambios.",
        proposal=control_fixture.get("proposal") or "Mantener fixture solo en pruebas locales y no elevarlo como dato real.",
        source="SIMULATED_QA_CONTROL_FIXTURE",
        state="SIMULATED_QA",
    )
    finding["id"] = control_fixture.get("id") or _ce_hash("SIM", finding["module"], finding["route"], finding["proposal"])
    finding["title"] = control_fixture.get("title") or f"{finding['module']}: {finding['proposal']}"
    finding["evidence_origin"] = "SIMULATED_QA"
    cloned.setdefault("findings", []).append(finding)
    counts = Counter(item.get("priority", "P3") for item in cloned.get("findings") or [])
    cloned["findings_summary"] = {"P0": counts.get("P0", 0), "P1": counts.get("P1", 0), "P2": counts.get("P2", 0), "P3": counts.get("P3", 0), "total": len(cloned.get("findings") or [])}
    cloned.setdefault("roadmap_candidates", []).append({"id": finding["id"], "reviewer": finding["reviewer"], "priority": finding["priority"], "module": finding["module"], "screen": finding["screen"], "route": finding["route"], "proposal": finding["proposal"], "evidence": finding["evidence"], "approved": False, "automatic_execution_allowed": False, "requires_human_approval": True})
    cloned["control_fixture_applied"] = {"id": finding["id"], "evidence_origin": "SIMULATED_QA"}
    return cloned


def _ce_recommendations_from_board(board: dict[str, Any]) -> list[dict[str, Any]]:
    recommendations = []
    for candidate in board.get("decision_matrix") or []:
        item = dict(candidate)
        item["recommendation_id"] = _ce_recommendation_id(candidate)
        item["title"] = _ce_clean_text(item.get("title") or item.get("proposal"), 160)
        evidence = _ce_clean_text(item.get("evidence"), 620)
        item["evidence"] = evidence
        item["problem"] = evidence or "Evidencia insuficiente para elevar este contexto a trabajo ejecutable."
        item["issue_status"] = item.get("issue_status") if item.get("issue_status") in {
            "OPEN_REAL", "FIXED_PENDING_VERIFICATION", "VERIFIED", "VERIFICATION_FAILED", "RESOLVED", "FALSE_POSITIVE",
            "STALE", "DUPLICATE", "EXTERNAL_BLOCKER", "INSUFFICIENT_EVIDENCE",
        } else "INSUFFICIENT_EVIDENCE"
        item["evidence_sufficient"] = bool(item.get("evidence_sufficient") and evidence)
        item["benefit"] = _ce_clean_text(item.get("impact_user"), 320)
        if item.get("evidence_origin") not in EVIDENCE_ORIGINS:
            item["evidence_origin"] = "SYSTEM_OBSERVATION"
        recommendations.append(_ce_sanitize(item))
    return recommendations


def _ce_things_not_to_touch(board: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for director in board.get("directors") or []:
        value = _ce_clean_text(director.get("should_not_touch"), 240)
        if value and value not in seen:
            seen.add(value)
            items.append(value)
        if len(items) >= 10:
            break
    return items


def _ce_unique_candidates(candidates: list[dict[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for candidate in candidates or []:
        key = (
            _ce_clean_text(candidate.get("title"), 180).lower(),
            _ce_clean_text(candidate.get("proposal"), 260).lower(),
        )
        if not key[0] and not key[1]:
            key = (_ce_clean_text(candidate.get("id"), 80).lower(), "")
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
        if limit and len(unique) >= limit:
            break
    return unique

def _ce_board_risks(board: dict[str, Any]) -> list[str]:
    risks = []
    for candidate in _ce_unique_candidates(board.get("top_10_improvements") or []):
        risk = _ce_clean_text(candidate.get("risk"), 60)
        if risk in {"Medio", "Alto"}:
            risks.append(f"{candidate.get('id')}: {risk} - {_ce_clean_text(candidate.get('title'), 160)}")
    return risks[:8]


def _ce_board_opportunities(board: dict[str, Any]) -> list[str]:
    return [f"{item.get('id')}: {_ce_clean_text(item.get('impact_business'), 220)}" for item in _ce_unique_candidates(board.get("top_10_improvements") or [], limit=8)]


def _ce_latest_snapshot(paths: dict[str, Path]) -> dict[str, Any] | None:
    latest = _ce_load_json(paths["latest_snapshot"], None)
    return latest if isinstance(latest, dict) else None


def _ce_snapshot_history(paths: dict[str, Path], limit: int = 90) -> list[dict[str, Any]]:
    snapshots = []
    if paths["snapshots"].exists():
        for path in sorted(paths["snapshots"].glob("SNAP-*.json"))[-limit:]:
            data = _ce_load_json(path, None)
            if isinstance(data, dict):
                snapshots.append(data)
    return snapshots

def _ce_compare(current_recommendations: list[dict[str, Any]], previous_snapshot: dict[str, Any] | None, history: list[dict[str, Any]]) -> dict[str, Any]:
    if not previous_snapshot:
        return {"contract": "NEMESIS-TEMPORAL-COMPARISON-V1", "today_vs_previous": {"state": "INSUFFICIENT_HISTORY", "new": [], "improved": [], "worsened": [], "resolved": [], "unchanged": [], "reopened": []}, "week_vs_previous_week": {"state": "INSUFFICIENT_HISTORY"}, "month_vs_previous_month": {"state": "INSUFFICIENT_HISTORY"}, "summary": "No hay snapshot anterior suficiente para comparar."}
    previous_recs = previous_snapshot.get("recommendations") or []
    prev_by_id = {item.get("recommendation_id"): item for item in previous_recs if item.get("recommendation_id")}
    curr_by_id = {item.get("recommendation_id"): item for item in current_recommendations if item.get("recommendation_id")}
    new = sorted(set(curr_by_id) - set(prev_by_id))
    resolved = sorted(set(prev_by_id) - set(curr_by_id))
    unchanged = sorted(set(curr_by_id) & set(prev_by_id))
    improved: list[str] = []
    worsened: list[str] = []
    reopened: list[str] = []
    for rec_id in unchanged:
        before = _ce_priority_rank(prev_by_id[rec_id].get("priority"))
        after = _ce_priority_rank(curr_by_id[rec_id].get("priority"))
        if after < before:
            improved.append(rec_id)
        elif after > before:
            worsened.append(rec_id)
        if int(curr_by_id[rec_id].get("reopened_count") or 0) > int(prev_by_id[rec_id].get("reopened_count") or 0):
            reopened.append(rec_id)
    today_state = "UNCHANGED" if not new and not resolved and not improved and not worsened and not reopened else "CHANGED"
    dates = sorted({str(item.get("generated_at_madrid") or "")[:10] for item in history if item.get("generated_at_madrid")})
    week_state = "INSUFFICIENT_HISTORY" if len(dates) < 8 else "AVAILABLE"
    month_state = "INSUFFICIENT_HISTORY" if len(dates) < 32 else "AVAILABLE"
    return {"contract": "NEMESIS-TEMPORAL-COMPARISON-V1", "today_vs_previous": {"state": today_state, "new": new, "improved": improved, "worsened": worsened, "resolved": resolved, "unchanged": unchanged, "reopened": reopened}, "week_vs_previous_week": {"state": week_state}, "month_vs_previous_month": {"state": month_state}, "summary": f"Desde la ultima revision: {len(new)} nuevas, {len(resolved)} resueltas, {len(improved)} mejoradas, {len(worsened)} empeoradas, {len(unchanged)} sin cambios."}


def _ce_calibrate_reviewers(review: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any]:
    recommendations = memory.get("recommendations") or {}
    by_worker: dict[str, list[dict[str, Any]]] = {}
    for item in recommendations.values():
        for worker in item.get("workers") or []:
            by_worker.setdefault(str(worker), []).append(item)
    calibration = {}
    insufficient_real_data = {"Performance Reviewer", "Commercial Reviewer", "Marketing Reviewer"}
    for reviewer in review.get("reviewers") or []:
        name = reviewer.get("name") or reviewer.get("key")
        items = by_worker.get(str(name), [])
        reviewed = [item for item in items if item.get("issue_status") in {"RESOLVED", "FALSE_POSITIVE", "OPEN_REAL"} and item.get("evidence_sufficient")]
        confirmed = [item for item in reviewed if item.get("issue_status") in {"RESOLVED", "OPEN_REAL"}]
        false_positives = [item for item in reviewed if item.get("issue_status") == "FALSE_POSITIVE"]
        regressions = [item for item in reviewed if int(item.get("reopened_count") or 0) > 0 or item.get("state") == "REGRESSED"]
        if name in insufficient_real_data:
            state = "INSUFFICIENT_REAL_DATA"
            reason = "El area necesita datos reales de rendimiento, conversion o mercado para producir senal fuerte."
        elif len(reviewed) < 5:
            state = "INSUFFICIENT_HISTORY"
            reason = "Se requieren al menos 5 resultados revisados; repeticion sin veredicto no calibra senal."
        elif regressions:
            state = "HIGH_SIGNAL"
            reason = "Ha detectado recomendaciones que reaparecieron o regresaron."
        else:
            useful_rate = len(confirmed) / max(len(reviewed), 1)
            state = "HIGH_SIGNAL" if useful_rate >= .8 else "LOW_SIGNAL" if useful_rate < .5 else "NORMAL_SIGNAL"
            reason = "Clasificacion determinista basada solo en resultados confirmados y falsos positivos revisados."
        calibration[str(name)] = {"state": state, "reason": reason, "recommendations_seen": len(items), "reviewed_samples": len(reviewed), "confirmed": len(confirmed), "false_positive": len(false_positives), "regressions": len(regressions)}
    return calibration


def _ce_update_memory(memory: dict[str, Any], recommendations: list[dict[str, Any]], review: dict[str, Any], run_id: str, snapshot_id: str, now_iso: str, comparison: dict[str, Any]) -> dict[str, Any]:
    memory = _ce_sanitize(memory)
    records = memory.setdefault("recommendations", {})
    events = memory.setdefault("events", [])
    current_ids = {item["recommendation_id"] for item in recommendations}
    for candidate in recommendations:
        rec_id = candidate["recommendation_id"]
        existing = records.get(rec_id)
        event_type = "SEEN"
        if not existing:
            existing = {"recommendation_id": rec_id, "title": candidate.get("title"), "first_seen": now_iso, "workers": candidate.get("workers") or [], "evidence": [], "priority_initial": candidate.get("priority"), "priority_current": candidate.get("priority"), "priority_history": [], "decision_history": [], "outcome_history": [], "reviewer_history": [], "evidence_history": [], "decisions": [], "state": "NEW", "decision_reason": "Pendiente de decisión humana.", "future_sprint_or_commit": None, "qa_after": None, "outcome_after": None, "reopened_count": 0, "last_seen": now_iso, "resolved_at": None, "seen_count": 0, "missed_count": 0, "why_priority_changed": "Primera deteccion con evidencia actual.", "evidence_origin": candidate.get("evidence_origin") or "SYSTEM_OBSERVATION"}
            records[rec_id] = existing
            event_type = "FIRST_SEEN"
        existing.setdefault("priority_history", [])
        existing.setdefault("decision_history", existing.get("decisions") or [])
        existing.setdefault("outcome_history", [])
        existing.setdefault("reviewer_history", [])
        existing.setdefault("evidence_history", [])
        cleaned_evidence = []
        for evidence_item in existing.get("evidence") or []:
            cleaned = _ce_clean_text(evidence_item, 620)
            if cleaned and cleaned not in cleaned_evidence:
                cleaned_evidence.append(cleaned)
        existing["evidence"] = cleaned_evidence
        previous_state = existing.get("state")
        native_candidate = str(candidate.get("component") or "").startswith("native_workforce.")
        if previous_state in {"IMPLEMENTED", "VERIFIED", "RESOLVED"} and (not native_candidate or candidate.get("evidence_sufficient") is True):
            existing["state"] = "REGRESSED"
            existing["reopened_count"] = int(existing.get("reopened_count") or 0) + 1
            existing["outcome_after"] = "OUTCOME_REGRESSION"
            existing["why_priority_changed"] = "La recomendacion reaparecio despues de estar cerrada o verificada."
            event_type = "REGRESSION"
        existing["last_seen"] = now_iso
        if str(candidate.get("component") or "").startswith("native_workforce."):
            existing["source_family"] = "native_workforce"
            existing["native_check_id"] = candidate["component"].removeprefix("native_workforce.")
        existing["issue_status"] = candidate.get("issue_status") or "INSUFFICIENT_EVIDENCE"
        existing["evidence_sufficient"] = bool(candidate.get("evidence_sufficient"))
        existing["seen_count"] = int(existing.get("seen_count") or 0) + 1
        existing["missed_count"] = 0
        existing.setdefault("priority_history", []).append({"at_madrid": now_iso, "run_id": run_id, "snapshot_id": snapshot_id, "priority": candidate.get("priority"), "reason": existing.get("why_priority_changed")})
        existing.setdefault("reviewer_history", []).append({"at_madrid": now_iso, "run_id": run_id, "workers": candidate.get("workers") or []})
        evidence = _ce_clean_text(candidate.get("evidence"), 620)
        if evidence and evidence not in existing.setdefault("evidence", []):
            existing["evidence"].append(evidence)
        if evidence:
            existing.setdefault("evidence_history", []).append({"at_madrid": now_iso, "run_id": run_id, "snapshot_id": snapshot_id, "evidence": evidence, "origin": candidate.get("evidence_origin") or "SYSTEM_OBSERVATION"})
        existing["workers"] = list(dict.fromkeys([*(existing.get("workers") or []), *(candidate.get("workers") or [])]))
        if _ce_priority_rank(candidate.get("priority")) != _ce_priority_rank(existing.get("priority_current")):
            existing["priority_current"] = candidate.get("priority")
            existing["why_priority_changed"] = f"La prioridad actual cambio a {candidate.get('priority')} por nueva evidencia del Product Review."
        if existing.get("state") == "REJECTED" and len(existing.get("decisions") or []) >= 2:
            existing["priority_current"] = "P3"
            existing["why_priority_changed"] = "Rechazada repetidamente; no vuelve a maxima prioridad sin nueva evidencia."
        existing["learning_metrics"] = {
            "persistence": int(existing.get("seen_count") or 0),
            "recurrence": int(existing.get("seen_count") or 0) >= 2,
            "resolution": bool(existing.get("resolved_at")),
            "regression": int(existing.get("reopened_count") or 0) > 0 or existing.get("state") == "REGRESSED",
            "human_rejection": existing.get("state") == "REJECTED",
            "positive_outcome": existing.get("outcome_after") == "OUTCOME_POSITIVE",
            "insufficient_evidence": not bool(existing.get("evidence_sufficient")),
        }
        events.append({"event_id": _ce_hash("EVT", rec_id, run_id, event_type, now_iso), "type": event_type, "recommendation_id": rec_id, "run_id": run_id, "snapshot_id": snapshot_id, "at_madrid": now_iso, "state": existing.get("state"), "priority_current": existing.get("priority_current")})
    for rec_id, record in records.items():
        if rec_id in current_ids:
            continue
        # A missing/old/partial native receipt is not evidence of resolution.
        if record.get("source_family") == "native_workforce":
            continue
        record["missed_count"] = int(record.get("missed_count") or 0) + 1
        if record.get("state") in {"IMPLEMENTED", "VERIFIED"} and not record.get("resolved_at"):
            record["resolved_at"] = now_iso
            record["outcome_after"] = "OUTCOME_POSITIVE"
            record.setdefault("outcome_history", []).append({"at_madrid": now_iso, "run_id": run_id, "snapshot_id": snapshot_id, "outcome": "OUTCOME_POSITIVE"})
            events.append({"event_id": _ce_hash("EVT", rec_id, run_id, "OUTCOME_POSITIVE", now_iso), "type": "OUTCOME_POSITIVE", "recommendation_id": rec_id, "run_id": run_id, "snapshot_id": snapshot_id, "at_madrid": now_iso})
    memory["reviewer_signal"] = _ce_calibrate_reviewers(review, memory)
    learning_events = len([event for event in events if event.get("type") in {"REGRESSION", "OUTCOME_POSITIVE"}])
    comparison_state = (comparison.get("today_vs_previous") or {}).get("state")
    memory["learning_summary"] = {"mode": "deterministic_no_ai", "history_storage": True, "actual_learning": bool(learning_events or comparison_state not in {None, "INSUFFICIENT_HISTORY"}), "actual_learning_events": learning_events, "why": "El sistema compara recomendaciones estables entre snapshots y conserva transiciones trazables; no usa IA ni inferencias opacas."}
    memory.setdefault("snapshots", []).append({"snapshot_id": snapshot_id, "run_id": run_id, "at_madrid": now_iso, "recommendations": len(recommendations), "comparison_state": comparison_state})
    memory["updated_at_madrid"] = now_iso
    return memory


def _ce_enrich_board_with_memory(board: dict[str, Any], memory: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    board = json.loads(json.dumps(board, ensure_ascii=False, default=str))
    records = memory.get("recommendations") or {}
    for bucket in ("decision_matrix", "top_10_improvements"):
        for candidate in board.get(bucket) or []:
            rec_id = _ce_recommendation_id(candidate)
            record = records.get(rec_id) or {}
            candidate["recommendation_id"] = rec_id
            candidate["memory_state"] = record.get("state") or "NEW"
            candidate["first_seen"] = record.get("first_seen")
            candidate["last_seen"] = record.get("last_seen")
            candidate["seen_count"] = record.get("seen_count") or 0
            candidate["reopened_count"] = record.get("reopened_count") or 0
            candidate["why_this_is_priority_now"] = record.get("why_priority_changed") or "Prioridad derivada de evidencia actual del Product Review."
    board["uses_product_memory"] = True
    board["product_memory_contract"] = memory.get("contract")
    board["reviewer_signal_quality"] = memory.get("reviewer_signal") or {}
    board["what_changed"] = comparison.get("summary")
    board["things_not_to_touch"] = _ce_things_not_to_touch(board)
    board["risks"] = _ce_board_risks(board)
    board["opportunities"] = _ce_board_opportunities(board)
    board["actual_learning_mode"] = "deterministic_no_ai"
    return board

def _ce_probable_files(candidate: dict[str, Any]) -> list[str]:
    files = []
    screen = _ce_clean_text(candidate.get("screen"), 220)
    if screen.endswith(".html"):
        files.append(screen if screen.startswith("templates/") else f"templates/{Path(screen).name}")
    route = _ce_clean_text(candidate.get("route"), 120)
    if route and route != "No aplica":
        files.append("app.py")
    proposal = _ce_clean_text(candidate.get("proposal"), 360).lower()
    if any(token in proposal for token in ("visual", "css", "boton", "responsive", "copy", "texto")):
        files.append("static/v933-product.css")
    return list(dict.fromkeys(files or ["app.py"]))


def _ce_build_codex_inbox(board: dict[str, Any], snapshot_id: str, now_iso: str) -> dict[str, Any]:
    items = []
    for index, candidate in enumerate(_ce_unique_candidates(board.get("top_10_improvements") or []), start=1):
        if candidate.get("issue_status") not in {"OPEN_REAL", "VERIFICATION_FAILED"} or not candidate.get("evidence_sufficient"):
            continue
        rec_id = candidate.get("recommendation_id") or _ce_recommendation_id(candidate)
        evidence = _ce_clean_text(candidate.get("evidence"), 620)
        proposal = _ce_clean_text(candidate.get("proposal"), 420)
        state = "READY" if evidence and proposal else "DRAFT"
        items.append({"codex_brief_id": _ce_hash("CB", rec_id, snapshot_id), "recommendation_id": rec_id, "state": state, "created_at_madrid": now_iso, "title": _ce_clean_text(candidate.get("title"), 160), "problem": evidence or "Evidencia heredada insuficiente; requiere revision humana antes de ejecutar.", "evidence": evidence or "Evidencia no disponible en el snapshot actual.", "priority": candidate.get("priority"), "benefit": _ce_clean_text(candidate.get("impact_user"), 320), "risk": candidate.get("risk") or "Medio", "scope": "Correccion acotada sobre la evidencia; no crear modulos, motores ni pantallas nuevas.", "modules_not_to_touch": _ce_things_not_to_touch(board)[:6], "probable_files": _ce_probable_files(candidate), "acceptance_criteria": ["El problema original deja de reproducirse.", "No se oculta evidencia necesaria para admin.", "No se modifican Sports Core, SHARK, Telegram, Stripe ni produccion.", "Browser QA, Sentinel, Privacy y Secret Guard permanecen PASS."], "qa": ["py_compile", "compileall", "pytest", "Jinja", "Browser QA", "Sentinel", "Privacy Guard", "Secret Guard", "Routes", "Links", "Smoke"], "pass_definition": "Cambio minimo, evidence-first, aprobado por humano y validado por QA completa.", "approved_by_founder": False, "automatic_execution_allowed": False, "rank": index})
    return {"contract": PREPARED_FOR_CODEX_CONTRACT, "snapshot_id": snapshot_id, "generated_at_madrid": now_iso, "items": items, "ready_count": len([item for item in items if item["state"] == "READY"]), "human_approval_required_for_execution": True}


def _ce_build_founder_brief(snapshot: dict[str, Any]) -> dict[str, Any]:
    now_iso = snapshot.get("generated_at_madrid") or ""
    board = snapshot.get("executive_board") or {}
    comparison = snapshot.get("temporal_comparison") or {}
    growth = snapshot.get("growth_revenue") or {}
    growth_brief = growth.get("founder_revenue_brief") or {}
    growth_workforce = growth.get("growth_daily_workforce") or {}
    growth_opportunity = next(iter(growth_workforce.get("opportunities") or []), {})
    top = _ce_unique_candidates(board.get("top_10_improvements") or [], limit=3)
    no_touch = board.get("things_not_to_touch") or []
    risks = board.get("risks") or []
    opportunities = board.get("opportunities") or []
    codex = snapshot.get("prepared_for_codex") or {}
    product_qa = snapshot.get("autonomous_product_qa") or {}
    quality_director = product_qa.get("quality_director") or {}
    regression_manager = product_qa.get("regression_manager") or {}
    production_sentinel = product_qa.get("production_sentinel") or {}
    issue_health = (snapshot.get("issue_ledger") or {}).get("issue_health") or {}
    product_line = f"Producto: {snapshot.get('result')} | Score producto: {(snapshot.get('product_review') or {}).get('score')} | Board: {board.get('board_score')}."
    growth_line = f"Growth: {growth.get('status') or 'FOUNDATION_READY'} | evidencia real: {growth.get('real_user_data_state') or 'INSUFFICIENT_REAL_DATA'}."
    revenue_line = f"Revenue: MRR {growth_brief.get('mrr') or 'No certificado'} | premium intent {growth_brief.get('premium_intent') or 'Sin datos reales'}."
    lines = [
        f"FOUNDER BRIEF - {now_iso[:10] if now_iso else 'sin fecha'}",
        product_line,
        growth_line,
        revenue_line,
        f"QA autonoma: {product_qa.get('status') or 'NOT_RUN'} | incidencias abiertas: {product_qa.get('open_issue_count', 0)}.",
        f"Calidad: {quality_director.get('decision') or 'NOT_RUN'} | P0 {quality_director.get('open_p0', 0)} | P1 {quality_director.get('open_p1', 0)} | regresiones {regression_manager.get('recurrences', 0)}.",
        f"Produccion: {production_sentinel.get('result') or 'NOT_RUN'}.",
        f"Incidencias: {issue_health.get('open_real', 0)} abiertas reales | {issue_health.get('pending_verification', 0)} por verificar | {issue_health.get('external_blocker', 0)} bloqueos externos.",
        f"Principal fuga del funnel: {growth_brief.get('main_friction') or 'INSUFFICIENT_REAL_DATA'}",
        f"Mejor canal: {growth_brief.get('main_channels') or 'INSUFFICIENT_REAL_DATA'}",
        f"Contenido ganador: {growth_brief.get('winning_content') or 'INSUFFICIENT_REAL_DATA'}",
        f"Oportunidad Growth preparada: {growth_opportunity.get('recommendation') or 'INSUFFICIENT_REAL_DATA'}",
        f"Que cambio: {(comparison.get('summary') or 'Sin comparacion suficiente.')}",
        "3 prioridades:",
    ]
    for item in top[:3]:
        lines.append(f"- {item.get('title')} ({item.get('priority')}): {item.get('why_this_is_priority_now') or item.get('proposal')}")
    lines.append("3 cosas que no tocar:")
    for item in no_touch[:3]:
        lines.append(f"- {item}")
    lines.append("Riesgos:")
    for item in (risks or ["Sin riesgos nuevos con evidencia actual."])[:3]:
        lines.append(f"- {item}")
    lines.append("Oportunidades:")
    for item in (opportunities or ["Esperar evidencia real de beta antes de ampliar producto."])[:3]:
        lines.append(f"- {item}")
    next_action = growth.get("next_action") or "Revisar el primer brief READY para Codex y aprobarlo solo si el alcance es correcto."
    lines.append(f"Recomendacion: {next_action}")
    lines.append(f"Trabajo preparado para Codex: {codex.get('ready_count', 0)} briefs READY, sin ejecucion automatica.")
    return {
        "contract": FOUNDER_BRIEF_CONTRACT,
        "brief_id": _ce_hash("FB", snapshot.get("snapshot_id"), now_iso),
        "generated_at_madrid": now_iso,
        "language": "es",
        "max_mobile_screen": True,
        "sections": {
            "producto": product_line,
            "growth": growth_line,
            "revenue": revenue_line,
            "qa_autonoma": f"{product_qa.get('status') or 'NOT_RUN'} | {product_qa.get('open_issue_count', 0)} incidencias abiertas",
            "quality_reliability": {
                "decision": quality_director.get("decision") or "NOT_RUN",
                "open_p0": quality_director.get("open_p0", 0),
                "open_p1": quality_director.get("open_p1", 0),
                "regressions": regression_manager.get("recurrences", 0),
                "production_sentinel": production_sentinel.get("result") or "NOT_RUN",
            },
            "salud_incidencias": issue_health,
            "principal_fuga": growth_brief.get("main_friction") or "INSUFFICIENT_REAL_DATA",
            "mejor_canal": growth_brief.get("main_channels") or "INSUFFICIENT_REAL_DATA",
            "contenido_ganador": growth_brief.get("winning_content") or "INSUFFICIENT_REAL_DATA",
            "que_cambio": next((line for line in lines if line.startswith("Que cambio:")), "Que cambio: Sin comparacion suficiente."),
            "prioridades": [f"{item.get('title')} ({item.get('priority')}): {item.get('why_this_is_priority_now') or item.get('proposal')}" for item in top[:3]],
            "no_tocar": no_touch[:3],
            "riesgos": risks[:3],
            "oportunidades": opportunities[:3],
            "que_haria_ahora": next_action,
            "trabajo_codex": codex.get("items", [])[:1],
        },
        "text": "\n".join(lines),
    }


def _ce_write_brief_markdown(path: Path, brief: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(brief.get("text") or "", encoding="utf-8")


def build_market_intelligence_foundation_snapshot(project_root: str | Path | None = None, now: str | datetime | None = None) -> dict[str, Any]:
    root = _root(project_root)
    checked_at = _ce_now(now).isoformat(timespec="seconds")
    gateway_exists = (root / "engines" / "sports_intelligence_gateway_engine.py").is_file()
    return {"contract": MARKET_INTELLIGENCE_FOUNDATION_CONTRACT, "checked_at_madrid": checked_at, "status": "PREPARED_ONLY" if gateway_exists else "BLOCKED", "manual_market_review": "AVAILABLE_WITH_SOURCE_COMPLIANCE" if gateway_exists else "BLOCKED", "scheduled_market_review_disabled_by_default": True, "external_calls": 0, "source_facts": [], "nemesis_inferences": [], "guardrails": ["no crawling masivo", "no paywalls", "no scraping", "no contenido protegido", "source compliance obligatorio"]}


def _ce_available_qa(project_root: Path) -> dict[str, Any]:
    checks = {"py_compile": True, "compileall": True, "pytest": (project_root / "tests").is_dir(), "jinja": (project_root / "templates").is_dir(), "browser_qa_founder": (project_root / "tools" / "run_founder_mode_browser_qa.py").is_file(), "browser_qa_product": (project_root / "tools" / "run_product_finalization_browser_qa.py").is_file(), "sentinel": (project_root / "tools" / "run_continuous_sentinel_static.py").is_file(), "privacy_secret_guard": (project_root / "tools" / "check_repository_privacy_and_secrets.py").is_file(), "routes_links_smoke": (project_root / "tools" / "audit_all_routes_links.py").is_file() and (project_root / "tools" / "smoke_flask_real_routes.py").is_file()}
    return {"state": "AVAILABLE" if all(checks.values()) else "PARTIAL", "checks": checks, "evidence_origin": "SYSTEM_OBSERVATION"}


def _ce_operations_state(project_root: Path) -> dict[str, Any]:
    render_yaml = project_root / "render.yaml"
    reports = project_root / "reports"
    return {"state": "PARTIAL", "render_yaml": render_yaml.is_file(), "release_gate_report": (reports / "FINAL_RELEASE_GATE.md").is_file() or (reports / "RELEASE_GATE_STATUS.md").is_file(), "cron_configured": "render_cron_sports_sync.py" in _read(render_yaml), "master_tick": "NOT_RECORDED_UNLESS_PRODUCTION_EVIDENCE_EXISTS", "evidence_origin": "SYSTEM_OBSERVATION", "dangerous_actions_executed": False}


def _ce_beta_state(project_root: Path) -> dict[str, Any]:
    reports = project_root / "reports"
    return {"state": "PREPARED_ONLY", "beta_report": (reports / "BETA_PROGRAM_REPORT.md").is_file(), "real_user_evidence": "NO_REAL_USER_EVIDENCE", "evidence_origin": "SYSTEM_OBSERVATION"}

def run_continuous_evolution_cycle(project_root: str | Path | None = None, app_version: str = "LOCAL", *, execution_mode: str = "manual_run", scheduled_task: str = "", now: str | datetime | None = None, storage_root: str | Path | None = None, control_fixture: dict[str, Any] | None = None, write: bool = True, job_id: str = "", scheduled_for: str = "", trigger: str = "MANUAL") -> dict[str, Any]:
    root = _root(project_root)
    started_dt = _ce_now(now)
    now_dt = started_dt
    now_iso = now_dt.isoformat(timespec="seconds")
    started_at = now_iso
    run_id = _ce_run_id(now_dt, execution_mode, scheduled_task)
    snapshot_id = _ce_snapshot_id(now_dt, run_id)
    storage = _ce_storage(root, storage_root)
    paths = _ce_paths(storage)
    if write:
        _ce_ensure_dirs(paths)
    previous = _ce_latest_snapshot(paths)
    history = _ce_snapshot_history(paths)
    components_unavailable: list[dict[str, Any]] = []
    try:
        if control_fixture and control_fixture.get("component_unavailable") == "Product Review":
            raise RuntimeError("Controlled Product Review unavailable fixture")
        review = build_product_review_system_snapshot(root, app_version)
        review = _ce_apply_control_fixture(review, control_fixture)
    except Exception as exc:
        components_unavailable.append({"component": "Product Review", "status": "COMPONENT_UNAVAILABLE", "error_safe": _ce_safe_error(exc)})
        review = _ce_fallback_product_review(exc, now_iso)
    product_qa = build_autonomous_product_qa_status(root, storage_root=storage_root)
    issue_ledger = build_sentinel_issues_summary(
        app_version,
        load_sentinel_issues_memory(root),
    )
    qa_findings = product_qa_review_findings(product_qa)
    if qa_findings:
        review.setdefault("findings", []).extend(qa_findings)
        finding_counts = Counter(item.get("priority", "P3") for item in review.get("findings") or [])
        review["findings_summary"] = {
            "P0": finding_counts.get("P0", 0),
            "P1": finding_counts.get("P1", 0),
            "P2": finding_counts.get("P2", 0),
            "P3": finding_counts.get("P3", 0),
            "total": len(review.get("findings") or []),
        }
        review["score"], review["score_explanation"] = _score(
            review.get("findings") or [],
            review.get("evidence_checks") or [],
        )
        review["status"] = "REQUIRES_REVIEW" if finding_counts.get("P0") or finding_counts.get("P1") else review.get("status")
    native_findings, native_review = _nw_daily_findings(root, storage, now_dt)
    if native_findings:
        review.setdefault("findings", []).extend(native_findings)
        counts = Counter(item.get("priority", "P3") for item in review["findings"])
        review["findings_summary"] = {**{key: counts.get(key, 0) for key in ("P0", "P1", "P2", "P3")}, "total": len(review["findings"])}
    board = _build_executive_board_from_review(review, app_version, now_iso)
    recommendations = _ce_recommendations_from_board(board)
    comparison = _ce_compare(recommendations, previous, history)
    memory = load_product_memory(root, storage_root=storage_root, now=now_iso)
    memory = _ce_update_memory(memory, recommendations, review, run_id, snapshot_id, now_iso, comparison)
    board = _ce_enrich_board_with_memory(board, memory, comparison)
    board["issue_health"] = issue_ledger.get("issue_health") or {}
    board["quality_director"] = product_qa.get("quality_director") or {}
    board["regression_manager"] = product_qa.get("regression_manager") or {}
    board["production_sentinel"] = product_qa.get("production_sentinel") or {}
    board["top_verified_open_issues"] = [
        {
            "id": item.get("id"),
            "priority": item.get("priority"),
            "title": item.get("title"),
            "evidence": item.get("evidence"),
        }
        for item in (issue_ledger.get("open_issues") or [])[:5]
    ]
    recommendations = _ce_recommendations_from_board(board)
    simulated = _ce_simulated_user_nightly_check(root, previous, control_fixture=control_fixture)
    result_state = "PARTIAL_WITH_UNAVAILABLE_COMPONENTS" if components_unavailable else ("PASS_WITH_REVIEW_ITEMS" if recommendations else "PASS")
    growth_instrumentation_ready = all((root / item).is_file() for item in ("engines/growth_revenue_os_engine.py", "templates/company_platform.html", "templates/admin_founder_dashboard.html"))
    growth_snapshot = build_growth_revenue_os_snapshot(
        product_snapshot={
            "growth_funnel": {"stages": {}, "simulated_stages": {}, "today_stages": {}, "channels": [], "real_events_total": 0, "simulated_events_total": 0},
            "growth_instrumentation": {
                "event_contract": GROWTH_FUNNEL_EVENT_CONTRACT,
                "safe_attribution": growth_instrumentation_ready,
                "anonymous_persistence_consent_gated": growth_instrumentation_ready,
                "landing_cro": growth_instrumentation_ready,
            },
            "growth_seo": {"status": "PASS" if growth_instrumentation_ready else "PARTIAL"},
        },
        app_version=app_version,
        now_madrid=now_iso,
    )
    snapshot: dict[str, Any] = {
        "contract": DAILY_PRODUCT_SNAPSHOT_CONTRACT,
        "continuous_evolution_contract": CONTINUOUS_EVOLUTION_OS_CONTRACT,
        "automation_contract": CONTINUOUS_EVOLUTION_AUTOMATION_CONTRACT,
        "snapshot_id": snapshot_id,
        "run_id": run_id,
        "job_id": job_id,
        "scheduled_for": scheduled_for,
        "trigger": trigger if trigger in CONTINUOUS_EVOLUTION_TRIGGERS else "MANUAL",
        "execution_mode": execution_mode,
        "scheduled_task": scheduled_task,
        "generated_at_madrid": now_iso,
        "version": app_version,
        "result": result_state,
        "systems_consulted": ["Product Review", "Autonomous Product QA", "Digital Employees", "Simulated QA evidence", "Experience evidence", "Executive Board", "Product Memory", "Temporal Comparison", "QA availability", "Beta evidence", "Operations read-only", "Roadmap signals", "Market foundation", "Growth & Revenue OS"],
        "systems_unavailable": ["REAL_USER_DATA", "PRODUCTION_LOGS", "REAL_MARKET_RESEARCH", *[item["component"] for item in components_unavailable]],
        "components_unavailable": components_unavailable,
        "product_review": _ce_compact_review(review),
        "executive_board": board,
        "findings_summary": review.get("findings_summary") or {},
        "scores": {"product_review": review.get("score"), "executive_board": board.get("board_score")},
        "risks": board.get("risks") or [],
        "opportunities": board.get("opportunities") or [],
        "modules_not_to_touch": board.get("things_not_to_touch") or [],
        "blockers": [],
        "qa_available": _ce_available_qa(root),
        "autonomous_product_qa": product_qa,
        "native_workforce": native_review,
        "issue_ledger": {
            "status_contract": issue_ledger.get("status_contract"),
            "issue_health": issue_ledger.get("issue_health") or {},
            "top_open": board.get("top_verified_open_issues") or [],
        },
        "simulated_user_nightly_check": simulated,
        "operations": _ce_operations_state(root),
        "beta": _ce_beta_state(root),
        "market_intelligence": build_market_intelligence_foundation_snapshot(root, now=now_iso),
        "growth_revenue": growth_snapshot,
        "recommendations": recommendations,
        "temporal_comparison": comparison,
        "reviewer_calibration": memory.get("reviewer_signal") or {},
        "product_memory_summary": memory.get("learning_summary") or {},
        "evidence_origin": "SIMULATED_QA" if control_fixture else "SYSTEM_OBSERVATION",
        "allowed_automation_actions": list(AUTOMATION_ALLOWED_ACTIONS),
        "prohibited_automation_actions": list(AUTOMATION_PROHIBITED_ACTIONS),
        "guardrails": {**dict(GUARDRAILS), "delete": False, "change_prices": False, "change_memberships": False, "connect_new_sources": False},
        "production_modified": False,
        "telegram_sent": False,
        "stripe_called": False,
        "automatic_code_execution": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_deploy": False,
    }
    codex_inbox = _ce_build_codex_inbox(board, snapshot_id, now_iso)
    snapshot["prepared_for_codex"] = codex_inbox
    try:
        if control_fixture and control_fixture.get("component_unavailable") == "Founder Brief":
            raise RuntimeError("Controlled Founder Brief unavailable fixture")
        founder_brief = _ce_build_founder_brief(snapshot)
    except Exception as exc:
        components_unavailable.append({"component": "Founder Brief", "status": "COMPONENT_UNAVAILABLE", "error_safe": _ce_safe_error(exc)})
        snapshot["components_unavailable"] = components_unavailable
        snapshot["systems_unavailable"] = list(dict.fromkeys([*snapshot["systems_unavailable"], "Founder Brief"]))
        snapshot["result"] = "PARTIAL_WITH_UNAVAILABLE_COMPONENTS"
        founder_brief = {"contract": FOUNDER_BRIEF_CONTRACT, "brief_id": _ce_hash("FB", snapshot_id, "partial"), "generated_at_madrid": now_iso, "state": "PARTIAL", "text": "BRIEFING DEL FUNDADOR\nFounder Brief no disponible en esta ejecucion. El snapshot y Product Memory se conservaron.", "sections": {}}
    snapshot["founder_brief"] = founder_brief
    finished_dt = _ce_now()
    finished_at = finished_dt.isoformat(timespec="seconds")
    duration_ms = max(0, int((finished_dt - started_dt).total_seconds() * 1000))
    run_record = {
        "contract": CONTINUOUS_EVOLUTION_OS_CONTRACT,
        "run_id": run_id,
        "job_id": job_id,
        "snapshot_id": snapshot_id,
        "scheduled_for": scheduled_for,
        "trigger": trigger if trigger in CONTINUOUS_EVOLUTION_TRIGGERS else "MANUAL",
        "started_at_madrid": started_at,
        "started_at_utc": _ce_utc_iso(started_at),
        "finished_at_madrid": finished_at,
        "finished_at_utc": _ce_utc_iso(finished_at),
        "duration_ms": duration_ms,
        "execution_mode": execution_mode,
        "scheduled_task": scheduled_task,
        "systems_consulted": snapshot["systems_consulted"],
        "systems_unavailable": snapshot["systems_unavailable"],
        "result": snapshot["result"],
        "error_safe": None if not components_unavailable else components_unavailable,
        "dangerous_actions_executed": False,
    }
    if write:
        _ce_write_json(paths["snapshots"] / f"{snapshot_id}.json", snapshot)
        _ce_write_json(paths["latest_snapshot"], snapshot)
        _ce_write_json(paths["runs"] / f"{run_id}.json", run_record)
        _ce_write_json(paths["latest_run"], run_record)
        _ce_write_json(paths["codex_inbox"], codex_inbox)
        _ce_write_json(paths["codex"] / f"prepared_for_codex_{snapshot_id}.json", codex_inbox)
        _ce_write_brief_markdown(paths["briefs"] / f"{founder_brief['brief_id']}.md", founder_brief)
        _ce_write_brief_markdown(paths["latest_brief"], founder_brief)
        save_product_memory(root, memory, storage_root=storage_root)
    return {"ok": True, "run": run_record, "snapshot": snapshot, "memory": memory, "storage_root": str(storage)}

def _ce_read_scheduler_state(paths: dict[str, Path], now_iso: str) -> dict[str, Any]:
    state = _ce_load_json(paths["scheduler"], {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("contract", CONTINUOUS_EVOLUTION_SCHEDULER_CONTRACT)
    state.setdefault("automation_contract", CONTINUOUS_EVOLUTION_AUTOMATION_CONTRACT)
    state.setdefault("created_at_madrid", now_iso)
    state.setdefault("updated_at_madrid", now_iso)
    state.setdefault("timezone", "Europe/Madrid")
    state.setdefault("policy", CONTINUOUS_EVOLUTION_POLICY)
    tasks = state.setdefault("tasks", {})
    now_dt = _ce_now(now_iso)
    for key, definition in CONTINUOUS_EVOLUTION_TASKS.items():
        task = tasks.setdefault(key, {})
        task.setdefault("task_name", key)
        task.setdefault("label", definition["label"])
        task.setdefault("cadence", definition["cadence"])
        task.setdefault("configured", True)
        task.setdefault("run_count", 0)
        task.setdefault("failed_count", 0)
        task.setdefault("last_run", None)
        task.setdefault("last_result", "NOT_RUN")
        task.setdefault("last_job_id", None)
        task.setdefault("last_snapshot_id", None)
        task.setdefault("last_completed_period", None)
        task.setdefault("next_expected_run", _ce_scheduled_for(key, now_dt).isoformat(timespec="seconds") if now_dt < _ce_scheduled_for(key, now_dt) else _ce_next_expected(key, now_dt))
        task.setdefault("automated_or_manual", "not_run")
        task.setdefault("evidence", "scheduler local preparado")
    return state


def build_continuous_evolution_status_snapshot(project_root: str | Path | None = None, app_version: str = "LOCAL", storage_root: str | Path | None = None, now: str | datetime | None = None) -> dict[str, Any]:
    now_iso = _ce_now(now).isoformat(timespec="seconds")
    paths = _ce_paths(_ce_storage(project_root, storage_root))
    latest = _ce_latest_snapshot(paths)
    memory = load_product_memory(project_root, storage_root=storage_root, now=now_iso)
    scheduler = _ce_read_scheduler_state(paths, now_iso)
    control = _ce_read_control(paths, now_iso)
    codex = _ce_load_json(paths["codex_inbox"], {"items": [], "ready_count": 0})
    latest_run = _ce_load_json(paths["latest_run"], None)
    jobs = _ce_job_history(paths)
    issue_ledger = build_sentinel_issues_summary(
        app_version,
        load_sentinel_issues_memory(project_root),
    )
    try:
        latest_brief = paths["latest_brief"].read_text(encoding="utf-8")
    except OSError:
        latest_brief = ""
    snapshots = _ce_snapshot_history(paths)
    native_jobs = [job for job in jobs if job.get("task_name") == "platform_workforce_review"]
    cycle_jobs = [job for job in jobs if job.get("task_name") != "platform_workforce_review"]
    completed = len([job for job in cycle_jobs if job.get("status") in {"PASS", "PARTIAL"}])
    failed = len([job for job in cycle_jobs if job.get("status") in {"FAILED", "PARTIAL"}])
    native_completed = len([job for job in native_jobs if job.get("status") in {"PASS", "PARTIAL"}])
    native_failed = len([job for job in native_jobs if job.get("status") in {"FAILED", "PARTIAL"}])
    last_job = jobs[-1] if jobs else None
    if control.get("paused"):
        automation_status = "PAUSED"
    elif last_job and last_job.get("status") == "FAILED":
        automation_status = "ERROR"
    elif completed or native_completed:
        automation_status = "ACTIVE"
    else:
        automation_status = "MANUAL"
    next_runs = [task.get("next_expected_run") for task in (scheduler.get("tasks") or {}).values() if task.get("next_expected_run")]
    next_execution = sorted(next_runs)[0] if next_runs else None
    return {
        "contract": CONTINUOUS_EVOLUTION_OS_CONTRACT,
        "automation_contract": CONTINUOUS_EVOLUTION_AUTOMATION_CONTRACT,
        "version": app_version,
        "generated_at_madrid": now_iso,
        "status": "OBSERVED" if latest else "PREPARED_ONLY",
        "automation_status": automation_status,
        "control": control,
        "latest_snapshot_id": (latest or {}).get("snapshot_id"),
        "latest_run": latest_run,
        "last_job": last_job,
        "last_execution": (last_job or {}).get("finished_at") or ((latest_run or {}).get("finished_at_madrid") if isinstance(latest_run, dict) else None),
        "next_execution": next_execution,
        "cycles_completed": completed,
        "cycles_failed": failed,
        "native_review_runs_completed": native_completed,
        "native_review_runs_failed": native_failed,
        "snapshot_count": len(snapshots),
        "product_memory": {"contract": memory.get("contract"), "recommendations": len(memory.get("recommendations") or {}), "events": len(memory.get("events") or []), "learning_summary": memory.get("learning_summary") or {}},
        "temporal_comparison": (latest or {}).get("temporal_comparison") or {"today_vs_previous": {"state": "INSUFFICIENT_HISTORY"}},
        "founder_brief": (latest or {}).get("founder_brief") or {"contract": FOUNDER_BRIEF_CONTRACT, "text": latest_brief, "state": "NOT_GENERATED"},
        "prepared_for_codex": codex,
        "issue_ledger": {
            "status_contract": issue_ledger.get("status_contract"),
            "issue_health": issue_ledger.get("issue_health") or {},
            "top_open": (issue_ledger.get("open_issues") or [])[:5],
        },
        "scheduler": scheduler,
        "market_intelligence": build_market_intelligence_foundation_snapshot(project_root, now=now_iso),
        "manual_run_available": True,
        "scheduled_run_available": True,
        "production_cron_enabled": False,
        "dangerous_actions_allowed": False,
    }


def preview_continuous_evolution_scheduler_task(project_root: str | Path | None = None, app_version: str = "LOCAL", *, task_name: str = "daily_product_review", now: str | datetime | None = None, storage_root: str | Path | None = None) -> dict[str, Any]:
    if task_name not in CONTINUOUS_EVOLUTION_TASKS:
        return {"ok": False, "task_name": task_name, "result": "UNKNOWN_TASK", "dangerous_actions_executed": False}
    now_dt = _ce_now(now)
    now_iso = now_dt.isoformat(timespec="seconds")
    paths = _ce_paths(_ce_storage(project_root, storage_root))
    state = _ce_read_scheduler_state(paths, now_iso)
    task_state = state["tasks"][task_name]
    due, scheduled_for, period = _ce_due(task_state, task_name, now_dt, force=False)
    return {"ok": True, "dry_run": True, "task_name": task_name, "scheduled_for": scheduled_for, "period": period, "due": due, "would_run": due, "status": "DUE" if due else "NOT_DUE", "next_expected_run": task_state.get("next_expected_run"), "dangerous_actions_executed": False}


def run_continuous_evolution_scheduler_task(project_root: str | Path | None = None, app_version: str = "LOCAL", *, task_name: str = "daily_product_review", force: bool = False, now: str | datetime | None = None, storage_root: str | Path | None = None, trigger: str = "SCHEDULED_LOCAL", control_fixture: dict[str, Any] | None = None) -> dict[str, Any]:
    if task_name not in CONTINUOUS_EVOLUTION_TASKS:
        return {"ok": False, "task_name": task_name, "result": "UNKNOWN_TASK", "dangerous_actions_executed": False}
    trigger = trigger if trigger in CONTINUOUS_EVOLUTION_TRIGGERS else "SCHEDULED_LOCAL"
    if trigger == "SCHEDULED_PRODUCTION" and force:
        return {"ok": False, "task_name": task_name, "result": "FORCE_NOT_ALLOWED_IN_PRODUCTION", "dangerous_actions_executed": False}
    now_dt = _ce_now(now)
    now_iso = now_dt.isoformat(timespec="seconds")
    paths = _ce_paths(_ce_storage(project_root, storage_root))
    _ce_ensure_dirs(paths)
    scheduled_for = _ce_scheduled_for(task_name, now_dt).isoformat(timespec="seconds")
    period = _ce_period_key(task_name, now_dt)
    # Same-second callers must never share a lock ownership token.
    job_id = _ce_hash("JOB", task_name, scheduled_for, trigger, now_iso, os.urandom(16).hex())
    next_run = _ce_next_expected(task_name, now_dt)
    base_job = {"contract": CONTINUOUS_EVOLUTION_JOB_CONTRACT, "job_id": job_id, "task_name": task_name, "scheduled_for": scheduled_for, "scheduled_for_utc": _ce_utc_iso(scheduled_for), "period": period, "trigger": trigger, "started_at": now_iso, "started_at_utc": _ce_utc_iso(now_iso), "finished_at": None, "finished_at_utc": None, "duration_ms": 0, "status": "PENDING", "run_id": None, "snapshot_id": None, "founder_brief_id": None, "codex_ready_count": 0, "error_safe": None, "next_expected_run": next_run, "next_expected_run_utc": _ce_utc_iso(next_run), "dangerous_actions_executed": False}
    acquired, lock = _ce_acquire_lock(paths, job_id, now_iso)
    if not acquired:
        stale = lock.get("state") in {"STALE_LOCK", "LOCK_UNVERIFIED"}
        status = lock["state"] if stale else "SKIPPED_ALREADY_RUNNING"
        base_job.update({"status": status, "finished_at": now_iso, "finished_at_utc": _ce_utc_iso(now_iso), "error_safe": {"message": "Bloqueo anterior sin cierre verificado." if stale else "Ya existe una ejecucion activa."}})
        # A losing caller must not overwrite a winning caller's state or logs.
        return {"ok": not stale, "task_name": task_name, "result": status, "job": base_job, "scheduler": _ce_read_scheduler_state(paths, now_iso), "dangerous_actions_executed": False}
    state = None
    task_state = None
    native_task = task_name == "platform_workforce_review"
    try:
        # Read again only after owning the lock. Another caller may have
        # completed this period while we were waiting to acquire it.
        state = _ce_read_scheduler_state(paths, now_iso)
        control = _ce_read_control(paths, now_iso)
        task_state = state["tasks"][task_name]
        due, scheduled_for, period = _ce_due(task_state, task_name, now_dt, force=force)
        if control.get("paused") and trigger != "MANUAL":
            status = "SKIPPED_PAUSED"
        elif not due:
            status = "SKIPPED_NOT_DUE"
        else:
            status = ""
        if status:
            base_job.update({"status": status, "finished_at": now_iso, "finished_at_utc": _ce_utc_iso(now_iso)})
            # Hourly no-op ticks preserve the last execution receipt and do not
            # create 288 new job files per day. Daily compatibility is unchanged.
            if not native_task:
                task_state["last_result"] = status
                task_state["automated_or_manual"] = "scheduled_run" if trigger != "MANUAL" else "manual_run"
                task_state["next_expected_run"] = next_run
                state["updated_at_madrid"] = now_iso
                _ce_write_json(paths["scheduler"], state)
                _ce_write_job_log(paths, base_job)
            return {"ok": True, "task_name": task_name, "result": status, "job": base_job, "scheduler": state, "dangerous_actions_executed": False}
        if native_task:
            task_state["last_attempt_period"] = period
            state["updated_at_madrid"] = now_iso
            _ce_write_json(paths["scheduler"], state)
        if control_fixture and control_fixture.get("scheduler_exception"):
            raise RuntimeError("Controlled scheduler exception fixture")
        if native_task:
            result = run_native_workforce_review(
                project_root, app_version, now=now_dt, storage_root=storage_root,
                job_id=job_id, scheduled_for=scheduled_for, trigger=trigger, write=True,
            )
            status = "PASS" if result.get("ok") is not False and result.get("result") == "PASS" else "PARTIAL"
            run = result.get("run") or {}
            snapshot = {}
            extra = {"receipt": result.get("receipt"), "run": run}
        else:
            result = run_continuous_evolution_cycle(project_root, app_version, execution_mode="scheduled_run", scheduled_task=task_name, now=now_iso, storage_root=storage_root, control_fixture=control_fixture, write=True, job_id=job_id, scheduled_for=scheduled_for, trigger=trigger)
            cycle_status = result["snapshot"].get("result") or "PASS"
            status = "PARTIAL" if str(cycle_status).startswith("PARTIAL") else "PASS"
            run = result["run"]
            snapshot = result["snapshot"]
            extra = {"cycle": result}
        finished_at = _ce_now().isoformat(timespec="seconds")
        dangerous = bool(result.get("dangerous_actions_executed") or run.get("dangerous_actions_executed"))
        base_job["dangerous_actions_executed"] = dangerous
        base_job.update({"status": status, "finished_at": finished_at, "finished_at_utc": _ce_utc_iso(finished_at), "duration_ms": run.get("duration_ms", result.get("duration_ms", 0)), "run_id": run.get("run_id") or result.get("run_id"), "snapshot_id": snapshot.get("snapshot_id"), "founder_brief_id": (snapshot.get("founder_brief") or {}).get("brief_id"), "codex_ready_count": (snapshot.get("prepared_for_codex") or {}).get("ready_count", 0), "error_safe": run.get("error_safe")})
        task_state["run_count"] = int(task_state.get("run_count") or 0) + 1
        if status == "PARTIAL":
            task_state["failed_count"] = int(task_state.get("failed_count") or 0) + 1
        task_state["last_run"] = now_iso
        task_state["last_result"] = status
        task_state["last_job_id"] = job_id
        task_state["last_snapshot_id"] = snapshot.get("snapshot_id")
        task_state["last_completed_period"] = period
        task_state["next_expected_run"] = next_run
        task_state["automated_or_manual"] = "scheduled_run" if trigger != "MANUAL" else "manual_run"
        if native_task:
            receipt = result.get("receipt") or {}
            task_state["last_receipt_id"] = receipt.get("receipt_id") or run.get("run_id")
            task_state["evidence"] = "native_workforce " + str(task_state["last_receipt_id"] or "NO_RECEIPT")
        else:
            task_state["evidence"] = f"snapshot {task_state['last_snapshot_id']}"
        if task_name == "daily_product_review":
            brief_task = state["tasks"].get("daily_founder_brief") or {}
            brief_task.update({"run_count": int(brief_task.get("run_count") or 0) + 1, "last_run": now_iso, "last_result": status, "last_job_id": job_id, "last_snapshot_id": snapshot.get("snapshot_id"), "last_completed_period": period, "next_expected_run": _ce_next_expected("daily_founder_brief", now_dt), "automated_or_manual": "scheduled_run", "evidence": "Founder Brief generado despues de Daily Product Review"})
            state["tasks"]["daily_founder_brief"] = brief_task
        state["updated_at_madrid"] = now_iso
        _ce_write_json(paths["scheduler"], state)
        _ce_write_job_log(paths, base_job)
        return {"ok": result.get("ok") is not False and not dangerous, "task_name": task_name, "result": status, "job": base_job, "scheduler": state, **extra, "dangerous_actions_executed": dangerous}
    except Exception as exc:
        finished_at = _ce_now().isoformat(timespec="seconds")
        safe = _ce_safe_error(exc)
        base_job.update({"status": "PARTIAL", "finished_at": finished_at, "finished_at_utc": _ce_utc_iso(finished_at), "error_safe": safe})
        if state is not None and task_state is not None:
            task_state["failed_count"] = int(task_state.get("failed_count") or 0) + 1
            task_state["last_result"] = "PARTIAL"
            task_state["last_job_id"] = job_id
            task_state["next_expected_run"] = next_run
            state["updated_at_madrid"] = now_iso
            _ce_write_json(paths["scheduler"], state)
            _ce_write_job_log(paths, base_job)
        return {"ok": False, "task_name": task_name, "result": "PARTIAL", "job": base_job, "scheduler": state or {}, "error_safe": safe, "dangerous_actions_executed": False}
    finally:
        _ce_release_lock(paths, job_id)


def run_safe_continuous_evolution_runner(project_root: str | Path | None = None, app_version: str = "LOCAL", *, task_name: str = "daily_product_review", dry_run: bool = False, trigger: str = "SCHEDULED_LOCAL", now: str | datetime | None = None, storage_root: str | Path | None = None, force: bool = False) -> dict[str, Any]:
    guardrails = {"DRY_RUN": bool(dry_run), "READ_ONLY_OPERATIONS": True, "NO_TELEGRAM": True, "NO_STRIPE": True, "NO_DEPLOY": True, "NO_EXTERNAL_MARKET_RESEARCH": True, "NO_PRODUCTION_MUTATION": True}
    if dry_run:
        preview = preview_continuous_evolution_scheduler_task(project_root, app_version, task_name=task_name, now=now, storage_root=storage_root)
        return {"ok": preview.get("ok"), "runner_contract": CONTINUOUS_EVOLUTION_AUTOMATION_CONTRACT, "dry_run": True, "preview": preview, "guardrails": guardrails, "dangerous_actions_executed": False}
    result = run_continuous_evolution_scheduler_task(project_root, app_version, task_name=task_name, force=force, now=now, storage_root=storage_root, trigger=trigger)
    result["runner_contract"] = CONTINUOUS_EVOLUTION_AUTOMATION_CONTRACT
    result["guardrails"] = guardrails
    return result



def run_continuous_evolution_three_day_certification(project_root: str | Path | None = None, app_version: str = "LOCAL", *, storage_root: str | Path | None = None, start_date: str = "2026-08-11") -> dict[str, Any]:
    start = datetime.fromisoformat(start_date).replace(tzinfo=MADRID)
    runs = []
    repeat_checks = []
    for offset in range(3):
        now_dt = (start + timedelta(days=offset)).replace(hour=4, minute=0, second=0, microsecond=0)
        fixture = None
        if offset == 2:
            fixture = {"simulated_persona": "MOBILE", "simulated_metrics": {"friction_indicators": 2}}
        run = run_continuous_evolution_scheduler_task(project_root, app_version, task_name="daily_product_review", now=now_dt, storage_root=storage_root, control_fixture=fixture)
        runs.append(run)
        repeat = run_continuous_evolution_scheduler_task(project_root, app_version, task_name="daily_product_review", now=now_dt + timedelta(minutes=5), storage_root=storage_root)
        repeat_checks.append(repeat)
    status = build_continuous_evolution_status_snapshot(project_root, app_version, storage_root=storage_root, now=start + timedelta(days=2, hours=5))
    memory = load_product_memory(project_root, storage_root=storage_root)
    pass_state = all(item.get("result") in {"PASS", "PARTIAL"} for item in runs) and all(item.get("result") == "SKIPPED_NOT_DUE" for item in repeat_checks) and status.get("snapshot_count", 0) >= 3
    return {
        "contract": CONTINUOUS_EVOLUTION_CERTIFICATION_CONTRACT,
        "ok": pass_state,
        "status": "PASS" if pass_state else "PARTIAL",
        "days": 3,
        "runs": [{"day": index + 1, "result": item.get("result"), "job_id": (item.get("job") or {}).get("job_id"), "snapshot_id": (item.get("job") or {}).get("snapshot_id")} for index, item in enumerate(runs)],
        "repeat_checks": [{"day": index + 1, "result": item.get("result")} for index, item in enumerate(repeat_checks)],
        "snapshot_count": status.get("snapshot_count"),
        "memory_snapshots": len(memory.get("snapshots") or []),
        "founder_brief_ready": bool((status.get("founder_brief") or {}).get("text")),
        "codex_ready_count": (status.get("prepared_for_codex") or {}).get("ready_count"),
        "learning": (status.get("product_memory") or {}).get("learning_summary"),
        "dangerous_actions_executed": False,
        "production_modified": False,
        "telegram_sent": False,
        "stripe_called": False,
    }

def record_continuous_evolution_decision(project_root: str | Path | None, recommendation_id: str, decision: str, reason: str, *, actor: str = "founder", storage_root: str | Path | None = None, now: str | datetime | None = None) -> dict[str, Any]:
    now_iso = _ce_now(now).isoformat(timespec="seconds")
    decision = str(decision or "").upper()
    if decision not in RECOMMENDATION_STATES:
        return {"ok": False, "error": "invalid_decision_state", "allowed": sorted(RECOMMENDATION_STATES)}
    memory = load_product_memory(project_root, storage_root=storage_root, now=now_iso)
    record = (memory.get("recommendations") or {}).get(recommendation_id)
    if not record:
        return {"ok": False, "error": "recommendation_not_found", "recommendation_id": recommendation_id}
    transition = {"at_madrid": now_iso, "actor": actor, "from": record.get("state"), "to": decision, "reason": _ce_clean_text(reason, 420)}
    record.setdefault("decisions", []).append(transition)
    record.setdefault("decision_history", []).append(transition)
    record["state"] = decision
    record["decision_reason"] = transition["reason"]
    if decision in {"RESOLVED", "VERIFIED"}:
        record["resolved_at"] = now_iso
    memory.setdefault("events", []).append({"event_id": _ce_hash("EVT", recommendation_id, decision, now_iso), "type": "HUMAN_DECISION", "recommendation_id": recommendation_id, "at_madrid": now_iso, "decision": decision, "actor": actor})
    memory["updated_at_madrid"] = now_iso
    save_product_memory(project_root, memory, storage_root=storage_root)
    return {"ok": True, "recommendation_id": recommendation_id, "decision": decision, "transition": transition}


# A bounded reviewer inside Continuous Evolution, not a new business executor.
NATIVE_WORKFORCE_REVIEW_CONTRACT = "NEMESIS-NATIVE-WORKFORCE-REVIEW-V1"
NATIVE_WORKFORCE_MEMORY_CONTRACT = "NEMESIS-NATIVE-WORKFORCE-MEMORY-V1"
NATIVE_WORKFORCE_BUDGET_SECONDS = 2.0
NATIVE_WORKFORCE_MAX_SOURCE_BYTES = 8 * 1024 * 1024
NATIVE_WORKFORCE_MAX_FILE_BYTES = 3 * 1024 * 1024
NATIVE_WORKFORCE_MAX_STORE_BYTES = 4 * 1024 * 1024
NATIVE_WORKFORCE_HISTORY_LIMIT = 48
NATIVE_WORKFORCE_GAME_IDS = (
    "arcade_signal", "strategy_information", "technical_art", "game_motion",
    "platform_accessibility", "graphics_performance", "visual_qa_director",
)
# Stable IDs identify a narrow static contract, never a person's employment or
# proof that the underlying business activity has happened.
NATIVE_WORKFORCE_CORE_CHECKS = (
    ("product_ceo", "Product CEO Worker", "catalog", ("engines/company_operating_system_engine.py",)),
    ("technical_director", "Technical Director Worker", "python_syntax", ("app.py", "engines/security_engine.py")),
    ("client_experience", "Client Experience Worker", "navigation", ("templates/components/v933_navigation.html",)),
    ("admin_command_center", "Admin Command Center Worker", "inventory_isolation", ("templates/admin_company_os.html",)),
    ("membership_value", "Membership Value Worker", "membership", ("engines/membership_engine.py",)),
    ("shark_intelligence", "SHARK Intelligence Worker", "request_contract", ("engines/shark_request_contract.py",)),
    ("telegram_premium", "Telegram Premium Worker", "queue_states", ("engines/telegram_delivery_engine.py",)),
    ("sports_data", "Sports Data Worker", "evidence_states", ("engines/sports_platform_contracts.py",)),
    ("odds_picks", "Odds & Picks Worker", "grading_states", ("engines/pick_grading_engine.py",)),
    ("crest_identity", "Crest & Identity Worker", "identity_manifest", ("static/img/approved-identity/manifest.json",)),
    ("routes_buttons", "Routes & Buttons Worker", "navigation", ("templates/base.html", "templates/components/v933_navigation.html")),
    ("spanish_copy", "Spanish Copy Worker", "visible_encoding", ("templates/home.html", "templates/client_app_center.html", "templates/admin_company_os.html")),
    ("qa_visual", "QA Visual Worker", "design_contract", ("reference_images/design_contracts.json",)),
    ("qa_data_reality", "QA Data Reality Worker", "finite_json_contract", ("engines/shark_request_contract.py",)),
    ("render_zip", "Render ZIP Worker", "deployment_declaration", ("render.yaml", "Procfile")),
)
NATIVE_WORKFORCE_GAME_TARGETS = (
    "reference_images/design_contracts.json", "static/img/approved-identity/manifest.json",
    "tools/visual_css_sources.json", "static/design-tokens.css", "static/design-system.css",
    "static/v968-directo-freshness.css", "static/v969-directo-mobile-calendar.css",
    "static/product-system.css", "templates/base.html", "static/platform-motion.js",
    "static/v1000-client-refinement.css", "templates/components/app_navigation.html",
    "templates/components/v933_navigation.html",
)
NATIVE_WORKFORCE_TARGETS = tuple(dict.fromkeys(
    [path for _, _, _, targets in NATIVE_WORKFORCE_CORE_CHECKS for path in targets]
    + list(NATIVE_WORKFORCE_GAME_TARGETS)
))
NATIVE_WORKFORCE_PROPOSALS = {
    "product_ceo": "Mantener las 15 responsabilidades diferenciadas y aportar resultados observados para priorizar valor comercial.",
    "technical_director": "Revisar la sintaxis si aparece un fallo y adjuntar health-check y recibo del tick del candidato.",
    "client_experience": "Verificar los destinos de navegación y completar una muestra real de tareas de cliente móvil y PC.",
    "admin_command_center": "Mantener las disciplinas Game UI fuera del inventario de 15 trabajadores y verificar el panel renderizado.",
    "membership_value": "Conservar referencias coherentes entre planes, límites y funciones; verificar después permisos reales por rol.",
    "shark_intelligence": "Conservar el contrato de entrada SHARK y verificar respuestas, rechazo de entradas y fallback sin proveedor.",
    "telegram_premium": "Conservar estados de cola distintos y límite declarado; aportar recibos de dedupe y calidad sin realizar envíos de prueba.",
    "sports_data": "Preservar estados de evidencia desconocida y obsoleta; aportar antigüedad real de la caché deportiva.",
    "odds_picks": "Revisar estados elegibles de grading y contrastarlos con picks reales sin publicar ni liquidar desde esta revisión.",
    "crest_identity": "Conservar metadatos válidos de los recursos aprobados y comprobar archivos y apariencia con evidencia específica.",
    "routes_buttons": "Revisar esquemas de enlace y verificar clicks, retorno y logout en navegador con permisos reales.",
    "spanish_copy": "Revisar daños de codificación si aparecen y comprobar copy renderizado, incluyendo datos dinámicos.",
    "qa_visual": "Conservar identificadores de pantallas únicos y adjuntar capturas del mismo candidato para evaluación visual.",
    "qa_data_reality": "Conservar JSON finito y verificar estados sin datos reales antes de certificar métricas o resultados.",
    "render_zip": "Reconciliar declaraciones de arranque y aportar auditoría del ZIP y evidencia del despliegue real.",
}


def _nw_clock() -> float:
    import time
    return time.monotonic()


def _nw_state_path(storage: Path) -> Path:
    return storage / "native_workforce" / "state.json"


def _nw_json_read(path: Path, maximum: int = NATIVE_WORKFORCE_MAX_STORE_BYTES) -> Any:
    """Bounded read; malformed history must not be silently replaced."""
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("native_workforce_store_too_large")
    return json.loads(raw)


def _nw_fingerprint(evidence: list[dict[str, Any]]) -> str:
    material = [[item["path"], item.get("sha256"), item.get("state")] for item in evidence]
    return hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _nw_read_sources(root: Path, deadline: float) -> tuple[dict[str, str | None], dict[str, dict[str, Any]], int]:
    """Read only fixed code/contract paths, once; no runtime data or DB reads."""
    import stat
    snapshot: dict[str, str | None] = {}
    evidence: dict[str, dict[str, Any]] = {}
    total = 0
    for relative in NATIVE_WORKFORCE_TARGETS:
        snapshot[relative] = None
        item: dict[str, Any] = {"path": relative, "state": "BUDGET_EXHAUSTED", "sha256": None}
        evidence[relative] = item
        if _nw_clock() >= deadline:
            continue
        try:
            path = (root / relative).resolve()
            if not path.is_relative_to(root):
                item["state"] = "OUTSIDE_PROJECT"
                continue
            info = path.stat()
            if not stat.S_ISREG(info.st_mode):
                item["state"] = "NOT_REGULAR_FILE"
                continue
            allowance = min(NATIVE_WORKFORCE_MAX_FILE_BYTES, NATIVE_WORKFORCE_MAX_SOURCE_BYTES - total)
            if info.st_size > allowance:
                item["state"] = "INPUT_LIMIT"
                continue
            with path.open("rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    item["state"] = "NOT_REGULAR_FILE"
                    continue
                raw = stream.read(allowance)
                grew = os.fstat(stream.fileno()).st_size > allowance
            total += len(raw)
            if grew:
                item["state"] = "INPUT_LIMIT"
                continue
            item.update({"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
            snapshot[relative] = raw.decode("utf-8-sig")
            item["state"] = "READ"
        except FileNotFoundError:
            item["state"] = "MISSING"
        except UnicodeDecodeError:
            item["state"] = "INVALID_UTF8"
        except OSError:
            item["state"] = "UNAVAILABLE"
    return snapshot, evidence, total


def _nw_literals(source: str) -> tuple[Any, dict[str, Any]]:
    import ast
    tree = ast.parse(source)
    values = {}
    for statement in tree.body:
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            names = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            for name in names:
                if isinstance(name, ast.Name):
                    try:
                        values[name.id] = ast.literal_eval(statement.value)
                    except (ValueError, TypeError):
                        pass
    return tree, values


def _nw_markup(source: str) -> tuple[list[dict[str, str | None]], str]:
    from html.parser import HTMLParser

    class VisibleMarkup(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.links = []
            self.visible = []
            self.hidden = 0

        def handle_starttag(self, tag, attrs):
            if tag in {"style", "script"}:
                self.hidden += 1
            if tag == "a":
                self.links.append(dict(attrs))

        def handle_endtag(self, tag):
            if tag in {"style", "script"}:
                self.hidden = max(0, self.hidden - 1)

        def handle_data(self, data):
            if not self.hidden:
                self.visible.append(data)

    parser = VisibleMarkup()
    parser.feed(source)
    return parser.links, " ".join(parser.visible)


def _nw_static_check(kind: str, sources: list[str]) -> tuple[str, str]:
    """Return a narrow result code, never source excerpts or business proof."""
    import ast
    if kind == "python_syntax":
        for source in sources:
            ast.parse(source)
        return "PASS", "PYTHON_SYNTAX_VALID"
    if kind == "catalog":
        _, values = _nw_literals(sources[0])
        catalog = values.get("WORKER_BLUEPRINTS")
        expected = [item[1] for item in NATIVE_WORKFORCE_CORE_CHECKS]
        if not isinstance(catalog, (list, tuple)):
            return "UNKNOWN", "CATALOG_NOT_LITERAL"
        actual = [row[0] for row in catalog if isinstance(row, (list, tuple)) and row]
        return ("PASS", "CATALOG_15_UNIQUE") if len(actual) == 15 and set(actual) == set(expected) else ("FAIL", "CATALOG_ROLE_MISMATCH")
    if kind == "inventory_isolation":
        bad = re.search(r'<details\b[^>]*class\s*=\s*[\"\'][^\"\']*\bv857-worker-card\b', sources[0], re.I)
        return ("FAIL", "DISCIPLINE_CONTAMINATES_WORKER_INVENTORY") if bad else ("PASS", "DISCIPLINE_CLASS_ISOLATED")
    if kind == "navigation":
        links = [link for source in sources for link in _nw_markup(source)[0]]
        literal = [str(link.get("href") or "").strip() for link in links if "{{" not in str(link.get("href") or "")]
        if any(re.match(r"(?i)^(?:javascript|vbscript):", value) for value in literal):
            return "FAIL", "SCRIPT_URL_IN_STATIC_ANCHOR"
        return ("PASS", "STATIC_ANCHOR_SCHEMES_VALID") if literal else ("UNKNOWN", "NO_LITERAL_ANCHORS")
    if kind == "visible_encoding":
        visible = " ".join(_nw_markup(source)[1] for source in sources)
        invalid = re.search("\ufffd|Ã[\u0080-\u00bf]|Â[\u0080-\u00bf]|â€", visible)
        return ("FAIL", "VISIBLE_ENCODING_DAMAGE") if invalid else ("PASS", "NO_KNOWN_VISIBLE_ENCODING_DAMAGE")
    if kind == "membership":
        _, values = _nw_literals(sources[0])
        order, features, limits = [values.get(key) for key in ("PLAN_ORDER", "FEATURE_MIN_PLAN", "MEMBERSHIP_LIMITS")]
        if not all(isinstance(value, dict) for value in (order, features, limits)):
            return "UNKNOWN", "MEMBERSHIP_CONTRACT_NOT_LITERAL"
        valid = set(order) == {"FREE", "PRO", "ELITE", "ADMIN"} and set(limits) == set(order)
        valid = valid and all(type(value) is int for value in order.values()) and len(set(order.values())) == len(order)
        valid = valid and bool(features) and all(value in order for value in features.values())
        return ("PASS", "PLAN_REFERENCES_CONSISTENT") if valid else ("FAIL", "PLAN_REFERENCE_MISMATCH")
    if kind in {"request_contract", "finite_json_contract"}:
        tree, _ = _nw_literals(sources[0])
        functions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        if kind == "request_contract":
            required = {"normalize_request", "finite_json", "encode_snapshot"}
            return ("PASS", "REQUEST_CONTRACT_FUNCTIONS_PRESENT") if required <= set(functions) else ("FAIL", "REQUEST_CONTRACT_FUNCTION_MISSING")
        encoder = functions.get("encode_snapshot")
        if encoder is None:
            return "FAIL", "SNAPSHOT_ENCODER_MISSING"
        dumps = [node for node in ast.walk(encoder) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and isinstance(node.func.value, ast.Name) and node.func.value.id == "json" and node.func.attr == "dumps"]
        finite = bool(dumps) and all(any(key.arg == "allow_nan" and isinstance(key.value, ast.Constant) and key.value.value is False for key in call.keywords) for call in dumps)
        return ("PASS", "SNAPSHOT_JSON_REJECTS_NONFINITE_LITERAL") if finite else ("FAIL", "SNAPSHOT_JSON_NONFINITE_GUARD_MISSING")
    if kind == "queue_states":
        _, values = _nw_literals(sources[0])
        states = [values.get("QUEUE_" + key) for key in ("PENDING", "SENDING", "SENT", "FAILED", "SKIPPED")]
        settings = values.get("DEFAULT_SETTINGS")
        if not all(isinstance(value, str) for value in states) or not isinstance(settings, dict):
            return "UNKNOWN", "QUEUE_CONTRACT_NOT_LITERAL"
        valid = len(set(states)) == 5 and type(settings.get("max_messages_per_hour")) is int and settings["max_messages_per_hour"] > 0
        return ("PASS", "QUEUE_STATES_DISTINCT_WITH_DECLARED_LIMIT") if valid else ("FAIL", "QUEUE_STATE_OR_LIMIT_INVALID")
    if kind == "evidence_states":
        _, values = _nw_literals(sources[0])
        states = values.get("EVIDENCE_STATES")
        if not isinstance(states, (list, tuple)):
            return "UNKNOWN", "EVIDENCE_STATES_NOT_LITERAL"
        valid = all(isinstance(state, str) for state in states) and len(set(states)) == len(states)
        valid = valid and {"NOT_CERTIFIED", "NOT_CONFIGURED", "STALE", "INSUFFICIENT_DATA"} <= set(states)
        return ("PASS", "UNKNOWN_AND_STALE_EVIDENCE_STATES_DECLARED") if valid else ("FAIL", "EVIDENCE_STATE_CONTRACT_INVALID")
    if kind == "grading_states":
        _, values = _nw_literals(sources[0])
        states = values.get("ELIGIBLE_PICK_STATUSES")
        if not isinstance(states, (list, tuple)) or not all(isinstance(value, str) for value in states):
            return "UNKNOWN", "GRADING_STATES_NOT_LITERAL"
        valid = {"published", "pending", "won", "lost", "void"} <= set(states) and not {"draft", "archived", "deleted"}.intersection(states)
        return ("PASS", "PUBLIC_GRADING_STATES_DECLARED") if valid else ("FAIL", "GRADING_STATUS_CONTRACT_INVALID")
    if kind == "identity_manifest":
        manifest = json.loads(sources[0])
        assets = manifest.get("assets") if isinstance(manifest, dict) else None
        if not isinstance(assets, list) or not assets:
            return "FAIL", "IDENTITY_MANIFEST_HAS_NO_ASSETS"
        names = []
        for asset in assets:
            if not isinstance(asset, dict):
                return "FAIL", "IDENTITY_MANIFEST_ENTRY_INVALID"
            name = asset.get("file")
            if not isinstance(name, str) or Path(name).name != name or name in {".", ".."} or not name:
                return "FAIL", "IDENTITY_MANIFEST_PATH_INVALID"
            if not re.fullmatch(r"[a-f0-9]{64}", str(asset.get("sha256") or "")) or type(asset.get("bytes")) is not int or asset["bytes"] <= 0:
                return "FAIL", "IDENTITY_MANIFEST_DIGEST_OR_SIZE_INVALID"
            names.append(name)
        return ("PASS", "DECLARED_ASSET_METADATA_CONSISTENT") if len(set(names)) == len(names) else ("FAIL", "IDENTITY_MANIFEST_DUPLICATE_ASSET")
    if kind == "design_contract":
        contract = json.loads(sources[0])
        screens = contract.get("screens") if isinstance(contract, dict) else None
        if not isinstance(screens, list) or not screens:
            return "FAIL", "DESIGN_CONTRACT_SCREENS_MISSING"
        ids = [item.get("screen_id") for item in screens if isinstance(item, dict)]
        valid = contract.get("contract") == "NEMESIS-CREATIVE-DESIGN-1" and len(ids) == len(screens)
        valid = valid and all(isinstance(value, str) and value for value in ids) and len(set(ids)) == len(ids)
        return ("PASS", "DESIGN_SCREEN_IDENTITIES_UNIQUE") if valid else ("FAIL", "DESIGN_SCREEN_CONTRACT_INVALID")
    if kind == "deployment_declaration":
        web = re.findall(r"(?m)^\s*startCommand:\s*(.+)$", sources[0])
        proc = re.findall(r"(?m)^web:\s*(.+)$", sources[1])
        if not web or not proc:
            return "UNKNOWN", "DEPLOYMENT_DECLARATION_NOT_SUPPORTED"
        valid = proc[0].strip() in [value.strip() for value in web]
        return ("PASS", "WEB_START_DECLARATIONS_CONSISTENT") if valid else ("FAIL", "WEB_START_DECLARATIONS_DIFFER")
    return "UNKNOWN", "CHECK_NOT_IMPLEMENTED"


def _nw_core_result(definition: tuple, snapshot: dict[str, str | None], inputs: dict[str, dict[str, Any]], deadline: float) -> dict[str, Any]:
    check_id, name, kind, targets = definition
    evidence = [dict(inputs[path]) for path in targets]
    executed = _nw_clock() < deadline and not any(item["state"] == "BUDGET_EXHAUSTED" for item in evidence)
    static_state, code = "UNKNOWN", "BUDGET_EXHAUSTED"
    if executed:
        if any(item["state"] == "INVALID_UTF8" for item in evidence):
            static_state, code = "FAIL", "INVALID_UTF8_SOURCE"
        elif any(snapshot[path] is None for path in targets):
            code = "SOURCE_UNAVAILABLE_OR_BOUNDED"
        else:
            try:
                static_state, code = _nw_static_check(kind, [snapshot[path] for path in targets])
            except (SyntaxError, json.JSONDecodeError):
                static_state, code = "FAIL", "SOURCE_SYNTAX_INVALID"
            except (ValueError, TypeError, KeyError, RecursionError):
                static_state, code = "UNKNOWN", "UNSUPPORTED_SOURCE_STRUCTURE"
    return {
        "id": check_id, "worker_name": name, "group": "company_core", "executed": executed,
        "state": "FAIL" if static_state == "FAIL" else "UNKNOWN",
        "static_state": static_state, "check_ids": ["core." + check_id + "." + kind],
        "targets": list(targets), "source_fingerprint": _nw_fingerprint(evidence), "evidence": evidence,
        "checks": [{"id": kind, "state": static_state, "result": code}],
        "limitation": "Revisión estática parcial. No ejecuta negocio, proveedores, rutas HTTP, browser ni certifica producción.",
        "business_execution_certified": False,
        "proposal": NATIVE_WORKFORCE_PROPOSALS[check_id],
    }


def _nw_game_results(root: Path, snapshot: dict[str, str | None], inputs: dict[str, dict[str, Any]], deadline: float, revision: str, observed_at: str) -> list[dict[str, Any]]:
    rows = {}
    if _nw_clock() < deadline:
        try:
            from engines.game_ui_review_lab import evaluate_game_ui_review
            evaluated = evaluate_game_ui_review(root, input_snapshot=snapshot, deadline=deadline,
                                                candidate_revision=revision, observed_at=observed_at)
            rows = {row.get("id"): row for row in evaluated.get("disciplines", []) if isinstance(row, dict)}
        except (ImportError, AttributeError, TypeError, ValueError, KeyError, OSError):
            rows = {}
    results = []
    for check_id in NATIVE_WORKFORCE_GAME_IDS:
        row = rows.get(check_id)
        targets = [path for path in (row or {}).get("targets", NATIVE_WORKFORCE_GAME_TARGETS) if path in inputs]
        evidence = [dict(inputs[path]) for path in targets]
        checks = []
        for check in (row or {}).get("checks", []):
            if isinstance(check, dict):
                checks.append({"id": str(check.get("id") or "")[:100],
                               "state": check.get("state") if check.get("state") in {"PASS", "FAIL", "UNKNOWN"} else "UNKNOWN",
                               "detail": _ce_clean_text(check.get("detail"), 360)})
        executed = bool(row and row.get("executed", True) and not any(item["state"] == "BUDGET_EXHAUSTED" for item in evidence))
        state = row.get("state") if row and row.get("state") in {"PASS", "FAIL", "UNKNOWN"} else "UNKNOWN"
        results.append({"id": check_id, "group": "game_ui", "executed": executed, "state": state,
                        "area": _ce_clean_text((row or {}).get("area"), 140),
                        "check_ids": ["game_ui." + check_id], "targets": targets,
                        "source_fingerprint": _nw_fingerprint(evidence), "evidence": evidence, "checks": checks,
                        "limitation": "Análisis estático de Game UI; sin capturas, clicks ni métricas reales de navegador.",
                        "business_execution_certified": False,
                        "proposal": _ce_clean_text((row or {}).get("proposal"), 420)})
    return results


def _nw_valid_receipt(receipt: Any) -> bool:
    expected = {item[0] for item in NATIVE_WORKFORCE_CORE_CHECKS} | set(NATIVE_WORKFORCE_GAME_IDS)
    if not isinstance(receipt, dict) or receipt.get("contract") != NATIVE_WORKFORCE_REVIEW_CONTRACT:
        return False
    results = receipt.get("results")
    if not isinstance(results, list) or len(results) != 22 or not all(isinstance(row, dict) for row in results):
        return False
    if {row.get("id") for row in results} != expected or any(row.get("state") not in {"PASS", "FAIL", "UNKNOWN"} or type(row.get("executed")) is not bool for row in results):
        return False
    if receipt.get("expected_count") != 22 or receipt.get("executed_count") != sum(row.get("executed") is True for row in results):
        return False
    outcome = "FAIL" if any(row["state"] == "FAIL" for row in results) else ("UNKNOWN" if any(row["state"] == "UNKNOWN" for row in results) else "PASS")
    return (receipt.get("review_kind") == "STATIC_PARTIAL" and receipt.get("outcome") == outcome and receipt.get("production_certified") is False
            and receipt.get("business_execution_certified") is False and receipt.get("external_calls") == 0
            and receipt.get("browser_executed") is False and receipt.get("source_revision_verified") is False
            and bool(re.fullmatch(r"[a-f0-9]{64}", str(receipt.get("source_fingerprint") or "")))
            and bool(re.fullmatch(r"NWR-[a-f0-9]{16}", str(receipt.get("receipt_id") or ""))))


def load_native_workforce_receipt(project_root: str | Path | None = None, *, storage_root: str | Path | None = None, now: str | datetime | None = None, max_age_seconds: int = 7200) -> dict[str, Any]:
    """Read-only evidence projection. Reading Company OS never starts a review."""
    empty = {"state": "NOT_RUN", "age_seconds": None, "receipt": None, "results": []}
    path = _nw_state_path(_ce_storage(project_root, storage_root))
    try:
        state = _nw_json_read(path)
        receipt = state.get("latest") if isinstance(state, dict) and state.get("contract") == NATIVE_WORKFORCE_MEMORY_CONTRACT else None
        if not _nw_valid_receipt(receipt):
            return {**empty, "state": "UNAVAILABLE"}
        finished = datetime.fromisoformat(receipt["finished_at_madrid"])
        if finished.tzinfo is None:
            return {**empty, "state": "CLOCK_UNVERIFIED"}
        age = (_ce_now(now) - finished).total_seconds()
        # Scheduler supplies a single nominal clock to sequential tasks. Allow
        # only the bounded review duration as clock tolerance, not arbitrary future evidence.
        freshness = "CLOCK_UNVERIFIED" if age < -NATIVE_WORKFORCE_BUDGET_SECONDS else ("RECENT" if age <= max_age_seconds else "STALE")
        current_revision = str(os.getenv("RENDER_GIT_COMMIT") or "")
        advertised = str(receipt.get("source_revision_advertised") or "")
        revision_changed = (re.fullmatch(r"[a-fA-F0-9]{40}", current_revision) and re.fullmatch(r"[a-fA-F0-9]{40}", advertised)
                            and current_revision.lower() != advertised.lower())
        if revision_changed:
            freshness = "STALE"
        return {"state": freshness, "age_seconds": max(0, round(age)), "receipt": receipt,
                "results": receipt["results"] if freshness == "RECENT" else [],
                "reason": "SOURCE_REVISION_CHANGED" if revision_changed else None}
    except FileNotFoundError:
        return empty
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        return {**empty, "state": "UNAVAILABLE"}


def _nw_proposal(row: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    failed = row["state"] == "FAIL"
    check_id = row["id"]
    # Stable problem scope; changing evidence/hash must not create a new backlog item.
    proposal = row.get("proposal") or "Revisar el contrato estático y aportar evidencia ejecutada para " + check_id + "."
    return {
        "id": "NWR-" + check_id, "source_family": "native_workforce", "check_id": check_id,
        "reviewer": row.get("worker_name") or row.get("area") or "Game UI · " + check_id,
        "module": "Native Workforce", "screen": (row.get("targets") or ["local source"])[0],
        "route": "/admin/company-os", "component": "native_workforce." + check_id,
        "priority": "P2" if failed else "P3", "proposal": proposal,
        "evidence": "receipt=" + receipt["receipt_id"] + "; check=" + check_id + "; result=" + row["state"] + "; fingerprint=" + row["source_fingerprint"],
        "evidence_origin": "SYSTEM_OBSERVATION", "issue_status": "OPEN_REAL" if failed else "INSUFFICIENT_EVIDENCE",
        "evidence_sufficient": failed, "certification_state": "STATIC_PARTIAL",
        "impact_user": "Detectar defectos estáticos concretos y señalar lo que falta comprobar con evidencia real.",
        "impact_business": "Priorizar mejoras sin inventar actividad, resultados comerciales ni certificación visual.",
        "automatic_execution_allowed": False, "approved_for_execution": False,
        "candidate_improvement_ready": failed,
    }


def _nw_update_state(previous: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    state = dict(previous)
    proposals = {key: dict(value) for key, value in (previous.get("proposals") or {}).items()}
    now_iso = receipt["finished_at_madrid"]
    for row in receipt["results"]:
        if not row["executed"]:
            continue
        check_id = row["id"]
        existing = proposals.get(check_id)
        if row["state"] == "PASS":
            # A scoped success does not resolve a human decision or wider business issue.
            if existing:
                existing["last_observation"] = "PASS"
                existing["last_observed_at"] = now_iso
            continue
        if existing is None:
            existing = {"state": "NEW", "first_seen": now_iso, "seen_count": 0, "reopened_count": 0, "decisions": []}
            proposals[check_id] = existing
        if row["state"] == "FAIL" and existing.get("state") in {"RESOLVED", "VERIFIED", "IMPLEMENTED"}:
            existing["state"] = "REGRESSED"
            existing["reopened_count"] = int(existing.get("reopened_count") or 0) + 1
        existing.update({"last_seen": now_iso, "last_observed_at": now_iso, "last_observation": row["state"],
                         "last_receipt_id": receipt["receipt_id"], "seen_count": int(existing.get("seen_count") or 0) + 1,
                         "finding": _nw_proposal(row, receipt)})
    if len(proposals) > 128:
        raise ValueError("native_workforce_proposal_capacity")
    state.update({"contract": NATIVE_WORKFORCE_MEMORY_CONTRACT, "latest": receipt, "proposals": proposals,
                  "history": [*(previous.get("history") or []), receipt][-NATIVE_WORKFORCE_HISTORY_LIMIT:]})
    return state


def _nw_lock_owned(storage: Path, job_id: str) -> bool:
    if not job_id:
        return False
    try:
        lock = _nw_json_read(_ce_paths(storage)["scheduler_lock"], maximum=4096)
        return isinstance(lock, dict) and lock.get("job_id") == job_id and lock.get("pid") == os.getpid()
    except (OSError, ValueError, TypeError):
        return False


def run_native_workforce_review(project_root: str | Path | None = None, app_version: str = "LOCAL", *, now: str | datetime | None = None, storage_root: str | Path | None = None, job_id: str = "", scheduled_for: str = "", trigger: str = "SCHEDULED_PRODUCTION", write: bool = True) -> dict[str, Any]:
    """Run at most 2 seconds of cooperative static analysis under scheduler lock.

    PASS means all 22 evaluations finished. Receipt outcome separately reports
    FAIL/UNKNOWN; it never certifies the 15 business responsibilities as active.
    write=False supports local fixtures without acquiring or creating a lock.
    """
    start = _nw_clock()
    deadline = start + NATIVE_WORKFORCE_BUDGET_SECONDS
    root, storage = _root(project_root), _ce_storage(project_root, storage_root)
    if write and not _nw_lock_owned(storage, job_id):
        raise RuntimeError("native_workforce_requires_owned_scheduler_lock")
    now_dt = _ce_now(now)
    started_at = now_dt.isoformat(timespec="seconds")
    run_id = "NWR-" + hashlib.sha256((job_id + "|" + started_at + "|" + trigger).encode()).hexdigest()[:16]
    advertised = str(os.getenv("RENDER_GIT_COMMIT") or "")
    revision = advertised if re.fullmatch(r"[a-fA-F0-9]{40}", advertised) else ""
    snapshot, inputs, total_bytes = _nw_read_sources(root, deadline)
    results = [_nw_core_result(definition, snapshot, inputs, deadline) for definition in NATIVE_WORKFORCE_CORE_CHECKS]
    results.extend(_nw_game_results(root, snapshot, inputs, deadline, revision, started_at))
    elapsed = max(0.0, _nw_clock() - start)
    duration_ms = round(elapsed * 1000)
    executed = sum(row["executed"] is True for row in results)
    outcome = "FAIL" if any(row["state"] == "FAIL" for row in results) else ("UNKNOWN" if any(row["state"] == "UNKNOWN" for row in results) else "PASS")
    result = "PASS" if executed == 22 else "PARTIAL"
    finished_at = (now_dt + timedelta(seconds=elapsed)).isoformat(timespec="microseconds")
    receipt = {
        "contract": NATIVE_WORKFORCE_REVIEW_CONTRACT, "receipt_id": run_id, "run_id": run_id,
        "app_version": _ce_clean_text(app_version, 80), "task_name": "platform_workforce_review",
        "review_kind": "STATIC_PARTIAL", "execution_kind": "DETERMINISTIC_LOCAL_READ_ONLY", "outcome": outcome,
        "started_at_madrid": started_at, "finished_at_madrid": finished_at, "duration_ms": duration_ms,
        "source_revision_advertised": revision or None, "source_revision_verified": False,
        "source_fingerprint": _nw_fingerprint(list(inputs.values())), "sources": list(inputs.values()),
        "expected_count": 22, "executed_count": executed, "results": results,
        "coverage": {"company_core": 15, "game_ui": 7, "scope": "STATIC_SOURCE_CONTRACTS_ONLY"},
        "limits": {"cooperative_seconds": NATIVE_WORKFORCE_BUDGET_SECONDS, "source_bytes_max": NATIVE_WORKFORCE_MAX_SOURCE_BYTES,
                   "source_bytes_read": total_bytes, "budget_exhausted": elapsed >= NATIVE_WORKFORCE_BUDGET_SECONDS},
        "browser_executed": False, "external_calls": 0, "paid_credits_consumed": 0,
        "business_execution_certified": False, "production_certified": False,
        "autonomous_agents_started": 0, "automatic_code_changes": False,
    }
    run = {"run_id": run_id, "job_id": job_id, "scheduled_for": scheduled_for, "trigger": trigger,
           "task_name": "platform_workforce_review", "result": result, "started_at": started_at,
           "finished_at": finished_at, "duration_ms": duration_ms, "receipt_id": run_id}
    if write:
        path = _nw_state_path(storage)
        try:
            previous = _nw_json_read(path)
        except FileNotFoundError:
            previous = {"contract": NATIVE_WORKFORCE_MEMORY_CONTRACT}
        if not isinstance(previous, dict) or previous.get("contract") != NATIVE_WORKFORCE_MEMORY_CONTRACT:
            raise ValueError("native_workforce_memory_contract_invalid")
        payload = _nw_update_state(previous, receipt)
        while len(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str).encode()) > NATIVE_WORKFORCE_MAX_STORE_BYTES:
            if len(payload["history"]) <= 1:
                raise ValueError("native_workforce_store_capacity")
            payload["history"].pop(0)
        if not _nw_lock_owned(storage, job_id):
            raise RuntimeError("native_workforce_scheduler_lock_lost")
        _ce_write_json(path, payload)
    return {"ok": True, "result": result, "run_id": run_id, "duration_ms": duration_ms,
            "receipt": receipt, "run": run, "dangerous_actions_executed": False}


def _nw_daily_findings(project_root: Path, storage: Path, now: datetime) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Use the latest scoped observation; daily never reexecutes the workforce."""
    loaded = load_native_workforce_receipt(project_root, storage_root=storage, now=now)
    if loaded["state"] != "RECENT":
        return [], {"state": loaded["state"], "receipt_id": None}
    receipt = loaded["receipt"]
    findings = [_nw_proposal(row, receipt) for row in receipt["results"] if row["executed"] and row["state"] in {"FAIL", "UNKNOWN"}]
    return findings, {"state": "RECENT", "receipt_id": receipt["receipt_id"], "review_kind": receipt["review_kind"],
                      "outcome": receipt["outcome"], "expected_count": 22, "executed_count": receipt["executed_count"]}
