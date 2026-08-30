from __future__ import annotations

import sqlite3

import app as app_module
from engines.content_rights_engine import classify_media_asset
from engines.sportsdb_highlights_engine import (
    _upsert_highlight,
    classify_stored_highlight,
    ensure_sportsdb_highlights_schema,
    sportsdb_highlights_for_match,
    sportsdb_highlights_summary,
)


VIDEO_URL = "https://www.youtube.com/watch?v=rights-qa"
EMBED_URL = "https://www.youtube-nocookie.com/embed/rights-qa"


def _insert(db_path, *, item_id="h-1", match_id="m-1", rights="UNKNOWN_RIGHTS", commercial="UNKNOWN", attribution="", attribution_required=0, official=0, geo="UNKNOWN"):
    ensure_sportsdb_highlights_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO sportsdb_match_highlights(
                id,match_id,title,video_url,embed_url,thumbnail_url,source,provider,
                status,client_status,rights_status,commercial_use_status,attribution,
                attribution_required,rights_verified_at,official_source_verified,
                geo_restriction_status,rights_note,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item_id, match_id, "Partido real QA", VIDEO_URL, EMBED_URL,
                "https://example.invalid/unlicensed-thumbnail.jpg", "TheSportsDB",
                "YouTube", "READY", "READY", rights, commercial, attribution,
                attribution_required, "2026-08-30T12:00:00+02:00", official, geo,
                rights, "2026-08-30T12:00:00+02:00", "2026-08-30T12:00:00+02:00",
            ),
        )


def test_provider_url_is_metadata_only_until_rights_are_explicit(tmp_path):
    db_path = tmp_path / "media.db"
    _insert(db_path)

    match_media = sportsdb_highlights_for_match(db_path, "m-1")
    summary = sportsdb_highlights_summary(db_path)

    assert match_media["highlights"] == []
    assert match_media["all_highlights"][0]["decision"] == "REVIEW_REQUIRED"
    assert match_media["rights_warnings"] == 1
    assert summary["stored_media_total"] == 1
    assert summary["authorized_highlights"] == 0
    assert summary["blocked_highlights"] == 1


def test_official_authorized_video_is_visible_but_unknown_thumbnail_is_not(tmp_path):
    db_path = tmp_path / "media.db"
    _insert(db_path, rights="LICENSED", commercial="ALLOWED", attribution="Canal oficial", official=1)

    item = sportsdb_highlights_for_match(db_path, "m-1")["highlights"][0]

    assert item["show_block"] is True
    assert item["can_embed"] is True
    assert item["video_classification"] == "OFFICIAL_EMBED"
    assert item["thumbnail_url"] == ""
    assert item["thumbnail_rights"]["decision"] == "REVIEW_REQUIRED"


def test_required_attribution_missing_blocks_video(tmp_path):
    db_path = tmp_path / "media.db"
    _insert(db_path, rights="ATTRIBUTION_REQUIRED", commercial="ALLOWED", attribution="", attribution_required=1)

    item = sportsdb_highlights_for_match(db_path, "m-1")["all_highlights"][0]

    assert item["show_block"] is False
    assert item["decision"] == "REVIEW_REQUIRED"
    assert "atribución" in item["reason"]


def test_known_geo_restriction_falls_back_to_authorized_external_link(tmp_path):
    db_path = tmp_path / "media.db"
    _insert(db_path, rights="LICENSED", commercial="ALLOWED", attribution="Fuente autorizada", geo="RESTRICTED")

    item = sportsdb_highlights_for_match(db_path, "m-1")["highlights"][0]

    assert item["geo_restricted"] is True
    assert item["can_embed"] is False
    assert item["can_link"] is True
    assert item["show_block"] is True
    assert item["video_classification"] == "AUTHORIZED_LINK"


def test_provider_resync_does_not_overwrite_human_rights_decision(tmp_path):
    db_path = tmp_path / "media.db"
    ensure_sportsdb_highlights_schema(db_path)
    payload = {
        "idEvent": "event-1",
        "strEvent": "Club Norte vs Club Sur",
        "dateEvent": "2026-08-30",
        "strVideo": VIDEO_URL,
    }
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        first = _upsert_highlight(conn, payload)
        conn.execute(
            """UPDATE sportsdb_match_highlights
               SET rights_status='LICENSED', commercial_use_status='ALLOWED',
                   attribution='Canal oficial', official_source_verified=1,
                   rights_verified_at='2026-08-30T12:00:00+02:00'
               WHERE id=?""",
            (first["id"],),
        )
        _upsert_highlight(conn, payload)
        row = dict(conn.execute("SELECT * FROM sportsdb_match_highlights WHERE id=?", (first["id"],)).fetchone())

    assert row["rights_status"] == "LICENSED"
    assert row["commercial_use_status"] == "ALLOWED"
    assert row["attribution"] == "Canal oficial"
    assert row["client_status"] == "AUTHORIZED"


def test_legacy_client_adapter_cannot_surface_unknown_rights(tmp_path, monkeypatch):
    db_path = tmp_path / "media.db"
    _insert(db_path, item_id="unknown", rights="UNKNOWN_RIGHTS")
    _insert(db_path, item_id="allowed", rights="LICENSED", commercial="ALLOWED", attribution="Canal oficial")
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path))

    mapped = app_module.v766_highlight_map(["m-1"], limit_per_match=5)
    unknown_detail = app_module.v769_get_highlight_by_id("unknown")
    allowed_detail = app_module.v769_get_highlight_by_id("allowed")

    assert [item["id"] for item in mapped["m-1"]] == ["allowed"]
    assert unknown_detail == {}
    assert allowed_detail["can_link"] is True


def test_media_channel_restriction_fails_closed():
    decision = classify_media_asset({
        "content_type": "player_photo",
        "photo_url": "https://example.invalid/player.jpg",
        "rights_status": "LICENSED",
        "commercial_use_status": "ALLOWED",
        "allowed_channels": ["EDITORIAL_ARCHIVE"],
    }, channel="APP")

    assert decision["decision"] == "BLOCKED"
    assert decision["channel_allowed"] is False
    assert decision["can_display"] is False
