"""Chromium geometry for the four membership tiers, isolated from billing.

Uses the real generated product bundle followed by the real page-specific CSS.
All markup is synthetic and no request, checkout or payment is performed.
"""
from pathlib import Path

import pytest

from test_app_navigation_browser import browser


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("width,columns", [
    (320, 1),
    (390, 1),
    (768, 1),
    (1024, 2),
    (1440, 4),
])
def test_membership_four_card_layout_has_no_orphan_or_overflow(browser, width, columns):
    context = browser.new_context(viewport={"width": width, "height": 900})
    page = context.new_page()
    try:
        cards = []
        for plan, price in (
            ("FREE", "0 €"),
            ("PRO", "14,99 €/mes"),
            ("ELITE", "29,99 €/mes"),
            ("ELITE+", "44,99 €/mes"),
        ):
            cards.append(
                '<article class="v933-plan-card"><header><h3>' + plan +
                '</h3></header><strong class="v933-plan-price">' + price +
                '</strong><p>Datos deportivos y prestaciones cuando estén disponibles</p>' +
                '<ul><li>Información deportiva verificable</li></ul>' +
                '<button type="button" class="v933-action">Elegir ' + plan + ' anual</button></article>'
            )
        page.set_content(
            '<!doctype html><html lang="es"><body class="ns-app" style="margin:0">' +
            '<main class="v933-page v933-memberships-page" style="width:100%;max-width:1160px;margin:auto;padding:12px;box-sizing:border-box">' +
            '<section class="v933-plan-grid">' + ''.join(cards) + '</section></main>' +
            '</body></html>',
            wait_until="load",
        )
        page.add_style_tag(content=(ROOT / "static" / "product-system.css").read_text(encoding="utf-8"))
        page.add_style_tag(content=(ROOT / "static" / "membership-comparison-layout.css").read_text(encoding="utf-8"))
        measured = page.locator(".v933-plan-card").evaluate_all(
            """items => items.map(card => {
                const cardRect = card.getBoundingClientRect();
                const button = card.querySelector('button');
                const buttonRect = button.getBoundingClientRect();
                return {
                    x: cardRect.x, top: cardRect.top,
                    left: cardRect.left, right: cardRect.right,
                    width: cardRect.width,
                    buttonHeight: buttonRect.height,
                    visible: cardRect.width > 0 && cardRect.height > 0
                };
            })"""
        )
        assert len(measured) == 4
        first_row = sum(abs(card["top"] - measured[0]["top"]) < 2 for card in measured)
        assert first_row == columns, (width, measured)
        assert all(card["visible"] and card["width"] > 180 for card in measured), (width, measured)
        assert all(card["left"] >= -2 and card["right"] <= width + 2 for card in measured), (width, measured)
        assert all(card["buttonHeight"] >= 44 for card in measured), (width, measured)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    finally:
        context.close()


def test_memberships_loads_scoped_css_after_base_bundle():
    source = (ROOT / "templates" / "membership.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "membership-comparison-layout.css").read_text(encoding="utf-8")
    assert '{% block head_extra %}' in source
    assert "membership-comparison-layout.css" in source
    assert source.count('class="v933-plan-grid"') == 1
    assert ".v933-memberships-page > .v933-plan-grid" in css
    assert "repeat(4, minmax(0, 1fr))" in css
    assert "@media (max-width: 800px)" in css
