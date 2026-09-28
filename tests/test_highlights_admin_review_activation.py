"""Admin-only activation contract for the recovered Highlights review foundation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_media_review_is_mounted_by_existing_admin_composition():
    source = (ROOT / "blueprints" / "architecture.py").read_text(encoding="utf-8")
    assert "create_media_review_blueprint" in source
    assert "bp.register_blueprint(create_media_review_blueprint(db_path, _admin_required))" in source


def test_highlights_review_routes_are_registered_and_protected(app_module, client):
    routes = {rule.rule for rule in app_module.app.url_map.iter_rules()}
    assert "/admin/highlights-review" in routes
    assert "/api/admin/highlights/readiness" in routes
    assert "/admin/highlights-review/<highlight_id>/decision" in routes
    assert "/admin/highlights-review/sync" in routes

    page = client.get("/admin/highlights-review")
    api = client.get("/api/admin/highlights/readiness")
    assert page.status_code == 403
    assert api.status_code == 403
    assert page.get_json()["error"] == "admin_required"
    assert api.get_json()["error"] == "admin_required"


def test_existing_admin_highlights_center_links_to_rights_review():
    template = (ROOT / "templates" / "admin_highlights_center.html").read_text(encoding="utf-8")
    assert 'href="/admin/highlights-review"' in template
    assert "Revisar derechos" in template


def test_activation_does_not_mount_client_player_or_telegram_delivery():
    source = (ROOT / "blueprints" / "architecture.py").read_text(encoding="utf-8")
    assert "highlight_player" not in source
    assert "telegram" not in (ROOT / "blueprints" / "media_review.py").read_text(encoding="utf-8").lower().replace(
        "never changes rights or sends telegram", ""
    )
