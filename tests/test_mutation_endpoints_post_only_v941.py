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
