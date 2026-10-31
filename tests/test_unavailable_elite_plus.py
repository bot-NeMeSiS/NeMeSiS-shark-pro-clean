"""ELITE+ is a distinct future-ready tier; no unverified beta promises or payments."""
import pytest

from engines.membership_experience_engine import build_membership_value, build_membership_experience_matrix
from engines.client_screen_experience_engine import build_client_screen_state
from engines.visual_experience_engine import THEMES


@pytest.mark.parametrize("plan", ["ELITE+", "ELITE_PLUS"])
def test_elite_plus_is_not_silently_downgraded_in_client_experience(plan):
    value = build_membership_value(plan)
    assert value["label"] == "ELITE+"
    assert "cuando estén habilitadas" in value["summary"]
    screen = build_client_screen_state(plan=plan)
    assert screen["plan"] == "ELITE+"
    assert any(cta["label"] == "Ver picks" for cta in screen["primary_ctas"])


@pytest.mark.parametrize("plan", ["UNKNOWN", "invalid-user-input", ""])
def test_unknown_plan_stays_free_and_cannot_promise_paid_benefits(plan):
    assert build_membership_value(plan)["label"] == "FREE"
    screen = build_client_screen_state(plan=plan)
    assert screen["plan"] == "FREE"
    assert not any(cta["label"] == "Ver picks" for cta in screen["primary_ctas"])


def test_four_real_memberships_and_admin_are_presented():
    assert set(build_membership_experience_matrix()) == {
        "free", "pro", "elite", "elite_plus", "admin"
    }
    assert set(THEMES) == {"FREE", "PRO", "ELITE", "ELITE+", "ADMIN"}
    assert THEMES["ELITE+"]["name"] != THEMES["ADMIN"]["name"]


@pytest.mark.parametrize("plan,expected", [
    ("FREE", "FREE"), ("PRO", "PRO"), ("ELITE", "ELITE"),
    ("ELITE+", "ELITE+"), ("ELITE_PLUS", "ELITE+"),
    ("ADMIN", "ELITE"), ("garbage", "FREE"),
])
def test_navigation_badge_matches_supported_access(plan, expected):
    from jinja2 import Environment, FileSystemLoader
    from types import SimpleNamespace
    env = Environment(loader=FileSystemLoader("templates"))
    env.globals.update(ui=lambda value: value, request=SimpleNamespace(path="/app"))
    module = env.get_template("components/v933_navigation.html").module
    html = module.v933_client_navigation(plan)
    assert f"<strong>{expected}</strong>" in html
    if expected == "ELITE+":
        assert "is-eliteplus" in html


@pytest.mark.parametrize("plan", ["ELITE+", "ELITE_PLUS"])
def test_four_tier_value_ladder_highlights_elite_plus(plan, app_module):
    with app_module.app.test_request_context("/membresias"):
        html = app_module.app.jinja_env.get_template("components/v936_product.html").module.value_ladder(plan)
    assert 'is-eliteplus is-current' in html
    assert "Funciones beta solo cuando estén habilitadas" in html


def test_unknown_value_ladder_highlights_free(app_module):
    with app_module.app.test_request_context("/membresias"):
        html = app_module.app.jinja_env.get_template("components/v936_product.html").module.value_ladder("UNKNOWN")
    assert '<article class="is-current">' in html
    assert "is-eliteplus is-current" not in html


def test_checkout_remains_blocked_in_local_safe_mode(monkeypatch):
    from engines import stripe_payments_engine as billing
    monkeypatch.setenv("NEMESIS_LOCAL_SAFE_MODE", "true")
    monkeypatch.setattr(billing, "stripe_sdk", lambda: pytest.fail("Unexpected SDK access"))
    result = billing.create_checkout_session("unused", {"id": "local-only"}, "ELITE+")
    assert result["status"] == "LOCAL_SAFE_BLOCKED"
    assert result["external_calls"] == result["membership_changes"] == 0
