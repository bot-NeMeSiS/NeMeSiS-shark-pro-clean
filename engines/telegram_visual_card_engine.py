"""Optional Telegram visual cards for premium NeMeSiS messages.

The engine never fetches external assets. It uses real message data and safe
fallback initials, and it degrades to text-only delivery when Pillow is missing.
"""
from __future__ import annotations

import io
import os
import textwrap


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y", "si", "sí"}


def telegram_visual_card_config():
    return {
        "visual_cards_enabled": _env_bool("TELEGRAM_VISUAL_CARDS_ENABLED", True),
        "send_pick_cards": _env_bool("TELEGRAM_SEND_PICK_CARDS", True),
        "send_combi_cards": _env_bool("TELEGRAM_SEND_COMBI_CARDS", True),
        "send_result_cards": _env_bool("TELEGRAM_SEND_RESULT_CARDS", True),
        "send_highlight_cards": _env_bool("TELEGRAM_SEND_HIGHLIGHT_CARDS", True),
        "send_live_cards": _env_bool("TELEGRAM_SEND_LIVE_CARDS", False),
    }


def _text(value, fallback="Pendiente"):
    value = str(value or "").strip()
    return value if value else fallback


def _number(value, fallback=""):
    if value in (None, "", 0, 0.0):
        return fallback
    return str(value)


def _teams(item):
    item = item or {}
    return (
        _text(item.get("home_team") or item.get("home"), "Local"),
        _text(item.get("away_team") or item.get("away"), "Visitante"),
    )


def _competition(item):
    item = item or {}
    return _text(item.get("competition_name") or item.get("league_name") or item.get("competition"), "Competición")


def _initials(name):
    parts = [p for p in str(name or "").replace("-", " ").split() if p]
    if not parts:
        return "NS"
    return "".join(p[:1].upper() for p in parts[:2])[:2]


def _score(item):
    item = item or {}
    if item.get("score"):
        return str(item.get("score"))
    home = item.get("home_score")
    away = item.get("away_score")
    if home not in (None, "") and away not in (None, ""):
        return f"{home}-{away}"
    return "vs"


def build_pick_visual_card_payload(pick=None):
    pick = pick or {}
    home, away = _teams(pick)
    return {
        "kind": "pick",
        "eyebrow": "PICK PREMIUM SHARK",
        "competition": _competition(pick),
        "title": f"{home} vs {away}",
        "left_label": home,
        "right_label": away,
        "center": _text(pick.get("selection") or pick.get("recommendation"), "Selección pendiente"),
        "market": _text(pick.get("market") or pick.get("pick_type"), "Mercado pendiente"),
        "odds": _number(pick.get("odds"), "Sin cuota"),
        "confidence": _number(pick.get("confidence") or pick.get("shark_score") or pick.get("score"), "Pendiente"),
        "risk": _text(pick.get("risk_level") or pick.get("risk"), "Medio"),
        "stake": _number(pick.get("stake_units") or pick.get("stake"), "Pendiente"),
        "reason": _text(pick.get("main_reason") or pick.get("reasoning") or pick.get("reason"), "SHARK solo publica si detecta valor real."),
    }


def build_combi_visual_card_payload(combi=None):
    combi = combi or {}
    legs = combi.get("picks") or combi.get("legs") or []
    return {
        "kind": "combi",
        "eyebrow": "COMBI SHARK",
        "competition": _text(combi.get("competition") or combi.get("label"), "Combinada premium"),
        "title": _text(combi.get("title") or combi.get("name"), "Combi sugerida"),
        "left_label": f"{len(legs) or combi.get('legs_count') or 0} picks",
        "right_label": _text(combi.get("risk") or combi.get("risk_level"), "Riesgo controlado"),
        "center": _text(combi.get("strategy") or combi.get("type"), "Estrategia SHARK"),
        "market": "Cuota total",
        "odds": _number(combi.get("total_odds") or combi.get("odds"), "Pendiente"),
        "confidence": _number(combi.get("confidence") or combi.get("shark_score"), "Pendiente"),
        "risk": _text(combi.get("risk") or combi.get("risk_level"), "Medio"),
        "stake": _number(combi.get("stake_units") or combi.get("stake"), "Pendiente"),
        "reason": _text(combi.get("reason") or combi.get("main_reason"), "Combi basada en picks válidos disponibles."),
    }


def build_result_visual_card_payload(match=None, pick=None):
    match = match or {}
    home, away = _teams(match)
    return {
        "kind": "result",
        "eyebrow": "RESULTADO SHARK",
        "competition": _competition(match),
        "title": f"{home} vs {away}",
        "left_label": home,
        "right_label": away,
        "center": _score(match),
        "market": _text((pick or {}).get("market") or (pick or {}).get("selection"), "Resultado final"),
        "odds": _number((pick or {}).get("odds"), ""),
        "confidence": _number((pick or {}).get("confidence") or (pick or {}).get("shark_score"), ""),
        "risk": _text((pick or {}).get("result_status"), "Auditado"),
        "stake": _number((pick or {}).get("profit") or (pick or {}).get("stake_units"), ""),
        "reason": "Track record actualizado cuando el resultado queda auditado.",
    }


def build_highlight_visual_card_payload(match=None, highlight=None):
    match = match or highlight or {}
    home, away = _teams(match)
    return {
        "kind": "highlight",
        "eyebrow": "RESUMEN DISPONIBLE",
        "competition": _competition(match),
        "title": f"{home} vs {away}",
        "left_label": home,
        "right_label": away,
        "center": _score(match),
        "market": "Highlights",
        "odds": "",
        "confidence": "",
        "risk": "Contenido externo",
        "stake": "",
        "reason": "Resumen disponible si la fuente externa lo permite.",
    }


