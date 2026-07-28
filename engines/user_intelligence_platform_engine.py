"""Privacy-first User Intelligence Platform for NeMeSiS.

This module is a pure analysis layer. It receives already-collected first-party
usage signals and builds a transparent sports preference profile. It does not
query databases, call providers, send Telegram messages, charge Stripe, run
generative AI, infer sensitive traits or apply product personalization
automatically.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Iterable, Mapping

from engines.match_intelligence_engine import MATCH_INTELLIGENCE_CONTRACT
from engines.shark_intelligence_platform_engine import SHARK_INTELLIGENCE_PLATFORM_CONTRACT
from engines.sports_domain_model_engine import SPORTS_DOMAIN_MODEL_CONTRACT
from engines.sports_graph_foundation_engine import SPORTS_GRAPH_FOUNDATION_CONTRACT
from engines.sports_knowledge_layer_engine import SPORTS_KNOWLEDGE_LAYER_CONTRACT


USER_INTELLIGENCE_PLATFORM_CONTRACT = "USER-INTELLIGENCE-PLATFORM-V1"
USER_INTELLIGENCE_PRIVACY_CONTRACT = "USER-PRIVACY-CONTROLS-V1"

ALLOWED_EVIDENCE_STATES = {
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

ALLOWED_LANGUAGE = {"es", "en"}
ALLOWED_THEME = {"system", "dark", "compact", "comfortable"}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _state(value: Any) -> str:
    candidate = _text(value, 60).upper()
    return candidate if candidate in ALLOWED_EVIDENCE_STATES else "REQUIRES_REVIEW"


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _payload(item: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(item.get("payload") or item.get("payload_json"))


def _hour_from_iso(value: Any) -> str:
    raw = _text(value, 64)
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return f"{parsed.hour:02d}:00"
    except ValueError:
        return ""


def _counter_to_ranked(counter: Counter[str], *, source: str, limit: int = 6) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for label, count in counter.most_common(limit):
        text = _text(label, 120)
        if not text:
            continue
        ranked.append(
            {
                "label": text,
                "count": int(count),
                "source": source,
                "evidence_state": "VERIFIED",
                "limitations": [],
            }
        )
    return ranked


def default_user_intelligence_preferences() -> dict[str, Any]:
    return {
        "personalization_enabled": False,
        "consent_state": "NOT_GRANTED",
        "history_enabled": True,
        "remember_filters": False,
        "language": "es",
        "visual_preference": "system",
        "retention_days": 90,
        "updated_at_madrid": "",
        "last_action": "default",
    }


def sanitize_user_intelligence_preferences(
    current: Mapping[str, Any] | None = None,
    updates: Mapping[str, Any] | None = None,
    *,
    action: str = "update",
    observed_at_madrid: Any = "",
) -> dict[str, Any]:
    """Return safe preferences for the first-party personalization profile."""

    preferences = default_user_intelligence_preferences()
    preferences.update(_mapping(current))
    incoming = _mapping(updates)
    action_key = _text(action, 40).lower()

    if action_key == "enable":
        preferences["personalization_enabled"] = True
        preferences["consent_state"] = "GRANTED"
    elif action_key == "disable":
        preferences["personalization_enabled"] = False
        preferences["consent_state"] = "DISABLED"
    elif action_key == "reset":
        preferences = default_user_intelligence_preferences()
        preferences["consent_state"] = "RESET"
    elif action_key == "delete":
        preferences = default_user_intelligence_preferences()
        preferences["consent_state"] = "DELETED"
    else:
        if "personalization_enabled" in incoming:
            preferences["personalization_enabled"] = bool(incoming.get("personalization_enabled"))
            preferences["consent_state"] = "GRANTED" if preferences["personalization_enabled"] else "DISABLED"
        if "history_enabled" in incoming:
            preferences["history_enabled"] = bool(incoming.get("history_enabled"))
        if "remember_filters" in incoming:
            preferences["remember_filters"] = bool(incoming.get("remember_filters"))
        language = _text(incoming.get("language"), 12).lower()
        if language in ALLOWED_LANGUAGE:
            preferences["language"] = language
        visual = _text(incoming.get("visual_preference"), 24).lower()
        if visual in ALLOWED_THEME:
            preferences["visual_preference"] = visual
        retention = _safe_int(incoming.get("retention_days"))
        if 1 <= retention <= 365:
            preferences["retention_days"] = retention

    preferences["updated_at_madrid"] = _text(observed_at_madrid, 80)
    preferences["last_action"] = action_key or "update"
    return preferences


def build_user_privacy_state(
    preferences: Mapping[str, Any] | None = None,
    *,
    stored_counts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    prefs = default_user_intelligence_preferences()
    prefs.update(_mapping(preferences))
    counts = _mapping(stored_counts)
    enabled = bool(prefs.get("personalization_enabled"))
    return {
        "contract": USER_INTELLIGENCE_PRIVACY_CONTRACT,
        "personalization_enabled": enabled,
        "consent_state": _text(prefs.get("consent_state") or ("GRANTED" if enabled else "NOT_GRANTED"), 40),
        "controls": {
            "view_stored_data": True,
            "export_preferences": True,
            "reset_preferences": True,
            "delete_profile": True,
            "disable_personalization": True,
        },
        "stored_data": {
            "first_party_usage_events": _safe_int(counts.get("activity")),
            "favorites": _safe_int(counts.get("favorites")),
            "preferences_profile": bool(prefs),
        },
        "not_stored": [
            "tokens",
            "passwords",
            "payment_cards",
            "full_ip_address",
            "device_fingerprint",
            "private_messages",
            "sensitive_personal_traits",
            "third_party_exports",
        ],
        "data_leaves_nemesis": False,
        "third_party_sale": False,
        "generative_ai_used": False,
        "automatic_home_changes": False,
    }


def _collect_signals(
    *,
    activity: Iterable[Mapping[str, Any]],
    favorites: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    teams: Counter[str] = Counter()
    competitions: Counter[str] = Counter()
    matches: Counter[str] = Counter()
    filters: Counter[str] = Counter()
    modules: Counter[str] = Counter()
    hours: Counter[str] = Counter()
    markets: Counter[str] = Counter()
    ignored: Counter[str] = Counter()

    for fav in _items(list(favorites)):
        kind = _text(fav.get("kind"), 40).lower()
        value = _text(fav.get("label") or fav.get("value"), 160)
        if kind == "team":
            teams[value] += 3
        elif kind in {"league", "competition"}:
            competitions[value] += 3
        elif kind == "match":
            matches[value] += 3

    for item in _items(list(activity)):
        activity_type = _text(item.get("activity_type"), 80).lower()
        target_type = _text(item.get("target_type"), 80).lower()
        target_id = _text(item.get("target_id"), 160)
        payload = _payload(item)
        if target_type:
            modules[target_type] += 1
        if activity_type and activity_type not in {"view", "click"}:
            modules[activity_type] += 1
        if target_type == "team":
            teams[_text(payload.get("team_name") or payload.get("label") or target_id, 160)] += 1
        if target_type in {"league", "competition"}:
            competitions[_text(payload.get("competition_name") or payload.get("league_name") or payload.get("label") or target_id, 160)] += 1
        if target_type == "match":
            matches[_text(payload.get("match_title") or payload.get("label") or target_id, 160)] += 1
            teams[_text(payload.get("home_team"), 160)] += 1 if payload.get("home_team") else 0
            teams[_text(payload.get("away_team"), 160)] += 1 if payload.get("away_team") else 0
            competitions[_text(payload.get("competition_name") or payload.get("league_name"), 160)] += 1 if (payload.get("competition_name") or payload.get("league_name")) else 0
        lane = _text(payload.get("lane") or payload.get("filter") or payload.get("tab"), 80)
        if lane:
            filters[lane] += 1
        market = _text(payload.get("market") or payload.get("pick_type"), 80)
        if market:
            markets[market] += 1
        hour = _hour_from_iso(item.get("created_at"))
        if hour:
            hours[hour] += 1

    for key in {"telegram", "picks", "combis", "shark", "calendar", "live"}:
        if modules.get(key) == 0:
            ignored[key] = 1

    return {
        "teams": _counter_to_ranked(teams, source="favorites_and_activity"),
        "competitions": _counter_to_ranked(competitions, source="favorites_and_activity"),
        "matches": _counter_to_ranked(matches, source="favorites_and_activity"),
        "filters": _counter_to_ranked(filters, source="activity_payload"),
        "modules": _counter_to_ranked(modules, source="user_activity"),
        "hours": _counter_to_ranked(hours, source="activity_created_at"),
        "markets": _counter_to_ranked(markets, source="activity_payload"),
        "ignored_content": _counter_to_ranked(ignored, source="absence_in_recent_activity"),
    }


def _confidence(total_events: int, favorites_count: int) -> dict[str, Any]:
    if total_events >= 20 or favorites_count >= 5:
        return {"state": "PARTIALLY_VERIFIED", "label": "Muestra razonable", "score": 70}
    if total_events >= 5 or favorites_count:
        return {"state": "PARTIALLY_VERIFIED", "label": "Muestra limitada", "score": 45}
    return {"state": "INSUFFICIENT_DATA", "label": "Datos insuficientes", "score": 15}


def build_user_intelligence_platform_snapshot(
    *,
    user: Mapping[str, Any] | None = None,
    activity: Iterable[Mapping[str, Any]] = (),
    favorites: Iterable[Mapping[str, Any]] = (),
    preferences: Mapping[str, Any] | None = None,
    sports_contracts: Mapping[str, Any] | None = None,
    shark_intelligence: Mapping[str, Any] | None = None,
    observed_at_madrid: Any = "",
) -> dict[str, Any]:
    """Build a privacy-safe first-party user sports intelligence snapshot."""

    safe_user = _mapping(user)
    activity_items = _items(list(activity))
    favorite_items = _items(list(favorites))
    prefs = default_user_intelligence_preferences()
    prefs.update(_mapping(preferences))
    contracts = _mapping(sports_contracts)
    shark = _mapping(shark_intelligence)
    signals = _collect_signals(activity=activity_items, favorites=favorite_items)
    event_count = len(activity_items)
    favorite_count = len(favorite_items)
    confidence = _confidence(event_count, favorite_count)
    privacy = build_user_privacy_state(
        prefs,
        stored_counts={"activity": event_count, "favorites": favorite_count},
    )
    enabled = bool(prefs.get("personalization_enabled")) and privacy.get("consent_state") == "GRANTED"

    signal_count = sum(len(signals[key]) for key in signals)
    certification_state = confidence["state"] if signal_count else "INSUFFICIENT_DATA"
    if not enabled:
        certification_state = "NOT_CONFIGURED" if signal_count else "INSUFFICIENT_DATA"

    recommendations: list[dict[str, Any]] = []
    if signals["teams"]:
        recommendations.append(
            {
                "id": "future-highlight-teams",
                "title": "Destacar equipos consultados",
                "state": "PREPARED_NOT_APPLIED",
                "evidence": [item["label"] for item in signals["teams"][:3]],
                "requires_consent": True,
            }
        )
    if signals["competitions"]:
        recommendations.append(
            {
                "id": "future-highlight-competitions",
                "title": "Destacar competiciones consultadas",
                "state": "PREPARED_NOT_APPLIED",
                "evidence": [item["label"] for item in signals["competitions"][:3]],
                "requires_consent": True,
            }
        )
    if signals["filters"] and bool(prefs.get("remember_filters")):
        recommendations.append(
            {
                "id": "future-remember-filters",
                "title": "Recordar filtros usados",
                "state": "PREPARED_NOT_APPLIED",
                "evidence": [item["label"] for item in signals["filters"][:3]],
                "requires_consent": True,
            }
        )

    modules = [
        {
            "key": "sports_core",
            "name": "Sports Core",
            "contract": SPORTS_DOMAIN_MODEL_CONTRACT,
            "state": "AVAILABLE",
            "role": "validar entidades deportivas antes de personalizar",
        },
        {
            "key": "sports_knowledge",
            "name": "Sports Knowledge",
            "contract": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
            "state": "AVAILABLE",
            "role": "contextualizar equipos y competiciones consultadas",
        },
        {
            "key": "sports_graph",
            "name": "Sports Graph",
            "contract": SPORTS_GRAPH_FOUNDATION_CONTRACT,
            "state": "AVAILABLE",
            "role": "relacionar usuario con entidades por uso propio observado",
        },
        {
            "key": "match_intelligence",
            "name": "Match Intelligence",
            "contract": MATCH_INTELLIGENCE_CONTRACT,
            "state": "AVAILABLE",
            "role": "explicar partidos consultados sin generar predicciones",
        },
        {
            "key": "shark_intelligence",
            "name": "SHARK Intelligence",
            "contract": shark.get("contract") or SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
            "state": "AVAILABLE" if shark else "CONTRACT_READY",
            "role": "mostrar contexto deportivo disponible con transparencia",
        },
    ]

    missing: list[str] = []
    if not event_count:
        missing.append("No hay actividad reciente suficiente para aprender preferencias.")
    if not favorite_count:
        missing.append("No hay favoritos guardados.")
    if not enabled:
        missing.append("La personalizacion no esta activada por consentimiento.")
    if not signals["markets"]:
        missing.append("No hay mercados consultados con evidencia propia.")
    if not shark:
        missing.append("No se recibio snapshot SHARK Intelligence completo.")

    return {
        "ok": True,
        "contract": USER_INTELLIGENCE_PLATFORM_CONTRACT,
        "privacy_contract": USER_INTELLIGENCE_PRIVACY_CONTRACT,
        "source_contracts": {
            "sports_domain_model": SPORTS_DOMAIN_MODEL_CONTRACT,
            "sports_knowledge": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
            "sports_graph": SPORTS_GRAPH_FOUNDATION_CONTRACT,
            "match_intelligence": MATCH_INTELLIGENCE_CONTRACT,
            "shark_intelligence": shark.get("contract") or SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
        },
        "observed_at_madrid": _text(observed_at_madrid, 100),
        "certification_state": certification_state,
        "summary": {
            "headline": "Personalizacion preparada" if enabled else "Personalizacion bajo control del usuario",
            "body": (
                "NeMeSiS puede preparar accesos y preferencias usando solo actividad propia observada."
                if enabled
                else "La plataforma muestra lo almacenado y no aplica personalizacion automatica sin consentimiento."
            ),
            "next_action": "Activar personalizacion" if not enabled else "Revisar o ajustar preferencias",
        },
        "user_context": {
            "user_id_present": bool(safe_user.get("id")),
            "membership": _text(safe_user.get("membership") or safe_user.get("role") or "FREE", 40),
            "email_included": False,
            "name_included": False,
        },
        "preferences": prefs,
        "privacy": privacy,
        "signals": signals,
        "metrics": {
            "activity_events": event_count,
            "favorites": favorite_count,
            "teams_observed": len(signals["teams"]),
            "competitions_observed": len(signals["competitions"]),
            "matches_observed": len(signals["matches"]),
            "filters_observed": len(signals["filters"]),
            "modules_observed": len(signals["modules"]),
            "markets_observed": len(signals["markets"]),
            "recommendations_prepared": len(recommendations),
        },
        "confidence": confidence,
        "modules": modules,
        "recommendations": recommendations,
        "personalization": {
            "enabled": enabled,
            "automatic_home_personalization": False,
            "prepared_only": True,
            "future_uses": [
                "destacar equipos favoritos",
                "destacar competiciones favoritas",
                "destacar proximos partidos relevantes",
                "recordar filtros utilizados",
                "personalizar accesos rapidos",
            ],
            "blocked_without_consent": True,
        },
        "missing_information": missing[:12],
        "limitations": [
            "No infiere gustos no respaldados por comportamiento observado.",
            "No utiliza datos sensibles ajenos al uso de NeMeSiS.",
            "No cambia la Home automaticamente en esta fase.",
            "No envia datos a terceros.",
        ],
        "diagnostics": {
            "database_reads_expected": True,
            "database_writes_by_get": 0,
            "database_writes_allowed_for_privacy_actions": True,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "automatic_actions": 0,
            "third_party_exports": 0,
            "fake_data_created": 0,
        },
        "no_fake_data": True,
        "no_predictions": True,
        "no_generative_ai": True,
        "transparent": True,
        "user_controlled": True,
    }


def user_intelligence_platform_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        "contract": USER_INTELLIGENCE_PLATFORM_CONTRACT,
        "privacy_contract": USER_INTELLIGENCE_PRIVACY_CONTRACT,
        "requires": [
            SPORTS_DOMAIN_MODEL_CONTRACT,
            SPORTS_KNOWLEDGE_LAYER_CONTRACT,
            SPORTS_GRAPH_FOUNDATION_CONTRACT,
            MATCH_INTELLIGENCE_CONTRACT,
            SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
        ],
        "guardrails": {
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "automatic_home_changes": 0,
            "third_party_exports": 0,
            "fake_data_created": 0,
            "predictions_created": 0,
        },
        "privacy_controls": {
            "view_stored_data": True,
            "export_preferences": True,
            "reset_preferences": True,
            "delete_profile": True,
            "disable_personalization": True,
        },
    }
