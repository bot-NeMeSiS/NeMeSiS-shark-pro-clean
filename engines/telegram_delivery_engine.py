"""Premium Telegram delivery helpers for NeMeSiS SHARK PRO.

Pure helpers only. Persistence, HTTP and Flask live in app.py.
"""

import hashlib
import html


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


def safe_html(value):
    return html.escape(str(value or ""), quote=False)


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


def format_match_line(match):
    comp = safe_html(match.get("league_name") or match.get("competition_name") or "Futbol")
    home = safe_html(match.get("home_team") or "Equipo local")
    away = safe_html(match.get("away_team") or "Equipo visitante")
    time = safe_html(match.get("kickoff_time") or match.get("match_time") or match.get("minute") or "Hora pendiente")
    status = safe_html((match.get("live_depth") or {}).get("label") or match.get("status") or "Programado")
    odds = f" - cuotas {safe_html(match.get('bookmaker'))}" if match.get("bookmaker") else ""
    return f"- <b>{home} vs {away}</b> - {time} - {comp} - {status}{odds}"


def build_daily_matches_message(matches, date_key, premium_name="NeMeSiS SHARK PRO"):
    lines = [
        f"<b>{safe_html(premium_name)}</b>",
        f"Partidos destacados - {safe_html(date_key)}",
        "",
    ]
    if not matches:
        lines.append("No hay partidos sincronizados para hoy. El calendario se actualizara cuando las fuentes autorizadas tengan datos.")
    else:
        for match in matches[:12]:
            lines.append(format_match_line(match))
    lines.extend(["", "Datos desde APIs permitidas, import legal y cache propio."])
    return "\n".join(lines)


def build_daily_picks_message(picks, force_empty=False, premium_name="NeMeSiS SHARK PRO"):
    lines = [f"<b>SHARK PICK PREMIUM</b>", f"{safe_html(premium_name)}", ""]
    if not picks:
        if not force_empty:
            return ""
        lines.append("No hay picks publicados ahora mismo. SHARK no fabrica picks sin fuente real/autorizada.")
        return "\n".join(lines)

    for index, pick in enumerate(picks[:6], start=1):
        home = pick.get("home_team") or "Equipo local"
        away = pick.get("away_team") or "Equipo visitante"
        match = safe_html(f"{home} vs {away}")
        comp = safe_html(pick.get("competition_name") or pick.get("league_name") or "Competicion")
        date = safe_html(pick.get("match_date") or "Fecha pendiente")
        selection = safe_html(pick.get("selection") or "Pick SHARK")
        market = safe_html(pick.get("market") or pick.get("pick_type") or "Mercado")
        odds = safe_html(pick.get("odds") or "Pendiente")
        confidence = safe_html(pick.get("confidence") or pick.get("shark_score") or "-")
        stake = safe_html(pick.get("stake_units") or "1")
        risk = safe_html(pick.get("risk_level") or "Medio")
        reason = safe_html(pick.get("reasoning") or "SHARK detecta valor con los datos disponibles.")
        warning = safe_html(pick.get("warning_reason") or "Gestiona stake y banca. Ningun pick es seguro.")
        value = "Detectado" if pick.get("odds") and pick.get("confidence") else "En calculo"
        lines.extend(
            [
                f"<b>{index}. {match}</b>",
                f"{comp} - {date}",
                f"Pick: <b>{selection}</b>",
                f"Mercado: {market}",
                f"Cuota: {odds} - Stake: {stake}/5",
                f"SHARK Score: {confidence}/100 - Riesgo: {risk}",
                f"Value: {value}",
                f"Por que entrar: {reason}",
                f"Riesgo: {warning}",
                "",
            ]
        )
    lines.extend(["Gestion de riesgo primero. Picks solo desde fuente autorizada o motor propio."])
    return "\n".join(lines)


def build_live_alert_message(match, event=None, internal_url="/live"):
    score = safe_html((match.get("live_depth") or {}).get("score") or match.get("score") or "sin marcador")
    minute = safe_html((match.get("live_depth") or {}).get("minute") or match.get("minute") or "LIVE")
    home = safe_html(match.get("home_team") or "Equipo local")
    away = safe_html(match.get("away_team") or "Equipo visitante")
    detail = safe_html((event or {}).get("title") or (event or {}).get("detail") or "Seguimiento en directo")
    return "\n".join(
        [
            "<b>Alerta live SHARK</b>",
            f"{minute} - <b>{home} vs {away}</b>",
            f"Marcador: {score}",
            detail,
            f"Ver en la app: {safe_html(internal_url)}",
        ]
    )


def build_system_test_message(now_iso, premium_name="NeMeSiS SHARK PRO"):
    return "\n".join(
        [
            f"<b>{safe_html(premium_name)}</b>",
            "Mensaje de prueba admin.",
            f"Hora: {safe_html(now_iso)}",
            "Canal Telegram premium operativo si recibes este aviso.",
        ]
    )


def queue_summary(rows):
    counts = {QUEUE_PENDING: 0, QUEUE_SENDING: 0, QUEUE_SENT: 0, QUEUE_FAILED: 0, QUEUE_SKIPPED: 0}
    for row in rows or []:
        status = str(row.get("status") or "").lower()
        counts[status] = counts.get(status, 0) + 1
    return counts
