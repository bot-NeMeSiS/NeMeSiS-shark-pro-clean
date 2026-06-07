"""Picks Intelligence helpers for NeMeSiS SHARK PRO.

This module intentionally contains pure helpers so the Flask app can keep
SQLite/session ownership in app.py while tests can import the pick rules.
"""

VALID_PICK_STATUSES = {"draft", "published", "archived", "won", "lost", "void", "pending"}
VALID_MEMBERSHIPS = {"FREE": 0, "PRO": 1, "ELITE": 2, "ADMIN": 3}


def normalize_pick_status(value: str | None) -> str:
    value = str(value or "draft").strip().lower()
    aliases = {
        "pending": "published",
        "publicado": "published",
        "pendiente": "published",
        "borrador": "draft",
        "archivado": "archived",
        "ganado": "won",
        "perdido": "lost",
        "nulo": "void",
    }
    return aliases.get(value, value if value in VALID_PICK_STATUSES else "draft")


def membership_rank(plan: str | None) -> int:
    return VALID_MEMBERSHIPS.get(str(plan or "FREE").strip().upper(), 0)


def membership_allows(user_plan: str | None, required_plan: str | None) -> bool:
    return membership_rank(user_plan) >= membership_rank(required_plan)


def combi_risk_from_picks(picks: list[dict]) -> str:
    if not picks:
        return "EMPTY"
    avg_confidence = sum(int(p.get("confidence") or 50) for p in picks) / len(picks)
    legs = len(picks)
    if legs <= 2 and avg_confidence >= 70:
        return "BAJO"
    if legs <= 4 and avg_confidence >= 58:
        return "MEDIO"
    return "ALTO"