def build_live_visual_card_payload(match=None):
    match = match or {}
    home, away = _teams(match)
    minute = _text(match.get("minute") or match.get("status") or match.get("state"), "En directo")
    return {
        "kind": "live",
        "eyebrow": "ALERTA LIVE SHARK",
        "competition": _competition(match),
        "title": f"{home} vs {away}",
        "left_label": home,
        "right_label": away,
        "center": _score(match),
        "market": "Directo",
        "odds": minute,
        "confidence": _number(match.get("shark_score") or match.get("confidence"), ""),
        "risk": _text(match.get("risk") or match.get("risk_level"), "Seguimiento"),
        "stake": "",
        "reason": _text(match.get("live_alert") or match.get("main_reason"), "SHARK monitoriza momentum y estado del partido."),
    }


def build_visual_card_for_message(kind, payload=None):
    cfg = telegram_visual_card_config()
    if not cfg["visual_cards_enabled"]:
        return {"ok": False, "mode": "disabled", "fallback_reason": "visual_cards_disabled"}
    kind = str(kind or "").strip().lower()
    payload = payload or {}
    if kind == "pick_alert":
        if not cfg["send_pick_cards"]:
            return {"ok": False, "mode": "disabled", "fallback_reason": "pick_cards_disabled"}
        card = build_pick_visual_card_payload(payload.get("pick") or payload)
    elif kind == "combi_alert":
        if not cfg["send_combi_cards"]:
            return {"ok": False, "mode": "disabled", "fallback_reason": "combi_cards_disabled"}
        card = build_combi_visual_card_payload(payload.get("combi") or payload)
    elif kind == "result_final":
        if not cfg["send_result_cards"]:
            return {"ok": False, "mode": "disabled", "fallback_reason": "result_cards_disabled"}
        card = build_result_visual_card_payload(payload.get("match") or payload, payload.get("pick") or {})
    elif kind == "highlight_available":
        if not cfg["send_highlight_cards"]:
            return {"ok": False, "mode": "disabled", "fallback_reason": "highlight_cards_disabled"}
        card = build_highlight_visual_card_payload(payload.get("match") or payload, payload.get("highlight") or {})
    elif kind == "live_alert":
        if not cfg["send_live_cards"]:
            return {"ok": False, "mode": "disabled", "fallback_reason": "live_cards_disabled"}
        card = build_live_visual_card_payload(payload.get("match") or payload)
    else:
        return {"ok": False, "mode": "unsupported", "fallback_reason": f"unsupported_kind:{kind}"}
    png = build_telegram_visual_card_png(card)
    if not png:
        return {"ok": False, "mode": "text_fallback", "card": card, "fallback_reason": "pillow_not_available"}
    return {
        "ok": True,
        "mode": "png",
        "card": card,
        "png_bytes": png,
        "filename": f"nemesis_{card['kind']}_card.png",
    }


def build_telegram_visual_card_png(card, width=960, height=540):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    card = card or {}
    image = Image.new("RGB", (width, height), "#07111f")
    draw = ImageDraw.Draw(image)
    try:
        font_big = ImageFont.truetype("arial.ttf", 44)
        font_mid = ImageFont.truetype("arial.ttf", 28)
        font_small = ImageFont.truetype("arial.ttf", 22)
        font_tiny = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font_big = font_mid = font_small = font_tiny = ImageFont.load_default()

    draw.rounded_rectangle((26, 24, width - 26, height - 24), radius=28, fill="#0d1b2e", outline="#1f8cff", width=3)
    draw.text((56, 48), "NeMeSiS SHARK PRO", fill="#7dd3fc", font=font_small)
    draw.text((56, 86), _text(card.get("eyebrow"), "SHARK"), fill="#f8fafc", font=font_big)
    draw.text((56, 142), _text(card.get("competition"), "Competición"), fill="#cbd5e1", font=font_small)

    left = _text(card.get("left_label"), "Local")
    right = _text(card.get("right_label"), "Visitante")
    for x, label in ((78, left), (width - 218, right)):
        draw.ellipse((x, 205, x + 124, 329), fill="#13243a", outline="#38bdf8", width=2)
        draw.text((x + 42, 248), _initials(label), fill="#f8fafc", font=font_mid)
    draw.text((236, 222), left[:22], fill="#f8fafc", font=font_mid)
    draw.text((236, 268), _text(card.get("center"), "vs")[:32], fill="#facc15", font=font_big)
    draw.text((236, 326), right[:22], fill="#f8fafc", font=font_mid)

    metrics = [
        ("Mercado", card.get("market")),
        ("Cuota", card.get("odds")),
        ("Confianza", card.get("confidence")),
        ("Riesgo", card.get("risk")),
        ("Stake", card.get("stake")),
    ]
    x = 56
    for label, value in metrics:
        if not _text(value, ""):
            continue
        draw.rounded_rectangle((x, 388, x + 158, 448), radius=12, fill="#13243a")
        draw.text((x + 14, 398), label, fill="#94a3b8", font=font_tiny)
        draw.text((x + 14, 424), _text(value)[:14], fill="#f8fafc", font=font_small)
        x += 172

    reason = _text(card.get("reason"), "Lectura SHARK disponible.")
    wrapped = textwrap.wrap(reason, width=76)[:2]
    draw.text((56, 470), "Lectura SHARK: " + (wrapped[0] if wrapped else ""), fill="#e2e8f0", font=font_tiny)
    if len(wrapped) > 1:
        draw.text((56, 494), wrapped[1], fill="#e2e8f0", font=font_tiny)

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
