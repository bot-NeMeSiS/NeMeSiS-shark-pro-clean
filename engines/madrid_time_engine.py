"""Central Madrid-time helpers for match display.

All sports API datetimes are normalized here before they reach templates,
Telegram, SHARK or admin diagnostics. Naive datetimes are treated as UTC
because most upstream sports APIs send UTC even when the timezone suffix is
missing.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

MADRID_TZ = ZoneInfo("Europe/Madrid")
UTC_TZ = ZoneInfo("UTC")

WEEKDAYS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MONTHS_ES_SHORT = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
LIVE_STATUSES = {"live", "inplay", "in_play", "1h", "2h", "et", "pen", "en directo"}
HALFTIME_STATUSES = {"ht", "halftime", "descanso"}
FINISHED_STATUSES = {"ft", "finished", "final", "finalizado", "aet"}


def madrid_now() -> datetime:
    return datetime.now(MADRID_TZ)


def _clean_datetime_text(value: object) -> str:
    return str(value or "").strip().replace(" UTC", "+00:00")


def _has_tz_suffix(value: str) -> bool:
    text = value.strip()
    return text.endswith("Z") or bool(re.search(r"[+-]\d{2}:?\d{2}$", text))


def _from_common_formats(value: str) -> datetime | None:
    for fmt in ("%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_madrid_local_datetime(value: object) -> datetime | None:
    """Parse date/time values that are already written in Spain/Madrid time.

    This is used for manual admin values or DB rows where ``match_date`` +
    ``kickoff_time`` are already Madrid-facing fields. It avoids the classic
    double-shift bug where 21:00 Madrid became 23:00 in the UI.
    """
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, time.min)
    else:
        raw = _clean_datetime_text(value)
        if not raw:
            return None
        if raw.endswith("Z") or _has_tz_suffix(raw):
            return to_madrid_time(raw)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            dt = datetime.fromisoformat(raw)
        else:
            iso = raw.replace(" ", "T")
            if re.match(r"^\d{4}-\d{2}-\d{2}T\d{1,2}:\d{2}$", iso):
                iso += ":00"
            try:
                dt = datetime.fromisoformat(iso)
            except ValueError:
                dt = _from_common_formats(raw)
                if dt is None:
                    return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MADRID_TZ)
    return dt.astimezone(MADRID_TZ)


def madrid_local_from_parts(date_value: object, time_value: object = "") -> datetime | None:
    date_text = str(date_value or "").strip()[:10]
    time_text = str(time_value or "").strip()[:5]
    if not date_text:
        return None
    if not time_text or not re.match(r"^\d{1,2}:\d{2}$", time_text):
        return None
    return parse_madrid_local_datetime(f"{date_text}T{time_text}:00")


def parse_match_datetime(value: object) -> datetime | None:
    """Parse any known match datetime into an aware UTC datetime."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, time.min)
    elif isinstance(value, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(value), tz=UTC_TZ)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        raw = _clean_datetime_text(value)
        if not raw:
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            dt = datetime.fromisoformat(raw)
        else:
            iso = raw.replace("Z", "+00:00")
            if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$", iso):
                iso += ":00"
            try:
                dt = datetime.fromisoformat(iso)
            except ValueError:
                dt = _from_common_formats(raw)
                if dt is None:
                    return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(UTC_TZ)


def to_madrid_time(value: object) -> datetime | None:
    dt = parse_match_datetime(value)
    return dt.astimezone(MADRID_TZ) if dt else None


def format_madrid_short_time(value: object) -> str:
    dt = to_madrid_time(value)
    return dt.strftime("%H:%M") if dt else ""


def format_madrid_sync_label(value: object) -> str:
    """Return the canonical client label for an operational timestamp."""
    dt = to_madrid_time(value)
    if not dt:
        return "Sin sincronización confirmada"
    return f"{dt.day:02d} {MONTHS_ES_SHORT[dt.month - 1]} {dt.year}, {dt:%H:%M} · Madrid"


def is_today_madrid(value: object) -> bool:
    dt = to_madrid_time(value)
    return bool(dt and dt.date() == madrid_now().date())


def is_tomorrow_madrid(value: object) -> bool:
    dt = to_madrid_time(value)
    return bool(dt and dt.date() == madrid_now().date() + timedelta(days=1))


def format_madrid_date_label(value: object) -> str:
    dt = to_madrid_time(value)
    if not dt:
        return ""
    today = madrid_now().date()
    if dt.date() == today:
        return "Hoy"
    if dt.date() == today + timedelta(days=1):
        return "Mañana"
    return f"{WEEKDAYS_ES[dt.weekday()]} {dt:%d/%m}"


def _status_key(status: object) -> str:
    return re.sub(r"\s+", " ", str(status or "").strip().lower())


