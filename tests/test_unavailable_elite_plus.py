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
