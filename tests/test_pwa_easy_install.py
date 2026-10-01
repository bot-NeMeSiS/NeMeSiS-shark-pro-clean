"""PWA install UX and icon-versioning regression contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_base_loads_install_assets_and_keeps_manifest_split():
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    assert "pwa-install.css" in base
    assert "pwa-install.js" in base
    assert "app_icon_version" in base
    assert "founder_manifest_json" in base
    assert "manifest_json" in base


def test_install_script_supports_native_prompt_ios_and_installed_state():
    js = (ROOT / "static" / "pwa-install.js").read_text(encoding="utf-8")
    assert "beforeinstallprompt" in js
    assert "appinstalled" in js
    assert "Añadir a pantalla de inicio" in js
    assert "display-mode: standalone" in js
    assert "window.nemesisInstallApp" in js
    assert "accepted" in js
    assert "appinstalled" in js
    assert "installed" in js
    assert "unavailable" in js


def test_install_ui_is_compact_and_safe_area_aware():
    css = (ROOT / "static" / "pwa-install.css").read_text(encoding="utf-8")
    assert "env(safe-area-inset-bottom)" in css
    assert "@media (display-mode: standalone)" in css
    assert "position: fixed" in css
    assert "bottom: calc(164px + env(safe-area-inset-bottom))" in css


def test_manifest_and_service_worker_keep_single_icon_family():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'APP_ICON_VERSION' in app
    assert 'img/app-icons/app-icon-{size}.png' in app
    assert 'img/app-icons/app-icon-maskable-{size}.png' in app
    assert 'app-icon-180.png' in app
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip().split("_", 1)[0]
    assert f"NEMESIS_CACHE_{version}_ICON_" in app


def test_served_worker_activation_preserves_unrelated_caches(app_module):
    """Execute the actual served JS in an isolated browser, not an installed PWA."""
    import os
    from playwright.sync_api import sync_playwright

    response = app_module.app.test_client().get('/service-worker.js')
    assert response.status_code == 200
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path,
                                    headless=True)
        try:
            page = browser.new_page()
            result = page.evaluate("""async script => {
                const listeners = {}, removed = [];
                let pending, claimed = false;
                const self = {addEventListener: (name, fn) => listeners[name] = fn,
                              clients: {claim: async () => { claimed = true; }}};
                const caches = {keys: async () => ['NEMESIS_CACHE_OLD', 'other-app', 'FOUNDER_PRIVATE'],
                                delete: async key => { removed.push(key); return true; }};
                new Function('self', 'caches', script)(self, caches);
                listeners.activate({waitUntil: promise => { pending = promise; }});
                await pending;
                return {removed, claimed};
            }""", response.get_data(as_text=True))
            assert result == {'removed': ['NEMESIS_CACHE_OLD'], 'claimed': True}
        finally:
            browser.close()
