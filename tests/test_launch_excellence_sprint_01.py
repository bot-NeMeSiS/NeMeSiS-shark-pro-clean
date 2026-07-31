from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="strict")


def test_launch_excellence_home_guidance_is_present():
    home = read_text("templates/home.html")
    required = [
        'data-launch-excellence="home-start"',
        'data-launch-onboarding="first-run"',
        'Entiende NeMeSiS en 30 segundos',
        'Continua sin buscar otra vez',
        'data-launch-continue="last-route"',
        'data-launch-last-match="true"',
        '/daily-briefing',
        '/evening-recap',
        '/activity-center',
    ]
    for snippet in required:
        assert snippet in home
    assert '/player/101' not in home


def test_launch_excellence_client_js_is_local_and_safe():
    js = read_text("static/v937-product-client.js")
    required = [
        'nemesis.launch.recentRoutes.v1',
        'nemesis.launch.onboarding.dismissed.v1',
        'allowedRoutePrefixes',
        'data-launch-onboarding-dismiss',
        'data-launch-last-match',
    ]
    for snippet in required:
        assert snippet in js
    forbidden = ['fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', '/api/admin', 'stripe']
    lowered = js.lower()
    for snippet in forbidden:
        assert snippet.lower() not in lowered


def test_launch_excellence_css_accessibility_and_mobile_rules_exist():
    css = read_text("static/v933-product.css")
    required = [
        'Launch Excellence Sprint 01',
        '.v933-launch-start-strip',
        '.v933-launch-onboarding',
        '.v933-launch-continuity-grid',
        'min-height: 44px',
        'prefers-reduced-motion: reduce',
        'touch-action: manipulation',
    ]
    for snippet in required:
        assert snippet in css


def test_launch_excellence_roadmap_and_reports_are_registered():
    roadmap = read_text("engines/project_operating_system_engine.py")
    assert 'Launch Excellence Sprint 01' in roadmap
    assert 'reports/LAUNCH_EXCELLENCE_SPRINT_01_REPORT.md' in roadmap
    report_files = [
        'reports/LAUNCH_EXCELLENCE_SPRINT_01_REPORT.md',
        'reports/ONBOARDING_REVIEW_REPORT.md',
        'reports/UX_POLISH_REPORT.md',
        'reports/MOBILE_EXPERIENCE_REPORT.md',
        'reports/ACCESSIBILITY_REPORT.md',
    ]
    for file_name in report_files:
        assert (ROOT / file_name).is_file()


def test_launch_excellence_does_not_add_routes_or_runtime_version():
    app = read_text("app.py")
    assert 'launch-excellence' not in app
    assert 'LAUNCH_EXCELLENCE' not in app
    version = read_text("VERSION.txt")
    assert 'LAUNCH_EXCELLENCE' not in version
