"""Build a factual, single-match iCalendar download from persisted match data."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo


_MADRID = ZoneInfo("Europe/Madrid")


def _unambiguous_madrid_time(value: datetime) -> datetime | None:
    """Attach Madrid time only when the wall clock maps to one real instant."""
    instants: dict[datetime, datetime] = {}
    for fold in (0, 1):
        candidate = value.replace(tzinfo=_MADRID, fold=fold)
        instant = candidate.astimezone(timezone.utc)
        if instant.astimezone(_MADRID).replace(tzinfo=None) == value:
            instants[instant] = candidate
    if len(instants) != 1:
        # A missing instant is a daylight-saving gap; two distinct instants
        # are the repeated hour at the autumn clock change.
        return None
    return next(iter(instants)).astimezone(_MADRID)


def _text(value: Any, limit: int = 240) -> str:
    if value is None:
        return ""
    return str(value).strip()[:limit]


def _escape_ical(value: Any) -> str:
    text = _text(value, 1000).replace("\\", "\\\\")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(char for char in text if char == "\n" or ord(char) >= 0x20)
    return text.replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def _fold_ical_line(line: str, limit: int = 75) -> list[str]:
    """Fold by UTF-8 octets, as required by RFC 5545, without splitting a character."""
    pieces: list[str] = []
    current = ""
    current_bytes = 0
    for char in line:
        encoded_size = len(char.encode("utf-8"))
        if current and current_bytes + encoded_size > limit:
            pieces.append(current)
            current = " "
            current_bytes = 1
        current += char
        current_bytes += encoded_size
    pieces.append(current)
    return pieces


def _kickoff(match: Mapping[str, Any]) -> datetime | date | None:
    raw_iso = _text(match.get("kickoff_iso"), 80)
    candidates: list[str] = []
    iso_date: date | None = None
    if raw_iso:
        try:
            iso_date = date.fromisoformat(raw_iso)
        except ValueError:
            candidates.append(raw_iso)
    match_date = _text(match.get("match_date"), 20)
    match_time = _text(match.get("kickoff_time") or match.get("match_time"), 20)
    # `kickoff_iso` is the canonical kickoff source in the rest of the app. If it
    # carries only a date, combine an available local kickoff time with that
    # date instead of silently replacing it with a conflicting legacy date.
    date_source = iso_date.isoformat() if iso_date else match_date
    if date_source and match_time:
        candidates.append(f"{date_source}T{match_time}")

    for raw in candidates:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        # NeMeSiS displays unspecific provider/local times in Madrid time.
        if parsed.tzinfo is None:
            parsed = _unambiguous_madrid_time(parsed)
            if parsed is None:
                return None
        return parsed.astimezone(timezone.utc)

    if date_source:
        try:
            return date.fromisoformat(date_source)
        except ValueError:
            return None
    return None


def build_match_calendar_event(
    match: Mapping[str, Any] | None,
    *,
    event_url: str,
    static_copy_notice: str = "Copia estática importada; no se actualiza automáticamente.",
    lifecycle_label: str = "",
    generated_at: datetime | None = None,
) -> str | None:
    """Return one factual iCalendar event, respecting the canonical match lifecycle."""
    item = dict(match or {})
    match_id = _text(item.get("id") or item.get("external_id"), 160)
    home = _text(item.get("home_team"), 160)
    away = _text(item.get("away_team"), 160)
    lifecycle = _text(item.get("calendar_lifecycle"), 32).upper() or "UPCOMING"
    uncertain_lifecycles = {"POSTPONED", "SUSPENDED", "STALE", "INCOMPLETE", "CONFLICT", "ARCHIVED"}
    cancelled_lifecycles = {"CANCELLED", "ABANDONED"}
    kickoff = None if lifecycle in uncertain_lifecycles else _kickoff(item)
    # This is a static import file, not an iTIP scheduling transaction. Do not
    # emit METHOD:PUBLISH (which requires ORGANIZER and DTSTART), and refuse to
    # manufacture an event when the stored kickoff is not trustworthy.
    if not (match_id and home and away and kickoff is not None):
        return None

    stamp = generated_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    stamp = stamp.astimezone(timezone.utc)
    uid = hashlib.sha256(match_id.encode("utf-8")).hexdigest() + "@nemesis-shark-pro"
    lifecycle_prefixes = {
        "CANCELLED": "Cancelado",
        "ABANDONED": "Abandonado",
    }
    prefix = _text(lifecycle_label, 80) or lifecycle_prefixes.get(lifecycle, "")
    summary = f"{prefix}: {home} vs {away}" if prefix else f"{home} vs {away}"
    competition = _text(item.get("competition_name") or item.get("league_name"), 160)
    venue = _text(item.get("venue"), 160)
    description = []
    if competition:
        description.append(f"Competición: {competition}")
    if isinstance(kickoff, date) and not isinstance(kickoff, datetime):
        description.append("Hora de inicio no disponible en la fuente; se añade solo la fecha.")
    if _text(static_copy_notice, 500):
        description.append(_text(static_copy_notice, 500))

    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//NeMeSiS SHARK PRO//Calendario de partidos//ES",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp.strftime('%Y%m%dT%H%M%SZ')}",
    ]
    if isinstance(kickoff, datetime):
        lines.append(f"DTSTART:{kickoff.strftime('%Y%m%dT%H%M%SZ')}")
    elif isinstance(kickoff, date):
        lines.append(f"DTSTART;VALUE=DATE:{kickoff.strftime('%Y%m%d')}")
    if lifecycle in cancelled_lifecycles:
        lines.append("STATUS:CANCELLED")
    elif lifecycle == "RESULT_PENDING":
        lines.append("STATUS:TENTATIVE")
    else:
        lines.append("STATUS:CONFIRMED")
    lines.append(f"SUMMARY:{_escape_ical(summary)}")
    if _text(event_url, 1000):
        lines.append(f"URL:{_escape_ical(event_url)}")
    if description:
        lines.append(f"DESCRIPTION:{_escape_ical(chr(10).join(description))}")
    if venue:
        lines.append(f"LOCATION:{_escape_ical(venue)}")
    lines.extend(["END:VEVENT", "END:VCALENDAR"])
    physical_lines = [part for line in lines for part in _fold_ical_line(line)]
    return "\r\n".join(physical_lines) + "\r\n"
