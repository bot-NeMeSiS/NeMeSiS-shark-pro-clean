"""Canonical public navigation for Sports Core entities.

This module owns URL construction only. Entity identity still belongs to the
Sports Domain Model / historical memory. Keeping URL generation here prevents
Team Center, Match Center, Competition Center and shared cards from inventing
different public destinations for the same entity.

The module is pure: no database, Flask, provider or network access.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote


PUBLIC_ENTITY_ROUTES = {
    "team": "/team",
    "player": "/player",
    "competition": "/competition",
    "match": "/match",
}

PREPARED_CONTEXTUAL_ENTITIES = frozenset({"stadium", "referee", "coach"})


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def public_entity_route_id(entity_type: Any, identifier: Any = "", label: Any = "") -> str:
    """Return the public route identifier without merging or guessing identities.

    Team pages historically resolve aliases/names, so a verified display label is
    preferred there. Player/competition canonical ids may be namespaced; only
    an explicit namespace suffix for that same entity type is removed.
    """
    kind = _text(entity_type, 40).casefold()
    identity = _text(identifier, 200)
    display = _text(label, 200)

    if kind == "team":
        # A provider-scoped identifier keeps homonymous teams navigable without
        # guessing from a display name. Legacy name routes remain the fallback.
        parts = identity.split(":", 2)
        provider = parts[0].casefold().replace("-", "_") if len(parts) == 3 else ""
        if len(parts) == 3 and parts[1].casefold() == "team" and provider in {"sportsdb", "api_football"} and parts[2]:
            return f"{provider}:team:{parts[2]}"
        return display or identity

    if kind in {"player", "competition"} and identity:
        marker = f":{kind}:"
        if marker in identity:
            suffix = identity.rsplit(marker, 1)[-1]
            if suffix:
                return suffix

    if kind == "match":
        return identity

    return identity or display


def entity_href(
    entity_type: Any,
    identifier: Any = "",
    label: Any = "",
    *,
    allow_label_fallback: bool = True,
) -> str:
    """Build the canonical public href for a supported entity.

    Stadium/referee/coach are intentionally not linked yet: their contracts are
    prepared in sports history, but a public route must exist before emitting a
    clickable URL. This fails closed instead of creating broken links.
    """
    kind = _text(entity_type, 40).casefold()
    prefix = PUBLIC_ENTITY_ROUTES.get(kind)
    if not prefix:
        return ""

    route_id = public_entity_route_id(kind, identifier, label if allow_label_fallback else "")
    if not route_id:
        return ""
    route_parts = route_id.split(":", 2)
    safe = ":" if (
        kind == "team"
        and len(route_parts) == 3
        and route_parts[0] in {"sportsdb", "api_football"}
        and route_parts[1] == "team"
    ) else ""
    return f"{prefix}/{quote(route_id, safe=safe)}"


def entity_navigation_contract(
    entity_type: Any,
    identifier: Any = "",
    label: Any = "",
) -> dict[str, Any]:
    kind = _text(entity_type, 40).casefold()
    href = entity_href(kind, identifier, label)
    return {
        "contract": "SPORTS-ENTITY-NAVIGATION-V1",
        "kind": kind,
        "identifier": _text(identifier, 200) or None,
        "label": _text(label, 200) or None,
        "href": href or None,
        "public": bool(href),
        "state": "ACTIVE" if href else "PREPARED" if kind in PREPARED_CONTEXTUAL_ENTITIES else "UNAVAILABLE",
    }
