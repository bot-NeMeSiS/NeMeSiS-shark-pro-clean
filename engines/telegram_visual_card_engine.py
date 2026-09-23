"""Optional Telegram cards: local crests or initials, never external requests."""
from __future__ import annotations

import io
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .telegram_message_formatter import (
    _text, _v889_odds_label, competition_label, first_value, highlight_link,
    madrid_match_time_label, match_title, pick_result_label, score_label, status_label,
)
from .v935_launch_trust_engine import match_status_truth
from .crest_engine import _fetch_one

STATIC_ROOT = Path(__file__).resolve().parents[1] / "static"


def resolve_cached_visual_payload(payload, connection=None):
    """Reuse exact URL-to-local-path mappings; no downloads or name matching."""
    source = dict(payload or {})
    for key in ("pick", "match", "combi"):
        if isinstance(source.get(key), dict):
            source[key] = resolve_cached_visual_payload(source[key], connection)
    for key in ("picks", "legs"):
        if isinstance(source.get(key), list):
            source[key] = [resolve_cached_visual_payload(leg, connection) for leg in source[key][:8] if isinstance(leg, dict)]
    for side in ("home", "away"):
        url = first_value(source, side + "_logo", side + "_crest", side + "_logo_url", side + "_crest_url")
        if not url or connection is None:
            continue
        row = _fetch_one(connection, "SELECT local_path FROM team_logo_cache WHERE logo_url=? AND COALESCE(is_fallback,0)=0 AND local_path IS NOT NULL LIMIT 1", (url,))
        local = str(row.get("local_path") or "")
        if local.startswith("static/"):
            local = "/" + local
        if local.startswith("/static/") and _load_crest(local, 96)[0] is not None:
            source[side + "_logo"] = local
    return source


def _env_bool(name, default=False):
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on", "y", "si", "sí"}


def telegram_visual_card_config():
    return {
        "visual_cards_enabled": _env_bool("TELEGRAM_VISUAL_CARDS_ENABLED", True),
        "send_pick_cards": _env_bool("TELEGRAM_SEND_PICK_CARDS", True),
        "send_combi_cards": _env_bool("TELEGRAM_SEND_COMBI_CARDS", True),
        "send_result_cards": _env_bool("TELEGRAM_SEND_RESULT_CARDS", True),
        "send_highlight_cards": _env_bool("TELEGRAM_SEND_HIGHLIGHT_CARDS", True),
        "send_live_cards": _env_bool("TELEGRAM_SEND_LIVE_CARDS", False),
    }


def _base(item, kind, eyebrow):
    return {
        "kind": kind, "eyebrow": eyebrow, "title": match_title(item),
        "competition": competition_label(item), "datetime": madrid_match_time_label(item),
        "competition_logo": first_value(item, "competition_logo", "league_logo", "competition_logo_url", "league_logo_url"),
        "left_label": _text(first_value(item, "home_team", "home"), "Local por confirmar"),
        "right_label": _text(first_value(item, "away_team", "away"), "Visitante por confirmar"),
        "left_crest": first_value(item, "home_logo", "home_crest", "home_logo_url", "home_crest_url"),
        "right_crest": first_value(item, "away_logo", "away_crest", "away_logo_url", "away_crest_url"),
        "status": status_label(item), "membership": item.get("membership"),
    }


def build_pick_visual_card_payload(pick=None):
    pick = pick or {}
    return {**_base(pick, "pick", "PICK PREMIUM"),
        "center": _text(first_value(pick, "selection", "recommendation"), "Selección pendiente"),
        "market": _text(first_value(pick, "market", "pick_type"), "Mercado pendiente"),
        "metrics": [("Cuota registrada", _v889_odds_label(pick.get("odds"))),
                    ("Stake · unidades", _text(first_value(pick, "stake_units", "stake"))),
                    ("Confianza SHARK", _text(first_value(pick, "confidence", "shark_score"))),
                    ("Riesgo", _text(first_value(pick, "risk_level", "risk"), "No especificado"))],
        "reason": _text(first_value(pick, "main_reason", "reasoning", "reason"), "Análisis no publicado. Espera contexto suficiente antes de decidir."),
        "warning": _text(first_value(pick, "caution", "warning", "risk_note"), "Comprueba cuota y condiciones antes de decidir."),
    }


