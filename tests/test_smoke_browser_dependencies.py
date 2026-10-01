"""Regression for Actions collection failing before browser tests could execute."""
from pathlib import Path
import ast
import shlex

import pytest


ROOT = Path(__file__).resolve().parents[1]


def validate_fast_test_imports(source):
    for node in ast.walk(ast.parse(source)):
        modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                   else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
        assert not any(name == 'playwright' or name.startswith('playwright.') for name in modules), (
            'Browser regressions belong after runtime installation, outside the fast gate')


def validate_browser_setup(workflow):
    # Validate the literal shell commands used by this existing workflow.
    commands = [(index, shlex.split(line.strip().removeprefix("run: ")))
                for index, line in enumerate(workflow.splitlines())
                if line.strip().startswith(("pip ", "pytest ", "run: python ", "run: pytest"))]
    dependencies = [i for i, cmd in commands if cmd == ["pip", "install", "-r", "browser_qa/playwright_requirements.txt"]]
    browsers = [i for i, cmd in commands if cmd == ["python", "-m", "playwright", "install", "--with-deps", "chromium"]]
    tests = [i for i, cmd in commands if cmd == ["pytest"]]
    assert dependencies and browsers and tests, "Browser dependency, runtime and full suite are required"
    assert dependencies[0] < browsers[0] < tests[0]
    for index, cmd in commands:
        if index < browsers[0] and cmd and cmd[0] == 'pytest':
            for path in cmd[1:]:
                if path.startswith('tests/') and path.endswith('.py'):
                    validate_fast_test_imports((ROOT / path).read_text(encoding='utf-8'))
    assert "continue-on-error:" not in workflow
    assert "playwright" in (ROOT / "browser_qa/playwright_requirements.txt").read_text().splitlines()


def test_smoke_installs_browser_before_unchanged_full_suite():
    validate_browser_setup((ROOT / ".github/workflows/nemesis-smoke.yml").read_text())


@pytest.mark.parametrize('source', ['import playwright.sync_api',
                                  'def test_worker():\n    from playwright.sync_api import sync_playwright'])
def test_browser_dependency_in_fast_gate_is_rejected(source):
    with pytest.raises(AssertionError):
        validate_fast_test_imports(source)


@pytest.mark.parametrize("removed", ["pip install -r browser_qa/playwright_requirements.txt", "python -m playwright install --with-deps chromium", "pytest"])
def test_missing_dependency_browser_or_tests_is_still_a_failure(removed):
    workflow = (ROOT / ".github/workflows/nemesis-smoke.yml").read_text().replace(removed, "echo missing-command")
    with pytest.raises(AssertionError):
        validate_browser_setup(workflow)
