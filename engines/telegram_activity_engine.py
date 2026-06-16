"""Telegram activity planning for NeMeSiS SHARK PRO V771/V772.

The engine decides which premium Telegram messages are due on a frequent Render
Cron tick. It does not send messages by itself and does not call external APIs.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")

ACTIVITY_MESSAGE_TYPES = {
    "daily_summary",
    "midday_update",
    "live_alert",
    "pick_alert",
    "combi_alert",
    "result_final",
    "highlight_available",
    "prematch_reminder",
    "evening_recap",
}


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y", "si", "sí"}


def env_int(name, default):
    try:
        return int(str(os.getenv(name, default)).strip())
    except Exception:
        return int(default)


def now_madrid():
    return datetime.now(TZ)


def today_key(current=None):
    return (current or now_madrid()).date().isoformat()


def _minute_of_day(dt):
    return dt.hour * 60 + dt.minute


def _parse_time(value, fallback):
    raw = str(value or fallback).strip()[:5]
    try:
        hour, minute = raw.split(":", 1)
        return int(hour) * 60 + int(minute)
    except Exception:
        hour, minute = fallback.split(":", 1)
        return int(hour) * 60 + int(minute)


def _within_minutes(target_hhmm, tolerance=8, current=None):
    current = current or now_madrid()
    target = _parse_time(target_hhmm, "09:00")
    return 0 <= (_minute_of_day(current) - target) <= int(tolerance or 8)


def _parse_kickoff(item):
    item = item or {}
    raw = (
        item.get("kickoff_iso")
        or item.get("kickoff_time")
        or item.get("match_time")
        or item.get("commence_time")
        or item.get("date_time")
        or ""
    )
    if not raw:
        date_value = str(item.get("match_date") or item.get("date") or "").strip()[:10]
        time_value = str(item.get("time") or item.get("hour") or "").strip()[:5]
        raw = f"{date_value}T{time_value}:00" if date_value and time_value else ""
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except Exception:
        return None


def _status(item):
    return str((item or {}).get("status") or (item or {}).get("state") or "").strip().lower()


def _is_live(item):
    status = _status(item)
    return status in {"live", "inplay", "en directo", "directo", "ht", "descanso"} or bool((item or {}).get("minute"))


def _is_finished(item):
    return _status(item) in {"ft", "final", "finished", "finalizado"}


def _is_world_cup_or_top(item):
    text = " ".join(
        str((item or {}).get(key) or "")
        for key in ("competition_name", "league_name", "competition", "country", "title")
    ).lower()
    top_terms = (
        "mundial",
        "world cup",
        "fifa",
        "champions",
        "europa league",
        "laliga",
        "premier",
        "serie a",
        "bundesliga",
        "ligue 1",
    )
    return any(term in text for term in top_terms) or int((item or {}).get("priority") or 0) >= 85


# V810: Telegram profesional. La app puede listar muchas ligas, pero el canal solo
# debe publicar partidos/picks de competiciones top o campeonatos claros. No llama
# APIs externas; solo filtra los datos reales ya recibidos por el ecosistema.
DEFAULT_TELEGRAM_TOP_COMPETITION_TERMS = (
    "fifa world cup", "world cup", "mundial", "copa mundial", "fifa",
    "uefa euro", "eurocopa", "nations league", "copa america",
    "champions league", "uefa champions", "europa league", "conference league",
    "laliga", "la liga", "primera division spain", "primera división spain",
    "premier league", "serie a", "bundesliga", "ligue 1", "liga portugal",
    "eredivisie", "copa del rey", "fa cup", "supercopa", "super cup",
    "libertadores", "sudamericana",
)
DEFAULT_TELEGRAM_BLOCKED_COMPETITION_TERMS = (
    "u23", "u21", "u20", "u19", "u18", "u17", "youth", "juvenil",
    "reserve", "reserves", "primavera", "academy", "amistoso", "friendly",
    "regional", "amateur", "segunda", "tercera", "fourth", "league two",
    "women", "femen", "femenino", "feminine", "sub-", "sub ", "andaluza",
)


def _split_env_terms(name, defaults):
    raw = os.getenv(name, "")
    if not raw:
        return tuple(defaults)
    return tuple(term.strip().lower() for term in raw.split(",") if term.strip()) or tuple(defaults)


def _competition_text(item):
    item = item or {}
    fields = (
        "competition_name", "league_name", "league", "competition", "country",
        "sport_key", "title", "home_team", "away_team", "name",
    )
    return " ".join(str(item.get(key) or "") for key in fields).lower()


def _competition_has_blocked_term(item):
    text = _competition_text(item)
    blocked = _split_env_terms("TELEGRAM_BLOCKED_COMPETITION_TERMS", DEFAULT_TELEGRAM_BLOCKED_COMPETITION_TERMS)
    return any(term and term in text for term in blocked)


def is_telegram_professional_competition(item):
    """True only for top leagues/championships suitable for the public Telegram channel."""
    item = item or {}
    if _competition_has_blocked_term(item):
        return False
    text = _competition_text(item)
    allowed = _split_env_terms("TELEGRAM_TOP_COMPETITION_TERMS", DEFAULT_TELEGRAM_TOP_COMPETITION_TERMS)
    if any(term and term in text for term in allowed):
        return True
    try:
        return int(item.get("priority") or item.get("importance") or 0) >= 90
    except Exception:
        return False


def filter_telegram_professional_items(items, kind="match", limit=None):
    """Return allowed items and blockers for admin diagnostics; never invents replacements."""
    allowed_items = []
    blockers = []
    for item in list(items or []):
        if not isinstance(item, dict):
            continue
        if is_telegram_professional_competition(item):
            allowed_items.append(item)
            continue
        blockers.append({
            "kind": kind,
            "id": item.get("id") or item.get("match_id") or item.get("fixture_id"),
            "competition": item.get("competition_name") or item.get("league_name") or item.get("competition") or "—",
            "reason": "competicion_no_top_para_canal_telegram",
        })
    if limit:
        allowed_items = allowed_items[: int(limit)]
    return allowed_items, blockers


def telegram_activity_config():
    return {
        "activity_level": os.getenv("TELEGRAM_ACTIVITY_LEVEL", "medium_high"),
        "quiet_hours_enabled": env_bool("TELEGRAM_QUIET_HOURS_ENABLED", False),
        "world_cup_override": env_bool("TELEGRAM_WORLD_CUP_OVERRIDE", True),
        "send_daily_summary": env_bool("TELEGRAM_SEND_DAILY_SUMMARY", True),
        "send_live_alerts": env_bool("TELEGRAM_SEND_LIVE_ALERTS", True),
        "send_pick_alerts": env_bool("TELEGRAM_SEND_PICK_ALERTS", True),
        "send_combi_alerts": env_bool("TELEGRAM_SEND_COMBI_ALERTS", True),
        "send_result_alerts": env_bool("TELEGRAM_SEND_RESULT_ALERTS", True),
        "send_highlight_alerts": env_bool("TELEGRAM_SEND_HIGHLIGHT_ALERTS", True),
        "send_prematch_reminders": env_bool("TELEGRAM_SEND_PREMATCH_REMINDERS", True),
        "send_evening_recap": env_bool("TELEGRAM_SEND_EVENING_RECAP", True),
        "send_live_images": env_bool("TELEGRAM_SEND_LIVE_IMAGES", False),
        "visual_cards_enabled": env_bool("TELEGRAM_VISUAL_CARDS_ENABLED", True),
        "send_pick_cards": env_bool("TELEGRAM_SEND_PICK_CARDS", True),
        "cron_interval_minutes": env_int("TELEGRAM_CRON_INTERVAL_MINUTES", 10),
        "daily_summary_time": os.getenv("TELEGRAM_DAILY_SUMMARY_TIME", "09:00"),
        "midday_update_time": os.getenv("TELEGRAM_MIDDAY_UPDATE_TIME", "13:30"),
        "evening_recap_time": os.getenv("TELEGRAM_EVENING_RECAP_TIME", "23:30"),
        "prematch_minutes_before": env_int("TELEGRAM_PREMATCH_REMINDER_MINUTES", 60),
        "professional_competitions_only": env_bool("TELEGRAM_PROFESSIONAL_COMPETITIONS_ONLY", True),
        "top_match_limit": env_int("TELEGRAM_TOP_MATCH_LIMIT", 18),
        "top_pick_limit": env_int("TELEGRAM_TOP_PICK_LIMIT", 8),
        "quiet_start": os.getenv("TELEGRAM_QUIET_START", "00:30"),
        "quiet_end": os.getenv("TELEGRAM_QUIET_END", "09:30"),
    }


def build_dedupe_key(message_type, match_id="", pick_id="", market="", status="", madrid_date="", module="activity"):
    raw = "|".join(
        [
            str(message_type or "").strip().lower(),
            str(match_id or "").strip().lower(),
            str(pick_id or "").strip().lower(),
            str(market or "").strip().lower(),
            str(status or "").strip().lower(),
            str(madrid_date or today_key()).strip(),
            str(module or "activity").strip().lower(),
        ]
    )
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"{message_type}:{digest}"


def is_world_cup_override_allowed(item=None, pick=None, current=None):
    cfg = telegram_activity_config()
    if not cfg["world_cup_override"]:
        return False
    return _is_world_cup_or_top(item or pick or {})


def is_quiet_hours_blocked(message_type, item=None, pick=None, current=None):
    cfg = telegram_activity_config()
    if not cfg["quiet_hours_enabled"]:
        return False
    current = current or now_madrid()
    start = _parse_time(cfg["quiet_start"], "00:30")
    end = _parse_time(cfg["quiet_end"], "09:30")
    minute = _minute_of_day(current)
    active = start <= minute <= end if start < end else minute >= start or minute <= end
    if not active:
        return False
    if is_world_cup_override_allowed(item=item, pick=pick, current=current):
        return False
    if message_type in {"pick_alert", "result_final", "highlight_available"}:
        return False
    return True


def should_send_daily_summary(current=None):
    cfg = telegram_activity_config()
    return cfg["send_daily_summary"] and _within_minutes(cfg["daily_summary_time"], cfg["cron_interval_minutes"], current)


def should_send_midday_update(matches=None, picks=None, current=None):
    cfg = telegram_activity_config()
    if not _within_minutes(cfg["midday_update_time"], cfg["cron_interval_minutes"], current):
        return False
    return bool(matches or picks)


def should_send_live_alert(match=None, current=None):
    cfg = telegram_activity_config()
    if not cfg["send_live_alerts"] or not _is_live(match):
        return False
    if is_quiet_hours_blocked("live_alert", item=match, current=current):
        return False
    return _is_world_cup_or_top(match) or bool((match or {}).get("has_pick") or (match or {}).get("favorite"))


def pick_has_real_value(pick=None):
    pick = pick or {}
    market = str(pick.get("market") or pick.get("pick_type") or "").strip()
    selection = str(pick.get("selection") or pick.get("recommendation") or "").strip()
    try:
        odds = float(str(pick.get("odds") or "0").replace(",", "."))
    except Exception:
        odds = 0.0
    risk = str(pick.get("risk_level") or pick.get("risk") or "").lower()
    if not market or market.lower() in {"principal", "main", "default"}:
        return False
    if not selection:
        return False
    if odds <= 1.0:
        return False
    if "alto" in risk or "high" in risk:
        score = int(pick.get("confidence") or pick.get("score") or pick.get("shark_score") or 0)
        return score >= 85
    return True


def should_send_pick_alert(pick=None, current=None):
    cfg = telegram_activity_config()
    if not cfg["send_pick_alerts"] or not pick_has_real_value(pick):
        return False
    if is_quiet_hours_blocked("pick_alert", pick=pick, current=current):
        return False
    kickoff = _parse_kickoff(pick)
    if not kickoff:
        return True
    return (kickoff - (current or now_madrid())).total_seconds() >= -900


def should_send_combi_alert(combi=None, current=None):
    cfg = telegram_activity_config()
    if not cfg["send_combi_alerts"]:
        return False
    combi = combi or {}
    try:
        odds = float(str(combi.get("total_odds") or combi.get("odds") or "0").replace(",", "."))
    except Exception:
        odds = 0.0
    legs = combi.get("picks") or combi.get("legs") or []
    if not legs and not combi.get("legs_count"):
        return False
    if odds <= 1.0:
        return False
    if is_quiet_hours_blocked("combi_alert", pick=combi, current=current):
        return False
    return True


def should_send_result_alert(match=None, pick=None, current=None):
    cfg = telegram_activity_config()
    if not cfg["send_result_alerts"] or not _is_finished(match):
        return False
    return bool(pick) or _is_world_cup_or_top(match)


def should_send_highlight_alert(match=None, highlight=None, current=None):
    cfg = telegram_activity_config()
    if not cfg["send_highlight_alerts"]:
        return False
    if not highlight or not (highlight.get("video_url") or highlight.get("safe_url") or highlight.get("detail_url")):
        return False
    return bool((match or {}).get("has_pick")) or _is_world_cup_or_top(match or highlight)


def should_send_prematch_reminder(match=None, pick=None, current=None):
    cfg = telegram_activity_config()
    if not cfg["send_prematch_reminders"]:
        return False
    kickoff = _parse_kickoff(match or pick)
    if not kickoff:
        return False
    minutes = int((kickoff - (current or now_madrid())).total_seconds() // 60)
    target = cfg["prematch_minutes_before"]
    if not (target - cfg["cron_interval_minutes"] <= minutes <= target):
        return False
    return bool(pick) or _is_world_cup_or_top(match or {})


def should_send_evening_recap(activity=None, current=None):
    cfg = telegram_activity_config()
    if not cfg["send_evening_recap"] or not _within_minutes(cfg["evening_recap_time"], cfg["cron_interval_minutes"], current):
        return False
    activity = activity or {}
    return bool(activity.get("results") or activity.get("picks") or activity.get("highlights"))


def _candidate(kind, title, priority, dedupe_key, payload):
    return {
        "kind": kind,
        "title": title,
        "priority": int(priority),
        "dedupe_key": dedupe_key,
        "payload": payload,
    }


def build_telegram_activity_plan(matches=None, picks=None, highlights=None, combis=None, current=None):
    current = current or now_madrid()
    cfg = telegram_activity_config()
    matches = list(matches or [])
    picks = list(picks or [])
    highlights = list(highlights or [])
    combis = list(combis or [])
    candidates = []
    blockers = []
    if cfg.get("professional_competitions_only", True):
        matches, match_blockers = filter_telegram_professional_items(matches, kind="match", limit=cfg.get("top_match_limit") or 18)
        picks, pick_blockers = filter_telegram_professional_items(picks, kind="pick", limit=cfg.get("top_pick_limit") or 8)
        filtered_highlights, highlight_blockers = filter_telegram_professional_items(highlights, kind="highlight", limit=cfg.get("top_match_limit") or 18)
        highlights = filtered_highlights
        blockers.extend(match_blockers[:18] + pick_blockers[:12] + highlight_blockers[:8])
    date_key = today_key(current)

    if should_send_daily_summary(current):
        candidates.append(_candidate("daily_summary", "Resumen SHARK del dia", 60, build_dedupe_key("daily_summary", madrid_date=date_key), {"matches": matches[:5]}))
    else:
        blockers.append({"kind": "daily_summary", "reason": "fuera_de_hora_o_desactivado"})

    if should_send_midday_update(matches, picks, current):
        candidates.append(_candidate("midday_update", "Actualizacion SHARK de mediodia", 58, build_dedupe_key("midday_update", madrid_date=date_key), {"matches": matches[:4], "picks_count": len(picks)}))

    for pick in picks[:12]:
        if should_send_pick_alert(pick, current):
            candidates.append(_candidate("pick_alert", "Pick premium SHARK", 95, build_dedupe_key("pick_alert", match_id=pick.get("match_id"), pick_id=pick.get("id"), market=pick.get("market"), madrid_date=date_key), {"pick": pick}))
        else:
            blockers.append({"kind": "pick_alert", "pick_id": pick.get("id"), "reason": "sin_cuota_mercado_riesgo_o_ventana"})

    for combi in combis[:6]:
        if should_send_combi_alert(combi, current):
            candidates.append(_candidate("combi_alert", "Combi SHARK", 92, build_dedupe_key("combi_alert", pick_id=combi.get("id"), market=combi.get("title") or combi.get("name"), madrid_date=date_key), {"combi": combi}))
        else:
            blockers.append({"kind": "combi_alert", "combi_id": combi.get("id"), "reason": "sin_picks_cuota_o_ventana"})

    for match in matches[:30]:
        if should_send_live_alert(match, current):
            if str(match.get("minute") or "").isdigit():
                minute_bucket = str((int(match.get("minute") or 0) // 10) * 10)
            else:
                minute_bucket = _status(match)
            candidates.append(_candidate("live_alert", "Alerta live SHARK", 90, build_dedupe_key("live_alert", match_id=match.get("id"), status=minute_bucket, madrid_date=date_key), {"match": match}))
        if should_send_prematch_reminder(match, None, current):
            candidates.append(_candidate("prematch_reminder", "Partido en 60 min", 75, build_dedupe_key("prematch_reminder", match_id=match.get("id"), status="60min", madrid_date=date_key), {"match": match}))
        if should_send_result_alert(match, None, current):
            candidates.append(_candidate("result_final", "Resultado final SHARK", 88, build_dedupe_key("result_final", match_id=match.get("id"), status="final", madrid_date=date_key), {"match": match, "pick": {}}))

    for highlight in highlights[:12]:
        match = highlight.get("match") or highlight
        if should_send_highlight_alert(match, highlight, current):
            candidates.append(_candidate("highlight_available", "Resumen disponible", 84, build_dedupe_key("highlight_available", match_id=highlight.get("match_id") or match.get("id"), status=highlight.get("id") or highlight.get("video_url"), madrid_date=date_key), {"match": match, "highlight": highlight}))

    activity = {
        "results": any(_is_finished(m) for m in matches),
        "picks": bool(picks),
        "combis": bool(combis),
        "highlights": bool(highlights),
    }
    if should_send_evening_recap(activity, current):
        candidates.append(_candidate("evening_recap", "Cierre SHARK del dia", 55, build_dedupe_key("evening_recap", madrid_date=date_key), {"summary": activity}))

    candidates = sorted(candidates, key=lambda x: x["priority"], reverse=True)
    return {
        "ok": True,
        "madrid_now": current.isoformat(timespec="seconds"),
        "config": cfg,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "blockers": blockers[:30],
        "modules": sorted(ACTIVITY_MESSAGE_TYPES),
        "priority_order": [
            "pick_alert",
            "combi_alert",
            "live_alert",
            "result_final",
            "highlight_available",
            "daily_summary",
            "evening_recap",
            "midday_update",
            "prematch_reminder",
        ],
    }


def telegram_activity_status(plan=None):
    plan = plan or build_telegram_activity_plan()
    cfg = plan.get("config") or telegram_activity_config()
    if plan.get("candidate_count"):
        status = "Telegram vivo"
    elif cfg.get("quiet_hours_enabled"):
        status = "Telegram sin candidatos"
    else:
        status = "Telegram listo para enviar"
    return {
        "status": status,
        "activity_level": cfg.get("activity_level"),
        "quiet_hours": "activo" if cfg.get("quiet_hours_enabled") else "inactivo",
        "world_cup_override": "activo" if cfg.get("world_cup_override") else "inactivo",
        "professional_competitions_only": "activo" if cfg.get("professional_competitions_only", True) else "inactivo",
        "candidate_count": plan.get("candidate_count", 0),
        "next_estimated": "Siguiente tick Render Cron",
    }
