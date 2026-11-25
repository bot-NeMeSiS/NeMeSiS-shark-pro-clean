"""Premium Telegram message formatting for NeMeSiS SHARK PRO.

Visible timestamps are formatted for Europe/Madrid. The helpers keep messages
short, Spanish and free of raw technical labels.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from html.parser import HTMLParser
import math
import re
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo

from .madrid_time_engine import format_telegram_match_time_madrid
from .v935_launch_trust_engine import match_status_truth
from .content_rights_engine import classify_media_asset
from .ui_localization_engine import preferred_terms

TZ = ZoneInfo("Europe/Madrid")
MONTHS_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}
WEEKDAYS_ES = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


BRAND_HEADER = "🦈 NeMeSiS SHARK PRO"
MESSAGE_SEPARATOR = "━" * 18
MESSAGE_SOFT_SEPARATOR = "─" * 14
RESPONSIBLE_FOOTER = "Juego responsable: ningún análisis garantiza resultados."
TRANSPARENCY_FOOTER = "Fuente: NeMeSiS · Evidencia: datos disponibles. Limitaciones: lo no confirmado queda pendiente."


def first_value(item, *keys, default=None):
    """An observed zero is not a missing value."""
    return next((item[key] for key in keys if _text(item.get(key), "")), default)


def public_link(value):
    try:
        parsed = urlsplit(str(value or ""))
        path = unquote(parsed.path).lower()
        if (parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username
                or parsed.password or any(part in path for part in ("/admin", "/api/", "/founder"))):
            return ""
        return parsed.geturl()
    except ValueError:
        return ""


class _TelegramHTML(HTMLParser):
    """Escape text and close formatting even when the UTF-16 budget is exhausted."""
    def __init__(self, limit):
        super().__init__(convert_charrefs=True)
        self.remaining = max(0, limit - 1)
        self.parts, self.stack = [], []
        self.truncated = False

    def handle_starttag(self, tag, attrs):
        if self.truncated or tag not in {"b", "i", "u", "s", "code", "pre", "a"}:
            return
        if tag == "a":
            href = public_link(dict(attrs).get("href"))
            if not href:
                return
            self.parts.append(f'<a href="{escape(href, quote=True)}">')
        else:
            self.parts.append(f"<{tag}>")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack:
                closed = self.stack.pop()
                self.parts.append(f"</{closed}>")
                if closed == tag:
                    break

    def handle_data(self, data):
        if self.truncated:
            return
        accepted = []
        for char in data:
            units = 2 if ord(char) > 0xFFFF else 1
            if units > self.remaining:
                self.truncated = True
                break
            accepted.append(char)
            self.remaining -= units
        self.parts.append(escape("".join(accepted), quote=False))

    def result(self):
        return "".join(self.parts) + ("…" if self.truncated else "") + "".join(f"</{tag}>" for tag in reversed(self.stack))


def limit_telegram_html(text, limit=3900):
    parser = _TelegramHTML(limit)
    parser.feed(str(text or ""))
    parser.close()
    return parser.result()


def premium_text_html(text, limit=3900):
    headings = {"Partido", "Entrada", "Contexto SHARK", "Lectura SHARK", "Riesgo a vigilar", "Selecciones", "Resumen", "Estado", "Acción", "Resultado", "Partidos destacados", "Próximo paso", "Motivo", "Antes de decidir", "Selección publicada", "Datos del partido", "Qué ha cambiado", "Contenido de tu cuenta", "Ver ficha del partido:"}
    lines = []
    for index, line in enumerate(str(text or "").splitlines()):
        safe = escape(line, quote=False)
        lines.append(f"<b>{safe}</b>" if index in {0, 2} or line in headings else safe)
    return limit_telegram_html("\n".join(lines), limit)


def telegram_photo_caption(html_text):
    body = limit_telegram_html(html_text, 880)
    if "Juego responsable" not in body:
        body += "\n\n<i>Juego responsable. Sin garantías de resultado.</i>"
    return limit_telegram_html(body, 1024)


def pick_result_label(pick):
    return {"won": "✅ ACERTADO", "lost": "❌ FALLADO", "void": "➖ NULO", "pending": "⏳ PENDIENTE"}.get(str(first_value(pick, "result_status", "pick_result", default="")).lower(), "⏳ PENDIENTE")


def highlight_link(highlight):
    # A URL is not evidence of playback or redistribution rights.
    if highlight.get("blocked"):
        return ""
    url = public_link(first_value(highlight, "safe_url", "detail_url", "url", "source_url", "video_url", "highlight_url"))
    decision = classify_media_asset({**highlight, "url": url}, channel="TELEGRAM")
    return url if decision["can_display"] else ""


def _message_header(title, subtitle=""):
    lines = [_text(title, "Actualización"), BRAND_HEADER]
    if subtitle:
        lines.append(_text(subtitle))
    return lines


def _section(title, lines=None):
    clean = [str(line).strip() for line in (lines or []) if str(line or "").strip()]
    if not clean:
        return []
    return ["", title] + clean


def data_update_label(item):
    """Display only this match's canonical provider clock, never render time."""
    item = item or {}
    truth = match_status_truth(item)
    field = truth.get("live_timestamp_source")
    if field not in {"live_updated_at", "provider_updated_at", "last_synced_at"}:
        return "Actualización de datos: sin hora confirmada"
    raw = item.get(field)
    try:
        observed = raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if observed.tzinfo is None:
            return "Actualización de datos: sin hora confirmada"
        if observed > datetime.now(TZ):
            return "Actualización de datos: hora por confirmar"
        observed = observed.astimezone(TZ)
    except (ValueError, TypeError, OverflowError):
        return "Actualización de datos: sin hora confirmada"
    return f"Actualización de datos: {observed.strftime('%d/%m/%Y · %H:%M:%S')} Madrid (partido)"


