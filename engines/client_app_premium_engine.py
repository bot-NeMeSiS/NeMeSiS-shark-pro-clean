"""V756 premium client app experience helpers.

Pure, defensive builders used by routes/templates to make the client app feel
more cohesive without touching Telegram, Cron, DB_PATH or data pipelines.
"""
from __future__ import annotations

from typing import Any


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    return []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _txt(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _num(value: Any, fallback: Any = 0) -> Any:
    try:
        return int(float(str(value or "0").replace(",", ".")))
    except Exception:
        return fallback


def _pick_title(pick: dict[str, Any]) -> str:
    home = _txt(pick.get("home_team") or pick.get("safe_home"), "Equipo local")
    away = _txt(pick.get("away_team") or pick.get("safe_away"), "Equipo visitante")
    return f"{home} vs {away}"


def _pick_selection(pick: dict[str, Any]) -> str:
    return _txt(
        pick.get("selection_display")
        or pick.get("selection")
        or pick.get("recommended_pick")
        or pick.get("pick")
        or pick.get("market"),
        "Selección pendiente",
    )


def _match_title(match: dict[str, Any]) -> str:
    home = _txt(match.get("safe_home") or match.get("home_team"), "Equipo local")
    away = _txt(match.get("safe_away") or match.get("away_team"), "Equipo visitante")
    return f"{home} vs {away}"


def _match_time(match: dict[str, Any]) -> str:
    live_depth = _as_dict(match.get("live_depth"))
    return _txt(
        match.get("safe_time")
        or match.get("madrid_display")
        or match.get("display_datetime")
        or match.get("kickoff_time")
        or match.get("match_time")
        or live_depth.get("minute"),
        "Hora pendiente",
    )


def _match_comp(match: dict[str, Any]) -> str:
    return _txt(match.get("safe_competition") or match.get("competition_name") or match.get("league_name") or match.get("competition_key"), "Competición")


def _pick_status_label(pick: dict[str, Any]) -> str:
    status = _txt(pick.get("result_status") or pick.get("status"), "pending").lower()
    return {
        "won": "Ganado",
        "lost": "Perdido",
        "void": "Nulo",
        "published": "Pendiente",
        "pending": "Pendiente",
        "draft": "En estudio",
    }.get(status, status.capitalize())


def _safe_href(prefix: str, value: Any, fallback: str) -> str:
    text = _txt(value)
    return f"{prefix}{text}" if text else fallback


def build_client_premium_home(data: dict[str, Any], user: dict[str, Any] | None = None) -> dict[str, Any]:
    data = _as_dict(data)
    user = _as_dict(user)
    hub = _as_dict(data.get("match_hub"))
    counts = _as_dict(hub.get("counts"))
    home_summary = _as_dict(data.get("home_summary"))
    summary_counts = _as_dict(home_summary.get("counts"))
    smart = _as_dict(data.get("smart_picks"))
    hot = _as_list(smart.get("hot")) or _as_list(data.get("picks"))
    today_matches = _as_list(hub.get("today"))
    live_matches = _as_list(hub.get("live"))
    upcoming = _as_list(data.get("upcoming_matches")) or _as_list(hub.get("upcoming"))
    featured_matches = (live_matches + today_matches + upcoming)[:6]
    plan = _txt(user.get("membership") or user.get("role"), "FREE").upper()
    has_real_data = bool(home_summary.get("has_real_data") or counts or summary_counts)
    return {
        "plan": plan,
        "headline": "Centro cliente SHARK",
        "subtitle": "Tu inicio rápido para ver partidos, picks, directo y alertas sin perderte entre pantallas.",
        "has_real_data": has_real_data,
        "data_message": _txt(home_summary.get("message") or hub.get("data_message"), "SHARK mostrará datos reales cuando producción sincronice partidos y picks."),
        "summary_cards": [
            {"label": "Partidos hoy", "value": summary_counts.get("today", counts.get("today", "—")), "href": "/calendar?lane=today", "hint": "agenda", "tone": "primary"},
            {"label": "Directo", "value": summary_counts.get("live", counts.get("live", "—")), "href": "/live", "hint": "minuto", "tone": "live"},
            {"label": "Picks activos", "value": len(hot), "href": "/picks", "hint": "premium", "tone": "pick"},
            {"label": "Favoritos", "value": summary_counts.get("favorites", counts.get("favorites", "—")), "href": "/favorites", "hint": "mi feed", "tone": "favorite"},
        ],
        "quick_actions": [
            {"label": "Partidos de hoy", "href": "/calendar?lane=today", "badge": "Hoy"},
            {"label": "Directos", "href": "/live", "badge": "Live"},
            {"label": "Picks", "href": "/picks", "badge": "SHARK"},
            {"label": "Telegram", "href": "/telegram", "badge": "Auto"},
            {"label": "Track Record", "href": "/track-record", "badge": "ROI"},
            {"label": "SHARK IA", "href": "/shark", "badge": "AI"},
        ],
        "featured_picks": [
            {
                "id": p.get("id"),
                "match_id": p.get("match_id"),
                "title": _pick_title(p),
                "selection": _pick_selection(p),
                "market": _txt(p.get("market"), "Mercado"),
                "odds": p.get("odds") or "—",
                "stake": p.get("stake_units") or "1",
                "risk": _txt(p.get("risk_level"), "Medio"),
                "score": p.get("quality_score") or p.get("confidence") or p.get("shark_score") or 0,
                "href": _safe_href("/match/", p.get("match_id"), "/picks"),
            }
            for p in hot[:3]
        ],
        "featured_matches": [
            {
                "id": m.get("id"),
                "title": _match_title(m),
                "competition": _match_comp(m),
                "time": _match_time(m),
                "status": _txt(_as_dict(m.get("live_depth")).get("label") or m.get("safe_status") or m.get("status"), "Próximo"),
                "score": _txt(_as_dict(m.get("live_depth")).get("score") or m.get("score"), "vs"),
                "has_pick": bool(m.get("has_pick")),
                "href": _safe_href("/match/", m.get("id"), "/calendar"),
            }
            for m in featured_matches[:6]
        ],
    }


def build_client_premium_picks(data: dict[str, Any], user: dict[str, Any] | None = None, filter_key: str = "all") -> dict[str, Any]:
    data = _as_dict(data)
    user = _as_dict(user)
    smart = _as_dict(data.get("smart_picks"))
    hot = _as_list(smart.get("hot"))
    study = _as_list(smart.get("study"))
    published = _as_list(smart.get("published")) or _as_list(data.get("picks"))
    candidates = _as_list(data.get("candidate_matches"))
    plan = _txt(user.get("membership") or user.get("role"), "FREE").upper()
    return {
        "plan": plan,
        "filter": _txt(filter_key, "all"),
        "status_cards": [
            {"label": "Premium listos", "value": len(hot), "hint": "con cuota/mercado", "href": "#premium"},
            {"label": "En estudio", "value": len(study), "hint": "sin vender humo", "href": "#en-estudio"},
            {"label": "Partidos analizables", "value": len(candidates), "hint": "próximos", "href": "#en-estudio"},
            {"label": "Publicados", "value": len(published), "hint": "histórico", "href": "/track-record"},
        ],
        "filters": [
            {"label": "Todos", "href": "/picks", "active": filter_key in {"", "all", "todos"}},
            {"label": "Hoy", "href": "/picks?filtro=hoy", "active": filter_key == "hoy"},
            {"label": "Próximos", "href": "/picks?filtro=proximos", "active": filter_key == "proximos"},
            {"label": "Telegram", "href": "/picks?filtro=telegram", "active": filter_key == "telegram"},
            {"label": "TOP", "href": "/picks?filtro=top", "active": filter_key == "top"},
            {"label": "En estudio", "href": "#en-estudio", "active": filter_key == "estudio"},
        ],
        "featured": [
            {
                "title": _pick_title(p),
                "selection": _pick_selection(p),
                "odds": p.get("odds") or "—",
                "risk": _txt(p.get("risk_level"), "Medio"),
                "status": _pick_status_label(p),
                "href": _safe_href("/match/", p.get("match_id"), "/picks"),
            }
            for p in (hot or published)[:4]
        ],
        "empty_message": "No hay picks premium listos. SHARK mantiene la disciplina y no publica apuestas sin mercado claro.",
    }


def build_client_premium_calendar(data: dict[str, Any]) -> dict[str, Any]:
    data = _as_dict(data)
    calendar = _as_dict(data.get("calendar"))
    counts = _as_dict(calendar.get("counts"))
    groups = _as_list(calendar.get("groups"))
    return {
        "summary": [
            {"label": "Visibles", "value": counts.get("visible", 0)},
            {"label": "Directo", "value": counts.get("live", 0)},
            {"label": "Con pick", "value": counts.get("picks", 0)},
            {"label": "Ligas", "value": counts.get("leagues", 0)},
        ],
        "smart_links": [
            {"label": "Hoy", "href": "/calendar?lane=today"},
            {"label": "Mañana", "href": "/calendar?lane=tomorrow"},
            {"label": "Semana", "href": "/calendar?lane=week"},
            {"label": "Con pick", "href": "/calendar?lane=with_pick"},
            {"label": "Directo", "href": "/live"},
            {"label": "España", "href": "/calendar?lane=spain"},
        ],
        "guide": "Ordenado por directo, picks, favoritos, importancia de competición y hora Madrid.",
        "has_results": bool(groups or counts.get("visible")),
    }


def build_client_premium_match(detail: dict[str, Any] | None) -> dict[str, Any]:
    detail = _as_dict(detail)
    match = _as_dict(detail.get("match"))
    related = _as_list(detail.get("related_picks"))
    state = _as_dict(detail.get("state"))
    return {
        "title": _match_title(match) if match else "Partido",
        "status": _txt(state.get("label") or match.get("status"), "Próximo"),
        "time": _match_time(match),
        "related_picks": len(related),
        "actions": [
            {"label": "Volver al calendario", "href": "/calendar"},
            {"label": "Ver directos", "href": "/live"},
            {"label": "Picks", "href": "/picks"},
            {"label": "Preguntar a SHARK", "href": f"/shark?match={match.get('id') or ''}"},
        ],
        "client_hint": "Revisa hora, mercado, cuota y riesgo antes de entrar. SHARK no fuerza picks si faltan datos fiables.",
    }


def build_client_app_premium_context(data: dict[str, Any], user: dict[str, Any] | None = None, *, filter_key: str = "all", detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "home": build_client_premium_home(data, user),
        "picks": build_client_premium_picks(data, user, filter_key=filter_key),
        "calendar": build_client_premium_calendar(data),
        "match": build_client_premium_match(detail),
        "version_tag": "V756_CLIENT_APP_PREMIUM_EXPERIENCE_TOTAL_POLISH",
    }