def format_madrid_match_time(value: object, status: object = None, minute: object = None) -> str:
    status_key = _status_key(status)
    minute_text = str(minute or "").strip()
    if status_key in FINISHED_STATUSES:
        return "Finalizado"
    if status_key in HALFTIME_STATUSES:
        return "Descanso"
    if status_key in LIVE_STATUSES:
        return f"En directo · {minute_text}" if minute_text else "En directo"
    dt = to_madrid_time(value)
    if not dt:
        return "Hora pendiente"
    return f"{format_madrid_date_label(dt)} · {dt:%H:%M}"


def _first_match_datetime_value(match: dict) -> tuple[str, object]:
    keys = ("kickoff_iso", "commence_time", "start_time", "event_time", "datetime", "date_time", "kickoff")
    for key in keys:
        value = match.get(key)
        if value not in (None, ""):
            return key, value
    date_value = match.get("match_date") or match.get("date")
    time_value = match.get("kickoff_time") or match.get("match_time") or match.get("time")
    if date_value and time_value:
        return "match_date+time", f"{str(date_value)[:10]}T{str(time_value)[:5]}:00"
    if date_value:
        return "match_date", str(date_value)[:10]
    return "", ""


def normalize_kickoff_for_display(match: dict | None) -> dict:
    item = dict(match or {})
    key, raw_value = _first_match_datetime_value(item)
    warnings: list[str] = []
    raw_text = str(raw_value or "").strip()
    dt_madrid = None
    dt_utc = None
    if key == "match_date+time":
        dt_madrid = madrid_local_from_parts(item.get("match_date") or item.get("date"), item.get("kickoff_time") or item.get("match_time") or item.get("time"))
        dt_utc = dt_madrid.astimezone(UTC_TZ) if dt_madrid else None
        if dt_madrid:
            warnings.append("manual_madrid_local")
        else:
            warnings.append("missing_or_invalid_madrid_time")
    elif key == "match_date":
        dt_utc = None
        dt_madrid = None
        warnings.append("date_without_time")
    else:
        dt_utc = parse_match_datetime(raw_value)
        dt_madrid = dt_utc.astimezone(MADRID_TZ) if dt_utc else None
        if not raw_text:
            warnings.append("missing_kickoff")
        elif raw_text and not _has_tz_suffix(raw_text) and "T" in raw_text:
            warnings.append("naive_api_datetime_assumed_utc")
    if raw_text.endswith("+01:00") or raw_text.endswith("+02:00"):
        warnings.append("source_already_timezone_aware")
    if dt_madrid:
        item["madrid_dt_iso"] = dt_madrid.isoformat(timespec="seconds")
        item["madrid_utc_iso"] = dt_utc.isoformat(timespec="seconds")
        item["madrid_time"] = dt_madrid.strftime("%H:%M")
        item["madrid_date"] = dt_madrid.date().isoformat()
        item["madrid_date_label"] = format_madrid_date_label(dt_madrid)
        item["madrid_display"] = format_madrid_match_time(
            dt_madrid,
            item.get("status"),
            item.get("minute") or (item.get("live_depth") or {}).get("minute"),
        )
        item["match_date"] = item["madrid_date"]
        item["kickoff_time"] = item["madrid_time"]
        item["match_time"] = item["madrid_time"]
        item["safe_time"] = item["madrid_time"]
        item["safe_date"] = dt_madrid.strftime("%d/%m/%Y")
        item["safe_datetime"] = f"{item['safe_date']} · {item['madrid_time']}"
        item["display_time"] = item["madrid_time"]
        item["display_date_label"] = item["madrid_date_label"]
        item["display_status_label"] = item["madrid_display"]
        item["kickoff_display"] = item["madrid_display"]
        item["display_datetime"] = item["madrid_display"]
        item["kickoff_iso_madrid"] = item["madrid_dt_iso"]
    else:
        fallback_date = str(item.get("match_date") or "")[:10]
        fallback_time = str(item.get("kickoff_time") or item.get("match_time") or "")[:5]
        item["madrid_time"] = fallback_time
        item["madrid_date"] = fallback_date
        item["madrid_date_label"] = format_madrid_date_label(fallback_date) if fallback_date else "Sin fecha"
        item["madrid_display"] = (f"{item['madrid_date_label']} · {fallback_time}" if fallback_date and fallback_time else (f"{item['madrid_date_label']} · Hora pendiente" if fallback_date else "Hora pendiente"))
        item["safe_time"] = fallback_time or "Hora pendiente"
        item["safe_date"] = item.get("safe_date") or fallback_date
        item["display_time"] = item["safe_time"]
        item["display_date_label"] = item["madrid_date_label"] or "Sin fecha"
        item["display_status_label"] = item["madrid_display"]
        item["kickoff_display"] = item["madrid_display"]
        item["display_datetime"] = item.get("display_datetime") or item["madrid_display"]
    item["timezone_label"] = "Europe/Madrid"
    item["time_context"] = "Hora oficial de España (Madrid)"
    item["time_source_field"] = key
    item["time_source_value"] = raw_text
    item["time_warnings"] = warnings
    return item


