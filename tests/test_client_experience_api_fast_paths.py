"""Fast-path contracts for presentation-only client experience APIs."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")


def _function_source(name):
    node = next(
        node for node in ast.parse(SOURCE).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    return ast.get_source_segment(SOURCE, node) or ""


def test_client_experience_apis_use_compact_context():
    for name in (
        "api_v757_client_app_center",
        "api_v758_device_experience",
        "api_client_v777_product_experience",
        "api_client_v778_product_organization",
    ):
        route = _function_source(name)
        assert "v932_safe_dashboard_data(request.path, compact=True)" in route
        assert "dashboard_data()" not in route


def test_client_experience_apis_keep_auth_guards():
    for name in (
        "api_v757_client_app_center",
        "api_v758_device_experience",
        "api_client_v777_product_experience",
        "api_client_v778_product_organization",
    ):
        route = _function_source(name)
        assert "current_session_user()" in route
        assert '"login_required"' in route
        assert "403" in route


def test_product_apis_keep_real_track_record_context():
    for name in (
        "api_v757_client_app_center",
        "api_client_v777_product_experience",
        "api_client_v778_product_organization",
    ):
        assert "v742_track_record_context()" in _function_source(name)


def test_device_api_stays_presentation_only():
    route = _function_source("api_v758_device_experience")
    assert "build_v758_device_api_payload(" in route
    for marker in ("sync_", "fetch_odds_events", "sportsdb_v1", "telegram_send", "stripe"):
        assert marker not in route
