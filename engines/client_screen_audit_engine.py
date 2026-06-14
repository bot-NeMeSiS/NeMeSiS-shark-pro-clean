"""V791 client screen audit and professional polish guardrails.

Read-only helper: scans routes/templates/CSS for client-facing quality without
requiring Flask imports, external APIs, secrets or database mutations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

CLIENT_ROUTES = [
    "/", "/app", "/calendar", "/live", "/picks", "/combis", "/mercados",
    "/match/<match_id>", "/highlights", "/track-record", "/shark", "/telegram",
    "/mi-cuenta", "/membresias", "/menu", "/legal", "/terminos", "/privacidad",
    "/juego-responsable", "/no-somos-casa-de-apuestas",
]

CLIENT_TEMPLATES = [
    "base.html", "home.html", "client_app_center.html", "client_menu.html",
    "calendar.html", "live.html", "picks.html", "combis.html", "betting_markets.html",
    "match_detail.html", "highlights.html", "track_record.html", "shark.html",
    "telegram.html", "account_center.html", "membership.html", "legal_compliance.html",
    "legal_basic.html", "legal_trust.html", "responsible_betting.html",
]

REQUIRED_CSS_TOKENS = [
    "V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH",
    "v774-match-card", "v774-pick-card", "v785-price-card", "v787-checkout-legal",
    "bottom-nav-clean", "nav-clean", "v790-shell",
]

UNSAFE_CLIENT_PHRASES = [
    "ganancia segura", "dinero garantizado", "beneficio garantizado", "apuesta segura",
    "sin riesgo", "te hacemos ganar", "cuota segura", "combi segura",
]
TECHNICAL_CLIENT_MARKERS = ["Traceback", "UndefinedError", "sqlite3.", "NoneType", "UTC crudo", "json visible", "debug panel"]
MOJIBAKE_MARKERS = ["�", "Ã", "Â", "â€™", "â€œ", "â€", "producci?n"]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _route_exists(route: str, registered: set[str]) -> bool:
    if route in registered:
        return True
    # Dynamic route aliases: compare fixed prefix and segment count.
    route_parts = [p for p in route.strip("/").split("/") if p]
    for candidate in registered:
        cand_parts = [p for p in candidate.strip("/").split("/") if p]
        if len(route_parts) != len(cand_parts):
            continue
        ok = True
        for expected, actual in zip(route_parts, cand_parts):
            if expected.startswith("<") and expected.endswith(">"):
                continue
            if actual.startswith("<") and actual.endswith(">"):
                continue
            if expected != actual:
                ok = False
                break
        if ok:
            return True
    return False


def _template_report(template_root: Path) -> list[dict]:
    reports: list[dict] = []
    for name in CLIENT_TEMPLATES:
        path = template_root / name
        raw = _read(path)
        lower = raw.lower()
        unsafe = [phrase for phrase in UNSAFE_CLIENT_PHRASES if phrase in lower]
        tech = [marker for marker in TECHNICAL_CLIENT_MARKERS if marker.lower() in lower]
        mojibake = [marker for marker in MOJIBAKE_MARKERS if marker in raw]
        has_legal = name.startswith("legal") or name in {"base.html", "membership.html", "responsible_betting.html"} or any(
            token in raw for token in ["+18", "juego responsable", "no es casa de apuestas", "no acepta apuestas"]
        )
        uses_madrid = any(token in raw for token in [
            "match_madrid_context", "match_full_datetime", "madrid_datetime_label",
            "client_full_datetime_label", "client_time_label", "Hora Madrid", "Europe/Madrid"
        ]) or name in {"base.html", "client_menu.html", "legal_basic.html", "legal_trust.html", "legal_compliance.html"}
        reports.append({
            "template": name,
            "exists": bool(raw),
            "professional_layer": any(token in raw for token in ["v774", "v778", "v783", "v785", "v787", "v790"]),
            "uses_madrid_time": uses_madrid,
            "legal_context": has_legal,
            "unsafe_phrases": unsafe,
            "technical_markers": tech,
            "mojibake_markers": mojibake,
            "status": "OK" if raw and not unsafe and not tech and not mojibake else "REVIEW",
        })
    return reports


def _css_report(static_css_path: Path) -> dict:
    css = _read(static_css_path)
    tokens = [{"token": token, "ok": token in css} for token in REQUIRED_CSS_TOKENS]
    return {
        "exists": bool(css),
        "size_bytes": len(css.encode("utf-8")),
        "required_tokens": tokens,
        "responsive": "@media" in css,
        "readability_rules": all(token in css for token in ["line-height", "font-size", "gap", "border-radius"]),
        "mobile_rules": "max-width:760px" in css or "max-width: 760px" in css,
    }


def client_screen_audit_snapshot(app_version: str, registered_routes: Iterable[str], template_root: str, static_css_path: str) -> dict:
    registered = set(registered_routes or [])
    routes = [{"route": route, "ok": _route_exists(route, registered)} for route in CLIENT_ROUTES]
    templates = _template_report(Path(template_root))
    css = _css_report(Path(static_css_path))
    route_score = int(100 * sum(1 for r in routes if r["ok"]) / max(1, len(routes)))
    template_ok = sum(1 for t in templates if t["exists"] and t["status"] == "OK")
    template_score = int(100 * template_ok / max(1, len(templates)))
    css_score = int(100 * sum(1 for t in css["required_tokens"] if t["ok"]) / max(1, len(css["required_tokens"]))) if css["exists"] else 0
    score = round(route_score * 0.35 + template_score * 0.45 + css_score * 0.20)
    critical = []
    if route_score < 100:
        critical.append("Hay rutas cliente críticas sin registrar.")
    unsafe_count = sum(len(t["unsafe_phrases"]) for t in templates)
    if unsafe_count:
        critical.append(f"Hay {unsafe_count} frases comerciales que conviene evitar en cliente.")
    if not css.get("responsive"):
        critical.append("CSS sin reglas responsive suficientes.")
    status = "READY" if score >= 92 and not critical else ("REVIEW" if score >= 80 else "FIX_REQUIRED")
    return {
        "version": app_version,
        "score": score,
        "status": status,
        "routes": routes,
        "templates": templates,
        "css": css,
        "critical": critical,
        "summary": {
            "routes_ok": sum(1 for r in routes if r["ok"]),
            "routes_total": len(routes),
            "templates_ok": template_ok,
            "templates_total": len(templates),
            "css_tokens_ok": sum(1 for t in css["required_tokens"] if t["ok"]),
            "css_tokens_total": len(css["required_tokens"]),
        },
        "guardrails": [
            "Cliente profesional primero: inicio, directo, calendario, picks, partido, cuenta, Telegram y membresías.",
            "Lenguaje legalmente prudente: análisis informativo, no casa de apuestas, sin garantías.",
            "Nada de secretos, datos inventados, ROI inventado, partidos falsos ni promesas de beneficio.",
            "Mantener Stripe, Telegram, Cron, DB_PATH, Madrid Time y datos reales intactos.",
        ],
    }
