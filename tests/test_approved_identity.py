"""Owner-approved assets, cache identity and one noninteractive static scene."""
from pathlib import Path
import hashlib
import json
import re
from PIL import Image
import pytest
from test_shark_workspace import shell

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'static/img/approved-identity'


def test_approved_assets_are_intact_proportional_and_bounded_for_each_delivery():
    manifest=json.loads((ASSETS/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['family']=='owner-approved-20261023'
    assert len(manifest['assets'])==7
    for asset in manifest['assets']:
        path=ASSETS/asset['file']
        assert path.parent==ASSETS
        assert hashlib.sha256(path.read_bytes()).hexdigest()==asset['sha256']
        assert path.stat().st_size==asset['bytes']
        with Image.open(path) as im:assert list(im.size)==asset['size']
    sizes={row['file']:row['bytes'] for row in manifest['assets']}
    assert sum(sizes[name] for name in ('nemesis-approved-mark-256.webp','nemesis-approved-ocean-768.webp','nemesis-approved-wireframe-480.webp'))<155000
    assert sum(sizes[name] for name in ('nemesis-approved-mark-256.webp','nemesis-approved-ocean-1600.webp','nemesis-approved-wireframe-960.webp'))<400000


def test_scene_image_and_header_urls_are_versioned_by_actual_content():
    manifest=json.loads((ASSETS/'manifest.json').read_text(encoding='utf-8'))
    css=(ROOT/'static/design-system.css').read_text(encoding='utf-8')
    partial=(ROOT/'templates/partials/brand_logo.html').read_text(encoding='utf-8')
    for row in manifest['assets']:
        name=row['file']
        if name.endswith('1024.webp'):continue  # Build input, not a UI download.
        text=partial if 'mark-' in name else css
        assert name+'?v='+row['sha256'][:12] in text
    assert not re.search(r'animation\s*:',css.split('/* Approved identity:',1)[1])


@pytest.mark.parametrize('path,role',[('/',None),('/cliente-login',None),('/app','FREE'),
    ('/calendario','PRO'),('/mi-cuenta','ELITE'),('/admin/control-center','ADMIN')])
def test_every_shell_has_one_scene_with_no_focusable_or_business_controls(app_module,path,role):
    dom=shell(app_module,path,role)
    scene,=[node for node in dom.nodes if 'data-brand-scene' in node['attrs']]
    assert scene['attrs']['aria-hidden']=='true'
    assert 'tabindex' not in scene['attrs']
    assert not any(scene in node['parents'] and node['tag'] in ('a','button','form','input') for node in dom.nodes)