def build_combi_visual_card_payload(combi=None):
    combi = combi or {}
    legs = [leg for leg in (combi.get("picks") or combi.get("legs") or []) if isinstance(leg, dict)]
    return {**_base(combi, "combi", "COMBI SHARK"),
        "title": _text(first_value(combi, "title", "name"), "Combinada"),
        "competition": "Selecciones combinadas", "legs": legs,
        "center": _text(first_value(combi, "title", "name"), "Selecciones pendientes" if not legs else "Tu combinada, al detalle"),
        "market": ("1 selección" if len(legs) == 1 else f"{len(legs)} selecciones") if legs else "Sin selecciones publicadas",
        "metrics": [("Cuota total registrada", _v889_odds_label(first_value(combi, "total_odds", "odds"))),
                    ("Stake · unidades", _text(first_value(combi, "stake_units", "stake"))),
                    ("Riesgo", _text(first_value(combi, "risk_level", "risk"), "No especificado"))],
        "reason": _text(first_value(combi, "reason", "main_reason"), "Cada selección añade riesgo. Sin análisis publicado, espera."),
        "warning": "Una combinada nunca es una apuesta segura.",
    }


def build_result_visual_card_payload(match=None, pick=None):
    match, pick = match or {}, pick or {}
    return {**_base(match, "result", "RESULTADO / SEGUIMIENTO"),
        "center": score_label(match), "market": pick_result_label(pick).split(" ", 1)[-1],
        "metrics": [("Selección", _text(pick.get("selection"), "Sin pick publicado")),
                    ("Mercado", _text(pick.get("market"))),
                    ("Cuota registrada", _v889_odds_label(pick.get("odds")))],
        "reason": "Track Record actualizado." if pick.get("track_record_updated") is True else "Consulta la liquidación del pick. No se deduce del marcador.",
        "warning": "Resultado del partido y liquidación del pick son estados distintos.",
    }


def build_highlight_visual_card_payload(match=None, highlight=None):
    match, highlight = match or {}, highlight or {}
    available = bool(highlight_link(highlight))
    return {**_base(match or highlight, "highlight", "RESUMEN DEL PARTIDO"),
        "center": "Fuente disponible" if available else "Resumen pendiente",
        "market": "Contenido externo" if available else "Sin enlace habilitado",
        "metrics": [("Marcador", score_label(match)), ("Estado", status_label(match))],
        "reason": "Consulta el enlace en el mensaje. La reproducción depende de la fuente y sus permisos." if available else "Todavía no hay un resumen enlazable. No se promete reproducción ni disponibilidad.",
        "warning": "No alojamos ni redistribuimos vídeos sin autorización.",
    }


def build_live_visual_card_payload(match=None):
    match = match or {}
    live = match_status_truth(match)["is_live"]
    minute = first_value(match, "minute", "elapsed") if live else None
    return {**_base(match, "live", "EN DIRECTO" if live else "ESTADO POR CONFIRMAR"),
        "center": score_label(match) if live else "Marcador pendiente", "market": status_label(match),
        "metrics": [("Minuto confirmado", _text(minute, "Sin dato vigente")), ("Estado", status_label(match))],
        "reason": _text(first_value(match, "live_alert", "event_title") if live else None, "Sin evento confirmado disponible."),
        "warning": "El estado en directo requiere una observación vigente.",
    }


