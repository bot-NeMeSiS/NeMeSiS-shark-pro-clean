"""Membership display uses local configuration truth without executing payments.

The view runs in a real request context. The actual membership template and
shared macros render with a minimal base, isolating this contract from unrelated
navigation and sports context. All users, keys, prices and databases are synthetic.
"""
from html.parser import HTMLParser
from pathlib import Path
import socket

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
import pytest

from engines import stripe_payments_engine as payments


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_payment_configuration(monkeypatch):
    for key in (
        "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_PRO",
        "STRIPE_PRICE_ELITE", "APP_PUBLIC_URL", "PUBLIC_BASE_URL",
        "RENDER_EXTERNAL_URL", "PAYMENTS_MODE", "PAYMENTS_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(payments, "stripe_sdk", lambda: object())

    def forbidden(*_args, **_kwargs):
        pytest.fail("Membership configuration reads must not execute network or payment operations")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(payments, "ensure_stripe_schema", forbidden)
    monkeypatch.setattr(payments, "create_checkout_session", forbidden)
    monkeypatch.setattr(payments, "create_customer_portal_session", forbidden)


def configure(monkeypatch, environment="test", enabled=True):
    # These are intentionally synthetic, and never sent to Stripe.
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_" + environment + "_synthetic_local_qa")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_synthetic_only")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_synthetic_pro")
    monkeypatch.setenv("STRIPE_PRICE_ELITE", "price_synthetic_elite")
    monkeypatch.setenv("APP_PUBLIC_URL", "https://membership-qa.invalid")
    monkeypatch.setenv("PAYMENTS_ENABLED", "true" if enabled else "false")


@pytest.mark.parametrize("kind,environment", [
    ("sk", "test"), ("sk", "live"), ("rk", "test"), ("rk", "live"),
])
def test_runtime_exposes_only_the_key_environment(monkeypatch, kind, environment):
    secret = kind + "_" + environment + "_synthetic_local_qa"
    monkeypatch.setenv("STRIPE_SECRET_KEY", secret)
    monkeypatch.setenv("PAYMENTS_MODE", "stripe_real")
    status = payments.stripe_runtime_status("")
    assert status["stripe_environment"] == environment
    assert secret not in repr(status)
    assert status["summary"] == {}


@pytest.mark.parametrize("secret,expected", [("", "unconfigured"), ("unrecognized", "unknown")])
def test_missing_or_unknown_key_never_claims_a_live_environment(monkeypatch, secret, expected):
    monkeypatch.setenv("STRIPE_SECRET_KEY", secret)
    assert payments.stripe_runtime_status("")["stripe_environment"] == expected


class Controls(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms, self.links, self.inputs = [], [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.forms.append(attrs)
        elif tag == "a":
            self.links.append(attrs)
        elif tag == "input":
            self.inputs.append(attrs)


def render_membership(app_module, monkeypatch, tmp_path, user=None, status_override=None):
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "absent.sqlite"))
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", lambda *_a, **_kw: ({}, {}))
    monkeypatch.setattr(app_module, "v566_membership_ui", lambda _user: {})
    monkeypatch.setattr(app_module, "_v931_provider_context", lambda _summary: {})
    monkeypatch.setattr(app_module, "get_v935_customer_trust_context", lambda _summary: {})
    monkeypatch.setattr(app_module, "legal_compliance_payload", lambda: {"version": "SYNTHETIC_LEGAL"})
    monkeypatch.setattr(app_module, "checkout_legal_checklist", lambda: [{"key": "accept_terms", "label": "Acepto las condiciones"}])
    anonymous_reads = []

    def read_status(path=""):
        anonymous_reads.append(path)
        assert path == "", "Anonymous membership must not read billing records"
        return payments.stripe_runtime_status("") if status_override is None else status_override

    monkeypatch.setattr(app_module, "stripe_runtime_status", read_status)
    monkeypatch.setattr(app_module, "client_payments_context", payments.client_payments_context)
    env = Environment(loader=ChoiceLoader([
        DictLoader({"base.html": "{% block content %}{% endblock %}"}),
        FileSystemLoader(ROOT / "templates"),
    ]), autoescape=True)
    env.filters.update(app_module.app.jinja_env.filters)
    env.globals.update(ui=lambda value: value, ui_price_label=lambda value: value,
                       csrf_token=lambda: "synthetic-csrf", current_user=user)
    captured = {}

    def render(template, **context):
        captured.update(context["data"]["payments_client"])
        return env.get_template(template).render(**context)

    monkeypatch.setattr(app_module, "render_template", render)
    with app_module.app.test_request_context("/membresias"):
        html = app_module.membership_page()
    assert not (tmp_path / "absent.sqlite").exists()
    return html, captured, anonymous_reads


