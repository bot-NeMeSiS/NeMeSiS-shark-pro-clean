"""Professional team identity helpers for NeMeSiS SHARK PRO.

This module is intentionally lightweight and pure-stdlib. It centralises crest/logo
validation, national-team flags and graceful fallbacks so templates and Telegram
never show broken images, raw URLs or oversized placeholder letters.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import urllib.parse
from typing import Any


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _slug(value: Any) -> str:
    text = _norm(value)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "equipo"


COUNTRY_FLAGS = {
    "argentina": "🇦🇷",
    "australia": "🇦🇺",
    "austria": "🇦🇹",
    "belgium": "🇧🇪",
    "belgica": "🇧🇪",
    "bolivia": "🇧🇴",
    "bosnia herzegovina": "🇧🇦",
    "bosnia y herzegovina": "🇧🇦",
    "brazil": "🇧🇷",
    "brasil": "🇧🇷",
    "canada": "🇨🇦",
    "canada": "🇨🇦",
    "chile": "🇨🇱",
    "china": "🇨🇳",
    "colombia": "🇨🇴",
    "costa rica": "🇨🇷",
    "croatia": "🇭🇷",
    "croacia": "🇭🇷",
    "czech republic": "🇨🇿",
    "republica checa": "🇨🇿",
    "denmark": "🇩🇰",
    "dinamarca": "🇩🇰",
    "ecuador": "🇪🇨",
    "egypt": "🇪🇬",
    "egipto": "🇪🇬",
    "england": "🏴",
    "inglaterra": "🏴",
    "france": "🇫🇷",
    "francia": "🇫🇷",
    "germany": "🇩🇪",
    "alemania": "🇩🇪",
    "ghana": "🇬🇭",
    "italy": "🇮🇹",
    "italia": "🇮🇹",
    "japan": "🇯🇵",
    "japon": "🇯🇵",
    "mexico": "🇲🇽",
    "mexico": "🇲🇽",
    "morocco": "🇲🇦",
    "marruecos": "🇲🇦",
    "netherlands": "🇳🇱",
    "paises bajos": "🇳🇱",
    "norway": "🇳🇴",
    "noruega": "🇳🇴",
    "paraguay": "🇵🇾",
    "peru": "🇵🇪",
    "peru": "🇵🇪",
    "poland": "🇵🇱",
    "polonia": "🇵🇱",
    "portugal": "🇵🇹",
    "qatar": "🇶🇦",
    "romania": "🇷🇴",
    "rumania": "🇷🇴",
    "scotland": "🏴",
    "escocia": "🏴",
    "senegal": "🇸🇳",
    "serbia": "🇷🇸",
    "south africa": "🇿🇦",
    "sudafrica": "🇿🇦",
    "south korea": "🇰🇷",
    "corea del sur": "🇰🇷",
    "spain": "🇪🇸",
    "espana": "🇪🇸",
    "sweden": "🇸🇪",
    "suecia": "🇸🇪",
    "switzerland": "🇨🇭",
    "suiza": "🇨🇭",
    "turkey": "🇹🇷",
    "turquia": "🇹🇷",
    "ukraine": "🇺🇦",
    "ucrania": "🇺🇦",
    "united states": "🇺🇸",
    "estados unidos": "🇺🇸",
    "usa": "🇺🇸",
    "uruguay": "🇺🇾",
    "venezuela": "🇻🇪",
    "wales": "🏴",
    "gales": "🏴",
}

# Common global clubs where a simple colour emoji improves readability when no logo exists.
CLUB_EMOJIS = {
    "barcelona": "🔵🔴",
    "fc barcelona": "🔵🔴",
    "real madrid": "⚪",
    "atletico madrid": "🔴⚪",
    "atletico de madrid": "🔴⚪",
    "sevilla": "🔴⚪",
    "real betis": "🟢⚪",
    "chelsea": "🔵",
    "arsenal": "🔴",
    "liverpool": "🔴",
    "manchester city": "🔵",
    "manchester united": "🔴",
    "bayern munich": "🔴⚪",
    "bayern de munich": "🔴⚪",
    "inter milan": "🔵⚫",
    "inter de milan": "🔵⚫",
    "juventus": "⚫⚪",
    "psg": "🔵🔴",
}


def safe_logo_url(url: Any) -> str:
    """Return a safe web logo URL or empty string.

    Accepts https/http, app-local SVG fallback routes and data:image SVG/PNG/JPEG.
    Rejects text placeholders and javascript-like values.
    """
    value = str(url or "").strip()
    if not value:
        return ""
    low = value.lower()
    if low in {"none", "null", "undefined", "nan", "false", "0", "-"}:
        return ""
    if any(bad in low for bad in ("javascript:", "<script", "data:text/html")):
        return ""
    if value.startswith("/team-crest.svg"):
        return value
    if value.startswith("data:image/"):
        return value
    if value.startswith("https://") or value.startswith("http://"):
        return value
    return ""


def initials(name: Any) -> str:
    ignore = {"fc", "cf", "cd", "ud", "ad", "club", "de", "del", "la", "el", "los", "las", "the"}
    words = [w for w in re.split(r"[\s\-]+", str(name or "")) if w]
    letters = [w[0].upper() for w in words if _norm(w) not in ignore]
    if not letters and words:
        letters = [words[0][0].upper()]
    return "".join(letters[:3]) or "NS"


def flag_or_emoji(name: Any, country: Any = "") -> str:
    keys = [_norm(name), _norm(country)]
    for key in keys:
        if key in COUNTRY_FLAGS:
            return COUNTRY_FLAGS[key]
        if key in CLUB_EMOJIS:
            return CLUB_EMOJIS[key]
    return ""


def fallback_crest_url(name: Any) -> str:
    return "/team-crest.svg?" + urllib.parse.urlencode({"name": str(name or "Equipo")})


def emoji_crest_data_url(emoji: Any, name: Any = "Equipo") -> str:
    symbol = str(emoji or "⚽")[:4]
    label = str(name or "Equipo").replace('"', "")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-label="{label}">
  <defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#153252"/><stop offset="1" stop-color="#07111f"/></linearGradient></defs>
  <rect width="96" height="96" rx="24" fill="url(#g)"/>
  <circle cx="48" cy="48" r="34" fill="rgba(255,255,255,.08)" stroke="rgba(255,255,255,.22)" stroke-width="2"/>
  <text x="48" y="59" text-anchor="middle" font-family="Apple Color Emoji,Segoe UI Emoji,Noto Color Emoji,Arial,sans-serif" font-size="40">{symbol}</text>
</svg>"""
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="/:;,=?&%#@+!$'()*[]")


