from __future__ import annotations

from engines.telegram_delivery_engine import (
    build_combi_message,
    build_daily_matches_message,
    build_daily_picks_message,
    build_live_alert_message,
    build_system_test_message,
)
from engines.telegram_intelligence_engine import build_premium_message
from engines.telegram_message_formatter import (
    format_combi_message,
    format_daily_summary_message,
    format_evening_recap_message,
    format_highlight_message,
    format_live_alert_message,
    format_membership_pick_message,
    format_midday_update_message,
    format_pick_message,
    format_pick_result_tracking_message,
    format_premium_combi_message,
    format_premium_pick_message,
    format_prematch_message,
    format_result_message,
)

SAMPLE_MATCH = {
    "id": "m-premium-communication",
    "sport_key": "soccer_spain_la_liga",
    "home_team": "Real Madrid",
    "away_team": "Barcelona",
    "competition_name": "LaLiga",
    "kickoff_iso": "2026-08-01T21:00:00+02:00",
    "status": "upcoming",
    "market": "Resultado final",
    "selection": "Real Madrid",
    "odds": 1.85,
    "confidence": 82,
    "risk_level": "Medio",
    "stake_units": 1.5,
    "reasoning": "Mercado claro con cuota real y contexto suficiente.",
    "match_url": "https://nemesis.local/match/m-premium-communication",
}

BAD_VISIBLE_TEXT = (
    "\ufffd",
    chr(0x00C3),
    chr(0x00C2),
    "\u00e2\u20ac",
    "\u00e2\u20ac\u2122",
    "? Agenda",
    "Selecci?n",
    "Actualizaci?n",
    "An?",
    "membres?",
    "undefined",
    "null",
    "None",
    "ROI garantizado",
    "apuesta segura",
)


def _assert_premium_message_contract(text: str, *, require_transparency: bool = True) -> None:
    assert text
    assert "NeMeSiS SHARK PRO" in text
    assert len(text) <= 3900
    assert all(term not in text for term in BAD_VISIBLE_TEXT)
    assert text.count("\n\n\n") == 0
    if require_transparency:
        assert "Fuente: NeMeSiS" in text
        assert "Evidencia:" in text
        assert "Limitaciones:" in text


def _assert_telegram_html_is_balanced(text: str) -> None:
    assert text.count("<b>") == text.count("</b>")
    assert text.count("<i>") == text.count("</i>")
    assert "<script" not in text.lower()


def test_plain_activity_messages_share_premium_identity_and_transparency():
    messages = [
        format_daily_summary_message([SAMPLE_MATCH]),
        format_midday_update_message([SAMPLE_MATCH], picks_count=1),
        format_live_alert_message({**SAMPLE_MATCH, "status": "live", "home_score": 1, "away_score": 0}),
        format_pick_message(SAMPLE_MATCH),
        format_premium_pick_message(SAMPLE_MATCH, quality={"sendable": True}, membership="PRO"),
        format_membership_pick_message(SAMPLE_MATCH, quality={"sendable": True}, membership="FREE"),
        format_premium_combi_message([SAMPLE_MATCH], quality={"status": "En revision"}, membership="ELITE"),
        format_pick_result_tracking_message(SAMPLE_MATCH, {"score": "1-0", "result_status": "won"}),
        format_combi_message({"picks": [SAMPLE_MATCH], "total_odds": 1.85}),
        format_result_message({**SAMPLE_MATCH, "score": "1-0"}, {"result_status": "won", "selection": "Real Madrid"}),
        format_highlight_message(SAMPLE_MATCH),
        format_prematch_message(SAMPLE_MATCH),
        format_evening_recap_message({"results": True, "track_record": True, "highlights": False}),
    ]
    for message in messages:
        _assert_premium_message_contract(message)


def test_delivery_messages_keep_send_logic_read_only_and_html_safe():
    messages = [
        build_daily_matches_message([SAMPLE_MATCH], "2026-08-01"),
        build_daily_picks_message([SAMPLE_MATCH], force_empty=False),
        build_combi_message([SAMPLE_MATCH]),
        build_live_alert_message({**SAMPLE_MATCH, "status": "live", "home_score": 1, "away_score": 0}),
    ]
    for message in messages:
        _assert_premium_message_contract(message)
        _assert_telegram_html_is_balanced(message)

    admin_message = build_system_test_message("2026-08-01T10:00:00+02:00")
    _assert_premium_message_contract(admin_message, require_transparency=False)
    _assert_telegram_html_is_balanced(admin_message)
    assert "No es un pick ni una recomendacion" not in admin_message
    assert "No es un pick ni una recomendaci\u00f3n" in admin_message


def test_telegram_intelligence_preview_is_premium_and_never_sends():
    pro = build_premium_message(SAMPLE_MATCH, "PRO")
    free = build_premium_message(SAMPLE_MATCH, "FREE")
    assert pro["send_executed"] is False
    assert free["send_executed"] is False
    _assert_premium_message_contract(pro["preview"])
    _assert_premium_message_contract(free["preview"])
    assert "Cuota registrada" in pro["preview"]
    assert "Cuota registrada" not in free["preview"]
