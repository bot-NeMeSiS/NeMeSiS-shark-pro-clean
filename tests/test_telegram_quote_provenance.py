"""Quote metadata stays bound to its own stored observation, never a match clock."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from engines import telegram_message_formatter as fmt
from engines.telegram_autonomous_delivery_engine import _pick_message


def pick(n=1, **extra):
    return {"match_id": f"qa-quote-{n}", "sport_key": "soccer",
            "home_team": f"Local {n}", "away_team": f"Visitante {n}",
            "competition_name": "Liga QA", "kickoff_iso": "2025-07-01T18:00:00+00:00",
            "market": "Resultado final", "selection": f"Gana Local {n}", "odds": 1.8,
            **extra}


def test_pick_uses_own_recorded_quote_time_and_distinguishes_match_update():
    item = pick(odds_source="API-Football", bookmaker="Casa & Norte",
                odds_updated_at="2025-07-01T10:11:12Z", last_synced_at="2025-07-01T11:22:33Z")
    body = fmt.format_pick_message(item)
    assert "Casa: Casa & Norte · Fuente de cuota: API-Football" in body
    assert "Hora de cuota registrada: 01/07/2025 · 12:11:12 Madrid" in body
    assert "Hora de cuota registrada: 01/07/2025 · 13:22:33" not in body
    assert "cuota vigente" not in body.lower()


@pytest.mark.parametrize("field", ["updated_at", "provider_updated_at", "last_synced_at", "created_at", "published_at", "observed_at"])
def test_generic_clocks_do_not_become_quote_clock(field):
    body = fmt.format_pick_message(pick(**{field: "2025-01-01T12:00:00Z", "source": "GENERIC_SOURCE_QA"}))
    assert "Hora de cuota: sin confirmar" in body
    assert "Fuente de cuota: sin registrar" in body
    assert "GENERIC_SOURCE_QA" not in body
    assert "Hora de cuota registrada:" not in body


@pytest.mark.parametrize("scope_field", ["quote_clock_scope", "clock_scope"])
@pytest.mark.parametrize("scope,label", [
    ("PROVIDER_QUOTE_TIME", "Hora de cuota del proveedor:"),
    ("RECORDED_QUOTE_TIME", "Hora de cuota registrada:"),
    ("RECEIPT_ONLY", "Recepción de cuota:")])
def test_scoped_observation_has_its_actual_meaning(scope_field, scope, label):
    body = fmt.format_pick_message(pick(**{scope_field: scope, "observed_at": "2025-01-01T12:00:00Z"}))
    assert label + " 01/01/2025 · 13:00:00 Madrid" in body
    if scope == "RECEIPT_ONLY":
        assert "hora del proveedor sin confirmar" in body
        assert "Hora de cuota del proveedor:" not in body


@pytest.mark.parametrize("clock", [None, "not-a-clock", "2025-01-01T12:00:00", True])
def test_missing_invalid_or_naive_own_clock_does_not_fall_back(clock):
    body = fmt.format_pick_message(pick(odds_updated_at=clock, updated_at="2025-01-01T12:00:00Z"))
    assert "Hora de cuota: sin confirmar" in body
    assert "Hora de cuota registrada:" not in body


def test_future_quote_clock_is_not_confirmed_or_replaced_by_now():
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    body = fmt.format_pick_message(pick(odds_updated_at=future))
    assert "Hora de cuota: por confirmar" in body and future not in body


@pytest.mark.parametrize("scope", ["MATCH_TIME", "INVALID_PROVIDER_PAYLOAD", {"scope": "PROVIDER_QUOTE_TIME"}])
def test_unknown_scope_cannot_be_repaired_with_another_clock(scope):
    body = fmt.format_pick_message(pick(quote_clock_scope=scope, observed_at="2025-01-01T12:00:00Z",
                                        odds_updated_at="2025-01-01T12:00:00Z"))
    assert "Hora de cuota: sin confirmar" in body


def test_invalid_scoped_clock_cannot_be_repaired_with_fresh_alias():
    body = fmt.format_pick_message(pick(quote_clock_scope="PROVIDER_QUOTE_TIME", observed_at="bad-clock",
                                        odds_updated_at="2025-01-01T12:00:00Z"))
    assert "Hora de cuota: sin confirmar" in body


@pytest.mark.parametrize("source", ["https://qa.example/status?token=qa-only-token", {"token": "qa-only-token"}, "qa-only-token" * 10])
def test_source_labels_do_not_dump_urls_objects_or_overlong_payloads(source):
    body = fmt.format_pick_message(pick(odds_source=source, bookmaker=source))
    assert "Fuente de cuota: sin registrar" in body
    assert "qa-only-token" not in body


def test_combi_groups_identical_leg_metadata_without_losing_nine_selections_or_total():
    rows = [pick(n, odds_source="API-Football", bookmaker="Casa QA", odds_updated_at="2025-07-01T10:11:12Z") for n in range(1, 10)]
    original = deepcopy(rows)
    body = fmt.format_combi_message({"picks": rows, "total_odds": 9.9})
    assert body and "Partidos: 9" in body and "Cuota total registrada: 9.9" in body
    assert all(row["selection"] in body for row in rows)
    assert body.count("Fuente de cuota: API-Football") == 1
    assert body.count("Hora de cuota registrada: 01/07/2025 · 12:11:12 Madrid") == 1
    assert "Total · Fuente de cuota: sin registrar" in body
    assert rows == original


def test_combi_does_not_borrow_metadata_between_legs_or_from_legs_for_joint_quote():
    rows = [pick(1, odds_source="Fuente A", odds_updated_at="2025-01-01T10:00:00Z"), pick(2)]
    body = fmt.format_combi_message({"picks": rows, "total_odds": 3.24})
    assert "Cuotas de selecciones 1" in body
    assert "Cuotas de selecciones 2" in body
    assert "Total · Fuente de cuota: sin registrar" in body
    assert "Total · Hora de cuota: sin confirmar" in body
    assert body.count("Fuente de cuota: Fuente A") == 1


def test_total_quote_metadata_is_its_own_not_a_leg_price_or_time():
    rows = [pick(1, odds_source="Fuente A", odds_updated_at="2025-07-01T10:00:00Z"), pick(2)]
    body = fmt.format_combi_message({"picks": rows, "total_odds": 3.24,
        "odds_source": "Registro total QA", "odds_updated_at": "2025-01-01T09:00:00Z"})
    assert "Total · Fuente de cuota: Registro total QA" in body
    assert "Total · Hora de cuota registrada: 01/01/2025 · 10:00:00 Madrid" in body
    assert "Cuota total registrada: 3.24" in body


def test_actual_autonomous_html_keeps_quote_metadata_escaped_and_free_preview_private():
    item = pick(odds_source="API-Football", bookmaker="Casa & Norte", odds_updated_at="2025-07-01T10:11:12Z")
    _, html = _pick_message(item)
    assert "Casa &amp; Norte" in html and "12:11:12 Madrid" in html
    preview = fmt.format_membership_pick_message(item, membership="FREE")
    assert "API-Football" not in preview and "Casa & Norte" not in preview and "12:11:12" not in preview


def test_actual_combi_transport_uses_same_quote_metadata_snapshot(app_module, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "qa-disposable-not-a-real-token")
    item = {"picks": [pick(1, odds_source="API-Football", odds_updated_at="2025-01-01T12:00:00Z"), pick(2)], "total_odds": 3.24}
    original = deepcopy(item)
    sent = []
    monkeypatch.setattr(app_module, "telegram_send_text_with_fallback", lambda _url, data: sent.append(data) or {"sent": True})
    result = app_module.telegram_send_http("qa-disposable", "OLD_BODY", message_type="combi_alert", payload={"visual_card_payload": {"combi": item}})
    assert result["sent"] and len(sent) == 1
    assert "Fuente de cuota: API-Football" in sent[0]["text"] and "13:00:00 Madrid" in sent[0]["text"]
    assert item == original


def test_quote_metadata_does_not_repair_incomplete_legacy_draft():
    item = {"status": "DRAFT", "picks": [{"selection": "Local", "odds": 1.8, "odds_source": "API-Football",
        "odds_updated_at": "2025-01-01T12:00:00Z"}] * 2}
    assert fmt.format_combi_message(item) == ""



def test_recorded_quote_field_does_not_need_generic_clock_fallback():
    body = fmt.format_pick_message(pick(odds_recorded_at="2025-01-01T12:00:00Z"))
    assert "Hora de cuota registrada: 01/01/2025 · 13:00:00 Madrid" in body


def test_receipt_field_is_displayed_only_with_explicit_receipt_scope():
    body = fmt.format_pick_message(pick(clock_scope="RECEIPT_ONLY", received_at="2025-01-01T12:00:00Z",
                                       created_at="2025-07-01T10:11:12Z"))
    assert "Recepción de cuota: 01/01/2025 · 13:00:00 Madrid" in body
    assert "hora del proveedor sin confirmar" in body and "12:11:12" not in body


def test_missing_quote_value_does_not_publish_unbound_provenance():
    body = fmt.format_pick_message(pick(odds=None, odds_source="UNBOUND_SOURCE_QA", bookmaker="UNBOUND_BOOK_QA",
                                       odds_updated_at="2025-01-01T12:00:00Z"))
    assert "UNBOUND_SOURCE_QA" not in body and "UNBOUND_BOOK_QA" not in body
    assert "Hora de cuota: sin confirmar" in body



def test_blank_legacy_bookmaker_keeps_its_explicit_nominal_alias():
    body = fmt.format_pick_message(pick(bookmaker="", bookmaker_name="Casa nominal QA"))
    assert "Casa: Casa nominal QA" in body
    assert "Fuente de cuota: sin registrar" in body and "Hora de cuota: sin confirmar" in body
