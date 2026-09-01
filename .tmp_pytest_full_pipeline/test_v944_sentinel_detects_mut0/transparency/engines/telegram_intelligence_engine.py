"""Telegram decision support for V939. This module never sends messages."""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Iterable

from engines.company_intelligence_engine import MADRID_TZ, classify_freshness, readonly_connection, safe_rows, table_exists
from engines.pick_intelligence_pipeline_engine import build_pick_pipeline_snapshot
from engines.sports_platform_contracts import build_assistant_context
from engines.sports_domain_model_engine import build_telegram_readonly_contract
from engines.telegram_message_formatter import (
    BRAND_HEADER,
    MESSAGE_SEPARATOR,
    MESSAGE_SOFT_SEPARATOR,
    RESPONSIBLE_FOOTER,
    TRANSPARENCY_FOOTER,
)


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if row.get(key) not in (None, ""):
            return row.get(key)
    return None


def score_telegram_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    evaluation = candidate or {}
    quality = int(evaluation.get("quality_score") or 0)
    reasons = list(evaluation.get("blocking_reasons") or [])
    ready = bool(evaluation.get("telegram_ready")) and not reasons
    value_score = quality if ready else 0
    return {
        "eligible": ready,
        "value_score": value_score,
        "value_score_type": "message_data_quality_not_sport_probability",
        "blocked_reasons": reasons,
        "state": "READY" if ready else "BLOCKED",
    }


def calculate_dedupe_key(candidate: dict[str, Any], membership: str = "PRO") -> str:
    item = candidate.get("candidate") if isinstance(candidate.get("candidate"), dict) else candidate
    raw = "|".join((
        str(item.get("match_id") or "").strip().lower(),
        str(item.get("market") or "").strip().lower(),
        str(item.get("selection") or "").strip().lower(),
        str(membership or "PRO").strip().upper(),
    ))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24] if raw.strip("|") else ""


def evaluate_daily_limit(selected_count: int, already_sent: int, daily_limit: int) -> dict[str, Any]:
    limit = max(0, int(daily_limit))
    remaining = max(0, limit - max(0, int(already_sent)))
    return {
        "allowed": min(max(0, int(selected_count)), remaining),
        "remaining_before_selection": remaining,
        "daily_limit": limit,
        "state": "AVAILABLE" if remaining else "LIMIT_REACHED",
    }


def calculate_send_window(candidate: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    item = candidate.get("candidate") if isinstance(candidate.get("candidate"), dict) else candidate
    text = str(item.get("kickoff_at") or "").replace("Z", "+00:00")
    try:
        kickoff = datetime.fromisoformat(text)
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=MADRID_TZ)
        kickoff = kickoff.astimezone(MADRID_TZ)
    except (TypeError, ValueError):
        return {"state": "NOT_CERTIFIED", "recommended_at_madrid": None, "reason": "kickoff_missing_or_invalid"}
    now = now or datetime.now(MADRID_TZ)
    recommended = kickoff - timedelta(minutes=90)
    if kickoff <= now:
        return {"state": "EXPIRED", "recommended_at_madrid": recommended.isoformat(timespec="minutes")}
    return {
        "state": "VERIFIED",
        "recommended_at_madrid": max(now, recommended).isoformat(timespec="minutes"),
        "kickoff_at_madrid": kickoff.isoformat(timespec="minutes"),
    }


def build_membership_variant(candidate: dict[str, Any], membership: str = "PRO") -> dict[str, Any]:
    item = candidate.get("candidate") if isinstance(candidate.get("candidate"), dict) else candidate
    plan = str(membership or "PRO").upper()
    base = {
        "membership": plan,
        "competition": item.get("competition") or "",
        "match": " vs ".join(part for part in (str(item.get("home_team") or ""), str(item.get("away_team") or "")) if part),
        "responsible_note": "Análisis informativo. No garantiza resultados; stake orientativo.",
    }
    if plan == "FREE":
        base.update({
            "market": "",
            "selection": "",
            "odds": None,
            "summary": "Existe un análisis validado. El detalle completo está reservado a membresías premium.",
            "premium_analysis_revealed": False,
        })
    else:
        base.update({
            "market": item.get("market") or "",
            "selection": item.get("selection") or "",
            "odds": item.get("odds"),
            "stake": item.get("stake"),
            "risk": item.get("risk") or "",
            "reason": item.get("reason") or "",
            "counterargument": item.get("risks") or "",
            "premium_analysis_revealed": True,
        })
        if plan in {"ELITE", "ELITE+"}:
            base["advanced_reading"] = "Disponible solo cuando la evidencia SHARK persistida la respalda."
            base["bankroll_guidance"] = "Gestión responsable; nunca perseguir pérdidas."
    return base


