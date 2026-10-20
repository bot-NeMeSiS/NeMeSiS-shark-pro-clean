"""Primary brand vector stays crisp, self-contained, and separate from the PWA icon."""
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def test_primary_brand_vector_is_self_contained_and_described():
    asset = ROOT / "static/img/nemesis-shark-mark.svg"
    svg = ET.parse(asset).getroot()

    assert svg.tag == "{http://www.w3.org/2000/svg}svg"
    assert svg.attrib["viewBox"] == "0 0 160 96"
    assert svg.find("{http://www.w3.org/2000/svg}title") is not None
    assert svg.find("{http://www.w3.org/2000/svg}desc") is not None
    forbidden = {"image", "script", "foreignObject", "iframe"}
    assert not [node.tag.rsplit("}", 1)[-1] for node in svg.iter()
                if node.tag.rsplit("}", 1)[-1] in forbidden]


def test_shared_brand_uses_vector_mark_while_pwa_install_icon_remains_independent():
    partial = (ROOT / "templates/partials/brand_logo.html").read_text(encoding="utf-8")
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    css = (ROOT / "static/product-system.css").read_text(encoding="utf-8")
    contracts = (ROOT / "reference_images/design_contracts.json").read_text(encoding="utf-8")

    assert "nemesis-shark-mark.svg?v=brand-20261020-1" in partial
    assert 'data-brand-source="official-brand-vector"' in partial
    assert "app-icon-{size}.png" in app
    assert "official_app_icon_master.svg" in (ROOT / "static/img/app-icons/icons.json").read_text(encoding="utf-8")
    assert ".brand.v949-brand .ns-brand-name" in css
    assert "PRIMARY_BRAND_MARK" in contracts and "nemesis-shark-mark.svg" in contracts
