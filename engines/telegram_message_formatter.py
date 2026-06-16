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
    lines = [
        "🦈 NeMeSiS SHARK PRO",
        "📅 Agenda TOP del día",
        madrid_date_label(),
        "",
        "Canal profesional: solo primeras ligas y campeonatos importantes.",
        "",
    ]
    if matches:
        for index, match in enumerate(matches, 1):
            lines.extend([
                f"{index}. ⚽ {match_title(match)}",
                f"   🏆 {competition_label(match)}",
                f"   🕘 {madrid_match_time_label(match)} · {status_label(match)}",
            ])
    else:
        lines.append("Sin partidos TOP publicados ahora mismo.")
    lines.extend([
        "",
        "SHARK no publica ligas raras ni partidos sin contexto suficiente.",
        "Picks solo con cuota real, mercado claro y riesgo controlado.",
        "",
        "Abrir app: Partidos · Picks · Directo",
    ])
    return "\n".join(lines).strip()

def format_midday_update_message(matches=None, picks_count=0):
    matches = list(matches or [])[:4]
    lines = ["🦈 SHARK PRO · Actualización", madrid_date_label(include_hour=True), ""]
    if matches:
        lines.append("Partidos TOP vigilados:")
        for match in matches:
            lines.append(f"• {match_title(match)} · {competition_label(match)} · {madrid_match_time_label(match)}")
    else:
        lines.append("Sin cambios relevantes en competiciones TOP.")
    lines.append(f"Picks premium activos: {int(picks_count or 0)}")
    lines.append("Abrir app: Partidos · Picks · Directo")
    return "\n".join(lines)

def format_live_alert_message(match=None):
    match = match or {}
    lines = [
        "🔴 LIVE SHARK · Partido TOP",
        "",
        f"🏆 {competition_label(match)}",
        f"⚽ {match_title(match)}",
        f"📊 {score_label(match)} · {status_label(match)}",
        "",
        f"Lectura real: {_pressure_line(match)}",
        "",
        "SHARK sigue el directo con datos reales. Si no hay tracking avanzado, no se simula.",
        "",
        "Abrir directo · Ver partido",
    ]
    return "\n".join(lines)

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
    lines = [
        "🦈 PICK SHARK PRO",
        "",
        f"🏆 {competition_label(pick)}",
        f"⚽ {match_title(pick)}",
        f"🕘 {madrid_match_time_label(pick)}",
        "",
        f"🎯 Qué apostar: {selection}",
        f"📌 Mercado: {market}",
        f"💰 Cuota real: {odds_label}",
        f"📏 Stake sugerido: {stake_label}",
        f"🧠 Confianza SHARK: {_confidence_label(confidence)}",
        f"⚠️ Riesgo: {risk}",
    ]
    if value not in (None, ""):
        lines.append(f"📈 Value: {value}")
    lines.extend([
        "",
        "✅ Por qué entra SHARK:",
        reason,
        "",
        "⚠️ Cuidado:",
        caution,
        "",
        "Abrir pick · Ver partido · Juego responsable",
    ])
    return "\n".join(lines)

def format_combi_message(combi=None):
    combi = combi or {}
    picks = combi.get("picks") or combi.get("legs") or []
    odds = combi.get("total_odds") or combi.get("odds") or "Pendiente"
    confidence = combi.get("confidence") or combi.get("shark_score") or "Pendiente"
    risk = _text(combi.get("risk_level") or combi.get("risk"), "Medio")
    reason = _text(combi.get("reason") or combi.get("main_reason"), "Combinada basada en picks válidos y partidos con datos suficientes.")
    lines = [
        "COMBI SHARK",
        "",
        _text(combi.get("title") or combi.get("name"), "Combinada premium"),
        f"Partidos: {len(picks) or combi.get('legs_count') or 'Pendiente'}",
        f"Cuota total: {odds}",
        f"Confianza SHARK: {_confidence_label(confidence)}",
        f"Riesgo: {risk}",
        "",
        "Lectura SHARK:",
        reason,
        "",
        "Ver combis - Ver picks",
    ]
    return "\n".join(lines)


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
    lines = [
        "RESULTADO FINAL SHARK",
        "",
        competition_label(match),
        f"{_text(match.get('home_team'), 'Local')} {score_label(match)} {_text(match.get('away_team'), 'Visitante')}",
        "",
        "Pick relacionado:",
        _text(pick.get("market") or pick.get("selection"), "Sin pick relacionado"),
        "",
        f"Estado: {pick_state}",
        "Track Record actualizado si el resultado está auditado.",
        "",
        "Ver histórico - Ver resumen si existe",
    ]
    return "\n".join(lines)


def format_highlight_message(match=None, highlight=None):
    match = match or {}
    highlight = highlight or {}
    lines = [
        "RESUMEN DISPONIBLE",
        "",
        competition_label(match or highlight),
        match_title(match or highlight),
        "Finalizado - Hora Madrid",
        "",
        "Ya puedes ver el resumen del partido.",
        "",
        "Ver resumen - Ver partido",
    ]
    return "\n".join(lines)


def format_prematch_message(match=None):
    match = match or {}
    lines = [
        "PARTIDO EN 60 MIN",
        "",
        competition_label(match),
        match_title(match),
        madrid_match_time_label(match),
        "",
        "SHARK está monitorizando este partido.",
        "",
        "Ver partido - Ver picks",
    ]
    return "\n".join(lines)


def format_evening_recap_message(summary=None):
    summary = summary or {}
    lines = [
        "CIERRE SHARK DEL DÍA",
        "",
        madrid_date_label(),
        "",
        "Resultados actualizados" if summary.get("results") else "Resultados pendientes",
        "Track Record revisado" if summary.get("track_record") else "Track Record sin nuevos cierres",
        "Resúmenes detectados" if summary.get("highlights") else "Sin resúmenes nuevos detectados",
        "Picks premium publicados si hubo valor real",
        "",
        "Mañana SHARK volverá a monitorizar la agenda.",
        "",
        "Ver histórico - Ver partidos",
    ]
    return "\n".join(lines)
