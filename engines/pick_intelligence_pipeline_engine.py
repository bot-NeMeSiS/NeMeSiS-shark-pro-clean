"""Auditable, non-publishing pick intelligence pipeline for V939."""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime
from typing import Any

from engines.company_intelligence_engine import MADRID_TZ, classify_freshness, readonly_connection, safe_rows


PIPELINE_STATES = (
    "CANDIDATE",
    "VALIDATED",
    "REVIEW_REQUIRED",
    "PREMIUM_READY",
    "BLOCKED",
    "EXPIRED",
    "DUPLICATE",
    "DATA_INCOMPLETE",
    "PROVIDER_STALE",
    "PUBLISHED",
    "RESULT_PENDING",
    "GRADED",
)
SETTLED_STATES = {"won", "lost", "void", "win", "loss", "ganado", "perdido", "nulo", "graded", "settled"}


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if row.get(key) not in (None, ""):
            return row.get(key)
    return None


def _float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=MADRID_TZ)
        return parsed.astimezone(MADRID_TZ)
    except (TypeError, ValueError):
        return None


def build_pick_dedupe_key(pick: dict[str, Any]) -> str:
    parts = (
        _first(pick, "match_id", "fixture_id", "event_id"),
        _first(pick, "market", "market_name", "pick_type"),
        _first(pick, "selection", "selection_name", "tip"),
        _first(pick, "membership_required", "membership", "audience") or "ALL",
    )
    normalized = "|".join(str(part or "").strip().lower() for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24] if normalized.strip("|") else ""


def _match_is_real(pick: dict[str, Any], match: dict[str, Any] | None) -> bool:
    if pick.get("_match_verified") is True:
        return True
    if not match:
        return False
    return bool(
        _first(match, "id", "match_id", "fixture_id", "event_id")
        and _first(match, "home_team", "home_name", "home")
        and _first(match, "away_team", "away_name", "away")
        and _first(match, "competition_name", "league_name", "competition", "league")
        and _first(match, "kickoff_at", "match_date", "start_time", "event_date", "date")
        and _first(match, "source", "provider", "data_source")
    )


