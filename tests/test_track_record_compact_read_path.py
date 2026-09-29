"""Performance contract for the public/client Track Record read path."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _route_source():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index("def public_track_record_page():")
    end = source.index('\n@app.route("/api/track-record")', start)
    return source[start:end]


def test_track_record_does_not_build_dashboard_or_sports_context():
    route = _route_source()
    assert "dashboard_data(" not in route
    assert "v932_safe_dashboard_data(" not in route
    assert "get_public_home_sports_summary(" not in route
    assert "home_light_data(" not in route


def test_track_record_only_builds_visible_payload():
    route = _route_source()
    assert '"track_record": v931_safe_context(' in route
    for marker in (
        "commercial_launch_snapshot",
        "build_v757_trust_snapshot",
        "build_v757_app_center",
        "v758_adaptive_context",
        "v769_highlights_content_center",
        "get_v935_customer_trust_context",
    ):
        assert marker not in route


def test_track_record_template_only_reads_track_record_route_payload():
    template = (ROOT / "templates" / "track_record.html").read_text(encoding="utf-8")
    assert "data.get('track_record')" in template
    for marker in (
        "data.get('certification')",
        "data.get('v757_track')",
        "data.get('v757_app')",
        "data.get('v758_adaptive')",
        "data.get('v769_highlights_center')",
        "data.get('v935_customer_trust')",
    ):
        assert marker not in template


def test_base_template_does_not_require_removed_track_record_contexts():
    template = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    for marker in (
        "v757_app",
        "v758_adaptive",
        "v769_highlights_center",
        "v935_customer_trust",
        "certification",
    ):
        assert marker not in template
