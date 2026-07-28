"""Evidence-backed SHARK Intelligence Platform.

This module is a read-only orchestration layer. It consumes already-built
Sports Core, Sports Knowledge, Sports Graph, Match Intelligence, Team Center
and Competition Center snapshots. It does not query databases, call providers,
send Telegram messages, write files, charge Stripe, run generative AI or invent
missing sports facts.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from engines.match_intelligence_engine import (
    MATCH_INTELLIGENCE_CONTRACT,
    build_match_intelligence_consumer_view,
)
from engines.sports_domain_model_engine import SPORTS_DOMAIN_MODEL_CONTRACT
from engines.sports_graph_foundation_engine import SPORTS_GRAPH_FOUNDATION_CONTRACT
from engines.sports_knowledge_layer_engine import SPORTS_KNOWLEDGE_LAYER_CONTRACT


SHARK_INTELLIGENCE_PLATFORM_CONTRACT = "SHARK-INTELLIGENCE-PLATFORM-V1"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _state(value: Any) -> str:
    candidate = _text(value, 40).upper()
    allowed = {
        "VERIFIED",
        "PARTIALLY_VERIFIED",
        "NOT_CERTIFIED",
        "NOT_CONFIGURED",
        "STALE",
        "BLOCKED_BY_ACCESS",
        "HYPOTHESIS",
        "INSUFFICIENT_DATA",
        "REQUIRES_REVIEW",
    }
    return candidate if candidate in allowed else "REQUIRES_REVIEW"


def _first_present(*values: Any) -> str:
    for value in values:
        text = _text(value, 180)
        if text:
            return text
    return ""


def _freshness(value: Any, fallback: Any = "") -> dict[str, Any]:
    data = _mapping(value)
    if data:
        label = _first_present(data.get("label"), data.get("state"), data.get("status"), "No disponible")
        return {
            "label": label,
            "state": _text(data.get("state") or data.get("status") or "unknown", 60),
            "source_timestamp": _text(data.get("source_timestamp") or data.get("updated_at") or fallback, 100),
            "limitations": list(data.get("limitations") or []),
        }
    text = _text(value or fallback, 120)
    return {
        "label": text or "No disponible",
        "state": "unknown" if not text else "provided",
        "source_timestamp": text,
        "limitations": [] if text else ["Freshness was not supplied by the upstream snapshot."],
    }


def _evidence_labels(evidence: Iterable[Mapping[str, Any]] | None, limit: int = 6) -> list[str]:
    labels: list[str] = []
    for item in _items(evidence)[:limit]:
        data = _mapping(item.get("data"))
        label = _first_present(
            item.get("label"),
            data.get("label"),
            item.get("kind"),
            item.get("source"),
            item.get("id"),
            "Evidencia deportiva",
        )
        if label and label not in labels:
            labels.append(label)
    return labels


def _quality(state: Any, source: Any = "", evidence_count: int = 0) -> dict[str, Any]:
    normalized = _state(state)
    if normalized == "VERIFIED":
        label = "Evidencia confirmada"
    elif normalized == "PARTIALLY_VERIFIED":
        label = "Evidencia parcial"
    elif normalized == "STALE":
        label = "Evidencia desactualizada"
    elif normalized == "INSUFFICIENT_DATA":
        label = "Datos insuficientes"
    elif normalized == "NOT_CONFIGURED":
        label = "No configurado"
    else:
        label = "Requiere revision"
    return {
        "state": normalized,
        "label": label,
        "source": _text(source, 120) or "upstream_snapshot",
        "evidence_items": evidence_count,
        "numeric_confidence_score": None,
        "quality_is_not_sport_probability": True,
    }


def _claim(
    claim_id: str,
    title: str,
    body: str,
    *,
    source: Any,
    source_type: str,
    state: Any,
    evidence: Iterable[Any] = (),
    freshness: Any = None,
    limitations: Iterable[Any] = (),
    link: str = "",
) -> dict[str, Any]:
    evidence_items = [_text(item, 220) for item in evidence if _text(item, 220)]
    limitation_items = [_text(item, 220) for item in limitations if _text(item, 220)]
    if not evidence_items:
        evidence_items = ["La afirmacion procede del snapshot indicado; no hay item de evidencia adicional."]
    return {
        "id": _text(claim_id, 80),
        "title": _text(title, 140),
        "body": _text(body, 420),
        "source": _text(source, 120) or "upstream_snapshot",
        "source_type": _text(source_type, 80),
        "certification_state": _state(state),
        "evidence": evidence_items,
        "freshness": _freshness(freshness),
        "quality": _quality(state, source, len(evidence_items)),
        "limitations": limitation_items,
        "link": _text(link, 220),
    }


def _status_from_counts(metrics: Mapping[str, Any]) -> tuple[str, str]:
    if not metrics:
        return "Sin evidencia suficiente", "No hay snapshot deportivo suficiente para construir una lectura SHARK."
    live = int(metrics.get("live_confirmed") or 0)
    available = int(metrics.get("matches_available") or 0)
    picks = int(metrics.get("picks_ready") or 0)
    if live:
        return "Directo confirmado", f"{live} partido(s) en directo con evidencia valida."
    if picks:
        return "Picks contextualizables", f"{picks} pick(s) completos pueden conectarse con partidos reales."
    if available:
        return "Agenda util", f"{available} partido(s) disponibles para explorar contexto."
    return "Esperando datos", "No hay suficiente contexto deportivo completo para priorizar una lectura."


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _missing_from_sources(*sources: Any) -> list[str]:
    missing: set[str] = set()
    for source in sources:
        if isinstance(source, Mapping):
            raw_values = source.get("missing") or source.get("limitations") or source.get("missing_information") or []
        else:
            raw_values = source
        if isinstance(raw_values, str):
            values = [raw_values]
        elif isinstance(raw_values, (list, tuple, set)):
            values = list(raw_values)
        else:
            values = []
        for value in values:
            text = _text(value, 220)
            if text:
                missing.add(text)
    return sorted(missing)


def _module(
    key: str,
    name: str,
    *,
    state: str,
    contract: Any = "",
    evidence: Any = "",
    link: str = "",
    limitations: Iterable[Any] = (),
) -> dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "state": _state(state) if state.isupper() else state,
        "contract": _text(contract, 120),
        "evidence": _text(evidence, 220),
        "link": _text(link, 220),
        "limitations": [_text(item, 180) for item in limitations if _text(item, 180)],
    }


def build_shark_intelligence_platform_snapshot(
    *,
    sports_summary: Mapping[str, Any] | None = None,
    sports_metrics: Mapping[str, Any] | None = None,
    match_context: Mapping[str, Any] | None = None,
    team_center: Mapping[str, Any] | None = None,
    competition_center: Mapping[str, Any] | None = None,
    observed_at_madrid: Any = "",
    navigation_links: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the central SHARK sports intelligence snapshot from known facts."""

    summary = _mapping(sports_summary)
    metrics = _mapping(sports_metrics or summary.get("sports_metrics"))
    match = _mapping(match_context)
    team = _mapping(team_center)
    competition = _mapping(competition_center)
    links = _mapping(navigation_links)
    intelligence = _mapping(match.get("intelligence"))
    sports_knowledge = _mapping(match.get("sports_knowledge"))
    sports_graph = _mapping(match.get("sports_graph"))
    shark_match_view = {}
    if intelligence.get("contract") == MATCH_INTELLIGENCE_CONTRACT:
        try:
            shark_match_view = build_match_intelligence_consumer_view(intelligence, "shark")
        except ValueError:
            shark_match_view = {}
    conclusions = _mapping(shark_match_view.get("conclusions"))
    evidence_labels = _evidence_labels(shark_match_view.get("evidence") or intelligence.get("evidence"))
    freshness = (
        _mapping(match.get("evidence")).get("updated_at")
        or _mapping(match.get("madrid_time")).get("iso")
        or observed_at_madrid
        or summary.get("last_sync")
    )
    status_title, status_body = _status_from_counts(metrics)
    claims: list[dict[str, Any]] = [
        _claim(
            "sports-data-state",
            status_title,
            status_body,
            source=metrics.get("source") or "sports-metrics-v1",
            source_type="sports_metrics",
            state="VERIFIED" if metrics.get("contract") else "INSUFFICIENT_DATA",
            evidence=[
                f"matches_available={_safe_int(metrics.get('matches_available'))}",
                f"live_confirmed={_safe_int(metrics.get('live_confirmed'))}",
                f"picks_ready={_safe_int(metrics.get('picks_ready'))}",
            ],
            freshness=metrics.get("last_sync") or summary.get("last_sync") or observed_at_madrid,
            limitations=[
                "Counts follow sports-metrics-v1 and exclude stale or incomplete live records.",
            ],
            link=links.get("calendar") or "/calendar",
        )
    ]
    lifecycle = _mapping(match.get("lifecycle"))
    match_title = _first_present(
        _mapping(match.get("match")).get("title"),
        intelligence.get("title"),
        lifecycle.get("summary"),
    )
    if match_title or intelligence:
        phase = _mapping(_mapping(conclusions.get("fase")).get("value"))
        state_label = _first_present(phase.get("label"), lifecycle.get("label"), lifecycle.get("summary"), "Estado parcial")
        claims.append(
            _claim(
                "anchor-match-context",
                "Partido ancla",
                f"{match_title or 'Partido seleccionado'}: {state_label}.",
                source=intelligence.get("contract") or match.get("contract") or "match_context",
                source_type="match_intelligence",
                state=intelligence.get("certification_state") or "PARTIALLY_VERIFIED",
                evidence=evidence_labels,
                freshness=_mapping(match.get("evidence")).get("updated_at") or freshness,
                limitations=intelligence.get("limitations") or match.get("limitations") or [],
                link=links.get("match_center"),
            )
        )
    changes = _mapping(_mapping(conclusions.get("cambios_recientes")).get("value"))
    change_count = _safe_int(changes.get("count"))
    if change_count:
        claims.append(
            _claim(
                "recent-changes",
                "Cambios recientes",
                f"{change_count} cambio(s) confirmado(s) en la ventana reciente del partido ancla.",
                source=MATCH_INTELLIGENCE_CONTRACT,
                source_type="match_intelligence",
                state=_mapping(conclusions.get("cambios_recientes")).get("state") or "PARTIALLY_VERIFIED",
                evidence=evidence_labels,
                freshness=freshness,
                limitations=_mapping(conclusions.get("cambios_recientes")).get("limitations") or [],
                link=links.get("match_center"),
            )
        )
    else:
        claims.append(
            _claim(
                "recent-changes-missing",
                "Cambios recientes",
                "No hay cambios recientes confirmados en el snapshot suministrado.",
                source=MATCH_INTELLIGENCE_CONTRACT if intelligence else "match_context",
                source_type="missing_information",
                state="INSUFFICIENT_DATA",
                evidence=["No existe conclusion cambios_recientes con count mayor que cero."],
                freshness=freshness,
                limitations=["SHARK no infiere cambios si no aparecen en timeline, tracker o Match Intelligence."],
                link=links.get("match_center"),
            )
        )
    if sports_graph.get("contract"):
        claims.append(
            _claim(
                "sports-graph-context",
                "Relaciones deportivas",
                f"Sports Graph aporta {_safe_int(sports_graph.get('edge_count'))} relacion(es) reutilizables.",
                source=SPORTS_GRAPH_FOUNDATION_CONTRACT,
                source_type="sports_graph",
                state="PARTIALLY_VERIFIED" if sports_graph.get("edge_count") else "INSUFFICIENT_DATA",
                evidence=sports_graph.get("relationships") or [],
                freshness=freshness,
                limitations=sports_graph.get("skipped") or [],
                link=links.get("sports_graph"),
            )
        )
    if sports_knowledge.get("contract"):
        claims.append(
            _claim(
                "sports-knowledge-context",
                "Conocimiento reutilizable",
                "Sports Knowledge organiza equipo, competicion, temporada, rivalidad y cronologia cuando existen datos.",
                source=sports_knowledge.get("contract"),
                source_type="sports_knowledge",
                state=sports_knowledge.get("certification_state") or "PARTIALLY_VERIFIED",
                evidence=[
                    sports_knowledge.get("source_domain_contract") or SPORTS_DOMAIN_MODEL_CONTRACT,
                    sports_knowledge.get("source_intelligence_contract") or MATCH_INTELLIGENCE_CONTRACT,
                ],
                freshness=sports_knowledge.get("observed_at_madrid") or freshness,
                limitations=sports_knowledge.get("limitations") or [],
                link=links.get("match_center"),
            )
        )
    if team.get("contract"):
        team_name = _first_present(_mapping(team.get("team")).get("official_name"), _mapping(team.get("team")).get("name"), "Equipo")
        claims.append(
            _claim(
                "team-center-context",
                "Contexto de equipo",
                f"Team Center contiene contexto disponible para {team_name}.",
                source=team.get("contract"),
                source_type="team_center",
                state=_mapping(team.get("data_quality")).get("certification_state") or "PARTIALLY_VERIFIED",
                evidence=team.get("available_information") or [],
                freshness=_mapping(_mapping(team.get("data_quality")).get("freshness")),
                limitations=team.get("missing_information") or _mapping(team.get("data_quality")).get("limitations") or [],
                link=links.get("team_center"),
            )
        )
    if competition.get("contract"):
        competition_name = _first_present(_mapping(competition.get("competition")).get("official_name"), _mapping(competition.get("competition")).get("name"), "Competicion")
        claims.append(
            _claim(
                "competition-center-context",
                "Contexto de competicion",
                f"Competition Center contiene contexto disponible para {competition_name}.",
                source=competition.get("contract"),
                source_type="competition_center",
                state=_mapping(competition.get("data_quality")).get("certification_state") or "PARTIALLY_VERIFIED",
                evidence=competition.get("available_information") or [],
                freshness=_mapping(_mapping(competition.get("data_quality")).get("freshness")),
                limitations=competition.get("missing_information") or _mapping(competition.get("data_quality")).get("limitations") or [],
                link=links.get("competition_center"),
            )
        )
    missing = _missing_from_sources(
        *(summary.get("incomplete_matches") or []),
        match.get("absent_information") or [],
        intelligence.get("missing_information") or [],
        sports_knowledge.get("limitations") or [],
        team.get("missing_information") or [],
        competition.get("missing_information") or [],
    )
    if not missing and not any((metrics, match, team, competition)):
        missing.append("No hay snapshot deportivo, Match Context, Team Center ni Competition Center disponibles.")
    modules = [
        _module(
            "match_center",
            "Match Center",
            state="PARTIALLY_VERIFIED" if match else "INSUFFICIENT_DATA",
            contract=match.get("contract"),
            evidence=match_title or "Partido ancla pendiente",
            link=links.get("match_center"),
            limitations=[] if match else ["No hay partido ancla disponible."],
        ),
        _module(
            "match_intelligence",
            "Match Intelligence",
            state=intelligence.get("certification_state") or ("INSUFFICIENT_DATA" if not intelligence else "PARTIALLY_VERIFIED"),
            contract=intelligence.get("contract") or MATCH_INTELLIGENCE_CONTRACT,
            evidence=", ".join(evidence_labels) or "Evidencia de inteligencia pendiente",
            link=links.get("match_center"),
            limitations=intelligence.get("missing_information") or intelligence.get("limitations") or [],
        ),        _module(
            "team_center",
            "Team Center",
            state=_mapping(team.get("data_quality")).get("certification_state") or ("INSUFFICIENT_DATA" if not team else "PARTIALLY_VERIFIED"),
            contract=team.get("contract"),
            evidence=", ".join(team.get("available_information") or []) or "Contexto de equipo pendiente",
            link=links.get("team_center"),
            limitations=team.get("missing_information") or [],
        ),
        _module(
            "competition_center",
            "Competition Center",
            state=_mapping(competition.get("data_quality")).get("certification_state") or ("INSUFFICIENT_DATA" if not competition else "PARTIALLY_VERIFIED"),
            contract=competition.get("contract"),
            evidence=", ".join(competition.get("available_information") or []) or "Contexto de competicion pendiente",
            link=links.get("competition_center"),
            limitations=competition.get("missing_information") or [],
        ),
        _module(
            "sports_graph",
            "Sports Graph",
            state="PARTIALLY_VERIFIED" if sports_graph.get("edge_count") else "INSUFFICIENT_DATA",
            contract=SPORTS_GRAPH_FOUNDATION_CONTRACT,
            evidence=f"{_safe_int(sports_graph.get('edge_count'))} relaciones",
            link=links.get("sports_graph"),
            limitations=[] if sports_graph.get("edge_count") else ["No hay relaciones suficientes en el snapshot."],
        ),
        _module(
            "telegram",
            "Telegram",
            state="NOT_CONFIGURED",
            contract=_mapping(match.get("telegram_readonly_contract")).get("contract"),
            evidence="Contrato solo lectura preparado; no se envia nada.",
            link=links.get("telegram") or "/telegram",
            limitations=["Esta fase no implementa mensajes nuevos."],
        ),
    ]
    blocking_limitations = [
        "No se ejecuta IA generativa.",
        "No se generan predicciones.",
        "No se envia Telegram.",
        "No se modifican pesos SHARK.",
        "No se escriben datos por GET.",
    ]
    diagnostics = {
        "database_queries": 0,
        "database_writes": 0,
        "external_calls": 0,
        "telegram_sends": 0,
        "stripe_calls": 0,
        "generative_ai_calls": 0,
        "automatic_actions": 0,
        "new_provider_calls": 0,
        "new_cache_writes": 0,
        "parallel_data_source_created": False,
    }
    state_priority = [claim["certification_state"] for claim in claims]
    if any(item == "STALE" for item in state_priority):
        certification_state = "STALE"
    elif any(item == "VERIFIED" for item in state_priority) and any(item == "PARTIALLY_VERIFIED" for item in state_priority):
        certification_state = "PARTIALLY_VERIFIED"
    elif all(item == "VERIFIED" for item in state_priority if item):
        certification_state = "VERIFIED"
    elif any(item in {"VERIFIED", "PARTIALLY_VERIFIED"} for item in state_priority):
        certification_state = "PARTIALLY_VERIFIED"
    else:
        certification_state = "INSUFFICIENT_DATA"
    return {
        "ok": True,
        "contract": SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
        "source_contracts": {
            "sports_domain_model": SPORTS_DOMAIN_MODEL_CONTRACT,
            "sports_knowledge": sports_knowledge.get("contract") or SPORTS_KNOWLEDGE_LAYER_CONTRACT,
            "sports_graph": SPORTS_GRAPH_FOUNDATION_CONTRACT,
            "match_intelligence": intelligence.get("contract") or MATCH_INTELLIGENCE_CONTRACT,
            "team_center": team.get("contract") or "TEAM-CENTER-PREMIUM-CLUB-EXPERIENCE-V1",
            "competition_center": competition.get("contract") or "COMPETITION-CENTER-LEAGUE-INTELLIGENCE-PLATFORM-V1",
        },
        "observed_at_madrid": _text(observed_at_madrid or freshness, 100),
        "certification_state": certification_state,
        "summary": {
            "title": "SHARK Intelligence Platform",
            "headline": status_title,
            "body": status_body,
            "next_action": "Abrir el modulo con mas evidencia antes de tomar una decision.",
        },
        "claims": claims,
        "modules": modules,
        "missing_information": missing[:20],
        "changed_information": [
            claim for claim in claims if claim["id"].startswith("recent-changes")
        ],
        "transparency": {
            "claim_count": len(claims),
            "claims_with_source": sum(1 for claim in claims if claim.get("source")),
            "claims_with_evidence": sum(1 for claim in claims if claim.get("evidence")),
            "claims_with_freshness": sum(1 for claim in claims if claim.get("freshness")),
            "claims_with_quality": sum(1 for claim in claims if claim.get("quality")),
            "claims_with_limitations": len(claims),
            "all_claims_traceable": all(
                claim.get("source")
                and claim.get("evidence")
                and claim.get("freshness")
                and claim.get("quality")
                and "limitations" in claim
                for claim in claims
            ),
        },
        "sports_graph": {
            "contract": SPORTS_GRAPH_FOUNDATION_CONTRACT,
            "edge_count": _safe_int(sports_graph.get("edge_count")),
            "relationships": sports_graph.get("relationships") or [],
            "persistence_authorized": False,
        },
        "assistant_preparation": {
            "future_assistant_ready": True,
            "generative_ai_enabled": False,
            "allowed_actions": [
                "explicar evidencia existente",
                "mostrar limitaciones",
                "dirigir al modulo con mas contexto",
            ],
            "blocked_actions": [
                "inventar hechos",
                "predecir sin evidencia",
                "enviar Telegram",
                "modificar picks",
                "desplegar",
            ],
        },
        "limitations": blocking_limitations,
        "diagnostics": diagnostics,
        "no_fake_data": True,
        "no_predictions": True,
        "read_only": True,
    }


def shark_intelligence_platform_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        "contract": SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
        "requires": [
            SPORTS_DOMAIN_MODEL_CONTRACT,
            SPORTS_KNOWLEDGE_LAYER_CONTRACT,
            SPORTS_GRAPH_FOUNDATION_CONTRACT,
            MATCH_INTELLIGENCE_CONTRACT,
        ],
        "guardrails": {
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "automatic_actions": 0,
            "fake_data_created": 0,
            "predictions_created": 0,
        },
    }

