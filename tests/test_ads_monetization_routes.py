from datetime import timedelta
from pathlib import Path

import pytest
from flask import Flask
from jinja2 import DictLoader

from blueprints.admin_productivity import create_admin_productivity_blueprint
from engines import ads_monetization_engine as ads


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "ads-routes.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    app = Flask(__name__)
    app.secret_key = "synthetic-test-only"
    app.jinja_loader = DictLoader({
        "advertiser_portal.html": "{{ ad_message or '' }}",
        "admin_ads.html": "{{ campaigns|length }}|{{ revenue_cents }}|{{ impressions }}|{{ clicks }}",
    })
    app.register_blueprint(create_admin_productivity_blueprint(lambda: True))
    app.testing = True
    return app.test_client(), str(db_path)


def form_data(**overrides):
    data = {
        "advertiser_name": "Ana Publicidad",
        "company_name": "Marca Deportiva SL",
        "contact_email": "ads@example.com",
        "title": "Equipamiento para jugar mejor",
        "body": "Descubre equipamiento deportivo y prepara tu próximo partido.",
        "destination_url": "https://example.com/campana",
        "package_days": "30",
        "accept_terms": "yes",
    }
    data.update(overrides)
    return data


def test_portal_saves_lead_without_claiming_payment(client):
    c, db_path = client
    response = c.post("/publicidad", data=form_data())
    assert response.status_code == 200
    assert b"no se ha realizado ning" in response.data
    campaign = ads.list_campaigns(db_path)[0]
    assert campaign["status"] == "awaiting_payment_setup"
    assert campaign["stripe_session_id"] is None


def test_admin_ads_is_private(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "private.db"))
    app = Flask(__name__)
    app.secret_key = "synthetic-test-only"
    app.jinja_loader = DictLoader({"admin_ads.html": "admin"})
    app.register_blueprint(create_admin_productivity_blueprint(lambda: False))
    assert app.test_client().get("/admin/ads").status_code == 403


def test_active_ad_counts_once_per_session_and_redirects_https(client):
    c, db_path = client
    data, error = ads.validate_campaign_form(form_data())
    assert error is None
    campaign_id = ads.create_campaign(data, True, db_path)
    with ads.connect(db_path) as conn:
        conn.execute(
            "UPDATE ad_campaigns SET status='active', starts_at=?, ends_at=? WHERE id=?",
            (ads.stamp(ads.utc_now() - timedelta(minutes=1)),
             ads.stamp(ads.utc_now() + timedelta(days=1)), campaign_id),
        )
    assert c.get(f"/ads/impression/{campaign_id}").status_code == 204
    assert c.get(f"/ads/impression/{campaign_id}").status_code == 204
    response = c.get(f"/ads/click/{campaign_id}")
    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com/campana"
    c.get(f"/ads/click/{campaign_id}")
    campaign = ads.campaign_by_id(campaign_id, db_path)
    assert campaign["impressions"] == 1
    assert campaign["clicks"] == 1


def test_payment_return_fails_closed_without_stripe(client):
    c, _ = client
    response = c.get("/publicidad/pago-completado?session_id=cs_test_fake")
    assert response.status_code == 400
    assert b"No hemos podido verificar el pago" in response.data
