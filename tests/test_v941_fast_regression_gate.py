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
        "test_revenue_readonly_safety.py",
        "test_subscription_revenue_truth_v941.py",
        "test_shark_membership_limits_v941.py",
        "test_automation_schedule_minimal.py",
        "test_privacy_classification_v941.py",
        "test_mutation_endpoints_post_only_v941.py",
        "test_legacy_automation_safety_v941.py",
        "test_active_cron_header_transport_v941.py",
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
