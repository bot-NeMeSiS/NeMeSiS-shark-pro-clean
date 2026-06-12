"""Deep data foundation for team form without invented stats."""
from __future__ import annotations


def team_form_snapshot(matches: list[dict] | None = None, team: str = "") -> dict:
    matches = matches or []
    team_low = str(team or "").lower()
    related = [
        m for m in matches
        if team_low and (str(m.get("home_team") or "").lower() == team_low or str(m.get("away_team") or "").lower() == team_low)
    ][:5]
    return {
        "ok": True,
        "team": team,
        "matches_found": len(related),
        "form_available": bool(related),
        "message": "Datos pendientes de sincronización." if not related else "Forma basada en partidos sincronizados disponibles.",
        "last_matches": related,
        "no_fake_data": True,
    }