def _message_match_context(item):
    return [f"⚽ {match_title(item)}", f"🏆 {competition_label(item)}",
            f"🕘 {madrid_match_time_label(item)}", f"Estado: {status_label(item)}",
            data_update_label(item)]


def _message_match_action(item):
    item = item or {}
    url = public_link(item.get("match_url") or item.get("detail_url"))
    if url:
        return ["", "Ver ficha del partido:", url]
    return ["", "Abre la ficha del partido en la aplicación."]


def _message_footer(*extra):
    lines = ["", MESSAGE_SOFT_SEPARATOR, TRANSPARENCY_FOOTER, RESPONSIBLE_FOOTER]
    lines.extend(str(item).strip() for item in extra if str(item or "").strip())
    return lines


def _join_message(lines, limit=3900):
    text = preferred_terms("\n".join(str(line) for line in lines if line is not None).strip(), "es")
    # Telegram measures visible text in UTF-16 units, including emoji pairs.
    budget = max(0, min(int(limit), 3900))
    if len(text.encode("utf-16-le", errors="replace")) // 2 <= budget:
        return text
    suffix = "\n\nMensaje abreviado. Consulta la ficha en la aplicación."
    suffix_units = len(suffix.encode("utf-16-le")) // 2
    if budget <= suffix_units:
        return text.encode("utf-16-le", errors="replace")[:max(0, budget - 1) * 2].decode("utf-16-le", errors="ignore") + ("…" if budget else "")
    units = budget - suffix_units
    return text.encode("utf-16-le", errors="replace")[:units * 2].decode("utf-16-le", errors="ignore").rstrip() + suffix


def _text(value, fallback="Pendiente"):
    if isinstance(value, (dict, list, tuple, set, bool)):
        return fallback
    value = re.sub(r"\s+", " ", str(value if value is not None else "")).strip()
    if not value or value.lower() in {"none", "null", "undefined", "nan", "n/a", "inf", "-inf"}:
        return fallback
    return value if len(value) <= 320 else value[:319].rstrip() + "…"


def _dt(value=None):
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value or "").strip()
        if not raw:
            return datetime.now(TZ)
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(TZ)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TZ)
    return parsed.astimezone(TZ)


def madrid_date_label(value=None, include_hour=False):
    current = _dt(value)
    label = f"{WEEKDAYS_ES[current.weekday()]} {current.day} de {MONTHS_ES[current.month]}"
    if include_hour:
        return f"{label} - {current.strftime('%H:%M')} Madrid"
    return f"{label} - Hora Madrid"


