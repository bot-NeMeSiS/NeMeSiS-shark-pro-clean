"""Synthetic validator fixtures are not rendered Browser QA evidence."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from tools.check_v944_match_center_foundation import validate_browser_evidence
from tools.run_v944_match_center_browser_qa import (
    COMPONENTS, PROFILES, SCENARIOS, install_boundary, observation_failures, write_result,
)


def capture(scenario, profile):
    return dict(
        scenario=scenario, profile=profile, http=200, path="/match/" + SCENARIOS[scenario],
        shell_count=1, components=list(COMPONENTS),
        component_states=[("MatchHeader", "finished" if scenario == "available" else "ready"),
                          ("Timeline", "ready" if scenario == "available" else "partial"),
                          ("StatsPanel", "ready" if scenario == "available" else "partial")],
        teams=["Club Norte", "Club Sur"] if scenario == "available" else ["Club Este", "Club Oeste"],
        score="2-0" if scenario == "available" else "VS", temporal_labels=["Madrid time fixture"],
        horizontal_overflow=False, clipped_text=[], broken_images=[], admin_links=0,
        js_errors=[], console_errors=[], http_errors=[], external_requests=[],
        navigation=["/calendar", "/match/" + SCENARIOS[scenario]], viewport=list(PROFILES[profile]),
    )


@pytest.fixture
def evidence(tmp_path):
    rows = []
    for scenario in SCENARIOS:
        for profile, size in PROFILES.items():
            row = capture(scenario, profile)
            png = tmp_path / (scenario + "-" + profile + ".png")
            # This image only tests the evidence validator, never the application.
            Image.new("RGB", size, "black").save(png)
            row.update(screenshot=png.name, screenshot_sha256=hashlib.sha256(png.read_bytes()).hexdigest())
            rows.append(row)
    write_result(tmp_path, rows, "test-fingerprint", [], "SIMULATED_VALIDATOR_FIXTURE")
    return tmp_path / "browser_qa_result.json"


def test_complete_artifact_validates(evidence):
    assert validate_browser_evidence(evidence, "test-fingerprint")[1] == []


def test_scaled_screenshot_is_not_complete_browser_evidence(evidence):
    result = json.loads(evidence.read_text(encoding="utf-8"))
    row = result["captures"][0]
    png = evidence.parent / row["screenshot"]
    Image.new("RGB", (1300, 700), "black").save(png)
    row["screenshot_sha256"] = hashlib.sha256(png.read_bytes()).hexdigest()
    updated = write_result(evidence.parent, result["captures"], "test-fingerprint", [], "SIMULATED_VALIDATOR_FIXTURE")
    assert updated["status"] == "FAIL"
    assert "Browser screenshot dimensions/format mismatch" in validate_browser_evidence(evidence, "test-fingerprint")[1]


@pytest.mark.parametrize("defect", ["missing_result", "old_tree", "missing_image", "image_changed", "duplicate_case", "incomplete", "old_pass_only", "outside_image", "production", "network"])
def test_evidence_fails_closed(evidence, defect):
    result = json.loads(evidence.read_text(encoding="utf-8"))
    fingerprint = "test-fingerprint"
    if defect == "missing_result":
        evidence = evidence.with_name("absent.json")
    elif defect == "old_tree":
        fingerprint = "other-candidate"
    elif defect == "missing_image":
        result["captures"][0]["screenshot"] = "absent.png"
    elif defect == "image_changed":
        result["captures"][0]["screenshot_sha256"] = "incorrect"
    elif defect == "duplicate_case":
        result["captures"][1] = copy.deepcopy(result["captures"][0])
    elif defect == "incomplete":
        result["captures"].pop()
    elif defect == "old_pass_only":
        result = {"status": "PASS", "screenshots_captured": 6, "production_modified": False}
    elif defect == "outside_image":
        result["captures"][0]["screenshot"] = "../outside.png"
    elif defect == "production":
        result["production_modified"] = True
    elif defect == "network":
        result["blocked_attempts"] = ["NETWORK"]
    if defect != "missing_result":
        evidence.write_text(json.dumps(result), encoding="utf-8")
    assert validate_browser_evidence(evidence, fingerprint)[1]


@pytest.mark.parametrize("field,value", [
    ("http", 500), ("path", "/cliente-login"), ("shell_count", 2), ("components", []),
    ("teams", ["Wrong", "identity"]), ("score", "0-0"), ("component_states", []),
    ("temporal_labels", []), ("navigation", []), ("viewport", [360, 800]),
    ("horizontal_overflow", True), ("clipped_text", ["button"]), ("broken_images", ["crest"]),
    ("admin_links", 1), ("js_errors", ["fatal"]), ("console_errors", ["error"]),
    ("http_errors", [503]), ("external_requests", ["provider.invalid"]),
])
def test_product_regressions_cannot_be_hidden_by_pass_flag(field, value):
    row = capture("available", "desktop")
    row[field] = value
    assert observation_failures(row)


def test_partial_must_not_invent_zero_score():
    row = capture("partial", "mobile")
    assert not observation_failures(row)
    row["score"] = "0-0"
    assert observation_failures(row)


def test_isolation_accepts_only_owned_sqlite_uri_and_browser_driver(tmp_path, monkeypatch):
    callbacks = []
    monkeypatch.setattr("sys.addaudithook", callbacks.append)
    db = tmp_path / "qa.sqlite"
    guards = install_boundary(tmp_path / "temp", tmp_path / "out", db, ["node", "cli.js", "run-driver"])
    audit = callbacks[0]
    audit("sqlite3.connect", (db.as_uri() + "?mode=ro",))
    audit("subprocess.Popen", ("node", ["node", "cli.js", "run-driver"]))
    audit("socket.connect", (None, ("127.0.0.1", 5000)))
    for event, args in (
        ("sqlite3.connect", ((tmp_path / "real.sqlite").as_uri() + "?mode=ro",)),
        ("sqlite3.connect", ("file://remote/qa.sqlite?mode=ro",)),
        ("subprocess.Popen", ("node", ["node", "arbitrary.js"])),
        ("socket.connect", (None, ("provider.invalid", 443))),
        ("open", (str(tmp_path / "outside.json"), "w", 0)),
    ):
        with pytest.raises(PermissionError):
            audit(event, args)
    assert len(guards) == 5


def test_preflight_produces_browser_evidence_before_check_and_uploads_it():
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/render-deploy.yml").read_text(encoding="utf-8")
    preflight = workflow.split("  dry-run:")[0]
    commands = ["python -m pip install -r browser_qa/playwright_requirements.txt",
                "python -m playwright install --with-deps chromium",
                "python tools/run_v944_match_center_browser_qa.py",
                "python tools/check_v944_match_center_foundation.py"]
    assert [preflight.index(c) for c in commands] == sorted(preflight.index(c) for c in commands)
    assert "browser_qa/V944_MATCH_CENTER_FOUNDATION/*.png" in preflight
    assert "browser_qa/V944_MATCH_CENTER_FOUNDATION/*.json" in preflight
    assert "continue-on-error" not in preflight
    assert "persist-credentials: false" in preflight
