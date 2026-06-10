"""Premium Telegram delivery helpers for NeMeSiS SHARK PRO.

Pure helpers only. Persistence, HTTP and Flask live in app.py.
"""

import hashlib
import html
import re
from datetime import datetime

from engines.spanish_localization_engine import (
    apply_match_localization,
    apply_pick_localization,
    madrid_values_from_datetime,
    spanish_competition_name,
    spanish_country_name,
    spanish_team_name,
)


DEFAULT_SETTINGS = {
    "id": "default",
    "enabled": False,
    "auto_daily_matches": True,
    "auto_daily_picks": False,
    "auto_live_alerts": False,
    "daily_matches_time": "09:00",
    "daily_picks_time": "11:00",
    "max_messages_per_hour": 10,
}


QUEUE_PENDING = "pending"
QUEUE_SENDING = "sending"
QUEUE_SENT = "sent"
QUEUE_FAILED = "failed"
QUEUE_SKIPPED = "skipped"


_COUNTRY_FLAGS = {
    "spain": "🇪🇸",
    "españa": "🇪🇸",
    "england": "🏴",
    "united kingdom": "🇬🇧",
    "france": "🇫🇷",
    "germany": "🇩🇪",
    "italy": "🇮🇹",
    "portugal": "🇵🇹",
    "netherlands": "🇳🇱",
    "argentina": "🇦🇷",
    "brazil": "🇧🇷",
    "usa": "🇺🇸",
    "united states": "🇺🇸",
    "international": "🌍",
    "internacional": "🌍",
    "mundial": "🌍",
    "world": "🌍",
    "global": "🌍",
    "méxico": "🇲🇽",
    "mexico": "🇲🇽",
    "sudáfrica": "🇿🇦",
    "corea del sur": "🇰🇷",
    "república checa": "🇨🇿",
}


_COMPETITION_EMOJIS = {
    "champions": "🏆",
    "europa": "🌍",
    "conference": "🌍",
    "laliga": "🇪🇸",
    "liga": "🏆",
    "premier": "🏴",
    "serie a": "🇮🇹",
    "bundesliga": "🇩🇪",
    "ligue 1": "🇫🇷",
    "portugal": "🇵🇹",
    "cup": "🏆",
    "copa": "🏆",
    "world": "🌍",
    "mundial": "🌍",
}


_SEPARATOR = "━━━━━━━━━━━━━━━━"


def safe_html(value):
    return html.escape(str(value or ""), quote=False)


def safe_url(value):
    url = str(value or "").strip()
    if not re.match(r"^https?://", url, flags=re.I):
        return ""
    return html.escape(url, quote=True)


def compact_text(value, max_len=220):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_len:
        return text
    return text[: max(0, max_len - 1)].rstrip() + "…"


def telegram_dedupe_key(message_type, date_key, target_key="global"):
    raw = f"{message_type}:{date_key}:{target_key}".lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def normalize_settings(row=None):
    settings = dict(DEFAULT_SETTINGS)
    if row:
        for key in DEFAULT_SETTINGS:
            if key in row and row.get(key) is not None:
                settings[key] = row.get(key)
    for key in ("enabled", "auto_daily_matches", "auto_daily_picks", "auto_live_alerts"):
        settings[key] = str(settings.get(key)).lower() in {"1", "true", "yes", "on"} or settings.get(key) is True
    settings["max_messages_per_hour"] = max(1, int(settings.get("max_messages_per_hour") or 10))
    return settings


def membership_label(value):
    value = str(value or "FREE").upper()
    if value not in {"FREE", "PRO", "ELITE", "ADMIN"}:
        return "FREE"
    return value


def subscriber_payload(user=None, chat_id="", username="", first_name="", membership="FREE"):
    user = dict(user or {})
    return {
        "user_id": user.get("id") or "",
        "chat_id": chat_id or user.get("telegram_chat_id") or "",
        "username": username or user.get("username") or "",
        "first_name": first_name or user.get("name") or "",
        "membership": membership_label(membership or user.get("membership")),
        "is_active": True,
    }