def madrid_match_time_label(item):
    item = dict(item or {})
    raw_kickoff = item.get("kickoff_time")
    if not item.get("kickoff_iso") and isinstance(raw_kickoff, str) and "T" in raw_kickoff:
        item["kickoff_iso"] = raw_kickoff
    info = format_telegram_match_time_madrid(item)
    if info.get("source_field") == "match_date":
        raw_date = item.get("match_date") or item.get("date")
        if isinstance(raw_date, datetime) or "T" in str(raw_date or ""):
            item["kickoff_iso"] = raw_date.isoformat() if isinstance(raw_date, datetime) else raw_date
            info = format_telegram_match_time_madrid(item)
        else:
            try:
                day = datetime.strptime(str(raw_date), "%Y-%m-%d").strftime("%d/%m/%Y")
                return f"{day} · hora pendiente (Madrid)"
            except (ValueError, TypeError):
                return "Hora pendiente"
    parsed = datetime.fromisoformat(info["iso_madrid"]) if info.get("iso_madrid") else None
    if not parsed:
        return "Hora pendiente"
    today = datetime.now(TZ).date()
    if parsed.date() == today:
        prefix = "Hoy"
    elif (parsed.date() - today).days == 1:
        prefix = "Mañana"
    else:
        prefix = f"{WEEKDAYS_ES[parsed.weekday()]} {parsed.day}/{parsed.month:02d}"
    return f"{prefix} - {parsed.strftime('%H:%M')} Madrid"


def match_title(item):
    item = item or {}
    home = _text(item.get("home_team") or item.get("home"), "Local")
    away = _text(item.get("away_team") or item.get("away"), "Visitante")
    return f"{home} vs {away}"


def competition_label(item):
    item = item or {}
    return _text(item.get("competition_name") or item.get("league_name") or item.get("competition"), "Competición")


def score_label(item):
    item = item or {}
    score = str(first_value(item, "score", "final_score", "result", default="")).strip()
    if re.fullmatch(r"\d{1,2}\s*[-:–]\s*\d{1,2}", score):
        return re.sub(r"\s*[-:–]\s*", "–", score)
    home_score, away_score = item.get("home_score"), item.get("away_score")
    if all(re.fullmatch(r"\d{1,2}", str(value)) for value in (home_score, away_score)):
        return f"{home_score}–{away_score}"
    return "Marcador pendiente"


def status_label(item):
    truth = match_status_truth(item or {})
    return {"FINISHED": "Finalizado", "ARCHIVED": "Finalizado", "LIVE": "En directo", "HALFTIME": "Descanso", "UPCOMING": "Próximo", "POSTPONED": "Aplazado", "SUSPENDED": "Suspendido", "CANCELLED": "Cancelado", "ABANDONED": "Abandonado", "STALE": "Actualización pendiente", "RESULT_PENDING": "Resultado pendiente"}.get(truth["lifecycle"], "Estado por confirmar")


def _clean_metric(value, suffix=""):
    text = _text(value, "Sin dato")
    return f"{text}{suffix}" if suffix and not text.endswith(suffix) else text


def _pressure_line(item):
    item = item or {}
    possession = first_value(item, "possession", "ball_possession")
    shots = first_value(item, "shots_on_goal", "shots_on_target")
    corners = first_value(item, "corners", "corner_kicks")
    attacks = first_value(item, "dangerous_attacks", "attacks")
    bits = []
    if possession not in (None, ""):
        bits.append(f"posesión {_clean_metric(possession, '%') if str(possession).isdigit() else _text(possession)}")
    if shots not in (None, ""):
        bits.append(f"tiros a puerta {_clean_metric(shots)}")
    if corners not in (None, ""):
        bits.append(f"córners {_clean_metric(corners)}")
    if attacks not in (None, ""):
        bits.append(f"ataques {_clean_metric(attacks)}")
    return " · ".join(bits) if bits else "Estadísticas detalladas: sin datos confirmados."


def _confidence_label(value):
    text = _text(value)
    return f"{text}/100" if text.isdigit() else text


def format_daily_summary_message(matches=None, focus="Partidos destacados"):
    matches = list(matches or [])[:5]
    lines = _message_header("📅 Agenda de fútbol", madrid_date_label())
    if matches:
        lines.append(f"Partidos en este resumen: {len(matches)}")
        for index, match in enumerate(matches, 1):
            lines.extend(_section(f"{index}. {match_title(match)}", [
                competition_label(match), madrid_match_time_label(match),
                f"Estado: {status_label(match)}", data_update_label(match)]))
            lines.extend(_message_match_action(match))
    else:
        lines.extend(_section("Agenda", ["No hay partidos confirmados para este resumen."]))
    lines.extend(_message_footer("Los pronósticos se consultan por separado, según tu cuenta y los requisitos de edad."))
    return _join_message(lines, 3600)


