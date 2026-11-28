"""Actual pick storage must preserve only quote metadata bound to the same snapshot."""
import json
from copy import deepcopy

import pytest
from engines import telegram_message_formatter as fmt


def stored_pick():
    raw = {"id": "qa-stored-quote", "match_id": "qa-stored-fixture", "home_team": "Local QA", "away_team": "Visitante QA",
           "market": "1X2", "selection": "1", "odds": "1.80", "bookmaker": "Casa QA",
           "odds_source": "API-Football", "odds_updated_at": "2025-01-01T12:00:00Z"}
    row = {key: value for key, value in raw.items() if key not in {"odds_source", "odds_updated_at"}}
    row.update({"market": "1X2", "selection": "Gana Local QA", "odds": 1.8,
                "_raw_selection": "1", "raw_json": json.dumps(raw), "updated_at": "2025-07-01T10:11:12Z"})
    return row, raw


def test_actual_writer_reader_and_candidate_keep_own_saved_quote_metadata(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "safe_memory_call", lambda *a, **kw: None)
    _, payload = stored_pick()
    payload.update({"status": "published", "sport_key": "soccer", "competition_name": "Liga QA", "membership_required": "PRO"})
    saved = app_module.create_or_update_pick(payload, pick_id=payload["id"], publish=True)
    assert "odds_source" not in saved and "odds_updated_at" not in saved
    assert json.loads(saved["raw_json"])["odds_source"] == "API-Football"
    body = app_module.v771_format_activity_candidate({"kind": "pick_alert", "payload": {"pick": saved}}, membership="PRO")
    assert "Fuente de cuota: API-Football" in body
    assert "Hora de cuota registrada: 01/01/2025 · 13:00:00 Madrid" in body
    preview = app_module.v771_format_activity_candidate({"kind": "pick_alert", "payload": {"pick": saved}}, membership="FREE")
    assert "API-Football" not in preview and "13:00:00" not in preview


def test_stored_identity_handles_existing_localization_and_decimal_representation():
    item, _ = stored_pick()
    before = deepcopy(item)
    body = fmt.format_pick_message(item)
    assert "Fuente de cuota: API-Football" in body
    assert "Hora de cuota registrada: 01/01/2025 · 13:00:00 Madrid" in body
    assert item == before


@pytest.mark.parametrize("field,value", [("id", "other-pick"), ("match_id", "other-fixture"), ("market", "Over 2.5"), ("selection", "2"),
    ("odds", 4.75), ("bookmaker", "Otra Casa"), ("home_team", "Otro Local"), ("away_team", "Otro Visitante")])
def test_stored_reference_cannot_cross_quote_identity_or_changed_visible_value(field, value):
    item, raw = stored_pick()
    raw[field] = value
    item["raw_json"] = json.dumps(raw)
    body = fmt.format_pick_message(item)
    assert "Fuente de cuota: sin registrar" in body
    assert "Hora de cuota: sin confirmar" in body
    assert "API-Football" not in body


@pytest.mark.parametrize("raw", ["{broken", "[]", "null", "x" * 5001])
def test_invalid_ambiguous_or_oversize_stored_record_remains_unconfirmed(raw):
    item, _ = stored_pick()
    item["raw_json"] = raw
    body = fmt.format_pick_message(item)
    assert "Fuente de cuota: sin registrar" in body and "Hora de cuota: sin confirmar" in body


def test_stored_metadata_needs_fixture_identity_not_only_matching_price():
    item, raw = stored_pick()
    raw.pop("match_id")
    item["raw_json"] = json.dumps(raw)
    body = fmt.format_pick_message(item)
    assert "API-Football" not in body and "Hora de cuota: sin confirmar" in body


def test_explicit_invalid_flat_quote_is_not_repaired_by_old_stored_alias():
    item, _ = stored_pick()
    item["odds_updated_at"] = "bad-clock"
    body = fmt.format_pick_message(item)
    assert "API-Football" not in body and "Hora de cuota: sin confirmar" in body


def test_changed_visible_selection_cannot_inherit_stale_raw_selection_reference():
    item, _ = stored_pick()
    item["_raw_selection"] = "1"
    item["selection"] = "Gana Visitante QA"
    body = fmt.format_pick_message(item)
    assert "API-Football" not in body and "Hora de cuota: sin confirmar" in body



@pytest.mark.parametrize("field", ["odds", "match_id", "odds_source"])
def test_duplicate_stored_keys_are_rejected_even_if_last_value_would_match(field):
    item, raw = stored_pick()
    encoded = json.dumps(raw)
    item["raw_json"] = encoded[:-1] + "," + json.dumps(field) + ":" + json.dumps(raw[field]) + "}"
    body = fmt.format_pick_message(item)
    assert "API-Football" not in body and "Hora de cuota: sin confirmar" in body


@pytest.mark.parametrize("scope,label", [("PROVIDER_QUOTE_TIME", "Hora de cuota del proveedor:"),
    ("RECORDED_QUOTE_TIME", "Hora de cuota registrada:"), ("RECEIPT_ONLY", "Recepción de cuota:")])
def test_stored_observation_keeps_existing_quote_clock_scope(scope, label):
    item, raw = stored_pick()
    raw.pop("odds_updated_at")
    raw.update({"quote_clock_scope": scope, "observed_at": "2025-01-01T12:00:00Z"})
    item["raw_json"] = json.dumps(raw)
    body = fmt.format_pick_message(item)
    assert label + " 01/01/2025 · 13:00:00 Madrid" in body
    if scope == "RECEIPT_ONLY":
        assert "hora del proveedor sin confirmar" in body