def _first_value(data, keys, default=""):
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def _competition_name(item):
    return spanish_competition_name(_first_value(item, ["competition_name", "league_name", "competition", "league"], "Competición")) or "Competición"


def _competition_emoji(item):
    country = str(spanish_country_name(item.get("country") or item.get("safe_country") or "") or "").strip().lower()
    if country in _COUNTRY_FLAGS:
        return _COUNTRY_FLAGS[country]
    comp = str(_competition_name(item)).lower()
    for key, emoji in _COMPETITION_EMOJIS.items():
        if key in comp:
            return emoji
    return "🏆"


def _format_date(value):
    raw = str(value or "").strip()
    if not raw:
        return "Fecha pendiente"
    values = madrid_values_from_datetime(raw)
    if values.get("safe_datetime"):
        return values["safe_datetime"]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw[:19] if "T" in raw else raw[:19], fmt)
            if fmt == "%Y-%m-%d":
                return dt.strftime("%d/%m/%Y")
            return dt.strftime("%d/%m/%Y · %H:%M")
        except ValueError:
            continue
    return raw


def _match_time(item):
    values = madrid_values_from_datetime(item.get("kickoff_iso") or item.get("kickoff_iso_madrid") or "", item.get("match_date") or item.get("date"), item.get("kickoff_time") or item.get("match_time") or item.get("time"))
    if values.get("safe_time") and values.get("safe_time") != "Hora":
        return safe_html(values["safe_time"])
    time = _first_value(item, ["safe_time", "kickoff_time", "match_time", "time", "minute"], "")
    date = _first_value(item, ["safe_date", "match_date", "date", "kickoff_iso"], "")
    if time:
        return safe_html(time)
    return safe_html(_format_date(date))


def _team_crest_url(item, side):
    identity = item.get(f"{side}_identity") or {}
    keys = [
        f"{side}_logo",
        f"{side}_badge",
        f"{side}_crest_url",
        f"{side}_team_logo",
        f"{side}_team_badge",
    ]
    url = _first_value(item, keys, "") or identity.get("crest_url") or identity.get("logo_url") or ""
    return safe_url(url)


def _crest_anchor(url, fallback="⚽"):
    url = safe_url(url)
    if not url:
        return fallback
    return f'<a href="{url}">🛡️</a>'


def _team_block(item, side):
    team = safe_html(spanish_team_name(_first_value(item, [f"{side}_team", f"{side}", f"{side}_name"], "Equipo")) or "Equipo")
    crest = _crest_anchor(_team_crest_url(item, side))
    side_icon = "🏠" if side == "home" else "✈️"
    return f"{side_icon} {crest} <b>{team}</b>"


def _score_text(item):
    score = _first_value(item, ["score", "result", "live_score"], "")
    if score:
        return safe_html(score)
    home_score = item.get("home_score")
    away_score = item.get("away_score")
    if home_score not in (None, "") and away_score not in (None, ""):
        return safe_html(f"{home_score}-{away_score}")
    return ""


def _status_label(item):
    live_depth = item.get("live_depth") or {}
    status = live_depth.get("label") or item.get("status_label") or item.get("status") or "Programado"
    minute = live_depth.get("minute") or item.get("minute") or ""
    if minute and str(minute).lower() not in {"hora", "programado"}:
        return f"{safe_html(status)} · {safe_html(minute)}"
    return safe_html(status)


