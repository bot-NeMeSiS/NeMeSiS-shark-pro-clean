"""Pure navigation evidence for the existing motion toggle; no App import."""
from pathlib import Path

import pytest

from engines.navigation_integrity_engine import (
    _NavigationHTMLParser, _entry_payload, classify_navigation_finding,
)

ROOT = Path(__file__).resolve().parents[1]


def button_entries(source):
    parser = _NavigationHTMLParser("templates/base.html")
    parser.feed(source)
    return [item for item in parser.entries if item["kind"] == "button"]


def test_real_motion_toggle_keeps_visible_javascript_warning():
    base = (ROOT / "templates/base.html").read_text(encoding="utf-8")
    script = (ROOT / "static/platform-motion.js").read_text(encoding="utf-8")
    assert "filename='platform-motion.js'" in base
    assert "document.querySelector('[data-motion-preferences]')" in script
    assert "controls.querySelector('[data-motion-toggle]')" in script
    assert "toggle.addEventListener('click', function ()" in script
    assert "paused = !paused;" in script
    toggle = [item for item in button_entries(base)
              if item.get("javascript_action") == "platform-motion.toggle"]
    assert len(toggle) == 1
    assert toggle[0]["selector"] == "button[data-motion-toggle]"
    # The empty target takes the pure branch; no Flask application is needed.
    result = _entry_payload(None, toggle[0], {})
    assert result["result"] == "WARNING"
    assert "platform-motion.js" in result["detail"]
    assert classify_navigation_finding(result)[0] == "AVISO_ESPERADO"


@pytest.mark.parametrize("source", [
    '<button type="button">Unbound action</button>',
    '<button type="button" data-motion-toggle>Outside preferences</button>',
    '<details data-motion-preferences><button type="button" data-unknown-action>Unknown</button></details>',
    '<details data-motion-preferences><button type="button" data-motion-toggl>Misspelled</button></details>',
    '<details data-motion-preferences><button type="button">Marker removed</button></details>',
    '<details data-motion-preferences></details><button type="button" data-motion-toggle>Closed scope</button>',
])
def test_unbound_buttons_remain_real_navigation_failures(source):
    entries = button_entries(source)
    assert len(entries) == 1
    assert not entries[0].get("has_identifier")
    assert not entries[0].get("javascript_action")
    result = _entry_payload(None, entries[0], {})
    assert result["result"] == "BOTÓN_SIN_ACCIÓN"
    assert classify_navigation_finding(result)[0] == "FALLO_REAL"