def build_visual_card_for_message(kind, payload=None):
    cfg = telegram_visual_card_config()
    if not cfg["visual_cards_enabled"]:
        return {"ok": False, "mode": "disabled", "fallback_reason": "visual_cards_disabled"}
    payload = payload or {}
    builders = {
        "pick_alert": ("send_pick_cards", lambda: build_pick_visual_card_payload(payload.get("pick") or payload)),
        "combi_alert": ("send_combi_cards", lambda: build_combi_visual_card_payload(payload.get("combi") or payload)),
        "result_final": ("send_result_cards", lambda: build_result_visual_card_payload(payload.get("match") or payload, payload.get("pick"))),
        "highlight_available": ("send_highlight_cards", lambda: build_highlight_visual_card_payload(payload.get("match") or payload, payload.get("highlight"))),
        "live_alert": ("send_live_cards", lambda: build_live_visual_card_payload(payload.get("match") or payload)),
    }
    if kind not in builders:
        return {"ok": False, "mode": "unsupported", "fallback_reason": "unsupported_kind"}
    flag, build = builders[kind]
    if not cfg[flag]:
        return {"ok": False, "mode": "disabled", "fallback_reason": f"{flag}_disabled"}
    try:
        card = build()
        card["membership"] = payload.get("membership") or card.get("membership")
        if card["membership"] == "FREE" and kind == "pick_alert":
            risk = next((metric for metric in card["metrics"] if metric[0] == "Riesgo"), ("Riesgo", "No especificado"))
            card["metrics"] = [("Plan", "FREE"), ("Estado", card["status"]), risk]
            card["reason"] = "Lectura disponible. El detalle del análisis depende de tu plan."
        png = build_telegram_visual_card_png(card)
        if not png:
            return {"ok": False, "mode": "text_fallback", "fallback_reason": "pillow_not_available"}
        return {"ok": True, "mode": "png", "card": card, "png_bytes": png, "filename": f"nemesis_{card['kind']}_card.png", "asset_diagnostics": card.get("asset_diagnostics", {})}
    except Exception:
        # Do not leak filesystem paths or arbitrary provider text in delivery logs.
        return {"ok": False, "mode": "text_fallback", "fallback_reason": "visual_render_failed"}


def _load_crest(value, size):
    from PIL import Image, ImageOps
    if not value:
        return None, "missing"
    parsed = urlsplit(str(value))
    if parsed.scheme or parsed.netloc:
        return None, "remote_not_cached"
    path = unquote(parsed.path)
    if not path.startswith("/static/"):
        return None, "unsupported_asset"
    try:
        root = STATIC_ROOT.resolve()
        candidate = root / path[len("/static/"):]
        resolved = candidate.resolve()
        resolved.relative_to(root)
        for parent in (candidate, *candidate.parents):
            if root in parent.parents and (parent.is_symlink() or (parent.exists() and getattr(parent.stat(), "st_file_attributes", 0) & 0x400)):
                return None, "unsafe_asset"
        if resolved.suffix.lower() not in {".png", ".webp", ".jpg", ".jpeg"} or resolved.stat().st_size > 2_000_000:
            return None, "unsupported_asset"
        with Image.open(resolved) as image:
            if image.width * image.height > 4_000_000:
                return None, "oversized_asset"
            crest = ImageOps.contain(image.convert("RGBA"), (size, size))
        return crest, "local_crest"
    except Exception:
        return None, "unavailable_asset"