def _odds_line(item):
    bookmaker = item.get("bookmaker") or item.get("bookmaker_name") or ""
    home_odds = item.get("home_odds") or item.get("odds_home")
    draw_odds = item.get("draw_odds") or item.get("odds_draw")
    away_odds = item.get("away_odds") or item.get("odds_away")
    if any(x not in (None, "", 0, 0.0) for x in (home_odds, draw_odds, away_odds)):
        pieces = []
        if home_odds:
            pieces.append(f"1 {safe_html(home_odds)}")
        if draw_odds:
            pieces.append(f"X {safe_html(draw_odds)}")
        if away_odds:
            pieces.append(f"2 {safe_html(away_odds)}")
        book = f" · {safe_html(bookmaker)}" if bookmaker else ""
        return f"💹 <b>Cuotas:</b> {' · '.join(pieces)}{book}"
    if bookmaker:
        return f"💹 <b>Casa:</b> {safe_html(bookmaker)}"
    return ""


def _match_url_line(item, label="Abrir partido en la app"):
    url = safe_url(item.get("match_url") or item.get("url") or "")
    if not url:
        return ""
    return f'🔗 <a href="{url}">{safe_html(label)}</a>'


def format_match_line(match):
    match = apply_match_localization(match)
    comp = safe_html(_competition_name(match))
    time = _match_time(match)
    status = _status_label(match)
    score = _score_text(match)
    score_line = f" · <b>{score}</b>" if score else ""
    lines = [
        f"{_competition_emoji(match)} <b>{comp}</b>",
        f"🕘 {time} h España · {status}{score_line}",
        _team_block(match, "home"),
        "🆚",
        _team_block(match, "away"),
    ]
    odds = _odds_line(match)
    if odds:
        lines.append(odds)
    match_url = _match_url_line(match)
    if match_url:
        lines.append(match_url)
    return "\n".join(lines)


def build_daily_matches_message(matches, date_key, premium_name="NeMeSiS SHARK PRO"):
    lines = [
        f"<b>🦈 {safe_html(premium_name)}</b>",
        f"<b>📅 Partidos destacados · {safe_html(_format_date(date_key))}</b>",
        _SEPARATOR,
    ]
    if not matches:
        lines.extend([
            "No hay partidos sincronizados para hoy.",
            "El calendario se actualizará cuando las fuentes autorizadas tengan datos.",
        ])
    else:
        for index, match in enumerate(matches[:8], start=1):
            lines.append(f"<b>#{index}</b>")
            lines.append(format_match_line(match))
            lines.append(_SEPARATOR)
    lines.append("🧠 SHARK revisa calendario, cuotas, estado live y valor antes de publicar picks.")
    return "\n".join(lines).strip()


def _pick_value_label(pick):
    explicit = pick.get("value_label") or pick.get("value") or pick.get("ev_label") or ""
    if explicit:
        return safe_html(explicit)
    odds = pick.get("odds")
    confidence = pick.get("confidence") or pick.get("shark_score")
    if odds and confidence:
        return "Value detectado"
    return "En revisión"


def _pick_score(pick):
    score = pick.get("confidence") or pick.get("shark_score") or pick.get("score") or "-"
    return safe_html(score)


def _stake_text(pick):
    stake = pick.get("stake_units") or pick.get("stake") or "1"
    euros = pick.get("stake_euros_example") or pick.get("stake_euros") or ""
    if euros not in (None, "", 0, 0.0):
        return f"{safe_html(stake)}/5 · ejemplo {safe_html(euros)} €"
    return f"{safe_html(stake)}/5"


def _pick_title(index, pick):
    home = spanish_team_name(_first_value(pick, ["home_team", "home"], "Equipo local"))
    away = spanish_team_name(_first_value(pick, ["away_team", "away"], "Equipo visitante"))
    return f"<b>#{index} · {safe_html(home)} vs {safe_html(away)}</b>"


