"""Safe video highlights foundation: metadata only, no downloads."""
from __future__ import annotations

from engines.content_rights_engine import classify_external_content, classify_media_asset


def classify_match_video(item: dict | None = None) -> dict:
    item = dict(item or {})
    item.setdefault("content_type", "video")
    legacy = classify_external_content(item)
    media = classify_media_asset(item, channel="APP")
    can_embed = bool(media["can_display"] and legacy.get("can_embed"))
    can_link = bool(media["can_display"] and legacy.get("can_link"))
    rights_status = str(media.get("rights_status") or "UNKNOWN_RIGHTS")
    if media.get("decision") == "BLOCKED":
        video_classification = "BLOCKED"
    elif not media.get("can_display"):
        video_classification = "REVIEW_REQUIRED"
    elif rights_status == "OWNED":
        video_classification = "OWN_GENERATED"
    elif can_embed and bool(item.get("official_source_verified")):
        video_classification = "OFFICIAL_EMBED"
    elif can_link and not can_embed:
        video_classification = "AUTHORIZED_LINK"
    elif rights_status in {"LICENSED", "PROVIDER_ALLOWED", "OPEN_LICENSE_ALLOWED", "ATTRIBUTION_REQUIRED"}:
        video_classification = "LICENSED_PROVIDER"
    else:
        video_classification = "REVIEW_REQUIRED"
    return {
        **legacy,
        **media,
        "can_embed": can_embed,
        "can_link": can_link,
        "autoplay": False,
        "downloads_video": False,
        "rehosts_video": False,
        "show_block": bool(can_embed or can_link),
        "video_classification": video_classification,
    }


def video_highlights_snapshot(items: list[dict] | None = None, *, preclassified: bool = False) -> dict:
    videos = [dict(item) if preclassified else classify_match_video(item) for item in (items or [])]
    visible = [item for item in videos if item.get("show_block")]
    return {
        "ok": True,
        "status": "VIDEO_HIGHLIGHTS_SAFE_FOUNDATION",
        "videos": videos,
        "visible_videos": visible,
        "visible_count": len(visible),
        "rights_warnings": len([item for item in videos if item.get("decision") in {"REVIEW_REQUIRED", "BLOCKED"}]),
        "rules": [
            "Solo embeds/enlaces permitidos.",
            "No descargar.",
            "No rehostear.",
            "No autoplay.",
            "No mostrar iframe roto.",
            "Una URL de proveedor no certifica por sí sola derechos comerciales.",
        ],
    }
