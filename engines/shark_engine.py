def explain_pick_risk(pick):
    confidence = int(pick.get("confidence") or 50)
    odds = float(pick.get("odds") or 0)
    if confidence >= 72 and odds <= 1.7:
        risk = "bajo"
    elif confidence >= 58:
        risk = "medio"
    else:
        risk = "alto"
    return {
        "risk": risk,
        "confidence": confidence,
        "odds": odds,
        "explanation": pick.get("reasoning") or f"Riesgo {risk}: confianza {confidence}% con cuota {odds}.",
    }


def build_shark_context(
    match=None,
    league=None,
    favorites=None,
    picks=None,
    profile=None,
    match_intelligence=None,
):
    favorites = favorites or []
    picks = picks or []
    profile = profile or {}
    return {
        "match": match or {},
        "match_intelligence": dict(match_intelligence or {}),
        "league": league or ((match or {}).get("competition_name") if match else ""),
        "favorites": favorites[:20],
        "recent_picks": picks[:12],
        "profile": {
            "name": profile.get("name"),
            "plan": profile.get("membership_plan"),
            "focus": (profile.get("preferences") or {}).get("focus") if isinstance(profile.get("preferences"), dict) else "",
        },
        "context_ready": True,
    }
