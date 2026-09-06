"""Picks Quality Engine for NeMeSiS SHARK PRO.

Small, dependency-free helpers that make picks easier to rank, label and
explain for customers. The functions are intentionally defensive: they never
perform I/O and they never raise for malformed API/pick rows.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from engines.spanish_localization_engine import (
    parse_datetime_to_madrid,
    spanish_competition_name,
    spanish_market_name,
    spanish_pick_selection_name,
    spanish_team_name,
)

_PENDING_RE = re.compile(
    r"(esperar|pendiente|sin cuota|no disponible|value en c[aá]lculo|cuota pendiente|mercado pendiente|null|none|undefined|nan)",
    flags=re.I,
)

_HIGH_VALUE_COMPETITIONS = (
    "Mundial FIFA",
    "Mundial de Clubes FIFA",
    "Eurocopa",
    "Copa América",
    "Champions League",
    "Europa League",
    "Conference League",
    "Liga de Naciones UEFA",
    "LaLiga EA Sports",
    "Premier League",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
    "Primeira Liga",
    "Eredivisie",
    "Libertadores",
    "Sudamericana",
)

_SOLID_COMPETITIONS = (
    "Segunda División",
    "Championship",
    "Copa del Rey",
    "Copa FA",
    "Copa de la Liga inglesa",
    "MLS",
    "Primera División Argentina",
    "Brasileirão",
)

_LOW_RELEVANCE_TERMS = (
    "georgian erovnuli",
    "erovnuli liga",
    "latvian higher",
    "finnish ykk",
    "ykkonen",
    "ykkönen",
    "reserve",
    "reserves",
    "youth",
    "u19",
    "u20",
    "u21",
    "u23",
    "regional",
    "amateur",
    "friendly",
    "segunda extranjera",
    "tercera",
    "cuarta",
)

_RISK_MAP = {
    "low": "Bajo",
    "bajo": "Bajo",
    "baja": "Bajo",
    "medium": "Medio",
    "medio": "Medio",
    "media": "Medio",
    "high": "Alto",
    "alto": "Alto",
    "alta": "Alto",
}


def _as_float(value, default=0.0) -> float:
    try:
        if value in (None, ""):
            return default
        n = float(str(value).replace(",", "."))
        if math.isnan(n) or math.isinf(n):
            return default
        return n
    except Exception:
        return default


def _as_int(value, default=0) -> int:
    try:
        return int(round(_as_float(value, default)))
    except Exception:
        return default


def _clean_text(value) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if _PENDING_RE.fullmatch(text):
        return ""
    return text


def _risk_label(value) -> str:
    raw = str(value or "Medio").strip().lower()
    for needle, label in _RISK_MAP.items():
        if needle in raw:
            return label
    return "Medio"


def competition_priority(competition) -> int:
    comp = spanish_competition_name(competition) or "Competición"
    low = comp.lower()
    if any(x in low for x in _LOW_RELEVANCE_TERMS):
        return 1
    if any(x.lower() in low for x in _HIGH_VALUE_COMPETITIONS):
        return 14
    if any(x.lower() in low for x in _SOLID_COMPETITIONS):
        return 8
    if any(x in low for x in ("amistoso", "friendly", "regional", "provincial")):
        return 2
    return 5


def is_low_relevance_competition(competition) -> bool:
    low = (spanish_competition_name(competition) or str(competition or "")).lower()
    return any(x in low for x in _LOW_RELEVANCE_TERMS) or competition_priority(competition) <= 2


def _pick_datetime(item):
    item = dict(item or {})
    for key in ("kickoff_iso", "match_datetime", "start_time", "published_at"):
        dt = parse_datetime_to_madrid(item.get(key) or "")
        if dt:
            return dt
    date = str(item.get("match_date") or item.get("date") or "").strip()
    time = str(item.get("kickoff_time") or item.get("match_time") or "").strip()
    if date:
        dt = parse_datetime_to_madrid((date + ("T" + time if time else "T00:00:00")).strip())
        if dt:
            return dt
    return None


def is_stale_pick(item, hours_grace=6) -> bool:
    dt = _pick_datetime(item)
    if not dt:
        return False
    now = datetime.now(dt.tzinfo or timezone.utc)
    return (now - dt).total_seconds() > int(hours_grace) * 3600


def odds_quality_points(odds) -> int:
    odds = _as_float(odds, 0)
    if odds <= 1:
        return -25
    if odds < 1.35:
        return -6
    if 1.45 <= odds <= 2.35:
        return 16
    if 2.36 <= odds <= 3.20:
        return 8
    if odds <= 4.50:
        return 2
    return -8


def timing_points(item) -> int:
    dt = _pick_datetime(item)
    if not dt:
        return 0
    now = datetime.now(dt.tzinfo or timezone.utc)
    hours = (dt - now).total_seconds() / 3600
    if hours < -1:
        return -30
    if -1 <= hours <= 48:
        return 10
    if hours <= 96:
        return 6
    return 2


def _valid_selection(item) -> str:
    raw_selection = item.get("selection") or item.get("pick") or item.get("recommendation") or ""
    home = item.get("home_team") or item.get("home") or ""
    away = item.get("away_team") or item.get("away") or ""
    market = item.get("market") or item.get("pick_type") or ""
    if _PENDING_RE.search(str(raw_selection or "")):
        return ""
    return spanish_pick_selection_name(raw_selection, home, away, market) or ""


def pick_quality_score(item) -> int:
    item = dict(item or {})
    base_conf = _as_int(item.get("confidence") or item.get("shark_score") or item.get("score"), 50)
    score = max(0, min(100, base_conf))

    selection = _valid_selection(item)
    market = spanish_market_name(item.get("market") or item.get("pick_type") or "")
    odds = _as_float(item.get("odds"), 0)

    if not selection:
        score -= 32
    else:
        score += 7
    if not market or _PENDING_RE.search(market):
        score -= 12
    else:
        score += 4
    score += odds_quality_points(odds)
    comp = item.get("competition_name") or item.get("league_name")
    score += competition_priority(comp)
    if is_low_relevance_competition(comp):
        score -= 42
    score += timing_points(item)
    if is_stale_pick(item):
        score -= 38

    risk = _risk_label(item.get("risk_level") or item.get("risk"))
    if risk == "Bajo":
        score += 8
    elif risk == "Alto":
        score -= 12

    reason = _clean_text(item.get("reasoning") or item.get("reason") or "")
    caution = _clean_text(item.get("warning_reason") or item.get("warning") or "")
    if reason:
        score += 4
    if caution:
        score += 2

    status = str(item.get("status") or item.get("match_status") or "").lower()
    if any(x in status for x in ("final", "finished", "ended", "cancelled", "postponed")):
        score -= 40

    return int(max(0, min(100, score)))


def quality_label(score: int) -> str:
    score = int(score or 0)
    if score >= 88:
        return "TOP SHARK"
    if score >= 78:
        return "Pick premium"
    if score >= 68:
        return "Value controlado"
    return "En estudio"


def quality_bucket(score: int, item=None, premium_ready=None) -> str:
    if premium_ready is None:
        premium_ready = pick_is_premium_ready(item or {}, min_score=68)
    if not premium_ready:
        return "study"
    if score >= 88:
        return "top"
    if score >= 78:
        return "premium"
    return "value"


def pick_is_premium_ready(item, min_score=68, quality_score=None) -> bool:
    item = dict(item or {})
    selection = _valid_selection(item)
    market = spanish_market_name(item.get("market") or item.get("pick_type") or "")
    odds = _as_float(item.get("odds"), 0)
    status = str(item.get("status") or item.get("match_status") or "").lower()
    if not selection or not market:
        return False
    if odds <= 1:
        return False
    if _PENDING_RE.search(selection) or _PENDING_RE.search(market):
        return False
    if any(x in status for x in ("final", "finished", "ended", "cancelled", "postponed")):
        return False
    if is_stale_pick(item):
        return False
    if is_low_relevance_competition(item.get("competition_name") or item.get("league_name")):
        return False
    score = pick_quality_score(item) if quality_score is None else int(quality_score)
    return score >= int(min_score)


def enrich_pick_quality(item) -> dict:
    item = dict(item or {})
    item["competition_name"] = spanish_competition_name(item.get("competition_name") or item.get("league_name") or "") or "Competición"
    item["league_name"] = spanish_competition_name(item.get("league_name") or item.get("competition_name") or "") or item["competition_name"]
    item["market"] = spanish_market_name(item.get("market") or item.get("pick_type") or "") or "Ganador del partido"
    item["pick_type"] = spanish_market_name(item.get("pick_type") or item.get("market") or "") or item["market"]
    selection = _valid_selection(item)
    if selection:
        item["selection"] = selection
        item["selection_display"] = selection
    score = pick_quality_score(item)
    premium_ready = pick_is_premium_ready(item, quality_score=score)
    item["quality_score"] = score
    item["quality_label"] = quality_label(score)
    item["quality_bucket"] = quality_bucket(score, item, premium_ready=premium_ready)
    item["premium_ready"] = premium_ready
    item["competition_priority"] = competition_priority(item.get("competition_name") or item.get("league_name"))
    item["low_relevance_competition"] = is_low_relevance_competition(item.get("competition_name") or item.get("league_name"))
    item["stale_pick"] = is_stale_pick(item)
    if item["stale_pick"]:
        item["app_pick_state"] = "Archivado"
        item["app_pick_note"] = "Pick pasado: no aparece como activo premium."
    elif item["low_relevance_competition"]:
        item["app_pick_state"] = "Liga baja relevancia"
        item["app_pick_note"] = "Se degrada para no ocupar protagonismo comercial."
    elif not item.get("premium_ready"):
        item["app_pick_state"] = "Pick en revisión"
        item["app_pick_note"] = "Faltan cuota, selección o contexto suficiente."
    else:
        item["app_pick_state"] = "Pick activo"
        item["app_pick_note"] = "Publicado con datos suficientes para mostrarse arriba."
    if not item.get("reasoning"):
        item["reasoning"] = "SHARK prioriza este pick por cuota real, mercado claro y señal deportiva disponible."
    if not item.get("warning_reason"):
        item["warning_reason"] = "No subir stake si la cuota baja demasiado. Revisa alineaciones antes de entrar."
    return item


def _quality_sort_key(pick):
    return (
        int(bool(pick.get("premium_ready"))),
        -int(bool(pick.get("stale_pick"))),
        -int(bool(pick.get("low_relevance_competition"))),
        int(pick.get("quality_score") or 0),
        int(pick.get("competition_priority") or 0),
        _as_float(pick.get("odds"), 0),
        _as_int(pick.get("confidence") or pick.get("shark_score"), 0),
    )


def sort_enriched_picks_by_quality(picks):
    """Sort already-enriched picks without repeating localization or scoring."""
    return sorted(
        [dict(pick or {}) for pick in (picks or [])],
        key=_quality_sort_key,
        reverse=True,
    )


def sort_picks_by_quality(picks):
    return sort_enriched_picks_by_quality([enrich_pick_quality(pick) for pick in (picks or [])])


def split_enriched_picks_by_quality(picks):
    result = {"top": [], "premium": [], "value": [], "study": [], "ready": []}
    for pick in sort_enriched_picks_by_quality(picks):
        bucket = pick.get("quality_bucket") or "study"
        if bucket not in result:
            bucket = "study"
        result[bucket].append(pick)
        if pick.get("premium_ready"):
            result["ready"].append(pick)
    return result


def split_picks_by_quality(picks):
    return split_enriched_picks_by_quality([enrich_pick_quality(pick) for pick in (picks or [])])
