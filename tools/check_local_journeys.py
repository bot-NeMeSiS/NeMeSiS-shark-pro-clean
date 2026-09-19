"""Browser journeys on the supervised loopback app, using explicit QA accounts."""
import json
import os
import secrets
from pathlib import Path
import time
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/local_dev' / ('journeys-' + uuid.uuid4().hex)
OUT.mkdir()
preview = json.loads((ROOT/'data/local_dev/sentinel-preview.json').read_text())
BASE = 'http://127.0.0.1:' + str(preview['port'])
report = {'environment':'SIMULATED_QA', 'routes':[], 'views':[], 'external':[], 'errors':[], 'timings':[], 'failures':[]}

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=os.environ['NEMESIS_QA_CHROMIUM'])
    for language, zone in [('es','Asia/Tokyo'),('en','America/New_York'),('fr','Europe/London')]:
        context = browser.new_context(viewport={'width':1366,'height':900}, timezone_id=zone)
        def network(route):
            if route.request.url.startswith(BASE+'/'):
                route.continue_()
            else:
                report['external'].append(route.request.url.split('?')[0]); route.abort()
        context.route('**/*', network)
        context.request.get(preview['url'].replace('/login/admin','/login/client'), max_redirects=0)
        page = context.new_page()
        page.on('pageerror', lambda e: report['errors'].append(str(e)))
        page.goto(BASE+'/profile', wait_until='domcontentloaded')
        selector = page.locator('[data-language-selector]')
        selector.locator('select').select_option(language)
        with page.expect_navigation():
            selector.locator('button').click()
        assert page.locator('html').get_attribute('lang') == language
        for path in ['/app','/calendar','/partidos','/live','/directo','/picks','/match/local-match-1','/shark','/track-record','/historico','/combis','/mercados','/highlights','/favorites','/profile','/telegram','/support','/memberships','/recommendations']:
            start = time.perf_counter()
            response = page.goto(BASE+path, wait_until='domcontentloaded')
            report['routes'].append({'language':language,'path':path,'status':response.status,'seconds':round(time.perf_counter()-start,3)})
            if response.status != 200:
                report['failures'].append(language+':'+path+':'+str(response.status))
        for width in (1366,390,430):
            page.set_viewport_size({'width':width,'height':900 if width>500 else 932})
            for path, name in [('/app','home'),('/calendar','calendar'),('/match/local-match-1','match')]:
                page.goto(BASE+path, wait_until='domcontentloaded')
                page.wait_for_timeout(150)
                overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 2')
                clocks = page.locator('[data-match-temporal-context], [data-match-kickoff-clock]').all_text_contents()
                filename = f'{name}-{language}-{width}.png'
                page.screenshot(path=str(OUT/filename))
                report['views'].append({'language':language,'zone':zone,'width':width,'path':path,'overflow':overflow,'clocks':clocks,'image':filename})
                if overflow: report['failures'].append(filename+':overflow')
        page.goto(BASE+'/app', wait_until='domcontentloaded')
        link = page.locator('a[href="/calendar"]:visible').first
        with page.expect_navigation(): link.click()
        assert '/calendar' in page.url
        # Use the stored QA fixture, never fabricate a real provider identity.
        tomorrow = (datetime.now(ZoneInfo('Europe/Madrid')) + timedelta(days=1)).date().isoformat()
        page.goto(BASE+'/calendar?date='+tomorrow, wait_until='domcontentloaded')
        fixture = page.locator('a[href="/match/local-match-2"]:visible').first
        if fixture.count():
            with page.expect_navigation(): fixture.click()
            assert '/match/local-match-2' in page.url
            page.go_back(wait_until='domcontentloaded')
            assert '/calendar' in page.url
            report.setdefault('click_journeys',[]).append(language+':Home-Calendar-Match-Back')
        else:
            report['failures'].append(language+':QA_fixture_not_in_calendar')
        for i in range(3):
            start=time.perf_counter(); response=context.request.get(BASE+'/app')
            report['timings'].append({'language':language,'sample':i,'status':response.status,'seconds':round(time.perf_counter()-start,3)})
        if language == 'es':
            for path in ['/picks','/track-record','/combis','/mercados','/highlights','/favorites','/profile','/telegram','/support','/memberships','/recommendations']:
                for width in (1366,390,430):
                    page.set_viewport_size({'width':width,'height':900 if width>500 else 932})
                    response=page.goto(BASE+path,wait_until='domcontentloaded')
                    overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth + 2')
                    filename=f'client-{path[1:]}-{width}.png'
                    page.screenshot(path=str(OUT/filename))
                    report['views'].append({'path':path,'width':width,'overflow':overflow,'image':filename})
                    if overflow or response.status!=200: report['failures'].append(filename+':layout_or_http')
            page.goto(BASE+'/calendar',wait_until='domcontentloaded')
            date_form=page.locator('.v933-calendar-date-form')
            if not date_form.is_visible():
                page.locator('details').filter(has=date_form).locator('summary').click()
            date_form.locator('[name=date]').fill(tomorrow)
            with page.expect_navigation(): date_form.locator('button[type=submit]').click()
            assert 'date='+tomorrow in page.url
            report.setdefault('click_journeys',[]).append('calendar:date-selector-submit')
            page.goto(BASE+'/favorites',wait_until='domcontentloaded')
            page.locator('#add-favorite-manual summary').click()
            form=page.locator('#add-favorite-manual form')
            favorite_label='QA saved match '+uuid.uuid4().hex[:6]
            form.locator('[name=kind]').select_option('match')
            form.locator('[name=value]').fill('local-match-2')
            form.locator('[name=label]').fill(favorite_label)
            with page.expect_navigation(): form.locator('button').click()
            favorite=page.locator('.favorite-item').filter(has_text=favorite_label)
            assert favorite.count()==1
            page.reload(wait_until='domcontentloaded')
            assert favorite.count()==1
            with page.expect_navigation(): favorite.locator('button').click()
            assert favorite.count()==0
            report['click_journeys'].append('favorites:add-reload-remove')
            page.goto(BASE+'/support', wait_until='domcontentloaded')
            subject='LOCAL_QA_' + uuid.uuid4().hex[:8]
            page.locator('[name=subject]').fill(subject)
            page.locator('[name=message]').fill('Prueba local autorizada de entrega a bandeja; sin correo externo.')
            with page.expect_navigation(): page.locator('.v933-support-form button[type=submit]').click()
            assert page.locator('[data-support-received]').count() == 1
            context.request.get(preview['url'],max_redirects=0)
            page.goto(BASE+'/admin/support-center', wait_until='domcontentloaded')
            assert subject in page.locator('body').inner_text()
            report['support']='PERSISTED_AND_VISIBLE_IN_ADMIN_LOCAL_INBOX'
            page.screenshot(path=str(OUT/'support-admin.png'))
            for path in ['/admin','/admin/sentinel-issues','/admin/automation-workforce','/admin/telegram/command-center','/admin/users','/admin/memberships','/admin/sports-realtime','/admin/data-center','/admin/payments','/admin/highlights','/admin/release-candidate','/admin/recommendations']:
                for width in (1366,390,430):
                    page.set_viewport_size({'width':width,'height':900 if width>500 else 932})
                    response=page.goto(BASE+path,wait_until='domcontentloaded')
                    overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth + 2')
                    filename=f'{path[1:].replace("/","-")}-{width}.png'
                    page.screenshot(path=str(OUT/filename))
                    report['views'].append({'path':path,'width':width,'overflow':overflow,'image':filename,'http':response.status})
                    if overflow or response.status!=200: report['failures'].append(filename+':layout_or_http')
            # Real safe navigation only; provider/payment/mutation controls are not activated.
            page.goto(BASE+'/admin',wait_until='domcontentloaded')
            link=page.locator('a[href="/admin/users"]:visible').first
            with page.expect_navigation(): link.click()
            assert '/admin/users' in page.url
            report.setdefault('click_journeys',[]).append('admin:dashboard-users')
        if language=='fr':
            page.goto(BASE+'/profile',wait_until='domcontentloaded')
            with page.expect_navigation(): page.locator('a[href="/logout"]:visible').first.click()
            page.goto(BASE+'/registro',wait_until='domcontentloaded')
            username='qa_'+uuid.uuid4().hex[:12]
            password=secrets.token_urlsafe(28)
            form=page.locator('form[action="/registro"]')
            form.locator('[name=name]').fill('Local QA')
            form.locator('[name=username]').fill(username)
            form.locator('[name=email]').fill(username+'@example.invalid')
            form.locator('[name=password]').fill(password)
            with page.expect_navigation(): form.locator('button').click()
            assert '/registro' not in page.url
            page.goto(BASE+'/profile',wait_until='domcontentloaded')
            assert username in page.locator('body').inner_text()
            with page.expect_navigation(): page.locator('a[href="/logout"]:visible').first.click()
            page.goto(BASE+'/cliente-login',wait_until='domcontentloaded')
            form=page.locator('form[action="/cliente-login"]')
            form.locator('[name=login]').fill(username)
            form.locator('[name=password]').fill(password)
            with page.expect_navigation(): form.locator('button').click()
            assert '/cliente-login' not in page.url
            report['click_journeys'].append('auth:logout-register-free-logout-password-login')
        context.close()
    browser.close()
(OUT/'result.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'output':str(OUT),'routes':len(report['routes']),'views':len(report['views']),'failures':report['failures'],'errors':report['errors'],'external_count':len(report['external'])}))
raise SystemExit(bool(report['failures'] or report['errors']))