def _madrid_label_from_dt(dt: datetime) -> str:
    today = madrid_now().date()
    if dt.date() == today:
        return "Hoy"
    if dt.date() == today + timedelta(days=1):
        return "Mañana"
    return f"{WEEKDAYS_ES[dt.weekday()]} {dt:%d/%m}"


def format_telegram_match_time_madrid(match: dict | None) -> dict:
    """Return Telegram-ready match time labels in Europe/Madrid.

    Sports API datetimes with ``Z`` or an explicit offset are converted to
    Madrid. Manual admin values expressed as ``match_date`` + ``match_time``
    are treated as Madrid local time, so they are not shifted again.
    """
    item = dict(match or {})
    source_key, raw_value = _first_match_datetime_value(item)
    raw_text = str(raw_value or "").strip()
    warning = ""
    detected = "unknown"
    dt_madrid: datetime | None = None

    if source_key == "match_date+time":
        date_value = str(item.get("match_date") or item.get("date") or "")[:10]
        time_value = str(item.get("kickoff_time") or item.get("match_time") or item.get("time") or "")[:5]
        try:
            dt_madrid = datetime.fromisoformat(f"{date_value}T{time_value}:00").replace(tzinfo=MADRID_TZ)
            detected = "madrid_local_manual"
        except ValueError:
            warning = "ambiguous_manual_datetime"
    elif raw_text:
        dt_utc = parse_match_datetime(raw_text)
        if dt_utc:
            dt_madrid = dt_utc.astimezone(MADRID_TZ)
            detected = "utc_or_offset" if _has_tz_suffix(raw_text) else "naive_assumed_utc"
            if detected == "naive_assumed_utc":
                warning = "naive_api_datetime_assumed_utc"
        else:
            warning = "unparseable_datetime"
    else:
        warning = "missing_datetime"

    if not dt_madrid:
        fallback_date = str(item.get("match_date") or "")[:10]
        fallback_time = str(item.get("kickoff_time") or item.get("match_time") or "")[:5]
        fallback_label = "Hora pendiente"
        if fallback_date and fallback_time:
            fallback_label = f"{fallback_date} · {fallback_time} · Madrid"
        elif fallback_time:
            fallback_label = f"{fallback_time} · Madrid"
        return {
            "date_label": fallback_date,
            "time_label": fallback_time,
            "datetime_label": fallback_label,
            "iso_madrid": "",
            "source_timezone_detected": detected,
            "source_field": source_key,
            "source_value": raw_text,
            "warning": warning,
        }

    return {
        "date_label": _madrid_label_from_dt(dt_madrid),
        "time_label": dt_madrid.strftime("%H:%M"),
        "datetime_label": f"{_madrid_label_from_dt(dt_madrid)} · {dt_madrid:%H:%M} · Madrid",
        "iso_madrid": dt_madrid.isoformat(timespec="seconds"),
        "source_timezone_detected": detected,
        "source_field": source_key,
        "source_value": raw_text,
        "warning": warning,
    }


def madrid_conversion_selftest() -> dict:
    cases = [
        ("summer_utc_1900", "2026-06-12T19:00:00Z", "21:00"),
        ("winter_utc_2000", "2026-12-12T20:00:00Z", "21:00"),
    ]
    results = []
    ok = True
    for name, raw, expected in cases:
        got = format_madrid_short_time(raw)
        passed = got == expected
        ok = ok and passed
        results.append({"name": name, "input": raw, "expected": expected, "got": got, "ok": passed})
    return {"ok": ok, "timezone": "Europe/Madrid", "cases": results}


def madrid_time_diagnostics(matches: list[dict]) -> dict:
    rows = []
    warnings_count: dict[str, int] = {}
    for match in matches:
        item = normalize_kickoff_for_display(match)
        for warning in item.get("time_warnings", []):
            warnings_count[warning] = warnings_count.get(warning, 0) + 1
        rows.append({
            "id": item.get("id"),
            "home_team": item.get("home_team") or item.get("home"),
            "away_team": item.get("away_team") or item.get("away"),
            "competition": item.get("competition_name") or item.get("league_name"),
            "original_field": item.get("time_source_field"),
            "original": item.get("time_source_value"),
            "utc": item.get("madrid_utc_iso", ""),
            "madrid": item.get("madrid_dt_iso", ""),
            "display": item.get("madrid_display"),
            "warnings": item.get("time_warnings", []),
        })
    return {"selftest": madrid_conversion_selftest(), "total": len(rows), "warnings": warnings_count, "matches": rows}
