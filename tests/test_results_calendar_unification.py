"""Regression coverage for the unified Results/Calendar center and canonical match state."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_results_is_the_canonical_client_entry_and_calendar_is_internal_view():
    contract = (ROOT / "templates/components/navigation_contracts.html").read_text(encoding="utf-8")
    calendar = (ROOT / "templates/calendar.html").read_text(encoding="utf-8")
    assert "('Resultados','/calendario?lane=finished','history')" in contract
    assert "('Resultados y calendario','/admin/matches','matches')" in contract
    assert "data-results-calendar-tabs" in calendar
    assert "'label':'Resultados','href':'/calendario?lane=finished'" in calendar
    assert "'label':'Calendario','href':'/calendario?lane=today'" in calendar
    assert "'label':'Próximos','href':'/calendario?lane=week'" in calendar
    assert "'label':'Con pronóstico','href':'/calendario?lane=with_pick'" in calendar


def test_results_query_link_remains_active_on_the_canonical_route(app_module):
    template = app_module.app.jinja_env.from_string(
        "{% import 'components/navigation_contracts.html' as nav %}"
        "{{ nav.is_active('/calendario?lane=finished', '/calendario', 'client') }}"
    )
    assert template.render() == "1"


def test_finished_canonical_state_overrides_stale_live_presentation_copy(app_module):
    template = app_module.app.jinja_env.from_string(
        "{% from 'components/v933_ui.html' import canonical_match_state with context %}"
        "{{ canonical_match_state(match, true) }}"
    )
    match = {
        "client_status_label": "En directo",
        "status": "LIVE",
        "v935_lifecycle": "FINISHED",
        "is_live": False,
        "is_finished": True,
        "status_info": {"key": "FINISHED", "is_live": False, "is_finished": True},
    }
    with app_module.app.test_request_context("/calendario?lane=finished"):
        html = template.render(match=match)
    assert "Finalizado" in html
    assert "En directo" not in html


def test_match_card_hides_live_minute_once_match_is_finished():
    source = (ROOT / "templates/components/v933_ui.html").read_text(encoding="utf-8")
    assert "canonical_match_state(match, complete)" in source
    assert "canonical_live and canonical_status in ['LIVE','HALFTIME']" in source
    assert "minute is not none" in source


def test_admin_realtime_reuses_the_same_canonical_state_component():
    admin = (ROOT / "templates/admin_realtime_center.html").read_text(encoding="utf-8")
    assert "canonical_match_state" in admin
    assert "canonical_match_state(match, true)" in admin
    assert "status_chip(match.get('status_label')" not in admin


def test_sports_lifecycle_uses_canonical_spanish_routes():
    source = (ROOT / "templates/components/v937_sports_lifecycle.html").read_text(encoding="utf-8")
    assert 'href="/calendario?lane=today"' in source
    assert 'href="/calendario?lane=finished"' in source
    assert 'href="/directo?f=live"' in source
    assert 'href="/calendar?lane=' not in source
    assert 'href="/live?f=' not in source
