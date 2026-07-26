"""Canonical Match Center context for MATCH-CENTER-LIFECYCLE-STORY-V1.

The builder is deliberately pure: callers provide data already loaded from the
local store and this module performs no database, network, session or provider
work. That keeps every Match Center component on one factual snapshot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from engines.match_live_story_engine import build_match_live_story


MATCH_CENTER_CONTRACT = "MATCH-CENTER-LIFECYCLE-STORY-V1"
MATCH_CENTER_FOUNDATION = "V944_MATCH_CENTER_FOUNDATION_PHASE_1_FINAL"

CANONICAL_COMPONENT_STATES = (
    "loading",
    "ready",
    "partial",
    "finished",
    "error",
    "offline",
    "unknown",
)

MATCH_CENTER_COMPONENTS = (
    "MatchHeader",
    "ScoreWidget",
    "MatchStory",
    "Timeline",
    "StatsPanel",
    "SharkPanel",
    "TelegramPanel",
    "BankrollPanel",
    "CompetitionPanel",
    "QuickActions",
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _present(value: Any) -> bool:
    return value not in (None, "")


def _score(match: Mapping[str, Any], display: Mapping[str, Any]) -> dict[str, Any]:
    home = match.get("home_score")
    away = match.get("away_score")
    confirmed = _present(home) and _present(away)
    label = _text(display.get("client_score_label"))
    if confirmed:
        label = f"{home}-{away}"
    elif label.lower() in {"", "-", "vs", "pendiente"}:
        label = "VS"
    return {
        "home": home if confirmed else None,
        "away": away if confirmed else None,
        "label": label,
        "confirmed": confirmed,
    }


def _lifecycle(match: Mapping[str, Any], detail: Mapping[str, Any]) -> dict[str, Any]:
    status_info = _mapping(match.get("status_info"))
    live_depth = _mapping(match.get("live_depth") or detail.get("state"))
    key = _text(
        match.get("v935_lifecycle")
        or status_info.get("key")
        or live_depth.get("state")
        or match.get("status")
    ).upper()
    label = _text(
        status_info.get("label")
        or live_depth.get("label")
        or match.get("client_status_label")
        or match.get("status")
    )
    is_finished = bool(status_info.get("is_finished")) or key in {
        "FT",
        "FINISHED",
        "FINAL",
        "FINALIZADO",
    }
    is_live = bool(status_info.get("is_live")) or key in {
        "LIVE",
        "HT",
        "1H",
        "2H",
        "EN DIRECTO",
    }
    is_stale = bool(
        match.get("is_stale")
        or match.get("stale")
        or _mapping(match.get("v935_freshness")).get("is_stale")
    )
    return {
        "key": key or "UNKNOWN",
        "label": label or "Estado pendiente",
        "is_finished": is_finished,
        "is_live": is_live and not is_finished,
        "is_stale": is_stale,
        "minute": match.get("minute") or live_depth.get("minute"),
    }


def _shell_state(
    match: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    *,
    offline: bool,
) -> str:
    if offline:
        return "offline"
    if lifecycle.get("is_finished"):
        return "finished"
    if lifecycle.get("is_stale"):
        return "partial"
    identity_complete = all(
        _text(value)
        for value in (
            match.get("id"),
            match.get("home_team"),
            match.get("away_team"),
        )
    )
    if identity_complete and lifecycle.get("key") != "UNKNOWN":
        return "ready"
    if identity_complete:
        return "partial"
    return "unknown"


def _component(state: str, message: str, *, available: bool) -> dict[str, Any]:
    canonical = state if state in CANONICAL_COMPONENT_STATES else "unknown"
    return {
        "state": canonical,
        "message": message,
        "available": bool(available),
    }


def _story(
    match: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    score: Mapping[str, Any],
    event_summary: Mapping[str, Any],
) -> dict[str, str]:
    home = _text(match.get("home_team")) or "Equipo local"
    away = _text(match.get("away_team")) or "Equipo visitante"
    latest = _mapping(event_summary.get("latest"))
    latest_title = _text(latest.get("title") or latest.get("detail"))

    if lifecycle.get("is_finished"):
        if score.get("confirmed"):
            summary = f"{home} y {away} finalizaron con marcador {score.get('label')}."
        else:
            summary = (
                "El partido figura como finalizado, pero el resultado confirmado "
                "todavía no está disponible."
            )
        phase = "Cierre del partido"
    elif lifecycle.get("is_live"):
        summary = f"{home} y {away} están disputando el partido."
        if latest_title:
            summary += f" Ultimo hecho disponible: {latest_title}."
        phase = "Partido en curso"
    elif lifecycle.get("is_stale"):
        summary = (
            "La ultima lectura se conserva como contexto, pero no se presenta "
            "como informacion actual."
        )
        phase = "Actualizacion pendiente"
    elif lifecycle.get("key") != "UNKNOWN":
        summary = f"{home} y {away} tienen un encuentro programado."
        phase = "Antes del partido"
    else:
        summary = (
            "Se muestran unicamente los datos confirmados mientras se completa "
            "el estado del partido."
        )
        phase = "Cobertura parcial"
    return {"phase": phase, "summary": summary}


@dataclass(frozen=True)
class MatchContext:
    contract: str
    foundation: str
    state: str
    match: dict[str, Any]
    lifecycle: dict[str, Any]
    competition: dict[str, Any]
    teams: dict[str, Any]
    score: dict[str, Any]
    madrid_time: dict[str, Any]
    favorite: bool
    picks: dict[str, Any]
    event_summary: dict[str, Any]
    statistics: dict[str, Any]
    story: dict[str, Any]
    live_story: dict[str, Any]
    components: dict[str, dict[str, Any]]
    evidence: dict[str, Any]
    limitations: list[str]
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_match_context(
    detail: Mapping[str, Any] | None,
    *,
    madrid_context: Mapping[str, Any] | None = None,
    live_context: Mapping[str, Any] | None = None,
    offline: bool = False,
) -> dict[str, Any]:
    """Build one immutable factual snapshot for every Match Center component."""

    detail_data = _mapping(detail)
    match = _mapping(detail_data.get("match"))
    display = _mapping(madrid_context)
    live = _mapping(live_context or detail_data.get("api_football_live_tracker"))
    lifecycle = _lifecycle(match, detail_data)
    score = _score(match, display)
    shell_state = _shell_state(match, lifecycle, offline=offline)

    raw_timeline = _items(live.get("events")) or _items(
        detail_data.get("timeline") or detail_data.get("events")
    )
    live_story = build_match_live_story(match, raw_timeline)
    timeline = _items(live_story.get("timeline"))
    latest_event = _mapping(live_story.get("latest_event"))
    event_summary = {
        "available": bool(timeline),
        "count": len(timeline),
        "latest": latest_event,
        "items": timeline,
        "raw_count": len(raw_timeline),
        "excluded_without_evidence": max(0, len(raw_timeline) - len(timeline)),
    }

    raw_stats = _mapping(detail_data.get("statistics"))
    live_state = _mapping(detail_data.get("state"))
    stats_available = bool(
        _mapping(live_state.get("shark_momentum")).get("stats_available")
    )
    statistics = {
        "available": stats_available,
        "item_count": len(_items(raw_stats.get("items"))) if stats_available else 0,
        "status": "available" if stats_available else "not_available",
    }

    related_picks = _items(detail_data.get("related_picks"))
    picks = {
        "available": bool(related_picks),
        "count": len(related_picks),
        "items": related_picks,
    }

    home_identity = _mapping(match.get("home_identity"))
    away_identity = _mapping(match.get("away_identity"))
    teams = {
        "home": {
            "id": match.get("home_team_id"),
            "name": _text(match.get("home_team")) or "Equipo local pendiente",
            "logo": home_identity.get("logo")
            or home_identity.get("crest_url")
            or match.get("home_logo")
            or match.get("home_crest"),
        },
        "away": {
            "id": match.get("away_team_id"),
            "name": _text(match.get("away_team")) or "Equipo visitante pendiente",
            "logo": away_identity.get("logo")
            or away_identity.get("crest_url")
            or match.get("away_logo")
            or match.get("away_crest"),
        },
    }

    competition_name = _text(
        display.get("client_competition")
        or match.get("competition_name")
        or match.get("league_name")
    )
    competition = {
        "id": match.get("competition_id") or match.get("competition_key"),
        "name": competition_name or "Competición pendiente",
        "round": _text(match.get("round") or match.get("stage")),
        "country": _text(match.get("country")),
        "available": bool(competition_name),
    }

    madrid_time = {
        "label": _text(
            display.get("client_full_datetime_label")
            or display.get("client_datetime_label")
            or display.get("client_time_label")
        )
        or "Hora Madrid pendiente",
        "date": _text(display.get("client_date_label") or match.get("match_date")),
        "time": _text(display.get("client_time_label") or match.get("kickoff_time")),
        "iso": match.get("kickoff_iso") or match.get("commence_time"),
    }

    limitations: list[str] = []
    if not competition["available"]:
        limitations.append("Competición no confirmada.")
    if madrid_time["label"] == "Hora Madrid pendiente":
        limitations.append("Hora Madrid no confirmada.")
    if not event_summary["available"]:
        limitations.append("Sin eventos confirmados.")
    if not statistics["available"]:
        limitations.append("Sin estadísticas confirmadas.")
    if lifecycle.get("is_stale"):
        limitations.append("La última lectura deportiva está desactualizada.")

    story = _story(match, lifecycle, score, event_summary)
    header_state = shell_state if shell_state in {"ready", "finished"} else "partial"
    score_state = (
        "finished"
        if lifecycle.get("is_finished")
        else "ready"
        if score.get("confirmed") or lifecycle.get("key") != "UNKNOWN"
        else "unknown"
    )
    timeline_state = "ready" if event_summary["available"] else "partial"
    stats_state = "ready" if statistics["available"] else "partial"

    components = {
        "MatchHeader": _component(
            header_state,
            "Identidad y contexto confirmados."
            if header_state in {"ready", "finished"}
            else "Se muestran los datos de identidad disponibles.",
            available=bool(match),
        ),
        "ScoreWidget": _component(
            score_state,
            "Marcador confirmado."
            if score.get("confirmed")
            else "El marcador no está disponible todavía.",
            available=True,
        ),
        "MatchStory": _component(
            shell_state,
            "Historia construida solo con el estado disponible.",
            available=True,
        ),
        "Timeline": _component(
            timeline_state,
            "Cronología disponible."
            if event_summary["available"]
            else "No disponible todavía.",
            available=event_summary["available"],
        ),
        "StatsPanel": _component(
            stats_state,
            "Cobertura estadística detectada."
            if statistics["available"]
            else "No disponible todavía.",
            available=statistics["available"],
        ),
        "SharkPanel": _component(
            "partial",
            "La integración completa de SHARK llegará en una fase posterior.",
            available=False,
        ),
        "TelegramPanel": _component(
            "partial",
            "No disponible todavía.",
            available=False,
        ),
        "BankrollPanel": _component(
            "partial",
            "No disponible todavía.",
            available=False,
        ),
        "CompetitionPanel": _component(
            "ready" if competition["available"] else "partial",
            "Contexto de competición disponible."
            if competition["available"]
            else "Competición pendiente de confirmar.",
            available=competition["available"],
        ),
        "QuickActions": _component(
            "ready",
            "Acciones seguras de continuidad.",
            available=True,
        ),
    }

    context = MatchContext(
        contract=MATCH_CENTER_CONTRACT,
        foundation=MATCH_CENTER_FOUNDATION,
        state=shell_state,
        match=match,
        lifecycle=lifecycle,
        competition=competition,
        teams=teams,
        score=score,
        madrid_time=madrid_time,
        favorite=bool(detail_data.get("favorite") or match.get("is_favorite")),
        picks=picks,
        event_summary=event_summary,
        statistics=statistics,
        story=story,
        live_story=live_story,
        components=components,
        evidence={
            "source": _text(match.get("source") or match.get("v935_source"))
            or "Fuente no identificada",
            "updated_at": match.get("updated_at"),
            "certification_state": _text(match.get("certification_state"))
            or ("PARTIAL" if limitations else "AVAILABLE"),
            "match_id": match.get("id") or detail_data.get("id"),
        },
        limitations=limitations,
        diagnostics={
            "builder_database_queries": 0,
            "builder_database_writes": 0,
            "external_calls": 0,
            "single_snapshot": True,
            "component_contracts": list(MATCH_CENTER_COMPONENTS),
            "canonical_states": list(CANONICAL_COMPONENT_STATES),
        },
    )
    return context.to_dict()
