from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_calendar_collection_reclaims_full_width_without_breaking_mobile_order():
    template = _read("templates/calendar.html")

    assert 'class="v933-rail-flow"' in template
    assert 'data-v939-layout-contract="full-width-continuation"' in template
    assert 'data-v939-layout-contract="context-strip"' in template
    assert template.index('data-v939-layout-contract="full-width-continuation"') < template.index(
        'data-v939-layout-contract="context-strip"'
    )
    assert 'class="v933-two-col"' not in template
    assert template.count("v933-match-grid") == 1


def test_client_quick_actions_continue_outside_the_bounded_rail():
    template = _read("templates/client_app_center.html")
    bounded = template.index('data-v939-layout-contract="bounded-rail"')
    continuation = template.index('data-v939-layout-contract="full-width-continuation"')
    segment = template[bounded:continuation]

    assert continuation > bounded
    assert "Tus accesos rápidos" not in segment
    assert template.count("Tus accesos rápidos") == 1
    assert template.index("Tus accesos rápidos") > continuation


def test_telegram_supporting_blocks_form_a_balanced_pair_after_the_rail():
    template = _read("templates/telegram.html")
    bounded = template.index('data-v939-layout-contract="bounded-rail"')
    balanced = template.index('data-v939-layout-contract="balanced-pair"')
    rail_segment = template[bounded:balanced]
    pair_segment = template[balanced:]

    assert "Configurar en 3 pasos" in rail_segment
    assert "Telegram extiende la app; no la sustituye" not in rail_segment
    assert "Calidad del canal" not in rail_segment
    assert 'class="v933-two-col is-balanced"' in template
    assert "Telegram extiende la app; no la sustituye" in pair_segment
    assert "Calidad del canal" in pair_segment


def test_bounded_rail_css_contract_has_desktop_reclaim_and_mobile_collapse():
    css = _read("static/v933-product.css")

    assert ".v933-two-col.is-balanced" in css
    assert ".v933-rail-flow" in css
    assert '[data-v939-layout-contract="context-strip"] { grid-row: 1; }' in css
    assert '[data-v939-layout-contract="full-width-continuation"] { grid-row: 2; }' in css
    assert re.search(
        r"@media \(max-width: 800px\)\s*\{[\s\S]*?"
        r"\.v933-two-col,\.v933-two-col\.is-balanced[^\{]+\{\s*grid-template-columns:\s*1fr;",
        css,
    )


def test_pqv939_004_templates_remain_valid_jinja():
    environment = Environment()
    for path in (
        "templates/calendar.html",
        "templates/client_app_center.html",
        "templates/telegram.html",
    ):
        environment.parse(_read(path))

