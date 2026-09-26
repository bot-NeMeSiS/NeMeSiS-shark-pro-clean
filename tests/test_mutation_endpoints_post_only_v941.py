"""V941 mutation safety: execution endpoints must never mutate through GET."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

POST_ONLY_PATHS=(
    "/api/data-center/warmup",
    "/api/scheduler/run-now",
    "/api/scheduler/run-calendar",
    "/api/scheduler/run-crests",
    "/api/scheduler/run-odds",
    "/api/scheduler/run-live",
    "/api/admin/data-memory/cleanup",
    "/api/sportsdb/sync-crests",
    "/api/sportsdb/sync-competitions",
    "/api/sportsdb/sync-teams",
    "/api/sportsdb/sync-feed",
    "/api/sportsdb/sync-matches",
    "/api/sportsdb/sync-calendar",
    "/api/sportsdb/sync-results",
    "/api/matches/sync-now",
    "/api/odds/sync-events",
    "/api/odds/sync-odds",
    "/api/picks/publish",
    "/api/picks/archive",
    "/api/shark/ask",
    "/telegram/regenerar-código",
    "/telegram/desvincular",
    "/api/admin/highlights/sync",
    "/api/admin/autonomous-company-sentinel/run",
    "/api/admin/autonomous-company-sentinel/sync-issues",
    "/api/admin/autonomous-sentinel/run",
    "/api/admin/autonomous-sentinel/sync-issues",
    "/api/admin/sentinel/issues/scan",
    "/api/admin/sentinel/issues/sync-autopilot",
    "/api/admin/sentinel/issues/sync-visual-worker",
    "/api/admin/sentinel-autopilot/run",
    "/api/admin/shark-sentinel/run",
    "/api/admin/continuous-sentinel/run",
    "/api/admin/visual-worker/run",
    "/api/admin/daily-automation/dry-run",
    "/api/telegram/auto-run",
    "/api/v495/telegram-auto-run",
    "/api/telegram/scheduler-tick",
    "/api/automation/highlights/sync",
    "/api/automation/daily/run",
    "/api/automation/sports/sync",
    "/api/automation/telegram/tick",
    "/api/automation/picks/grade",
    "/api/automation/data-backup/run",
    "/api/automation/master-tick",
    "/api/automation/auto-improvement/run",
    "/api/automation/shark-sentinel/run",
    "/api/automation/continuous-sentinel/run",
    "/api/automation/visual-worker/run",
    "/api/automation/sentinel-autopilot/run",
    "/api/automation/autonomous-sentinel/run",
    "/api/automation/autonomous-company-sentinel/run",
)

def test_mutation_routes_are_post_only_in_flask_map():
    import app
    rules={rule.rule:set(rule.methods or ()) for rule in app.app.url_map.iter_rules()}
    for path in POST_ONLY_PATHS:
        assert path in rules, path
        assert "POST" in rules[path], path
        assert "GET" not in rules[path], path

def test_mutation_route_contract_is_documented_in_source():
    source=(ROOT/"app.py").read_text(encoding="utf-8")
    for path in POST_ONLY_PATHS:
        assert f'@app.route("{path}", methods=["POST"])' in source


def test_admin_run_ui_uses_post_or_explicit_post_fetch():
    templates = {
        "admin_highlights_center.html": "/api/admin/highlights/sync",
        "admin_sentinel_autopilot.html": "/api/admin/sentinel-autopilot/run",
        "admin_autonomous_sentinel.html": "/api/admin/autonomous-sentinel/run",
        "admin_visual_worker.html": "/api/admin/visual-worker/run",
        "admin_daily_automation.html": "/api/admin/daily-automation/dry-run",
    }
    for name, endpoint in templates.items():
        text=(ROOT/"templates"/name).read_text(encoding="utf-8")
        assert endpoint in text
        assert f'href="{endpoint}' not in text
        assert 'method="post"' in text

    company=(ROOT/"templates"/"admin_autonomous_company_sentinel.html").read_text(encoding="utf-8")
    assert 'data-v904-method="POST"' in company
    assert company.count('data-v904-method="POST"') >= 4

    base=(ROOT/"templates"/"base.html").read_text(encoding="utf-8")
    assert "X-CSRF-Token" in base
    assert "data-v904-method" in base

