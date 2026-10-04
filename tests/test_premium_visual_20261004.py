from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_premium_visual_pass_is_scoped_and_loaded_after_product_system():
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "premium-visual-20261004.css").read_text(encoding="utf-8")

    product_pos = base.index("product-system.css")
    premium_pos = base.index("premium-visual-20261004.css")
    assert premium_pos > product_pos
    assert 'data-visual-release="premium-pass-20261004"' in base
    assert 'body[data-visual-release="premium-pass-20261004"]' in css
    assert ".v933-match-card" in css
    assert ".v944-match-sections" in css
    assert ".v933-admin-sidebar" in css


def test_visual_pass_keeps_mobile_and_accessibility_guards():
    css = (ROOT / "static" / "premium-visual-20261004.css").read_text(encoding="utf-8")
    assert "@media (max-width: 800px)" in css
    assert "@media (max-width: 420px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "overflow-x: auto" in css
    assert "min-width: 0" in css


def test_visual_pass_does_not_add_navigation_or_product_logic():
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "premium-visual-20261004.css").read_text(encoding="utf-8")

    assert base.count("premium-visual-20261004.css") == 1
    assert "fetch(" not in css
    assert "/api/" not in css
    assert "THE_ODDS_API" not in css
    assert "THESPORTSDB" not in css
