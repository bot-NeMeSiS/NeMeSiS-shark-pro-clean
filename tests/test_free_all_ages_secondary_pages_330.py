"""Regression for the legacy account directory and profile (#330).

Presentation tests only. They do not certify adulthood, route-level
authorization, provider terms, or readiness to release premium billing.
"""
from pathlib import Path

import pytest
from flask import render_template

from test_home_canonical_consistency import component_env

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_GENERAL_LINKS = (
    '/picks', '/combinadas', '/mercados', '/historico',
    '/track-record', '/membresias', '/telegram',
)


@pytest.mark.parametrize('tier', ['FREE', 'PRO'])
def test_legacy_client_directory_split_is_rendered_not_css_hidden(app_module, tier):
    user = {'id': 'qa-navigation-only', 'name': 'QA', 'membership': tier, 'role': tier}
    env = component_env('/menu')
    markup = env.get_template('client_menu.html').render(
        items=app_module.v566_client_menu_items(), current_user=user,
    )
    if tier == 'FREE':
        for path in FORBIDDEN_GENERAL_LINKS:
            assert f'href="{path}"' not in markup, path
        assert 'Pronósticos SHARK' not in markup
        assert 'Cuota, unidades, riesgo' not in markup
        assert 'href="/competiciones"' in markup
        assert 'href="/calendario?lane=finished"' in markup
        assert 'href="/shark"' in markup
        assert '<h2>Pronósticos</h2>' not in markup
    else:
        for path in ('/picks', '/combinadas', '/mercados', '/track-record'):
            assert f'href="{path}"' in markup
        assert 'Pronósticos SHARK' in markup


@pytest.mark.parametrize('tier', ['FREE', 'PRO'])
def test_profile_actions_do_not_upsell_betting_to_free(app_module, tier):
    user = {'id': 'qa-profile-only', 'name': 'QA', 'membership': tier, 'role': tier}
    data = {
        'session_user': user, 'favorites': [], 'client_activity': [],
        'activity_snapshot': {'items': []}, 'telegram_state': {'linked': False},
    }
    with app_module.app.test_request_context('/perfil'):
        markup = render_template('profile.html', data=data, current_user=user)
    content = markup.split('data-v933-template="profile"', 1)[1]
    if tier == 'FREE':
        assert 'Tu espacio FREE' in content
        for path in ('/combinadas#combinadas-guardadas', '/membresias', '/telegram'):
            assert f'href="{path}"' not in content, path
        assert 'Mis combinadas' not in content
    else:
        assert 'Mis combinadas' in content
        assert 'href="/combinadas#combinadas-guardadas"' in content
        assert 'href="/membresias"' in content



def test_menu_source_uses_canonical_sport_routes(app_module):
    entries = {item["title"]: item["href"] for item in app_module.v566_client_menu_items()}
    assert entries["Partidos de hoy"] == "/calendario?lane=today"
    assert entries["Directo ahora"] == "/directo"

def test_free_page_only_uses_explicit_whitelisted_sports_destinations():
    source = (ROOT / 'templates/client_menu.html').read_text(encoding='utf-8')
    assert "all_items|selectattr('href', 'in', free_allowed_hrefs)|list" in source
    assert "visible_items|groupby('group')" in source
    assert 'paid_product_plan' in source
