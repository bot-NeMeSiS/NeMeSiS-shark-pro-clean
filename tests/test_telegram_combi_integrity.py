from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from engines.telegram_activity_engine import build_telegram_activity_plan, should_send_combi_alert
from engines.telegram_delivery_engine import build_combi_message
from engines.telegram_message_formatter import format_combi_message


def legs():
    return [{"match_id": f"qa-match-{n}", "home_team": f"QA Local {n}",
             "away_team": f"QA Visitante {n}", "competition_name": "LaLiga", "sport_key": "soccer_spain_la_liga",
             "kickoff_iso": "2026-11-28T20:00:00+01:00", "market": "Resultado final",
             "selection": f"QA Local {n}", "odds": 1.8} for n in range(2)]


def invalid_combi(case):
    rows = legs()
    if case == "one": rows = rows[:1]
    elif case == "duplicate": rows[1] = dict(rows[0])
    elif case == "suspended": rows[1]["suspended"] = True
    elif case == "closed": rows[1]["market_closed"] = "true"
    elif case == "missing_market": rows[1].pop("market")
    elif case == "missing_selection": rows[1].pop("selection")
    elif case == "invalid_odds": rows[1]["odds"] = float("nan")
    elif case == "wrong_type": rows[1] = "not a leg"
    elif case == "sixteen": rows = [{**rows[0], "match_id": f"qa-{n}"} for n in range(16)]
    return {"picks": rows, "total_odds": 3.24}


@pytest.mark.parametrize("case", ["one", "duplicate", "suspended", "closed", "missing_market", "missing_selection", "invalid_odds", "wrong_type", "sixteen"])
def test_incomplete_or_ineligible_whole_combi_is_not_prepared_or_planned(case, monkeypatch):
    monkeypatch.setenv("TELEGRAM_QUIET_HOURS_ENABLED", "false")
    combi = invalid_combi(case)
    original = deepcopy(combi)
    assert format_combi_message(combi) == ""
    assert build_combi_message(combi["picks"]) == ""
    assert not should_send_combi_alert(combi)
    assert combi.keys() == original.keys()
    assert len(combi["picks"]) == len(original["picks"])


def test_valid_combi_preserves_both_legs_and_unknown_joint_quote():
    rows = legs()
    text = format_combi_message({"picks": rows})
    assert "Partidos: 2" in text
    assert all(row["selection"] in text for row in rows)
    assert "Cuota total registrada: Cuota pendiente" in text
    assert "3.24" not in text


@pytest.mark.parametrize("value", [0, 0.0, "0"])
def test_planner_does_not_substitute_observed_zero_joint_odds(value, monkeypatch):
    monkeypatch.setenv("TELEGRAM_QUIET_HOURS_ENABLED", "false")
    assert not should_send_combi_alert({"picks": legs(), "total_odds": value, "odds": 4.75})


def test_overlong_combi_is_not_silently_cut_after_count():
    rows = [{**row, "selection": "LONG_SELECTION_" + "x" * 4000} for row in legs()]
    assert format_combi_message({"picks": rows, "total_odds": 3.24}) == ""


@pytest.mark.parametrize("payload", [None, {}, {"picks": []}, {"picks": [], "legs": legs()}, {"picks": legs(), "legs_count": 3}])
def test_no_alias_or_declared_count_can_repair_an_incomplete_set(payload):
    assert format_combi_message(payload) == ""


def test_explicit_false_closure_flags_do_not_discard_valid_set():
    rows = [{**row, "suspended": False, "market_closed": "false", "is_suspended": "0"} for row in legs()]
    assert format_combi_message({"picks": rows})


def test_all_legs_are_shown_or_message_is_retained_without_partial_text():
    rows = [{**legs()[0], "match_id": f"qa-{i}", "home_team": f"QA Home {i}", "selection": f"QA_SELECTION_{i}"} for i in range(9)]
    text = format_combi_message({"picks": rows, "total_odds": 9.9})
    assert text and "Partidos: 9" in text
    assert all(row["selection"] in text for row in rows)
    assert "mÃƒÂ¡s en la plataforma" not in text


def test_planner_records_reason_without_mutating_stored_combi(monkeypatch):
    monkeypatch.setenv("TELEGRAM_QUIET_HOURS_ENABLED", "false")
    combi = invalid_combi("suspended")
    original = deepcopy(combi)
    plan = build_telegram_activity_plan(combis=[combi], current=datetime(2026, 11, 28, 12, tzinfo=ZoneInfo("Europe/Madrid")))
    assert not any(row["kind"] == "combi_alert" for row in plan["candidates"])
    assert any(row["reason"] == "COMBI_MARKET_UNAVAILABLE" for row in plan["blockers"])
    assert combi == original


