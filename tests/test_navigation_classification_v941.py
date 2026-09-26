"""V941 navigation evidence classification keeps raw findings visible and actionable."""

from engines.navigation_integrity_engine import classify_navigation_finding


def classify(result, *, kind="link", target="/calendar", origin="templates/calendar.html", endpoint="calendar_page"):
    return classify_navigation_finding({
        "result": result,
        "source_kind": kind,
        "generated_url": target,
        "origin_screen": origin,
        "flask_endpoint": endpoint,
    }, {"templates/legacy.html"})


def test_broken_route_is_real_failure():
    label, reason = classify("ROTA_404", target="/missing")
    assert label == "FALLO_REAL"
    assert reason


def test_dynamic_template_is_expected_warning():
    label, _ = classify("WARNING", target="/match/{{ match.id }}", endpoint="dynamic_template")
    assert label == "AVISO_ESPERADO"


def test_javascript_button_is_expected_warning():
    label, _ = classify("WARNING", kind="button", target="", endpoint="")
    assert label == "AVISO_ESPERADO"


def test_non_interactive_metric_is_false_positive():
    label, _ = classify("RUTA_INTERNA_NO_DEBE_SER_VISIBLE", kind="static_anchor", target="", endpoint="")
    assert label == "FALSO_POSITIVO"


def test_orphan_surface_is_legacy_debt():
    label, _ = classify("WARNING", origin="templates/legacy.html", target="{{ item.href }}", endpoint="dynamic_template")
    assert label == "DEUDA_HEREDADA"


def test_normal_route_remains_ok():
    label, _ = classify("OK")
    assert label == "OK"
