"""Client experience guard for NeMeSiS SHARK PRO.

This module produces a read-only QA snapshot focused on what the client sees:
raw UTC/time fields, technical text, empty-state safety, and mobile-critical
screens. It is intentionally conservative: it reports warnings, it does not
change runtime data and it does not require Flask or a live database.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable

CLIENT_TEMPLATE_NAMES = {
    "home.html",
    "client_overview.html",
    "dashboard.html",
    "sports_hub.html",
    "live.html",
    "calendar.html",
    "picks.html",
    "combis.html",
    "shark.html",
    "telegram.html",
    "favorites.html",
    "perfil.html",
    "membership.html",
    "match_detail.html",
    "match_hub.html",
    "team_detail.html",
    "daily_briefing.html",
    "recommendations.html",
    "account_center.html",
}

CRITICAL_SCREENS = [
    {"route": "/", "template": "home.html", "label": "Home pública", "priority": "alta"},
    {"route": "/dashboard", "template": "client_overview.html", "label": "Dashboard cliente", "priority": "alta"},
    {"route": "/sports-hub", "template": "sports_hub.html", "label": "Sports Hub / Partidos", "priority": "alta"},
    {"route": "/live", "template": "live.html", "label": "Directo", "priority": "alta"},
    {"route": "/calendar", "template": "calendar.html", "label": "Calendario", "priority": "alta"},
    {"route": "/picks", "template": "picks.html", "label": "Picks", "priority": "alta"},
    {"route": "/combis", "template": "combis.html", "label": "Combis", "priority": "alta"},
    {"route": "/shark", "template": "shark.html", "label": "SHARK", "priority": "media", "needs_time_filter": False},
    {"route": "/telegram", "template": "telegram.html", "label": "Telegram cliente", "priority": "alta", "needs_time_filter": False},
    {"route": "/favorites", "template": "favorites.html", "label": "Favoritos", "priority": "media"},
    {"route": "/perfil", "template": "profile.html", "label": "Perfil", "priority": "media", "needs_time_filter": False},
    {"route": "/membership", "template": "membership.html", "label": "Membresías", "priority": "media", "needs_time_filter": False},
    {"route": "/match/<id>", "template": "match_detail.html", "label": "Detalle partido", "priority": "alta"},
]

# Direct references to these fields in client templates are risky because they
# often bypass madrid_time_engine and may show UTC. Allowlist filters are checked
# at template level in the scanner.
RAW_TIME_PATTERNS = (
    "kickoff_time",
    "kickoff_iso",
    "commence_time",
    "match_time",
    "event_time",
    "start_time",
)
SAFE_TIME_FILTERS = (
    "match_time_short",
    "match_time_label",
    "match_date_label",
    "madrid_time",
    "safe_time",
)
TECHNICAL_CLIENT_PATTERNS = (
    "runtime-version",
    "debug",
    "traceback",
    "stack trace",
    "scheduler",
    "automation_secret",
    "db_path",
    "raw json",
    "undefined",
    "null",
    "None",
    "+00:00",
    "Z</",
    " UTC",
)
SPANISH_COPY_HINTS = (
    ("Live", "Usar Directo cuando sea texto visible al cliente."),
    ("Moneyline", "Usar Ganador del partido."),
    ("Over", "Usar Más de."),
    ("Under", "Usar Menos de."),
    ("Draw", "Usar Empate."),
)


def _project_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root).resolve()
    return Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def _line_no(text: str, pattern: str) -> int:
    idx = text.find(pattern)
    if idx < 0:
        return 0
    return text[:idx].count("\n") + 1


def _client_templates(root: Path) -> list[Path]:
    templates = root / "templates"
    return sorted(p for p in templates.glob("*.html") if p.name in CLIENT_TEMPLATE_NAMES)


def _screen_status(root: Path) -> list[dict]:
    result = []
    for screen in CRITICAL_SCREENS:
        path = root / "templates" / screen["template"]
        exists = path.exists()
        text = _read(path) if exists else ""
        needs_time_filter = screen.get("needs_time_filter", screen.get("priority") == "alta")
        uses_madrid_filters = any(token in text for token in SAFE_TIME_FILTERS)
        time_status_ok = (not needs_time_filter) or uses_madrid_filters
        has_empty_state = any(token in text.lower() for token in ("empty", "no hay", "sin ", "aún no", "preparación"))
        result.append({
            **screen,
            "exists": exists,
            "needs_time_filter": needs_time_filter,
            "uses_madrid_filters": uses_madrid_filters,
            "time_status_ok": time_status_ok,
            "has_empty_state_hint": has_empty_state,
            "size_bytes": path.stat().st_size if exists else 0,
            "status": "OK" if exists else "FALTA",
        })
    return result


def _scan_patterns(paths: Iterable[Path]) -> tuple[list[dict], Counter]:
    findings: list[dict] = []
    counts: Counter = Counter()
    for path in paths:
        text = _read(path)
        lower = text.lower()
        # Raw time fields are only a warning if there is no obvious safe filter in
        # the same template. This avoids punishing controlled fallback logic.
        has_safe_filter = any(token in text for token in SAFE_TIME_FILTERS)
        for pattern in RAW_TIME_PATTERNS:
            if pattern in text and not has_safe_filter:
                findings.append({
                    "severity": "WARN",
                    "category": "hora_madrid",
                    "template": path.name,
                    "pattern": pattern,
                    "line": _line_no(text, pattern),
                    "message": "Posible uso de hora cruda sin filtro Madrid.",
                })
                counts["raw_time"] += 1
        for pattern in TECHNICAL_CLIENT_PATTERNS:
            lookup = pattern.lower()
            if lookup in lower:
                findings.append({
                    "severity": "INFO" if pattern in {"None", "null", "undefined"} else "WARN",
                    "category": "texto_tecnico",
                    "template": path.name,
                    "pattern": pattern,
                    "line": _line_no(lower, lookup),
                    "message": "Revisar que este texto no sea visible al cliente final.",
                })
                counts["technical_text"] += 1
        for english, advice in SPANISH_COPY_HINTS:
            if english in text:
                findings.append({
                    "severity": "INFO",
                    "category": "microcopy",
                    "template": path.name,
                    "pattern": english,
                    "line": _line_no(text, english),
                    "message": advice,
                })
                counts["microcopy"] += 1
    return findings, counts


def _css_snapshot(root: Path) -> dict:
    css = root / "static" / "app.css"
    text = _read(css)
    checks = {
        "bottom_nav": ".bottom-nav-clean" in text,
        "shark_widget": ".shark-widget" in text,
        "mobile_media": "@media(max-width" in text or "@media (max-width" in text,
        "live_rows": ".sports-row" in text,
        "v728_layer": "V728 Final Client Experience" in text,
        "v731_layer": "V731" in text,
    }
    return {
        "exists": css.exists(),
        "size_bytes": css.stat().st_size if css.exists() else 0,
        "checks": checks,
        "score": sum(1 for ok in checks.values() if ok),
        "max_score": len(checks),
    }


def client_experience_snapshot(root: str | Path | None = None) -> dict:
    project = _project_root(root)
    templates = _client_templates(project)
    findings, counts = _scan_patterns(templates)
    screens = _screen_status(project)
    css = _css_snapshot(project)
    missing = [item for item in screens if not item["exists"]]
    no_madrid = [item for item in screens if item["exists"] and item.get("needs_time_filter") and not item["uses_madrid_filters"]]
    high_warnings = [item for item in findings if item["severity"] == "WARN"]
    score = 100
    score -= min(35, len(missing) * 7)
    score -= min(25, len(no_madrid) * 4)
    score -= min(30, len(high_warnings) * 3)
    score -= max(0, css["max_score"] - css["score"]) * 2
    score = max(0, min(100, score))
    recommended_next_steps = []
    if missing:
        recommended_next_steps.append("Crear o restaurar templates cliente críticos faltantes.")
    if no_madrid:
        recommended_next_steps.append("Forzar filtros match_time_label/match_time_short en pantallas con partidos.")
    if high_warnings:
        recommended_next_steps.append("Revisar textos técnicos o campos horarios crudos antes de publicar.")
    if not recommended_next_steps:
        recommended_next_steps.append("Mantener QA visual con capturas reales de móvil/desktop tras desplegar.")
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project),
        "templates_scanned": len(templates),
        "critical_screens": screens,
        "findings": findings[:200],
        "findings_count": len(findings),
        "warning_count": len(high_warnings),
        "counts": dict(counts),
        "css": css,
        "score": score,
        "status": "OK" if score >= 85 and not missing and not no_madrid else "REVISAR",
        "recommended_next_steps": recommended_next_steps,
    }


__all__ = ["client_experience_snapshot"]
