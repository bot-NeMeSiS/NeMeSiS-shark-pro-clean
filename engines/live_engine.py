"""Live intelligence helpers for NeMeSiS SHARK PRO.

Pure helpers: no Flask, no network and no SQLite writes here.
"""

import json
import re

from engines.v935_launch_trust_engine import match_status_truth


LIVE_STATES = {
    "LIVE": {"label": "LIVE", "badge": "live", "priority": 100},
    "HT": {"label": "DESCANSO", "badge": "half", "priority": 92},
    "FT": {"label": "FINAL", "badge": "done", "priority": 35},
    "UPCOMING": {"label": "PROXIMO", "badge": "upcoming", "priority": 65},
    "SUSPENDED": {"label": "SUSPENDIDO", "badge": "suspended", "priority": 20},
}

SUPPORTED_EVENT_TYPES = {"goal", "yellow", "red", "substitution", "penalty", "var", "state"}


def _minute_number(value):
    found = re.findall(r"\d+", str(value or ""))
    return int(found[0]) if found else 0


def _number(match, *keys, default=0.0):
    for key in keys:
        value = match.get(key)
        if value in (None, ""):
            continue
        try:
            return float(str(value).replace("%", "").replace(",", "."))
        except (TypeError, ValueError):
            continue
    return float(default)


def _payload(match):
    raw = match.get("payload_json") or match.get("raw_json") or "{}"
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


def normalize_live_state(match):
    truth = match_status_truth(dict(match or {}))
    lifecycle = truth.get("lifecycle")
    if lifecycle == "HALFTIME":
        key = "HT"
    elif lifecycle == "LIVE" and not truth.get("status_conflict"):
        key = "LIVE"
    elif lifecycle in {"FINISHED", "ARCHIVED"}:
        key = "FT"
    elif lifecycle in {"POSTPONED", "SUSPENDED", "CANCELLED", "ABANDONED", "RESULT_PENDING", "INCOMPLETE"}:
        key = "SUSPENDED"
    else:
        key = "UPCOMING"
    state = dict(LIVE_STATES[key])
    state["key"] = key
    state["status_contract"] = truth.get("contract")
    state["status_conflict"] = bool(truth.get("status_conflict"))
    if lifecycle == "RESULT_PENDING":
        state.update({"label": "RESULTADO PENDIENTE", "badge": "result_pending"})
    elif lifecycle == "CANCELLED":
        state.update({"label": "CANCELADO", "badge": "cancelled"})
    elif lifecycle == "ABANDONED":
        state.update({"label": "ABANDONADO", "badge": "abandoned"})
    elif lifecycle == "POSTPONED":
        state.update({"label": "APLAZADO", "badge": "postponed"})
    return state


