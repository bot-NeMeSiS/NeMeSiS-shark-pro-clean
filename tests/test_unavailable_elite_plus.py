from engines.membership_experience_engine import build_membership_value, build_membership_experience_matrix
from engines.client_screen_experience_engine import build_client_screen_state
from engines.visual_experience_engine import THEMES
import pytest

@pytest.mark.parametrize("plan", ["ELITE+", "ELITE_PLUS", "eliteplus", "UNKNOWN"])
def test_unsupported_plan_cannot_promise_paid_benefits(plan):
    assert build_membership_value(plan)["label"] == "FREE"
    screen = build_client_screen_state(plan=plan)
    assert screen["plan"] == "FREE"
    assert not any(cta["label"] == "Ver picks" for cta in screen["primary_ctas"])

def test_only_real_memberships_and_admin_are_presented():
    assert set(build_membership_experience_matrix()) == {"free", "pro", "elite", "admin"}
    assert set(THEMES) == {"FREE", "PRO", "ELITE", "ADMIN"}

@pytest.mark.parametrize("plan", ["ELITE+", "ELITE_PLUS", "ADMIN", "ELITE"])
def test_navigation_badge_matches_supported_access(plan):
    from jinja2 import Environment, FileSystemLoader
    from types import SimpleNamespace
    env = Environment(loader=FileSystemLoader("templates"))
    env.globals.update(ui=lambda text: text, request=SimpleNamespace(path="/app"))
    module = env.get_template("components/v933_navigation.html").module
    html = module.v933_client_navigation(plan)
    expected = "ELITE" if plan in {"ADMIN", "ELITE"} else "FREE"
    assert f"<strong>{expected}</strong>" in html
    assert "<strong>ELITE+" not in html

def test_checkout_remains_blocked_in_local_safe_mode(monkeypatch):
    from engines import stripe_payments_engine as billing
    monkeypatch.setenv("NEMESIS_LOCAL_SAFE_MODE", "true")
    monkeypatch.setattr(billing, "stripe_sdk", lambda: pytest.fail("Unexpected SDK access"))
    result = billing.create_checkout_session("unused", {"id": "local-only"}, "PRO")
    assert result["status"] == "LOCAL_SAFE_BLOCKED"
    assert result["external_calls"] == result["membership_changes"] == 0

@pytest.mark.parametrize("plan", ["ELITE+", "ELITE_PLUS"])
def test_unsupported_value_ladder_highlights_free(plan, app_module):
    with app_module.app.test_request_context("/membresias"):
        html = app_module.app.jinja_env.get_template("components/v936_product.html").module.value_ladder(plan)
    assert '<article class="is-current">' in html
    assert 'is-elite is-current' not in html
