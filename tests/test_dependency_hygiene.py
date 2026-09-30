"""Dependency boundary: test-only tooling must not ship in Render runtime."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lines(name):
    return [line.strip() for line in (ROOT / name).read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]


def test_pytest_is_dev_only():
    prod = _lines("requirements.txt")
    dev = _lines("requirements-dev.txt")
    assert not any(line.lower().startswith("pytest") for line in prod)
    assert "-r requirements.txt" in dev
    assert "pytest==8.3.4" in dev


def test_smoke_installs_dev_bundle_once():
    workflow = (ROOT / ".github" / "workflows" / "nemesis-smoke.yml").read_text(encoding="utf-8")
    assert "pip install -r requirements-dev.txt" in workflow
    install_block = workflow.split("- name: Install dependencies", 1)[1].split("- name:", 1)[0]
    assert "pip install -r requirements.txt" not in install_block
