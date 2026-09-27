"""Current client surfaces, canonical routes and QA guard truth."""
from pathlib import Path

from engines.client_experience_guard_engine import client_experience_snapshot

ROOT = Path(__file__).resolve().parents[1]


def test_client_experience_guard_tracks_current_product_surfaces():
    snapshot = client_experience_snapshot(ROOT)
    by_route = {item["route"]: item for item in snapshot["critical_screens"]}
    assert "/dashboard" not in by_route
    assert by_route["/app"]["template"] == "client_app_center.html"
    assert by_route["/track-record"]["template"] == "track_record.html"
    assert by_route["/profile"]["template"] == "profile.html"
    assert by_route["/membresias"]["template"] == "membership.html"
    assert all(item["exists"] and item["time_status_ok"] for item in snapshot["critical_screens"])
    assert snapshot["status"] == "OK"
    assert snapshot["score"] == 100


def test_client_templates_use_spanish_canonical_support_and_plan_routes():
    names = (
        "templates/profile.html",
        "templates/company_platform.html",
        "templates/components/platform_faq.html",
        "templates/home.html",
        "templates/recommendations.html",
    )
    combined = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in names)
    assert "'/memberships'" not in combined
    assert "'/support'" not in combined
    assert "'/membresias'" in combined
    assert "'/soporte'" in combined


def test_support_surface_uses_canonical_spanish_routes_and_copy():
    source=(ROOT / "templates/support.html").read_text(encoding="utf-8")
    assert "next=/support" not in source
    assert 'href="/profile"' not in source
    assert "Picks / combinadas" not in source
    assert "next=/soporte" in source
    assert 'href="/mi-cuenta"' in source
    assert "Pronósticos / combinadas" in source


def test_core_client_favorites_navigation_uses_spanish_canonical_route():
    names = (
        "templates/home.html",
        "templates/client_app_center.html",
        "templates/favorites.html",
        "templates/account_center.html",
    )
    combined = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in names)
    assert '"/favorites"' not in combined
    assert "'/favorites'" not in combined
    assert "/favoritos" in combined

    source=(ROOT / "app.py").read_text(encoding="utf-8")
    assert 'return redirect("/favoritos")' in source
    assert '"href": "/favorites"' not in source
    assert '@app.route("/favorites", methods=["GET", "POST"])' in source
    assert '@app.route("/api/favorites", methods=["GET", "POST", "DELETE"])' in source


def test_top_level_client_templates_do_not_reintroduce_legacy_english_aliases():
    legacy_tokens = (
        '"/favorites"', "'/favorites'",
        '"/support"', "'/support'",
        '"/memberships"', "'/memberships'",
    )
    offenders=[]
    for path in sorted((ROOT / "templates").glob("*.html")):
        if path.name.startswith("admin_"):
            continue
        source=path.read_text(encoding="utf-8")
        for token in legacy_tokens:
            if token in source:
                offenders.append((path.name, token))
    assert offenders == []


def test_secondary_client_copy_uses_current_spanish_vocabulary():
    sports=(ROOT / "templates/sports_hub.html").read_text(encoding="utf-8")
    favorites=(ROOT / "templates/favorites.html").read_text(encoding="utf-8")
    recommendations=(ROOT / "templates/recommendations.html").read_text(encoding="utf-8")
    for forbidden in (">Picks</a>", "<span>Picks</span>", "<span>Combis</span>", "calendario o picks"):
        assert forbidden not in sports
    assert "Pronósticos" in sports and "Combinadas" in sports
    for forbidden in ("Sports Hub, Live, Calendar", "Live relacionados", "Picks relacionados", "Pick SHARK"):
        assert forbidden not in favorites
    assert "Centro deportivo, Directo, Calendario" in favorites
    assert "Pronósticos relacionados" in favorites
    assert "picks relacionados" not in favorites.lower()
    assert "ver picks" not in favorites.lower()
    assert "recap" not in favorites.lower()
    assert "Picks publicados" not in recommendations
    assert "Pronósticos publicados" in recommendations


def test_secondary_client_surfaces_finish_spanish_first_vocabulary():
    names = (
        "templates/action_platform.html",
        "templates/alerts.html",
        "templates/auto_picks.html",
        "templates/autonomous_ecosystem.html",
        "templates/ecosystem.html",
        "templates/highlight_detail.html",
    )
    combined = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in names)
    for forbidden in (
        "Picks sin grading", "datos stale", "Auto Picks", "Picks publicados",
        "Picks candidatos", "Live, Telegram, picks", ">Track Record<",
        'href="/perfil"',
    ):
        assert forbidden not in combined
    for required in (
        "Pronósticos sin resultado evaluado", "datos desactualizados",
        "Pronósticos automáticos", "Pronósticos publicados",
        "Pronósticos candidatos", "Directo, Telegram, pronósticos",
        ">Historial<", 'href="/mi-cuenta"',
    ):
        assert required in combined


