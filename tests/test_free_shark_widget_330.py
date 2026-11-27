"""All-ages FREE widget and mobile controls remain sports-only (#330).

These tests exercise the original Flask/Jinja components, not legal adulthood
verification or the SHARK answer service. No external requests are made.
"""
import pytest
from flask import render_template


@pytest.mark.parametrize("plan,paid", [("FREE", False), ("PRO", True), ("ELITE", True), ("ELITE+", True)])
def test_actual_widget_copy_and_quota_action_are_plan_scoped(app_module, plan, paid):
    with app_module.app.test_request_context("/app"):
        user = {"id": "synthetic-qa", "membership": plan, "role": plan}
        html = render_template("components/shark_workspace.html", data={},
                               current_user=user, is_admin_surface=False,
                               csrf_token=lambda: "qa-csrf")
    assert "data-assistant-upgrade" in html
    assert 'data-ns-assistant' in html
    assert ('href="/membresias"' in html) is paid
    if paid:
        assert "pronósticos o tus favoritos" in html
        assert "Consultar planes" in html
    else:
        assert 'href="/shark"' in html
        assert "resultados o tus favoritos" in html
        assert "Abrir SHARK deportivo" in html
        assert "Consultar planes" not in html


@pytest.mark.parametrize("plan,paid", [("FREE", False), ("PRO", True), ("ELITE", True), ("ELITE+", True)])
def test_mobile_header_never_promotes_betting_notifications_to_free(app_module, plan, paid):
    with app_module.app.test_request_context("/app"):
        nav = app_module.app.jinja_env.get_template("components/v933_navigation.html").make_module()
        html = str(nav.v933_client_navigation(plan))
    assert ('href="/telegram"' in html) is paid
    if paid:
        assert 'href="/membresias"' in html
    else:
        assert 'href="/favoritos"' in html
        assert 'href="/membresias"' not in html
