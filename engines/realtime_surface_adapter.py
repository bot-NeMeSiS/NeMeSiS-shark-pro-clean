"""Read-only adapters that expose Real-Time State to existing UI payloads.

The adapter keeps legacy payload keys intact while attaching a canonical
`realtime_state`. It performs no I/O and does not alter provider or lifecycle
logic.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from engines.live_match_experience_engine import build_live_card_payload, normalize_live_match
from engines.realtime_state_engine import build_realtime_match_state


def build_live_surface_state(match: dict[str, Any] | None, now: datetime | None = None) -> dict[str, Any]:
    """Return the current LIVE card plus the canonical Real-Time State.

    Existing card fields remain available for templates. Canonical fields are
    additive and intended to become the shared contract for Home/Live/Match.
    """
    source = deepcopy(match or {})
    normalized = normalize_live_match(source)
    card = build_live_card_payload(normalized)
    realtime = build_realtime_match_state(normalized, now=now)

    # Fail closed if a legacy card ever disagrees with the canonical contract.
    card["is_live"] = bool(realtime["is_live"])
    card["is_finished"] = bool(realtime["is_finished"])
    if realtime["is_stale"]:
        card["data_state"] = "Datos retrasados"
        card["minute_label"] = ""
    elif realtime["is_live"]:
        card["data_state"] = "Datos live reales"
    elif realtime["freshness_state"] == "NOT_ESTABLISHED":
        card["data_state"] = "Frescura no establecida"

    card.update(
        {
            "realtime_contract": realtime["contract"],
            "realtime_state": realtime,
            "status_canonical": realtime["status_canonical"],
            "freshness_state": realtime["freshness_state"],
            "freshness_seconds": realtime["freshness_seconds"],
            "confidence_state": realtime["confidence_state"],
            "provider_observed_at": realtime["provider_observed_at"],
            "coverage": deepcopy(realtime["coverage"]),
        }
    )
    return card


def build_live_surface_collection(matches: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None, now: datetime | None = None) -> dict[str, Any]:
    cards = [build_live_surface_state(match, now=now) for match in (matches or [])]
    public_live = [card for card in cards if card["is_live"]]
    return {
        "contract": "NEMESIS-LIVE-SURFACE-V1",
        "cards": cards,
        "live_cards": public_live,
        "counts": {
            "input": len(cards),
            "live": len(public_live),
            "stale": sum(1 for card in cards if card["realtime_state"]["is_stale"]),
            "conflicted": sum(1 for card in cards if card["realtime_state"]["status_conflict"]),
        },
    }
