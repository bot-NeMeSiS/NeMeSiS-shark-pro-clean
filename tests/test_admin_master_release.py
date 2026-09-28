"""Release identity and static integration gates; no application import or IO mutations."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V941_ADMIN_PC_MASTER_CONTROL_CENTER_SHARK_AI_OPERATING_SYSTEM"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig")


def route_inventory() -> set[str]:
    routes = set()
    for path in [ROOT / "app.py", *sorted((ROOT / "blueprints").glob("*.py"))]:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not decorator.args:
                    continue
                if getattr(decorator.func, "attr", "") not in {"route", "get", "post"}:
                    continue
                route = decorator.args[0]
                if isinstance(route, ast.Constant) and isinstance(route.value, str):
                    routes.add(route.value)
    return routes


def test_release_authorities_and_service_worker_agree():
    assert read("VERSION.txt").strip() == VERSION
    assert read("APP_VERSION").strip() == VERSION
    tree = ast.parse(read("app.py"))
    versions = [
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "APP_VERSION" for target in node.targets)
        and isinstance(node.value, ast.Constant)
    ]
    assert versions == [VERSION]
    assert re.search(r"const NEMESIS_CACHE=['\"]NEMESIS_CACHE_V941(?:_ICON_|['\"])", read("app.py"))


def test_all_jinja_templates_parse():
    environment = Environment()
    failures = []
    for path in sorted((ROOT / "templates").rglob("*.html")):
        try:
            environment.parse(path.read_text(encoding="utf-8-sig"))
        except Exception as error:
            failures.append(f"{path.relative_to(ROOT)}: {error}")
    assert not failures, "\n".join(failures)


def test_control_center_retains_both_canonical_entrypoints():
    routes = route_inventory()
    assert {"/admin/dashboard", "/admin/control-center"} <= routes


def test_literal_admin_navigation_targets_resolve():
    """Catches newly visible dead links without starting background jobs."""
    routes = route_inventory()
    targets = set()
    for relative in ("templates/admin_dashboard.html", "templates/components/v933_navigation.html"):
        source = read(relative)
        targets.update(re.findall(r"""["'](/admin/[A-Za-z0-9_/-]+)(?:[?#][^"']*)?["']""", source))
    assert targets, "No admin navigation targets found"
    assert not sorted(targets - routes), f"Unregistered admin destinations: {sorted(targets - routes)}"


def test_master_static_assets_are_packaged_and_template_uses_them():
    source = read("templates/admin_dashboard.html")
    for filename in ("admin-master-control.css", "admin-master-control.js"):
        assert (ROOT / "static" / filename).is_file(), filename
        assert filename in source, f"Admin does not reference {filename}"


def test_master_view_has_no_placeholder_navigation():
    source = read("templates/admin_dashboard.html")
    assert not re.search(r"""href\s*=\s*["'](?:#|javascript:[^"']*)["']""", source, re.I)
    assert not re.search(r"""(?:action|src)\s*=\s*["']javascript:""", source, re.I)


@pytest.mark.parametrize("relative", [
    "app.py",
    "tools/check_admin_master_control.py",
])
def test_release_python_sources_parse(relative):
    ast.parse(read(relative), filename=relative)



def test_sprint_label_does_not_override_runtime_identity(tmp_path):
    from tools.print_release_identity import runtime_identity
    from tools.check_v944_match_center_foundation import BASE_RUNTIME, SPRINT
    assert BASE_RUNTIME.startswith("V940_") and SPRINT.startswith("V944_")
    (tmp_path / "VERSION.txt").write_text(VERSION)
    (tmp_path / "APP_VERSION").write_text(VERSION)
    (tmp_path / "app.py").write_text("APP_VERSION = " + repr(VERSION))
    identity = runtime_identity(tmp_path)
    assert identity["ok"] and identity["runtime_version"] == VERSION
    assert identity["deployment_certified"] is False


@pytest.mark.parametrize("mutation", ["missing", "mismatch", "duplicate", "sprint_only"])
def test_release_identity_fails_closed_on_missing_or_conflicting_evidence(tmp_path, mutation):
    from tools.print_release_identity import runtime_identity
    (tmp_path / "VERSION.txt").write_text(VERSION)
    (tmp_path / "APP_VERSION").write_text(VERSION)
    (tmp_path / "app.py").write_text("APP_VERSION = " + repr(VERSION))
    if mutation == "missing":
        (tmp_path / "APP_VERSION").unlink()
    elif mutation == "mismatch":
        (tmp_path / "APP_VERSION").write_text("V940_UNEXPECTED_RUNTIME")
    elif mutation == "duplicate":
        (tmp_path / "app.py").write_text("APP_VERSION = " + repr(VERSION) + "\nAPP_VERSION = 'V944_CHECK'")
    else:
        (tmp_path / "app.py").write_text("SPRINT = " + repr(VERSION))
    identity = runtime_identity(tmp_path)
    assert not identity["ok"] and identity["errors"]
    assert identity["deployment_certified"] is False


@pytest.mark.parametrize("cache,expected", [("V941_ICON_1", "V941"), ("V940", "V940"), ("unknown", "unknown")])
def test_cache_identity_parses_actual_runtime_prefix(cache, expected):
    from tools.print_release_identity import service_worker_cache_from_source
    assert service_worker_cache_from_source("const NEMESIS_CACHE='NEMESIS_CACHE_" + cache + "';") == expected


@pytest.mark.parametrize("template", ["admin_dashboard.html", "admin_users.html", "admin_picks.html"])
def test_master_buttons_use_identifiable_delegated_action_contract(template):
    from engines.navigation_integrity_engine import _NavigationHTMLParser
    parser = _NavigationHTMLParser("templates/"+template)
    parser.feed(read("templates/"+template))
    assert not [item for item in parser.entries
                if item["kind"] == "button" and not item.get("has_identifier")]
    # The auditor must continue rejecting a genuinely inert, unbound control.
    inert = _NavigationHTMLParser("unbound.html")
    inert.feed('<button type="button">Unbound action</button>')
    assert any(item["kind"] == "button" and not item.get("has_identifier") for item in inert.entries)


@pytest.mark.parametrize("tag", ["button", "input", "select", "textarea"])
@pytest.mark.parametrize("closing", [">", "/>"])
def test_preview_controls_remain_read_only_with_session_context(tag, closing):
    from blueprints.admin_master_control import _preview_links
    from html.parser import HTMLParser
    controls = []
    class Parser(HTMLParser):
        def handle_starttag(self, name, attrs):
            controls.append((name, dict(attrs)))
    source = '<'+tag+' class="fav-star" onclick="writeFavorite()" formaction="/checkout"'+closing
    parser = Parser()
    parser.feed(_preview_links(source, "PRO"))
    assert len(controls) == 1
    name, attrs = controls[0]
    assert name == tag and "disabled" in attrs
    assert "onclick" not in attrs and "formaction" not in attrs
    assert attrs["class"] == "fav-star"
