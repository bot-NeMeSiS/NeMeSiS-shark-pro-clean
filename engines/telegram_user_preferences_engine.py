"""Personal Telegram focus preferences for NeMeSiS SHARK PRO.

Pure helpers: no DB writes, no Telegram calls and no external providers.
The global channel stays curated; private PRO/ELITE delivery can be focused
by league, message type and a hard daily budget.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Mapping

TELEGRAM_USER_PREFERENCES_CONTRACT = "NEMESIS-TELEGRAM-USER-FOCUS-V1"

LEAGUE_OPTIONS = (
    {"key": "laliga", "label": "LaLiga", "terms": ("laliga", "la liga", "primera division spain", "primera división spain")},
    {"key": "segunda", "label": "Segunda División", "terms": ("segunda division", "segunda división", "laliga 2", "hypermotion")},
    {"key": "premier", "label": "Premier League", "terms": ("premier league",)},
    {"key": "champions", "label": "Champions League", "terms": ("champions league", "uefa champions")},
    {"key": "europa", "label": "Europa League", "terms": ("europa league",)},
    {"key": "conference", "label": "Conference League", "terms": ("conference league",)},
    {"key": "serie_a", "label": "Serie A", "terms": ("serie a",)},
    {"key": "bundesliga", "label": "Bundesliga", "terms": ("bundesliga",)},
    {"key": "ligue_1", "label": "Ligue 1", "terms": ("ligue 1",)},
    {"key": "primeira", "label": "Primeira Liga", "terms": ("primeira liga", "liga portugal")},
    {"key": "eredivisie", "label": "Eredivisie", "terms": ("eredivisie",)},
    {"key": "copa_rey", "label": "Copa del Rey", "terms": ("copa del rey",)},
    {"key": "world_cup", "label": "Mundial FIFA", "terms": ("world cup", "mundial", "copa mundial", "fifa world cup")},
    {"key": "euro", "label": "Eurocopa / Nations League", "terms": ("eurocopa", "uefa euro", "nations league")},
    {"key": "libertadores", "label": "Libertadores", "terms": ("libertadores",)},
)

MESSAGE_TYPE_OPTIONS = (
    {"key": "summaries", "label": "Resúmenes"},
    {"key": "picks", "label": "Pronósticos SHARK"},
    {"key": "live", "label": "Alertas en directo"},
    {"key": "results", "label": "Resultados"},
    {"key": "prematch", "label": "Recordatorios prepartido"},
    {"key": "highlights", "label": "Vídeos / resúmenes disponibles"},
    {"key": "combis", "label": "Combinadas"},
)

GLOBAL_CHANNEL_ALLOWED_TYPES = {
    "daily_summary",
    "daily_matches",
    "daily_picks",
    "evening_recap",
}

_MESSAGE_GROUPS = {
    "daily_summary": "summaries",
    "daily_matches": "summaries",
    "midday_update": "summaries",
    "evening_recap": "summaries",
    "daily_picks": "picks",
    "pick_alert": "picks",
    "auto_pick": "picks",
    "recommendation": "picks",
    "live_alert": "live",
    "result_final": "results",
    "pick_result": "results",
    "prematch_reminder": "prematch",
    "highlight_available": "highlights",
    "combi_alert": "combis",
}

_PLAN_POLICY = {
    "FREE": {
        "custom_leagues": False,
        "league_limit": 0,
        "categories": ("summaries",),
        "daily_limit": 2,
        "daily_limit_max": 2,
        "intensity": "essential",
    },
    "PRO": {
        "custom_leagues": True,
        "league_limit": 8,
        "categories": ("summaries", "picks", "results"),
        "daily_limit": 4,
        "daily_limit_max": 8,
        "intensity": "balanced",
    },
    "ELITE": {
        "custom_leagues": True,
        "league_limit": 15,
        "categories": ("summaries", "picks", "live", "results", "prematch", "highlights", "combis"),
        "daily_limit": 6,
        "daily_limit_max": 12,
        "intensity": "balanced",
    },
    "ADMIN": {
        "custom_leagues": True,
        "league_limit": 15,
        "categories": ("summaries", "picks", "live", "results", "prematch", "highlights", "combis"),
        "daily_limit": 8,
        "daily_limit_max": 20,
        "intensity": "balanced",
    },
}


def _plan(value: Any) -> str:
    text = str(value or "FREE").strip().upper().replace(" ", "")
    if text in {"ELITE+", "ELITEPLUS", "ELITE_PLUS"}:
        return "ELITE"
    return text if text in _PLAN_POLICY else "FREE"


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return re.sub(r"\s+", " ", text).strip()


def _bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def plan_telegram_policy(membership: Any) -> dict[str, Any]:
    plan = _plan(membership)
    return {"plan": plan, **dict(_PLAN_POLICY[plan])}


def default_telegram_user_preferences(membership: Any) -> dict[str, Any]:
    policy = plan_telegram_policy(membership)
    return {
        "contract": TELEGRAM_USER_PREFERENCES_CONTRACT,
        "plan": policy["plan"],
        "enabled": True,
        "pause_all": False,
        "intensity": policy["intensity"],
        "selected_leagues": [],
        "message_types": list(policy["categories"]),
        "daily_limit": int(policy["daily_limit"]),
        "custom_leagues": bool(policy["custom_leagues"]),
        "league_limit": int(policy["league_limit"]),
        "daily_limit_max": int(policy["daily_limit_max"]),
        "selection_mode": "all_curated" if policy["custom_leagues"] else "essential_only",
    }


def sanitize_telegram_user_preferences(
    current: Mapping[str, Any] | None,
    updates: Mapping[str, Any] | None,
    membership: Any,
) -> dict[str, Any]:
    policy = plan_telegram_policy(membership)
    base = default_telegram_user_preferences(membership)
    current = dict(current or {})
    if current:
        base.update({key: current.get(key) for key in (
            "enabled", "pause_all", "intensity", "selected_leagues", "message_types", "daily_limit"
        ) if key in current})
    updates = dict(updates or {})

    intensity = str(updates.get("intensity") or base.get("intensity") or policy["intensity"]).strip().lower()
    if intensity not in {"essential", "balanced", "focus", "paused"}:
        intensity = policy["intensity"]

    allowed_leagues = {item["key"] for item in LEAGUE_OPTIONS}
    requested_leagues = [item for item in _list(updates.get("selected_leagues", base.get("selected_leagues"))) if item in allowed_leagues]
    if not policy["custom_leagues"]:
        requested_leagues = []
    requested_leagues = requested_leagues[: int(policy["league_limit"])]

    allowed_types = {item["key"] for item in MESSAGE_TYPE_OPTIONS}
    requested_types = [item for item in _list(updates.get("message_types", base.get("message_types"))) if item in allowed_types]
    plan_types = set(policy["categories"])
    requested_types = [item for item in requested_types if item in plan_types]
    if not requested_types:
        requested_types = list(policy["categories"])

    try:
        daily_limit = int(updates.get("daily_limit", base.get("daily_limit") or policy["daily_limit"]))
    except (TypeError, ValueError):
        daily_limit = int(policy["daily_limit"])
    daily_limit = max(1, min(daily_limit, int(policy["daily_limit_max"])))

    pause_all = _bool(updates.get("pause_all")) if "pause_all" in updates else bool(base.get("pause_all"))
    if intensity == "paused":
        pause_all = True

    return {
        "contract": TELEGRAM_USER_PREFERENCES_CONTRACT,
        "plan": policy["plan"],
        "enabled": not pause_all,
        "pause_all": pause_all,
        "intensity": intensity,
        "selected_leagues": requested_leagues,
        "message_types": requested_types,
        "daily_limit": daily_limit,
        "custom_leagues": bool(policy["custom_leagues"]),
        "league_limit": int(policy["league_limit"]),
        "daily_limit_max": int(policy["daily_limit_max"]),
        "selection_mode": "selected_leagues" if requested_leagues else ("all_curated" if policy["custom_leagues"] else "essential_only"),
    }


def telegram_preferences_from_profile(profile_preferences: Mapping[str, Any] | None, membership: Any) -> dict[str, Any]:
    outer = dict(profile_preferences or {})
    saved = outer.get("telegram") if isinstance(outer.get("telegram"), Mapping) else {}
    return sanitize_telegram_user_preferences(saved, {}, membership)


def telegram_preference_options(membership: Any) -> dict[str, Any]:
    policy = plan_telegram_policy(membership)
    return {
        "contract": TELEGRAM_USER_PREFERENCES_CONTRACT,
        "plan": policy["plan"],
        "leagues": [dict(item) for item in LEAGUE_OPTIONS],
        "message_types": [dict(item) for item in MESSAGE_TYPE_OPTIONS if item["key"] in set(policy["categories"])],
        "intensities": [
            {"key": "essential", "label": "Esencial", "hint": "Muy pocos mensajes; solo lo más importante."},
            {"key": "balanced", "label": "Equilibrado", "hint": "Resúmenes y alertas seleccionadas sin saturar."},
            {"key": "focus", "label": "Foco", "hint": "Prioriza únicamente tus ligas y tipos elegidos."},
            {"key": "paused", "label": "Pausado", "hint": "No recibir avisos automáticos privados."},
        ],
        "custom_leagues": bool(policy["custom_leagues"]),
        "league_limit": int(policy["league_limit"]),
        "daily_limits": list(range(1, int(policy["daily_limit_max"]) + 1)),
    }


def _competition_text(item: Mapping[str, Any] | None) -> str:
    item = dict(item or {})
    return _fold(" | ".join(str(item.get(key) or "") for key in (
        "competition_name", "league_name", "league", "competition", "competition_key", "sport_key", "country"
    )))


def item_matches_selected_leagues(item: Mapping[str, Any] | None, selected_leagues: Iterable[str]) -> bool:
    selected = {str(value) for value in selected_leagues or [] if str(value)}
    if not selected:
        return True
    context = _competition_text(item)
    if not context:
        return False
    by_key = {item["key"]: item for item in LEAGUE_OPTIONS}
    for key in selected:
        option = by_key.get(key)
        if option and any(_fold(term) in context for term in option["terms"]):
            return True
    return False


def message_group(message_type: Any) -> str:
    return _MESSAGE_GROUPS.get(str(message_type or "").strip().lower(), "")


def private_destination_allows(
    preferences: Mapping[str, Any] | None,
    message_type: Any,
    item: Mapping[str, Any] | None = None,
) -> tuple[bool, str]:
    prefs = dict(preferences or {})
    if not prefs.get("enabled", True) or prefs.get("pause_all"):
        return False, "telegram_usuario_pausado"
    group = message_group(message_type)
    if group and group not in set(_list(prefs.get("message_types"))):
        return False, "tipo_aviso_no_seleccionado"
    if item and not item_matches_selected_leagues(item, _list(prefs.get("selected_leagues"))):
        return False, "liga_no_seleccionada"
    return True, ""


def global_channel_allows(message_type: Any) -> bool:
    return str(message_type or "").strip().lower() in GLOBAL_CHANNEL_ALLOWED_TYPES


def destination_daily_limit(destination: Mapping[str, Any] | None) -> int:
    destination = dict(destination or {})
    if destination.get("target_kind") == "channel":
        return 4
    prefs = destination.get("telegram_preferences") if isinstance(destination.get("telegram_preferences"), Mapping) else {}
    try:
        return max(1, min(int(prefs.get("daily_limit") or 4), 20))
    except (TypeError, ValueError):
        return 4


def destination_allows_message(
    destination: Mapping[str, Any] | None,
    message_type: Any,
    item: Mapping[str, Any] | None = None,
) -> tuple[bool, str]:
    destination = dict(destination or {})
    if destination.get("target_kind") == "channel":
        return (True, "") if global_channel_allows(message_type) else (False, "canal_global_solo_resumenes")
    prefs = destination.get("telegram_preferences") if isinstance(destination.get("telegram_preferences"), Mapping) else {}
    return private_destination_allows(prefs, message_type, item)


def _candidate_item(candidate: Mapping[str, Any]) -> Mapping[str, Any] | None:
    payload = candidate.get("payload") if isinstance(candidate.get("payload"), Mapping) else {}
    for key in ("match", "pick", "highlight"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            return value
    combi = payload.get("combi")
    if isinstance(combi, Mapping):
        picks = combi.get("picks") or combi.get("legs") or []
        return next((item for item in picks if isinstance(item, Mapping)), combi)
    return None


def filter_candidate_for_destination(
    candidate: Mapping[str, Any] | None,
    destination: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, str]:
    candidate = dict(candidate or {})
    destination = dict(destination or {})
    kind = str(candidate.get("kind") or "activity")
    if destination.get("target_kind") == "channel":
        allowed, reason = destination_allows_message(destination, kind)
        return (candidate, "") if allowed else (None, reason)

    prefs = destination.get("telegram_preferences") if isinstance(destination.get("telegram_preferences"), Mapping) else {}
    payload = dict(candidate.get("payload") or {})
    group = message_group(kind)
    if group and group not in set(_list(prefs.get("message_types"))):
        return None, "tipo_aviso_no_seleccionado"
    if not prefs.get("enabled", True) or prefs.get("pause_all"):
        return None, "telegram_usuario_pausado"

    if kind in {"daily_summary", "midday_update"}:
        matches = [dict(item) for item in payload.get("matches") or [] if isinstance(item, Mapping)]
        selected = _list(prefs.get("selected_leagues"))
        filtered = [item for item in matches if item_matches_selected_leagues(item, selected)]
        if selected and not filtered:
            return None, "sin_partidos_de_ligas_seleccionadas"
        payload["matches"] = filtered if selected else matches
        clone = dict(candidate)
        clone["payload"] = payload
        return clone, ""

    item = _candidate_item(candidate)
    allowed, reason = private_destination_allows(prefs, kind, item)
    return (candidate, "") if allowed else (None, reason)


def filter_items_for_preferences(
    items: Iterable[Mapping[str, Any]] | None,
    preferences: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    prefs = dict(preferences or {})
    selected = _list(prefs.get("selected_leagues"))
    return [dict(item) for item in items or [] if isinstance(item, Mapping) and item_matches_selected_leagues(item, selected)]
