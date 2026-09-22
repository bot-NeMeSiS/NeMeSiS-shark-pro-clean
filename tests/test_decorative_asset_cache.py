"""Exact static assets only: never public cache of cookies, HTML or live data."""
import secrets
from pathlib import Path
import pytest
from flask import Flask, session, Response
from engines.decorative_asset_cache import (cache_headers, install_decorative_asset_cache,
                                          DecorativeCacheHeaders, DECORATIVE_FILES, MARKER)


def asset_headers(**values):
    headers={'Content-Type':'image/png','Cache-Control':'no-cache','ETag':'"qa-bytes"',
             'Vary':'Cookie, Accept-Encoding','X-Frame-Options':'SAMEORIGIN',MARKER:'1'}
    headers.update(values)
    return list(headers.items())


def test_only_cookie_vary_is_removed_security_and_validator_preserved():
    result=dict(cache_headers('200 OK',asset_headers(),candidate=True))
    assert result['Cache-Control']=='private, max-age=300, must-revalidate'
    assert result['Vary']=='Accept-Encoding' and result['ETag']=='"qa-bytes"'
    assert result['X-Frame-Options']=='SAMEORIGIN' and MARKER not in result
    assert 'Expires' in result and 'immutable' not in result['Cache-Control']


@pytest.mark.parametrize('change',[{'Set-Cookie':'session=do-not-cache'}, {'X-Nemesis-Local-Safe':'1'},
 {'Content-Type':'text/html'}, {'Cache-Control':'private, no-store'}, {'Cache-Control':'no-store'},
 {'Cache-Control':'public, max-age=10'}, {'Vary':'*'}, {'WWW-Authenticate':'Bearer'},
 {'Content-Range':'bytes 1-2/3'}, {'ETag':''}])
def test_existing_restrictions_are_not_weakened(change):
    before=dict(asset_headers(**change));after=dict(cache_headers('200 OK',list(before.items()),candidate=True))
    before.pop(MARKER)
    assert after==before


@pytest.mark.parametrize('status',['206 Partial Content','403 Forbidden','404 Not Found','500 Error','302 Found'])
def test_errors_partial_ranges_and_redirects_are_not_cached(status):
    assert 'X-Nemesis-Asset-Cache' not in dict(cache_headers(status,asset_headers(),candidate=True))


@pytest.mark.parametrize('candidate,marker',[(False,'1'),(True,'0'),(False,'0')])
def test_marking_and_exact_request_identity_both_required(candidate,marker):
    assert 'X-Nemesis-Asset-Cache' not in dict(cache_headers('200 OK',asset_headers(**{MARKER:marker}),candidate=candidate))


@pytest.fixture
def application(tmp_path):
    static=tmp_path/'static';(static/'img').mkdir(parents=True)
    for name in DECORATIVE_FILES:(static/name).write_bytes(b'public-image-qa-bytes')
    (static/'other.png').write_bytes(b'not-allowlisted')
    app=Flask(__name__,static_folder=str(static));app.secret_key=secrets.token_urlsafe(40);app.testing=True
    @app.before_request
    def csrf_bootstrap():session.setdefault('csrf',secrets.token_urlsafe(16))
    @app.get('/private')
    def private():
        session['role']='example-session'
        return Response('private page',headers={'Cache-Control':'private, no-store'})
    install_decorative_asset_cache(app)
    return app


def test_final_cookie_from_flask_session_is_never_discarded(application):
    c=application.test_client();url='/static/img/nemesis-ocean-depth-r5.png'
    first=c.get(url)
    assert first.status_code==200 and first.headers.get('Set-Cookie')
    assert first.headers['Cache-Control']=='no-cache'
    second=c.get(url)
    assert second.data==first.data
    assert not second.headers.get('Set-Cookie')
    assert second.headers['Cache-Control'].startswith('private, max-age=300')
    assert 'Cookie' not in second.headers.get('Vary','')
    assert MARKER not in second.headers


def test_untouched_html_other_static_and_session_identity(application):
    c=application.test_client();response=c.get('/private')
    assert response.headers['Cache-Control']=='private, no-store' and response.headers.get('Set-Cookie')
    assert 'Cookie' in response.headers['Vary']
    c.get('/static/img/nemesis-ocean-depth-r5.png')
    with c.session_transaction() as current: assert current['role']=='example-session'
    assert c.get('/static/other.png').headers['Cache-Control']=='no-cache'
    assert c.get('/static/img/../other.png').headers['Cache-Control']=='no-cache'
    assert 'X-Nemesis-Asset-Cache' not in c.get('/static/missing.png').headers


def test_head_conditional_and_range_use_existing_file_semantics(application):
    c=application.test_client();c.get('/private');url='/static/img/nemesis-ocean-depth-r5.png'
    original=c.get(url);etag=original.headers['ETag']
    head=c.head(url); assert head.status_code==200 and head.data==b''
    not_modified=c.get(url,headers={'If-None-Match':etag})
    assert not_modified.status_code==304 and not_modified.data==b''
    assert not_modified.headers['Cache-Control'].startswith('private, max-age=300')
    part=c.get(url,headers={'Range':'bytes=0-4'})
    assert part.status_code==206 and part.data==original.data[:5]
    assert 'X-Nemesis-Asset-Cache' not in part.headers


def test_local_safe_responses_unchanged(application):
    @application.after_request
    def local_safe(response): response.headers['X-Nemesis-Local-Safe']='1';return response
    c=application.test_client();c.get('/private')
    r=c.get('/static/img/nemesis-ocean-depth-r5.png')
    assert r.headers['X-Nemesis-Local-Safe']=='1' and r.headers['Cache-Control']=='no-cache'


def test_installation_is_idempotent(application):
    original=application.wsgi_app;install_decorative_asset_cache(application)
    assert application.wsgi_app is original
    assert len(application.extensions['nemesis_decorative_asset_cache']['files'])==2


def test_changed_file_validator_revalidation(application):
    c=application.test_client();c.get('/private');url='/static/img/nemesis-ocean-depth-r5.png'
    old=c.get(url);(Path(application.static_folder)/'img/nemesis-ocean-depth-r5.png').write_bytes(b'changed-public-image')
    r=c.get(url,headers={'If-None-Match':old.headers['ETag']})
    assert r.status_code==200 and r.data==b'changed-public-image' and r.headers['ETag']!=old.headers['ETag']


def test_full_app_installs_cache_without_caching_private_pages(app_module):
    assert 'nemesis_decorative_asset_cache' in app_module.app.extensions
    c=app_module.app.test_client();c.get('/combinadas')
    r=c.get('/static/img/nemesis-ocean-depth-r5.png')
    assert r.status_code==200 and r.headers['Cache-Control'].startswith('private, max-age=300')
    assert c.get('/api/client/combinadas').headers['Cache-Control']=='private, no-store'
    assert c.get('/shark').headers['Cache-Control']=='private, no-store'