def identity_payload(name: Any, *, logo_url: Any = "", country: Any = "", source: Any = "", display_name: Any = "") -> dict[str, Any]:
    display = str(display_name or name or "Equipo").strip() or "Equipo"
    safe_logo = safe_logo_url(logo_url)
    emoji = flag_or_emoji(display, country)
    mode = "logo" if safe_logo else ("flag" if emoji else "fallback")
    crest_url = safe_logo or (emoji_crest_data_url(emoji, display) if emoji else fallback_crest_url(display))
    return {
        "key": _slug(display),
        "name": display,
        "display_name": display,
        "country": str(country or ""),
        "initials": initials(display),
        "flag_emoji": emoji,
        "team_emoji": emoji,
        "logo_url": safe_logo,
        "crest_url": crest_url,
        "crest_mode": mode,
        "crest_source": str(source or ("logo" if safe_logo else "fallback propio")),
        "has_real_logo": bool(safe_logo and not safe_logo.startswith("/team-crest.svg")),
        "ui_class": f"crest-{mode}",
        "dedupe_key": hashlib.md5(_slug(display).encode("utf-8")).hexdigest()[:10],
    }


def merge_identity(base: dict[str, Any] | None, *, name: Any = "", logo_url: Any = "", country: Any = "", source: Any = "") -> dict[str, Any]:
    base = dict(base or {})
    display = base.get("display_name") or base.get("name") or name or "Equipo"
    candidate_logo = safe_logo_url(logo_url) or safe_logo_url(base.get("crest_url")) or safe_logo_url(base.get("logo_url"))
    merged = identity_payload(display, logo_url=candidate_logo, country=country or base.get("country"), source=source or base.get("crest_source") or base.get("source"))
    for key, value in base.items():
        if key not in merged or not merged.get(key):
            merged[key] = value
    # Prefer known logo from the new payload if it is safe.
    if candidate_logo:
        merged["logo_url"] = candidate_logo
        merged["crest_url"] = candidate_logo
        merged["crest_mode"] = "logo"
        merged["ui_class"] = "crest-logo"
        merged["has_real_logo"] = not candidate_logo.startswith("/team-crest.svg")
    return merged
