"""Full admin shells with synthetic records; all requests intercepted, no actions run."""
import mimetypes
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest
from test_app_navigation_browser import browser
from test_company_execution_truth import workforce
from engines.company_operating_system_engine import build_company_os_summary

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', ['admin_company_os', 'admin_automation_workforce'])
@pytest.mark.parametrize('width', [320, 1440])
@pytest.mark.parametrize('language', ['es', 'en', 'fr'])
def test_admin_inventory_is_readable_and_does_not_claim_current_execution(browser, app_module, name, width, language, tmp_path):
    from flask import render_template, session
    path = '/admin/company-os' if name == 'admin_company_os' else '/admin/automation-workforce'
    with app_module.app.test_request_context(path, headers={'Accept-Language': language}):
        session.update(user_id='admin-evidence-qa', user_role='ADMIN', membership='ADMIN', user_membership='ADMIN')
        markup = render_template(name+'.html', data={},
            current_user={'id':'admin-evidence-qa','role':'ADMIN','membership':'ADMIN','name':'Admin QA'},
            summary=build_company_os_summary('SIMULATED_QA', {}),
            workforce=workforce(latest_run={'overall_status':'action_required',
                'version':'SIMULATED_OLD', 'generated_at_madrid':'2020-01-02T10:00:00+01:00', 'dry_run':True}))
    markup = re.sub(r'<script\b([^>]*)>.*?</script>', lambda m:m.group(0) if any(
        keep in m[1] for keep in ('application/json', 'v930-icons.js', 'ui-localization.js')) else '',
        markup, flags=re.S|re.I)
    context = browser.new_context(viewport={'width':width,'height':900}, locale=language, reduced_motion='reduce', service_workers='block')
    page=context.new_page(); calls=[]; errors=[]
    page.on('pageerror', lambda e:errors.append(str(e)))
    def serve(route):
        url=urlsplit(route.request.url); calls.append((route.request.method,url.path))
        if url.netloc!='company.invalid': route.abort(); return
        if url.path==path:
            route.fulfill(status=200,content_type='text/html; charset=utf-8',body=markup);return
        asset=(ROOT/url.path.lstrip('/')).resolve()
        if url.path.startswith('/static/') and asset.is_relative_to(ROOT/'static') and asset.is_file():
            route.fulfill(status=200,content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream',body=asset.read_bytes());return
        route.fulfill(status=200,content_type='text/html',body='<p>SIMULATED_QA destination</p>')
    page.route('**/*',serve)
    try:
        page.goto('https://company.invalid'+path)
        if name=='admin_company_os':
            assert page.locator('.v857-worker-card').count()==15
            assert 'Operativo con revisión continua' not in page.locator('body').inner_text()
            expected={'es':'Sin ejecución acreditada','en':'No verified execution','fr':'Aucune exécution attestée'}[language]
            assert expected in page.locator('.v857-worker-card').first.inner_text()
        else:
            panel=page.locator('[data-workforce-execution]')
            assert 'SIMULATED_OLD' in panel.inner_text() and 'action_required' in panel.inner_text()
            assert panel.locator('time').get_attribute('datetime')=='2020-01-02T10:00:00+01:00'
            expected={'es':'Resultado guardado','en':'Saved result','fr':'Résultat enregistré'}[language]
            assert expected in panel.inner_text()
            assert panel.locator('.is-success').count()==0
            panel.locator('h2').scroll_into_view_if_needed()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        assert not errors
        assert all(method=='GET' and not path.startswith('/api/') for method,path in calls)
        if language=='es':
            page.screenshot(path=str(tmp_path/f'{name}-{width}.png'))
    finally:
        context.close()