@pytest.mark.parametrize("environment", ["test", "live"])
def test_guest_with_configured_payments_gets_login_and_correct_environment(
    app_module, monkeypatch, tmp_path, environment,
):
    configure(monkeypatch, environment)
    html, pay, reads = render_membership(app_module, monkeypatch, tmp_path)
    controls = Controls(html)
    assert pay["checkout_configured"] is True
    assert pay["checkout_ready"] is False
    assert reads == [""]
    assert controls.forms == []
    assert {"/comprar/PRO", "/comprar/ELITE"} <= {a.get("href") for a in controls.links}
    assert "Inicia sesión" in html
    assert "Pago pendiente de configuración" not in html
    assert "Pago configurado" not in html  # A key mode does not certify webhooks or successful payments.
    assert ("Modo de pruebas de pago" in html) == (environment == "test")
    assert ("No se realizarán cobros reales" in html) == (environment == "test")
    assert "synthetic_local_qa" not in html


@pytest.mark.parametrize("state", ["missing_key", "missing_webhook", "disabled", "missing_price", "unavailable"])
def test_incomplete_or_unavailable_payment_state_has_no_purchase_control(
    app_module, monkeypatch, tmp_path, state,
):
    configure(monkeypatch)
    override = None
    if state == "missing_key":
        monkeypatch.delenv("STRIPE_SECRET_KEY")
    elif state == "missing_webhook":
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET")
    elif state == "disabled":
        monkeypatch.setenv("PAYMENTS_ENABLED", "false")
    elif state == "missing_price":
        monkeypatch.delenv("STRIPE_PRICE_PRO")
    else:
        override = {}
    html, pay, _ = render_membership(app_module, monkeypatch, tmp_path, status_override=override)
    controls = Controls(html)
    assert pay["checkout_configured"] is False
    assert not controls.forms
    assert not [a for a in controls.links if (a.get("href") or "").startswith("/comprar/")]
    expected = "Estado del pago temporalmente no disponible" if state == "unavailable" else "Pago pendiente de configuración"
    assert expected in html
    assert "Modo de pruebas de pago" not in html


@pytest.mark.parametrize("membership,expected_plans", [("FREE", {"PRO", "ELITE"}), ("PRO", {"ELITE"})])
def test_signed_in_checkout_keeps_csrf_consent_and_current_plan_gates(
    app_module, monkeypatch, tmp_path, membership, expected_plans,
):
    configure(monkeypatch)
    user = {"id": "synthetic-user", "membership": membership, "role": membership}
    html, pay, reads = render_membership(app_module, monkeypatch, tmp_path, user=user)
    controls = Controls(html)
    assert reads == []
    assert pay["checkout_ready"] is True and pay["checkout_configured"] is True
    assert {form["action"].rsplit("/", 1)[1] for form in controls.forms} == expected_plans
    assert all(form["method"] == "post" for form in controls.forms)
    assert len([item for item in controls.inputs if item.get("name") == "csrf_token" and item.get("value") == "synthetic-csrf"]) == len(expected_plans)
    assert len([item for item in controls.inputs if item.get("name") == "accept_terms" and "required" in item]) == len(expected_plans)
    assert "Modo de pruebas de pago" in html
    assert "Inicia sesión" not in html
