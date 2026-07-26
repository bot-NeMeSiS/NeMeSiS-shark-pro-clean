from __future__ import annotations

import re
import zipfile
from pathlib import PurePosixPath

from v929_check_support import ROOT, VERSION, finish, load_json, prepare_app


V930_VERSION = "V930_CANONICAL_REFERENCE_VISUAL_PARITY_ADMIN_CLIENT_MOBILE_FINAL"
V931_VERSION = "V931_PRODUCTION_CLIENT_ROUTES_AND_HOME_DATA_CONSISTENCY_HOTFIX_FINAL"
V932_VERSION = "V932_AUTHENTICATED_PRODUCTION_CLIENT_ADMIN_AND_REAL_SPORTS_VALUE_FINAL"
V933_VERSION = "V933_REFERENCE_PARITY_PRODUCT_DESIGN_SPRINT_SYSTEM_FINAL"
V934_VERSION = "V934_REFERENCE_EXACTNESS_REALTIME_SPORTS_PRODUCTION_PERFECTION_FINAL"
V935_VERSION = "V935_LAUNCH_TRUST_REAL_DATA_LIFECYCLE_PERFORMANCE_REFERENCE_POLISH_FINAL"
V936_VERSION = "V936_COMMERCIAL_PRODUCT_READINESS_REFERENCE_EXCELLENCE_FINAL"
V937_VERSION = "V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL"
V938_VERSION = "V938_COMPANY_OPERATIONS_RECOVERY_OBSERVABILITY_CENTER_FINAL"
V939_VERSION = "V939_AUTONOMOUS_COMPANY_INTELLIGENCE_GROWTH_AND_QUALITY_PLATFORM_FINAL"


def main() -> int:
    app_module = prepare_app()
    client = app_module.app.test_client()
    runtime_response = client.get("/api/runtime-version")
    runtime = runtime_response.get_json(silent=True) or {}
    matrix = load_json(ROOT / "reports" / "V929_FULL_NAVIGATION_ROUTE_MATRIX.json")
    click = load_json(ROOT / "reports" / "V929_CLICK_NAVIGATION_MATRIX.json")
    version_raw = (ROOT / "VERSION.txt").read_bytes()
    current_version = version_raw.decode("utf-8").strip().lstrip("\ufeff")
    zip_path = ROOT / "release_output" / "NeMeSiS_SHARK_PRO_V929_NAVIGATION_INTEGRITY_ROUTE_NOT_FOUND_FULL_APP_RECOVERY_FINAL_RENDER_READY.zip"
    zip_clean = True
    if zip_path.exists():
        forbidden_parts = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output", "logs"}
        forbidden_suffixes = {".db", ".sqlite", ".sqlite3", ".log", ".zip"}
        with zipfile.ZipFile(zip_path) as archive:
            for name in archive.namelist():
                path = PurePosixPath(name)
                if (
                    set(path.parts) & forbidden_parts
                    or path.name == ".env"
                    or any(path.name.lower().endswith(suffix) for suffix in forbidden_suffixes)
                ):
                    zip_clean = False
                    break
    checks = {
        "version_v929_or_successor": bool(re.match(r"^V(\d+)", current_version) and int(re.match(r"^V(\d+)", current_version).group(1)) >= 929),
        "version_without_bom": not version_raw.startswith(b"\xef\xbb\xbf"),
        "app_version": app_module.APP_VERSION == current_version,
        "runtime_200": runtime_response.status_code == 200,
        "runtime_version": runtime.get("version") == current_version,
        "version_files_match": runtime.get("version_files_match") is True,
        "deployment_aligned": runtime.get("deployment_alignment_status") == "aligned_local_files",
        "flags_v929": all(runtime.get(key) is True for key in (
            "has_v929_navigation_integrity", "has_v929_route_not_found_video_fix",
            "has_v929_internal_link_audit", "has_v929_dynamic_route_guard",
            "has_v929_admin_client_navigation_separation", "has_v929_mobile_navigation_guard",
            "has_v929_navigation_worker", "has_v929_click_browser_qa",
        )),
        "video_route_fixed": client.get("/clientes", follow_redirects=False).status_code in {301, 302, 303, 307, 308},
        "matrix_clean": int(matrix.get("broken_links") or 0) == 0,
        "click_matrix_clean": int(click.get("failures_count") or 0) == 0 and int(click.get("clicks_tested") or 0) > 0,
        "admin_summary_protected": client.get("/api/admin/navigation-integrity/summary").status_code == 403,
        "admin_run_protected": client.post("/api/admin/navigation-integrity/run").status_code == 403,
        "engine_exists": (ROOT / "engines" / "navigation_integrity_engine.py").exists(),
        "worker_exists": (ROOT / "automation_workforce" / "navigation_integrity_worker.py").exists(),
        "panel_exists": (ROOT / "templates" / "admin_navigation_integrity.html").exists(),
        "zip_clean_if_present": zip_clean,
    }
    return finish("V929 navigation integrity", checks, {
        "links_audited": matrix.get("links_audited", 0),
        "clicks_tested": click.get("clicks_tested", 0),
    })


if __name__ == "__main__":
    raise SystemExit(main())
