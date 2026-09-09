"""Regression for Actions collection failing before browser tests could execute."""
from pathlib import Path
import shlex

import pytest


ROOT = Path(__file__).resolve().parents[1]


def validate_browser_setup(workflow):
    # Validate the literal shell commands used by this existing workflow.
    commands = [(index, shlex.split(line.strip().removeprefix("run: ")))
                for index, line in enumerate(workflow.splitlines())
                if line.strip().startswith(("pip ", "run: python ", "run: pytest"))]
    dependencies = [i for i, cmd in commands if cmd == ["pip", "install", "-r", "browser_qa/playwright_requirements.txt"]]
    browsers = [i for i, cmd in commands if cmd == ["python", "-m", "playwright", "install", "--with-deps", "chromium"]]
    tests = [i for i, cmd in commands if cmd == ["pytest"]]
    assert dependencies and browsers and tests, "Browser dependency, runtime and full suite are required"
    assert dependencies[0] < browsers[0] < tests[0]
    assert "continue-on-error:" not in workflow
    assert "playwright" in (ROOT / "browser_qa/playwright_requirements.txt").read_text().splitlines()


def test_smoke_installs_browser_before_unchanged_full_suite():
    validate_browser_setup((ROOT / ".github/workflows/nemesis-smoke.yml").read_text())


@pytest.mark.parametrize("removed", ["pip install -r browser_qa/playwright_requirements.txt", "python -m playwright install --with-deps chromium", "pytest"])
def test_missing_dependency_browser_or_tests_is_still_a_failure(removed):
    workflow = (ROOT / ".github/workflows/nemesis-smoke.yml").read_text().replace(removed, "echo missing-command")
    with pytest.raises(AssertionError):
        validate_browser_setup(workflow)
