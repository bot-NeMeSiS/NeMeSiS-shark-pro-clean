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


def telegram_dedupe_key(message_type, date_key, target_key="global") -> str:
    raw = f"{message_type}:{date_key}:{target_key}".lower()
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
    telegram_time = format_telegram_match_time_madrid(dict(item or {}))
    if telegram_time.get("datetime_label") and telegram_time.get("datetime_label") != "Hora pendiente":
        return telegram_time["datetime_label"]
    localized = normalize_kickoff_for_display(dict(item or {}))
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
    odds = _clean_odds(pick.get("odds"))
    confidence = pick.get("confidence") or pick.get("shark_score")
    if odds and confidence:
        return "Value positivo"
    return "Controlado"


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
    pick = enrich_pick_quality(apply_pick_localization(pick))
    selection = _selection_text(pick)
    odds = _clean_odds(pick.get("odds"))
    if not selection or not odds:
        return ""
    comp = safe_html(_competition_name(pick))
    date = safe_html(_display_datetime(pick))
    market = safe_html(_market_text(pick))
    risk = safe_html(_risk_text(pick))
    reason = compact_text(pick.get("reasoning") or pick.get("reason") or "SHARK detecta una señal positiva con los datos disponibles.", 210)
    warning = compact_text(pick.get("warning_reason") or pick.get("warning") or "Revisar alineaciones y no subir stake si la cuota baja demasiado.", 180)
    lines = [
        f"<b>{safe_html(title)}</b>",
        _SEPARATOR,
        f"{_competition_emoji(pick)} <b>{comp}</b>",
        f"🕘 <b>{date}</b>",
        "",
        f"<b>{_match_title(pick)}</b>",
        "",
        f"✅ <b>Pick:</b> {safe_html(selection)}",
        f"🎯 <b>Mercado:</b> {market}",
        f"💰 <b>Cuota:</b> {safe_html(odds)}",
        f"📌 <b>Stake:</b> {_stake_text(pick)}",
        f"📊 <b>Confianza SHARK:</b> {_pick_score(pick)}/100",
        f"🏅 <b>Calidad:</b> {safe_html(str(pick.get('quality_score') or _pick_score(pick)))}/100 · {safe_html(pick.get('quality_label') or 'Filtro SHARK')}",
        f"⚠️ <b>Riesgo:</b> {risk}",
        f"💎 <b>Value:</b> {_pick_value_label(pick)}",
        "",
        f"✅ <b>Motivo:</b> {safe_html(reason)}",
        f"🛡️ <b>Precaución:</b> {safe_html(warning)}",
        "",
        "Juego responsable: ningún pick garantiza resultado.",
    ]
    match_url = _match_url_line(pick, "Abrir partido y análisis SHARK")
    if match_url:
        lines.extend([_SOFT_SEPARATOR, match_url])
    return _limit_message("\n".join(line for line in lines if line is not None).strip(), 3800)


def build_daily_picks_message(picks, force_empty=False, premium_name="NeMeSiS SHARK PRO") -> str:
    clean = []
    for raw in picks or []:
        if not is_telegram_football_item(raw or {}):
            continue
        pick = enrich_pick_quality(apply_pick_localization(raw))
        if pick.get("premium_ready") and _selection_text(pick) and _clean_odds(pick.get("odds")):
            clean.append(pick)
    clean = sort_picks_by_quality(clean)
    if not clean:
        if not force_empty:
            return ""
        return "\n".join([
            "<b>🦈 SHARK PICKS</b>",
            _SEPARATOR,
            "Ahora mismo no hay picks premium cerrados con cuota real.",
            "SHARK seguirá revisando partidos, cuotas y riesgo antes de publicar.",
            "⚠️ Mejor no enviar una apuesta débil que forzar una señal sin valor.",
        ])
    if len(clean) == 1:
        return build_single_pick_message(clean[0], premium_name=premium_name)
    lines = [
        "<b>🦈 PICKS SHARK PREMIUM</b>",
        f"<b>{safe_html(premium_name)}</b>",
        _SEPARATOR,
        f"✅ <b>{len(clean[:3])} señales con cuota real</b>",
        "",
    ]
    for index, pick in enumerate(clean[:3], start=1):
        selection = _selection_text(pick)
        odds = _clean_odds(pick.get("odds"))
        lines.extend([
            f"<b>{index}. {_match_title(pick)}</b>",
            f"{_competition_emoji(pick)} {_competition_name(pick)} · 🕘 {_display_datetime(pick)}",
            f"✅ {safe_html(selection)} · 💰 {safe_html(odds)} · 📌 {_stake_text(pick)}",
            f"📊 Calidad {safe_html(str(pick.get('quality_score') or _pick_score(pick)))}/100 · {safe_html(pick.get('quality_label') or 'Filtro SHARK')} · ⚠️ Riesgo {_risk_text(pick)}",
            "",
        ])
    lines.extend([
        _SEPARATOR,
        "🛡️ Revisa alineaciones y mantén stake controlado.",
    ])
    return _limit_message("\n".join(lines).strip(), 3800)


def build_combi_message(picks, combi_type="media", premium_name="NeMeSiS SHARK PRO") -> str:
    clean = []
    seen = set()
    total_odds = 1.0
    for raw in picks or []:
        if not is_telegram_football_item(raw or {}):
            continue
        pick = enrich_pick_quality(apply_pick_localization(raw))
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
