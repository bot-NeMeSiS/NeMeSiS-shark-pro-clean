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


def test_client_menu_groups_follow_runtime_data_and_hide_internal_copy():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    menu=(root/"templates/client_menu.html").read_text(encoding="utf-8")
    nav=(root/"templates/client_navigation_map.html").read_text(encoding="utf-8")
    assert "all_items|groupby('group')" in menu
    assert "01 · Empezar" not in menu
    assert "super app completa" not in menu
    assert "/mapa, /navegacion y /todo" not in menu
    assert "PC usa la barra superior" not in menu
    assert "Mapa cliente · experiencia final" not in nav
    assert "para no perder botones" not in nav


def test_client_menu_runtime_groups_match_template_contract(app_module):
    groups={item["group"] for item in app_module.v566_client_menu_items()}
    assert groups=={
        "01 - Empezar","02 - Picks","03 - Resultados",
        "04 - Asistente","05 - Cuenta","06 - Ayuda",
    }
    template=(__import__("pathlib").Path(__file__).resolve().parents[1]/"templates/client_menu.html").read_text(encoding="utf-8")
    assert "group_items in all_items|groupby('group')" in template

    combinadas=[item for item in app_module.v566_client_menu_items() if item["title"]=="Combinadas"]
    assert len(combinadas)==1 and combinadas[0]["href"]=="/combinadas"
    shark_core=[item for item in app_module.v809_client_navigation_items() if item["title"]=="SHARK Core"]
    assert len(shark_core)==1
    assert "sin convertir indicadores en garantías" in shark_core[0]["body"]


def test_market_and_combi_query_links_use_real_query_separator():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    app=(root/"app.py").read_text(encoding="utf-8")
    assert "ítipo" not in app
    for href in (
        "/mercados?tipo=1x2",
        "/mercados?tipo=goles",
        "/mercados?tipo=doble",
        "/combis?tipo=mixta&partidos=3",
        "/combis?tipo=responsable&partidos=3",
    ):
        assert href in app
