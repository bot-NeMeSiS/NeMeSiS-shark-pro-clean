"""V941 admin JS-only form contract: explicit marker plus real submit handler."""
from pathlib import Path

from tools.audit_all_routes_links import _js_submit_bound, scan_template_links

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "master-chat-form",
    "master-settings-form",
    "reliability-verification-form",
    "reliability-resolve-form",
}


def test_admin_js_only_forms_are_explicit_and_bound():
    scan = scan_template_links()
    assert scan["forms_without_action"] == []
    assert scan["js_only_forms_unbound"] == []
    assert {item["id"] for item in scan["js_only_forms"]} == EXPECTED
    assert all(item["handler_bound"] for item in scan["js_only_forms"])


def test_admin_js_only_marker_matches_real_submit_handlers():
    dashboard = (ROOT / "templates/admin_dashboard.html").read_text(encoding="utf-8")
    reliability = (ROOT / "templates/components/admin_reliability.html").read_text(encoding="utf-8")
    javascript = (ROOT / "static/admin-master-control.js").read_text(encoding="utf-8")
    combined = dashboard + reliability
    for form_id in EXPECTED:
        assert f'id="{form_id}"' in combined
        assert _js_submit_bound(form_id, javascript)
    assert combined.count('data-js-only-form="true"') == 4
    assert not _js_submit_bound("missing-form", javascript)
    assert "necesitan JavaScript" in dashboard