def test_stored_generic_source_and_clock_are_not_quote_evidence():
    item, raw = stored_pick()
    raw.pop("odds_source"); raw.pop("odds_updated_at")
    raw.update({"source": "GENERIC_ONLY_QA", "updated_at": "2025-01-01T12:00:00Z", "observed_at": "2025-01-01T12:00:00Z"})
    item["raw_json"] = json.dumps(raw)
    body = fmt.format_pick_message(item)
    assert "GENERIC_ONLY_QA" not in body and "Hora de cuota: sin confirmar" in body


@pytest.mark.parametrize("field", ["raw_json", "payload_json"])
def test_deep_stored_json_is_not_a_notification_crash_or_a_recovery_attempt(field):
    item, _ = stored_pick()
    item[field] = "[" * 1100 + "0" + "]" * 1100
    body = fmt.format_pick_message(item)
    if field == "raw_json":
        assert "Hora de cuota: sin confirmar" in body
    else:
        # A bad unrelated status payload must not erase the valid quote record.
        assert "Hora de cuota registrada: 01/01/2025 · 13:00:00 Madrid" in body
    assert "🔴 EN DIRECTO" not in fmt.format_live_alert_message(item)


def test_stored_quote_fields_cannot_fill_missing_core_legs_in_legacy_draft():
    item, _ = stored_pick()
    combi = {"status": "DRAFT", "picks": [{"selection": "1", "odds": 1.8, "raw_json": item["raw_json"]}] * 2}
    assert fmt.format_combi_message(combi) == ""



@pytest.mark.parametrize("normalized", [False, True])
def test_lossy_period_collision_cannot_cross_quote_identity(normalized):
    item, raw = stored_pick()
    raw.update({"market": "Totales", "selection": "Over 2.5 first half"})
    item.update({"market": "Totales", "raw_json": json.dumps(raw)})
    if normalized:
        item["_raw_selection"] = "Over 2.5 second half"
        item["selection"] = "Más de 2.5 goles"
    else:
        item.pop("_raw_selection")
        item["selection"] = "Over 2.5 second half"
    body = fmt.format_pick_message(item)
    assert "API-Football" not in body and "Hora de cuota: sin confirmar" in body


def test_unattested_selection_translation_cannot_authorize_stored_quote():
    item, _ = stored_pick()
    item.pop("_raw_selection")
    body = fmt.format_pick_message(item)
    assert "API-Football" not in body and "Hora de cuota: sin confirmar" in body


def test_lossy_translation_of_same_record_does_not_accredit_hidden_period():
    item, raw = stored_pick()
    raw.update({"market": "Totales", "selection": "Over 2.5 first half"})
    item.update({"market": "Totales", "_raw_selection": raw["selection"],
                 "selection": "Más de 2.5 goles", "raw_json": json.dumps(raw)})
    body = fmt.format_pick_message(item)
    assert "API-Football" not in body and "Hora de cuota: sin confirmar" in body



@pytest.mark.parametrize("original,visible", [
    *[(value, "Gana Local QA") for value in ("home", "local", "1", "winner home", "match winner home", "home win", "local win", "equipo local", "Local QA")],
    *[(value, "Gana Visitante QA") for value in ("away", "visitante", "2", "winner away", "match winner away", "away win", "visitante win", "equipo visitante", "Visitante QA")],
    *[(value, "Empate") for value in ("draw", "empate", "x", "tie")],
])
def test_complete_owned_1x2_localization_contract_keeps_stored_quote(original, visible):
    item, raw = stored_pick()
    raw["selection"] = original
    item.update({"selection": visible, "_raw_selection": original, "raw_json": json.dumps(raw)})
    body = fmt.format_pick_message(item)
    assert "Fuente de cuota: API-Football" in body
    assert "Hora de cuota registrada: 01/01/2025 · 13:00:00 Madrid" in body


def test_literal_other_market_keeps_metadata_without_a_localization_claim():
    item, raw = stored_pick()
    raw.update({"market": "Totales", "selection": "Over 2.5 first half"})
    item.update({"market": raw["market"], "selection": raw["selection"], "raw_json": json.dumps(raw)})
    item.pop("_raw_selection")
    body = fmt.format_pick_message(item)
    assert "Fuente de cuota: API-Football" in body and "13:00:00 Madrid" in body


def test_changed_visible_market_qualifier_cannot_reuse_stored_quote():
    item, raw = stored_pick()
    raw["market"] = "Totales primera parte"
    item.update({"market": "Totales segunda parte", "raw_json": json.dumps(raw)})
    body = fmt.format_pick_message(item)
    assert "API-Football" not in body and "Hora de cuota: sin confirmar" in body



@pytest.mark.parametrize("book", [0, False])
def test_invalid_primary_bookmaker_is_not_replaced_by_stored_alias(book):
    item, raw = stored_pick()
    raw.update({"bookmaker": book, "bookmaker_name": "Casa secundaria QA"})
    item.update({"bookmaker": book, "bookmaker_name": "Casa secundaria QA", "raw_json": json.dumps(raw)})
    body = fmt.format_pick_message(item)
    assert "API-Football" not in body and "Hora de cuota: sin confirmar" in body
