"""Offline rendered pages and populated shared components, complete CSS cascade."""
from __future__ import annotations

import pytest

from test_journey_controls_browser import browser, page_html, _page, _capture, _inline_styles


@pytest.fixture(scope='module', autouse=True)
def density_account(app_module):
    import sqlite3
    app_module.app.test_client().get('/app')
    with sqlite3.connect(app_module.DB_PATH) as conn:
        conn.execute('INSERT OR IGNORE INTO users(id,email,password_hash,role,membership,created_at) VALUES (?,?,?,?,?,?)',
                     ('v941-click-free','density-qa@example.invalid','invalid_test_hash','FREE','FREE','2026-10-03'))
    yield
    with sqlite3.connect(app_module.DB_PATH) as conn:
        conn.execute('DELETE FROM users WHERE id=? AND email=?',('v941-click-free','density-qa@example.invalid'))


@pytest.mark.parametrize('width', [390, 1440])
@pytest.mark.parametrize('path,admin', [
    ('/app',False),('/calendario',False),('/directo',False),('/picks',False),
    ('/combinadas',False),('/historico',False),('/favoritos',False),
    ('/perfil',False),('/telegram',False),('/soporte',False),('/membresias',False),
    ('/admin/dashboard',True),('/admin/users',True),('/admin/picks',True),
    ('/admin/memberships',True),('/admin/matches-sync',True),
    ('/admin/data-center',True),('/admin/founder-os',True),
    ('/admin/client-preview/frame?page=matches&plan=FREE',True),
])
def test_screen_families_share_density_without_document_overflow(browser,page_html,width,path,admin):
    page = _page(browser,page_html(path,admin=admin),width)
    try:
        assert page.locator('body').get_attribute('data-ui-density') == 'adaptive-v1'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        assert page.locator('main').is_visible()
        _capture(page, 'density-' + path.split('?')[0].strip('/').replace('/','-') + '-' + str(width))
    finally:
        page.close()


@pytest.mark.parametrize('width',[320,390,768,1440,1920])
@pytest.mark.parametrize('count',[1,6])
def test_populated_match_collection_bounds_width_and_preserves_evidence(browser,app_module,width,count):
    from flask import render_template_string
    # Synthetic QA fixtures only; no storage or provider access.
    matches = [{'id':f'qa-{index}','home_team':'Real Sociedad de Fútbol',
                'away_team':'Club Atlético de Madrid','competition_name':'LaLiga',
                'country':'España','home_score':0,'away_score':0,
                'v935_lifecycle':'FINISHED','client_status_label':'Finalizado',
                'status_info':{'key':'FINISHED','is_finished':True,'is_live':False},
                'source':'offline-qa-fixture','match_date':'2026-10-02','kickoff_time':'20:00'}
               for index in range(count)]
    source = '''{% extends 'base.html' %}
    {% from 'components/density.html' import collection %}
    {% from 'components/v933_ui.html' import match_card with context %}
    {% block content %}<div class="v933-page">{% call collection('matches') %}
    {% for match in matches %}{{ match_card(match,false,true) }}{% endfor %}
    {% endcall %}</div>{% endblock %}'''
    with app_module.app.test_request_context('/calendario'):
        html = render_template_string(source,matches=matches,current_user=None)
    page = _page(browser,_inline_styles(html),width)
    try:
        cards = page.locator('.ns-collection .v933-match-card')
        assert cards.count() == count
        rects = [card.bounding_box() for card in cards.all()]
        assert all(rect['width'] <= 521 for rect in rects)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        if width >= 1440 and count > 1:
            assert abs(rects[0]['y']-rects[1]['y']) < 1  # useful records share a row
            assert rects[0]['height'] < 260  # includes confidence/provenance on detailed surfaces
        for card in cards.all():
            assert '0 - 0' in card.inner_text()
            assert 'Real Sociedad de Fútbol' in card.inner_text()
            assert card.get_attribute('data-canonical-live') == 'false'
            action=card.get_by_role('link',name='Ver partido',exact=True)
            assert action.is_visible()
            if width <= 600:
                assert action.bounding_box()['height'] >= 44
        _capture(page,f'density-populated-{count}-{width}')
    finally:
        page.close()


@pytest.mark.parametrize('width',[390,1440])
def test_admin_preview_is_optional_and_operable_without_scripts(browser,page_html,width):
    page=_page(browser,page_html('/admin/dashboard',admin=True),width,javascript=False)
    try:
        panel=page.locator('#master-client-preview')
        assert panel.get_attribute('open') is None
        assert not panel.locator('[data-preview-page]').is_visible()
        panel.locator('summary').click()
        assert panel.locator('[data-preview-page]').is_visible()
        assert panel.locator('[data-preview-full]').is_visible()
        panel.locator('summary').click()
        assert not panel.locator('[data-preview-page]').is_visible()
    finally:
        page.close()