def build_premium_message(candidate: dict[str, Any], membership: str = "PRO") -> dict[str, Any]:
    variant = build_membership_variant(candidate, membership)
    plan = membership.upper()
    lines = [
        BRAND_HEADER,
        MESSAGE_SEPARATOR,
        f"🎯 Preview Telegram {plan}",
        variant.get("match") or "Partido validado",
    ]
    if variant.get("premium_analysis_revealed"):
        lines.extend((
            "",
            "Entrada",
            f"Mercado: {variant.get('market') or 'No disponible'}",
            f"Selección: {variant.get('selection') or 'No disponible'}",
            f"Cuota registrada: {variant.get('odds') or 'No disponible'}",
            f"Riesgo: {variant.get('risk') or 'requiere revisión'}",
            "",
            "Contexto SHARK",
            f"Motivo: {variant.get('reason') or 'sin motivo publicable'}",
            f"Qué puede invalidarlo: {variant.get('counterargument') or 'sin contraargumento publicable'}",
        ))
    else:
        lines.extend(("", "Preview FREE", str(variant.get("summary") or "")))
    lines.extend((
        "",
        MESSAGE_SOFT_SEPARATOR,
        TRANSPARENCY_FOOTER,
        str(variant.get("responsible_note") or RESPONSIBLE_FOOTER),
    ))
    return {"membership": plan, "preview": "\n".join(lines), "send_executed": False}



def build_visual_card_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    item = candidate.get("candidate") if isinstance(candidate.get("candidate"), dict) else candidate
    return {
        "kind": "pick",
        "competition": item.get("competition") or "",
        "home_team": item.get("home_team") or "",
        "away_team": item.get("away_team") or "",
        "market": item.get("market") or "",
        "selection": item.get("selection") or "",
        "odds": item.get("odds"),
        "risk": item.get("risk") or "",
        "generated_image": False,
        "contains_synthetic_sports_data": False,
    }


def evaluate_message_value(candidate: dict[str, Any]) -> dict[str, Any]:
    scored = score_telegram_candidate(candidate)
    item = candidate.get("candidate") if isinstance(candidate.get("candidate"), dict) else candidate
    clarity = all(item.get(key) not in (None, "") for key in ("market", "selection", "odds", "reason", "risks"))
    return {
        **scored,
        "clear_reason_and_counterargument": clarity,
        "responsible_language_required": True,
        "automatic_send": False,
    }


def select_best_daily_picks(
    candidates: Iterable[dict[str, Any]],
    *,
    limit: int = 3,
    sent_dedupe_keys: set[str] | None = None,
    membership: str = "PRO",
) -> dict[str, Any]:
    sent = sent_dedupe_keys or set()
    eligible: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for candidate in candidates:
        scored = evaluate_message_value(candidate)
        key = calculate_dedupe_key(candidate, membership)
        if key and key in sent:
            blocked.append({"pick_id": candidate.get("pick_id"), "reason": "DUPLICATE", "dedupe_key": key})
            continue
        if not scored.get("eligible"):
            blocked.append({"pick_id": candidate.get("pick_id"), "reason": "QUALITY_BLOCKED", "details": scored.get("blocked_reasons")})
            continue
        eligible.append({**candidate, "telegram_score": scored, "dedupe_key": key})
    eligible.sort(key=lambda item: int((item.get("telegram_score") or {}).get("value_score") or 0), reverse=True)
    selected = eligible[: max(0, int(limit))]
    return {"selected": selected, "blocked": blocked + [{"pick_id": item.get("pick_id"), "reason": "DAILY_LIMIT"} for item in eligible[len(selected):]]}


def build_telegram_candidate_queue(
    candidates: Iterable[dict[str, Any]],
    *,
    daily_limit: int = 3,
    already_sent: int = 0,
    sent_dedupe_keys: set[str] | None = None,
    membership: str = "PRO",
) -> dict[str, Any]:
    limit_state = evaluate_daily_limit(9999, already_sent, daily_limit)
    selection = select_best_daily_picks(
        candidates,
        limit=int(limit_state.get("allowed") or 0),
        sent_dedupe_keys=sent_dedupe_keys,
        membership=membership,
    )
    queue = []
    for candidate in selection["selected"]:
        queue.append({
            "pick_id": candidate.get("pick_id"),
            "dedupe_key": candidate.get("dedupe_key"),
            "membership": membership.upper(),
            "send_window": calculate_send_window(candidate),
            "message": build_premium_message(candidate, membership),
            "visual_card": build_visual_card_payload(candidate),
            "state": "PREVIEW_READY",
            "send_executed": False,
        })
    return {
        "queue": queue,
        "blocked": selection["blocked"],
        "daily_limit": limit_state,
        "send_executed": False,
        "external_calls": 0,
    }


def _delivery_evidence(conn) -> dict[str, Any]:
    tables = ("telegram_deliveries", "telegram_delivery_logs", "telegram_delivery_memory", "telegram_queue")
    counts: Counter[str] = Counter()
    dedupe_keys: set[str] = set()
    latest = ""
    observed = 0
    used_tables: list[str] = []
    for table in tables:
        if not table_exists(conn, table):
            continue
        used_tables.append(table)
        for row in safe_rows(conn, table, 5000):
            observed += 1
            status = str(_first(row, "status", "delivery_status", "state") or "unknown").lower()
            counts[status] += 1
            key = str(_first(row, "dedupe_key", "source_key", "signature") or "")
            if key:
                dedupe_keys.add(key)
            timestamp = str(_first(row, "sent_at", "delivered_at", "created_at", "updated_at") or "")
            latest = max(latest, timestamp)
    return {
        "records": observed,
        "status_counts": dict(counts),
        "dedupe_keys": dedupe_keys,
        "last_delivery_at": latest,
        "tables": used_tables,
    }