def build_daily_picks_message(picks, force_empty=False, premium_name="NeMeSiS SHARK PRO"):
    lines = [
        f"<b>🦈 SHARK PICK PREMIUM</b>",
        f"<b>{safe_html(premium_name)}</b>",
        _SEPARATOR,
    ]
    if not picks:
        if not force_empty:
            return ""
        lines.append("No hay picks publicados ahora mismo. SHARK no fabrica picks sin fuente real/autorizada.")
        return "\n".join(lines)

    for index, pick in enumerate(picks[:4], start=1):
        pick = apply_pick_localization(pick)
        comp = safe_html(_competition_name(pick))
        date = safe_html(_format_date(pick.get("match_date") or pick.get("kickoff_iso") or pick.get("date")))
        time = _match_time(pick)
        selection = safe_html(compact_text(pick.get("selection") or "Pick SHARK", 90))
        market = safe_html(compact_text(pick.get("market") or pick.get("pick_type") or "Mercado", 80))
        odds = safe_html(pick.get("odds") or "Pendiente")
        risk = safe_html(pick.get("risk_level") or "Medio")
        reason = safe_html(compact_text(pick.get("reasoning") or pick.get("reason") or "SHARK detecta valor con los datos disponibles.", 260))
        warning = safe_html(compact_text(pick.get("warning_reason") or pick.get("warning") or "Gestiona stake y banca. Ningún pick es seguro.", 220))
        lines.extend(
            [
                _pick_title(index, pick),
                f"{_competition_emoji(pick)} <b>{comp}</b>",
                f"🕘 {date}" + (f" · {time} h España" if time and time != date else " · hora España"),
                _team_block(pick, "home"),
                "🆚",
                _team_block(pick, "away"),
                f"🎯 <b>Pick:</b> <b>{selection}</b>",
                f"🎲 <b>Mercado:</b> {market}",
                f"💰 <b>Cuota:</b> {odds}",
                f"📌 <b>Stake:</b> {_stake_text(pick)}",
                f"🧠 <b>SHARK Score:</b> {_pick_score(pick)}/100",
                f"⚠️ <b>Riesgo:</b> {risk}",
                f"💎 <b>Value:</b> {_pick_value_label(pick)}",
                f"✅ <b>Por qué entrar:</b> {reason}",
                f"🛡️ <b>Precaución:</b> {warning}",
            ]
        )
        match_url = _match_url_line(pick, "Ver partido y contexto SHARK")
        if match_url:
            lines.append(match_url)
        lines.append(_SEPARATOR)
    lines.append("📍 Gestión de riesgo primero. Picks solo desde datos reales, fuente autorizada o motor propio.")
    return "\n".join(lines).strip()


def build_live_alert_message(match, event=None, internal_url="/live"):
    match = apply_match_localization(match)
    event = event or {}
    score = _score_text(match) or "sin marcador"
    minute = safe_html((match.get("live_depth") or {}).get("minute") or match.get("minute") or "LIVE")
    detail = safe_html(compact_text(event.get("title") or event.get("detail") or "Seguimiento en directo", 180))
    url = safe_url(match.get("match_url") or internal_url)
    lines = [
        "<b>🔴 Alerta live SHARK</b>",
        _SEPARATOR,
        f"{_competition_emoji(match)} <b>{safe_html(_competition_name(match))}</b>",
        f"⏱️ <b>{minute}</b> · Marcador: <b>{safe_html(score)}</b>",
        _team_block(match, "home"),
        "🆚",
        _team_block(match, "away"),
        f"🧠 {detail}",
    ]
    if url:
        lines.append(f'🔗 <a href="{url}">Abrir live en NeMeSiS</a>')
    return "\n".join(lines).strip()


def build_system_test_message(now_iso, premium_name="NeMeSiS SHARK PRO"):
    return "\n".join(
        [
            f"<b>🦈 {safe_html(premium_name)}</b>",
            "✅ Mensaje de prueba admin.",
            f"🕘 Hora: {safe_html(now_iso)}",
            "Canal Telegram premium operativo si recibes este aviso.",
        ]
    )


def queue_summary(rows):
    counts = {QUEUE_PENDING: 0, QUEUE_SENDING: 0, QUEUE_SENT: 0, QUEUE_FAILED: 0, QUEUE_SKIPPED: 0}
    for row in rows or []:
        status = str(row.get("status") or "").lower()
        counts[status] = counts.get(status, 0) + 1
    return counts
