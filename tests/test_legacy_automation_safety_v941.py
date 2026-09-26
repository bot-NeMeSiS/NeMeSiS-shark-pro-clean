"""V941 legacy automation and mutation safety contracts."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

ADMIN_MUTATIONS={
    "/api/telegram/repair-automatic",
    "/api/telegram/settings/update",
    "/api/telegram/send-test",
    "/api/telegram/enqueue-daily-matches",
    "/api/telegram/enqueue-daily-picks",
    "/api/telegram/process-queue",
    "/api/telegram/scheduler-manager",
    "/api/telegram/enqueue-recommendations",
}

def _methods(app_module, path):
    rules=[rule for rule in app_module.app.url_map.iter_rules() if rule.rule==path]
    assert rules, path
    return set().union(*(set(rule.methods) for rule in rules))

def test_admin_mutations_are_post_only_and_not_csrf_exempt(app_module):
    for path in ADMIN_MUTATIONS:
        methods=_methods(app_module,path)
        assert "POST" in methods
        assert "GET" not in methods
        assert app_module.csrf_exempt_path(path) is False

def test_legacy_automation_defaults_are_off():
    source=(ROOT/"app.py").read_text(encoding="utf-8")
    for forbidden in (
        'env_bool("ENABLE_TELEGRAM_AUTOMATION", True)',
        'env_bool("TELEGRAM_AUTO_SEND_ENABLED", True)',
        'env_bool("ENABLE_AUTO_LIVE_SYNC", True)',
        'env_bool("ENABLE_AUTO_TELEGRAM_PRO", True)',
    ):
        assert forbidden not in source
    for expected in (
        'env_bool("ENABLE_TELEGRAM_AUTOMATION", False)',
        'env_bool("TELEGRAM_AUTO_SEND_ENABLED", False)',
        'env_bool("ENABLE_AUTO_LIVE_SYNC", False)',
        'env_bool("ENABLE_AUTO_TELEGRAM_PRO", False)',
    ):
        assert expected in source

def test_cron_endpoints_keep_automation_secret_compatibility(app_module):
    for path in (
        "/api/telegram/auto-run",
        "/api/telegram/scheduler-tick",
        "/api/automation/telegram/tick",
    ):
        methods=_methods(app_module,path)
        assert "GET" in methods and "POST" in methods
    assert app_module.csrf_exempt_path("/api/automation/telegram/tick") is True

def test_get_never_executes_manual_telegram_mutation(client):
    for path in ADMIN_MUTATIONS:
        response=client.get(path)
        assert response.status_code==405, (path,response.status_code)
