"""Safety contract for the service worker's static-asset cache.

Only same-origin CSS/JS whose URL carries the current app-version prefix may
enter Cache Storage. HTML navigation and private/API traffic remain network-only.
"""


def _worker_response(app_module, monkeypatch=None, revision=None):
    if monkeypatch is not None and revision is not None:
        monkeypatch.setenv("RENDER_GIT_COMMIT", revision)
    with app_module.app.test_request_context("/service-worker.js"):
        return app_module.service_worker()


def test_service_worker_uses_deploy_revision_for_cache_invalidation(app_module, monkeypatch):
    response = _worker_response(app_module, monkeypatch, "deadbeef1234")
    script = response.get_data(as_text=True)
    assert "NEMESIS_CACHE_V941_ICON_" in script and "deadbeef1234" in script
    assert "const NEMESIS_APP_VERSION=" in script


def test_only_current_app_versioned_same_origin_css_and_js_are_cacheable(app_module):
    script = _worker_response(app_module).get_data(as_text=True)
    assert "url.origin===self.location.origin" in script
    assert "url.pathname.startsWith('/static/')" in script
    assert "assetVersion.startsWith(NEMESIS_APP_VERSION)" in script
    assert "req.destination==='style'||req.destination==='script'" in script
    assert "const cache=await caches.open(NEMESIS_CACHE)" in script
    assert "const cached=await cache.match(req)" in script
    assert "await cache.put(req,response.clone()).catch(()=>{})" in script
    assert "response&&response.ok&&response.type==='basic'" in script


def test_navigation_icons_and_unversioned_assets_bypass_cache_storage(app_module):
    script = _worker_response(app_module).get_data(as_text=True)
    navigation = script.index("if(req.mode==='navigate')")
    static_cache = script.index("const versionedStatic")
    assert navigation < static_cache
    assert "fetch(req,{cache:'no-store'})" in script
    assert "url.pathname.startsWith('/static/img/app-icons/'))){event.respondWith(fetch(req,{cache:'reload'}));return;}" in script
    assert "if(req.destination==='style'||req.destination==='script'){event.respondWith(fetch(req,{cache:'reload'}));return;}" in script
    assert script.count("cache.put(req,response.clone())") == 1


def test_activation_preserves_other_apps_cache_namespaces(app_module):
    script = _worker_response(app_module).get_data(as_text=True)
    assert "keys.filter(key=>key.startsWith('NEMESIS_CACHE_')&&key!==NEMESIS_CACHE)" in script


def test_service_worker_headers_keep_script_fresh_and_scope_root(app_module):
    response = _worker_response(app_module)
    assert "no-store" in response.headers.get("Cache-Control", "")
    assert response.headers.get("Service-Worker-Allowed") == "/"
