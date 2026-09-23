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
