from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="strict")


def test_product_excellence_sprint_02_top100_markers_are_present():
    checks = {
        "templates/track_record.html": [
            'data-top100-improvement="7"',
            "Metodología del histórico",
            "Entra en el cálculo",
            "Muestra suficiente",
        ],
        "templates/support.html": [
            'data-top100-improvement="9,10"',
            "Cómo pedir ayuda sin perder tiempo",
            "Cancelación / cambio de plan",
            "Privacidad / datos personales",
        ],
        "templates/membership.html": [
            'data-top100-improvement="10"',
            "Cambiar o cancelar sin fricción",
            "Sin presión",
        ],
        "templates/profile.html": [
            'data-top100-improvement="14,15,16"',
            "Privacidad y medición de uso",
            "Primer uso real",
            "Hábito sin invasión",
        ],
        "templates/user_intelligence_center.html": [
            'data-top100-improvement="14,15,16"',
            "Qué se mide y qué no",
            "Centro de inteligencia de usuario",
            "state_labels.get(privacy.consent_state",
        ],
        "templates/home.html": [
            'data-top100-improvement="17"',
            "Estado de datos deportivos",
            "sports-metrics-v1",
            "Esperando sincronización",
        ],
        "templates/favorites.html": [
            'data-top100-improvement="18"',
            "Crea tu primer favorito",
            'id="add-favorite-manual"',
            "Añadir manualmente",
        ],
        "templates/action_platform.html": [
            'data-top100-improvement="20"',
            "Recap nocturno",
            "Siguiente acción útil",
            "esta sección",
        ],
        "templates/daily_briefing.html": [
            'data-top100-improvement="20"',
            "Después de la jornada",
            "Abrir recap nocturno",
        ],
    }
    for file_name, snippets in checks.items():
        text = read_text(file_name)
        for snippet in snippets:
            assert snippet in text


def test_product_excellence_sprint_02_visible_copy_has_no_known_regressions():
    files = [
        "templates/action_platform.html",
        "templates/daily_briefing.html",
        "templates/favorites.html",
        "templates/home.html",
        "templates/membership.html",
        "templates/profile.html",
        "templates/support.html",
        "templates/track_record.html",
        "templates/user_intelligence_center.html",
    ]
    bad_fragments = [
        "Aadir",
        "Siguiente accion",
        "está seccion",
        "C?mo",
        "competici?n",
        "fricci?n",
        "Metodolog?a",
        "Aplicaci?n",
        "Personalizaci?n",
        "sincronizaci?n",
        "contrase?as",
        "�",
    ]
    for file_name in files:
        text = read_text(file_name)
        for fragment in bad_fragments:
            assert fragment not in text


def test_product_excellence_sprint_02_profile_card_is_not_duplicated():
    profile = read_text("templates/profile.html")
    assert profile.count("profile_card(user, plan") == 1


def test_product_excellence_sprint_02_uses_existing_routes_only():
    app = read_text("app.py")
    expected_routes = [
        "def v724_contact_alias_page",
        "def membership_page",
        "def profile_page",
        "def user_intelligence_center_page",
        "def favorites_page",
        "def daily_briefing_page",
        "def action_evening_recap_page",
    ]
    for route_marker in expected_routes:
        assert route_marker in app

    forbidden_new_route_markers = [
        "product-excellence-sprint-02",
        "top100-sprint-02",
    ]
    for route_marker in forbidden_new_route_markers:
        assert route_marker not in app


def test_memberships_uses_compact_cache_first_sports_context():
    app = read_text("app.py")
    membership_handler = app.split("def membership_page():", 1)[1].split(
        '@app.route("/shark-ai")', 1
    )[0]
    assert "v932_safe_dashboard_data(request.path, compact=True)" in membership_handler
