"""Premium Telegram delivery helpers for NeMeSiS SHARK PRO.

Pure formatting helpers only. Persistence, HTTP and Flask live in app.py.
The goal is to keep Telegram messages short, elegant, safe and commercial.
"""

from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime

from engines.telegram_sport_filter_engine import is_telegram_football_item
from engines.picks_quality_engine import enrich_pick_quality, sort_picks_by_quality

from engines.spanish_localization_engine import (
    apply_match_localization,
    apply_pick_localization,
    madrid_values_from_datetime,
    spanish_competition_name,
    spanish_country_name,
    spanish_datetime_label,
    spanish_market_name,
    spanish_team_name,
)
from engines.madrid_time_engine import format_telegram_match_time_madrid, normalize_kickoff_for_display


DEFAULT_SETTINGS = {
    "id": "default",
    "enabled": False,
    "auto_daily_matches": True,
    "auto_daily_picks": False,
    "auto_live_alerts": False,
    "daily_matches_time": "10:00",
    "daily_picks_time": "13:30",
    "max_messages_per_hour": 1,
}


QUEUE_PENDING = "pending"
QUEUE_SENDING = "sending"
QUEUE_SENT = "sent"
QUEUE_FAILED = "failed"
QUEUE_SKIPPED = "skipped"


_SEPARATOR = "━━━━━━━━━━━━━━━━"
_SOFT_SEPARATOR = "────────────"

_COUNTRY_FLAGS = {
    "spain": "🇪🇸",
    "españa": "🇪🇸",
    "england": "🏴",
    "inglaterra": "🏴",
    "united kingdom": "🇬🇧",
    "france": "🇫🇷",
    "francia": "🇫🇷",
    "germany": "🇩🇪",
    "alemania": "🇩🇪",
    "italy": "🇮🇹",
    "italia": "🇮🇹",
    "portugal": "🇵🇹",
    "netherlands": "🇳🇱",
    "países bajos": "🇳🇱",
    "argentina": "🇦🇷",
    "brazil": "🇧🇷",
    "brasil": "🇧🇷",
    "usa": "🇺🇸",
    "united states": "🇺🇸",
    "estados unidos": "🇺🇸",
    "international": "🌍",
    "internacional": "🌍",
    "mundial": "🌍",
    "world": "🌍",
    "global": "🌍",
    "mexico": "🇲🇽",
    "méxico": "🇲🇽",
    "south africa": "🇿🇦",
    "sudáfrica": "🇿🇦",
    "south korea": "🇰🇷",
    "corea del sur": "🇰🇷",
    "czech republic": "🇨🇿",
    "república checa": "🇨🇿",
    "canada": "🇨🇦",
    "canadá": "🇨🇦",
    "bosnia y herzegovina": "🇧🇦",
    "bosnia and herzegovina": "🇧🇦",
    "japan": "🇯🇵",
    "japón": "🇯🇵",
    "morocco": "🇲🇦",
    "marruecos": "🇲🇦",
    "croatia": "🇭🇷",
    "croacia": "🇭🇷",
    "switzerland": "🇨🇭",
    "suiza": "🇨🇭",
    "belgium": "🇧🇪",
    "bélgica": "🇧🇪",
    "uruguay": "🇺🇾",
    "colombia": "🇨🇴",
    "chile": "🇨🇱",
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
    "fifa": "🌍",
}

_BAD_WORDS = re.compile(r"\b(none|null|undefined|nan)\b", flags=re.I)
_PENDING_PICK_RE = re.compile(
    r"(esperar|pendiente|sin cuota|no disponible|value en c[aá]lculo|cuota pendiente|mercado pendiente|null|none|undefined)",
    flags=re.I,
)


def safe_html(value) -> str:
    text = str(value if value is not None else "").strip()
    if not text or _BAD_WORDS.fullmatch(text):
        return ""
    return html.escape(text, quote=False)


