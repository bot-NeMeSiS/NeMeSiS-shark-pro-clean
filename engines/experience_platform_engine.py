"""Evidence-based product experience audit for NeMeSiS.

This module is intentionally read-only. It scans local templates, routes and CSS
contracts to organize UX evidence for Product Polish, Sentinel and AutoPilot.
It does not create product data, call providers, write databases, send Telegram,
charge Stripe, deploy, push, or modify UI automatically.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


MADRID = ZoneInfo("Europe/Madrid")

EXPERIENCE_PLATFORM_CONTRACT = "NEMESIS-EXPERIENCE-PLATFORM-V1"
EXPERIENCE_AUDITOR_CONTRACT = "NEMESIS-EXPERIENCE-AUDITOR-V1"
PRODUCT_POLISH_CONTRACT = "NEMESIS-PRODUCT-POLISH-ENGINE-V1"
UX_CONSISTENCY_CONTRACT = "NEMESIS-UX-CONSISTENCY-CHECKER-V1"
NAVIGATION_INTEGRITY_CONTRACT = "NEMESIS-NAVIGATION-INTEGRITY-CHECKER-V1"
VISUAL_DENSITY_CONTRACT = "NEMESIS-VISUAL-DENSITY-AUDITOR-V1"

TECHNICAL_TEXT_RE = re.compile(
    r"\b(?:None|null|undefined|Traceback|werkzeug|sqlite3|debug|TODO|FIXME|Lorem ipsum)\b",
    re.I,
)
MOJIBAKE_RE = re.compile(r"(?:Ã.|Â.|â€|ï¿½)")
ROUTE_RE = re.compile(r"@(?:app|[A-Za-z_][A-Za-z0-9_]*)\.route\(\s*['\"]([^'\"]+)")
HREF_RE = re.compile(r"\bhref\s*=\s*['\"]([^'\"]*)['\"]", re.I)
BUTTON_RE = re.compile(r"<button\b([^>]*)>", re.I)
CLASS_RE = re.compile(r"\bclass\s*=\s*['\"]([^'\"]+)['\"]", re.I)
TAG_RE = re.compile(r"<[^>]+>")
JINJA_RE = re.compile(r"(?:\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\})", re.S)

EXCLUDED_TEMPLATE_PARTS = {"components", "macros", "partials"}
BLOCKED_GUARDRAILS = {
    "external_calls": 0,
    "database_writes": 0,
    "telegram_sends": 0,
    "stripe_calls": 0,
    "generative_ai_calls": 0,
    "automatic_ui_changes": 0,
    "sports_core_changes": 0,
    "shark_logic_changes": 0,
    "new_api_routes": 0,
}


def _root(project_root: str | Path | None = None) -> Path:
    return Path(project_root).resolve() if project_root else Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_template_files(root: Path) -> Iterable[Path]:
    template_root = root / "templates"
    if not template_root.exists():
        return []
    return sorted(path for path in template_root.rglob("*.html") if path.is_file())


def _iter_css_files(root: Path) -> Iterable[Path]:
    static_root = root / "static"
    if not static_root.exists():
        return []
    return sorted(path for path in static_root.rglob("*.css") if path.is_file())


def _visible_words(html: str) -> list[str]:
    cleaned = JINJA_RE.sub(" ", html)
    cleaned = TAG_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return [word for word in cleaned.split(" ") if word]


def _audience(relative: str, html: str) -> str:
    lower = f"{relative}\n{html[:3000]}".lower()
    if "/admin" in lower or "admin_" in lower or "data-v933-shell='admin'" in lower or 'data-v933-shell="admin"' in lower:
        return "admin"
    if "client" in lower or "bottom-nav" in lower or "ns-client" in lower:
        return "client"
    if any(part in relative.split("/") for part in EXCLUDED_TEMPLATE_PARTS):
        return "component"
    return "public"


def _screen_kind(relative: str) -> str:
    parts = set(relative.split("/"))
    if parts & EXCLUDED_TEMPLATE_PARTS:
        return "component"
    return "screen"


def _issue(
    code: str,
    title: str,
    severity: str,
    category: str,
    screen: str,
    evidence: str,
    recommendation: str,
    *,
    check: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "title": title,
        "severity": severity,
        "category": category,
        "screen": screen,
        "evidence": _text(evidence, 500),
        "recommendation": _text(recommendation, 500),
        "check": check,
        "requires_human_approval": True,
        "autofix_allowed": False,
    }


def collect_screen_inventory(project_root: str | Path | None = None) -> dict[str, Any]:
    root = _root(project_root)
    screens: list[dict[str, Any]] = []
    totals = Counter()
    for path in _iter_template_files(root):
        relative = _relative(path, root)
        html = _read(path)
        words = _visible_words(html)
        buttons = len(BUTTON_RE.findall(html))
        hrefs = HREF_RE.findall(html)
        classes = CLASS_RE.findall(html)
        class_tokens = [token for group in classes for token in group.split()]
        card_count = sum(1 for token in class_tokens if "card" in token.lower())
        chip_count = sum(1 for token in class_tokens if "chip" in token.lower() or "badge" in token.lower())
        section_count = len(re.findall(r"<section\b|data-.*?section|class=['\"][^'\"]*section", html, re.I))
        table_count = len(re.findall(r"<table\b", html, re.I))
        image_count = len(re.findall(r"<img\b", html, re.I))
        audience = _audience(relative, html)
        kind = _screen_kind(relative)
        totals[f"{kind}s"] += 1
        totals[audience] += 1
        screens.append(
            {
                "path": relative,
                "kind": kind,
                "audience": audience,
                "word_count": len(words),
                "buttons": buttons,
                "links": len(hrefs),
                "cards": card_count,
                "chips_badges": chip_count,
                "sections": section_count,
                "tables": table_count,
                "images": image_count,
                "extends_base": "extends" in html and "base" in html,
                "uses_ns_system": "ns-" in html or "v933" in html,
            }
        )
    return {
        "contract": EXPERIENCE_AUDITOR_CONTRACT,
        "screens": screens,
        "totals": dict(totals),
        "screen_count": len([item for item in screens if item["kind"] == "screen"]),
        "component_count": len([item for item in screens if item["kind"] == "component"]),
    }


def _route_set(root: Path) -> set[str]:
    routes: set[str] = set()
    files = [root / "app.py"]
    blueprint_root = root / "blueprints"
    if blueprint_root.exists():
        files.extend(sorted(blueprint_root.glob("*.py")))
    for path in files:
        routes.update(ROUTE_RE.findall(_read(path)))
    return routes


def _literal_internal_href(href: str) -> str | None:
    value = href.strip()
    if not value or value == "#" or value.lower().startswith("javascript:"):
        return value
    if "{{" in value or "{%" in value or "<" in value:
        return None
    if value.startswith(("mailto:", "tel:", "http://", "https://", "#")):
        return None
    if not value.startswith("/"):
        return None
    return value.split("?", 1)[0].rstrip("/") or "/"


def run_navigation_integrity_checker(project_root: str | Path | None = None) -> dict[str, Any]:
    root = _root(project_root)
    routes = _route_set(root)
    normalized_routes = {route.rstrip("/") or "/" for route in routes}
    findings: list[dict[str, Any]] = []
    href_count = 0
    for path in _iter_template_files(root):
        relative = _relative(path, root)
        html = _read(path)
        for href in HREF_RE.findall(html):
            href_count += 1
            literal = _literal_internal_href(href)
            if literal is None:
                continue
            if literal in {"", "#"} or literal.lower().startswith("javascript:"):
                findings.append(
                    _issue(
                        "NAV_EMPTY_OR_SCRIPT_HREF",
                        "Accion visible sin destino real",
                        "P2",
                        "navigation",
                        relative,
                        f"href={href!r}",
                        "Sustituir por accion real, estado deshabilitado honesto o eliminar la accion redundante.",
                        check="navigation_integrity",
                    )
                )
                continue
            if literal.startswith("/static/") or literal.startswith("/api/"):
                continue
            if literal not in normalized_routes and not any(
                route.endswith(">") and literal.startswith(route.split("<", 1)[0].rstrip("/"))
                for route in normalized_routes
            ):
                findings.append(
                    _issue(
                        "NAV_LITERAL_ROUTE_NOT_REGISTERED",
                        "Ruta literal no registrada",
                        "P3",
                        "navigation",
                        relative,
                        f"href={href!r}",
                        "Validar si la ruta es legacy, alias pendiente o enlace que debe usar endpoint canonico.",
                        check="navigation_integrity",
                    )
                )
    return {
        "contract": NAVIGATION_INTEGRITY_CONTRACT,
        "routes_detected": len(routes),
        "hrefs_scanned": href_count,
        "findings": findings,
        "status": "PASS" if not [f for f in findings if f["severity"] in {"P0", "P1"}] else "REQUIRES_REVIEW",
    }


def run_ux_consistency_checker(project_root: str | Path | None = None) -> dict[str, Any]:
    root = _root(project_root)
    findings: list[dict[str, Any]] = []
    button_count = 0
    for path in _iter_template_files(root):
        relative = _relative(path, root)
        html = _read(path)
        visible = " ".join(_visible_words(html))
        if TECHNICAL_TEXT_RE.search(visible):
            findings.append(
                _issue(
                    "UX_TECHNICAL_TEXT_VISIBLE",
                    "Texto tecnico puede quedar visible",
                    "P2",
                    "copy",
                    relative,
                    TECHNICAL_TEXT_RE.search(visible).group(0),
                    "Mover detalles tecnicos a admin o convertirlos en estado de usuario claro.",
                    check="ux_consistency",
                )
            )
        if MOJIBAKE_RE.search(visible):
            findings.append(
                _issue(
                    "UX_MOJIBAKE_RISK",
                    "Riesgo de mojibake visible",
                    "P2",
                    "copy",
                    relative,
                    MOJIBAKE_RE.search(visible).group(0),
                    "Normalizar encoding y copiar texto desde fuente UTF-8 limpia.",
                    check="ux_consistency",
                )
            )
        for attrs in BUTTON_RE.findall(html):
            button_count += 1
            attrs_lower = attrs.lower()
            if "type=" not in attrs_lower and "aria-label" not in attrs_lower and "class=" not in attrs_lower:
                findings.append(
                    _issue(
                        "UX_UNDESCRIBED_BUTTON",
                        "Boton sin tipo, clase ni etiqueta accesible",
                        "P3",
                        "component",
                        relative,
                        attrs.strip() or "<button>",
                        "Usar componente de boton existente o declarar tipo/aria-label segun la accion.",
                        check="ux_consistency",
                    )
                )
        class_groups = CLASS_RE.findall(html)
        naked_action_count = len(re.findall(r"<a\b(?![^>]*class=)[^>]*>", html, re.I))
        if naked_action_count > 8 and _screen_kind(relative) == "screen":
            findings.append(
                _issue(
                    "UX_MANY_UNSTYLED_LINKS",
                    "Demasiados enlaces sin sistema visual compartido",
                    "P3",
                    "component",
                    relative,
                    f"unstyled_links={naked_action_count}",
                    "Revisar si deben usar el sistema ns-/v933 o quedar como texto secundario.",
                    check="ux_consistency",
                )
            )
        if class_groups and not ("ns-" in html or "v933" in html) and _screen_kind(relative) == "screen":
            findings.append(
                _issue(
                    "UX_SCREEN_OUTSIDE_VISUAL_SYSTEM",
                    "Pantalla fuera del sistema visual actual",
                    "P3",
                    "visual_system",
                    relative,
                    "No se detectan clases ns- ni v933.",
                    "Verificar si es legacy o si debe migrar al sistema visual vigente.",
                    check="ux_consistency",
                )
            )
    return {
        "contract": UX_CONSISTENCY_CONTRACT,
        "templates_scanned": len(list(_iter_template_files(root))),
        "buttons_scanned": button_count,
        "findings": findings,
        "status": "PASS" if not [f for f in findings if f["severity"] in {"P0", "P1"}] else "REQUIRES_REVIEW",
    }


def run_visual_density_auditor(project_root: str | Path | None = None) -> dict[str, Any]:
    root = _root(project_root)
    findings: list[dict[str, Any]] = []
    css_findings: list[dict[str, Any]] = []
    for path in _iter_template_files(root):
        relative = _relative(path, root)
        html = _read(path)
        if _screen_kind(relative) != "screen":
            continue
        words = _visible_words(html)
        classes = [token for group in CLASS_RE.findall(html) for token in group.split()]
        card_count = sum(1 for token in classes if "card" in token.lower())
        section_count = len(re.findall(r"<section\b|data-.*?section", html, re.I))
        if card_count >= 12 and len(words) / max(card_count, 1) < 18:
            findings.append(
                _issue(
                    "DENSITY_CARD_HEAVY_LOW_TEXT",
                    "Muchas cards con baja densidad informativa",
                    "P3",
                    "density",
                    relative,
                    f"cards={card_count}, words_per_card={len(words) / max(card_count, 1):.1f}",
                    "Agrupar informacion repetitiva, reducir tarjetas decorativas o consolidar estados equivalentes.",
                    check="visual_density",
                )
            )
        if section_count >= 10 and len(words) < 600:
            findings.append(
                _issue(
                    "DENSITY_MANY_SECTIONS_LOW_CONTENT",
                    "Pantalla fragmentada en demasiados bloques",
                    "P3",
                    "density",
                    relative,
                    f"sections={section_count}, words={len(words)}",
                    "Revisar jerarquia: menos bloques, mas continuidad y acciones primarias mas claras.",
                    check="visual_density",
                )
            )
    for path in _iter_css_files(root):
        relative = _relative(path, root)
        css = _read(path)
        for match in re.finditer(r"(?:min-height|height)\s*:\s*(?:100vh|[7-9]\dvh|[8-9]\d{2,}px|\d{4,}px)", css, re.I):
            css_findings.append(
                _issue(
                    "DENSITY_LARGE_FIXED_HEIGHT",
                    "Altura fija grande puede crear espacio vacio o scroll excesivo",
                    "P3",
                    "density",
                    relative,
                    match.group(0),
                    "Validar en Browser QA antes de tocar CSS; preferir contenido fluido si se confirma el defecto.",
                    check="visual_density",
                )
            )
        for match in re.finditer(r"(?:padding|gap|margin)\s*:\s*(?:[7-9]\d|\d{3,})px", css, re.I):
            css_findings.append(
                _issue(
                    "DENSITY_LARGE_SPACING_TOKEN",
                    "Espaciado grande requiere validacion visual",
                    "P3",
                    "density",
                    relative,
                    match.group(0),
                    "No corregir sin evidencia visual; registrar como candidato de polish.",
                    check="visual_density",
                )
            )
    return {
        "contract": VISUAL_DENSITY_CONTRACT,
        "screens_scanned": len([p for p in _iter_template_files(root) if _screen_kind(_relative(p, root)) == "screen"]),
        "css_files_scanned": len(list(_iter_css_files(root))),
        "findings": findings + css_findings[:60],
        "css_findings_capped": max(0, len(css_findings) - 60),
        "status": "PASS_WITH_REVIEW_ITEMS" if findings or css_findings else "PASS",
    }


def build_product_polish_portfolio(audit: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for section in ("navigation", "ux_consistency", "visual_density"):
        findings.extend(audit.get(section, {}).get("findings") or [])
    severity_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    sorted_findings = sorted(findings, key=lambda item: (severity_order.get(item.get("severity", "P4"), 4), item.get("screen", ""), item.get("code", "")))
    grouped = defaultdict(list)
    for item in sorted_findings:
        grouped[item["severity"]].append(item)
    next_actions = []
    for severity in ("P0", "P1", "P2", "P3"):
        for item in grouped.get(severity, [])[:5]:
            next_actions.append(
                {
                    "priority": severity,
                    "screen": item["screen"],
                    "issue": item["title"],
                    "action": item["recommendation"],
                    "approval_required": True,
                    "browser_qa_required": True,
                }
            )
    return {
        "contract": PRODUCT_POLISH_CONTRACT,
        "total_findings": len(sorted_findings),
        "by_severity": {key: len(value) for key, value in grouped.items()},
        "top_findings": sorted_findings[:20],
        "next_actions": next_actions[:12],
        "autofix_allowed": False,
        "status": "PASS" if not grouped.get("P0") and not grouped.get("P1") else "REQUIRES_REVIEW",
    }


def build_experience_audit(project_root: str | Path | None = None) -> dict[str, Any]:
    root = _root(project_root)
    inventory = collect_screen_inventory(root)
    navigation = run_navigation_integrity_checker(root)
    ux = run_ux_consistency_checker(root)
    density = run_visual_density_auditor(root)
    audit = {
        "contract": EXPERIENCE_AUDITOR_CONTRACT,
        "generated_at_madrid": datetime.now(MADRID).isoformat(timespec="seconds"),
        "screen_inventory": inventory,
        "navigation": navigation,
        "ux_consistency": ux,
        "visual_density": density,
    }
    audit["product_polish"] = build_product_polish_portfolio(audit)
    return audit


def build_experience_platform_snapshot(project_root: str | Path | None = None) -> dict[str, Any]:
    root = _root(project_root)
    audit = build_experience_audit(root)
    polish = audit["product_polish"]
    status = "PASS" if polish["status"] == "PASS" else "PASS_WITH_REVIEW_ITEMS"
    return {
        "contract": EXPERIENCE_PLATFORM_CONTRACT,
        "generated_at_madrid": audit["generated_at_madrid"],
        "environment": "local_filesystem_read_only",
        "auditors": {
            "experience_auditor": EXPERIENCE_AUDITOR_CONTRACT,
            "product_polish_engine": PRODUCT_POLISH_CONTRACT,
            "ux_consistency_checker": UX_CONSISTENCY_CONTRACT,
            "navigation_integrity_checker": NAVIGATION_INTEGRITY_CONTRACT,
            "visual_density_auditor": VISUAL_DENSITY_CONTRACT,
        },
        "status": status,
        "screen_count": audit["screen_inventory"]["screen_count"],
        "component_count": audit["screen_inventory"]["component_count"],
        "routes_detected": audit["navigation"]["routes_detected"],
        "findings": {
            "total": polish["total_findings"],
            "by_severity": polish["by_severity"],
            "top": polish["top_findings"],
        },
        "next_actions": polish["next_actions"],
        "audit": audit,
        "guardrails": dict(BLOCKED_GUARDRAILS),
        "browser_qa_required_before_ui_changes": True,
        "sentinel_required": True,
        "autopilot_autofix_allowed": False,
        "production_modified": False,
    }


def experience_platform_snapshot(project_root: str | Path | None = None) -> dict[str, Any]:
    return build_experience_platform_snapshot(project_root)