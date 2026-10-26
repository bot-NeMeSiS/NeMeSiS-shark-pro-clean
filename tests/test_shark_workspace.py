"""Actual Jinja shell, progressive links, role separation and localized copy."""
from pathlib import Path
import json

import pytest
from flask import render_template
from test_design02_calendar_presentation import Structure

ROOT=Path(__file__).resolve().parents[1]


def shell(app_module,path='/app',role='FREE'):
    user=None if role is None else dict(id='workspace-qa',name='QA',role=role,membership=role)
    with app_module.app.test_request_context(path):
        return Structure(render_template('base.html',data={},current_user=user))


@pytest.mark.parametrize('role',[None,'FREE','PRO','ELITE','ADMIN'])
def test_one_progressive_launcher_and_dialog_per_client_shell(app_module,role):
    dom=shell(app_module,role=role)
    root,=[n for n in dom.nodes if 'data-ns-assistant' in n['attrs']]
    launcher,=[n for n in dom.nodes if 'data-ns-assistant-open' in n['attrs']]
    dialog,=[n for n in dom.nodes if n['tag']=='dialog' and n['attrs'].get('id')=='ns-assistant-dialog']
    assert root in launcher['parents'] and root in dialog['parents']
    assert launcher['tag']=='a' and launcher['attrs']['href']=='/shark'
    assert launcher['attrs'].get('aria-label') and launcher['attrs']['aria-controls']=='ns-assistant-dialog'
    assert dialog['attrs'].get('aria-labelledby')=='ns-assistant-title'
    assert not dom.with_class('shark-widget') and not dom.with_class('v825-public-floating-shark')


@pytest.mark.parametrize('path',['/admin/control-center','/admin-login','/admin/shark-center',
                                 '/shark','/shark-ai','/shark-core','/shark-intelligence'])
def test_separate_admin_and_full_shark_pages_have_no_client_panel(app_module,path):
    dom=shell(app_module,path,'ADMIN' if path.startswith('/admin') else 'PRO')
    assert not any('data-ns-assistant' in n['attrs'] for n in dom.nodes)


def test_authenticated_form_retains_post_and_csrf(app_module):
    dom=shell(app_module)
    form,=[n for n in dom.nodes if n['attrs'].get('id')=='ns-assistant-form']
    assert form['attrs']['method']=='post' and form['attrs']['action']=='/shark'
    token,=[n for n in dom.nodes if n['attrs'].get('name')=='csrf_token' and form in n['parents']]
    assert token['attrs'].get('value')
    field,=[n for n in dom.nodes if n['attrs'].get('name')=='q' and form in n['parents']]
    assert field['attrs'].get('maxlength')=='1000' and 'required' in field['attrs']


def test_anonymous_panel_never_pretends_to_offer_authenticated_submit(app_module):
    dom=shell(app_module,path='/',role=None)
    assert not any(n['attrs'].get('id')=='ns-assistant-form' for n in dom.nodes)
    assert any(n['attrs'].get('href')=='/cliente-login?next=/shark' for n in dom.nodes)


def test_shark_removed_only_from_primary_client_navigation(app_module):
    dom=shell(app_module)
    for zone in ('client-desktop','client-bottom'):
        root,=[n for n in dom.nodes if n['attrs'].get('data-nav-zone')==zone]
        links=[n['attrs']['href'] for n in dom.nodes if n['tag']=='a' and root in n['parents']]
        assert '/shark' not in links
        assert '/directo' in links and '/picks' in links and '/mi-cuenta' in links
    assert any(n['attrs'].get('href')=='/app' for n in dom.nodes if n['tag']=='a')
    assert any('data-ns-assistant-restore' in n['attrs'] and n['attrs'].get('href')=='/shark' for n in dom.nodes)


def test_all_workspace_copy_is_in_the_existing_language_catalogue():
    from engines.ui_localization_engine import translate
    catalogue=json.loads((ROOT/'localization/ui.json').read_text(encoding='utf-8'))['shark_workspace']
    assert len(catalogue)>=18
    for source,translations in catalogue.items():
        assert set(translations)=={'en','fr'} and all(translations.values())
        for language in ('en','fr'):
            assert translate(source,language)==translations[language]


def test_browser_controller_has_no_context_prefetch_or_prompt_storage():
    code=(ROOT/'static/shark-workspace.js').read_text(encoding='utf-8')
    assert '/api/shark/ask' in code and '/api/shark/context' not in code
    assert 'innerHTML' not in code and 'textContent' in code
    assert 'sessionStorage' not in code
    assert 'localStorage.setItem' not in code  # Transition fallback has no message or token storage.


def test_workspace_controls_are_identified_without_hiding_inert_buttons():
    from engines.navigation_integrity_engine import _NavigationHTMLParser
    parser = _NavigationHTMLParser('components/shark_workspace.html')
    parser.feed((ROOT/'templates/components/shark_workspace.html').read_text(encoding='utf-8'))
    controls = [x for x in parser.entries if x['kind'] == 'button']
    assert len(controls) == 3
    assert {x['selector'] for x in controls} == {
        'button#ns-assistant-expand', 'button#ns-assistant-minimize', 'button#ns-assistant-hide'}
    assert all(x.get('has_identifier') for x in controls)
    inert = _NavigationHTMLParser('unbound.html')
    inert.feed('<button type="button">Unbound action</button>')
    assert any(x['kind'] == 'button' and not x.get('has_identifier') for x in inert.entries)
