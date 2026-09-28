"""V941 privacy and preview coverage gate."""
from pathlib import Path
from tools.check_repository_privacy_and_secrets import scan_repository

ROOT=Path(__file__).resolve().parents[1]

def test_repository_privacy_has_no_real_review_candidates():
    result=scan_repository(ROOT, include_privacy=True)
    assert result["confirmed_secret_findings"] == 0
    assert result["secret_review_findings"] == 0
    assert result["privacy_review_findings"] == 0
    assert result["values_printed"] is False
    assert all(item["classification"] == "EXPECTED_FIXTURE" for item in result["privacy_findings"])

def test_preview_contract_contains_all_core_product_surfaces():
    from blueprints.admin_master_control import PAGES, SAFE_ROUTES
    expected={"home","matches","live","picks","history","shark","telegram","profile","memberships"}
    assert set(PAGES) == expected
    assert SAFE_ROUTES["/track-record"] == "history"
    assert PAGES["matches"] == "Calendario"
    assert PAGES["picks"] == "Pronósticos"
    assert PAGES["history"] == "Historial"
    assert PAGES["memberships"] == "Planes"