def test_transport_rejects_persisted_incomplete_combi_before_text_or_photo(app_module, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "qa-disposable-not-a-real-token")
    monkeypatch.setattr(app_module, "telegram_send_text_with_fallback", lambda *_: pytest.fail("unexpected text transport"))
    monkeypatch.setattr(app_module, "build_visual_card_for_message", lambda *_: pytest.fail("unexpected photo generation"))
    result = app_module.telegram_send_http("qa-disposable", "old partial body", message_type="combi_alert",
        payload={"visual_card_enabled": True, "visual_card_type": "combi_alert",
                 "visual_card_payload": {"combi": invalid_combi("suspended")}})
    assert not result["sent"] and result["status"] == "COMBI_INCOMPLETE_SET"


def test_transport_regenerates_complete_set_from_payload_not_old_body(app_module, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "qa-disposable-not-a-real-token")
    seen = []
    def mock_send(_url, data):
        seen.append(data["text"])
        return {"ok": True, "sent": True}
    monkeypatch.setattr(app_module, "telegram_send_text_with_fallback", mock_send)
    payload = {"visual_card_payload": {"combi": {"picks": legs(), "total_odds": 3.24}}}
    result = app_module.telegram_send_http("qa-disposable", "OLD_INCOMPLETE_BODY", message_type="combi_alert", payload=payload)
    assert result["sent"] and len(seen) == 1
    assert "OLD_INCOMPLETE_BODY" not in seen[0]
    assert all(row["selection"] in seen[0] for row in legs())


def test_queue_preserves_invalid_entry_history_as_skipped_without_send(app_module, tmp_path, monkeypatch):
    import json
    import sqlite3
    path = tmp_path / "owned-queue.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE telegram_queue(id TEXT,status TEXT,error_message TEXT,updated_at TEXT,body TEXT)")
        conn.execute("INSERT INTO telegram_queue(id,status,body) VALUES('qa-queue','pending','HISTORICAL_BODY')")
    monkeypatch.setattr(app_module, "db", lambda: sqlite3.connect(path))
    monkeypatch.setattr(app_module, "get_telegram_settings", lambda: {"enabled": True})
    monkeypatch.setattr(app_module, "telegram_pro_calibration", lambda: {"max_queue_per_tick": 5})
    monkeypatch.setattr(app_module, "telegram_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(app_module, "telegram_send_http", lambda *args, **kwargs: pytest.fail("queue must not send"))
    monkeypatch.setattr(app_module, "_telegram_queue_pending_rows", lambda **kwargs: [{"id": "qa-queue", "message_type": "combi_alert", "chat_id": "qa-disposable",
        "payload_json": json.dumps({"visual_card_payload": {"combi": invalid_combi("suspended")}})}])
    result = app_module.process_premium_telegram_queue(force=True)
    assert result["skipped"] == 1 and result["sent"] == 0
    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT status,error_message,body FROM telegram_queue").fetchone()
    assert row == (app_module.QUEUE_SKIPPED, "COMBI_INCOMPLETE_SET", "HISTORICAL_BODY")


def test_full_fifteen_leg_set_over_budget_is_rejected_not_abbreviated():
    rows = [{**legs()[0], "match_id": f"qa-long-{i}", "home_team": f"QA Home {i}",
             "selection": f"Selection {i} " + "x" * 200} for i in range(15)]
    assert format_combi_message({"picks": rows, "total_odds": 18}) == ""
    assert build_combi_message(rows) == ""


def test_supported_premium_formatter_does_not_silently_drop_fourth_leg():
    from engines.telegram_message_formatter import format_premium_combi_message
    rows = [{**legs()[0], "match_id": f"qa-four-{i}", "home_team": f"QA Home {i}", "selection": f"Unique leg {i}"} for i in range(4)]
    text = format_premium_combi_message(rows)
    assert "Partidos: 4" in text and all(row["selection"] in text for row in rows)
    assert format_premium_combi_message(invalid_combi("suspended")["picks"]) == ""


def test_malformed_leg_is_retained_as_invalid_not_filtered_by_sport_or_enrichment():
    rows = legs(); rows[1]["sport_key"] = "basketball_nba"
    assert not format_combi_message({"picks": rows})
    rows = legs(); rows[1]["selection"] = {"invented": "not text"}
    assert not format_combi_message({"picks": rows})
    rows = legs(); rows[1].pop("home_team")
    assert not format_combi_message({"picks": rows})


@pytest.mark.parametrize("value", [0, False, [], {"selection": "Local"}])
def test_non_text_selection_is_not_normalized_into_publishable_missing_value(value):
    rows = legs(); rows[1]["selection"] = value
    assert not format_combi_message({"picks": rows})


@pytest.mark.parametrize("count,long_selection", [(9, False), (4, False), (2, True)])
def test_photo_request_uses_complete_text_before_any_photo_when_it_cannot_fit(app_module, monkeypatch, count, long_selection):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "qa-disposable-not-a-real-token")
    rows = [{**legs()[0], "match_id": f"qa-photo-{i}", "home_team": f"Local {i}",
             "selection": f"Unique selection {i}" + (" & 🎯" * 35 if long_selection else "")} for i in range(count)]
    combi = {"picks": rows, "total_odds": 9.9}
    assert format_combi_message(combi)
    original = deepcopy(combi)
    monkeypatch.setattr(app_module, "resolve_cached_visual_payload", lambda *_: pytest.fail("must choose complete text before visual enrichment"))
    monkeypatch.setattr(app_module, "telegram_post_send_photo", lambda *_: pytest.fail("unexpected photo transport"))
    sent = []
    monkeypatch.setattr(app_module, "telegram_send_text_with_fallback", lambda _url, data: sent.append(data) or {"sent": True})
    result = app_module.telegram_send_http("qa-disposable", "OLD_BODY", payload={
        "visual_card_enabled": True, "visual_card_type": "combi_alert", "visual_card_payload": {"combi": combi}})
    assert result["sent"] and len(sent) == 1
    plain = app_module.telegram_plain_text_from_html(sent[0]["text"])
    assert f"Partidos: {count}" in plain
    assert all(row["selection"] in plain for row in rows)
    assert "Cuota total registrada: 9.9" in plain
    assert result["visual_card"]["reason"] == "combi_requires_complete_text"
    assert combi == original