@lru_cache(maxsize=32)
def _card_font(size, bold=False):
    from PIL import ImageFont
    for name in ("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)

def build_telegram_visual_card_png(card, width=960, height=1000):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    card = card or {}
    image = Image.new("RGB", (960, 1000), "#09151f")
    draw = ImageDraw.Draw(image)
    accent = {"pick": "#65e4dc", "combi": "#ffd37d", "live": "#ff8f92", "result": "#a4e6b4", "highlight": "#8cbbff"}.get(card.get("kind"), "#65e4dc")
    if card.get("kind") == "result":
        accent = {"FALLADO": "#ff8f92", "NULO": "#c2cfd6", "PENDIENTE": "#ffd37d"}.get(card.get("market"), accent)

    def text(value, x, y, max_width, size=26, lines=1, color="#eef6fa", bold=False, center=False):
        face = _card_font(size, bold)
        wrapped, current = [], ""
        for word in _text(value, "").split():
            if draw.textlength((current + " " + word).strip(), font=face) <= max_width:
                current = (current + " " + word).strip()
            else:
                if current:
                    wrapped.append(current)
                current = word
        if current:
            wrapped.append(current)
        for i, line in enumerate(wrapped[:lines]):
            if draw.textlength(line, font=face) > max_width or (i == lines - 1 and len(wrapped) > lines):
                while line and draw.textlength(line + "…", font=face) > max_width:
                    line = line[:-1]
                line += "…"
            offset = (max_width - draw.textlength(line, font=face)) / 2 if center else 0
            draw.text((x + offset, y + i * (size + 7)), line, fill=color, font=face)

    draw.rectangle((0, 0, 959, 7), fill=accent)
    text("NeMeSiS SHARK PRO", 48, 38, 570, 25, bold=True)
    plan = str(card.get("membership") or "").upper()
    text(plan if plan in {"FREE", "PRO", "ELITE"} else "SHARK", 740, 40, 172, 23, color=accent, bold=True)
    text(card.get("eyebrow"), 48, 86, 864, 24, color=accent, bold=True)
    league_logo, league_reason = _load_crest(card.get("competition_logo"), 46)
    if league_logo is not None:
        image.paste(league_logo, (48, 140), league_logo)
    text(card.get("competition"), 110 if league_logo is not None else 48, 143, 802 if league_logo is not None else 864, 29, bold=True)
    draw.line((48, 206, 912, 206), fill="#2d4250", width=2)
    if card.get("kind") == "combi":
        legs = card.get("legs") or []
        text(card.get("title"), 48, 228, 864, 29, bold=True)
        for i, leg in enumerate(legs[:3]):
            y = 281 + i * 73
            text(f"{i + 1:02d}", 48, y, 48, 23, color=accent, bold=True)
            for side, x in (("home", 106), ("away", 146)):
                crest, _ = _load_crest(first_value(leg, side + "_logo", side + "_crest", side + "_logo_url", side + "_crest_url"), 30)
                if crest is not None:
                    image.paste(crest, (x, y + 4), crest)
                else:
                    text(_text(leg.get(side + "_team"), "?")[0], x, y + 6, 30, 20, color=accent, center=True)
            text(match_title(leg), 194, y, 574, 24, bold=True)
            text(_text(leg.get("selection")) + " · " + madrid_match_time_label(leg), 108, y + 33, 660, 21, color="#b0c8d4")
            text(_v889_odds_label(leg.get("odds")), 788, y, 124, 23, color=accent)
            text(_v889_odds_label(leg.get("odds")), 788, y, 124, 23, color=accent)
        if not legs:
            text("Sin selecciones publicadas", 48, 298, 864, 28, color="#b0c8d4")
        if len(legs) > 3:
            remaining = len(legs) - 3
            label = "selección" if remaining == 1 else "selecciones"
            text(f"+ {remaining} {label} en el mensaje completo", 48, 503, 864, 21, color="#b0c8d4")
    else:
        diagnostics = {"competition": league_reason}
        for side, x in (("left", 48), ("right", 536)):
            label = card.get(f"{side}_label") or "Por confirmar"
            crest, reason = _load_crest(card.get(f"{side}_crest"), 96)
            diagnostics[side] = reason
            draw.rounded_rectangle((x, 235, x + 116, 351), radius=8, fill="#172936")
            if crest is not None:
                image.paste(crest, (x + (116 - crest.width) // 2, 235 + (116 - crest.height) // 2), crest)
            else:
                initials = "".join(word[0] for word in label.split()[:2]).upper()
                text(initials, x + 10, 269, 96, 34, center=True, bold=True, color=accent)
            text(label, x, 371, 376, 30, lines=2, bold=True)
        card["asset_diagnostics"] = diagnostics
        text("VS", 432, 275, 96, 22, center=True, color="#849eae")
        text(card.get("datetime"), 48, 465, 864, 25, color="#b0c8d4")
        text(card.get("status"), 48, 507, 864, 21, color=accent)

    draw.rounded_rectangle((48, 554, 912, 651), radius=8, fill="#132632")
    draw.rectangle((48, 562, 53, 643), fill=accent)
    text(card.get("market"), 76, 568, 808, 22, color=accent)
    text(card.get("center"), 76, 601, 808, 32, bold=True)
    metrics = (card.get("metrics") or [])[:4]
    col = 864 / max(1, len(metrics))
    for i, (label, value) in enumerate(metrics):
        x = 48 + i * col
        text(label, x, 680, col - 20, 20, color="#97b1c0")
        text(value, x, 714, col - 20, 25, lines=2, bold=True)
    draw.line((48, 791, 912, 791), fill="#2d4250", width=2)
    text("LECTURA SHARK", 48, 816, 864, 21, color=accent, bold=True)
    text(card.get("reason"), 48, 853, 864, 25, lines=2)
    text(card.get("warning"), 48, 935, 864, 19, color="#b0c8d4")
    text("Juego responsable · Sin garantías de resultado", 48, 967, 864, 16, color="#809eaf")
    if (width, height) != (960, 1000):
        image.thumbnail((max(320, min(width, 1920)), max(540, min(height, 2000))))
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