def format_midday_update_message(matches=None, picks_count=0):
    matches = list(matches or [])[:4]
    lines = _message_header("📡 Actualización SHARK", madrid_date_label(include_hour=True))
    if matches:
        lines.extend(_section("Partidos vigilados", [
            f"• {match_title(match)} · {competition_label(match)} · {madrid_match_time_label(match)}"
            for match in matches
        ]))
    else:
        lines.extend(_section("Partidos vigilados", ["Sin cambios relevantes en competiciones principales."]))
    lines.extend(_section("Picks", [f"Picks premium activos: {int(picks_count or 0)}"]))
    lines.extend(_message_footer("Abrir app: Partidos · Picks · Directo"))
    return _join_message(lines, 3200)


def format_live_alert_message(match=None):
    match = match or {}
    truth = match_status_truth(match)
    live = truth["is_live"]
    lines = _message_header("🔴 EN DIRECTO" if live else "📊 Última información del partido")
    lines.extend(_section("Partido", _message_match_context(match)))
    if live:
        lines.append(f"Marcador actual: {score_label(match)}")
    elif truth.get("is_finished"):
        lines.append(f"Resultado registrado: {score_label(match)}")
    else:
        lines.append("Marcador: no confirmado")
    minute = first_value(match, "minute", "elapsed")
    if live and minute is not None:
        lines.append(f"Minuto: {_text(minute)}")
    event = first_value(match, "live_alert", "event_title")
    if live and event:
        lines.extend(_section("Qué ha cambiado", [_text(event)]))
    if live:
        lines.extend(_section("Datos del partido", [_pressure_line(match)]))
    else:
        lines.append("Esta lectura no confirma un directo vigente.")
    lines.extend(_message_match_action(match))
    lines.extend(_message_footer())
    return _join_message(lines, 3200)


def format_pick_message(pick=None):
    pick = pick or {}
    market = _text(first_value(pick, "market", "pick_type"), "No publicado")
    selection = _text(first_value(pick, "selection", "recommendation"), "No publicada")
    confidence = first_value(pick, "confidence", "shark_score", default="No publicada")
    stake = first_value(pick, "stake_units", "stake", default="No publicado")
    risk = _text(first_value(pick, "risk_level", "risk"), "No publicado")
    reason = _text(first_value(pick, "reasoning", "reason", "main_reason"), "No hay un motivo publicado para esta selección.")
    caution = _text(first_value(pick, "caution", "warning", "precaution", "warning_reason", "risk_note"),
                    "La cuota registrada puede cambiar. Revisa las condiciones actuales antes de decidir.")
    plan = str(pick.get("membership") or "").upper()
    title = "🎯 Pronóstico SHARK" + (f" · {plan}" if plan in {"PRO", "ELITE", "ELITE+"} else "")
    lines = _message_header(title, "Información de pronósticos · Sólo +18")
    lines.extend(_section("Partido", _message_match_context(pick)))
    odds = _v889_odds_label(pick.get("odds"))
    stake_label = "No publicado" if stake == "No publicado" else f"{_text(stake)} uds"
    entry = [f"Selección: {selection}", f"Mercado: {market}",
             f"Cuota registrada: {odds}" if odds != "Cuota pendiente" else "Cuota: no publicada",
             f"Importe orientativo: {stake_label}",
             f"Valoración SHARK: {_confidence_label(confidence)}", f"Riesgo: {risk}"]
    bookmaker = first_value(pick, "bookmaker", "bookmaker_name")
    if bookmaker:
        entry.append(f"Casa: {_text(bookmaker)}")
    value = first_value(pick, "value", "value_score", "edge", default="")
    if value not in (None, ""):
        entry.append(f"Valoración adicional: {_text(value)}")
    lines.extend(_section("Selección publicada", entry))
    lines.extend(_section("Motivo", [reason]))
    lines.extend(_section("Antes de decidir", [caution]))
    lines.extend(_message_match_action(pick))
    lines.extend(_message_footer("La valoración SHARK no es una garantía ni una probabilidad de acierto."))
    return _join_message(lines, 3600)


def _v889_odds_label(value):
    try:
        odds = float(str(value).replace(",", "."))
    except Exception:
        return "Cuota pendiente"
    if not math.isfinite(odds) or odds <= 1.01:
        return "Cuota pendiente"
    return f"{odds:.2f}".rstrip("0").rstrip(".")


