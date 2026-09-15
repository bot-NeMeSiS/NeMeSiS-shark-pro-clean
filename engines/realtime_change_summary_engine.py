"""Factual differences between canonical snapshots, NOT a provider event stream.

The caller supplies ordered NEMESIS-REALTIME-STATE-V1 states. This boundary
checks that ordering rather than trusting argument position or wall-clock time.
It does not establish a user's last visit, persist data, resolve cross-provider
identity, reclassify Sports Truth, or perform I/O. Coverage is availability,
not a claim about its freshness. Missing evidence remains explicit.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite
import re
from typing import Any

from engines.realtime_state_engine import REALTIME_STATE_CONTRACT
from engines.v935_launch_trust_engine import LIVE_FUTURE_SKEW_SECONDS

CHANGE_SUMMARY_CONTRACT = "NEMESIS-REALTIME-CHANGE-SUMMARY-V1"

_STATUS_LABELS = {
    "UPCOMING": "Programado", "LIVE": "En directo", "HALFTIME": "Descanso",
    "FINISHED": "Finalizado", "RESULT_PENDING": "Resultado pendiente",
    "POSTPONED": "Aplazado", "SUSPENDED": "Suspendido", "CANCELLED": "Cancelado",
    "ABANDONED": "Abandonado", "STALE": "Datos retrasados",
    "INCOMPLETE": "Información incompleta", "ARCHIVED": "Archivado",
}
_CAPABILITY_LABELS = {
    "events": "Eventos", "lineups": "Alineaciones", "stats": "Estadísticas",
    "standings": "Clasificación", "odds": "Cuotas", "injuries": "Bajas",
    "players": "Jugadores",
}
_IDENTITY_FIELDS = ("competition_id", "season", "home_team_id", "away_team_id")
_CLOCK_FIELDS = {"live_updated_at", "provider_updated_at", "last_synced_at"}
_DISPLAY_ONLY_STATES = {"STALE", "INCOMPLETE", "RESULT_PENDING"}


def _text(value: Any, limit: int = 180) -> str:
    if not isinstance(value, str):
        return ""
    return value.replace("\r", " ").replace("\n", " ").strip()[:limit]


def _clock(value: Any) -> datetime | None:
    # Canonical timestamps carry an offset. Never guess one for naive clocks.
    if not isinstance(value, str) or not value or len(value) > 100:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _score(state: dict[str, Any]) -> str:
    values = (state.get("score_home"), state.get("score_away"))
    for value in values:
        if type(value) not in (int, float) or value < 0:
            return ""
        if isinstance(value, float) and not isfinite(value):
            return ""
    return "-".join(str(int(v)) if isinstance(v, float) and v.is_integer() else str(v) for v in values)


def _minute(value: Any) -> str:
    text = _text(value, 24).strip("'’")
    if not re.fullmatch(r"[0-9]{1,3}(?:\+[0-9]{1,2})?", text):
        return ""
    return text if int(text.split("+", 1)[0]) <= 130 else ""


def _coverage_state(state: dict[str, Any], name: str) -> str:
    coverage = state.get("coverage")
    payload = coverage.get(name) if isinstance(coverage, dict) else None
    if not isinstance(payload, dict):
        return "NOT_ESTABLISHED"
    status = _text(payload.get("state"), 40).upper()
    count = payload.get("count")
    if count is not None and (type(count) is not int or count < 0):
        return "NOT_ESTABLISHED"
    if status == "AVAILABLE":
        return status if payload.get("available") is True and payload.get("observed") is True and count != 0 else "NOT_ESTABLISHED"
    if status == "EMPTY_OBSERVED":
        return status if payload.get("available") is False and payload.get("observed") is True and count in (None, 0) else "NOT_ESTABLISHED"
    if status in {"PARTIAL", "STALE", "UNAVAILABLE"} and payload.get("observed") is True:
        return status
    return "NOT_ESTABLISHED"


def _event(code: str, message: str, *, before: Any = None, after: Any = None,
           importance: str = "INFO", capability: str | None = None) -> dict[str, Any]:
    event = dict(code=code, message=message, before=before, after=after,
                 importance=importance, evidence_kind="SNAPSHOT_DIFFERENCE")
    if capability is not None:
        event["capability"] = capability
    return event


def _blocked(fixture_id: str, reason: str, *, same_fixture: bool = False,
             state: str = "NOT_COMPARABLE") -> dict[str, Any]:
    return {
        "contract": CHANGE_SUMMARY_CONTRACT, "fixture_id": fixture_id,
        "same_fixture": same_fixture, "comparable": False,
        "comparison_state": state, "reason": reason, "changed": False,
        "events": [], "suppressed_changes": [], "headline": "No comparable",
        "summary": "No hay identidad y orden temporal suficientes para anunciar cambios.",
    }


def build_factual_change_summary(previous: dict[str, Any] | None,
                                 current: dict[str, Any] | None) -> dict[str, Any]:
    """Describe the same fixture's snapshot differences without inventing events.

    Additive comparison metadata distinguishes no changes from insufficient or
    out-of-order evidence. A score update never means a goal. State expiration
    can still be reported without a new provider response. Evaluation timestamps
    cannot rejuvenate observations. No persistent deduplication is claimed.
    """
    if previous is None:
        return _blocked(_text(current.get("fixture_id"), 100) if isinstance(current, dict) else "", "NO_BASELINE")
    if current is None:
        return _blocked(_text(previous.get("fixture_id"), 100) if isinstance(previous, dict) else "", "NO_CURRENT_STATE")
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return _blocked("", "INVALID_INPUT", state="INVALID_STATE")
    before, after = previous, current
    fixture_id = _text(after.get("fixture_id"), 100)
    same_fixture = bool(fixture_id and before.get("fixture_id") == after.get("fixture_id"))

    def reject(reason: str, state: str = "NOT_COMPARABLE") -> dict[str, Any]:
        return _blocked(fixture_id, reason, same_fixture=same_fixture, state=state)

    if not same_fixture:
        return reject("DIFFERENT_OR_MISSING_FIXTURE")
    if any(s.get("contract") != REALTIME_STATE_CONTRACT for s in (before, after)):
        return reject("CONTRACT_MISMATCH", "INVALID_STATE")
    flags = ("is_live", "is_finished", "is_stale", "status_conflict")
    if any(type(s.get(key)) is not bool for s in (before, after) for key in flags):
        return reject("INVALID_FLAGS", "INVALID_STATE")
    if any(not isinstance(s.get("status_canonical"), str) or s["status_canonical"] not in _STATUS_LABELS for s in (before, after)):
        return reject("INVALID_STATUS", "INVALID_STATE")
    # These IDs are already canonical; display truncation must not join entities.
    if any(before.get(key) not in (None, "") and after.get(key) not in (None, "")
           and before[key] != after[key] for key in _IDENTITY_FIELDS):
        return reject("IDENTITY_CONFLICT")
    if not _text(before.get("provider")) or not _text(after.get("provider")):
        return reject("SOURCE_NOT_ESTABLISHED")
    if before["provider"] != after["provider"]:
        return reject("SOURCE_CHANGED")

    old_eval, new_eval = (_clock(s.get("evaluated_at_madrid")) for s in (before, after))
    if old_eval is None or new_eval is None:
        return reject("EVALUATION_CLOCK_NOT_ESTABLISHED", "INVALID_STATE")
    if new_eval < old_eval:
        return reject("OLDER_EVALUATION", "OUT_OF_ORDER")
    old_observed, new_observed = (_clock(s.get("provider_observed_at")) for s in (before, after))
    for snapshot, observed, evaluated in ((before, old_observed, old_eval), (after, new_observed, new_eval)):
        if observed is not None and snapshot.get("provider_observed_at_source") not in _CLOCK_FIELDS:
            return reject("OBSERVATION_PROVENANCE_NOT_ESTABLISHED", "INVALID_STATE")
        if observed is not None and observed > evaluated + timedelta(seconds=LIVE_FUTURE_SKEW_SECONDS):
            return reject("FUTURE_PROVIDER_OBSERVATION", "INVALID_STATE")
    if old_observed is not None and new_observed is not None and new_observed < old_observed:
        return reject("OLDER_PROVIDER_OBSERVATION", "OUT_OF_ORDER")

    newer_observation = new_observed is not None and (old_observed is None or new_observed > old_observed)
    can_announce = (newer_observation and not after["is_stale"] and not after["status_conflict"]
                    and after.get("freshness_state") in {"FRESH", "OBSERVED"})
    events: list[dict[str, Any]] = []
    suppressed: list[str] = []
    old_status, new_status = before["status_canonical"], after["status_canonical"]
    if old_status != new_status:
        if can_announce or new_status in _DISPLAY_ONLY_STATES:
            events.append(_event("STATUS_CHANGE", f"Estado actualizado: {_STATUS_LABELS[old_status]} → {_STATUS_LABELS[new_status]}.",
                before=old_status, after=new_status, importance="HIGH"))
        else:
            suppressed.append("status")

    old_score, new_score = _score(before), _score(after)
    if old_score != new_score:
        if not new_score and old_score:
            events.append(_event("SCORE_UNAVAILABLE", f"Marcador completo no disponible; el último registrado era {old_score}.",
                before=old_score, after=None))
        elif can_announce:
            events.append(_event("SCORE_UPDATE", f"Marcador actualizado: {old_score or 'sin marcador'} → {new_score}.",
                before=old_score or None, after=new_score, importance="HIGH"))
        else:
            suppressed.append("score")

    old_minute, new_minute = _minute(before.get("minute")), _minute(after.get("minute"))
    if old_minute != new_minute and new_minute:
        if can_announce and after["is_live"] and new_status in {"LIVE", "HALFTIME"}:
            events.append(_event("MINUTE_UPDATE", f"Minuto actualizado: {new_minute}'.", before=old_minute or None, after=new_minute))
        elif after["is_live"]:
            suppressed.append("minute")

    old_fresh, new_fresh = (_text(s.get("freshness_state"), 40).upper() for s in (before, after))
    if old_fresh != new_fresh:
        if new_fresh == "STALE":
            message = "Los datos en directo han perdido frescura."
        elif old_fresh == "STALE" and new_fresh == "FRESH" and can_announce and after["is_live"]:
            message = "La fuente deportiva vuelve a tener datos recientes."
        elif new_fresh == "OBSERVED":
            message = "Hay una observación registrada; su frescura en directo no está certificada."
        elif new_fresh == "NOT_ESTABLISHED":
            message = "La frescura de los datos ya no está establecida."
        else:
            message = "La evaluación de frescura ha cambiado."
        events.append(_event("FRESHNESS_CHANGE", message, before=old_fresh or None, after=new_fresh or None,
            importance="HIGH" if new_fresh == "STALE" else "INFO"))

    if before["status_conflict"] != after["status_conflict"]:
        if after["status_conflict"]:
            events.append(_event("STATUS_CONFLICT", "Se ha detectado un conflicto entre señales deportivas.",
                before=False, after=True, importance="HIGH"))
        elif can_announce:
            events.append(_event("STATUS_CONFLICT_RESOLVED", "El conflicto entre señales deportivas ya no está presente.",
                before=True, after=False))
        else:
            suppressed.append("conflict_resolution")

    # Availability and LIVE freshness are independent: historical standings may
    # remain available while the match feed is stale. Never call them fresh here.
    for name, label in _CAPABILITY_LABELS.items():
        old_state, new_state = _coverage_state(before, name), _coverage_state(after, name)
        if old_state == new_state:
            continue
        if new_state == "AVAILABLE":
            code, message = "CAPABILITY_AVAILABLE", f"{label} disponibles."
        elif old_state == "AVAILABLE":
            code, message = {
                "EMPTY_OBSERVED": ("CAPABILITY_EMPTY", f"{label}: la observación disponible está vacía."),
                "PARTIAL": ("CAPABILITY_PARTIAL", f"{label}: cobertura parcial."),
                "STALE": ("CAPABILITY_STALE", f"{label}: datos retrasados."),
            }.get(new_state, ("CAPABILITY_LOST", f"{label}: disponibilidad ya no confirmada."))
        else:
            continue
        events.append(_event(code, message, before=old_state, after=new_state, capability=name))

    changed = bool(events)
    comparison_state = "PARTIAL" if changed and suppressed else "INSUFFICIENT_EVIDENCE" if suppressed else "COMPARABLE"
    headline = (f"{len(events)} cambio{'s' if len(events) != 1 else ''} desde la última revisión" if changed
                else "Cambios sin evidencia suficiente" if suppressed else "Sin cambios relevantes")
    summary = (" ".join(event["message"] for event in events[:4]) if changed
               else "Hay diferencias, pero falta una observación nueva y fiable para anunciarlas." if suppressed
               else "No hay diferencias factuales nuevas entre ambos estados.")
    return {
        "contract": CHANGE_SUMMARY_CONTRACT, "fixture_id": fixture_id,
        "same_fixture": True, "comparable": True, "comparison_state": comparison_state,
        "reason": "SPORTING_CHANGES_WITHHELD" if suppressed else "",
        "changed": changed, "events": events, "suppressed_changes": suppressed,
        "headline": headline, "summary": summary,
    }
