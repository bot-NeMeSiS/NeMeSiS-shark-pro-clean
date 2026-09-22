"""Browser-only caching for two public decorative files, after Flask security.

No file serving, DB access, image conversion, public proxy cache, cookie removal
or caching of HTML/API/crests. The existing Flask application handles every
request first. A response setting a cookie or belonging to LOCAL SAFE is untouched.
"""
from __future__ import annotations

from werkzeug.datastructures import Headers
from werkzeug.http import http_date
import time

MARKER = 'X-Nemesis-Decorative-Candidate'
CACHE_SECONDS = 300
DECORATIVE_FILES = frozenset({
    'img/nemesis-ocean-depth-r5.png',
    'img/nemesis-shark-atmosphere-v2.webp',
})
CONTENT_TYPES = frozenset({'image/png', 'image/webp'})


def cache_headers(status, pairs, *, candidate=False):
    """Change only the final headers of an explicitly marked static response.

    Called after Flask has saved/refreshed its session: Set-Cookie must already
    be visible. Never remove session or security headers. Short private freshness
    is deliberate: existing URLs are not content-addressed or immutable.
    """
    headers = Headers(pairs)
    marked = headers.pop(MARKER, None) == '1'
    if not candidate or not marked or str(status).split(' ', 1)[0] not in {'200', '304'}:
        return list(headers)
    if headers.getlist('Set-Cookie') or headers.get('X-Nemesis-Local-Safe') == '1':
        return list(headers)
    if headers.get('WWW-Authenticate') or headers.get('Content-Range'):
        return list(headers)
    mime = headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
    if str(status).startswith('200') and mime not in CONTENT_TYPES:
        return list(headers)
    # Never weaken no-store or any explicit cache policy from another component.
    directives = {part.strip().lower() for part in headers.get('Cache-Control', '').split(',') if part.strip()}
    if directives - {'no-cache'}:
        return list(headers)
    vary = [value.strip() for line in headers.getlist('Vary') for value in line.split(',') if value.strip()]
    if '*' in vary:
        return list(headers)
    if not headers.get('ETag'):
        return list(headers)
    headers['Cache-Control'] = f'private, max-age={CACHE_SECONDS}, must-revalidate'
    headers['Expires'] = http_date(time.time() + CACHE_SECONDS)
    # These exact static bytes cannot depend on a user's Cookie. Other Vary
    # dimensions remain intact. Never apply this to arbitrary assets or pages.
    headers.remove('Vary')
    remaining = list(dict.fromkeys(value for value in vary if value.casefold() != 'cookie'))
    if remaining:
        headers['Vary'] = ', '.join(remaining)
    headers['X-Nemesis-Asset-Cache'] = 'decorative-private-300s'
    return list(headers)


class DecorativeCacheHeaders:
    """Final response filter; no request, authentication or session bypass."""
    def __init__(self, application, static_prefix):
        self.application = application
        prefix = static_prefix.rstrip('/') + '/'
        self.paths = frozenset(prefix + name for name in DECORATIVE_FILES)

    def __call__(self, environ, start_response):
        candidate = environ.get('REQUEST_METHOD') in {'GET', 'HEAD'} and environ.get('PATH_INFO') in self.paths

        def send(status, headers, exc_info=None):
            return start_response(status, cache_headers(status, headers, candidate=candidate), exc_info)

        return self.application(environ, send)


def install_decorative_asset_cache(app):
    """Explicit one-time installation from the existing blueprint composition."""
    key = 'nemesis_decorative_asset_cache'
    if key in app.extensions:
        return
    if not app.static_folder or not app.static_url_path:
        return
    from flask import request

    @app.after_request
    def mark_static_response(response):
        filename = (request.view_args or {}).get('filename')
        if request.endpoint == 'static' and filename in DECORATIVE_FILES and request.method in {'GET', 'HEAD'}:
            response.headers[MARKER] = '1'
        return response

    app.wsgi_app = DecorativeCacheHeaders(app.wsgi_app, app.static_url_path)
    app.extensions[key] = {'contract': 'DECORATIVE-BROWSER-CACHE-V1', 'max_age': CACHE_SECONDS,
                           'files': sorted(DECORATIVE_FILES), 'public_proxy_cache': False}
