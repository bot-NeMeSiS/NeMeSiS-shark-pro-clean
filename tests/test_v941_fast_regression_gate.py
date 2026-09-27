"""V941 fast-fail contract for regressions already seen in PR92."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_smoke_runs_known_regressions_before_browser_install():
    workflow=(ROOT/".github/workflows/nemesis-smoke.yml").read_text(encoding="utf-8")
    gate=workflow.index("V941 known regression gate")
    browser=workflow.index("Install test browser")
    assert gate < browser
    required=(
        "test_product_excellence_sprint_02.py",
        "test_data_backup_master_dedupe.py",
        "test_product_language_clarity.py",
        "test_project_hygiene.py",
        "test_revenue_readonly_safety.py",
        "test_subscription_revenue_truth_v941.py",
        "test_shark_membership_limits_v941.py",
        "test_automation_schedule_minimal.py",
        "test_privacy_classification_v941.py",
        "test_public_api_scope_v941.py",
        "test_navigation_classification_v941.py",
        "test_mutation_endpoints_post_only_v941.py",
        "test_legacy_automation_safety_v941.py",
        "test_active_cron_header_transport_v941.py",
        "test_get_business_readonly_v941.py",
        "test_pronosticos_terminology.py",
        "test_calendar_terminology.py",
        "test_pwa_easy_install.py",
        "test_pwa_shareable_install_guide.py",
        "test_admin_shark_ai.py",
    )
    for name in required:
        assert name in workflow

def test_fast_gate_uses_isolated_database_and_blocks_auto_actions():
    workflow=(ROOT/".github/workflows/nemesis-smoke.yml").read_text(encoding="utf-8")
    assert "DB_PATH: /tmp/nemesis_fast_regression.db" in workflow
    assert "AUTO_GENERATE_PICKS: 'false'" in workflow
    assert "AUTO_SEND_TELEGRAM_PICKS: 'false'" in workflow

def test_clean_release_packages_current_reports_not_historical_report_families():
    build=(ROOT/"tools/build_clean_release.py").read_text(encoding="utf-8")
    assert 'rel_posix.startswith(f"reports/{VERSION_PREFIX}_")' in build
    assert 'rel_posix.startswith(f"reports/RELEASE_ZIP_AUDIT_{VERSION_PREFIX}")' in build
    assert '"reports/CODEX_DAILY_PROMPT_CURRENT.txt"' in build
    assert '"reports/LOCAL_CONTINUITY_20260919.md"' in build
    assert '"reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md"' in build
    for legacy in (
        'reports/V748_', 'reports/V860_', 'reports/V939_',
        'reports/RELEASE_ZIP_AUDIT_V759', 'reports/RELEASE_ZIP_AUDIT_V939',
    ):
        assert legacy not in build

def test_ci_artifact_upload_avoids_historical_reports_and_duplicate_deploy_tree():
    workflow=(ROOT/".github/workflows/nemesis-ci.yml").read_text(encoding="utf-8")
    upload=workflow.split("- name: Upload reports and release output", 1)[1]
    assert "reports/V941_*" in upload
    assert "release_output/*_RENDER_READY.zip" in upload
    assert "release_output/RELEASE_ZIP_AUDIT_V941.*" in upload
    assert "\n            reports/\n" not in upload
    assert "\n            release_output/\n" not in upload
    assert "V941_DEPLOY_ROOT_CONTENTS" not in upload

