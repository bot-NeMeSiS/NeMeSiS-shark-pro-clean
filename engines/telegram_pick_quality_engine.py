"""V889 premium Telegram pick quality gate.

This module is intentionally pure: no network calls, no database writes and no
Telegram delivery. It only classifies real pick payloads already available in
the app so Cron/admin can decide whether a message is worth sending.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")

PREMIUM_SEND = "PREMIUM_SEND"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
SKIP_LOW_QUALITY = "SKIP_LOW_QUALITY"
SKIP_MISSING_ODDS = "SKIP_MISSING_ODDS"
SKIP_MISSING_SELECTION = "SKIP_MISSING_SELECTION"
SKIP_DUPLICATE = "SKIP_DUPLICATE"
SKIP_UNSUPPORTED_LEAGUE = "SKIP_UNSUPPORTED_LEAGUE"
SKIP_TOO_LATE = "SKIP_TOO_LATE"
SKIP_TOO_EARLY = "SKIP_TOO_EARLY"
SKIP_NO_REAL_DATA = "SKIP_NO_REAL_DATA"

SENDABLE_STATUSES = {PREMIUM_SEND}
BLOCKED_STATUSES = {
    SKIP_LOW_QUALITY,
    SKIP_MISSING_ODDS,
    SKIP_MISSING_SELECTION,
    SKIP_DUPLICATE,
    SKIP_UNSUPPORTED_LEAGUE,
    SKIP_TOO_LATE,
    SKIP_TOO_EARLY,
    SKIP_NO_REAL_DATA,
}

SAFE_EMPTY_STATE = "No hay picks premium suficientes"
SAFE_REVIEW_STATE = "Pick en revision"

UNSUPPORTED_LEAGUE_RE = re.compile(
    r"\b(u17|u18|u19|u20|u21|juvenil|youth|reserve|reservas|amateur|regional|friendly|amistoso)\b",
    flags=re.I,
)


def _first(data: dict, keys: list[str], fallback=""):
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value
    return fallback


def _text(value, fallback="") -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if text.lower() in {"none", "null", "undefined", "nan"}:
        return fallback
    return text or fallback


def _number(value, default=None):
    try:
        parsed = float(str(value).replace(",", "."))
    except Exception:
        return default
    return parsed


def _valid_odds(value) -> bool:
    odds = _number(value)
    return odds is not None and odds > 1.01 and odds < 1000


def _kickoff_dt(pick: dict):
    raw = _first(pick, ["kickoff_iso", "kickoff_time", "match_time", "date_time", "commence_time", "date"], "")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TZ)
    return parsed.astimezone(TZ)


def _madrid_date_key(value=None) -> str:
    if isinstance(value, datetime):
        return value.astimezone(TZ).date().isoformat()
    return datetime.now(TZ).date().isoformat()


def normalize_pick_for_telegram(pick: dict | None) -> dict:
    pick = dict(pick or {})
    normalized = {
        "pick_id": _text(_first(pick, ["pick_id", "id", "slug"], "")),
        "match_id": _text(_first(pick, ["match_id", "fixture_id", "event_id", "game_id"], "")),
        "home_team": _text(_first(pick, ["home_team", "home", "home_name"], "")),
        "away_team": _text(_first(pick, ["away_team", "away", "away_name"], "")),
        "competition": _text(_first(pick, ["competition_name", "league_name", "competition", "league"], "")),
        "country": _text(_first(pick, ["country", "country_name"], "")),
        "market": _text(_first(pick, ["market", "pick_type", "bet_type"], "")),
        "selection": _text(_first(pick, ["selection", "recommendation", "pick", "choice"], "")),
        "odds": _first(pick, ["odds", "price", "decimal_odds", "best_odds"], None),
        "bookmaker": _text(_first(pick, ["bookmaker", "bookmaker_name", "sportsbook"], "")),
        "confidence": _first(pick, ["confidence", "shark_score", "score", "probability"], None),
        "stake": _first(pick, ["stake_units", "stake", "recommended_stake"], None),
        "risk": _text(_first(pick, ["risk_level", "risk"], "")),
        "reason": _text(_first(pick, ["reasoning", "reason", "main_reason", "analysis"], "")),
        "counterargument": _text(_first(pick, ["counterargument", "caution", "warning", "risk_reason"], "")),
        "status": _text(_first(pick, ["status", "state"], "")),
        "kickoff_iso": _text(_first(pick, ["kickoff_iso", "kickoff_time", "match_time", "date_time", "commence_time", "date"], "")),
        "match_url": _text(_first(pick, ["match_url", "url"], "")),
    }
    normalized["raw"] = pick
    return normalized


def build_telegram_pick_dedupe_key(pick: dict, destination="global", membership="PRO", module="telegram_premium_pick") -> str:
    item = normalize_pick_for_telegram(pick)
    raw = "|".join(
        [
            _madrid_date_key(),
            "premium_pick",
            item["match_id"],
            item["pick_id"],
            item["market"].lower(),
            item["selection"].lower(),
            str(item["odds"] or ""),
            str(destination or "global"),
            str(membership or "PRO").upper(),
            module,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def classify_telegram_pick(pick: dict | None, sent_dedupe_keys=None, membership="PRO", now=None) -> dict:
    item = normalize_pick_for_telegram(pick)
    now = now.astimezone(TZ) if isinstance(now, datetime) else datetime.now(TZ)
    sent_dedupe_keys = set(sent_dedupe_keys or [])
    dedupe_key = build_telegram_pick_dedupe_key(item, membership=membership)
    reasons: list[str] = []
    score = 0

    if dedupe_key in sent_dedupe_keys:
        return {"status": SKIP_DUPLICATE, "score": 0, "reasons": ["Pick duplicado para este destino/membresia."], "dedupe_key": dedupe_key, "pick": item, "sendable": False}

    if not (item["match_id"] or (item["home_team"] and item["away_team"])):
        return {"status": SKIP_NO_REAL_DATA, "score": 0, "reasons": ["Falta partido real identificable."], "dedupe_key": dedupe_key, "pick": item, "sendable": False}
    score += 16

    if item["competition"]:
        score += 10
        if UNSUPPORTED_LEAGUE_RE.search(item["competition"]):
            return {"status": SKIP_UNSUPPORTED_LEAGUE, "score": score, "reasons": ["Competicion no apta para envio premium."], "dedupe_key": dedupe_key, "pick": item, "sendable": False}
    else:
        reasons.append("Competicion pendiente.")

    if not item["selection"]:
        return {"status": SKIP_MISSING_SELECTION, "score": score, "reasons": ["Seleccion pendiente."], "dedupe_key": dedupe_key, "pick": item, "sendable": False}
    score += 16

    if not item["market"]:
        reasons.append("Mercado pendiente.")
    else:
        score += 10

    if not _valid_odds(item["odds"]):
        return {"status": SKIP_MISSING_ODDS, "score": score, "reasons": ["Cuota pendiente o invalida."], "dedupe_key": dedupe_key, "pick": item, "sendable": False}
    score += 18

    kickoff = _kickoff_dt(item)
    if kickoff:
        minutes = (kickoff - now).total_seconds() / 60
        if minutes < -30:
            return {"status": SKIP_TOO_LATE, "score": score, "reasons": ["Partido ya fuera de ventana prepartido."], "dedupe_key": dedupe_key, "pick": item, "sendable": False}
        if minutes > 60 * 36:
            return {"status": SKIP_TOO_EARLY, "score": score, "reasons": ["Partido demasiado lejano para envio premium."], "dedupe_key": dedupe_key, "pick": item, "sendable": False}
        score += 10
    else:
        reasons.append("Hora Madrid pendiente.")

    if item["stake"]:
        score += 6
    else:
        reasons.append("Stake pendiente.")
    if item["risk"]:
        score += 6
    else:
        reasons.append("Riesgo pendiente.")
    if item["reason"]:
        score += 10
    else:
        reasons.append("Motivo pendiente.")
    if item["counterargument"]:
        score += 4
    else:
        reasons.append("Contraargumento pendiente.")

    if score >= 76:
        status = PREMIUM_SEND
    elif score >= 58:
        status = REVIEW_REQUIRED
    else:
        status = SKIP_LOW_QUALITY
    return {
        "status": status,
        "score": min(score, 100),
        "reasons": reasons or ["Pick con datos suficientes para revision premium."],
        "dedupe_key": dedupe_key,
        "pick": item,
        "sendable": status in SENDABLE_STATUSES,
    }


def filter_premium_telegram_picks(picks, membership="PRO", limit=3, sent_dedupe_keys=None) -> dict:
    reviewed = []
    sendable = []
    blocked = []
    for pick in list(picks or []):
        quality = classify_telegram_pick(pick, sent_dedupe_keys=sent_dedupe_keys, membership=membership)
        reviewed.append(quality)
        if quality["sendable"]:
            sendable.append(quality)
        else:
            blocked.append(quality)
    sendable.sort(key=lambda item: item.get("score", 0), reverse=True)
    return {
        "ok": True,
        "membership": str(membership or "PRO").upper(),
        "reviewed": len(reviewed),
        "sendable": sendable[: max(0, int(limit or 3))],
        "blocked": blocked[:25],
        "status": "PREMIUM_READY" if sendable else SAFE_EMPTY_STATE,
        "no_filler_policy": "No se envia Telegram si no hay partido, seleccion y cuota reales.",
    }


def build_membership_message_variant(pick: dict, quality=None, membership="PRO") -> dict:
    membership = str(membership or "PRO").upper()
    quality = quality or classify_telegram_pick(pick, membership=membership)
    base = normalize_pick_for_telegram(pick)
    if membership == "FREE":
        includes = ["partido", "competicion", "seleccion resumida", "CTA a PRO"]
        locked = ["stake avanzado", "motivo completo", "lectura SHARK avanzada"]
    elif membership == "ELITE":
        includes = ["pick completo", "cuota", "stake", "riesgo", "motivo", "contraargumento", "lectura SHARK avanzada si existe", "seguimiento"]
        locked = []
    else:
        includes = ["pick completo", "cuota", "stake", "motivo", "riesgo"]
        locked = ["escenarios avanzados ELITE"]
    return {
        "membership": membership,
        "pick": base,
        "quality": quality,
        "includes": includes,
        "locked": locked,
        "safe_note": "No se inventa contenido por plan; si falta dato, queda marcado como pendiente.",
    }


def build_telegram_pick_quality_summary(picks) -> dict:
    reviewed = [classify_telegram_pick(pick) for pick in list(picks or [])]
    by_status = {}
    for item in reviewed:
        by_status[item["status"]] = by_status.get(item["status"], 0) + 1
    return {
        "ok": True,
        "reviewed": len(reviewed),
        "by_status": by_status,
        "sendable": sum(1 for item in reviewed if item.get("sendable")),
        "blocked": sum(1 for item in reviewed if not item.get("sendable")),
        "top": sorted(reviewed, key=lambda item: item.get("score", 0), reverse=True)[:5],
    }


def build_combi_quality(picks, membership="ELITE") -> dict:
    items = [classify_telegram_pick(pick, membership=membership) for pick in list(picks or [])[:3]]
    if len(items) < 2:
        return {"status": "Combi en revision", "sendable": False, "reasons": ["Faltan al menos dos selecciones reales."], "legs": items}
    blocked = [item for item in items if not item.get("sendable")]
    if blocked:
        return {"status": "Combi no enviada por datos insuficientes", "sendable": False, "reasons": ["Una o mas patas no alcanzan calidad premium."], "legs": items}
    avg = sum(item.get("score", 0) for item in items) / len(items)
    return {"status": "Combi premium revisada" if avg >= 76 else "Combi descartada por riesgo", "sendable": avg >= 76, "score": round(avg, 1), "risk": "Alto", "stake": "bajo", "legs": items}


def build_pick_result_payload(pick: dict, match: dict | None = None) -> dict:
    item = normalize_pick_for_telegram(pick)
    match = dict(match or {})
    result = _text(_first(match, ["pick_result", "result_status", "settlement"], ""), "Resultado pendiente")
    score = _text(_first(match, ["score", "result", "final_score"], ""), "Marcador pendiente")
    return {
        "pick": item,
        "result": result,
        "score": score,
        "safe_note": "Resultado solo se publica si procede de dato real o liquidacion guardada.",
    }
