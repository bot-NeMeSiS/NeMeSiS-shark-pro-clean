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


def test_navigation_auth_classification_matches_current_account_and_public_plan_routes():
    from engines.navigation_integrity_engine import _route_authentication
    assert _route_authentication("/mi-cuenta") == "client"
    assert _route_authentication("/profile") == "client"
    assert _route_authentication("/favoritos") == "client"
    assert _route_authentication("/membresias") == "public"
    assert _route_authentication("/memberships") == "public"


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
        "01 - Empezar","02 - Pronósticos","03 - Resultados",
        "04 - Asistente","05 - Cuenta","06 - Ayuda",
    }
    template=(__import__("pathlib").Path(__file__).resolve().parents[1]/"templates/client_menu.html").read_text(encoding="utf-8")
    assert "group_items in all_items|groupby('group')" in template

    combinadas=[item for item in app_module.v566_client_menu_items() if item["title"]=="Combinadas"]
    assert len(combinadas)==1 and combinadas[0]["href"]=="/combinadas"
    shark_core=[item for item in app_module.v809_client_navigation_items() if item["title"]=="SHARK Core"]
    assert len(shark_core)==1
    assert "sin convertir indicadores en garantías" in shark_core[0]["body"]
    menu_items=app_module.v566_client_menu_items()
    assert any(item["title"]=="Pronósticos SHARK" for item in menu_items)
    assert all(item["title"]!="Picks SHARK" for item in menu_items)
    assert all("stake" not in item["body"].lower() and "value" not in item["body"].lower() for item in menu_items)
    nav_items=app_module.v809_client_navigation_items()
    assert any(item["title"]=="Pronósticos" for item in nav_items)
    assert any(item["title"]=="Historial" for item in nav_items)
    assert all(item["title"] not in {"Picks","SHARK IA","Histórico"} for item in nav_items)


def test_market_and_combi_query_links_use_real_query_separator():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    app=(root/"app.py").read_text(encoding="utf-8")
    menu=(root/"templates/client_menu.html").read_text(encoding="utf-8")
    assert "ítipo" not in app
    assert "/combisí" not in app
    assert "/combinadas" in menu
    assert "/combis" not in menu


def test_client_facing_combi_navigation_prefers_canonical_route(app_module,monkeypatch):
    monkeypatch.setattr(app_module,"telegram_config",lambda: {"configured":False})
    recommended=app_module.client_command_center_data({"id":"qa","membership":"PRO","role":"PRO"}, briefing={
        "counts":{"favorites":0,"upcoming":0,"picks":0},
    })["recommended_tabs"]
    combinadas=[item for item in recommended if item["label"]=="Combinadas"]
    assert len(combinadas)==1 and combinadas[0]["href"]=="/combinadas"

    architecture=app_module.v776_client_information_architecture_snapshot()["routes"]
    canonical=[item for item in architecture if item["label"]=="Combinadas"]
    assert len(canonical)==1 and canonical[0]["href"]=="/combinadas"


def test_core_client_templates_use_canonical_spanish_routes():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    home=(root/"templates/client_app_center.html").read_text(encoding="utf-8")
    telegram=(root/"templates/telegram.html").read_text(encoding="utf-8")
    membership=(root/"templates/membership.html").read_text(encoding="utf-8")
    assert "'/memberships'" not in home and "'/support'" not in home
    assert "'/membresias'" in home and "'/soporte'" in home
    assert "'/profile'" not in telegram and "'/memberships'" not in telegram
    assert "'/mi-cuenta'" in telegram and "'/membresias'" in telegram
    assert "'/profile'" not in membership and "'/memberships?plan='" not in membership
    assert "'/mi-cuenta'" in membership and "'/membresias?plan='" in membership


def test_navigation_renderers_share_canonical_contract_source():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    contract=(root/"templates/components/navigation_contracts.html").read_text(encoding="utf-8")
    assert "CLIENT_LINKS" in contract and "ADMIN_LINKS" in contract
    assert "/calendario-global" in contract and "/partidos/calendario" in contract
    assert "/combis" in contract and "/combinadas" in contract
    mobile_contract=contract.split("{% set CLIENT_MOBILE_LINKS = [",1)[1].split("] %}",1)[0]
    assert "('SHARK','/shark','shark')" in mobile_contract
    assert "('Cuenta','/profile','user')" not in mobile_contract
    assert "('Cuenta','/mi-cuenta','user')" in contract
    source=(root/"templates/components/v933_navigation.html").read_text(encoding="utf-8")
    assert 'navigation_contracts.html' in source
    assert 'href="/mi-cuenta"' in source
    assert 'href="/profile"' not in source
    assert "nav_contracts.CLIENT_LINKS" in source
    assert "nav_contracts.ADMIN_LINKS" in source
    for name in ("v928_navigation.html","v930_navigation.html"):
        assert not (root/"templates/components"/name).exists()


def test_runtime_navigation_compatibility_flag_tracks_canonical_v933(app_module):
    response=app_module.app.test_client().get("/api/runtime-version")
    assert response.status_code==200
    runtime=response.get_json() or {}
    assert runtime.get("has_v929_mobile_navigation_guard") is True
    source=(__import__("pathlib").Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
    flag_block=source.split('"has_v929_mobile_navigation_guard": (',1)[1].split("),",1)[0]
    assert "v933_navigation.html" in flag_block
    assert "v928_navigation.html" not in flag_block


def test_navigation_contract_aliases_have_one_active_rule(app_module):
    template=app_module.app.jinja_env.from_string(
        "{% import 'components/navigation_contracts.html' as nav %}"
        "{{ nav.is_active('/calendar', path, 'client') }}|"
        "{{ nav.is_active('/picks', path, 'client') }}|"
        "{{ nav.is_active('/admin/matches', path, 'admin') }}"
    )
    assert template.render(path="/calendario-global")=="1||"
    assert template.render(path="/partidos/calendario")=="1||"
    assert template.render(path="/combinadas")=="|1|"
    assert template.render(path="/combis")=="|1|"
    assert template.render(path="/admin/matches-sync")=="||1"
    account=app_module.app.jinja_env.from_string(
        "{% import 'components/navigation_contracts.html' as nav %}"
        "{{ nav.is_active('/mi-cuenta', path, 'client') }}"
    )
    assert account.render(path="/mi-cuenta")=="1"
    assert account.render(path="/profile")=="1"
    assert account.render(path="/perfil")=="1"
    contextual=app_module.app.jinja_env.from_string(
        "{% import 'components/navigation_contracts.html' as nav %}"
        "{{ nav.is_active('/admin/dashboard#master-audit-title', '/admin/dashboard', 'admin') }}|"
        "{{ nav.is_active('/admin/dashboard?commands=1', '/admin/dashboard', 'admin') }}"
    )
    assert contextual.render()=="|"


def test_legacy_navigation_renderers_stay_purged_and_v933_is_canonical():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    templates=root/"templates"
    legacy_names={"v928_navigation.html","v930_navigation.html"}
    for name in legacy_names:
        assert not (templates/"components"/name).exists()

    offenders=[]
    for path in templates.rglob("*.html"):
        source=path.read_text(encoding="utf-8")
        if "components/v928_navigation.html" in source or "components/v930_navigation.html" in source:
            offenders.append(str(path.relative_to(root)))
    assert offenders==[]

    base=(templates/"base.html").read_text(encoding="utf-8")
    assert 'components/v933_navigation.html' in base
    assert 'components/v928_navigation.html' not in base
    assert 'components/v930_navigation.html' not in base
