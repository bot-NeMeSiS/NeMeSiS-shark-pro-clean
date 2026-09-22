"""Actual loopback HTTP cache test, synthetic pages and image bytes; no providers.

Do not use page.route: Playwright routing disables the browser's normal cache.
Only a loopback Flask page and two in-process PNG/WebP files are referenced.
"""
from pathlib import Path
from collections import Counter
from threading import Thread
import os
import secrets

import pytest
from flask import Flask, Response, session, request
from PIL import Image
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from engines.decorative_asset_cache import install_decorative_asset_cache, DECORATIVE_FILES


@pytest.mark.parametrize('enabled',[False,True])
def test_decorations_reused_after_navigation_changes_session_cookie(tmp_path,enabled):
    static=tmp_path/'static';(static/'img').mkdir(parents=True)
    for name in DECORATIVE_FILES:
        Image.new('RGB',(24,24)).save(static/name)
    app=Flask(__name__,static_folder=str(static));app.secret_key=secrets.token_urlsafe(40)
    seen=Counter()
    @app.before_request
    def security_and_count():
        session.setdefault('csrf',secrets.token_urlsafe(16))
        if request.endpoint=='static':seen[request.path]+=1
    @app.get('/')
    def page():
        session['navigation']=session.get('navigation',0)+1
        return Response('<!doctype html><title>SIMULATED_QA</title><h1>Public image cache</h1>'+
            ''.join('<img src="/static/'+name+'" alt="synthetic decoration">' for name in sorted(DECORATIVE_FILES)),
            headers={'Content-Type':'text/html','Cache-Control':'private, no-store',
                     'Content-Security-Policy':"default-src 'self'; img-src 'self'"})
    if enabled:install_decorative_asset_cache(app)
    server=make_server('127.0.0.1',0,app,threaded=True)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as pw:
            path=os.environ.get('NEMESIS_QA_CHROMIUM') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else '')
            options={'headless':True,'args':['--no-sandbox']}
            if path:options['executable_path']=path
            browser=pw.chromium.launch(**options)
            try:
                context=browser.new_context(service_workers='block')
                tab=context.new_page();base='http://127.0.0.1:'+str(server.server_port)
                tab.goto(base+'/?page=1',wait_until='networkidle')
                assert tab.locator('img').evaluate_all('(els)=>els.every(el=>el.complete&&el.naturalWidth===24)')
                first_cookie=context.cookies()[0]['value']
                initial=dict(seen)
                assert sum(initial.values())==2
                tab.goto(base+'/?page=2',wait_until='networkidle')
                assert tab.locator('img').evaluate_all('(els)=>els.every(el=>el.complete&&el.naturalWidth===24)')
                assert context.cookies()[0]['value']!=first_cookie
                expected=1 if enabled else 2
                assert all(seen['/static/'+name]==expected for name in DECORATIVE_FILES),dict(seen)
                assert 'Public image cache' in tab.locator('h1').inner_text()
            finally:browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)
