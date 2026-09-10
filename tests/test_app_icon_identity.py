"""App identity contract. Native OS installation is a separate manual/device gate."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / 'static/img/app-icons'
SIZES = (16, 32, 48, 64, 96, 128, 152, 167, 180, 192, 256, 512)


def metadata():
    return json.loads((ICONS / 'icons.json').read_text())


@pytest.mark.parametrize('size', SIZES)
def test_icon_is_opaque_sized_and_contains_visible_shark(size):
    with Image.open(ICONS / f'app-icon-{size}.png') as image:
        assert image.size == (size, size)
        assert image.mode == 'RGB'
        assert image.getpixel((0, 0)) != (255, 255, 255)
        # A background-only render must fail, even when the file is a valid PNG.
        bright_cyan = sum(g > 145 and b > 170 and b > r * 1.15 for r, g, b in image.getdata())
        assert bright_cyan >= max(3, size // 2)
    assert (ICONS / f'app-icon-{size}.png').stat().st_size < (4096 if size <= 32 else 130000)


@pytest.mark.parametrize('size', (192, 512))
def test_maskable_is_opaque_and_has_distinct_padding(size):
    with Image.open(ICONS / f'app-icon-maskable-{size}.png') as image:
        assert image.size == (size, size) and image.mode == 'RGB'
    assert (ICONS / f'app-icon-maskable-{size}.png').read_bytes() != (ICONS / f'app-icon-{size}.png').read_bytes()


def test_master_reuses_current_shark_and_mask_safe_circle():
    svg = ET.parse(ICONS / 'official_app_icon_master.svg')
    ns = {'s': 'http://www.w3.org/2000/svg'}
    images = svg.findall('.//s:image', ns)
    assert len(images) == 1
    source = images[0]
    assert source.attrib['{http://www.w3.org/1999/xlink}href'] == '../nemesis-shark-atmosphere-v2.webp'
    assert not svg.findall('.//s:text', ns)
    assert not svg.findall('.//s:script', ns)
    x, y, w, h = (float(source.attrib[k]) for k in ('x', 'y', 'width', 'height'))
    scale = metadata()['maskable_scale']
    with Image.open(ICONS / '../nemesis-shark-atmosphere-v2.webp') as image:
        alpha = image.getchannel('A')
        # Rotation around the center does not change radial distance.
        radius_squared = max(((x + (i % image.width) * w / image.width - 512) ** 2
                              + (y + (i // image.width) * h / image.height - 512) ** 2) * scale ** 2
                             for i, value in enumerate(alpha.getdata()) if value > 0)
    assert radius_squared < (1024 * .4) ** 2


def test_outputs_and_version_derive_from_same_master():
    info = metadata()
    source = (ICONS / info['source']).read_bytes()
    assert hashlib.sha256(source).hexdigest() == info['source_sha256']
    digest = hashlib.sha256((ICONS / info['master']).read_text(encoding='utf-8').encode() + source
                            + (ROOT / 'tools/build_app_icons.cjs').read_text(encoding='utf-8').encode()).hexdigest()[:12]
    assert digest == info['fingerprint']
    for name, row in info['files'].items():
        content = (ICONS / name).read_bytes()
        assert hashlib.sha256(content).hexdigest() == row['sha256']
        assert len(content) == row['bytes']


def test_ico_has_real_small_frames_and_desktop_size():
    with Image.open(ICONS / 'app-icon.ico') as icon:
        assert icon.ico.sizes() == {(n, n) for n in (16, 32, 48, 64, 128, 256)}
        assert (512, 512) not in icon.ico.sizes()


def test_manifest_keeps_installed_identity_and_valid_icon_urls(client, app_module, monkeypatch):
    def forbidden():
        raise AssertionError('Icon delivery must not initialize business runtime')
    monkeypatch.setattr(app_module, 'initialize_once', forbidden)
    response = client.get('/manifest.json')
    assert response.status_code == 200 and response.mimetype == 'application/manifest+json'
    assert 'no-store' in response.headers['Cache-Control']
    manifest = response.get_json()
    assert manifest['id'] == manifest['start_url'] == manifest['scope'] == '/'
    assert manifest['display'] == 'standalone'
    assert manifest['name'] == 'NeMeSiS SHARK PRO' and manifest['short_name'] == 'NeMeSiS'
    assert manifest['theme_color'] == manifest['background_color'] == '#020c18'
    assert {(i['sizes'], i['purpose']) for i in manifest['icons']} == {
        (f'{s}x{s}', p) for s in (192, 512) for p in ('any', 'maskable')}
    for item in manifest['icons']:
        parts = urlsplit(item['src'])
        assert not parts.netloc and item['type'] == 'image/png'
        assert parse_qs(parts.query) == {'v': [metadata()['fingerprint']]}
        asset = client.get(item['src'])
        assert asset.status_code == 200 and asset.mimetype == 'image/png'
        with Image.open(BytesIO(asset.data)) as image:
            assert f'{image.width}x{image.height}' == item['sizes']


@pytest.mark.parametrize('route, mime, expected', (
    ('/favicon.ico', 'image/x-icon', 'app-icon.ico'),
    ('/apple-touch-icon.png', 'image/png', 'app-icon-180.png'),
))
def test_public_icon_routes_do_not_initialize_business_runtime(client, app_module, monkeypatch, route, mime, expected):
    monkeypatch.setattr(app_module, 'initialize_once', lambda: pytest.fail('Unexpected business initialization'))
    response = client.get(route)
    assert response.status_code == 200 and response.mimetype == mime
    assert response.data == (ICONS / expected).read_bytes()
    assert 'max-age=0' in response.headers['Cache-Control']


def test_template_metadata_renders_all_current_targets(app_module):
    from flask import render_template_string
    base = (ROOT / 'templates/base.html').read_text(encoding='utf-8')
    head = base.split('</head>', 1)[0]
    with app_module.app.test_request_context('/'):
        html = render_template_string(head, csrf_token=lambda: 'qa-icon-only',
                                      app_version=app_module.APP_VERSION,
                                      app_icon_version=metadata()['fingerprint'])
    links = re.findall(r'<link\b[^>]+>', html)
    icon_links = [t for t in links if re.search(r'rel="(?:icon|shortcut icon|apple-touch-icon)"', t)]
    assert len(icon_links) == 6
    assert all('/static/img/app-icons/' in t and metadata()['fingerprint'] in t for t in icon_links)
    assert 'sizes="16x16"' in html and 'sizes="32x32"' in html
    assert all(f'sizes="{s}x{s}"' in html for s in (152, 167, 180))
    assert 'apple-mobile-web-app-title' in html


def test_service_worker_versions_identity_without_offline_private_cache(client):
    response = client.get('/service-worker.js')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'NEMESIS_CACHE_V940_ICON_' + metadata()['fingerprint'] in body
    assert '/static/img/app-icons/' in body and "cache:'reload'" in body
    assert "req.mode==='navigate'" in body and "cache:'no-store'" in body
    assert 'cache.put' not in body and 'cache.add' not in body
    assert 'no-store' in response.headers['Cache-Control']


def test_desktop_installer_changes_only_app_identity_not_startup_contract():
    script = (ROOT / 'tools/local_desktop/install_desktop_shortcuts.ps1').read_text()
    assert 'static\\img\\app-icons\\app-icon.ico' in script
    assert '$targetScript -eq $start' in script
    assert 'offline_safe' in script and 'integration_test' in script
    assert 'DETENER NEMESIS LOCAL' in script and 'shell32.dll,$iconIndex' in script
    assert 'Wallpaper' not in script and 'SystemParametersInfo' not in script
