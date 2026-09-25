"""V941 terminology: Calendario is the section name; match copy stays specific."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_canonical_navigation_uses_calendario_and_keeps_internal_routes():
    nav=(ROOT/"templates/components/v933_navigation.html").read_text(encoding="utf-8")
    assert "Calendario" in nav
    assert "/calendar" in nav
    assert "/partidos" in nav

def test_home_entry_points_name_the_section_calendario():
    home=(ROOT/"templates/home.html").read_text(encoding="utf-8")
    assert "Abrir calendario" in home
    assert "quick_action('Calendario'" in home
    assert "/calendar" in home
    assert "Partidos de hoy" in home or "partidos" in home.lower()

def test_dynamic_guard_only_maps_standalone_partidos_label():
    js=(ROOT/"static/ui-localization.js").read_text(encoding="utf-8")
    assert "const section = /^(\\s*)partidos(\\s*)$/i.exec(raw);" in js
    assert "'CALENDARIO'" in js
    assert "preferredTerms" in js

def test_match_specific_language_is_not_globally_replaced():
    calendar=(ROOT/"templates/calendar.html").read_text(encoding="utf-8")
    assert "Encontrar partidos" in calendar
    assert "Partidos encontrados" in calendar
