"""PWA installation and unified app identity. No provider calls or writes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shareable_install_routes_and_identity(app_module):
    client = app_module.app.test_client()
    for route in ("/instalar", "/install-app", "/anadir-a-inicio"):
        response = client.get(route)
        assert response.status_code == 200
        text = response.get_data(as_text=True)
        assert "Instala NeMeSiS como una app" in text
        assert "Añadir a pantalla de inicio" in text
        assert "app-icon-192.png" in text
    info = client.get("/api/app-install-info").get_json()
    assert info["ok"] is True
    assert info["same_icon_family_as_admin"] is True
    assert info["provider_calls"] == 0 and info["writes"] == 0
    assert info["icon_fingerprint"] == app_module.APP_ICON_VERSION


def test_header_admin_pwa_and_manifest_share_dynamic_version():
    base = (ROOT / "templates/base.html").read_text(encoding="utf-8")
    brand = (ROOT / "templates/partials/brand_logo.html").read_text(encoding="utf-8")
    prompt = (ROOT / "templates/partials/pwa_install_prompt.html").read_text(encoding="utf-8")
    js = (ROOT / "static/pwa-install.js").read_text(encoding="utf-8")
    assert "8d0ed4207e73" not in brand
    assert "app_icon_version" in brand
    assert "url_for('manifest_json')" in base
    assert "url_for('founder_manifest_json')" in base
    assert 'href="/instalar"' in base
    assert 'data-icon-version="{{ app_icon_version }}"' in prompt
    assert "nemesis-pwa-install-dismissed-" in js


def test_admin_surfaces_do_not_render_client_install_prompt(app_module):
    client = app_module.app.test_client()
    response = client.get("/admin-login")
    text = response.get_data(as_text=True)
    assert "data-ns-pwa-install" not in text


def test_manifests_use_same_official_icon_family(client):
    public = client.get("/manifest.json").get_json()
    founder = client.get("/founder-manifest.json").get_json()
    public_icons = {item["src"].split("?")[0] for item in public["icons"]}
    founder_icons = {item["src"].split("?")[0] for item in founder["icons"]}
    assert "/static/img/app-icons/app-icon-192.png" in public_icons
    assert "/static/img/app-icons/app-icon-512.png" in public_icons
    assert "/static/img/app-icons/app-icon-192.png" in founder_icons
    assert "/static/img/app-icons/app-icon-512.png" in founder_icons