def evaluate_pick_candidate(
    pick: dict[str, Any],
    match: dict[str, Any] | None = None,
    *,
    seen_dedupe_keys: set[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate data quality only. It never predicts sporting success."""
    item = dict(pick or {})
    now = now or datetime.now(MADRID_TZ)
    market = str(_first(item, "market", "market_name", "pick_type") or "").strip()
    selection = str(_first(item, "selection", "selection_name", "tip") or "").strip()
    odds = _float(_first(item, "odds", "price", "odds_value"))
    odds_at = _first(item, "odds_recorded_at", "odds_updated_at", "price_updated_at", "updated_at")
    provider = str(_first(item, "provider", "source", "data_source") or "").strip()
    match_id = str(_first(item, "match_id", "fixture_id", "event_id") or "").strip()
    kickoff = _parse_time(_first(item, "kickoff_at", "match_date", "event_date") or (match or {}).get("kickoff_at") or (match or {}).get("match_date"))
    status = str(_first(item, "result_status", "status") or "candidate").strip().lower()
    reasons: list[str] = []
    warnings: list[str] = []

    if not match_id:
        reasons.append("MATCH_ID_MISSING")
    if not _match_is_real(item, match):
        reasons.append("MATCH_NOT_VERIFIED")
    if not market:
        reasons.append("MARKET_MISSING")
    if not selection:
        reasons.append("SELECTION_MISSING")
    if odds is None or odds <= 1.0:
        reasons.append("ODDS_MISSING_OR_INVALID")
    if not provider:
        reasons.append("PROVIDER_MISSING")
    if not odds_at:
        reasons.append("ODDS_TIMESTAMP_MISSING")
    if item.get("source_conflict") or item.get("data_conflict"):
        reasons.append("SOURCE_CONFLICT")
    if item.get("league_blocked") is True:
        reasons.append("LEAGUE_BLOCKED")

    freshness = classify_freshness(odds_at, fresh_minutes=15, stale_minutes=60)
    if freshness.get("state") == "STALE":
        reasons.append("PROVIDER_STALE")
    elif freshness.get("state") == "PARTIALLY_VERIFIED":
        warnings.append("ODDS_RECORDED_NOT_FRESH")
    elif freshness.get("state") == "NOT_CERTIFIED" and odds_at:
        reasons.append("ODDS_TIMESTAMP_INVALID")

    dedupe_key = build_pick_dedupe_key(item)
    if dedupe_key and seen_dedupe_keys is not None and dedupe_key in seen_dedupe_keys:
        reasons.append("DUPLICATE")

    if kickoff and kickoff < now and status not in SETTLED_STATES:
        reasons.append("OUTSIDE_VALID_WINDOW")

    required_checks = {
        "real_match": _match_is_real(item, match),
        "market": bool(market),
        "selection": bool(selection),
        "real_odds": odds is not None and odds > 1.0,
        "provider": bool(provider),
        "freshness": freshness.get("state") in {"VERIFIED", "PARTIALLY_VERIFIED"},
        "risk": bool(_first(item, "risk", "risk_level")),
        "stake": _float(_first(item, "stake", "stake_units")) is not None,
        "reason": bool(_first(item, "reason", "reasoning", "rationale")),
        "risks_explained": bool(_first(item, "risks", "risk_notes", "counterargument")),
    }
    quality_score = int(round(sum(1 for value in required_checks.values() if value) / len(required_checks) * 100))

    if status in SETTLED_STATES:
        pipeline_state = "GRADED"
    elif "DUPLICATE" in reasons:
        pipeline_state = "DUPLICATE"
    elif "PROVIDER_STALE" in reasons:
        pipeline_state = "PROVIDER_STALE"
    elif "OUTSIDE_VALID_WINDOW" in reasons:
        pipeline_state = "EXPIRED"
    elif any(reason in reasons for reason in ("MATCH_ID_MISSING", "MATCH_NOT_VERIFIED", "MARKET_MISSING", "SELECTION_MISSING", "ODDS_MISSING_OR_INVALID", "PROVIDER_MISSING", "ODDS_TIMESTAMP_MISSING", "ODDS_TIMESTAMP_INVALID")):
        pipeline_state = "DATA_INCOMPLETE"
    elif reasons:
        pipeline_state = "BLOCKED"
    elif status in {"published", "sent", "active"}:
        pipeline_state = "PUBLISHED"
    elif quality_score >= 90 and freshness.get("state") == "VERIFIED":
        pipeline_state = "PREMIUM_READY"
    elif quality_score >= 75:
        pipeline_state = "VALIDATED"
    else:
        pipeline_state = "REVIEW_REQUIRED"

    publishable = pipeline_state in {"PREMIUM_READY", "PUBLISHED"}
    telegram_ready = publishable and not reasons and freshness.get("state") == "VERIFIED"
    return {
        "pick_id": str(_first(item, "id", "pick_id") or ""),
        "match_id": match_id,
        "pipeline_state": pipeline_state,
        "quality_score": quality_score,
        "quality_score_type": "data_completeness_not_win_probability",
        "blocking_reasons": sorted(set(reasons)),
        "warnings": sorted(set(warnings)),
        "required_checks": required_checks,
        "odds": odds,
        "odds_freshness": freshness,
        "dedupe_key": dedupe_key,
        "publishable": publishable,
        "telegram_ready": telegram_ready,
        "automatic_publish": False,
        "automatic_weight_change": False,
        "requires_human_review": pipeline_state in {"REVIEW_REQUIRED", "BLOCKED"},
        "candidate": {
            "id": str(_first(item, "id", "pick_id") or ""),
            "match_id": match_id,
            "competition": str(_first(item, "competition_name", "league_name", "competition") or (match or {}).get("competition_name") or ""),
            "home_team": str(_first(item, "home_team", "home_name") or (match or {}).get("home_team") or ""),
            "away_team": str(_first(item, "away_team", "away_name") or (match or {}).get("away_team") or ""),
            "market": market,
            "selection": selection,
            "odds": odds,
            "odds_recorded_at": str(odds_at or ""),
            "provider": provider,
            "risk": str(_first(item, "risk", "risk_level") or ""),
            "stake": _float(_first(item, "stake", "stake_units")),
            "reason": str(_first(item, "reason", "reasoning", "rationale") or "")[:1000],
            "risks": str(_first(item, "risks", "risk_notes", "counterargument") or "")[:1000],
            "membership_required": str(_first(item, "membership_required", "membership", "audience") or "PRO").upper(),
            "kickoff_at": kickoff.isoformat(timespec="seconds") if kickoff else "",
        },
    }


def _match_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        identifier = str(_first(row, "id", "match_id", "fixture_id", "event_id") or "").strip()
        if identifier:
            result[identifier] = row
    return result


def build_pick_pipeline_snapshot(
    db_path: str,
    app_version: str,
    *,
    environment: str = "local",
    limit: int = 500,
) -> dict[str, Any]:
    conn = readonly_connection(db_path)
    if conn is None:
        return {
            "version": app_version,
            "environment": environment,
            "certification_state": "NOT_CONFIGURED",
            "candidates": [],
            "counts": {},
            "database_written": False,
            "external_calls": 0,
            "limitations": ["DB local no disponible en modo read-only."],
        }
    try:
        picks = safe_rows(conn, "picks", limit)
        if not picks:
            picks = safe_rows(conn, "pick_decisions", limit)
        matches = _match_index(safe_rows(conn, "matches", max(limit * 2, 500)))
        seen: set[str] = set()
        evaluated: list[dict[str, Any]] = []
        for pick in picks:
            match_id = str(_first(pick, "match_id", "fixture_id", "event_id") or "")
            result = evaluate_pick_candidate(pick, matches.get(match_id), seen_dedupe_keys=seen)
            if result.get("dedupe_key"):
                seen.add(str(result["dedupe_key"]))
            evaluated.append(result)
        counts = Counter(item.get("pipeline_state") for item in evaluated)
        state = "PARTIALLY_VERIFIED" if evaluated else "INSUFFICIENT_DATA"
        last_odds = max((str(_first(row, "odds_recorded_at", "odds_updated_at", "updated_at") or "") for row in picks), default="")
        return {
            "version": app_version,
            "environment": environment,
            "certification_state": state,
            "confidence": 0.8 if evaluated else None,
            "freshness": classify_freshness(last_odds, fresh_minutes=15, stale_minutes=60),
            "candidates": evaluated,
            "counts": dict(counts),
            "candidate_count": len(evaluated),
            "premium_ready_count": int(counts.get("PREMIUM_READY", 0)),
            "blocked_count": sum(int(counts.get(name, 0)) for name in ("BLOCKED", "DATA_INCOMPLETE", "PROVIDER_STALE", "DUPLICATE", "EXPIRED")),
            "pipeline_states": list(PIPELINE_STATES),
            "database_written": False,
            "external_calls": 0,
            "telegram_sent": False,
            "automatic_approval": False,
            "limitations": [
                "El quality_score mide completitud del dato, nunca probabilidad de acierto.",
                "La lectura local no certifica el estado del proveedor en produccion.",
            ],
        }
    finally:
        conn.close()


def pick_quality_thresholds() -> dict[str, Any]:
    return {
        "premium_ready": {"minimum_data_quality": 90, "odds_freshness": "VERIFIED", "blocking_reasons": 0},
        "validated": {"minimum_data_quality": 75, "human_review_possible": True},
        "publish": {"automatic": False, "approval": "existing_policy_or_human_review"},
        "learning": {"automatic_weight_changes": False},
    }
