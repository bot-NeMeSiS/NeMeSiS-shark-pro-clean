"""Synthetic validator fixtures are not rendered Browser QA evidence."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from tools.check_v944_match_center_foundation import validate_browser_evidence
from tools.run_v944_match_center_browser_qa import (
    COMPONENTS, PROFILES, SCENARIOS, install_boundary, observation_failures, qa_identity, write_result,
)


def test_browser_qa_credentials_are_ephemeral_and_not_provider_credentials():
    first, second = qa_identity(), qa_identity()
    assert first["SECRET_KEY"] != second["SECRET_KEY"]
    assert first["ADMIN_PASSWORD"] != second["ADMIN_PASSWORD"]
    assert len(first["SECRET_KEY"]) >= 43 and len(first["ADMIN_PASSWORD"]) >= 32
    assert first["AUTOMATION_SECRET"] == second["AUTOMATION_SECRET"] == ""
    assert first["ADMIN_EMAIL"].endswith("@example.invalid")


def test_browser_runner_passes_unchanged_secret_guard(tmp_path):
    from tools.check_repository_privacy_and_secrets import scan_repository
    target = tmp_path / "tools"
    target.mkdir()
    source = Path(__file__).resolve().parents[1] / "tools/run_v944_match_center_browser_qa.py"
    (target / source.name).write_bytes(source.read_bytes())
    result = scan_repository(tmp_path)
    assert result["ok"] and result["files_scanned"] == 1
    assert result["privacy_review_findings"] == 0
    assert all(item["classification"] == "EXPECTED_FIXTURE" for item in result["privacy_findings"])
    assert all(item["value_redacted"] is True for item in result["privacy_findings"])
    # A new hardcoded session secret must still fail; no scanner exceptions.
    (target / "bad_runner.py").write_text("SECRET_KEY = 'unapproved-static-session-value'\n", encoding="utf-8")
    result = scan_repository(tmp_path)
    assert not result["ok"]
    assert any(f["type"] == "sensitive_literal_assignment" for f in result["secret_findings"])


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


def _exercise_delayed_image_wait(status, duplicate_release_signal, waiter):
    import os
    from playwright.sync_api import sync_playwright
    from tools.run_v944_match_center_browser_qa import INSPECT_JS
    with sync_playwright() as pw:
        options={"headless":True}
        if os.getenv("NEMESIS_QA_CHROMIUM"):
            options["executable_path"]=os.environ["NEMESIS_QA_CHROMIUM"]
        browser=pw.chromium.launch(**options)
        page=browser.new_page()
        fixture_url="http://localhost/qa-crest.svg"
        pending=[]
        release_attempts=[]
        release_completed=[]
        release_during_wait=[]
        response_status=[]
        signals=[]
        waiting=[False]
        entered=[]
        page.route("**/*",lambda route:pending.append(route))
        page.expose_function("qa_pending_image_count",lambda:len(pending))
        release_image=None
        release_registered=[False]
        def observe_response(response):
            if response.url==fixture_url:
                response_status.append(response.status)
        def observe_signal(message):
            if message.text=="QA_RELEASE_IMAGE":
                signals.append(message.text)
        page.on("response",observe_response)
        page.on("console",observe_signal)
        try:
            page.set_content('<img src="http://localhost/qa-crest.svg">',wait_until="domcontentloaded")
            page.wait_for_function("async () => (await window.qa_pending_image_count()) === 1")
            assert len(pending)==1 and pending[0].request.url==fixture_url
            held_route=pending[0]
            page.wait_for_function("() => document.images.length === 1 && !document.images[0].complete")
            def release_image(message):
                if message.text!="QA_RELEASE_IMAGE" or not release_registered[0]:
                    return
                release_registered[0]=False
                page.remove_listener("console",release_image)
                release_attempts.append(fixture_url)
                release_during_wait.append(waiting[0])
                held_route.fulfill(status=status,content_type="image/svg+xml",
                    body='<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><rect width="24" height="24"/></svg>' if status==200 else "missing")
                release_completed.append(fixture_url)
            page.on("console",release_image)
            release_registered[0]=True

            class DelayedResponsePage:
                # Forward the real native wait. Arm the response only after the
                # helper enters it: a no-op helper can never release the image.
                def wait_for_function(self,*args,**kwargs):
                    entered.append(True)
                    waiting[0]=True
                    try:
                        page.evaluate("(duplicate) => setTimeout(() => { console.log('QA_RELEASE_IMAGE'); if (duplicate) console.log('QA_RELEASE_IMAGE'); }, 100)",duplicate_release_signal)
                        return page.wait_for_function(*args,**kwargs)
                    finally:
                        waiting[0]=False
                def __getattr__(self,name):
                    return getattr(page,name)

            waiter(DelayedResponsePage())
            # These checks precede any extra wait which might mask a no-op.
            assert entered,"image_wait_not_entered"
            assert release_attempts==release_completed==[fixture_url]
            assert release_during_wait==[True]
            assert response_status==[status]
            image=page.evaluate("() => ({complete:document.images[0].complete,src:document.images[0].currentSrc,width:document.images[0].naturalWidth})")
            assert image["complete"] and image["src"]==fixture_url
            assert (image["width"]>0)==(status==200)
            observed=page.evaluate(INSPECT_JS)
            assert len(signals)==(2 if duplicate_release_signal else 1)
            assert bool(observed["broken_images"])==(status==404)
            row=capture("partial","mobile")
            row["broken_images"]=observed["broken_images"]
            assert ("broken_images" in observation_failures(row))==(status==404)
        finally:
            if release_registered[0]:
                release_registered[0]=False
                page.remove_listener("console",release_image)
            page.remove_listener("console",observe_signal)
            page.remove_listener("response",observe_response)
            browser.close()


@pytest.mark.parametrize("status", [200,404])
@pytest.mark.parametrize("duplicate_release_signal", [False,True])
def test_image_readiness_waits_for_pending_responses_and_preserves_broken_detection(status, duplicate_release_signal):
    from tools.run_v944_match_center_browser_qa import wait_for_rendered_images
    _exercise_delayed_image_wait(status,duplicate_release_signal,wait_for_rendered_images)


def test_delayed_image_fixture_rejects_a_noop_waiter():
    with pytest.raises(AssertionError,match="image_wait_not_entered"):
        _exercise_delayed_image_wait(404,True,lambda page:None)


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


@pytest.mark.parametrize("windows", [False, True])
def test_isolation_matches_exact_command_and_executable(tmp_path, monkeypatch, windows):
    import subprocess
    callbacks = []
    monkeypatch.setattr("sys.addaudithook", callbacks.append)
    command = ["C:/QA runtime/node.exe", "C:/QA runtime/cli.js", "run-driver"]
    extra = ["C:/QA runtime/python.exe", "check.py"]
    guards = install_boundary(tmp_path / "temp", tmp_path / "out", tmp_path / "qa.sqlite", command, [extra])
    audit = callbacks[0]
    serialize = subprocess.list2cmdline if windows else list
    for allowed in (command, extra):
        audit("subprocess.Popen", (allowed[0], serialize(allowed)))
        audit("subprocess.Popen", (None, serialize(allowed)))
    for executable, argv in (
        ("other.exe", command),
        (command[0], [*command, "--unexpected"]),
        (command[0], [command[0], "arbitrary.js"]),
        (None, [*command, "--unexpected"]),
    ):
        with pytest.raises(PermissionError, match="V944_QA_PROCESS_BLOCKED"):
            audit("subprocess.Popen", (executable, serialize(argv)))
    assert guards == ["PROCESS"] * 4


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
