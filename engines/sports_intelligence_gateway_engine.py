"""Legal and evidence-first Sports Intelligence Gateway.

This module is the single pre-ingestion gate for future sports information
sources. It registers and evaluates source metadata only. It does not connect
to providers, scrape websites, call APIs, download images, write databases,
send Telegram messages, charge Stripe, or authorize commercial reuse without a
clear compliance state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping

from engines.sports_platform_contracts import EVIDENCE_STATES


SPORTS_INTELLIGENCE_GATEWAY_CONTRACT = "SPORTS-INTELLIGENCE-GATEWAY-V1"
SOURCE_REGISTRY_CONTRACT = "SOURCE-REGISTRY-V1"
SOURCE_COMPLIANCE_CONTRACT = "SOURCE-COMPLIANCE-SYSTEM-V1"
SOURCE_HEALTH_CONTRACT = "SOURCE-HEALTH-MONITOR-V1"
SOURCE_EVIDENCE_CONTRACT = "SOURCE-EVIDENCE-REGISTRY-V1"

SOURCE_TYPES = ("API", "RSS", "OPEN_DATA", "OFFICIAL_WEB", "MANUAL_REVIEW")
SOURCE_STATES = (
    "REGISTERED",
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "SUSPENDED",
    "NOT_CONFIGURED",
    "BLOCKED_BY_ACCESS",
)

BLOCKED_PRACTICES = (
    "mass_scraping",
    "robots_bypass",
    "paywall_bypass",
    "article_copying",
    "protected_image_reuse",
    "unlicensed_content_reuse",
)


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _state(value: Any, *, allowed: Iterable[str], fallback: str) -> str:
    candidate = _text(value, 80).upper().replace(" ", "_").replace("-", "_")
    allowed_set = set(allowed)
    return candidate if candidate in allowed_set else fallback


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _bool_or_unknown(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in {"yes", "true", "allowed", "permitido", "commercial"}:
            return True
        if candidate in {"no", "false", "blocked", "prohibido"}:
            return False
    return None


def _safe_timestamp(value: Any) -> str:
    raw = _text(value, 80)
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return raw


@dataclass(frozen=True)
class SourceRegistration:
    source_id: str
    name: str
    license: str
    provenance: str
    source_type: str
    state: str
    coverage: str
    quality: str
    latency: str
    last_sync: str
    commercial_use_allowed: bool | None
    attribution_required: bool | None
    api: str
    rss: str
    open_data: str
    official_web: str
    limitations: tuple[str, ...]
    approval_required: bool = True
    connection_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def register_source(metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Normalize a source registration without connecting it."""

    data = dict(metadata or {})
    source_id = _text(data.get("source_id") or data.get("id") or data.get("name"), 100)
    source_type = _state(data.get("type") or data.get("source_type"), allowed=SOURCE_TYPES, fallback="MANUAL_REVIEW")
    registration = SourceRegistration(
        source_id=source_id or "source-pending-id",
        name=_text(data.get("name"), 140) or "Fuente pendiente de identificar",
        license=_text(data.get("license"), 160) or "No disponible",
        provenance=_text(data.get("provenance") or data.get("source"), 180) or "No disponible",
        source_type=source_type,
        state=_state(data.get("state"), allowed=SOURCE_STATES, fallback="REGISTERED"),
        coverage=_text(data.get("coverage"), 180) or "No disponible",
        quality=_text(data.get("quality"), 100) or "REQUIRES_REVIEW",
        latency=_text(data.get("latency"), 100) or "No disponible",
        last_sync=_safe_timestamp(data.get("last_sync") or data.get("last_synced_at")),
        commercial_use_allowed=_bool_or_unknown(data.get("commercial_use_allowed")),
        attribution_required=_bool_or_unknown(data.get("attribution_required")),
        api=_text(data.get("api"), 180),
        rss=_text(data.get("rss"), 180),
        open_data=_text(data.get("open_data"), 180),
        official_web=_text(data.get("official_web"), 180),
        limitations=tuple(_text(item, 180) for item in data.get("limitations") or [] if _text(item, 180)),
    )
    return registration.to_dict()


