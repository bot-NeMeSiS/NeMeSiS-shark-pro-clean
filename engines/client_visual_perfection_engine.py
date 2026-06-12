"""V740 client visual and pick-analysis QA snapshot.

Read-only checks for the final client polish layer. It verifies the presence of
membership visual skin, native app feel, crest fallbacks, Spanish labels and the
new pick explanation blocks without changing production data.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CRITICAL_TEMPLATES = [
    "templates/base.html",
    "templates/home.html",
    "templates/sports_hub.html",
    "templates/live.html",
    "templates/calendar.html",
    "templates/picks.html",
    "templates/combis.html",
    "templates/match_detail.html",
    "templates/match_hub.html",
    "templates/team_detail.html",
    "templates/track_record.html",
]


def _read(path: str) -> str:
    p = ROOT / path
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def _status(ok: bool) -> str:
    return "OK" if ok else "REVISAR"


def client_visual_perfection_snapshot(app_version: str = "") -> dict[str, Any]:
    css = _read("static/app.css")
    checks: list[dict[str, Any]] = []
    checks.append({"key": "v736_membership_skin", "label": "Skin visual por membresía", "status": _status("ns-tier-pro" in css and "ns-tier-elite" in css and "ns-tier-eliteplus" in css)})
    checks.append({"key": "v737_native_feel", "label": "Microinteracciones/app feel", "status": _status("nsAppEnhance" in _read("templates/base.html") and "ns-scroll-top" in css)})
    checks.append({"key": "v740_no_overlap_css", "label": "Protección visual anti-solape", "status": _status("V740 Client Visual" in css and "overflow-wrap:anywhere" in css)})
    checks.append({"key": "v740_pick_analysis", "label": "Análisis y conclusión en picks", "status": _status("v740-analysis-box" in _read("templates/picks.html") and "analysis_conclusion" in _read("templates/picks.html"))})
    checks.append({"key": "crest_fallbacks", "label": "Escudos con fallback propio", "status": _status("/team-crest.svg" in _read("app.py") and "compact-crest" in css)})
    checks.append({"key": "spanish_filters", "label": "Filtros castellano en ligas/mercados", "status": _status("competition_es" in _read("templates/picks.html") and "market_es" in _read("templates/picks.html"))})

    template_results = []
    for template in CRITICAL_TEMPLATES:
        text = _read(template)
        template_results.append({
            "template": template,
            "exists": bool(text),
            "has_crest": "crest" in text or template in {"templates/base.html"},
            "has_spanish_competition": "competition_es" in text or "safe_competition" in text or template in {"templates/base.html", "templates/track_record.html"},
            "raw_risk": any(token in text for token in ["undefined", "null", "None"]),
        })

    score = 100
    score -= 8 * sum(1 for c in checks if c["status"] != "OK")
    score -= 3 * sum(1 for t in template_results if not t["exists"])
    score -= 2 * sum(1 for t in template_results if t["raw_risk"])
    score = max(0, min(100, score))

    return {
        "version": app_version,
        "score": score,
        "status": "CLIENT_VISUAL_READY" if score >= 90 else "CLIENT_VISUAL_REVIEW",
        "checks": checks,
        "templates": template_results,
        "summary": "Revisión visual cliente: escudos, castellano, anti-solape, membresía y explicación avanzada de picks.",
        "next_steps": [
            "Validar en móvil real y PWA instalada.",
            "Comprobar que Render tiene datos reales para que los escudos y partidos se vean con contenido real.",
            "Revisar manualmente picks publicados para confirmar que el análisis no promete ganancias.",
        ],
    }