def safe_url(value) -> str:
    url = str(value or "").strip()
    if not re.match(r"^https?://", url, flags=re.I):
        return ""
    return html.escape(url, quote=True)


def compact_text(value, max_len=220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = _BAD_WORDS.sub("", text).strip()
    if len(text) <= max_len:
        return text
    return text[: max(0, max_len - 1)].rstrip() + "…"


def telegram_dedupe_key(message_type, date_key, target_key="global", pick_id="", match_id="", market="", source="automatic") -> str:
    """Build a Telegram dedupe key specific enough for automated picks.

    Kept backward-compatible with older calls while allowing V752 automation to
    distinguish source, pick, match, market, destination and Madrid date.
    """
    raw = f"telegram:{source}:{message_type}:{pick_id or date_key}:{match_id}:{market}:{target_key}:{date_key}".lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def normalize_settings(row=None) -> dict:
    settings = dict(DEFAULT_SETTINGS)
    if row:
        for key in DEFAULT_SETTINGS:
            if key in row and row.get(key) is not None:
                settings[key] = row.get(key)
    for key in ("enabled", "auto_daily_matches", "auto_daily_picks", "auto_live_alerts"):
        settings[key] = str(settings.get(key)).lower() in {"1", "true", "yes", "on"} or settings.get(key) is True
    settings["max_messages_per_hour"] = max(1, int(settings.get("max_messages_per_hour") or 10))
    return settings


def membership_label(value) -> str:
    value = str(value or "FREE").upper()
    if value not in {"FREE", "PRO", "ELITE", "ADMIN"}:
        return "FREE"
    return value


def subscriber_payload(user=None, chat_id="", username="", first_name="", membership="FREE") -> dict:
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


def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _competition_name(item) -> str:
    return spanish_competition_name(_first_value(item, ["competition_name", "league_name", "competition", "league"], "Competición")) or "Competición"


def _flag_for(value) -> str:
    translated = spanish_country_name(value) or spanish_team_name(value) or str(value or "")
    key = _norm(translated)
    if key in _COUNTRY_FLAGS:
        return _COUNTRY_FLAGS[key]
    raw = _norm(value)
    return _COUNTRY_FLAGS.get(raw, "")


def _team_emoji(team) -> str:
    return _flag_for(team) or "⚽"


def _competition_emoji(item) -> str:
    country = spanish_country_name(item.get("country") or item.get("safe_country") or "")
    flag = _flag_for(country)
    if flag:
        return flag
    comp = str(_competition_name(item)).lower()
    for key, emoji in _COMPETITION_EMOJIS.items():
        if key in comp:
            return emoji
    return "🏆"


def _display_datetime(item) -> str:
    item_for_time = dict(item or {})
    # Some payloads store an ISO API datetime inside kickoff_time instead of kickoff_iso.
    # Promote it for the Madrid helper so Telegram never shows raw/truncated UTC labels.
    kickoff_raw = str(item_for_time.get("kickoff_time") or "").strip()
    if kickoff_raw and ("T" in kickoff_raw or kickoff_raw.endswith("Z")) and not item_for_time.get("kickoff_iso"):
        item_for_time["kickoff_iso"] = kickoff_raw
    telegram_time = format_telegram_match_time_madrid(item_for_time)
    if telegram_time.get("datetime_label") and telegram_time.get("datetime_label") != "Hora pendiente":
        return telegram_time["datetime_label"]
    localized = normalize_kickoff_for_display(item_for_time)
    return (
        localized.get("madrid_display")
        or localized.get("display_datetime")
        or spanish_datetime_label(
            localized.get("kickoff_iso") or localized.get("kickoff_iso_madrid") or localized.get("madrid_dt_iso") or "",
            localized.get("match_date") or localized.get("date"),
            localized.get("kickoff_time") or localized.get("match_time") or localized.get("time"),
        )
    )


def _format_date(value) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "Hoy"
    values = madrid_values_from_datetime(raw)
    if values.get("safe_datetime"):
        return values["safe_datetime"]
    try:
        dt = datetime.strptime(raw[:10], "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return raw


def _team_name(item, side) -> str:
    return spanish_team_name(_first_value(item, [f"{side}_team", f"{side}", f"{side}_name"], "")) or ("Equipo local" if side == "home" else "Equipo visitante")


def _match_title(item) -> str:
    home = _team_name(item, "home")
    away = _team_name(item, "away")
    return f"{_team_emoji(home)} {safe_html(home)} vs {safe_html(away)} {_team_emoji(away)}".strip()


def _score_text(item) -> str:
    score = _first_value(item, ["score", "result", "live_score"], "")
    if score:
        return safe_html(score)
    home_score = item.get("home_score")
    away_score = item.get("away_score")
    if home_score not in (None, "") and away_score not in (None, ""):
        return safe_html(f"{home_score}-{away_score}")
    return ""


def _status_label(item) -> str:
    live_depth = item.get("live_depth") or {}
    status = live_depth.get("label") or item.get("status_label") or item.get("status") or "Programado"
    minute = live_depth.get("minute") or item.get("minute") or ""
    status = str(status or "Programado").replace("scheduled", "Programado").replace("live", "En directo")
    if minute and str(minute).lower() not in {"hora", "programado"}:
        return f"{safe_html(status)} · {safe_html(minute)}"
    return safe_html(status)


def _clean_odds(value) -> str:
    try:
        odds = float(str(value).replace(",", "."))
    except Exception:
        return ""
    if odds <= 1.0:
        return ""
    return f"{odds:.2f}".rstrip("0").rstrip(".")


def _odds_text(value) -> str:
    odds = _clean_odds(value)
    return odds if odds else "No disponible · revisar antes de entrar"


def _odds_line(item) -> str:
    bookmaker = item.get("bookmaker") or item.get("bookmaker_name") or ""
    home_odds = _clean_odds(item.get("home_odds") or item.get("odds_home"))
    draw_odds = _clean_odds(item.get("draw_odds") or item.get("odds_draw"))
    away_odds = _clean_odds(item.get("away_odds") or item.get("odds_away"))
    pieces = []
    if home_odds:
        pieces.append(f"1 {safe_html(home_odds)}")
    if draw_odds:
        pieces.append(f"X {safe_html(draw_odds)}")
    if away_odds:
        pieces.append(f"2 {safe_html(away_odds)}")
    if pieces:
        book = f" · {safe_html(bookmaker)}" if bookmaker else ""
        return f"💹 <b>Cuotas:</b> {' · '.join(pieces)}{book}"
    return ""


def _match_url_line(item, label="Abrir partido en la app") -> str:
    url = safe_url(item.get("match_url") or item.get("url") or "")
    if not url:
        return ""
    return f'🔗 <a href="{url}">{safe_html(label)}</a>'


def _pick_score(pick) -> str:
    score = pick.get("confidence") or pick.get("shark_score") or pick.get("score") or ""
    try:
        return str(int(float(score)))
    except Exception:
        return safe_html(score) or "--"


def _stake_text(pick) -> str:
    stake = pick.get("stake_units") or pick.get("stake") or pick.get("stake_suggested") or "1"
    text = str(stake).strip()
    if "/" in text:
        return safe_html(text)
    try:
        n = float(text.replace(",", "."))
        if n > 10:
            n = min(10, n / 10)
        return f"{n:g}/10"
    except Exception:
        return f"{safe_html(text)}/10" if text else "1/10"


def _risk_text(pick) -> str:
    risk = str(pick.get("risk_level") or pick.get("risk") or "Medio").strip().lower()
    if risk in {"low", "bajo", "baja"}:
        return "Bajo"
    if risk in {"high", "alto", "alta"}:
        return "Alto"
    if "alto" in risk:
        return "Alto"
    if "bajo" in risk:
        return "Bajo"
    return "Medio"


def _market_text(pick) -> str:
    market = pick.get("market") or pick.get("pick_type") or "Ganador del partido"
    translated = spanish_market_name(market) or "Ganador del partido"
    return compact_text(translated, 60)


def _selection_text(pick) -> str:
    pick = dict(pick or {})
    raw = str(pick.get("selection") or pick.get("pick") or pick.get("recommendation") or pick.get("pick_type") or "").strip()
    home = _team_name(pick, "home")
    away = _team_name(pick, "away")
    norm = _norm(raw)
    if not raw or _PENDING_PICK_RE.search(raw):
        return ""
    if norm in {"home", "local", "1", "winner home", "match winner home"}:
        return f"Gana {home}"
    if norm in {"away", "visitante", "2", "winner away", "match winner away"}:
        return f"Gana {away}"
    if norm in {"draw", "empate", "x"}:
        return "Empate"
    over_match = re.search(r"(?:over|m[aá]s de)\s*([0-9]+(?:[\.,][0-9]+)?)", raw, flags=re.I)
    if over_match:
        return f"Más de {over_match.group(1).replace(',', '.')} goles"
    under_match = re.search(r"(?:under|menos de)\s*([0-9]+(?:[\.,][0-9]+)?)", raw, flags=re.I)
    if under_match:
        return f"Menos de {under_match.group(1).replace(',', '.')} goles"
    if "btts" in norm or "both teams" in norm or "ambos equipos" in norm:
        if any(x in norm for x in ["no", "not"]):
            return "Ambos equipos marcan: No"
        return "Ambos equipos marcan: Sí"
    if norm == _norm(home) or norm in _norm(home).split():
        return f"Gana {home}"
    if norm == _norm(away) or norm in _norm(away).split():
        return f"Gana {away}"
    return compact_text(raw, 80)


def _pick_value_label(pick) -> str:
    explicit = pick.get("value_label") or pick.get("value") or pick.get("ev_label") or ""
    if explicit and not _PENDING_PICK_RE.search(str(explicit)):
        return safe_html(compact_text(explicit, 45))
    odds = _odds_text(pick.get("odds"))
    confidence = pick.get("confidence") or pick.get("shark_score")
    if odds and confidence:
        return "Value positivo"
    return "Controlado"


_TELEGRAM_PICK_PRO_MARKER = "V751_TELEGRAM_PICK_ULTRA_PRO"


def _bookmaker_text(pick) -> str:
    bookmaker = pick.get("bookmaker") or pick.get("bookmaker_name") or pick.get("sportsbook") or pick.get("book") or ""
    return safe_html(compact_text(bookmaker, 40)) if bookmaker else "Casa no fijada"


def _quality_badge(pick) -> str:
    try:
        score = int(float(pick.get("quality_score") or pick.get("confidence") or pick.get("shark_score") or 0))
    except Exception:
        score = 0
    label = str(pick.get("quality_label") or "").strip()
    if label:
        return safe_html(compact_text(label, 42))
    if score >= 82:
        return "Entrada premium"
    if score >= 72:
        return "Entrada con valor"
    if score >= 62:
        return "Entrada controlada"
    return "Señal prudente"


def _confidence_bar(pick) -> str:
    try:
        score = max(0, min(100, int(float(pick.get("confidence") or pick.get("shark_score") or pick.get("quality_score") or 0))))
    except Exception:
        score = 0
    filled = max(1, min(5, round(score / 20))) if score else 0
    return "▰" * filled + "▱" * (5 - filled)


def _probability_text(pick) -> str:
    for key in ("probability", "probability_pct", "implied_probability", "win_probability", "shark_probability"):
        value = pick.get(key)
        if value in (None, "", "None"):
            continue
        try:
            n = float(str(value).replace("%", "").replace(",", "."))
            if 0 < n <= 1:
                n *= 100
            if 0 < n <= 100:
                return f"{n:.0f}%"
        except Exception:
            text = compact_text(value, 18)
            if text:
                return safe_html(text)
    return "No publicada"


def _ev_text(pick) -> str:
    for key in ("ev", "expected_value", "ev_pct", "edge", "edge_pct", "value_pct"):
        value = pick.get(key)
        if value in (None, "", "None"):
            continue
        try:
            n = float(str(value).replace("%", "").replace(",", "."))
            if abs(n) <= 1:
                n *= 100
            sign = "+" if n > 0 else ""
            return f"{sign}{n:.1f}%"
        except Exception:
            text = compact_text(value, 18)
            if text:
                return safe_html(text)
    return _pick_value_label(pick)


def _stake_money_text(pick) -> str:
    for key in ("stake_eur", "stake_euros", "stake_amount", "stake_money", "stake_value"):
        value = pick.get(key)
        if value in (None, "", "None"):
            continue
        try:
            n = float(str(value).replace("€", "").replace(",", "."))
            if n > 0:
                return f"{n:g}€"
        except Exception:
            text = compact_text(value, 16)
            if text:
                return safe_html(text)
    return "Según banca"


def _odds_movement_text(pick) -> str:
    for key in ("odds_movement", "line_movement", "movement", "closing_line_note", "odds_trend"):
        text = compact_text(pick.get(key), 70)
        if text:
            return safe_html(text)
    return "Sin movimiento confirmado"


def _pick_context_text(pick) -> str:
    pieces = []
    for key in ("context", "match_context", "analysis_context", "league_context", "shark_context"):
        text = compact_text(pick.get(key), 150)
        if text and not _PENDING_PICK_RE.search(text):
            pieces.append(text)
            break
    if not pieces:
        status = _status_label(pick)
        if status:
            pieces.append(f"Estado del partido: {status}.")
    if not pieces:
        pieces.append("Contexto calculado con los datos disponibles en NeMeSiS.")
    return safe_html(compact_text(" ".join(pieces), 180))


def _reasons_for_pick(pick) -> list[str]:
    raw_values = [
        pick.get("reasoning"), pick.get("reason"), pick.get("motivo"), pick.get("why"),
        pick.get("analysis"), pick.get("headline"), pick.get("summary"),
    ]
    reasons = []
    for raw in raw_values:
        text = compact_text(raw, 170)
        if text and not _PENDING_PICK_RE.search(text) and text not in reasons:
            reasons.append(text)
        if len(reasons) >= 2:
            break
    if not reasons:
        reasons.append("SHARK detecta una señal positiva con cuota real, mercado definido y riesgo controlado.")
    return [safe_html(r) for r in reasons[:2]]


def _risk_controls(pick) -> list[str]:
    raw_values = [pick.get("warning_reason"), pick.get("warning"), pick.get("risk_note"), pick.get("caution"), pick.get("avoid_reason")]
    controls = []
    for raw in raw_values:
        text = compact_text(raw, 150)
        if text and text not in controls:
            controls.append(text)
        if len(controls) >= 2:
            break
    if not controls:
        controls.append("No subir stake si la cuota cae demasiado o aparecen bajas relevantes antes del inicio.")
    return [safe_html(c) for c in controls[:2]]


def _entry_rule_text(pick) -> str:
    odds = _clean_odds(pick.get("odds"))
    if odds:
        try:
            min_odds = max(1.01, float(odds) - 0.08)
            return f"Entrar solo si la cuota se mantiene cerca de {float(odds):.2f}; evitar si baja de {min_odds:.2f}."
        except Exception:
            pass
    return "Entrar solo con cuota disponible y mercado confirmado antes del inicio."


def _professional_footer() -> str:
    return "⚠️ Gestión SHARK: stake responsable, sin perseguir pérdidas y sin convertir una señal en obligación."


def _localize_pick_for_telegram(pick) -> dict:
    raw = dict(pick or {})
    localized = apply_pick_localization(raw)
    # Keep original datetime fields when localization receives a non-standard payload and truncates them.
    for key in ("kickoff_iso", "kickoff_time", "commence_time", "start_time", "event_time", "datetime", "date_time", "kickoff", "match_date", "match_time", "date", "time"):
        raw_value = raw.get(key)
        loc_value = localized.get(key)
        if raw_value not in (None, "") and (loc_value in (None, "") or str(loc_value).strip().endswith("-") or str(loc_value).strip() == "Hora pendiente"):
            localized[key] = raw_value
    return localized


def _premium_pick_card(pick, index: int | None = None, detailed: bool = True) -> list[str]:
    selection = _selection_text(pick)
    odds = _clean_odds(pick.get("odds"))
    comp = safe_html(_competition_name(pick))
    date = safe_html(_display_datetime(pick))
    market = safe_html(_market_text(pick))
    risk = safe_html(_risk_text(pick))
    score = safe_html(_pick_score(pick))
    quality = _quality_badge(pick)
    title_prefix = f"<b>{index}." if index else "<b>"
    title_suffix = "</b>" if index else "</b>"
    lines = [
        f"{title_prefix} {_match_title(pick)}{title_suffix}",
        f"{_competition_emoji(pick)} <b>{comp}</b>",
        f"📅 <b>{date}</b>",
        f"🎯 <b>Entrada:</b> {safe_html(selection)}",
        f"📌 <b>Mercado:</b> {market}",
        f"💰 <b>Cuota:</b> {safe_html(odds)} · {_bookmaker_text(pick)}",
        f"🧮 <b>Stake:</b> {_stake_text(pick)} · {_stake_money_text(pick)}",
        f"📊 <b>SHARK:</b> {score}/100 {_confidence_bar(pick)} · {quality}",
        f"💎 <b>Edge:</b> {_ev_text(pick)} · Prob. SHARK: {_probability_text(pick)}",
        f"⚠️ <b>Riesgo:</b> {risk}",
    ]
    if not detailed:
        lines.append(f"🛡️ <b>Condición:</b> {safe_html(_entry_rule_text(pick))}")
        return lines
    lines.extend([
        "",
        "<b>🧠 Lectura SHARK</b>",
        f"• {_pick_context_text(pick)}",
    ])
    for reason in _reasons_for_pick(pick):
        lines.append(f"• {reason}")
    lines.extend([
        "",
        "<b>🛡️ Gestión y riesgos</b>",
        f"• {safe_html(_entry_rule_text(pick))}",
        f"• Movimiento cuota: {_odds_movement_text(pick)}.",
    ])
    for control in _risk_controls(pick):
        lines.append(f"• {control}")
    lines.extend([
        "",
        "<b>✅ Conclusión</b>",
        f"Entrada válida solo si se mantiene cuota, mercado y lectura previa al partido. Perfil {risk.lower()} con stake {_stake_text(pick)}.",
    ])
    return lines


def format_match_line(match) -> str:
    if not is_telegram_football_item(match or {}):
        return ""
    match = apply_match_localization(match)
    comp = safe_html(_competition_name(match))
    score = _score_text(match)
    score_line = f" · <b>{score}</b>" if score else ""
    lines = [
        f"{_competition_emoji(match)} <b>{comp}</b>",
        f"🕘 {_display_datetime(match)} · {_status_label(match)}{score_line}",
        f"<b>{_match_title(match)}</b>",
    ]
    odds = _odds_line(match)
    if odds:
        lines.append(odds)
    match_url = _match_url_line(match)
    if match_url:
        lines.append(match_url)
    return "\n".join(line for line in lines if line).strip()


def build_daily_matches_message(matches, date_key, premium_name="NeMeSiS SHARK PRO") -> str:
    lines = [
        "<b>🦈 RESUMEN SHARK DEL DÍA</b>",
        f"📅 <b>{safe_html(_format_date(date_key))}</b>",
        _SEPARATOR,
    ]
    matches = [item for item in (matches or []) if is_telegram_football_item(item)]
    if not matches:
        lines.extend([
            "Hoy no hay partidos destacados cargados todavía.",
            "SHARK seguirá revisando calendario, directo y cuotas reales.",
        ])
    else:
        lines.append(f"⚽ <b>{len(matches)} partidos monitorizados</b>")
        lines.append("🔥 Selección destacada:")
        for index, match in enumerate(matches[:6], start=1):
            match = apply_match_localization(match)
            comp = safe_html(_competition_name(match))
            title = _match_title(match)
            time = safe_html(_display_datetime(match))
            score = _score_text(match)
            status = _status_label(match)
            score_part = f" · {score}" if score else ""
            lines.append(f"{index}. {title}")
            lines.append(f"   {_competition_emoji(match)} {comp} · 🕘 {time} · {status}{score_part}")
    lines.extend([
        _SEPARATOR,
        "🧠 SHARK solo publicará picks premium cuando haya cuota real, mercado claro y riesgo controlado.",
        "⚠️ Apuesta siempre con responsabilidad.",
    ])
    return _limit_message("\n".join(lines).strip(), 3600)


def build_single_pick_message(pick, premium_name="NeMeSiS SHARK PRO", title="🦈 PICK SHARK PREMIUM") -> str:
    if not is_telegram_football_item(pick or {}):
        return ""
    pick = enrich_pick_quality(_localize_pick_for_telegram(pick))
    selection = _selection_text(pick)
    odds = _odds_text(pick.get("odds"))
    if not selection:
        return ""
    lines = [
        f"<b>{safe_html(title)}</b>",
        f"<b>{safe_html(premium_name)}</b> · <i>Lectura profesional prepartido</i>",
        _SEPARATOR,
    ]
    lines.extend(_premium_pick_card(pick, detailed=True))
    match_url = _match_url_line(pick, "Abrir partido, cuotas y análisis SHARK")
    if match_url:
        lines.extend(["", _SOFT_SEPARATOR, match_url])
    lines.extend(["", _SOFT_SEPARATOR, _professional_footer()])
    return _limit_message("\n".join(line for line in lines if line is not None).strip(), 3900)


def build_daily_picks_message(picks, force_empty=False, premium_name="NeMeSiS SHARK PRO") -> str:
    clean = []
    for raw in picks or []:
        if not is_telegram_football_item(raw or {}):
            continue
        pick = enrich_pick_quality(_localize_pick_for_telegram(raw))
        if _selection_text(pick) and _market_text(pick):
            clean.append(pick)
    clean = sort_picks_by_quality(clean)
    if not clean:
        if not force_empty:
            return ""
        return "\n".join([
            "<b>🦈 SHARK PICKS PREMIUM</b>",
            f"<b>{safe_html(premium_name)}</b>",
            _SEPARATOR,
            "Ahora mismo no hay picks premium cerrados con cuota real, mercado claro y riesgo controlado.",
            "SHARK seguirá revisando calendario, cuotas y señales antes de publicar.",
            "⚠️ Mejor no enviar una apuesta débil que forzar una señal sin valor.",
        ])
    if len(clean) == 1:
        return build_single_pick_message(clean[0], premium_name=premium_name)
    top = clean[:3]
    lines = [
        "<b>🦈 PICKS SHARK PREMIUM</b>",
        f"<b>{safe_html(premium_name)}</b> · <i>Selección profesional del día</i>",
        _SEPARATOR,
        f"✅ <b>{len(top)} señales con cuota real y filtro SHARK</b>",
        "📍 Ordenadas por calidad, relevancia, riesgo y hora Madrid.",
        "",
    ]
    for index, pick in enumerate(top, start=1):
        lines.extend(_premium_pick_card(pick, index=index, detailed=False))
        if index != len(top):
            lines.append(_SOFT_SEPARATOR)
    lines.extend([
        _SEPARATOR,
        "🧠 SHARK publica menos, pero mejor: cuota real, mercado entendible y stake controlado.",
        _professional_footer(),
    ])
    return _limit_message("\n".join(lines).strip(), 3900)


def build_combi_message(picks, combi_type="media", premium_name="NeMeSiS SHARK PRO") -> str:
    clean = []
    seen = set()
    total_odds = 1.0
    for raw in picks or []:
        if not is_telegram_football_item(raw or {}):
            continue
        pick = enrich_pick_quality(_localize_pick_for_telegram(raw))
        selection = _selection_text(pick)
        odds = _clean_odds(pick.get("odds"))
        key = f"{_norm(_team_name(pick, 'home'))}:{_norm(_team_name(pick, 'away'))}:{pick.get('match_date') or ''}"
        if not selection or not odds or key in seen:
            continue
        seen.add(key)
        total_odds *= float(odds)
        clean.append((pick, selection, odds))
    if not clean:
        return ""
    legs = len(clean)
    if legs <= 4:
        label = "COMBI SEGURA SHARK"
        risk = "Controlado"
        stake = "1/10"
    elif legs <= 8:
        label = "COMBI MEDIA SHARK"
        risk = "Medio/Alto"
        stake = "0.5/10"
    else:
        label = "COMBI LARGA SHARK — ALTO RIESGO"
        risk = "Alto"
        stake = "0.25/10"
    lines = [
        f"<b>🦈 {label}</b>",
        _SEPARATOR,
        f"📌 <b>{legs} selecciones</b>",
        f"💰 <b>Cuota total aprox.:</b> {total_odds:.2f}",
        f"⚠️ <b>Riesgo:</b> {risk}",
        f"📌 <b>Stake recomendado:</b> {stake}",
        "",
    ]
    for idx, (pick, selection, odds) in enumerate(clean[:15], start=1):
        lines.append(f"{idx}. {safe_html(selection)} @ {safe_html(odds)}")
        lines.append(f"   {_match_title(pick)}")
    lines.extend([
        _SEPARATOR,
        "Nota SHARK: a más selecciones, más riesgo. No vendas una combi larga como segura.",
    ])
    return _limit_message("\n".join(lines).strip(), 3800)


def build_live_alert_message(match, event=None, internal_url="/live") -> str:
    if not is_telegram_football_item(match or {}):
        return ""
    match = apply_match_localization(match)
    event = event or {}
    score = _score_text(match) or "sin marcador"
    minute = safe_html((match.get("live_depth") or {}).get("minute") or match.get("minute") or "LIVE")
    detail = safe_html(compact_text(event.get("title") or event.get("detail") or "Seguimiento en directo", 150))
    url = safe_url(match.get("match_url") or internal_url)
    lines = [
        "<b>🔴 ALERTA LIVE SHARK</b>",
        _SEPARATOR,
        f"{_competition_emoji(match)} <b>{safe_html(_competition_name(match))}</b>",
        f"⏱️ <b>{minute}</b> · Marcador: <b>{safe_html(score)}</b>",
        f"<b>{_match_title(match)}</b>",
        f"🧠 {detail}",
    ]
    if url:
        lines.append(f'🔗 <a href="{url}">Abrir live en NeMeSiS</a>')
    return _limit_message("\n".join(lines).strip(), 3500)


def build_system_test_message(now_iso, premium_name="NeMeSiS SHARK PRO") -> str:
    madrid_time = format_telegram_match_time_madrid({"kickoff_iso": now_iso})
    return "\n".join([
        f"<b>🦈 {safe_html(premium_name)}</b>",
        "✅ Mensaje de prueba admin.",
        f"🕘 Hora Madrid: {safe_html(madrid_time.get('datetime_label') or now_iso)}",
        "Canal Telegram premium operativo si recibes este aviso.",
    ])


def queue_summary(rows) -> dict:
    counts = {QUEUE_PENDING: 0, QUEUE_SENDING: 0, QUEUE_SENT: 0, QUEUE_FAILED: 0, QUEUE_SKIPPED: 0}
    for row in rows or []:
        status = str(row.get("status") or "").lower()
        counts[status] = counts.get(status, 0) + 1
    return counts


def _limit_message(text: str, limit: int = 3900) -> str:
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 80].rstrip() + "\n\n… Mensaje recortado para Telegram. Abre la app para ver todo."
