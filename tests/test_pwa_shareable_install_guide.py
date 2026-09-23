"""Shareable install guide and non-intrusive PWA prompt contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_install_guide_routes_share_official_icon(app_module):
    client = app_module.app.test_client()
    for route in ("/instalar", "/install-app", "/anadir-a-inicio"):
        response = client.get(route)
        text = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "Instala NeMeSiS como una app" in text
        assert "Añadir a pantalla de inicio" in text
        assert "app-icon-192.png" in text
        assert "data-ns-install-now" in text


def test_prompt_skips_admin_and_uses_versioned_seven_day_dismissal():
    js = (ROOT / "static" / "pwa-install.js").read_text(encoding="utf-8")
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    assert "isAdminSurface" in js
    assert "isInstallGuide" in js
    assert "nemesis-pwa-install-dismissed-" in js
    assert "7 * 24 * 60 * 60 * 1000" in js
    assert "localStorage.setItem" in js
    assert 'href="/instalar"' in js
    assert 'nemesis-app-icon-version' in base


def test_install_guide_reuses_existing_pwa_not_second_manifest():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "install_app.html").read_text(encoding="utf-8")
    assert 'def pwa_install_guide_page' in app
    assert 'window.nemesisInstallApp' in template
    assert 'manifest.json' not in template
    assert 'service-worker' not in template


def test_install_assets_keep_mobile_clearance():
    css = (ROOT / "static" / "pwa-install.css").read_text(encoding="utf-8")
    assert "bottom: calc(164px + env(safe-area-inset-bottom))" in css
    assert ".ns-install-guide__grid" in css
