from datetime import timedelta
import sqlite3

import pytest

from engines import ads_monetization_engine as ads


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "ads.db"
    monkeypatch.setattr(ads, "database_path", lambda: str(path))
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    ads.ensure_schema(str(path))
    return str(path)


def valid_form(**overrides):
    data = {
        "advertiser_name": "Ana Publicidad",
        "company_name": "Marca Deportiva SL",
        "contact_email": "ads@example.com",
        "title": "Equipamiento para jugar mejor",
        "body": "Descubre equipamiento deportivo y prepara tu próximo partido.",
        "destination_url": "https://example.com/campana",
        "package_days": "30",
    }
    data.update(overrides)
    return data


def test_prices_and_https_validation():
    assert ads.PACKAGES[7]["amount_cents"] == 4900
    assert ads.PACKAGES[30]["amount_cents"] == 14900
    assert ads.PACKAGES[90]["amount_cents"] == 34900
    assert ads.validate_https_url("http://example.com") is None
    assert ads.validate_https_url("https://user:pass@example.com") is None
    assert ads.validate_https_url("https://192.168.1.1/admin") is None
    assert ads.validate_https_url("https://printer.local") is None
    assert ads.validate_https_url("https://example.com/path") == "https://example.com/path"


def test_rejects_invalid_creative_and_package():
    data, error = ads.validate_campaign_form(valid_form(destination_url="javascript:alert(1)"))
    assert data is None and error
    data, error = ads.validate_campaign_form(valid_form(package_days="999"))
    assert data is None and error


def test_campaign_waits_for_payment_configuration_and_review(db):
    data, error = ads.validate_campaign_form(valid_form())
    assert error is None
    campaign_id = ads.create_campaign(data, True, db)
    campaign = ads.campaign_by_id(campaign_id, db)
    assert campaign["status"] == "awaiting_payment_setup"
    assert campaign["impressions"] == campaign["clicks"] == 0


def test_unpaid_campaign_cannot_activate(db):
    data, _ = ads.validate_campaign_form(valid_form())
    campaign_id = ads.create_campaign(data, True, db)
    ok, message = ads.review_campaign(campaign_id, "activate", db)
    assert not ok
    assert ads.campaign_by_id(campaign_id, db)["status"] == "awaiting_payment_setup"


def test_paid_campaign_needs_review_before_delivery(db):
    data, _ = ads.validate_campaign_form(valid_form())
    campaign_id = ads.create_campaign(data, True, db)
    with ads.connect(db) as conn:
        conn.execute("UPDATE ad_campaigns SET status='pending_payment', stripe_session_id='cs_test_1' WHERE id=?", (campaign_id,))
    assert ads.mark_paid(campaign_id, "cs_wrong", path=db) is False
    assert ads.mark_paid(campaign_id, "cs_test_1", "pi_test_1", path=db) is True
    assert ads.campaign_by_id(campaign_id, db)["status"] == "paid_pending_review"
    assert ads.active_campaign(db) is None
    ok, _ = ads.review_campaign(campaign_id, "activate", db)
    assert ok
    assert ads.active_campaign(db)["id"] == campaign_id


def test_event_counters_only_change_for_active_campaign(db):
    data, _ = ads.validate_campaign_form(valid_form())
    campaign_id = ads.create_campaign(data, True, db)
    assert ads.record_event(campaign_id, "impressions", db) is False
    with ads.connect(db) as conn:
        conn.execute("UPDATE ad_campaigns SET status='active', starts_at=?, ends_at=? WHERE id=?", (
            ads.stamp(ads.utc_now() - timedelta(minutes=1)),
            ads.stamp(ads.utc_now() + timedelta(days=1)), campaign_id))
    assert ads.record_event(campaign_id, "impressions", db) is True
    assert ads.record_event(campaign_id, "clicks", db) is True
    campaign = ads.campaign_by_id(campaign_id, db)
    assert campaign["impressions"] == campaign["clicks"] == 1


def test_payment_must_match_campaign_checkout_session(db):
    data, _ = ads.validate_campaign_form(valid_form())
    campaign_id = ads.create_campaign(data, True, db)
    with ads.connect(db) as conn:
        conn.execute("UPDATE ad_campaigns SET status='pending_payment', stripe_session_id='cs_test_1' WHERE id=?", (campaign_id,))
    assert not ads.mark_paid(campaign_id, "cs_other", path=db)
    assert ads.campaign_by_id(campaign_id, db)["status"] == "pending_payment"

def test_rejected_paid_campaign_requires_explicit_refund_state(db):
    data, _ = ads.validate_campaign_form(valid_form())
    campaign_id = ads.create_campaign(data, True, db)
    with ads.connect(db) as conn:
        conn.execute("UPDATE ad_campaigns SET status='pending_payment', stripe_session_id='cs_test_refund' WHERE id=?", (campaign_id,))
    assert ads.mark_paid(campaign_id, "cs_test_refund", path=db)
    ok, _ = ads.review_campaign(campaign_id, "reject", db)
    assert ok
    assert ads.campaign_by_id(campaign_id, db)["status"] == "refund_required"
    ok, _ = ads.review_campaign(campaign_id, "mark_refunded", db)
    assert ok
    assert ads.campaign_by_id(campaign_id, db)["status"] == "refunded"
