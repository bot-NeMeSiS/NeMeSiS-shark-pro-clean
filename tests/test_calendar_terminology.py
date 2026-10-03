"""Results is the unified section; Calendario remains an internal sports view."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_canonical_navigation_uses_resultados_and_keeps_calendar_aliases():
    nav=(ROOT/"templates/components/navigation_contracts.html").read_text(encoding="utf-8")
    assert "('Resultados','/calendario?lane=finished','history')" in nav
    assert "('Resultados y calendario','/admin/matches','matches')" in nav
    assert "/calendar" in nav
    assert "/partidos" in nav
    renderer=(ROOT/"templates/components/v933_navigation.html").read_text(encoding="utf-8")
    assert "nav_contracts.CLIENT_LINKS" in renderer

def test_home_keeps_calendar_as_a_contextual_view_inside_results():
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


def test_calendar_does_not_claim_confirmation_without_source_and_uses_filter_language():
    calendar=(ROOT/"templates/calendar.html").read_text(encoding="utf-8")
    assert "Agenda deportiva confirmada." not in calendar
    assert "Estado de la agenda deportiva." in calendar
    assert "Limpiar capas" not in calendar
    assert "Limpiar filtros" in calendar
