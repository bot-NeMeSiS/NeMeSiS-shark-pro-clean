def build_sports_hub_payload(date, hub, matches, picks, recommendations, favorites, competitions):
    hub = hub or {}
    return {
        "date": date,
        "today": hub.get("today") or list(matches or [])[:14],
        "live": (hub.get("live") or [])[:10],
        "picks": list(picks or [])[:6],
        "recommendations": list(recommendations or [])[:6],
        "favorites": list(favorites or [])[:8],
        "top_leagues": (hub.get("top_leagues") or list(competitions or []))[:8],
        "counts": hub.get("counts") or {},
    }