def test_remaining_secondary_surfaces_use_spanish_client_labels():
    live_depth=(ROOT / "templates/live_depth.html").read_text(encoding="utf-8")
    local_safe=(ROOT / "templates/local_safe_portal.html").read_text(encoding="utf-8")
    player=(ROOT / "templates/player_detail.html").read_text(encoding="utf-8")
    assert "Live premium" not in live_depth and "Directo premium" in live_depth
    for forbidden in ("('Picks','/picks')", "('Track Record','/track-record')", "('Memberships','/membresias')", "('Profile','/profile')", ">Picks locales<"):
        assert forbidden not in local_safe
    for required in ("('Pronósticos','/picks')", "('Historial','/track-record')", "('Membresías','/membresias')", "('Mi cuenta','/mi-cuenta')", ">Pronósticos locales<"):
        assert required in local_safe
    assert 'ui("Picks")' not in player
    assert 'ui("Pronósticos")' in player


def test_team_and_user_intelligence_surfaces_use_canonical_spanish_labels():
    team=(ROOT / "templates/team_detail.html").read_text(encoding="utf-8")
    user_intelligence=(ROOT / "templates/user_intelligence_center.html").read_text(encoding="utf-8")
    assert 'ui("Picks")' not in team
    assert 'ui("Picks relacionados")' not in team
    assert 'ui("Pronósticos")' in team
    assert 'ui("Pronósticos relacionados")' in team
    assert 'href="/profile"' not in user_intelligence
    assert 'href="/mi-cuenta"' in user_intelligence
    assert 'ui("Mi cuenta")' in user_intelligence


def test_confirmed_orphan_legacy_templates_stay_purged():
    for name in ("client_progress.html", "product_audit.html", "admin_autonomous_ecosystem.html", "client_overview.html", "smart_dashboard.html"):
        assert not (ROOT / "templates" / name).exists()


def _app_function_source(name):
    source=(ROOT / "app.py").read_text(encoding="utf-8")
    start=source.index(f"def {name}(")
    end=source.find("\ndef ", start + 5)
    return source[start:] if end < 0 else source[start:end]


def test_python_generated_client_links_use_canonical_spanish_support_route():
    source=(ROOT / "app.py").read_text(encoding="utf-8")
    assert '"href": "/support"' not in source
    assert '"Customer Success", "/support")' not in source
    assert '{"label": "Soporte", "href": "/soporte"}' in source
    assert '@app.route("/support", methods=["GET", "POST"])' in source
    assert '@app.route("/soporte", methods=["GET", "POST"])' in source


def test_client_python_projections_use_current_spanish_vocabulary():
    checks = {
        "build_client_alerts": ("Picks publicados", "pick(s)", "picks publicados", '"PICKS"', '"LIVE"'),
        "build_daily_briefing": ('"Picks visibles"',),
        "client_command_center_data": ('"label": "Picks"', "Apuestas publicadas"),
        "sports_hub_page": ('"label": "Picks"',),
        "v566_client_menu_items": ("Histórico / ROI real",),
        "build_v763_world_cup_launch_context": ('"badge": "Live"',),
        "build_v764_dynamic_competition_mode": ('"label": "Histórico"',),
        "v777_client_product_context": ("Hay picks", "stake", '"icon": "Live"', '"icon": "Picks"', "Histórico"),
        "v778_client_product_organization_context": ('"label": "Picks"', "stake", "Track Record", '"Picks"', "histórico real", "Grading", "Prioridad: Picks"),
        "v809_client_navigation_items": ('"icon":"Live"',),
        "v724_contact_alias_page": ("'/support'", '"title": "Picks"'),
    }
    for name, forbidden in checks.items():
        source=_app_function_source(name)
        for token in forbidden:
            assert token not in source, (name, token)
    assert "Pronósticos publicados disponibles" in _app_function_source("build_client_alerts")
    assert "Prioridad: Pronósticos" in _app_function_source("v778_client_product_organization_context")
    assert "return redirect('/soporte', code=303)" in _app_function_source("v724_contact_alias_page")


def test_secondary_current_client_surfaces_drop_legacy_pick_combi_jargon():
    files = (
        "templates/adaptive_experience.html",
        "templates/client_success.html",
        "templates/shark_intelligence_center.html",
        "templates/components/picks_workspace_nav.html",
        "templates/partials/client_flow_bar.html",
        "engines/client_success_engine.py",
    )
    combined = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in files)
    for token in (
        ">Picks</a>", "<h3>Picks</h3>", "<strong>Picks</strong>",
        "Picks premium", "Combis inteligentes", "SHARK AI Advisor",
        "stake responsable", "interpretar picks, value", "sin compartir secrets",
    ):
        assert token not in combined
    assert "Pronósticos" in combined
    assert "Combinadas" in combined
    assert "Asistente SHARK" in combined
    assert "/combinadas" in combined


