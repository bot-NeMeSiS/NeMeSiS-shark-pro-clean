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

