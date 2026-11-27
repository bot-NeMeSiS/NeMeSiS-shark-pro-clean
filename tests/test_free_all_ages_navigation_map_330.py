"""All-ages FREE map: preserve access to facts without betting CTAs (#330).

The real app's route registry supplies the items. Jinja uses an isolated
rendering base, so this test neither mutates data nor calls providers.
"""
import pytest

from test_home_canonical_consistency import component_env


@pytest.mark.parametrize('tier', ['FREE', 'PRO', 'ELITE'])
def test_existing_client_map_is_scoped_to_sports_for_free(app_module, tier):
    nav_items = app_module.v809_client_navigation_items()
    user = {'id': 'synthetic-qa', 'membership': tier, 'role': tier}
    env = component_env('/app/mapa')
    html = env.get_template('client_navigation_map.html').render(
        data={}, items=nav_items, current_user=user, app_icon_version='synthetic-qa'
    )
    assert 'href="/calendario?lane=today"' in html
    assert 'href="/directo"' in html
    if tier == 'FREE':
        for path in ('/picks', '/track-record', '/telegram', '/membresias', '/shark-core'):
            assert f'href="{path}"' not in html, path
        assert 'Pronóstico</span>' not in html
        assert 'pronósticos y SHARK' not in html
        assert 'href="/calendario?lane=finished"' in html
        assert 'href="/favoritos"' in html
    else:
        assert 'href="/picks"' in html
        assert 'href="/telegram"' in html
        assert '<span>Pronóstico</span>' in html


def test_menu_data_returns_only_canonical_spanish_paths(app_module):
    entries = app_module.v809_client_navigation_items()
    hrefs = {entry['href'] for entry in entries}
    assert '/calendario?lane=today' in hrefs
    assert '/directo' in hrefs
    assert '/favoritos' in hrefs
    for outdated in ('/calendar?lane=today', '/live', '/favorites'):
        assert outdated not in hrefs
