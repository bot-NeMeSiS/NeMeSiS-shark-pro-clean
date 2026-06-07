"""Premium Telegram delivery helpers for NeMeSiS SHARK PRO.

Pure helpers only. Persistence, HTTP and Flask live in app.py.
"""

import hashlib
import html


DEFAULT_SETTINGS = {
    "id": "default",
    "enabled": False,
    "auto_daily_matches": True,
    "auto_daily_picks": True,
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


def membership_rank(value):
    return {"FREE": 0, "PRO": 1, "ELITE": 2, "ADMIN": 3}.get(membership_label(value), 0)


def telegram_plan_allows(user_membership, required_membership):
    return membership_rank(user_membership) >= membership_rank(required_membership)


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
    home = safe_html(match.get("home_team") or "")
    away = safe_html(match.get("away_team") or "")
    time = safe_html(match.get("kickoff_time") or match.get("match_time") or match.get("minute") or "hora por confirmar")
    status = safe_html((match.get("live_depth") or {}).get("label") or match.get("status") or "Programado")
    odds = ""
    if match.get("bookmaker"):
        odds = f" · cuotas {safe_html(match.get('bookmaker'))}"
    return f"• <b>{home} vs {away}</b> · {time} · {comp} · {status}{odds}"


def pick_required_membership(pick):
    return membership_label((pick or {}).get("membership_required") or (pick or {}).get("membership") or "FREE")


def pick_match_name(pick):
    home = safe_html((pick or {}).get("home_team") or (pick or {}).get("team_name") or "")
    away = safe_html((pick or {}).get("away_team") or "")
    if home and away:
        return f"{home} vs {away}"
    return home or away or "Partido"


def pick_badge_context(pick):
    pick = dict(pick or {})
    home_logo = pick.get("home_logo") or pick.get("home_badge") or ""
    away_logo = pick.get("away_logo") or pick.get("away_badge") or ""
    team_badge = pick.get("team_badge") or pick.get("badge_url") or ""
    league_badge = pick.get("league_badge") or pick.get("competition_badge") or ""
    has_badge = bool(home_logo or away_logo or team_badge or league_badge)
    return {
        "has_badge": has_badge,
        "home_logo": home_logo,
        "away_logo": away_logo,
        "team_badge": team_badge,
        "league_badge": league_badge,
        "fallback": "" if has_badge else "Escudo no disponible; se envía texto premium.",
        "delivery_mode": "text_with_badge_context" if has_badge else "text_only",
    }


def pick_line_common(pick):
    pick = dict(pick or {})
    selection = safe_html(pick.get("selection") or pick.get("pick_type") or "Pick SHARK")
    market = safe_html(pick.get("market") or "Mercado principal")
    odds = safe_html(pick.get("odds") or pick.get("odds_value") or "-")
    confidence = safe_html(pick.get("confidence") or pick.get("shark_score") or "-")
    risk = safe_html(pick.get("risk_level") or pick.get("risk") or "MEDIO")
    return selection, market, odds, confidence, risk, pick_match_name(pick)


def format_telegram_pick_free(pick):
    selection, market, odds, confidence, risk, match = pick_line_common(pick)
    return "\n".join(
        [
            f"<b>{selection}</b>",
            match,
            f"{market} · cuota {odds}",
            f"Confianza SHARK: {confidence}% · riesgo {risk}",
            "Vista FREE: análisis resumido. PRO desbloquea stake, motivo y value.",
        ]
    )


def format_telegram_pick_pro(pick):
    selection, market, odds, confidence, risk, match = pick_line_common(pick)
    stake = safe_html((pick or {}).get("stake_units") or "1")
    reason = safe_html((pick or {}).get("reasoning") or (pick or {}).get("reason") or "SHARK detecta valor con los datos disponibles.")
    return "\n".join(
        [
            f"<b>{selection}</b>",
            match,
            f"{market} · cuota {odds}",
            f"Confianza SHARK: {confidence}% · riesgo {risk} · stake sugerido {stake}u",
            f"Motivo: {reason}",
        ]
    )


def format_telegram_pick_elite(pick):
    selection, market, odds, confidence, risk, match = pick_line_common(pick)
    stake = safe_html((pick or {}).get("stake_units") or "1")
    value = safe_html((pick or {}).get("value_label") or (pick or {}).get("value") or "Value contextual")
    reason = safe_html((pick or {}).get("reasoning") or (pick or {}).get("reason") or "SHARK detecta valor con los datos disponibles.")
    learning = safe_html((pick or {}).get("learning_explanation") or "")
    warning = safe_html((pick or {}).get("warning_reason") or (pick or {}).get("warning") or "Gestiona banca y confirma cambios de cuota.")
    lines = [
        f"<b>{selection}</b>",
        match,
        f"{market} · cuota {odds} · {value}",
        f"Confianza SHARK: {confidence}% · riesgo {risk} · stake sugerido {stake}u",
        f"Análisis: {reason}",
    ]
    if learning:
        lines.append(f"Learning: {learning}")
    lines.append(f"Precaución: {warning}")
    return "\n".join(lines)


def format_telegram_pick_by_membership(pick, membership="ADMIN"):
    membership = membership_label(membership)
    if membership == "FREE":
        return format_telegram_pick_free(pick)
    if membership == "PRO":
        return format_telegram_pick_pro(pick)
    return format_telegram_pick_elite(pick)


def build_daily_matches_message(matches, date_key, premium_name="NeMeSiS SHARK PRO"):
    lines = [
        f"<b>{safe_html(premium_name)}</b>",
        f"Partidos destacados · {safe_html(date_key)}",
        "",
    ]
    if not matches:
        lines.append("No hay partidos sincronizados para hoy. El calendario se actualizara cuando las fuentes autorizadas tengan datos.")
    else:
        for match in matches[:12]:
            lines.append(format_match_line(match))
    lines.extend(["", "Datos desde APIs permitidas, import legal y cache propio."])
    return "\n".join(lines)


def build_daily_picks_message(picks, force_empty=False, premium_name="NeMeSiS SHARK PRO", membership="ADMIN"):
    membership = membership_label(membership)
    allowed = [pick for pick in (picks or []) if telegram_plan_allows(membership, pick_required_membership(pick))]
    if membership == "FREE":
        allowed = allowed[:3]
    lines = [f"<b>{safe_html(premium_name)}</b>", f"Picks destacados · {membership}", ""]
    if not allowed:
        if not force_empty:
            return ""
        lines.append("No hay picks disponibles para tu plan ahora mismo. SHARK no fabrica picks sin fuente real/autorizada.")
        return "\n".join(lines)
    for pick in allowed[:8]:
        lines.append(format_telegram_pick_by_membership(pick, membership))
        lines.append("")
    if membership == "FREE":
        lines.append("Mejora a PRO/ELITE para recibir stake, value y análisis completo.")
    else:
        lines.append("Gestión de riesgo primero. Picks solo desde fuente autorizada o motor propio.")
    return "\n".join(lines)


def build_live_alert_message(match, event=None, internal_url="/live"):
    score = safe_html((match.get("live_depth") or {}).get("score") or match.get("score") or "sin marcador")
    minute = safe_html((match.get("live_depth") or {}).get("minute") or match.get("minute") or "LIVE")
    home = safe_html(match.get("home_team") or "")
    away = safe_html(match.get("away_team") or "")
    detail = safe_html((event or {}).get("title") or (event or {}).get("detail") or "Seguimiento en directo")
    return "\n".join(
        [
            "<b>Alerta live SHARK</b>",
            f"{minute} · <b>{home} vs {away}</b>",
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