def _v889_value(value, fallback="Pendiente"):
    return _text(value, fallback)


def format_premium_pick_message(pick=None, quality=None, membership="PRO"):
    """All plan variants reuse the same canonical full-pick presentation."""
    pick, quality = pick or {}, quality or {}
    normalized = quality.get("pick") or {}
    source = {**pick, **normalized, "membership": membership}
    return format_pick_message(source)


def format_membership_pick_message(pick=None, quality=None, membership="PRO"):
    membership = str(membership or "PRO").upper()
    if membership == "FREE":
        pick, quality = pick or {}, quality or {}
        normalized = quality.get("pick") or pick
        lines = _message_header("🔎 Vista gratuita", "Detalle según los permisos de tu cuenta")
        lines.extend(_section("Partido", _message_match_context(normalized)))
        lines.extend(_section("Lectura disponible", [_v889_value(normalized.get("selection") or pick.get("selection"), "Lectura pendiente")]))
        lines.extend(_section("Antes de decidir", [
            _text(first_value(pick, "risk_level", "risk"), "Riesgo no publicado"),
            _text(first_value(pick, "caution", "warning", "risk_note"), "Revisa los datos y las condiciones en la aplicación.")]))
        lines.extend(_message_match_action(normalized))
        lines.extend(_message_footer("El detalle completo requiere el plan correspondiente y los requisitos de edad (+18)."))
        return _join_message(lines, 2600)
    return format_premium_pick_message(pick, quality=quality, membership=membership)


def format_premium_combi_message(picks=None, quality=None, membership="ELITE"):
    picks = list(picks or [])[:3]
    quality = quality or {}
    lines = _message_header(f"🧩 Combi Premium {str(membership or 'ELITE').upper()}", "Solo si todas las selecciones tienen datos suficientes")
    lines.extend(_section("Estado", [
        f"Estado: {quality.get('status') or 'Combi en revisión'}",
        f"Riesgo: {quality.get('risk') or 'No especificado'}",
        f"Stake: {_text(first_value(quality, 'stake'))}",
    ]))
    if not picks:
        lines.extend(_section("Selecciones", ["Combi no enviada por datos insuficientes."]))
    else:
        lines.extend(_section("Selecciones", [
            f"{index}. {match_title(pick)} · {_v889_value(pick.get('selection') or pick.get('recommendation'), 'Selección pendiente')} · {_v889_odds_label(pick.get('odds'))}"
            for index, pick in enumerate(picks, 1)
        ]))
    lines.extend(_message_footer("No combinar picks sin cuota real ni selección confirmada."))
    return _join_message(lines, 3600)


def format_pick_result_tracking_message(pick=None, match=None):
    pick = pick or {}
    match = match or {}
    result = _v889_value(match.get("pick_result") or match.get("result_status"), "Resultado pendiente")
    score = _v889_value(match.get("score") or match.get("final_score"), "Marcador pendiente")
    lines = _message_header("📊 Seguimiento de pick", "Resultado auditado solo con datos reales")
    lines.extend(_section("Partido", [match_title({**pick, **match})]))
    lines.extend(_section("Resultado", [
        f"Estado: {result}",
        f"Marcador real: {score}",
        f"Cuota: {_v889_odds_label(pick.get('odds'))}",
    ]))
    lines.extend(_message_footer("Sin dato real de cierre, el pick queda pendiente."))
    return _join_message(lines, 2800)


