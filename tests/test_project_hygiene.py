"""Release path policy, evaluated without importing the side-effecting builder."""
import ast
import os
from pathlib import Path
import shutil
import subprocess

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
    "localization/ui.json",
    "project_control/CODEX_QUEUE.md",
    "reports/LOCAL_CONTINUITY_20260919.md",
    "reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md",
    "reports/V915_SECURITY_SECRET_GUARD_REPORT.md",
    "reports/V915_QA/summary.json",
    "data/runtime/automation_workforce/latest_run.json",
    "data/runtime/automation_workforce/v935_workers/navigation.json",
])
def test_existing_source_and_explicit_report_contracts_stay_included(relative, release_includes):
    assert release_includes(relative) is True


def test_every_project_control_http_source_is_shipped(release_includes):
    from engines.project_control_reader import SOURCES
    assert all(release_includes(path) for path in SOURCES.values())


@pytest.mark.parametrize("relative,ignored", [
    ("tests/test_token_policy.py", False),
    ("engines/token_formatter.py", False),
    ("templates/secret_help.html", False),
    ("tools/token_audit.py", False),
    ("static/v933_design_tokens.css", False),
    ("reports/V915_SECURITY_SECRET_GUARD_REPORT.md", False),
    (".env.example", False),
    (".env.render.clean", False),
    (".env.staging", True),
    (".env.production", True),
    ("secrets/credentials.json", True),
    ("access_token.txt", True),
    ("service_secret.json", True),
    ("tools/__pycache__/check.cpython-311.pyc", True),
    ("data/local_dev/qa.sqlite", True),
    ("data/qa_tmp/result.xml", True),
    ("release_output/candidate.zip", True),
    ("logs/local.log", True),
])
def test_gitignore_distinguishes_source_from_local_artifacts(relative, ignored):
    git = shutil.which("git")
    assert git, "Git is required to validate actual ignore semantics"
    result = subprocess.run(
        [git, "--no-optional-locks", "check-ignore", "--no-index", "--quiet", "--", relative],
        cwd=ROOT, capture_output=True, check=False,
    )
    assert result.returncode in (0, 1), result.stderr.decode(errors="replace")
    assert (result.returncode == 0) is ignored


def test_release_collection_prunes_excluded_trees_before_traversal(tmp_path, monkeypatch):
    tree = ast.parse((ROOT / "tools/build_clean_release.py").read_text(encoding="utf-8-sig"))
    collect = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "collect_files")
    namespace = {"ROOT": tmp_path, "Path": Path, "os": os,
                 "EXCLUDE_DIRS": {"__pycache__", ".git", "release_output"},
                 "INCLUDE_TOP_LEVEL_DIRS": {"tools", "reports"},
                 "include": lambda path: path.suffix in (".py", ".json")}
    exec(compile(ast.Module(body=[collect], type_ignores=[]), "release-collection", "exec"), namespace)
    for relative in ["app.py", "tools/check.py", "tools/__pycache__/junk.py", "release_output/copy.py",
                     "data/local_dev/qa.py", ".tmp_reference_review/nested/app.py", "data/runtime/state.json"]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    walked = []
    original_walk = os.walk
    def record_walk(*args, **kwargs):
        for item in original_walk(*args, **kwargs):
            walked.append(Path(item[0]).relative_to(tmp_path).as_posix())
            yield item
    monkeypatch.setattr(os, "walk", record_walk)
    assert {p.relative_to(tmp_path).as_posix() for p in namespace["collect_files"]()} == {
        "app.py", "tools/check.py", "data/runtime/state.json",
    }
    assert not any(any(part in path.split("/") for part in
                       ("release_output", "__pycache__", "local_dev", ".tmp_reference_review")) for path in walked)
