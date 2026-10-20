from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="strict")


def test_launch_excellence_home_guidance_is_present():
    home = read_text("templates/home.html")
    required = [
        'data-launch-excellence="home-start"',
        '<details class="v933-home-more" data-home-extras>',
        'class="v933-home-more-summary"',
        'data-launch-onboarding="first-run"',
        'Entiende NeMeSiS rápido',
        "section_header('Continuar'",
        'data-launch-continue="last-route"',
        'data-launch-last-match="true"',
        '/daily-briefing',
        '/evening-recap',
        '/activity-center',
    ]
    for snippet in required:
        assert snippet in home
    assert home.index('<summary class="v933-home-more-summary">') < home.index('data-launch-onboarding="first-run"')
    assert home.rstrip().endswith('{% endblock %}')
    assert '/player/101' not in home


def test_home_has_one_primary_action_without_repeating_it_in_the_access_strip():
    home = read_text("templates/home.html")
    signed_in, remainder = home.split("{% if current_user %}", 1)[1].split("{% else %}", 1)
    public, remainder = remainder.split("{% endif %}", 1)
    access_strip = remainder.split('data-home-secondary-actions>', 1)[1].split('</nav>', 1)[0]

    assert signed_in.count("action_button(") == 1
    assert public.count("action_button(") == 1
    assert "data-home-primary-action" in home
    assert '{% if not current_user %}<a href="/directo">' in access_strip
    assert '<a href="/calendario">' in access_strip
    assert '<a href="/favoritos">' in access_strip
    assert '<a href="/picks">' in access_strip


def test_launch_excellence_client_js_is_local_and_safe():
    js = read_text("static/v937-product-client.js")
    required = [
        'nemesis.launch.recentRoutes.v1',
        'nemesis.launch.onboarding.dismissed.v1',
        'allowedRoutePrefixes',
        'data-launch-onboarding-dismiss',
        'data-launch-last-match',
        'homeExtras.open = true',
        'homeExtras.open = false',
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


def test_home_disclosure_visual_rules_are_scoped_to_the_home_only():
    css = read_text("static/home-league-disclosure.css")
    assert 'details.v933-home-more[data-home-extras] > summary' in css
    assert 'details[data-home-extras][open] .home-more-chevron' in css
    assert 'body.ns-app .ns16-home .v933-match-teams strong' in css
    assert '.v933-home-more > summary' not in css


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
