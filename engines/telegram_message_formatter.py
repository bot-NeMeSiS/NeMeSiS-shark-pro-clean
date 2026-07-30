"""Premium Telegram message formatting for NeMeSiS SHARK PRO.

Visible timestamps are formatted for Europe/Madrid. The helpers keep messages
short, Spanish and free of raw technical labels.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

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
RESPONSIBLE_FOOTER = "Juego responsable: una lectura no garantiza resultados. Stake orientativo."
TRANSPARENCY_FOOTER = "Fuente: NeMeSiS · Evidencia: datos reales disponibles · Calidad: según cobertura · Frescura: Hora Madrid · Limitaciones: lo no confirmado no se simula."


def _message_header(title, subtitle=""):
    lines = [BRAND_HEADER, MESSAGE_SEPARATOR, _text(title, "Actualización")]
    if subtitle:
        lines.append(_text(subtitle))
    return lines


def _section(title, lines=None):
    clean = [str(line).strip() for line in (lines or []) if str(line or "").strip()]
    if not clean:
        return []
    return ["", title] + clean


def _message_footer(*extra):
    lines = ["", MESSAGE_SOFT_SEPARATOR, TRANSPARENCY_FOOTER, RESPONSIBLE_FOOTER]
    lines.extend(str(item).strip() for item in extra if str(item or "").strip())
    return lines


def _join_message(lines, limit=3900):
    text = "\n".join(str(line) for line in lines if line is not None).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 82].rstrip() + "\n\nMensaje recortado para Telegram. Abre la app para ver todo."


def _text(value, fallback="Pendiente"):
    value = str(value or "").strip()
    return value if value else fallback


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
    item = item or {}
    raw = (
        item.get("kickoff_iso")
        or item.get("kickoff_time")
        or item.get("match_time")
        or item.get("date_time")
        or item.get("commence_time")
        or ""
    )
    parsed = _dt(raw) if raw else None
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
    score = str(item.get("score") or item.get("result") or "").strip()
    if score:
        return score
    home_score = item.get("home_score")
    away_score = item.get("away_score")
    if home_score not in (None, "") and away_score not in (None, ""):
        return f"{home_score}-{away_score}"
    return "Marcador pendiente"


def status_label(item):
    raw = str((item or {}).get("status") or (item or {}).get("state") or "").strip().lower()
    if raw in {"ft", "final", "finished", "finalizado"}:
        return "Finalizado"
    if raw in {"live", "inplay", "en directo", "directo"}:
        return "En directo"
    if raw in {"ht", "descanso"}:
        return "Descanso"
    if raw in {"upcoming", "scheduled", "not started", "proximo", "próximo"}:
        return "Próximo"
    return _text((item or {}).get("status") or (item or {}).get("state"), "Próximo")


def _clean_metric(value, suffix=""):
    if value in (None, "", "None"):
        return "—"
    text = str(value).strip()
    return f"{text}{suffix}" if suffix and not text.endswith(suffix) else text


def _pressure_line(item):
    item = item or {}
    possession = item.get("possession") or item.get("ball_possession")
    shots = item.get("shots_on_goal") or item.get("shots_on_target")
    corners = item.get("corners") or item.get("corner_kicks")
    attacks = item.get("dangerous_attacks") or item.get("attacks")
    bits = []
    if possession not in (None, ""):
        bits.append(f"posesión {_clean_metric(possession, '%') if str(possession).isdigit() else possession}")
    if shots not in (None, ""):
        bits.append(f"tiros a puerta {_clean_metric(shots)}")
    if corners not in (None, ""):
        bits.append(f"córners {_clean_metric(corners)}")
    if attacks not in (None, ""):
        bits.append(f"ataques {_clean_metric(attacks)}")
    return " · ".join(bits) if bits else "Live básico: sin estadísticas avanzadas del proveedor todavía"


def _confidence_label(value):
    if value in (None, ""):
        return "Pendiente"
    text = str(value)
    return f"{text}/100" if text.isdigit() else text


def format_daily_summary_message(matches=None, focus="Agenda TOP"):
    matches = list(matches or [])[:5]
    lines = _message_header("📅 Agenda premium", f"{_text(focus, 'Agenda deportiva')} · {madrid_date_label()}")
    if matches:
        match_lines = []
        for index, match in enumerate(matches, 1):
            match_lines.extend([
                f"{index}. ⚽ {match_title(match)}",
                f"   🏆 {competition_label(match)}",
                f"   🕘 {madrid_match_time_label(match)} · {status_label(match)}",
            ])
        lines.extend(_section("Partidos destacados", match_lines))
    else:
        lines.extend(_section("Partidos destacados", ["Sin partidos destacados publicados ahora mismo."]))
    lines.extend(_section("Criterio SHARK", [
        "Solo agenda con competiciones relevantes y contexto suficiente.",
        "Los picks se publican únicamente con cuota real, mercado claro y riesgo controlado.",
    ]))
    lines.extend(_message_footer("Abrir app: Partidos · Picks · Directo"))
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
    lines = _message_header("🔴 ALERTA LIVE SHARK", "Seguimiento con datos reales disponibles")
    lines.extend(_section("Partido", [
        f"🏆 {competition_label(match)}",
        f"⚽ {match_title(match)}",
        f"📊 {score_label(match)} · {status_label(match)}",
    ]))
    lines.extend(_section("Lectura real", [_pressure_line(match)]))
    lines.extend(_section("Limitación", ["Si el proveedor no ofrece tracking avanzado, NeMeSiS no lo simula."]))
    lines.extend(_message_footer("Abrir directo · Ver partido"))
    return _join_message(lines, 3200)


def format_pick_message(pick=None):
    pick = pick or {}
    market = _text(pick.get("market") or pick.get("pick_type"), "Mercado pendiente")
    selection = _text(pick.get("selection") or pick.get("recommendation"), "Selección pendiente")
    odds = pick.get("odds")
    confidence = pick.get("confidence") or pick.get("shark_score") or pick.get("score") or "Pendiente"
    risk = _text(pick.get("risk_level") or pick.get("risk"), "Medio")
    stake = pick.get("stake_units") or pick.get("stake") or "Pendiente"
    value = pick.get("value") or pick.get("value_score") or pick.get("edge") or ""
    reason = _text(pick.get("reasoning") or pick.get("reason") or pick.get("main_reason"), "Lectura SHARK pendiente de contexto suficiente.")
    caution = _text(pick.get("caution") or pick.get("warning") or pick.get("precaution") or pick.get("warning_reason"), "No aumentar stake si cambia la cuota o falta confirmación de alineaciones.")
    odds_label = odds if odds not in (None, "", 0, 0.0) else "No disponible"
    stake_label = f"{stake} uds" if str(stake) != "Pendiente" else "Pendiente"
    lines = _message_header("🎯 PICK PREMIUM SHARK", "Lectura prepartido · datos reales")
    lines.extend(_section("Partido", [
        f"🏆 {competition_label(pick)}",
        f"⚽ {match_title(pick)}",
        f"🕘 {madrid_match_time_label(pick)}",
    ]))
    bet_lines = [
        f"Selección: {selection}",
        f"Mercado: {market}",
        f"Cuota: {odds_label}",
        f"Stake sugerido: {stake_label}",
        f"Confianza SHARK: {_confidence_label(confidence)}",
        f"Riesgo: {risk}",
    ]
    if value not in (None, ""):
        bet_lines.append(f"Value: {value}")
    lines.extend(_section("Entrada", bet_lines))
    lines.extend(_section("Contexto SHARK", [reason]))
    lines.extend(_section("Riesgo a vigilar", [caution]))
    lines.extend(_message_footer("Abrir pick · Ver partido"))
    return _join_message(lines, 3600)


def _v889_odds_label(value):
    try:
        odds = float(str(value).replace(",", "."))
    except Exception:
        return "Cuota pendiente"
    if odds <= 1.01:
        return "Cuota pendiente"
    return f"{odds:.2f}".rstrip("0").rstrip(".")


def _v889_value(value, fallback="Pendiente"):
    text = str(value or "").strip()
    if not text or text.lower() in {"none", "null", "undefined", "nan"}:
        return fallback
    return text


def format_premium_pick_message(pick=None, quality=None, membership="PRO"):
    """V889 premium pick message: real data only, no filler."""
    pick = pick or {}
    quality = quality or {}
    normalized = quality.get("pick") or pick
    membership = str(membership or "PRO").upper()
    home = _v889_value(normalized.get("home_team") or pick.get("home_team") or pick.get("home"), "Equipo local")
    away = _v889_value(normalized.get("away_team") or pick.get("away_team") or pick.get("away"), "Equipo visitante")
    competition = _v889_value(normalized.get("competition") or competition_label(pick), "Competición pendiente")
    market = _v889_value(normalized.get("market") or pick.get("market"), "Mercado pendiente")
    selection = _v889_value(normalized.get("selection") or pick.get("selection") or pick.get("recommendation"), "Selección pendiente")
    odds = _v889_odds_label(normalized.get("odds") or pick.get("odds"))
    bookmaker = _v889_value(normalized.get("bookmaker") or pick.get("bookmaker"), "")
    stake = _v889_value(normalized.get("stake") or pick.get("stake_units") or pick.get("stake"), "Stake pendiente")
    risk = _v889_value(normalized.get("risk") or pick.get("risk_level") or pick.get("risk"), "Riesgo pendiente")
    confidence = _v889_value(normalized.get("confidence") or pick.get("confidence") or pick.get("shark_score"), "Confianza pendiente")
    reason = _v889_value(normalized.get("reason") or pick.get("reason") or pick.get("reasoning"), "Motivo pendiente por datos reales insuficientes.")
    counter = _v889_value(normalized.get("counterargument") or pick.get("caution") or pick.get("warning"), "Riesgo pendiente de confirmación.")
    time_label = madrid_match_time_label({**pick, "kickoff_iso": normalized.get("kickoff_iso") or pick.get("kickoff_iso") or pick.get("kickoff_time")})
    status = "En revisión" if not quality.get("sendable") else "Prepartido"
    lines = _message_header(f"🎯 Pick Premium {membership}", "Lectura SHARK con cuota y riesgo visibles")
    lines.extend(_section("Partido", [
        f"⚽ {home} vs {away}",
        f"🏆 {competition}",
        f"🕘 {time_label}",
    ]))
    lines.extend(_section("Entrada", [
        f"Mercado: {market}",
        f"Selección: {selection}",
        f"Cuota: {odds}" + (f" · {bookmaker}" if bookmaker else ""),
        f"Stake recomendado: {stake}",
        f"Riesgo: {risk}",
        f"Confianza: {confidence}",
    ]))
    lines.extend(_section("Contexto SHARK", [reason]))
    lines.extend(_section("Riesgo a vigilar", [counter]))
    lines.extend(_section("Gestión", ["No sobreexponerse. Validar que la cuota no haya caído demasiado antes de entrar.", f"Estado: {status}"]))
    lines.extend(_message_footer("Abrir app: Ver partido · Picks · SHARK"))
    return _join_message(lines, 3900)


def format_membership_pick_message(pick=None, quality=None, membership="PRO"):
    membership = str(membership or "PRO").upper()
    if membership == "FREE":
        pick = pick or {}
        quality = quality or {}
        normalized = quality.get("pick") or pick
        home = _v889_value(normalized.get("home_team") or pick.get("home_team"), "Equipo local")
        away = _v889_value(normalized.get("away_team") or pick.get("away_team"), "Equipo visitante")
        selection = _v889_value(normalized.get("selection") or pick.get("selection"), "Lectura pendiente")
        lines = _message_header("🔎 Preview FREE", "Valor detectado sin revelar el análisis premium completo")
        lines.extend(_section("Partido", [f"⚽ {home} vs {away}"]))
        lines.extend(_section("Lectura disponible", [selection]))
        lines.extend(_message_footer("Stake, motivo completo y lectura SHARK avanzada disponibles en PRO.", "Abrir app: mejorar plan"))
        return _join_message(lines, 2600)
    return format_premium_pick_message(pick, quality=quality, membership=membership)


def format_premium_combi_message(picks=None, quality=None, membership="ELITE"):
    picks = list(picks or [])[:3]
    quality = quality or {}
    lines = _message_header(f"🧩 Combi Premium {str(membership or 'ELITE').upper()}", "Solo si todas las selecciones tienen datos suficientes")
    lines.extend(_section("Estado", [
        f"Estado: {quality.get('status') or 'Combi en revisión'}",
        f"Riesgo: {quality.get('risk') or 'Alto'}",
        f"Stake: {quality.get('stake') or 'Bajo'}",
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
    risk = _text(combi.get("risk_level") or combi.get("risk"), "Medio")
    reason = _text(combi.get("reason") or combi.get("main_reason"), "Combinada basada en picks válidos y partidos con datos suficientes.")
    lines = _message_header("🧩 COMBI SHARK", _text(combi.get("title") or combi.get("name"), "Combinada premium"))
    lines.extend(_section("Resumen", [
        f"Partidos: {len(picks) or combi.get('legs_count') or 'Pendiente'}",
        f"Cuota total: {odds}",
        f"Confianza SHARK: {_confidence_label(confidence)}",
        f"Riesgo: {risk}",
    ]))
    lines.extend(_section("Lectura SHARK", [reason]))
    lines.extend(_message_footer("Ver combis · Ver picks"))
    return _join_message(lines, 3200)


def format_result_message(match=None, pick=None):
    match = match or {}
    pick = pick or {}
    result_status = str(pick.get("result_status") or "").lower()
    if result_status == "won":
        pick_state = "Ganado"
    elif result_status == "lost":
        pick_state = "Perdido"
    elif result_status == "void":
        pick_state = "Void"
    else:
        pick_state = "Pendiente de auditoría"
    lines = _message_header("🏁 Resultado final SHARK", "Cierre solo con marcador real disponible")
    lines.extend(_section("Partido", [
        f"🏆 {competition_label(match)}",
        f"{_text(match.get('home_team'), 'Local')} {score_label(match)} {_text(match.get('away_team'), 'Visitante')}",
    ]))
    lines.extend(_section("Pick relacionado", [_text(pick.get("market") or pick.get("selection"), "Sin pick relacionado")]))
    lines.extend(_section("Estado", [f"Resultado: {pick_state}", "Track Record actualizado si el resultado está auditado."]))
    lines.extend(_message_footer("Ver histórico · Ver resumen si existe"))
    return _join_message(lines, 3000)


def format_highlight_message(match=None, highlight=None):
    match = match or {}
    highlight = highlight or {}
    lines = _message_header("🎬 Resumen disponible", "Partido finalizado · contenido listo si existe fuente")
    lines.extend(_section("Partido", [
        f"🏆 {competition_label(match or highlight)}",
        f"⚽ {match_title(match or highlight)}",
        "Estado: Finalizado · Hora Madrid",
    ]))
    lines.extend(_section("Acción", ["Ya puedes ver el resumen del partido."]))
    lines.extend(_message_footer("Ver resumen · Ver partido"))
    return _join_message(lines, 2600)


def format_prematch_message(match=None):
    match = match or {}
    lines = _message_header("⏳ Partido en 60 min", "Preparación prepartido")
    lines.extend(_section("Partido", [
        f"🏆 {competition_label(match)}",
        f"⚽ {match_title(match)}",
        f"🕘 {madrid_match_time_label(match)}",
    ]))
    lines.extend(_section("SHARK", ["SHARK está monitorizando este partido con los datos disponibles."]))
    lines.extend(_message_footer("Ver partido · Ver picks"))
    return _join_message(lines, 2600)


def format_evening_recap_message(summary=None):
    summary = summary or {}
    lines = _message_header("🌙 Cierre SHARK del día", madrid_date_label())
    lines.extend(_section("Estado", [
        "Resultados actualizados" if summary.get("results") else "Resultados pendientes",
        "Track Record revisado" if summary.get("track_record") else "Track Record sin nuevos cierres",
        "Resúmenes detectados" if summary.get("highlights") else "Sin resúmenes nuevos detectados",
        "Picks premium publicados si hubo valor real",
    ]))
    lines.extend(_section("Próximo paso", ["Mañana SHARK volverá a monitorizar la agenda."]))
    lines.extend(_message_footer("Ver histórico · Ver partidos"))
    return _join_message(lines, 3000)
