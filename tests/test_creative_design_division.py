"""SIMULATED_QA for design governance, not visual approval of production."""
from copy import deepcopy
import json
from pathlib import Path

from engines.reference_image_manifest_engine import (
    DESIGN_STATUSES, build_creative_design_status, load_creative_design_contract,
)
from engines.autonomous_product_qa_engine import (
    WORKERS, build_autonomous_product_qa_status, load_product_qa_memory, record_product_qa_run,
)

ROOT = Path(__file__).resolve().parents[1]


def review(**changes):
    return {
        "screen_id": "HOME", "contract_fingerprint": load_creative_design_contract(ROOT)["fingerprint"],
        "candidate_revision": "SIMULATED_QA", "observed_at": "2026-09-09T12:00:00+02:00",
        "viewport": "390x844", "screenshots": ["SIMULATED_QA/home.png"],
        "reference_id": "REF-08", "reference_comparison": True,
        "functional_qa": "PASS", "visual_qa": "PASS", "design_status": "MINOR_DESIGN_GAP",
        **changes,
    }


def home(status):
    return next(s for s in status["screens"] if s["screen_id"] == "HOME")


def test_contract_has_16_direct_references_and_complete_derived_screens():
    contract = load_creative_design_contract(ROOT)
    direct = [s for s in contract["screens"] if s["reference_relation"] == "DIRECT"]
    assert len(direct) == 16
    assert {s["target_reference"] for s in direct} == {f"REF-{n:02}" for n in range(1, 17)}
    assert len(contract["screens"]) == 21
    for screen in contract["screens"]:
        assert screen["design_status"] in DESIGN_STATUSES
        assert (ROOT / screen["reference_file"]).is_file()
        assert all((ROOT / c).is_file() for c in screen["components"])
        assert screen["empty_state"] and screen["responsive_behavior"] and screen["actions"]


def test_ref12_is_match_detail_not_a_standalone_shark_portal():
    screens = load_creative_design_contract(ROOT)["screens"]
    match = next(s for s in screens if s["screen_id"] == "MATCH")
    shark = next(s for s in screens if s["screen_id"] == "SHARK")
    assert match["target_reference"] == shark["target_reference"] == "REF-12"
    assert match["reference_relation"] == "DIRECT"
    assert shark["reference_relation"] == "DERIVED_ANALYSIS"
    from engines.reference_image_manifest_engine import classify_reference_image
    classified = classify_reference_image(ROOT / match["reference_file"], ROOT)
    assert classified["canonical_route"] == match["route"]
    assert classified["screen_target"] == "/match/m-1"
    assert classified["screen"] == "Match Center"
    assert classified["category"] == "match"


def test_roles_reuse_real_executors_and_do_not_register_new_workers():
    original = dict(WORKERS)
    status = build_creative_design_status(ROOT)
    assert len(status["roles"]) == 7
    for role in status["roles"]:
        assert role["executor"] == "Codex" or role["executor"] in WORKERS
        assert role["reviewer"] == "QA Director" or role["reviewer"] in WORKERS
    assert WORKERS == original
    assert status["new_processes"] == 0
    assert status["automatic_approval"] is False
    assert status["authority"][0] == "OFFICIAL_16_TARGET_SCREENS"


def test_brand_kit_has_one_app_icon_master_and_all_sources_exist():
    kit = {b["role"]: b for b in build_creative_design_status(ROOT)["brand_kit"]}
    assert len(kit) == 7
    assert all(b["available"] for b in kit.values())
    assert kit["APP_ICON"]["derived_from"] == "ATMOSPHERIC_SHARK"
    for role in ("FAVICON", "PWA_ICONS", "APPLE_TOUCH_ICON"):
        assert kit[role]["derived_from"] == "APP_ICON"
    assert kit["BRAND_SHARK"]["status"] == "FOUNDER_SUBJECTIVE_REVIEW"


def test_functional_pass_does_not_hide_design_rework():
    status = build_creative_design_status(ROOT, reviews=[review(design_status="DESIGN_REWORK_REQUIRED")])
    assert home(status)["functional_qa"] == "PASS"
    assert home(status)["visual_qa"] == "PASS"
    assert home(status)["design_status"] == "DESIGN_REWORK_REQUIRED"
    assert status["release_quality"] == "WARNING"


def test_automated_match_cannot_grant_founder_approval():
    status = build_creative_design_status(ROOT, reviews=[review(design_status="DESIGN_MATCH", founder_approved=True)])
    assert home(status)["design_status"] == "FOUNDER_SUBJECTIVE_REVIEW"
    assert not status["production_certified"]


def test_unobserved_is_not_pass_and_other_screens_do_not_inherit_a_review():
    status = build_creative_design_status(ROOT, reviews=[review()])
    assert home(status)["design_status"] == "MINOR_DESIGN_GAP"
    for screen in status["screens"]:
        if screen["screen_id"] != "HOME":
            assert screen["functional_qa"] == screen["visual_qa"] == "NOT_RUN"


def test_wrong_contract_or_missing_capture_cannot_certify():
    for changes in ({"contract_fingerprint": "old"}, {"screenshots": []}, {"candidate_revision": ""}):
        assert home(build_creative_design_status(ROOT, reviews=[review(**changes)]))["functional_qa"] == "NOT_RUN"
    assert home(build_creative_design_status(ROOT, reviews=[review(reference_id="REF-01")]))["design_status"] == "FOUNDER_SUBJECTIVE_REVIEW"


