"""Factual 'what changed' summaries over canonical real-time states.

No persistence, provider I/O, user data, or betting inference lives here. The
module receives already-normalized `NEMESIS-REALTIME-STATE-V1` snapshots and
reports only directly observable differences.
"""
from __future__ import annotations

from typing import Any

from engines.realtime_state_engine import compare_realtime_match_state

CHANGE_SUMMARY_CONTRACT = "NEMESIS-REALTIME-CHANGE-SUMMARY-V1"

_STATUS_LABELS = {
    "UPCOMING": "Programado",
    "LIVE": "En directo",
    "HALFTIME": "Descanso",
    "FINISHED": "Finalizado",
    "RESULT_PENDING": "Resultado pendiente",
    "POSTPONED": "Aplazado",
    "SUSPENDED": "Suspendido",
    "CANCELLED": "Cancelado",
    "ABANDONED": "Abandonado",
    "STALE": "Datos retrasados",
    "INCOMPLETE": "Información incompleta",
    "ARCHIVED": "Archivado",
}

_CAPABILITY_LABELS = {
    "events": "Eventos",
    "lineups": "Alineaciones",
    "stats": "Estadísticas",
    "standings": "Clasificación",
    "odds": "Cuotas",
    "injuries": "Bajas",
    "players": "Jugadores",
}


def _text(value: Any, limit: int = 180) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _score(state: dict[str, Any]) -> str:
    home = state.get("score_home")
    away = state.get("score_away")
    if home is None or away is None:
        return ""
    return f"{home}-{away}"


def _status_label(value: Any) -> str:
    key = _text(value, 40).upper()
    return _STATUS_LABELS.get(key, key or "Estado desconocido")


def _coverage_state(state: dict[str, Any], name: str) -> str:
    coverage = state.get("coverage")
    if not isinstance(coverage, dict):
        return "NOT_ESTABLISHED"
    payload = coverage.get(name)
    if not isinstance(payload, dict):
        return "NOT_ESTABLISHED"
    return _text(payload.get("state"), 40).upper() or "NOT_ESTABLISHED"


def _event(code: str, message: str, *, before: Any = None, after: Any = None, importance: str = "INFO") -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "before": before,
        "after": after,
        "importance": importance,
    }


def build_factual_change_summary(previous: dict[str, Any] | None, current: dict[str, Any] | None) -> dict[str, Any]:
    """Describe observable changes between two states of the same fixture.

    Score changes are deliberately called score updates, not goals: without an
    observed event stream, a score correction and a goal cannot be distinguished.
    """
    before = dict(previous or {})
    after = dict(current or {})
    diff = compare_realtime_match_state(before, after)
    fixture_id = _text(diff.get("fixture_id"), 100)
    events: list[dict[str, Any]] = []

    if not diff.get("same_fixture"):
        return {
            "contract": CHANGE_SUMMARY_CONTRACT,
            "fixture_id": fixture_id,
            "same_fixture": False,
            "changed": False,
            "events": [],
            "headline": "No comparable",
            "summary": "Los estados no pertenecen al mismo partido.",
        }

    old_status = _text(before.get("status_canonical"), 40).upper()
    new_status = _text(after.get("status_canonical"), 40).upper()
    if old_status != new_status:
        events.append(
            _event(
                "STATUS_CHANGE",
                f"Estado actualizado: {_status_label(old_status)} → {_status_label(new_status)}.",
                before=old_status or None,
                after=new_status or None,
                importance="HIGH" if new_status in {"LIVE", "FINISHED", "SUSPENDED", "POSTPONED", "CANCELLED", "ABANDONED", "STALE"} else "INFO",
            )
        )

    old_score = _score(before)
    new_score = _score(after)
    if old_score != new_score and new_score:
        events.append(
            _event(
                "SCORE_UPDATE",
                f"Marcador actualizado: {old_score or 'sin marcador'} → {new_score}.",
                before=old_score or None,
                after=new_score,
                importance="HIGH",
            )
        )

    old_minute = _text(before.get("minute"), 24)
    new_minute = _text(after.get("minute"), 24)
    if old_minute != new_minute and new_minute and bool(after.get("is_live")):
        events.append(
            _event(
                "MINUTE_UPDATE",
                f"Minuto actualizado: {new_minute}'.",
                before=old_minute or None,
                after=new_minute,
            )
        )

    old_fresh = _text(before.get("freshness_state"), 40).upper()
    new_fresh = _text(after.get("freshness_state"), 40).upper()
    if old_fresh != new_fresh:
        if new_fresh == "STALE":
            message = "Los datos en directo han perdido frescura."
            importance = "HIGH"
        elif old_fresh == "STALE" and new_fresh in {"FRESH", "OBSERVED"}:
            message = "La fuente deportiva vuelve a tener datos recientes."
            importance = "INFO"
        else:
            message = f"Frescura actualizada: {old_fresh or 'NOT_ESTABLISHED'} → {new_fresh or 'NOT_ESTABLISHED'}."
            importance = "INFO"
        events.append(_event("FRESHNESS_CHANGE", message, before=old_fresh or None, after=new_fresh or None, importance=importance))

    old_conflict = bool(before.get("status_conflict"))
    new_conflict = bool(after.get("status_conflict"))
    if old_conflict != new_conflict:
        events.append(
            _event(
                "STATUS_CONFLICT" if new_conflict else "STATUS_CONFLICT_RESOLVED",
                "Se ha detectado un conflicto entre señales deportivas." if new_conflict else "El conflicto entre señales deportivas ya no está presente.",
                before=old_conflict,
                after=new_conflict,
                importance="HIGH" if new_conflict else "INFO",
            )
        )

    for name, label in _CAPABILITY_LABELS.items():
        old_state = _coverage_state(before, name)
        new_state = _coverage_state(after, name)
        if old_state == new_state:
            continue
        if new_state == "AVAILABLE":
            events.append(_event("CAPABILITY_AVAILABLE", f"{label} disponibles.", before=old_state, after=new_state, importance="INFO"))
        elif old_state == "AVAILABLE" and new_state in {"UNAVAILABLE", "NOT_ESTABLISHED"}:
            events.append(_event("CAPABILITY_LOST", f"{label}: disponibilidad ya no confirmada.", before=old_state, after=new_state, importance="INFO"))

    changed = bool(events)
    if not changed:
        headline = "Sin cambios relevantes"
        summary = "No hay diferencias factuales nuevas entre ambos estados."
    else:
        headline = f"{len(events)} cambio{'s' if len(events) != 1 else ''} desde la última revisión"
        summary = " ".join(event["message"] for event in events[:4])

    return {
        "contract": CHANGE_SUMMARY_CONTRACT,
        "fixture_id": fixture_id,
        "same_fixture": True,
        "changed": changed,
        "events": events,
        "headline": headline,
        "summary": summary,
    }
