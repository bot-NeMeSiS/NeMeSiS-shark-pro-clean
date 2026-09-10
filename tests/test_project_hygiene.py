"""Release path policy, evaluated without importing the side-effecting builder."""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def release_includes():
    tree = ast.parse((ROOT / "tools/build_clean_release.py").read_text(encoding="utf-8-sig"))
    namespace = {"ROOT": ROOT, "Path": Path}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    namespace[target.id] = value
    include = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "include")
    # Execute the actual pure selector, never release_output_dir or main.
    exec(compile(ast.Module(body=[include], type_ignores=[]), "release-path-policy", "exec"), namespace)
    return lambda relative: namespace["include"](ROOT / relative)


@pytest.mark.parametrize("relative", [
    "reports/V915_QA/__pycache__/worker.pyc",
    "reports/V915_QA/result.pyc",
    "reports/V915_QA/local.db",
    "reports/V915_QA/local.sqlite",
    "reports/V915_QA/local.log",
    "reports/V915_QA/nested.zip",
    "reports/V915_QA/local.tmp",
    "reports/V915_QA/.codex/config.toml",
    "reports/V915_QA/Thumbs.db",
    "reports/V915_QA/access_token.txt",
    ".tmp_pytest_owned/result.json",
    ".nemesis_test_owned/result.json",
    ".tmp_reference_review/private/manifest.json",
    "data/local_dev/qa.sqlite",
    "tools/__pycache__/runner.pyc",
])
def test_regenerable_or_private_artifact_cannot_reenter_release(relative, release_includes):
    assert release_includes(relative) is False


@pytest.mark.parametrize("relative", [
    "app.py",
    "engines/sports_domain_model_engine.py",
    "tests/test_coord_sports_evidence.py",
    "static/v933_design_tokens.css",
    "templates/match_detail.html",
    "reports/V915_SECURITY_SECRET_GUARD_REPORT.md",
    "reports/V915_QA/summary.json",
    "data/runtime/automation_workforce/latest_run.json",
    "data/runtime/automation_workforce/v935_workers/navigation.json",
])
def test_existing_source_and_explicit_report_contracts_stay_included(relative, release_includes):
    assert release_includes(relative) is True
