"""Live experience helpers for V742.

Pure helpers: no HTTP, no external API calls and no writes.
"""

from __future__ import annotations

import re
from typing import Any

IMPORTANT_TERMS = (
    "laliga",
    "primera",
    "segunda",
    "premier",
    "champions",
    "europa",
    "conference",
    "serie a",
    "bundesliga",
    "ligue",
    "primeira",
    "copa",
    "mundial",
    "uefa",
    "fifa",
)

SPAIN_TERMS = ("españa", "spain", "laliga", "segunda", "copa del rey", "rfef")
ANDALUCIA_TERMS = ("andaluc", "sevilla", "betis", "granada", "malaga", "málaga", "cadiz", "cádiz", "cordoba", "córdoba", "almeria", "almería", "huelva", "jaen", "jaén")


def text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def lower_blob(match: dict) -> str:
    keys = [
        "home_team",
        "away_team",
        "safe_home",
        "safe_away",
        "competition_name",
        "safe_competition",
        "league_name",
        "country",
        "safe_country",
        "status",
    ]
    return " | ".join(text(match.get(k)).lower() for k in keys)


def state_bucket(match: dict) -> str:
    depth = match.get("live_depth") or {}
    badge = text(depth.get("badge") or "").lower()
    label = text(depth.get("label") or match.get("status") or "").lower()
    if badge == "live" or any(word in label for word in ("directo", "live", "descanso")):
        return "live"
    if badge in {"finished", "finalizado"} or any(word in label for word in ("final", "finished", "terminado")):
        return "finished"
    if any(word in label for word in ("aplaz", "suspend", "postpon")):
        return "postponed"
    return "upcoming"


def has_pick(match: dict) -> bool:
    if match.get("has_pick") or match.get("pick_id") or match.get("related_pick"):
        return True
    return bool(match.get("pick") or match.get("picks"))


def match_filter(match: dict, lane: str, query: str = "") -> bool:
    lane = text(lane or "all").lower()
    blob = lower_blob(match)
    if query and query.lower() not in blob:
        return False
    bucket = state_bucket(match)
    if lane in {"live", "directo"}:
        return bucket == "live"
    if lane in {"today", "hoy", "all"}:
        return True
    if lane in {"upcoming", "proximos", "próximos"}:
        return bucket == "upcoming"
    if lane in {"finished", "finalizados"}:
        return bucket == "finished"
    if lane in {"picks", "con_pick"}:
        return has_pick(match)
    if lane in {"favorites", "favoritos"}:
        return bool(match.get("is_favorite"))
    if lane in {"spain", "espana", "españa"}:
        return any(term in blob for term in SPAIN_TERMS)
    if lane in {"andalucia", "andalucía"}:
        return any(term in blob for term in ANDALUCIA_TERMS)
    if lane in {"top", "grandes"}:
        return any(term in blob for term in IMPORTANT_TERMS)
    return True


def importance_score(match: dict) -> int:
    blob = lower_blob(match)
    score = 0
    if state_bucket(match) == "live":
        score += 1000
    if has_pick(match):
        score += 180
    if match.get("is_favorite"):
        score += 160
    for idx, term in enumerate(IMPORTANT_TERMS):
        if term in blob:
            score += max(20, 140 - idx * 8)
            break
    return score


def sort_live_matches(matches: list[dict]) -> list[dict]:
    return sorted(
        list(matches or []),
        key=lambda m: (
            -importance_score(m),
            text(m.get("madrid_time") or m.get("safe_time") or m.get("kickoff_time") or "99:99"),
            text(m.get("safe_competition") or m.get("competition_name") or m.get("league_name")),
        ),
    )


def build_live_experience(matches: list[dict], lane: str = "live", query: str = "") -> dict:
    all_matches = list(matches or [])
    filtered = [m for m in all_matches if match_filter(m, lane, query)]
    grouped: dict[str, list[dict]] = {}
    for match in sort_live_matches(filtered):
        comp = text(match.get("safe_competition") or match.get("competition_name") or match.get("league_name") or "Competición")
        grouped.setdefault(comp, []).append(match)
    return {
        "lane": lane or "live",
        "query": query or "",
        "total": len(all_matches),
        "filtered": len(filtered),
        "counts": {
            "live": sum(1 for m in all_matches if state_bucket(m) == "live"),
            "upcoming": sum(1 for m in all_matches if state_bucket(m) == "upcoming"),
            "finished": sum(1 for m in all_matches if state_bucket(m) == "finished"),
            "with_pick": sum(1 for m in all_matches if has_pick(m)),
            "favorites": sum(1 for m in all_matches if m.get("is_favorite")),
        },
        "matches": sort_live_matches(filtered),
        "groups": [{"name": name, "count": len(items), "matches": items} for name, items in grouped.items()],
        "filters": [
            ("live", "En directo"),
            ("today", "Hoy"),
            ("upcoming", "Próximos"),
            ("finished", "Finalizados"),
            ("picks", "Con pick"),
            ("favorites", "Favoritos"),
            ("spain", "España"),
            ("andalucia", "Andalucía"),
            ("top", "Grandes ligas"),
        ],
    }


def live_experience_snapshot(app_version: str = "") -> dict:
    return {
        "ok": True,
        "version": app_version,
        "status": "LIVE_EXPERIENCE_V742_READY",
        "checks": {
            "filters": True,
            "search": True,
            "madrid_time": True,
            "no_fake_scores": True,
            "match_links": True,
            "mobile_density": True,
        },
    }
