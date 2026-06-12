"""Legal-safe external content classification for NeMeSiS SHARK PRO.

This engine never downloads, rehosts or caches external binaries. It only
classifies metadata/URLs so the app can decide whether to embed, link or fall
back safely.
"""
from __future__ import annotations

from urllib.parse import urlparse

SAFE_EMBED = "SAFE_EMBED"
SAFE_LINK_ONLY = "SAFE_LINK_ONLY"
METADATA_ONLY = "METADATA_ONLY"
FALLBACK_ONLY = "FALLBACK_ONLY"
BLOCKED_NO_RIGHTS = "BLOCKED_NO_RIGHTS"
UNKNOWN_REVIEW_REQUIRED = "UNKNOWN_REVIEW_REQUIRED"

VIDEO_PROVIDERS = {"youtube.com", "www.youtube.com", "youtu.be", "player.vimeo.com", "vimeo.com"}
IMAGE_API_HINTS = {"thesportsdb", "api-football", "sportsdb"}


def _host(url: str) -> str:
    try:
        return (urlparse(str(url or "")).netloc or "").lower()
    except Exception:
        return ""


def _has_url(item: dict, *keys: str) -> bool:
    return any(bool(item.get(key)) for key in keys)


def classify_external_content(item: dict | None) -> dict:
    item = dict(item or {})
    content_type = str(item.get("content_type") or item.get("type") or "unknown").lower()
    source = str(item.get("source") or item.get("provider") or "").strip()
    original_url = str(item.get("original_url") or item.get("url") or "").strip()
    embed_url = str(item.get("embed_url") or "").strip()
    attribution = str(item.get("attribution") or source or "").strip()
    host = _host(embed_url or original_url)
    source_low = source.lower()

    can_embed = False
    can_link = False
    can_cache_metadata = True
    can_cache_binary = False
    requires_review = False
    rights_status = UNKNOWN_REVIEW_REQUIRED

    if content_type in {"video", "highlight", "highlights"}:
        if embed_url and any(domain in host for domain in VIDEO_PROVIDERS):
            rights_status = SAFE_EMBED
            can_embed = True
            can_link = True
        elif original_url:
            rights_status = SAFE_LINK_ONLY
            can_link = True
        else:
            rights_status = FALLBACK_ONLY
            can_cache_metadata = False
    elif content_type in {"image", "crest", "logo", "badge"}:
        if not _has_url(item, "original_url", "url", "thumbnail_url", "image_url"):
            rights_status = FALLBACK_ONLY
            can_cache_metadata = False
        elif any(hint in source_low or hint in host for hint in IMAGE_API_HINTS):
            rights_status = SAFE_LINK_ONLY
            can_link = True
        else:
            rights_status = UNKNOWN_REVIEW_REQUIRED
            can_link = bool(original_url)
            requires_review = True
    elif content_type in {"news", "article", "preview"}:
        if original_url and attribution:
            rights_status = METADATA_ONLY
            can_link = True
        else:
            rights_status = UNKNOWN_REVIEW_REQUIRED
            requires_review = True
    elif not original_url and not embed_url:
        rights_status = FALLBACK_ONLY
        can_cache_metadata = False
    else:
        rights_status = UNKNOWN_REVIEW_REQUIRED
        can_link = bool(original_url)
        requires_review = True

    if item.get("rights_status") == BLOCKED_NO_RIGHTS:
        rights_status = BLOCKED_NO_RIGHTS
        can_embed = False
        can_link = False
        requires_review = True

    notice = "Contenido externo sujeto a disponibilidad y derechos de su fuente original."
    if rights_status == SAFE_EMBED:
        notice = "Embed externo permitido por fuente compatible; no se descarga ni se rehostea."
    elif rights_status == SAFE_LINK_ONLY:
        notice = "Solo enlace externo; no se descarga ni se rehostea contenido."
    elif rights_status == METADATA_ONLY:
        notice = "Solo metadatos y enlace a fuente original."
    elif rights_status == FALLBACK_ONLY:
        notice = "Sin contenido externo utilizable; usar fallback propio."
    elif rights_status == BLOCKED_NO_RIGHTS:
        notice = "Bloqueado por falta de derechos claros."

    return {
        "source": source,
        "provider": source or host,
        "content_type": content_type,
        "original_url": original_url,
        "embed_url": embed_url,
        "attribution": attribution,
        "rights_status": rights_status,
        "can_embed": can_embed,
        "can_link": can_link,
        "can_cache_metadata": can_cache_metadata,
        "can_cache_binary": can_cache_binary,
        "requires_review": requires_review,
        "notice_text": notice,
    }


def content_rights_policy_summary(items: list[dict] | None = None) -> dict:
    classified = [classify_external_content(item) for item in (items or [])]
    counts = {}
    for item in classified:
        counts[item["rights_status"]] = counts.get(item["rights_status"], 0) + 1
    return {
        "ok": True,
        "policy": "No descargar, no rehostear, no cachear binarios externos sin permiso.",
        "classified": classified,
        "counts": counts,
        "rules": [
            "Vídeos solo como embed/enlace permitido.",
            "Escudos externos solo por URL/fuente permitida o fallback propio.",
            "Noticias solo como metadatos y enlace si no hay licencia de reproducción.",
            "Sin scraping ilegal ni copia de artículos completos.",
            "Todo contenido externo debe conservar fuente/atribución cuando corresponda.",
        ],
    }
