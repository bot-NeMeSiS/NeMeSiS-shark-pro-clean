import re


LIVE_STATES = {
    "LIVE": {"label": "LIVE", "badge": "live", "priority": 100},
    "HT": {"label": "DESCANSO", "badge": "half", "priority": 92},
    "FT": {"label": "FINAL", "badge": "done", "priority": 35},
    "UPCOMING": {"label": "PROXIMO", "badge": "upcoming", "priority": 65},
    "SUSPENDED": {"label": "SUSPENDIDO", "badge": "suspended", "priority": 20},
}


def _minute_number(value):
    found = re.findall(r"\d+", str(value or ""))
    return int(found[0]) if found else 0


def normalize_live_state(match):
    status = str(match.get("status") or "").strip().lower()
    minute = str(match.get("minute") or "").strip().lower()
    if any(x in status for x in ["suspend", "aplaz", "postponed", "abandoned"]):
        key = "SUSPENDED"
    elif status in {"ht", "descanso"} or "half" in status or minute == "ht":
        key = "HT"
    elif status in {"ft", "finalizado", "finished", "final"}:
        key = "FT"
    elif minute or any(x in status for x in ["live", "directo", "1h", "2h"]):
        key = "LIVE"
    else:
        key = "UPCOMING"
    state = dict(LIVE_STATES[key])
    state["key"] = key
    return state


def build_live_depth(match):
    state = normalize_live_state(match)
    minute_value = match.get("minute") or match.get("kickoff_time") or "-"
    minute_score = _minute_number(match.get("minute"))
    if state["key"] == "LIVE":
        momentum = min(100, 52 + minute_score // 2)
    elif state["key"] == "HT":
        momentum = 74
    elif state["key"] == "FT":
        momentum = 100
    elif state["key"] == "SUSPENDED":
        momentum = 8
    else:
        momentum = max(18, min(65, int(match.get("priority") or 50)))
    return {
        "state": state["key"],
        "label": state["label"],
        "badge": state["badge"],
        "momentum": momentum,
        "score": match.get("score") or "-",
        "minute": minute_value,
    }


def fallback_timeline(match):
    depth = build_live_depth(match)
    if depth["state"] in {"LIVE", "HT"}:
        title = "Partido activo"
        detail = f"{depth['label']} - marcador {depth['score']}"
    elif depth["state"] == "FT":
        title = "Partido finalizado"
        detail = f"Resultado {depth['score']}"
    elif depth["state"] == "SUSPENDED":
        title = "Partido suspendido"
        detail = "Estado pendiente de actualizacion oficial"
    else:
        title = "Partido preparado"
        detail = str(match.get("status") or "PROGRAMADO")
    return [{"minute": depth["minute"], "event_type": "state", "title": title, "detail": detail, "source": match.get("source")}]


def build_match_detail(match, timeline=None, related_picks=None, favorite=False):
    depth = build_live_depth(match)
    return {
        "id": match.get("id"),
        "match": match,
        "state": depth,
        "favorite": bool(favorite),
        "timeline": timeline or fallback_timeline(match),
        "events": timeline or fallback_timeline(match),
        "statistics": {
            "status": "fallback_ready",
            "items": [
                {"label": "Momentum", "home": depth["momentum"], "away": max(0, 100 - depth["momentum"])},
                {"label": "Prioridad", "home": int(match.get("priority") or 50), "away": 100},
            ],
        },
        "momentum": {"value": depth["momentum"], "label": depth["label"]},
        "lineups": {"status": "prepared", "home": [], "away": [], "note": "Estructura lista para fuente legal futura."},
        "related_picks": related_picks or [],
    }


def build_live_flow(hub, favorites=None, picks=None, profile=None):
    favorites = favorites or []
    picks = picks or []
    profile = profile or {}
    return {
        "hub_counts": hub.get("counts", {}),
        "live": hub.get("live", []),
        "favorites_live": [m for m in hub.get("favorites", []) if (m.get("live_depth") or {}).get("state") in {"LIVE", "HT"}],
        "favorite_count": len(favorites),
        "pick_count": len(picks),
        "profile_plan": profile.get("membership_plan", "free"),
        "shared_state": "CONNECTED",
    }
