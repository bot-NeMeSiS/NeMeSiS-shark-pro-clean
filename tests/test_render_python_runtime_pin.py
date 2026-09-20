from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_render_python_version_is_explicit_and_matches_ci():
    python_version = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    legacy_runtime = (ROOT / "runtime.txt").read_text(encoding="utf-8").strip()
    workflow = (ROOT / ".github" / "workflows" / "render-deploy.yml").read_text(
        encoding="utf-8"
    )

    assert python_version == "3.11.9"
    assert legacy_runtime == "python-3.11.9"
    assert re.search(r'python-version:\s*["\']3\.11\.9["\']', workflow)


def test_python_version_file_contains_only_version():
    value = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", value)