def track_message_outcome(message: dict[str, Any], outcome: dict[str, Any] | None = None) -> dict[str, Any]:
    outcome = outcome or {}
    return {
        "dedupe_key": message.get("dedupe_key") or "",
        "delivery_state": outcome.get("delivery_state") or "NOT_CERTIFIED",
        "pick_result": outcome.get("pick_result") or "NOT_CERTIFIED",
        "opened": outcome.get("opened") if "opened" in outcome else None,
        "clicked": outcome.get("clicked") if "clicked" in outcome else None,
        "conversion": outcome.get("conversion") if "conversion" in outcome else None,
        "persisted": False,
        "limitations": ["Aperturas, clics y conversiones solo se aceptan si existe una senal atribuible real."],
    }


def build_telegram_learning_summary(delivery: dict[str, Any]) -> dict[str, Any]:
    records = int(delivery.get("records") or 0)
    return {
        "certification_state": "PARTIALLY_VERIFIED" if records >= 30 else "INSUFFICIENT_DATA",
        "sample_size": records,
        "format_performance": None,
        "send_window_performance": None,
        "open_rate": None,
        "click_rate": None,
        "conversion_rate": None,
        "limitations": ["No se infieren aperturas, clics ni conversiones a partir de entregas."],
    }


def build_telegram_intelligence_snapshot(
    db_path: str,
    app_version: str,
    *,
    environment: str = "local",
    daily_limit: int = 3,
    sports_metrics: dict[str, Any] | None = None,
    match_context: dict[str, Any] | None = None,
    match_intelligence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sports_metrics = dict(sports_metrics or {})
    pipeline = build_pick_pipeline_snapshot(db_path, app_version, environment=environment)
    conn = readonly_connection(db_path)
    if conn is None:
        delivery = {"records": 0, "status_counts": {}, "dedupe_keys": set(), "last_delivery_at": "", "tables": []}
    else:
        try:
            delivery = _delivery_evidence(conn)
        finally:
            conn.close()
    already_sent = sum(int(value) for key, value in (delivery.get("status_counts") or {}).items() if key in {"sent", "delivered", "success"})
    queue = build_telegram_candidate_queue(
        pipeline.get("candidates") or [],
        daily_limit=daily_limit,
        already_sent=already_sent,
        sent_dedupe_keys=set(delivery.get("dedupe_keys") or set()),
        membership="PRO",
    )
    state = "PARTIALLY_VERIFIED" if delivery.get("records") or pipeline.get("candidate_count") else "INSUFFICIENT_DATA"
    domain_model = (match_context or {}).get("domain_model") if isinstance(match_context, dict) else {}
    if not isinstance(domain_model, dict):
        domain_model = {}
    domain_match = domain_model.get("match") if isinstance(domain_model.get("match"), dict) else {}
    telegram_readonly_contract = build_telegram_readonly_contract(
        match_entity=domain_match,
        match_intelligence=match_intelligence,
        timeline_events=domain_match.get("events") if isinstance(domain_match, dict) else [],
        freshness=domain_match.get("freshness") if isinstance(domain_match, dict) else {},
    )
    assistant_context = build_assistant_context(
        "telegram",
        match_context=match_context,
        match_intelligence=match_intelligence,
        sports_metrics=sports_metrics,
        evidence_state=state,
        limitations=["El envelope no autoriza envíos ni escrituras."],
    )
    return {
        "version": app_version,
        "environment": environment,
        "certification_state": state,
        "confidence": 0.7 if state == "PARTIALLY_VERIFIED" else None,
        "sports_metrics": sports_metrics,
        "assistant_context": assistant_context.to_dict(),
        "telegram_readonly_contract": telegram_readonly_contract,
        "match_intelligence_contract": (
            (match_intelligence or {}).get("contract")
            if isinstance(match_intelligence, dict)
            else None
        ),
        "public_picks_ready": sports_metrics.get("picks_ready"),
        "freshness": classify_freshness(delivery.get("last_delivery_at"), fresh_minutes=1440, stale_minutes=10080),
        "candidate_count": pipeline.get("candidate_count", 0),
        "preview_ready_count": len(queue.get("queue") or []),
        "blocked_count": len(queue.get("blocked") or []),
        "queue": queue,
        "delivery": {**delivery, "dedupe_keys": len(delivery.get("dedupe_keys") or set())},
        "learning": build_telegram_learning_summary(delivery),
        "send_executed": False,
        "telegram_api_called": False,
        "database_written": False,
        "limitations": [
            "No se valida el token ni el destino de producción desde esta lectura local.",
            "No se ejecuta envío real, ni siquiera cuando existe un preview listo.",
        ],
    }
