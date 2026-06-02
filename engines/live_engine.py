"""Live intelligence helpers for NeMeSiS SHARK PRO.

Pure helpers: no Flask, no network and no SQLite writes here.
"""

import json
import re


LIVE_STATES = {
    "LIVE": {"label": "En directo", "badge": "live", "priority": 100},
    "HT": {"label": "Descanso", "badge": "half", "priority": 92},
    "FT": {"label": "Finalizado", "badge": "done", "priority": 35},
    "UPCOMING": {"label": "Próximo", "badge": "upcoming", "priority": 65},
    "SUSPENDED": {"label": "Suspendido", "badge": "suspended", "priority": 20},
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
    return sorted(normalized, key=lambda item: _minute_number(item.get("minute")), reverse=True)


def shark_live_alerts(match, momentum=None):
    momentum = momentum or shark_momentum(match)
    alerts = []
    leader = "local" if momentum["momentum_local"] >= momentum["momentum_visitante"] else "visitante"
    if max(momentum["momentum_local"], momentum["momentum_visitante"]) > 85:
        alerts.append({"type": "momentum", "level": "high", "title": "Momentum SHARK alto", "body": f"El {leader} supera 85 de momentum.", "telegram_ready": True})
    if momentum["presion"] >= 88:
        alerts.append({"type": "pressure", "level": "critical", "title": "Presión extrema", "body": "El partido muestra presión elevada con los datos disponibles.", "telegram_ready": True})
    if momentum["riesgo"] >= 90:
        alerts.append({"type": "possible_goal", "level": "watch", "title": "Posible gol", "body": "Riesgo alto de evento importante. Revisar live antes de actuar.", "telegram_ready": True})
    return alerts


def build_live_depth(match):
    state = normalize_live_state(match)
    minute_value = match.get("minute") or match.get("kickoff_time") or "-"
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
        detail = "Estado pendiente de actualización oficial"
    else:
        title = "Partido preparado"
        detail = str(match.get("status") or "PROGRAMADO")
    return normalize_timeline_events([{"minute": depth["minute"], "event_type": "state", "title": title, "detail": detail, "source": match.get("source")}])


def build_match_detail(match, timeline=None, related_picks=None, favorite=False):
    depth = match.get("live_depth") or build_live_depth(match)
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


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("events", "timeline", "data", "items"):
            if isinstance(value.get(key), list):
                return value.get(key)
    return []


def extract_live_events(match):
    """Extract legal event/timeline rows from persisted payloads only."""
    payload = _payload(match)
    candidates = []
    for key in ("events", "timeline", "match_events", "event"):
        candidates.extend(_as_list(payload.get(key)))
    # TheSportsDB-like payloads sometimes keep a single descriptive event field.
    if payload.get("strEvent") and (payload.get("intHomeScore") or payload.get("intAwayScore")):
        candidates.append({
            "minute": payload.get("strProgress") or match.get("minute") or "",
            "event_type": "state",
            "title": "Estado live",
            "detail": f"{payload.get('strEvent')} · {payload.get('intHomeScore', '')}-{payload.get('intAwayScore', '')}",
            "source": match.get("source") or payload.get("source") or "persisted_payload",
        })
    return normalize_timeline_events(candidates)


def extract_live_statistics(match):
    """Return a compact stat pack without inventing missing figures."""
    payload = _payload(match)
    data = {**payload, **dict(match)}
    stat_defs = [
        ("posesion", "Posesión", ("home_possession", "home_possession_pct", "possession_home", "strHomePossession"), ("away_possession", "away_possession_pct", "possession_away", "strAwayPossession"), "%"),
        ("tiros", "Tiros", ("home_shots", "shots_home", "home_total_shots"), ("away_shots", "shots_away", "away_total_shots"), ""),
        ("tiros_puerta", "Tiros a puerta", ("home_shots_on_target", "shots_on_target_home", "home_sot"), ("away_shots_on_target", "shots_on_target_away", "away_sot"), ""),
        ("corners", "Córners", ("home_corners", "corners_home"), ("away_corners", "corners_away"), ""),
        ("amarillas", "Amarillas", ("home_yellow_cards", "yellow_home"), ("away_yellow_cards", "yellow_away"), ""),
        ("rojas", "Rojas", ("home_red_cards", "red_home"), ("away_red_cards", "red_away"), ""),
    ]
    items = []
    for key, label, hkeys, akeys, suffix in stat_defs:
        home = _number(data, *hkeys, default=None)
        away = _number(data, *akeys, default=None)
        if home is None and away is None:
            continue
        if key == "posesion":
            if home and not away:
                away = max(0, 100 - home)
            if away and not home:
                home = max(0, 100 - away)
        items.append({"key": key, "label": label, "home": home or 0, "away": away or 0, "suffix": suffix})
    return {"available": bool(items), "items": items, "source": match.get("source") or payload.get("source") or "sqlite"}


def build_live_intelligence_card(match):
    depth = build_live_depth(match)
    events = extract_live_events(match) or fallback_timeline(match)
    stats = extract_live_statistics(match)
    momentum = depth.get("shark_momentum") or shark_momentum(match)
    state = depth.get("state")
    score_pressure = momentum.get("presion", 0)
    if state in {"LIVE", "HT"} and score_pressure >= 88:
        action = "Vigilar ahora"
    elif state in {"LIVE", "HT"}:
        action = "Seguir evolución"
    elif state == "FT":
        action = "Guardar para histórico"
    else:
        action = "Preparar seguimiento"
    quality_score = 25
    quality_score += 25 if str(depth.get("minute") or "").strip() not in {"", "-", "Hora"} else 0
    quality_score += 25 if stats.get("available") else 0
    quality_score += 15 if events else 0
    quality_score += 10 if match.get("score") or depth.get("score") else 0
    return {
        "match_id": match.get("id"),
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "league_name": match.get("league_name") or match.get("competition_name"),
        "state": depth,
        "timeline": events[:12],
        "statistics": stats,
        "momentum": momentum,
        "alerts": depth.get("alerts") or [],
        "action": action,
        "data_quality_score": min(100, quality_score),
        "legal_note": match.get("legal_note") or "Datos construidos desde fuentes y payloads persistidos en SQLite.",
    }


def build_deep_live_intelligence(matches):
    cards = [build_live_intelligence_card(m) for m in matches or []]
    live_cards = [c for c in cards if (c.get("state") or {}).get("state") in {"LIVE", "HT"}]
    alerts = [a for c in live_cards for a in (c.get("alerts") or [])]
    return {
        "summary": {
            "total_matches": len(cards),
            "live_matches": len(live_cards),
            "alerts": len(alerts),
            "avg_data_quality": round(sum(c.get("data_quality_score", 0) for c in cards) / max(1, len(cards))),
        },
        "live": live_cards,
        "all": cards,
        "alerts": alerts[:30],
    }
