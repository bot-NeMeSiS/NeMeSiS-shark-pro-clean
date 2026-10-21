"""Responsive and no-JavaScript checks for the primary calendar view navigation."""
import os
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch(
            headless=True,
            executable_path=os.getenv("NEMESIS_QA_CHROMIUM") or playwright.chromium.executable_path,
        )
        yield chromium
        chromium.close()


def _calendar_markup(app_module):
    response = app_module.app.test_client().get("/calendario?lane=today")
    assert response.status_code == 200
    markup = response.get_data(as_text=True)
    markup = re.sub(r"<script\b[^>]*>.*?</script\s*>", "", markup, flags=re.IGNORECASE | re.DOTALL)
    markup = re.sub(r"<link\b(?=[^>]*\brel=[\"']stylesheet[\"'])[^>]*>", "", markup, flags=re.IGNORECASE)
    css = (ROOT / "static/product-system.css").read_text(encoding="utf-8")
    return markup.replace("</head>", f"<style>{css}</style></head>", 1)


@pytest.mark.parametrize("width", [320, 390, 1440])
def test_calendar_view_navigation_is_visible_and_responsive_without_javascript(browser, app_module, width):
    markup = _calendar_markup(app_module)
    context = browser.new_context(
        viewport={"width": width, "height": 900},
        java_script_enabled=False,
        locale="es-ES",
    )
    page = context.new_page()
    try:
        page.set_content(markup, wait_until="load")
        panel = page.locator("[data-results-calendar-tabs]")
        tabs = panel.locator(":scope > .v933-filter-tabs")
        links = tabs.locator(":scope > a")
        assert links.count() == 5
        assert [link.inner_text().strip() for link in links.all()] == [
            "Directo", "Resultados", "Calendario", "Próximos", "Con pronóstico"
        ]
        destinations = [urlsplit(link.get_attribute("href")) for link in links.all()]
        assert destinations[0].path == "/directo"
        assert [parse_qs(destination.query).get("lane", [None])[0] for destination in destinations[1:]] == [
            "finished", "today", "week", "with_pick"
        ]
        assert all(destination.path in {"/calendar", "/calendario"} for destination in destinations[1:])

        if width <= 600:
            assert tabs.evaluate("el => getComputedStyle(el).display") == "grid"
            assert tabs.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
            parent_box = tabs.bounding_box()
            boxes = [link.bounding_box() for link in links.all()]
            assert all(box is not None for box in boxes)
            assert all(
                box["x"] >= parent_box["x"] - 1
                and box["x"] + box["width"] <= parent_box["x"] + parent_box["width"] + 1
                for box in boxes
            )
            first_row = [box["y"] for box in boxes[:3]]
            second_row = [box["y"] for box in boxes[3:]]
            assert max(first_row) - min(first_row) <= 2
            assert max(second_row) - min(second_row) <= 2
            assert min(second_row) > max(first_row) + 10
            date_tabs = page.locator(".v933-calendar-date-navigation .v933-filter-tabs")
            if date_tabs.count():
                assert date_tabs.first.evaluate("el => getComputedStyle(el).display") == "grid"
                assert date_tabs.first.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
        else:
            assert tabs.evaluate("el => getComputedStyle(el).display") == "flex"
            assert tabs.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
    finally:
        context.close()