def format_combi_message(combi=None):
    combi = combi or {}
    picks = combi.get("picks") or combi.get("legs") or []
    odds = combi.get("total_odds") or combi.get("odds") or "Pendiente"
    confidence = combi.get("confidence") or combi.get("shark_score") or "Pendiente"
    risk = _text(combi.get("risk_level") or combi.get("risk"), "No especificado")
    reason = _text(combi.get("reason") or combi.get("main_reason"), "Análisis no publicado. Cada selección añade riesgo; no hay garantías de resultado.")
    lines = _message_header("🧩 COMBI SHARK", _text(combi.get("title") or combi.get("name"), "Combinada premium"))
    lines.extend(_section("Resumen", [
        f"Partidos: {len(picks) or combi.get('legs_count') or 'Pendiente'}",
        f"💸 Cuota total registrada: {_v889_odds_label(odds)}",
        f"Stake: {_text(first_value(combi, 'stake_units', 'stake'))}",
        f"Confianza SHARK: {_confidence_label(confidence)}",
        f"Riesgo: {risk}",
    ]))
    for index, leg in enumerate(picks[:8], 1):
        lines.extend(_section(f"{index}. {match_title(leg)}", [
            f"🏆 {competition_label(leg)} · {madrid_match_time_label(leg)}",
            f"🎯 {_text(leg.get('selection') or leg.get('recommendation'))}",
            f"{_text(leg.get('market'), 'Mercado pendiente')} · Cuota: {_v889_odds_label(leg.get('odds'))}",
        ]))
    if len(picks) > 8:
        lines.append(f"{len(picks) - 8} selecciones más en la plataforma.")
    lines.extend(_section("Lectura SHARK", [reason]))
    lines.extend(_message_footer("Ver combis · Ver picks"))
    return _join_message(lines, 3200)


def format_result_message(match=None, pick=None):
    match = match or {}
    pick = pick or {}
    pick_state = pick_result_label(pick)
    lines = _message_header("🏁 Resultado SHARK", status_label(match))
    lines.extend(_section("Partido", [
        f"🏆 {competition_label(match)}",
        f"{_text(match.get('home_team'), 'Local')} {score_label(match)} {_text(match.get('away_team'), 'Visitante')}",
        f"🕒 {madrid_match_time_label(match)}",
    ]))
    lines.extend(_section("Pick relacionado", [_text(pick.get("selection"), "Sin selección publicada"), _text(pick.get("market"), "Mercado pendiente"), f"Cuota histórica: {_v889_odds_label(pick.get('odds'))}"]))
    lines.extend(_section("Estado", [pick_state, "La liquidación del pick es independiente del estado del partido."]))
    if pick.get("track_record_updated") is True:
        lines.append("Track Record actualizado.")
    lines.extend(_message_footer("Ver histórico · Ver resumen si existe"))
    return _join_message(lines, 3000)


def format_highlight_message(match=None, highlight=None):
    match, highlight = match or {}, highlight or {}
    link = highlight_link(highlight)
    lines = _message_header("🎥 Resumen del partido", "Enlace habilitado" if link else "Resumen pendiente")
    lines.extend(_section("Partido", _message_match_context(match or highlight)))
    if link:
        lines.extend(_section("Ver en la fuente autorizada", [link,
            "La disponibilidad depende de la fuente y de sus permisos."]))
        if highlight.get("attribution"):
            lines.append(f"Atribución: {_text(highlight['attribution'])}")
    else:
        lines.append("No hay un enlace de resumen habilitado para este partido.")
    lines.extend(_message_match_action(match))
    lines.extend(_message_footer())
    return _join_message(lines, 2600)


def format_prematch_message(match=None):
    match = match or {}
    lines = _message_header("🕘 Recordatorio del partido")
    lines.extend(_section("Partido", _message_match_context(match)))
    lines.append("Comprueba la hora, el estado y los datos disponibles en la ficha.")
    lines.extend(_message_match_action(match))
    lines.extend(_message_footer())
    return _join_message(lines, 2600)


def format_evening_recap_message(summary=None):
    summary = summary or {}
    lines = _message_header("🌙 Cierre SHARK del día", madrid_date_label())
    counts = []
    for key, label in (("results", "Resultados"), ("track_record", "Cierres Track Record"), ("highlights", "Resúmenes"), ("picks", "Picks publicados")):
        value = summary.get(key)
        detail = ("Confirmado" if value else "Sin novedades confirmadas") if isinstance(value, bool) else _text(value, "Sin dato confirmado")
        counts.append(f"{label}: {detail}")
    lines.extend(_section("Estado", counts))
    lines.extend(_section("Próximo paso", ["Consulta la próxima agenda en Calendario."]))
    lines.extend(_message_footer("Ver histórico · Ver partidos"))
    return _join_message(lines, 3000)


def format_system_message(message, title="Cuenta y Telegram"):
    return _join_message([
        *_message_header(f"🦈 {title}"), "", _text(message, "Consulta el estado de tu cuenta en la plataforma."),
        "", MESSAGE_SOFT_SEPARATOR,
        "🔒 No compartas contraseñas ni códigos de vinculación.",
        "Abrir plataforma · Telegram",
    ], 2000)
