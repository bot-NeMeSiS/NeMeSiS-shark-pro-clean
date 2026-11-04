"""SHARK presentation boundary for all-ages sports versus paid analysis (#330).

Synthetic Jinja rendering only, without provider calls, payment flows or actual
adulthood checks. The server/API age gate is a separate launch blocker.
"""
import pytest

from test_home_canonical_consistency import component_env


@pytest.mark.parametrize("plan,expected_premium", [
    (None, False), ("FREE", False), ("PRO", True), ("ELITE", True),
])
def test_shark_free_sports_and_paid_menu_are_separate(plan, expected_premium):
    env = component_env("/shark")
    user = {"id": "synthetic-qa", "membership": plan, "role": plan} if plan else None
    data = {
        "shark_assistant": {"generation_enabled": False},
        "sports_metrics": {"matches_available": 2, "picks_ready": 2},
        "v925_picks": {"picks": []},
        "shark_usage": {"login_required": True},
    }
    html = env.get_template("shark.html").render(
        data=data, current_user=user, csrf_token=lambda: "synthetic-qa-csrf"
    )
    if expected_premium:
        assert 'href="/picks"' in html
        assert 'href="/membresias"' in html
        assert 'data-free-informational="true"' not in html
    else:
        assert 'data-free-informational="true"' in html
        assert 'href="/picks"' not in html
        assert 'href="/membresias"' not in html
        assert 'v933-shark-free-sports' in html
        assert "SHARK deportivo" in html
        assert "Cuotas" not in html
        assert "Pronósticos completos" not in html
        assert 'name="pick_id"' not in html
        assert 'href="/competiciones"' in html
        assert 'href="/calendario?lane=finished"' in html


def test_shark_template_contains_no_hidden_css_only_age_gate():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "templates/shark.html").read_text(encoding="utf-8")
    assert "{% if paid_product_plan %}" in source
    assert "{% else %}" in source
    assert "data-free-informational" in source