def test_shark_intelligence_visible_copy_stays_spanish_first():
    source=(ROOT / "templates/shark_intelligence_center.html").read_text(encoding="utf-8")
    for token in ("SHARK Platform", ">Picks</a>", ">Graph<", ">Claims<", ">Modulos<"):
        assert token not in source
    for token in ("Inteligencia SHARK", ">Pronósticos</a>", ">Grafo<", ">Afirmaciones<", ">Módulos<"):
        assert token in source



def test_client_visible_copy_stays_spanish_after_final_polish():
    names = (
        "templates/alerts.html",
        "templates/auto_picks.html",
        "templates/autonomous_ecosystem.html",
        "templates/ecosystem.html",
        "templates/global.html",
        "templates/legal_trust.html",
        "templates/onboarding.html",
        "templates/resource_unavailable.html",
        "templates/responsible_betting.html",
        "templates/combis.html",
        "templates/components/combi_match_catalogue.html",
        "templates/components/platform_faq.html",
        "templates/base.html",
        "templates/client_app_center.html",
        "templates/register.html",
        "templates/components/v933_ui.html",
        "templates/components/v936_product.html",
        "templates/components/v937_sports_lifecycle.html",
        "templates/local_safe_portal.html",
        "templates/import_center.html",
        "templates/partials/ui_components.html",
        "templates/opportunities.html",
        "templates/team_detail.html",
    )
    combined = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in names)
    for forbidden in (
        "live, picks, favoritos",
        ">picks visibles<",
        "picks candidatos",
        ">Ver picks<",
        "picks reales.",
        "Un pick o recomendación",
        "favoritos, picks y alertas",
        "Stake máximo por pick",
        "No hace falta un pick editorial",
        "También puedes elegir picks publicados",
        "Selecciona picks publicados",
        "Propuesta automática a partir de picks publicados",
        "Ordenación de picks elegibles",
        "un pick recomendado",
        'ns_ui("Value")',
        "con value y aviso",
        "favoritos, live, picks",
        'ui("Picks completos")',
        "Picks completos, SHARK",
        'ui("Picks publicables")',
        'ui("Expediente profesional del pick")',
        "jugadores y picks de esta seccion",
        "Partidos y live",
        "Importar picks",
        "Solo picks propios",
        "Pick cargado por administrador",
        "status='Pick en revisión'",
        "Score datos/picks",
        'ui("Aún no hay picks publicados para este equipo.")',
    ):
        assert forbidden not in combined, forbidden

    for required in (
        "directo, pronósticos, favoritos",
        ">pronósticos visibles<",
        "pronósticos candidatos",
        ">Ver pronósticos<",
        "pronósticos reales.",
        "Un pronóstico o una recomendación",
        "favoritos, pronósticos y alertas",
        "Importe máximo por pronóstico",
        "pronósticos publicados",
        "pronóstico recomendado",
        'ns_ui("Valor")',
        "favoritos, directo, pronósticos",
        'ui("Pronósticos completos")',
        "Pronósticos completos, SHARK",
        'ui("Pronósticos publicables")',
        'ui("Expediente profesional del pronóstico")',
        "Partidos y directo",
        "Importar pronósticos",
        "Pronóstico en revisión",
        "Calidad datos/pronósticos",
        'ui("Aún no hay pronósticos publicados para este equipo.")',
    ):
        assert required in combined, required

def test_v728_qa_uses_current_client_guard():
    from tools.check_v728_client_experience import scan_templates
    report = scan_templates()
    assert report["ok"] is True
    assert report["score"] == 100
    assert report["status"] == "OK"
    assert report["hard_errors"] == []
    routes = {item["route"] for item in report["critical_screens"]}
    assert "/app" in routes and "/dashboard" not in routes


def test_primary_client_surfaces_use_canonical_spanish_navigation_routes():
    names = (
        "templates/home.html",
        "templates/client_app_center.html",
        "templates/shark.html",
        "templates/sports_hub.html",
        "templates/recommendations.html",
        "templates/favorites.html",
        "templates/track_record.html",
        "templates/client_menu.html",
    )
    combined = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in names)
    for route in ("/calendar", "/live", "/track-record"):
        for suffix in ("'", '"', "?"):
            assert route + suffix not in combined
    for required in ("/calendario", "/directo", "/historico"):
        assert required in combined
