from datetime import datetime, timedelta


REAL_TIME_STATES = {
    "upcoming": {"label": "Proximo", "badge": "upcoming", "refresh_seconds": 90, "weight": 45},
    "live": {"label": "Live", "badge": "live", "refresh_seconds": 20, "weight": 100},
    "halftime": {"label": "Descanso", "badge": "half", "refresh_seconds": 35, "weight": 88},
    "finished": {"label": "Finalizado", "badge": "done", "refresh_seconds": 300, "weight": 25},
    "suspended": {"label": "Suspendido", "badge": "suspended", "refresh_seconds": 180, "weight": 10},
}


def real_time_state(match):
    status = str(match.get("status") or "").strip().lower()
    minute = str(match.get("minute") or "").strip().lower()
    if any(x in status for x in ["suspend", "aplaz", "postponed", "abandoned"]):
        key = "suspended"
    elif status in {"ht", "descanso"} or "half" in status or minute == "ht":
        key = "halftime"
    elif status in {"ft", "finalizado", "finished", "final"}:
        key = "finished"
    elif minute or any(x in status for x in ["live", "directo", "1h", "2h"]):
        key = "live"
    else:
        key = "upcoming"
    state = dict(REAL_TIME_STATES[key])
    state["key"] = key
    return state


def next_refresh_at(now_iso, seconds):
    try:
        base = datetime.fromisoformat(now_iso)
    except ValueError:
        base = datetime.utcnow()
    return (base + timedelta(seconds=int(seconds))).isoformat(timespec="seconds")


def sync_plan(matches, now_iso):
    states = {key: 0 for key in REAL_TIME_STATES}
    refresh_seconds = 120
    for match in matches:
        state = real_time_state(match)
        states[state["key"]] += 1
        refresh_seconds = min(refresh_seconds, int(state["refresh_seconds"]))
    if not matches:
        refresh_seconds = 180
    return {
        "states": states,
        "refresh_seconds": refresh_seconds,
        "next_refresh_at": next_refresh_at(now_iso, refresh_seconds),
        "fallback": "automatic",
        "sync_status": "live-linked" if states["live"] or states["halftime"] else "standby",
    }


def prioritize_matches(matches, favorite_ids=None, pick_match_ids=None):
    favorite_ids = set(favorite_ids or [])
    pick_match_ids = set(pick_match_ids or [])
    ranked = []
    for match in matches:
        state = real_time_state(match)
        score = int(match.get("priority") or 50) + int(state["weight"])
        if str(match.get("id") or "").lower() in favorite_ids or match.get("is_favorite"):
            score += 35
        if str(match.get("id") or "").lower() in pick_match_ids:
            score += 18
        item = dict(match)
        item["real_time_state"] = state
        item["real_time_score"] = score
        ranked.append(item)
    return sorted(ranked, key=lambda item: item.get("real_time_score", 0), reverse=True)


def hub_sections(matches, favorites=None, picks=None):
    favorites = favorites or []
    picks = picks or []
    favorite_ids = {str(f.get("value") or "").lower() for f in favorites if f.get("kind") == "match"}
    pick_match_ids = {str(p.get("match_id") or "").lower() for p in picks if p.get("match_id")}
    ranked = prioritize_matches(matches, favorite_ids=favorite_ids, pick_match_ids=pick_match_ids)
    return {
        "live": [m for m in ranked if (m.get("real_time_state") or {}).get("key") in {"live", "halftime"}],
        "today": ranked,
        "upcoming": [m for m in ranked if (m.get("real_time_state") or {}).get("key") == "upcoming"],
        "finished": [m for m in ranked if (m.get("real_time_state") or {}).get("key") == "finished"],
        "favorites": [m for m in ranked if m.get("is_favorite")],
        "with_picks": [m for m in ranked if str(m.get("id") or "").lower() in pick_match_ids],
        "top": ranked[:20],
    }
