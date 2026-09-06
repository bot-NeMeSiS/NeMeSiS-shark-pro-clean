from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from engines.content_rights_engine import ATTRIBUTION_REQUIRED, classify_media_asset
from engines.match_context_engine import build_match_context
from engines.team_center_engine import build_team_center_context
from engines.video_highlights_engine import classify_match_video, video_highlights_snapshot


def _match_detail(*, status: str = "upcoming") -> dict:
    is_live = status == "live"
    return {
        "match": {
            "id": "m-1",
            "home_team": "Club Norte",
            "away_team": "Club Sur",
            "competition_id": "140",
            "competition_name": "Liga Real",
            "match_date": "2026-08-30",
            "kickoff_iso": "2026-08-30T20:30:00+02:00",
            "status": status,
            "home_score": 1 if is_live else None,
            "away_score": 0 if is_live else None,
            "source": "qa_cache",
            "updated_at": datetime.now(ZoneInfo("Europe/Madrid")).isoformat(timespec="seconds") if is_live else "2026-08-30T20:45:00+02:00",
            "last_synced_at": datetime.now(ZoneInfo("Europe/Madrid")).isoformat(timespec="seconds") if is_live else "2026-08-30T20:45:00+02:00",
        },
        "timeline": [],
        "statistics": {"items": []},
        "related_picks": [],
        "lineups": [
            {
                "fixture_id": "m-1",
                "team_id": "club-norte",
                "team_name": "Club Norte",
                "player_id": "101",
                "player_name": "Jugador QA",
                "position": "MID",
                "number": "8",
                "is_starting": 1,
                "source": "qa_cache",
                "captured_at": "2026-08-30T19:30:00+02:00",
            }
        ],
        "media": video_highlights_snapshot([]),
        "state": {"shark_momentum": {"stats_available": False}},
    }


def _context(detail: dict) -> dict:
    return build_match_context(
        detail,
        madrid_context={
            "client_full_datetime_label": "domingo, 30 de agosto · 20:30",
            "client_date_label": "domingo, 30 de agosto",
            "client_time_label": "20:30",
            "client_competition": "Liga Real",
            "client_score_label": "1-0" if detail["match"].get("status") == "live" else "VS",
        },
    )


def test_confirmed_lineup_links_only_real_players_and_does_not_invent_pitch():
    context = _context(_match_detail())

    assert context["lineups"]["confirmed"] is True
    assert context["lineups"]["player_count"] == 1
    assert context["lineups"]["teams"][0]["starters"][0]["href"] == "/player/101"
    assert context["lineups"]["pitch_available"] is False
    assert context["lineups"]["fake_players_created"] == 0


def test_live_summary_is_factual_and_never_calls_generative_ai():
    context = _context(_match_detail(status="live"))
    summary = context["summaries"]

    assert summary["current_type"] == "LIVE_SUMMARY"
    assert "están disputando" in summary["items"][0]["text"]
    assert "programado" not in summary["items"][0]["text"]
    assert summary["generative_ai_calls"] == 0
    assert summary["unsupported_claims"] == 0


def test_team_context_exposes_real_lineup_player_to_player_center():
    detail = {
        "team": {"id": "club-norte", "name": "Club Norte", "competition_id": "140", "league": "Liga Real", "source": "qa_cache"},
        "name": "Club Norte",
        "players": _match_detail()["lineups"],
        "upcoming": [],
        "recent": [],
        "live": [],
        "picks": [],
    }
    context = build_team_center_context(detail, observed_at_madrid="2026-08-30T20:00:00+02:00")

    assert context["players"][0]["href"] == "/player/101"
    assert context["links"]["player_center"] == "/player/101"
    assert "team_has_player" in context["sports_graph"]["relationships"]


def test_team_context_never_links_player_without_real_persisted_id():
    player_without_id = dict(_match_detail()["lineups"][0])
    player_without_id.pop("player_id")
    detail = {
        "team": {"id": "club-norte", "name": "Club Norte", "competition_id": "140", "league": "Liga Real", "source": "qa_cache"},
        "name": "Club Norte",
        "players": [player_without_id],
        "upcoming": [],
        "recent": [],
        "live": [],
        "picks": [],
    }

    context = build_team_center_context(detail, observed_at_madrid="2026-08-30T20:00:00+02:00")

    assert context["players"] == []
    assert context["links"].get("player_center") in (None, "")
    assert "team_has_player" not in context["sports_graph"]["relationships"]


def test_unknown_or_incomplete_media_rights_fail_closed():
    unknown = classify_media_asset({"content_type": "player_photo", "photo_url": "https://example.invalid/player.jpg"})
    missing_attribution = classify_media_asset({
        "content_type": "player_photo",
        "photo_url": "https://example.invalid/player.jpg",
        "rights_status": ATTRIBUTION_REQUIRED,
        "commercial_use_status": "ALLOWED",
    })

    assert unknown["can_display"] is False
    assert unknown["decision"] == "REVIEW_REQUIRED"
    assert missing_attribution["can_display"] is False
    assert missing_attribution["decision"] == "REVIEW_REQUIRED"


def test_only_explicitly_authorized_official_video_is_visible():
    allowed = classify_match_video({
        "content_type": "video",
        "embed_url": "https://www.youtube.com/embed/official-qa",
        "original_url": "https://www.youtube.com/watch?v=official-qa",
        "source": "official_club_channel",
        "rights_status": "LICENSED",
        "commercial_use_status": "ALLOWED",
    })
    unknown = classify_match_video({
        "content_type": "video",
        "embed_url": "https://www.youtube.com/embed/unknown-qa",
        "source": "unknown_channel",
    })
    snapshot = video_highlights_snapshot([allowed, unknown], preclassified=True)

    assert allowed["show_block"] is True
    assert unknown["show_block"] is False
    assert snapshot["visible_count"] == 1
    assert snapshot["rights_warnings"] == 1
    assert all(item["downloads_video"] is False and item["rehosts_video"] is False for item in (allowed, unknown))
