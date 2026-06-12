"""Safe video highlights foundation: metadata only, no downloads."""
from __future__ import annotations

from engines.content_rights_engine import classify_external_content


def classify_match_video(item: dict | None = None) -> dict:
    item = dict(item or {})
    item.setdefault("content_type", "video")
    classified = classify_external_content(item)
    return {
        **classified,
        "autoplay": False,
        "downloads_video": False,
        "rehosts_video": False,
        "show_block": classified["rights_status"] in {"SAFE_EMBED", "SAFE_LINK_ONLY"},
    }


def video_highlights_snapshot(items: list[dict] | None = None) -> dict:
    videos = [classify_match_video(item) for item in (items or [])]
    return {
        "ok": True,
        "status": "VIDEO_HIGHLIGHTS_SAFE_FOUNDATION",
        "videos": videos,
        "rules": [
            "Solo embeds/enlaces permitidos.",
            "No descargar.",
            "No rehostear.",
            "No autoplay.",
            "No mostrar iframe roto.",
        ],
    }
