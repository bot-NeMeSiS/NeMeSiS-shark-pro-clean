"""V941 archived-template purge regression.

These files had no Flask renderer, no Jinja import/include, and no active
test/tool consumer. They must not return to the deployable tree.
"""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

PURGED = {
    "templates/admin_shark_sentinel.html",
    "templates/admin_shark_center.html",
    "templates/admin_autonomous_sentinel.html",
    "templates/admin_command_center.html",
    "templates/admin_commercial_readiness.html",
    "templates/admin_compliance_center.html",
    "templates/admin_data_depth.html",
    "templates/admin_growth_center.html",
    "templates/admin_intelligence.html",
    "templates/admin_live_depth.html",
    "templates/betting_recommendations.html",
    "templates/components/v832_design_system.html",
    "templates/data_depth.html",
    "templates/discovery.html",
    "templates/error_controlled.html",
    "templates/growth_client.html",
    "templates/ia_shark.html",
    "templates/sports_intelligence.html",
}


def test_archived_templates_are_absent_from_deploy_tree():
    assert all(not (ROOT / path).exists() for path in PURGED)


def test_runtime_does_not_render_purged_templates():
    names = {Path(path).name for path in PURGED}
    renderers = [ROOT / "app.py"]
    renderers += list((ROOT / "blueprints").glob("*.py"))
    renderers += list((ROOT / "engines").glob("*.py"))
    renderers += list((ROOT / "services").glob("*.py"))
    found = []
    for path in renderers:
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            arg = node.args[0]
            if name == "render_template" and isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if Path(arg.value).name in names:
                    found.append((str(path.relative_to(ROOT)), node.lineno, arg.value))
    assert found == []


def test_shark_sentinel_alias_uses_continuous_ui():
    source = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    alias = source.index('@app.route("/admin/shark-sentinel")')
    function = source.index("def admin_continuous_sentinel_page()", alias)
    rendered = source.index('render_template("admin_continuous_sentinel.html"', function)
    assert alias < function < rendered
