"""Read-only recent form from the same confirmed results as Team Center.

Callers supply already loaded records. This adapter cannot establish complete
season coverage and does not fetch, rewrite or infer missing match results.
"""
from __future__ import annotations

from engines.team_result_evidence_engine import build_team_result_evidence


RECENT_FORM_LIMIT = 5


def team_form_snapshot(matches: list[dict] | None = None, team: str = "") -> dict:
    """Keep the existing snapshot API, but never count a scheduled/live result."""
    name = str(team).strip() if team is not None else ""
    evidence = build_team_result_evidence(matches, name)
    accepted = evidence.get("items") or []
    recent = accepted[:RECENT_FORM_LIMIT]
    results = {"Victoria": "W", "Empate": "D", "Derrota": "L"}
    form = [results[item["outcome"]] for item in recent]
    total = len(recent)
    return {
        "ok": True,
        "contract": "TEAM-FORM-CONFIRMED-CACHE-V1",
        "team": name,
        "matches_found": total,
        "form_available": bool(recent),
        "message": (
            "Forma basada en los últimos resultados finalizados y registrados disponibles; "
            "no representa toda la temporada."
            if recent else
            "No hay resultados finales válidos con fecha e identidad para calcular la forma."
        ),
        "last_matches": [dict(item["match"]) for item in recent],
        "results": [
            {
                "home_team": item["match"].get("home_team") or item["match"].get("safe_home"),
                "away_team": item["match"].get("away_team") or item["match"].get("safe_away"),
                "home_score": item["home_score"], "away_score": item["away_score"],
                "outcome": item["outcome"], "href": item["href"],
                "kickoff": item["kickoff"], "date_label": item["date_label"],
            }
            for item in recent
        ],
        "form": form,
        "sample_size": total,
        "requested_sample_size": RECENT_FORM_LIMIT,
        "wins": form.count("W"),
        "draws": form.count("D"),
        "losses": form.count("L"),
        "goals_for": sum(item["goals_for"] for item in recent),
        "goals_against": sum(item["goals_against"] for item in recent),
        "valid_loaded_results": len(accepted),
        "coverage_state": "LOADED_SAMPLE_ONLY",
        "season_complete": False,
        "expected_played": None,
        "omitted_count": evidence.get("omitted_count", 0),
        "omissions": dict(evidence.get("omission_reasons") or {}),
        "no_fake_data": True,
        "external_calls": 0,
        "scope": "RECENT_LOADED_RESULTS_ALL_COMPETITIONS",
    }