@pytest.mark.parametrize("uncertain", [False, True])
def test_complete_small_combi_photo_retains_caption_and_no_duplicate_send(app_module, monkeypatch, uncertain):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "qa-disposable-not-a-real-token")
    combi = {"picks": legs(), "total_odds": 3.24}
    monkeypatch.setattr(app_module, "request_read_db", lambda: None)
    monkeypatch.setattr(app_module, "build_visual_card_for_message", lambda *_: {"ok": True, "png_bytes": b"owned-test-image", "mode": "png"})
    monkeypatch.setattr(app_module, "telegram_send_text_with_fallback", lambda *_: pytest.fail("unexpected duplicate text"))
    captions = []
    def photo(_token, _chat, _image, text, _payload):
        captions.append(app_module.telegram_photo_caption(text))
        return app_module.telegram_delivery_uncertain() if uncertain else {"sent": True}
    monkeypatch.setattr(app_module, "telegram_post_send_photo", photo)
    result = app_module.telegram_send_http("qa-disposable", "OLD_BODY", message_type="combi_alert", payload={
        "visual_card_enabled": True, "visual_card_type": "combi_alert", "visual_card_payload": {"combi": combi}})
    assert result.get("delivery_uncertain") if uncertain else result["sent"]
    assert len(captions) == 1
    plain = app_module.telegram_plain_text_from_html(captions[0])
    assert "Partidos: 2" in plain and "Cuota total registrada: 3.24" in plain
    assert all(row["selection"] in plain for row in legs())
    assert "Juego responsable" in plain


def test_combi_message_cannot_use_an_unrelated_pick_card(app_module, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "qa-disposable-not-a-real-token")
    monkeypatch.setattr(app_module, "resolve_cached_visual_payload", lambda *_: pytest.fail("unrelated visual must not be generated"))
    sent = []
    monkeypatch.setattr(app_module, "telegram_send_text_with_fallback", lambda _url, data: sent.append(data) or {"sent": True})
    result = app_module.telegram_send_http("qa-disposable", "OLD_BODY", message_type="combi_alert", payload={
        "visual_card_enabled": True, "visual_card_type": "pick_alert", "visual_card_payload": {"combi": {"picks": legs()}}})
    assert result["sent"] and len(sent) == 1
    assert all(row["selection"] in app_module.telegram_plain_text_from_html(sent[0]["text"]) for row in legs())
    assert result["visual_card"]["reason"] == "combi_requires_complete_text"
