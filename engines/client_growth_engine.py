"""V757 global client app experience, trust and navigation helpers.

Pure defensive builders. They only reshape existing data for templates and APIs;
they do not touch Telegram, Cron, DB_PATH, memberships or external services.
"""
from __future__ import annotations

from typing import Any


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _txt(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _num(value: Any, fallback: int = 0) -> int:
    try:
        return int(float(str(value or "0").replace(",", ".")))
    except Exception:
        return fallback


def _pct(value: Any) -> str:
    if value in (None, "", "—"):
        return "Pendiente"
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return _txt(value, "Pendiente")


def _pick_name(pick: dict[str, Any]) -> str:
    home = _txt(pick.get("home_team") or pick.get("safe_home"), "Local")
    away = _txt(pick.get("away_team") or pick.get("safe_away"), "Visitante")
    selection = _txt(pick.get("selection_display") or pick.get("selection") or pick.get("recommended_pick") or pick.get("market"), "Pick en estudio")
    return f"{selection} · {home} vs {away}"


def _match_name(match: dict[str, Any]) -> str:
    home = _txt(match.get("safe_home") or match.get("home_team"), "Local")
    away = _txt(match.get("safe_away") or match.get("away_team"), "Visitante")
    return f"{home} vs {away}"


def _score_from_data(data: dict[str, Any], track_record: dict[str, Any] | None = None) -> int:
    track_record = _dict(track_record)
    hub = _dict(data.get("match_hub"))
    counts = _dict(hub.get("counts"))
    picks = _list(data.get("picks"))
    live_count = _num(counts.get("live"), 0)
    today_count = _num(counts.get("today") or counts.get("upcoming"), 0)
    decided = _num(track_record.get("decided_total"), 0)
    score = 68
    score += min(10, today_count // 2)
    score += min(8, live_count * 2)
    score += min(10, len(picks) * 2)
    score += 6 if decided else 0
    return max(50, min(98, score))


def build_v757_trust_snapshot(track_record: dict[str, Any] | None) -> dict[str, Any]:
    track = _dict(track_record)
    decided = _num(track.get("decided_total") or (track.get("won", 0) + track.get("lost", 0)), 0)
    pending = _num(track.get("pending") or track.get("pending_review"), 0)
    return {
        "title": "Transparencia SHARK",
        "decided": decided,
        "pending": pending,
        "roi": _pct(track.get("roi")),
        "winrate": _pct(track.get("winrate")),
        "profit": track.get("profit") if track.get("profit") not in (None, "") else "Pendiente",
        "note": _txt(track.get("commercial_note"), "Pendiente de resultados reales. No se inventa rendimiento."),
        "status": "Con resultados reales" if decided else "Pendiente de resultados reales",
        "cards": [
            {"label": "Picks evaluados", "value": decided, "hint": "solo reales"},
            {"label": "Pendientes", "value": pending, "hint": "por resolver"},
            {"label": "ROI", "value": _pct(track.get("roi")), "hint": "si hay datos"},
            {"label": "Winrate", "value": _pct(track.get("winrate")), "hint": "si hay datos"},
        ],
    }


def build_v757_next_actions(data: dict[str, Any], user: dict[str, Any] | None = None, track_record: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    data = _dict(data)
    user = _dict(user)
    track = _dict(track_record)
    hub = _dict(data.get("match_hub"))
    counts = _dict(hub.get("counts"))
    picks = _list(data.get("picks"))
    plan = _txt(user.get("membership") or user.get("role"), "FREE").upper()
    actions = [
        {"priority": 1, "title": "Mirar partidos de hoy", "body": "Empieza por el calendario ordenado por directo, picks y ligas importantes.", "href": "/calendar?lane=today", "badge": "Hoy"},
        {"priority": 2, "title": "Revisar picks premium", "body": "Comprueba mercado, cuota, stake y riesgo antes de entrar.", "href": "/picks", "badge": "Picks"},
        {"priority": 3, "title": "Abrir directo", "body": "Sigue marcadores y estados sin salir de la app.", "href": "/live", "badge": "Live"},
    ]
    if not picks:
        actions.insert(1, {"priority": 1, "title": "Sin picks forzados", "body": "SHARK no publica picks si faltan mercado, cuota o valor real.", "href": "/picks", "badge": "Disciplina"})
    if _num(counts.get("live"), 0) > 0:
        actions.insert(0, {"priority": 0, "title": "Hay directo ahora", "body": "Revisa partidos live y posibles alertas SHARK.", "href": "/live", "badge": "En directo"})
    if plan == "FREE":
        actions.append({"priority": 4, "title": "Subir a PRO", "body": "Desbloquea picks premium, Telegram y análisis SHARK completo.", "href": "/membresias", "badge": "Plan"})
    if not _num(track.get("decided_total"), 0):
        actions.append({"priority": 5, "title": "Track Record transparente", "body": "El rendimiento se mostrará cuando existan resultados reales auditables.", "href": "/track-record", "badge": "Confianza"})
    return sorted(actions, key=lambda item: item.get("priority", 99))[:6]


def build_v757_app_center(data: dict[str, Any], user: dict[str, Any] | None = None, track_record: dict[str, Any] | None = None) -> dict[str, Any]:
    data = _dict(data)
    user = _dict(user)
    track = _dict(track_record)
    hub = _dict(data.get("match_hub"))
    counts = _dict(hub.get("counts"))
    picks = _list(data.get("picks"))
    smart = _dict(data.get("smart_picks"))
    hot = _list(smart.get("hot")) or picks
    today = _list(hub.get("today")) or _list(data.get("matches"))
    live = _list(hub.get("live"))
    upcoming = _list(data.get("upcoming_matches")) or _list(hub.get("upcoming"))
    plan = _txt(user.get("membership") or user.get("role"), "FREE").upper()
    score = _score_from_data(data, track)
    trust = build_v757_trust_snapshot(track)
    focus_matches = (live + today + upcoming)[:5]
    return {
        "version_tag": "V757_GLOBAL_APP_EXPERIENCE_TRUST_NAVIGATION_POLISH",
        "plan": plan,
        "score": score,
        "headline": "Centro de mando NeMeSiS",
        "subtitle": "Todo lo importante de tu app: partidos, picks, directo, Telegram, track record y siguientes pasos.",
        "health_label": "Operativa" if score >= 75 else "Pendiente de datos",
        "kpis": [
            {"label": "Partidos hoy", "value": counts.get("today", counts.get("upcoming", "—")), "href": "/calendar?lane=today", "hint": "agenda"},
            {"label": "Directo", "value": counts.get("live", "—"), "href": "/live", "hint": "live"},
            {"label": "Picks visibles", "value": len(picks), "href": "/picks", "hint": "premium"},
            {"label": "Confianza", "value": f"{score}/100", "href": "/track-record", "hint": trust.get("status")},
        ],
        "journey": [
            {"step": "1", "title": "Ver calendario", "body": "Hoy, mañana, semana, directo y favoritos.", "href": "/calendar"},
            {"step": "2", "title": "Entrar a picks", "body": "Solo señales con explicación, riesgo y stake responsable.", "href": "/picks"},
            {"step": "3", "title": "Seguir en Telegram", "body": "Automático cuando haya candidato válido y sin duplicar.", "href": "/telegram"},
            {"step": "4", "title": "Medir resultados", "body": "Track Record real, sin inventar ROI.", "href": "/track-record"},
        ],
        "next_actions": build_v757_next_actions(data, user, track),
        "featured_picks": [
            {"title": _pick_name(p), "risk": _txt(p.get("risk_level"), "Medio"), "odds": p.get("odds") or "—", "href": f"/match/{p.get('match_id')}" if p.get("match_id") else "/picks"}
            for p in hot[:4]
        ],
        "focus_matches": [
            {"title": _match_name(m), "time": _txt(m.get("safe_time") or m.get("madrid_display") or m.get("display_datetime") or m.get("kickoff_time") or m.get("match_time"), "Hora pendiente"), "competition": _txt(m.get("safe_competition") or m.get("competition_name") or m.get("league_name"), "Competición"), "href": f"/match/{m.get('id')}" if m.get("id") else "/calendar", "has_pick": bool(m.get("has_pick"))}
            for m in focus_matches
        ],
        "trust": trust,
        "safe_message": "NeMeSiS prioriza claridad, hora Madrid, no duplicar Telegram y no inventar picks ni resultados.",
    }
