"""V941 product vocabulary: internal pick identifiers, Spanish UI Pronóstico."""
from pathlib import Path
from engines.ui_localization_engine import preferred_terms, translate
from engines.telegram_message_formatter import format_midday_update_message, format_pick_message
from engines.telegram_visual_card_engine import build_pick_visual_card_payload

ROOT = Path(__file__).resolve().parents[1]

def test_spanish_ui_uses_pronostico_but_internal_route_stays_picks():
    assert preferred_terms("Pick · Picks · pick(s)", "es") == "Pronóstico · Pronósticos · pronóstico(s)"
    assert translate("Picks", "es") == "Pronósticos"
    nav=(ROOT/"templates/components/v933_navigation.html").read_text(encoding="utf-8")
    assert "Pronósticos" in nav and "/picks" in nav

def test_browser_guard_is_text_only():
    js=(ROOT/"static/ui-localization.js").read_text(encoding="utf-8")
    assert "preferredTerms" in js and "MutationObserver" in js and "SHOW_TEXT" in js

def test_telegram_visible_copy_uses_pronostico():
    summary=format_midday_update_message([],2)
    msg=format_pick_message({"home_team":"QA Norte","away_team":"QA Sur","market":"1X2","selection":"Local","odds":1.85})
    assert "pick" not in summary.casefold() and "pronóstico" in summary.casefold()
    assert "pick" not in msg.casefold() and "pronóstico" in msg.casefold()

def test_visual_card_preserves_internal_kind():
    card=build_pick_visual_card_payload({"home_team":"QA Norte","away_team":"QA Sur","market":"1X2","selection":"Local","odds":1.85})
    assert card["kind"]=="pick" and "PRONÓSTICO" in card["eyebrow"]
