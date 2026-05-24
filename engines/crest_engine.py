def crest_status(team):
    if team.get("logo_url"):
        return {"mode": "logo", "source": team.get("source") or "cache"}
    return {"mode": "fallback", "source": "svg propio"}
