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
    return {
        **legacy,
        **media,
        "can_embed": can_embed,
        "can_link": can_link,
        "autoplay": False,
        "downloads_video": False,
        "rehosts_video": False,
        "show_block": bool(can_embed or can_link),
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
