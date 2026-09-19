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
from engines.v935_launch_trust_engine import get_match_source, madrid_now


# Presentation of the canonical decision, NOT another lifecycle classifier.
_STATUS_LABELS = {
    "LIVE": "En directo", "HALFTIME": "Descanso", "FINISHED": "Finalizado",
    "ARCHIVED": "Finalizado", "RESULT_PENDING": "Resultado pendiente",
    "POSTPONED": "Aplazado", "SUSPENDED": "Suspendido", "CANCELLED": "Cancelado",
    "ABANDONED": "Abandonado", "STALE": "Datos retrasados",
    "INCOMPLETE": "Estado pendiente", "UPCOMING": "Próximo",
}


def build_live_surface_state(match: dict[str, Any] | None, now: datetime | None = None) -> dict[str, Any]:
    """Return the current LIVE card plus the canonical Real-Time State.

    Existing card fields remain available for templates. Canonical fields are
    additive and intended to become the shared contract for Home/Live/Match.
    """
    evaluated_at = madrid_now(now)
    source = deepcopy(match or {})
    normalized = normalize_live_match(source)
    # Preserve an explicit numeric zero lost by the legacy `or` fallback.
    # Absent values still permit the existing nested-provider normalization.
    if "minute" in source and source["minute"] not in (None, ""):
        normalized["minute"] = source["minute"]
    # Legacy normalization adapts identity/score shapes, but also aliases clocks
    # and provides a default source. Restore actual provenance before projection.
    for field in ("live_updated_at", "provider_updated_at", "last_synced_at"):
        normalized.pop(field, None)
        if field in source:
            normalized[field] = source[field]
    normalized["provider"] = get_match_source(source)
    card = build_live_card_payload(normalized)
    realtime = build_realtime_match_state(normalized, now=evaluated_at)
    status = realtime["status_canonical"]
    status_label = realtime.get('period_label') or _STATUS_LABELS.get(status, "Estado pendiente")
    minute = realtime["minute"]
    minute_label = f"{minute}'" if minute is not None else status_label
    if not realtime["is_live"]:
        minute_label = ""
    home, away = realtime["score_home"], realtime["score_away"]
    score_label = f"{home}-{away}" if home is not None and away is not None else (
        "Resultado pendiente" if home is not None or away is not None or status in
        {"LIVE", "HALFTIME", "FINISHED", "ARCHIVED", "RESULT_PENDING", "STALE"} else "VS")
    if realtime["status_conflict"]:
        data_state = "Señales deportivas en conflicto"
    elif realtime["is_stale"]:
        data_state = "Datos retrasados"
    elif realtime["confidence_state"] == "NOT_ESTABLISHED":
        data_state = "Frescura no establecida"
    elif realtime["is_live"]:
        data_state = "Datos live reales"
    else:
        data_state = "Datos observados; frescura en directo no certificada"
    # Every temporal/score legacy field is replaced together from this ONE
    # projection. The default clock used internally by old helpers cannot leak.
    card.update({
        "status_label": status_label, "minute_label": minute_label,
        "score_label": score_label, "is_pending": score_label in {"VS", "Resultado pendiente"},
        "is_live": realtime["is_live"], "is_finished": realtime["is_finished"],
        "is_stale": realtime["is_stale"], "stale_reason": realtime["stale_reason"],
        "status_conflict": realtime["status_conflict"], "provider": realtime["provider"],
        "live_age_seconds": realtime["freshness_seconds"], "data_state": data_state,
        "status_contract": realtime["sports_truth_contract"],
    })

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
    evaluated_at = madrid_now(now)
    cards = [build_live_surface_state(match, now=evaluated_at) for match in (matches or [])]
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