def shark_momentum(match):
    """Estimate live pressure using only available legal match stats.

    The function accepts flat fields or raw/payload JSON with common keys. If a
    stat is missing it contributes zero instead of inventing data.
    """
    payload = _payload(match)
    data = {**payload, **dict(match)}
    minute = _minute_number(data.get("minute"))
    home_score = _number(data, "home_score", "intHomeScore")
    away_score = _number(data, "away_score", "intAwayScore")
    home_possession = _number(data, "home_possession", "home_possession_pct", "possession_home", "strHomePossession")
    away_possession = _number(data, "away_possession", "away_possession_pct", "possession_away", "strAwayPossession")
    if home_possession and not away_possession:
        away_possession = max(0, 100 - home_possession)
    if away_possession and not home_possession:
        home_possession = max(0, 100 - away_possession)

    home_shots = _number(data, "home_shots", "shots_home", "home_total_shots")
    away_shots = _number(data, "away_shots", "shots_away", "away_total_shots")
    home_sot = _number(data, "home_shots_on_target", "shots_on_target_home", "home_sot")
    away_sot = _number(data, "away_shots_on_target", "shots_on_target_away", "away_sot")
    home_corners = _number(data, "home_corners", "corners_home")
    away_corners = _number(data, "away_corners", "corners_away")

    home_score_signal = max(-10, min(10, (home_score - away_score) * 4))
    away_score_signal = -home_score_signal
    tempo_bonus = 6 if 60 <= minute <= 88 else 3 if 35 <= minute < 60 else 0

    home = 45 + (home_possession - away_possession) * 0.18 + (home_shots - away_shots) * 1.6 + (home_sot - away_sot) * 4 + (home_corners - away_corners) * 1.8 + home_score_signal + tempo_bonus
    away = 45 + (away_possession - home_possession) * 0.18 + (away_shots - home_shots) * 1.6 + (away_sot - home_sot) * 4 + (away_corners - home_corners) * 1.8 + away_score_signal + tempo_bonus
    home = max(0, min(100, round(home)))
    away = max(0, min(100, round(away)))

    pressure = max(home, away)
    dominance_gap = abs(home - away)
    risk = min(100, pressure + min(20, dominance_gap // 2) + (8 if minute >= 75 else 0))
    dominant = "local" if home > away + 8 else "visitante" if away > home + 8 else "equilibrado"
    return {
        "momentum_local": home,
        "momentum_visitante": away,
        "presion": pressure,
        "dominancia": dominant,
        "riesgo": risk,
        "minute": minute,
        "stats_available": any([home_possession, away_possession, home_shots, away_shots, home_sot, away_sot, home_corners, away_corners]),
    }


def normalize_timeline_events(events):
    normalized = []
    for event in events or []:
        kind = str(event.get("event_type") or event.get("type") or "state").strip().lower()
        if kind not in SUPPORTED_EVENT_TYPES:
            kind = "state"
        normalized.append({
            "minute": event.get("minute") or event.get("time") or "",
            "event_type": kind,
            "title": event.get("title") or kind.replace("_", " ").title(),
            "detail": event.get("detail") or event.get("description") or "",
            "team": event.get("team") or "",
            "player": event.get("player") or "",
            "source": event.get("source") or "",
        })
    return normalized


def shark_live_alerts(match, momentum=None):
    momentum = momentum or shark_momentum(match)
    alerts = []
    leader = "local" if momentum["momentum_local"] >= momentum["momentum_visitante"] else "visitante"
    if max(momentum["momentum_local"], momentum["momentum_visitante"]) > 85:
        alerts.append({"type": "momentum", "level": "high", "title": "Momentum SHARK alto", "body": f"El {leader} supera 85 de momentum.", "telegram_ready": True})
    if momentum["presion"] >= 88:
        alerts.append({"type": "pressure", "level": "critical", "title": "Presion extrema", "body": "El partido muestra presion elevada con los datos disponibles.", "telegram_ready": True})
    if momentum["riesgo"] >= 90:
        alerts.append({"type": "possible_goal", "level": "watch", "title": "Posible gol", "body": "Riesgo alto de evento importante. Revisar live antes de actuar.", "telegram_ready": True})
    return alerts


def build_live_depth(match):
    state = normalize_live_state(match)
    raw_minute = str(match.get("minute") or match.get("elapsed") or match.get("live_minute") or "").strip().strip("'\u2019")
    minute_value = ""
    if state["key"] in {"LIVE", "HT"}:
        minute_value = f"{raw_minute}'" if re.fullmatch(r"(?:[1-9]\d?|1[0-2]\d)(?:\+\d{1,2})?", raw_minute) else state["label"].title()
    elif state["key"] == "FT":
        minute_value = "FT"
    elif state["key"] == "UPCOMING":
        minute_value = match.get("kickoff_time") or "Hora pendiente"
    else:
        minute_value = state["label"].title()
    minute_score = _minute_number(match.get("minute"))
    if state["key"] == "LIVE":
        base_momentum = min(100, 52 + minute_score // 2)
    elif state["key"] == "HT":
        base_momentum = 74
    elif state["key"] == "FT":
        base_momentum = 100
    elif state["key"] == "SUSPENDED":
        base_momentum = 8
    else:
        base_momentum = max(18, min(65, int(match.get("priority") or 50)))
    intelligence = shark_momentum(match)
    if state["key"] in {"LIVE", "HT"} and intelligence["stats_available"]:
        base_momentum = max(base_momentum, intelligence["presion"])
    return {
        "state": state["key"],
        "label": state["label"],
        "badge": state["badge"],
        "momentum": base_momentum,
        "score": match.get("score") or "-",
        "minute": minute_value,
        "shark_momentum": intelligence,
        "alerts": shark_live_alerts(match, intelligence) if state["key"] in {"LIVE", "HT"} else [],
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
    return normalize_timeline_events([{"minute": depth["minute"], "event_type": "state", "title": title, "detail": detail, "source": match.get("source")}])


def build_match_detail(match, timeline=None, related_picks=None, favorite=False):
    depth = build_live_depth(match)
    events = normalize_timeline_events(timeline) or fallback_timeline(match)
    momentum = depth["shark_momentum"]
    return {
        "id": match.get("id"),
        "match": match,
        "state": depth,
        "favorite": bool(favorite),
        "timeline": events,
        "events": events,
        "statistics": {
            "status": "live_intelligence_ready",
            "items": [
                {"label": "Momentum local", "home": momentum["momentum_local"], "away": momentum["momentum_visitante"]},
                {"label": "Presion", "home": momentum["presion"], "away": 100 - momentum["presion"]},
                {"label": "Riesgo", "home": momentum["riesgo"], "away": 100},
            ],
        },
        "momentum": {"value": depth["momentum"], "label": depth["label"], **momentum},
        "alerts": depth["alerts"],
        "lineups": {"status": "prepared", "home": [], "away": [], "note": "Estructura lista para fuente legal futura."},
        "related_picks": related_picks or [],
    }


def build_live_flow(hub, favorites=None, picks=None, profile=None):
    favorites = favorites or []
    picks = picks or []
    profile = profile or {}
    live = hub.get("live", [])
    return {
        "hub_counts": hub.get("counts", {}),
        "live": live,
        "alerts": [alert for match in live for alert in ((match.get("live_depth") or {}).get("alerts") or [])],
        "favorites_live": [m for m in hub.get("favorites", []) if (m.get("live_depth") or {}).get("state") in {"LIVE", "HT"}],
        "favorite_count": len(favorites),
        "pick_count": len(picks),
        "profile_plan": profile.get("membership_plan", "free"),
        "shared_state": "CONNECTED",
    }