def evaluate_source_compliance(source: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate legal readiness for a registered source."""

    item = dict(source or {})
    missing: list[str] = []
    for key in ("license", "provenance", "source_type", "coverage", "quality"):
        if not _text(item.get(key)) or _text(item.get(key)).lower() == "no disponible":
            missing.append(key)
    if item.get("commercial_use_allowed") is not True:
        missing.append("commercial_use_allowed")
    if item.get("attribution_required") is None:
        missing.append("attribution_required")
    approved = not missing and item.get("state") == "APPROVED"
    return {
        "contract": SOURCE_COMPLIANCE_CONTRACT,
        "source_id": _text(item.get("source_id"), 100),
        "state": "APPROVED" if approved else "PENDING_APPROVAL",
        "commercial_use_allowed": item.get("commercial_use_allowed"),
        "attribution_required": item.get("attribution_required"),
        "missing_requirements": missing,
        "blocked_practices": list(BLOCKED_PRACTICES),
        "connection_allowed": approved,
        "requires_human_approval": not approved,
        "limitations": list(item.get("limitations") or []),
    }


def build_source_health(source: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Describe source health without polling the source."""

    item = dict(source or {})
    last_sync = _text(item.get("last_sync"), 100)
    status = "NOT_CONFIGURED"
    if last_sync:
        status = "REGISTERED_NOT_CONNECTED"
    if item.get("state") == "APPROVED":
        status = "APPROVED_NOT_CONNECTED"
    return {
        "contract": SOURCE_HEALTH_CONTRACT,
        "source_id": _text(item.get("source_id"), 100),
        "status": status,
        "latency": _text(item.get("latency"), 100) or "No disponible",
        "last_sync": last_sync or "No disponible",
        "quality": _text(item.get("quality"), 100) or "REQUIRES_REVIEW",
        "coverage": _text(item.get("coverage"), 180) or "No disponible",
        "external_probe_performed": False,
        "automatic_connection": False,
    }


def build_source_evidence_record(
    *,
    source: Mapping[str, Any] | None = None,
    data_point: Mapping[str, Any] | None = None,
    observed_at_madrid: Any = "",
) -> dict[str, Any]:
    """Wrap one future data point with required provenance metadata."""

    src = dict(source or {})
    point = dict(data_point or {})
    evidence_state = _state(
        point.get("evidence_state") or src.get("evidence_state"),
        allowed=EVIDENCE_STATES,
        fallback="REQUIRES_REVIEW",
    )
    if not _text(src.get("source_id")):
        evidence_state = "INSUFFICIENT_DATA"
    return {
        "contract": SOURCE_EVIDENCE_CONTRACT,
        "source_id": _text(src.get("source_id"), 100) or "source-pending-id",
        "data_type": _text(point.get("data_type"), 100) or "No disponible",
        "provenance": _text(src.get("provenance"), 180) or "No disponible",
        "freshness": _text(point.get("freshness") or src.get("last_sync"), 100) or "No disponible",
        "evidence": _text(point.get("evidence"), 220) or "No disponible",
        "quality": _text(point.get("quality") or src.get("quality"), 100) or "REQUIRES_REVIEW",
        "limitations": list(point.get("limitations") or src.get("limitations") or []),
        "certification_state": evidence_state,
        "observed_at_madrid": _text(observed_at_madrid, 100),
        "commercial_use_allowed": src.get("commercial_use_allowed"),
        "attribution_required": src.get("attribution_required"),
    }


def build_sports_intelligence_gateway_snapshot(
    sources: Iterable[Mapping[str, Any]] | None = None,
    *,
    observed_at_madrid: Any = "",
) -> dict[str, Any]:
    """Build the complete local-only Gateway snapshot."""

    registrations = [register_source(item) for item in _items(list(sources or []))]
    compliance = [evaluate_source_compliance(item) for item in registrations]
    health = [build_source_health(item) for item in registrations]
    evidence = [
        build_source_evidence_record(source=item, observed_at_madrid=observed_at_madrid)
        for item in registrations
    ]
    approved = [item for item in compliance if item.get("connection_allowed") is True]
    pending = [item for item in compliance if item.get("connection_allowed") is not True]
    return {
        "contract": SPORTS_INTELLIGENCE_GATEWAY_CONTRACT,
        "source_registry_contract": SOURCE_REGISTRY_CONTRACT,
        "source_compliance_contract": SOURCE_COMPLIANCE_CONTRACT,
        "source_health_contract": SOURCE_HEALTH_CONTRACT,
        "source_evidence_contract": SOURCE_EVIDENCE_CONTRACT,
        "sources": registrations,
        "compliance": compliance,
        "health": health,
        "evidence_registry": evidence,
        "summary": {
            "registered_sources": len(registrations),
            "approved_sources": len(approved),
            "pending_sources": len(pending),
            "connected_sources": 0,
            "automatic_connections": 0,
        },
        "legal_policy": {
            "must_register_before_use": True,
            "must_approve_before_use": True,
            "mass_scraping_allowed": False,
            "robots_bypass_allowed": False,
            "paywall_bypass_allowed": False,
            "article_copying_allowed": False,
            "protected_image_reuse_allowed": False,
            "unlicensed_content_reuse_allowed": False,
            "blocked_practices": list(BLOCKED_PRACTICES),
        },
        "data_contract": {
            "provenance_required": True,
            "freshness_required": True,
            "evidence_required": True,
            "quality_required": True,
            "limitations_required": True,
            "no_fake_data": True,
        },
        "guardrails": {
            "external_calls": 0,
            "database_writes": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "scraping_jobs_started": 0,
            "paywall_access_attempts": 0,
            "provider_connections_enabled": 0,
            "automatic_source_approval": 0,
        },
        "observed_at_madrid": _text(observed_at_madrid, 100),
        "production_modified": False,
    }


def sports_intelligence_gateway_snapshot() -> dict[str, Any]:
    """Expose static metadata for checks and registries."""

    return {
        "contract": SPORTS_INTELLIGENCE_GATEWAY_CONTRACT,
        "source_registry_contract": SOURCE_REGISTRY_CONTRACT,
        "source_compliance_contract": SOURCE_COMPLIANCE_CONTRACT,
        "source_health_contract": SOURCE_HEALTH_CONTRACT,
        "source_evidence_contract": SOURCE_EVIDENCE_CONTRACT,
        "allowed_source_types": list(SOURCE_TYPES),
        "allowed_source_states": list(SOURCE_STATES),
        "blocked_practices": list(BLOCKED_PRACTICES),
        "guardrails": {
            "external_calls": 0,
            "database_writes": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "provider_connections_enabled": 0,
        },
    }
