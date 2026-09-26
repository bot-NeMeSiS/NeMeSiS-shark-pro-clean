"""V941 canonical browser coverage contract."""
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("v941_click_matrix",ROOT/"tools/run_v929_click_navigation_qa.py")
matrix=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(matrix)

EXPECTED_ADMIN={
    "/admin/dashboard","/admin/matches","/admin/realtime-center","/admin/picks",
    "/admin/telegram/command-center","/admin/users","/admin/memberships","/admin/payments",
    "/admin/shark-center","/admin/data-center","/admin/automation-center","/admin/sentinel-issues",
    "/admin/highlights-center","/admin/system","/admin/final-release",
}
EXPECTED_CLIENT={"/app","/calendar","/live","/picks","/track-record","/shark","/telegram","/profile","/memberships"}

def test_client_real_browser_matrix_covers_all_core_routes_on_mobile_and_desktop():
    assert set(matrix.CLIENT_ORIGINS)==EXPECTED_CLIENT
    assert set(matrix.MOBILE_ORIGINS)==EXPECTED_CLIENT

def test_admin_real_browser_matrix_covers_15_canonical_routes():
    assert set(matrix.ADMIN_ORIGINS)==EXPECTED_ADMIN
    assert len(matrix.ADMIN_ORIGINS)==15

def test_preflight_runs_real_canonical_browser_matrix():
    workflow=(ROOT/".github/workflows/render-deploy.yml").read_text(encoding="utf-8")
    assert "Canonical client and admin browser matrix" in workflow
    assert "python tools/run_v929_click_navigation_qa.py --timeout 15000" in workflow
