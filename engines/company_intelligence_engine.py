"""Evidence-first company intelligence for NeMeSiS SHARK PRO V939.

This module coordinates existing engines. Snapshot builders are read-only and
never call providers, Telegram, Stripe, Git, Render or deployment tooling.
Persistence is explicit and reserved for protected POST/Cron entry points.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


MADRID_TZ = ZoneInfo("Europe/Madrid")
EVIDENCE_STATES = (
    "VERIFIED",
    "PARTIALLY_VERIFIED",
    "NOT_CERTIFIED",
    "NOT_CONFIGURED",
    "STALE",
    "BLOCKED_BY_ACCESS",
    "HYPOTHESIS",
    "INSUFFICIENT_DATA",
    "REQUIRES_REVIEW",
)
SENSITIVE_KEY = re.compile(
    r"(secret|token|password|passwd|authorization|cookie|session|api[_-]?key|card|email|phone|address|ip$)",
    re.IGNORECASE,
)
MAX_MEMORY_SNAPSHOTS = 30
MAX_MEMORY_DECISIONS = 500


def madrid_now_iso() -> str:
    return datetime.now(MADRID_TZ).isoformat(timespec="seconds")


def _as_number(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(MADRID_TZ)
    except (TypeError, ValueError):
        return None


def classify_freshness(value: Any, fresh_minutes: int = 15, stale_minutes: int = 60) -> dict[str, Any]:
    parsed = _parse_datetime(value)
    if not parsed:
        return {"state": "NOT_CERTIFIED", "age_minutes": None, "observed_at": ""}
    age = max(0.0, (datetime.now(MADRID_TZ) - parsed).total_seconds() / 60.0)
    if age <= fresh_minutes:
        state = "VERIFIED"
    elif age <= stale_minutes:
        state = "PARTIALLY_VERIFIED"
    else:
        state = "STALE"
    return {"state": state, "age_minutes": round(age, 1), "observed_at": parsed.isoformat(timespec="seconds")}


def scrub_sensitive(value: Any) -> Any:
    """Remove values that could contain secrets or unnecessary PII."""
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if SENSITIVE_KEY.search(key_text):
                clean[key_text] = "[REDACTED]"
            else:
                clean[key_text] = scrub_sensitive(item)
        return clean
    if isinstance(value, list):
        return [scrub_sensitive(item) for item in value[:500]]
    if isinstance(value, tuple):
        return [scrub_sensitive(item) for item in value[:500]]
    if isinstance(value, str):
        return value[:4000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:1000]


def signal(
    name: str,
    source: str,
    source_type: str,
    app_version: str,
    environment: str,
    certification_state: str,
    evidence: Any,
    *,
    freshness: Any = None,
    confidence: float | None = None,
    limitations: Iterable[str] | None = None,
) -> dict[str, Any]:
    state = certification_state if certification_state in EVIDENCE_STATES else "REQUIRES_REVIEW"
    return {
        "name": str(name),
        "source": str(source),
        "source_type": str(source_type),
        "collected_at_madrid": madrid_now_iso(),
        "freshness": scrub_sensitive(freshness if freshness is not None else {"state": "NOT_CERTIFIED"}),
        "version": str(app_version),
        "environment": str(environment or "local"),
        "confidence": confidence,
        "certification_state": state,
        "evidence": scrub_sensitive(evidence),
        "limitations": [str(item)[:500] for item in (limitations or [])],
    }


def readonly_connection(db_path: str | Path) -> sqlite3.Connection | None:
    path = Path(str(db_path or ""))
    if not path.exists() or not path.is_file():
        return None
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA busy_timeout=1500")
        return conn
    except sqlite3.Error:
        return None


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    try:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)
        ).fetchone() is not None
    except sqlite3.Error:
        return False


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not table_exists(conn, table):
        return set()
    try:
        return {str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
    except sqlite3.Error:
        return set()


def safe_count(conn: sqlite3.Connection, table: str, where: str = "", params: Iterable[Any] = ()) -> int | None:
    if not table_exists(conn, table):
        return None
    query = f'SELECT COUNT(*) FROM "{table}"'
    if where:
        query += " WHERE " + where
    try:
        return int(conn.execute(query, tuple(params)).fetchone()[0])
    except sqlite3.Error:
        return None


def safe_rows(conn: sqlite3.Connection, table: str, limit: int = 500) -> list[dict[str, Any]]:
    if not table_exists(conn, table):
        return []
    try:
        return [dict(row) for row in conn.execute(f'SELECT * FROM "{table}" LIMIT ?', (max(1, min(int(limit), 2000)),)).fetchall()]
    except sqlite3.Error:
        return []


def _first_value(row: dict[str, Any], names: Iterable[str]) -> Any:
    for name in names:
        if row.get(name) not in (None, ""):
            return row.get(name)
    return None


def _complete_match(row: dict[str, Any]) -> bool:
    return bool(
        _first_value(row, ("home_team", "home_name", "home"))
        and _first_value(row, ("away_team", "away_name", "away"))
        and _first_value(row, ("competition_name", "league_name", "competition", "league"))
        and _first_value(row, ("kickoff_at", "match_date", "start_time", "event_date", "date"))
        and _first_value(row, ("source", "provider", "data_source"))
    )


def collect_sports_signals(
    db_path: str | Path,
    app_version: str,
    environment: str = "local",
    sports_metrics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    metrics = dict(sports_metrics or {})
    if metrics.get("contract") == "sports-metrics-v1":
        freshness = classify_freshness(metrics.get("last_sync"), fresh_minutes=60, stale_minutes=360)
        if freshness.get("state") == "STALE":
            state = "STALE"
        elif int(metrics.get("matches_synchronized") or 0) or metrics.get("last_sync"):
            state = "VERIFIED"
        else:
            state = "INSUFFICIENT_DATA"
        return [signal(
            "sports_data",
            "sports-metrics-v1",
            "canonical_snapshot",
            app_version,
            environment,
            state,
            {
                "sports_metrics": metrics,
                "records_total": int(metrics.get("matches_synchronized") or 0),
                "records_complete": int(metrics.get("matches_available") or 0),
                "records_incomplete": int(metrics.get("incomplete_excluded") or 0),
                "last_safe_sync": metrics.get("last_sync") or "",
                "external_calls": 0,
            },
            freshness=freshness,
            confidence=1.0 if state == "VERIFIED" else None,
            limitations=["La presencia local no certifica disponibilidad del proveedor en produccion."],
        )]
    return [signal(
        "sports_data",
        "sports-metrics-v1",
        "contract_required",
        app_version,
        environment,
        "NOT_CERTIFIED",
        {"contract_received": False, "external_calls": 0},
        confidence=None,
        limitations=[
            "Sports Data Contract ausente; Company Intelligence no recalcula metricas por su cuenta."
        ],
    )]


def collect_product_signals(db_path: str | Path, app_version: str, environment: str = "local") -> list[dict[str, Any]]:
    from engines.product_analytics_engine import build_product_analytics_snapshot

    snapshot = build_product_analytics_snapshot(str(db_path), app_version, environment)
    return [signal(
        "product_analytics",
        "product_analytics_engine",
        "aggregated_sqlite_read_only",
        app_version,
        environment,
        snapshot.get("certification_state", "INSUFFICIENT_DATA"),
        snapshot,
        freshness=snapshot.get("freshness"),
        confidence=snapshot.get("confidence"),
        limitations=snapshot.get("limitations", []),
    )]


def collect_customer_signals(db_path: str | Path, app_version: str, environment: str = "local") -> list[dict[str, Any]]:
    signals = collect_product_signals(db_path, app_version, environment)
    signals[0]["name"] = "customer_funnel"
    return signals


def collect_revenue_signals(db_path: str | Path, app_version: str, environment: str = "local") -> list[dict[str, Any]]:
    from engines.product_analytics_engine import build_revenue_analytics_snapshot

    snapshot = build_revenue_analytics_snapshot(str(db_path), app_version, environment)
    return [signal(
        "revenue",
        "stripe local event tables",
        "aggregated_sqlite_read_only",
        app_version,
        environment,
        snapshot.get("certification_state", "NOT_CERTIFIED"),
        snapshot,
        freshness=snapshot.get("freshness"),
        confidence=snapshot.get("confidence"),
        limitations=snapshot.get("limitations", []),
    )]


def collect_pick_signals(db_path: str | Path, app_version: str, environment: str = "local") -> list[dict[str, Any]]:
    from engines.pick_intelligence_pipeline_engine import build_pick_pipeline_snapshot

    snapshot = build_pick_pipeline_snapshot(str(db_path), app_version, environment=environment)
    return [signal(
        "pick_pipeline",
        "pick_intelligence_pipeline_engine",
        "sqlite_read_only",
        app_version,
        environment,
        snapshot.get("certification_state", "INSUFFICIENT_DATA"),
        snapshot,
        freshness=snapshot.get("freshness"),
        confidence=snapshot.get("confidence"),
        limitations=snapshot.get("limitations", []),
    )]


def collect_telegram_signals(
    db_path: str | Path,
    app_version: str,
    environment: str = "local",
    sports_metrics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    from engines.telegram_intelligence_engine import build_telegram_intelligence_snapshot

    snapshot = build_telegram_intelligence_snapshot(
        str(db_path), app_version, environment=environment, sports_metrics=sports_metrics
    )
    return [signal(
        "telegram_intelligence",
        "telegram_intelligence_engine",
        "sqlite_read_only",
        app_version,
        environment,
        snapshot.get("certification_state", "INSUFFICIENT_DATA"),
        snapshot,
        freshness=snapshot.get("freshness"),
        confidence=snapshot.get("confidence"),
        limitations=snapshot.get("limitations", []),
    )]


def collect_operations_signals(
    root: str | Path,
    db_path: str | Path,
    app_version: str,
    environment: str = "local",
    sports_metrics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    try:
        from engines.company_operations_center_engine import build_company_operations_snapshot

        snapshot = build_company_operations_snapshot(root, db_path, app_version, sports_metrics=sports_metrics)
        gate = str((snapshot.get("readiness") or {}).get("local_gate") or "NOT_CERTIFIED")
        state = "VERIFIED" if gate == "PASS" else "REQUIRES_REVIEW"
        evidence = {
            "readiness": snapshot.get("readiness", {}),
            "sports_metrics": snapshot.get("sports_metrics", {}),
            "incident_counts": snapshot.get("incident_counts", {}),
            "next_action": snapshot.get("next_action", ""),
            "mode": snapshot.get("mode", "read_only"),
        }
    except Exception as exc:
        state = "REQUIRES_REVIEW"
        evidence = {"safe_error_type": exc.__class__.__name__, "mode": "read_only"}
    return [signal(
        "operations",
        "company_operations_center_engine",
        "local_engine",
        app_version,
        environment,
        state,
        evidence,
        confidence=1.0 if state == "VERIFIED" else None,
        limitations=["La salud local no certifica Render, GitHub ni proveedores externos."],
    )]


def collect_recovery_signals(root: str | Path, db_path: str | Path, app_version: str, environment: str = "local") -> list[dict[str, Any]]:
    from engines.recovery_simulator_engine import build_recovery_simulator_snapshot

    snapshot = build_recovery_simulator_snapshot(root, db_path, app_version, environment)
    return [signal(
        "recovery",
        "recovery_simulator_engine",
        "simulation_only",
        app_version,
        environment,
        snapshot.get("certification_state", "NOT_CERTIFIED"),
        snapshot,
        confidence=snapshot.get("confidence"),
        limitations=snapshot.get("limitations", []),
    )]


def collect_company_signals(
    root: str | Path,
    db_path: str | Path,
    app_version: str,
    environment: str = "local",
    sports_metrics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    groups = (
        collect_product_signals(db_path, app_version, environment),
        collect_sports_signals(db_path, app_version, environment, sports_metrics),
        collect_pick_signals(db_path, app_version, environment),
        collect_telegram_signals(db_path, app_version, environment, sports_metrics),
        collect_revenue_signals(db_path, app_version, environment),
        collect_operations_signals(root, db_path, app_version, environment, sports_metrics),
        collect_recovery_signals(root, db_path, app_version, environment),
    )
    return [item for group in groups for item in group]


def classify_signal_quality(item: dict[str, Any]) -> dict[str, Any]:
    state = item.get("certification_state")
    rank = {
        "VERIFIED": 100,
        "PARTIALLY_VERIFIED": 70,
        "REQUIRES_REVIEW": 45,
        "NOT_CERTIFIED": 35,
        "STALE": 25,
        "INSUFFICIENT_DATA": 20,
        "NOT_CONFIGURED": 15,
        "BLOCKED_BY_ACCESS": 10,
        "HYPOTHESIS": 5,
    }.get(str(state), 0)
    return {"state": state, "evidence_quality_score": rank, "business_metric": False}


def build_evidence_graph(signals: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = [{
        "id": item.get("name"),
        "source": item.get("source"),
        "state": item.get("certification_state"),
        "quality": classify_signal_quality(item),
    } for item in signals]
    return {
        "nodes": nodes,
        "edges": [{"from": node["id"], "to": "company_decision", "type": "evidence_for"} for node in nodes],
        "limitations": ["El grafo describe procedencia; no demuestra causalidad."],
    }


def calculate_confidence_level(signals: list[dict[str, Any]]) -> dict[str, Any]:
    if not signals:
        return {"score": None, "state": "INSUFFICIENT_DATA", "metric_type": "evidence_coverage"}
    scores = [classify_signal_quality(item)["evidence_quality_score"] for item in signals]
    return {
        "score": round(sum(scores) / len(scores), 1),
        "state": "VERIFIED" if all(score == 100 for score in scores) else "PARTIALLY_VERIFIED",
        "metric_type": "evidence_coverage",
        "not_a_probability": True,
        "sample": len(scores),
    }


def calculate_business_health(signals: list[dict[str, Any]]) -> dict[str, Any]:
    confidence = calculate_confidence_level(signals)
    blockers = sum(1 for item in signals if item.get("certification_state") in {"STALE", "REQUIRES_REVIEW"})
    unknowns = sum(1 for item in signals if item.get("certification_state") in {"NOT_CERTIFIED", "NOT_CONFIGURED", "BLOCKED_BY_ACCESS", "INSUFFICIENT_DATA"})
    return {
        "evidence_coverage_score": confidence.get("score"),
        "certification_state": confidence.get("state"),
        "blockers_or_reviews": blockers,
        "unknown_areas": unknowns,
        "commercial_health_claim_allowed": False,
        "limitations": ["Es cobertura de evidencia, no salud financiera ni probabilidad de exito."],
    }


def build_priority_portfolio(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    severity_for = {
        "STALE": "P1",
        "REQUIRES_REVIEW": "P1",
        "NOT_CONFIGURED": "P2",
        "BLOCKED_BY_ACCESS": "P2",
        "NOT_CERTIFIED": "P2",
        "INSUFFICIENT_DATA": "P3",
        "HYPOTHESIS": "P4",
    }
    priorities = []
    for item in signals:
        state = str(item.get("certification_state") or "REQUIRES_REVIEW")
        if state in {"VERIFIED", "PARTIALLY_VERIFIED"}:
            continue
        priorities.append({
            "priority": severity_for.get(state, "P3"),
            "area": item.get("name"),
            "state": state,
            "evidence": item.get("evidence"),
            "action": f"Obtener evidencia segura para {item.get('name')} y volver a clasificar.",
            "requires_approval": False,
        })
    return sorted(priorities, key=lambda item: (item["priority"], str(item["area"])))


def build_company_next_actions(priorities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = []
    for index, priority in enumerate(priorities[:10], start=1):
        actions.append({
            "order": index,
            "area": priority.get("area"),
            "action": priority.get("action"),
            "approval": "REQUIRES_REVIEW" if priority.get("priority") in {"P0", "P1"} else "NOT_REQUIRED_FOR_EVIDENCE_COLLECTION",
        })
    return actions


def build_executive_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    priorities = snapshot.get("priorities", [])
    health = snapshot.get("business_health", {})
    return {
        "headline": "Empresa observable con decisiones bajo control humano",
        "certification_state": health.get("certification_state", "NOT_CERTIFIED"),
        "evidence_coverage_score": health.get("evidence_coverage_score"),
        "priority_count": len(priorities),
        "top_priority": priorities[0] if priorities else None,
        "production_claim": "NOT_CERTIFIED",
        "safe_message": "Se muestran unicamente senales locales trazables; las areas sin muestra permanecen sin certificar.",
    }


def generate_codex_company_prompt(snapshot: dict[str, Any], priority_id: str = "") -> str:
    priorities = snapshot.get("priorities", [])
    selected = next((item for item in priorities if str(item.get("area")) == str(priority_id)), None)
    selected = selected or (priorities[0] if priorities else {})
    return "\n".join((
        f"NeMeSiS SHARK PRO {snapshot.get('version', '')}",
        "Investiga esta prioridad con evidencia y sin modificar produccion.",
        f"Area: {selected.get('area', 'sin prioridad pendiente')}",
        f"Estado: {selected.get('state', 'NOT_CERTIFIED')}",
        f"Accion propuesta: {selected.get('action', 'Recopilar evidencia segura.')}",
        "No uses datos sinteticos como reales. No despliegues, no envies Telegram, no cobres y no alteres pesos SHARK.",
        "Propone el cambio minimo, pruebas, riesgos, rollback y aprobacion necesaria.",
    ))


def build_company_intelligence_snapshot(
    root: str | Path,
    db_path: str | Path,
    app_version: str,
    environment: str = "local",
    sports_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from engines.sentinel_autopilot_engine import build_customer_trust_icon_contract_snapshot

    signals = collect_company_signals(root, db_path, app_version, environment, sports_metrics)
    priorities = build_priority_portfolio(signals)
    product_quality_learning = build_customer_trust_icon_contract_snapshot(root, app_version)
    snapshot: dict[str, Any] = {
        "ok": True,
        "version": app_version,
        "environment": environment,
        "generated_at_madrid": madrid_now_iso(),
        "sports_metrics": dict(sports_metrics or {}),
        "mode": "read_only",
        "signals": signals,
        "evidence_graph": build_evidence_graph(signals),
        "confidence": calculate_confidence_level(signals),
        "business_health": calculate_business_health(signals),
        "priorities": priorities,
        "next_actions": build_company_next_actions(priorities),
        "product_quality_learning": [product_quality_learning],
        "production_modified": False,
        "external_calls": 0,
        "database_written": False,
        "telegram_sent": False,
        "payment_executed": False,
        "weights_modified": False,
        "deployment_executed": False,
    }
    snapshot["executive_summary"] = build_executive_summary(snapshot)
    return scrub_sensitive(snapshot)


def _memory_path(root: str | Path) -> Path:
    return Path(root) / "data" / "runtime" / "company_intelligence_memory.json"


def load_company_intelligence_memory(root: str | Path) -> dict[str, Any]:
    path = _memory_path(root)
    if not path.exists():
        return {"schema": "v939_company_intelligence_memory_v1", "snapshots": [], "decisions": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("memory root must be an object")
        return scrub_sensitive(payload)
    except (OSError, ValueError, json.JSONDecodeError):
        return {"schema": "v939_company_intelligence_memory_v1", "snapshots": [], "decisions": [], "read_state": "REQUIRES_REVIEW"}


def save_company_intelligence_memory(root: str | Path, snapshot: dict[str, Any]) -> Path:
    """Persist a scrubbed snapshot. Call only from an authorized POST/Cron."""
    path = _memory_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = load_company_intelligence_memory(root)
    snapshots = list(payload.get("snapshots") or [])
    snapshots.append(scrub_sensitive(snapshot))
    payload.update({
        "schema": "v939_company_intelligence_memory_v1",
        "updated_at_madrid": madrid_now_iso(),
        "snapshots": snapshots[-MAX_MEMORY_SNAPSHOTS:],
        "decisions": list(payload.get("decisions") or [])[-MAX_MEMORY_DECISIONS:],
    })
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return path


def record_company_intelligence_decision(
    root: str | Path,
    recommendation_id: str,
    decision: str,
    note: str = "",
) -> dict[str, Any]:
    recommendation_id = str(recommendation_id or "").strip()
    normalized = str(decision or "").strip().upper()
    if not recommendation_id:
        return {"ok": False, "error": "recommendation_id_required"}
    if normalized not in {"APPROVED", "REJECTED"}:
        return {"ok": False, "error": "invalid_decision"}
    payload = load_company_intelligence_memory(root)
    decisions = list(payload.get("decisions") or [])
    decisions.append({
        "recommendation_id": recommendation_id[:160],
        "decision": normalized,
        "note": str(note or "")[:500],
        "decided_at_madrid": madrid_now_iso(),
        "automatic_execution": False,
    })
    payload["decisions"] = decisions[-MAX_MEMORY_DECISIONS:]
    path = _memory_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(scrub_sensitive(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return {"ok": True, "recommendation_id": recommendation_id, "decision": normalized, "automatic_execution": False}

