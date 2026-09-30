"""Regression coverage for safe PWA static asset caching."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _between(start_marker, end_marker):
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def test_service_worker_caches_only_versioned_same_origin_static_assets():
    route = _between("def service_worker():", "def pwa_install_guide_page():")
    assert "NEMESIS_CACHE_V941_ICON_" in route
    assert "req.mode==='navigate'" in route
    assert "cache:'no-store'" in route
    assert "url.origin===self.location.origin" in route
    assert "url.pathname.startsWith('/static/')" in route
    assert "url.searchParams.has('v')" in route
    assert "req.destination==='style'||req.destination==='script'" in route
    assert "caches.open(NEMESIS_CACHE)" in route
    assert "cache.match(req)" in route
    assert "cache.put(req,response.clone())" in route
    assert "if(req.destination==='style'||req.destination==='script'){event.respondWith(fetch(req,{cache:'reload'}))" not in route


def test_service_worker_runtime_keeps_html_network_only_and_private_data_out_of_cache_storage(app_module):
    with app_module.app.test_request_context("/service-worker.js"):
        response = app_module.service_worker()

    body = response.get_data(as_text=True)
    assert "NEMESIS_CACHE_V941_ICON_" in body
    assert "if(req.mode==='navigate'){event.respondWith(fetch(req,{cache:'no-store'})" in body
    assert "url.pathname.startsWith('/static/')" in body
    assert "url.searchParams.has('v')" in body
    assert "caches.open(NEMESIS_CACHE)" in body
    assert "cache.put(req,response.clone())" in body
    assert "url.pathname.startsWith('/api/')" not in body
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["Service-Worker-Allowed"] == "/"