def test_founder_rejection_overrides_review_and_never_mutates_evidence():
    issues = [{"issue_id": "founder-shark", "category": "VISUAL_SHARK", "screen": "/app", "status": "FOUNDER_REJECTED"}]
    reviews = [review(design_status="DESIGN_MATCH")]
    before = deepcopy((issues, reviews))
    status = build_creative_design_status(ROOT, issues=issues, reviews=reviews)
    assert home(status)["design_status"] == "DESIGN_REWORK_REQUIRED"
    assert home(status)["functional_qa"] == "PASS"
    assert status["objective_gaps"]
    assert next(g for g in status["groups"] if g["area"] == "BRAND")["design_status"] == "DESIGN_REWORK_REQUIRED"
    assert (issues, reviews) == before


def test_resolved_issue_does_not_reopen_itself():
    issue = {"category": "VISUAL_SHARK", "screen": "/app", "status": "RESOLVED"}
    assert home(build_creative_design_status(ROOT, issues=[issue]))["design_status"] == "FOUNDER_SUBJECTIVE_REVIEW"


def test_missing_or_invalid_specification_is_honest_and_read_only(tmp_path):
    status = build_creative_design_status(tmp_path)
    assert not status["contract_available"]
    assert not status["production_certified"]
    assert status["screens"] == []
    assert list(tmp_path.iterdir()) == []
    (tmp_path / "reference_images").mkdir()
    (tmp_path / "reference_images/design_contracts.json").write_text('{"contract": "wrong"}')
    assert load_creative_design_contract(tmp_path) == {}
    (tmp_path / "reference_images/design_contracts.json").write_text('[]')
    assert load_creative_design_contract(tmp_path) == {}


def test_missing_reference_or_brand_is_a_gap_not_asset_pass(tmp_path):
    folder = tmp_path / "reference_images"
    folder.mkdir()
    (folder / "design_contracts.json").write_bytes((ROOT / "reference_images/design_contracts.json").read_bytes())
    status = build_creative_design_status(tmp_path)
    assert home(status)["design_status"] == "DESIGN_REWORK_REQUIRED"
    assert {g["id"] for g in status["objective_gaps"]} >= {"REFERENCE_UNAVAILABLE", "BRAND_ASSET_UNAVAILABLE"}


def test_existing_memory_records_decisions_once_and_reads_never_write(tmp_path):
    observation = {"run_id": "DESIGN-QA-1", "scope": "critical", "evidence_complete": False,
                   "design_reviews": [review()], "workers_executed": ["visual_experience_inspector"]}
    result = record_product_qa_run(observation, project_root=ROOT, storage_root=tmp_path, now="2026-09-09T12:00:00+02:00")
    assert result["creative_design"]["division"] == "NEMESIS CREATIVE & DESIGN"
    record_product_qa_run({**observation, "run_id": "DESIGN-QA-2"}, project_root=ROOT, storage_root=tmp_path, now="2026-09-09T12:01:00+02:00")
    memory = load_product_qa_memory(ROOT, tmp_path)
    assert len(memory["design_decisions"]) == 1
    expected = load_creative_design_contract(ROOT)["design_memory"]
    recorded = memory["design_decisions"][0]["decisions"]
    assert recorded == expected
    assert len({item["id"] for item in recorded}) == len(recorded)
    assert {"MOBILE_PRIMARY_NAV", "CALENDAR_HUB", "HOME_SELECTION",
            "TRACK_RECORD_PICKS", "SHARK_CONTEXTUAL", "SPORTS_VISUAL_TOKENS"} <= {item["id"] for item in recorded}
    assert memory["founder_overrides"]
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    status = build_autonomous_product_qa_status(ROOT, storage_root=tmp_path)
    assert home(status["creative_design"])["review_revision"] == "SIMULATED_QA"
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_record_dry_run_does_not_write_memory(tmp_path):
    record_product_qa_run({}, project_root=ROOT, storage_root=tmp_path, write=False)
    assert not list(tmp_path.rglob("*.json"))


def test_contract_routes_exist_and_are_not_new_endpoints(app_module):
    routes = {r.rule for r in app_module.app.url_map.iter_rules()}
    for screen in load_creative_design_contract(ROOT)["screens"]:
        assert screen["route"] in routes


def test_founder_renders_compact_division_with_independent_axes(client, app_module, monkeypatch, tmp_path):
    from tests.test_founder_mode_command_center import _sample_founder_snapshot, _admin_session
    snapshot = _sample_founder_snapshot()
    snapshot["autonomous_product_qa"] = build_autonomous_product_qa_status(ROOT, storage_root=tmp_path)
    monkeypatch.setattr(app_module, "founder_command_center_snapshot", lambda: snapshot)
    monkeypatch.setattr(app_module, "dashboard_data", lambda *a, **k: {})
    _admin_session(client)
    response = client.get("/admin/founder-dashboard")
    assert response.status_code == 200
    assert b'data-creative-design="read-only"' in response.data
    assert b'NEMESIS CREATIVE &amp; DESIGN' in response.data
    assert response.data.count(b"Sin muestra evaluada en este contrato") == 21
    assert "Revisión de marca pendiente".encode() in response.data


def test_contract_is_packaged_but_private_evidence_is_not():
    from tools.build_clean_release import include
    assert include(ROOT / "reference_images/design_contracts.json")
    assert not include(ROOT / ".tmp_reference_review/creative_design_20260909/before.json")
