"""Premium Telegram message formatting for NeMeSiS SHARK PRO.

All visible timestamps are formatted in Europe/Madrid and the helpers avoid
raw UTC, duplicated "Madrid" labels and placeholder-style technical text.
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
    2: "Miercoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sabado",
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
    label = f"{WEEKDAYS_ES[current.weekday()]} {current.day} {MONTHS_ES[current.month]}"
    if include_hour:
        return f"{label} · {current.strftime('%H:%M')} Madrid"
    return f"{label} · Hora Madrid"


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
        prefix = "Manana"
    else:
        prefix = f"{WEEKDAYS_ES[parsed.weekday()]} {parsed.day}/{parsed.month:02d}"
    return f"{prefix} · {parsed.strftime('%H:%M')} Madrid"


def match_title(item):
    item = item or {}
    home = _text(item.get("home_team") or item.get("home"), "Local")
    away = _text(item.get("away_team") or item.get("away"), "Visitante")
    return f"{home} vs {away}"


def competition_label(item):
    return _text((item or {}).get("competition_name") or (item or {}).get("league_name") or (item or {}).get("competition"), "Competicion")


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
        return "Proximo"
    return _text((item or {}).get("status") or (item or {}).get("state"), "Proximo")


def format_daily_summary_message(matches=None, focus="Agenda deportiva"):
    matches = list(matches or [])[:5]
    lines = [
        "SHARK RESUMEN DEL DIA",
        madrid_date_label(),
        "",
        f"{len(matches)} partidos monitorizados",
        f"Foco principal: {_text(focus, 'Agenda deportiva')}",
        "",
    ]
    for index, match in enumerate(matches, 1):
        lines.extend(
            [
                f"{index}. {match_title(match)}",
                f"   {competition_label(match)}",
                f"   {madrid_match_time_label(match)}",
                f"   Estado: {status_label(match)}",
                "",
            ]
        )
    if not matches:
        lines.extend(["Sin partidos destacados ahora mismo.", ""])
    lines.extend(
        [
            "SHARK solo publicara picks premium cuando haya cuota real, mercado claro y riesgo controlado.",
            "Apuesta siempre con responsabilidad.",
            "",
            "Ver partidos · Ver picks · Directo",
        ]
    )
    return "\n".join(lines).strip()


def format_midday_update_message(matches=None, picks_count=0):
    matches = list(matches or [])[:4]
    lines = ["SHARK ACTUALIZACION DE MEDIODIA", madrid_date_label(include_hour=True), ""]
    if matches:
        lines.append("Partidos relevantes:")
        for match in matches:
            lines.append(f"- {match_title(match)} · {madrid_match_time_label(match)}")
    else:
        lines.append("Sin cambios relevantes ahora mismo.")
    lines.append(f"Picks premium activos: {int(picks_count or 0)}")
    lines.append("Ver partidos · Ver picks")
    return "\n".join(lines)


def format_live_alert_message(match=None):
    match = match or {}
    lines = [
        "ALERTA LIVE SHARK",
        "",
        competition_label(match),
        f"{status_label(match)} · {score_label(match)}",
        "",
        f"Local: {_text(match.get('home_team'), 'Local')}",
        f"Visitante: {_text(match.get('away_team'), 'Visitante')}",
        "",
        "Seguimiento en directo activo",
        "",
        "Abrir directo · Ver picks",
    ]
    return "\n".join(lines)


def format_pick_message(pick=None):
    pick = pick or {}
    market = _text(pick.get("market") or pick.get("pick_type"), "Mercado pendiente")
    selection = _text(pick.get("selection") or pick.get("recommendation"), "Seleccion pendiente")
    odds = pick.get("odds")
    confidence = pick.get("confidence") or pick.get("shark_score") or pick.get("score") or "Pendiente"
    risk = _text(pick.get("risk_level") or pick.get("risk"), "Medio")
    stake = pick.get("stake_units") or pick.get("stake") or "Pendiente"
    reason = _text(pick.get("reasoning") or pick.get("reason") or pick.get("main_reason"), "Lectura SHARK disponible cuando haya contexto suficiente.")
    lines = [
        "PICK PREMIUM SHARK",
        "",
        competition_label(pick),
        match_title(pick),
        madrid_match_time_label(pick),
        "",
        f"Mercado: {market}",
        f"Seleccion: {selection}",
        f"Cuota: {odds if odds not in (None, '', 0, 0.0) else 'No disponible'}",
        f"Confianza SHARK: {confidence}/100" if str(confidence).isdigit() else f"Confianza SHARK: {confidence}",
        f"Riesgo: {risk}",
        f"Stake sugerido: {stake} uds" if str(stake) != "Pendiente" else "Stake sugerido: Pendiente",
        "",
        "Lectura SHARK:",
        reason,
        "",
        "Ver pick · Ver partido",
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
        pick_state = "Pendiente de auditoria"
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
        "Track Record actualizado si el resultado esta auditado.",
        "",
        "Ver historico · Ver resumen si existe",
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
        "Finalizado · Hora Madrid",
        "",
        "Ya puedes ver el resumen del partido.",
        "",
        "Ver resumen · Ver partido",
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
        "SHARK esta monitorizando este partido.",
        "",
        "Ver partido · Ver picks",
    ]
    return "\n".join(lines)


def format_evening_recap_message(summary=None):
    summary = summary or {}
    lines = [
        "CIERRE SHARK DEL DIA",
        "",
        madrid_date_label(),
        "",
        "Resultados actualizados" if summary.get("results") else "Resultados pendientes",
        "Track Record revisado" if summary.get("track_record") else "Track Record sin nuevos cierres",
        "Resumenes detectados" if summary.get("highlights") else "Sin resumenes nuevos detectados",
        "Picks premium publicados si hubo valor real",
        "",
        "Manana SHARK volvera a monitorizar la agenda.",
        "",
        "Ver historico · Ver partidos",
    ]
    return "\n".join(lines)
