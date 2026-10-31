"""No-network tests for evidence-aware three-role Company OS review."""
from __future__ import annotations

import json
from pathlib import Path

from engines.company_review_triad_engine import (
    TRIAD_CONTRACT,
    build_company_review_triads,
    independent_consensus,
)


def _workers():
    return [{"worker_name": f"Core {idx}"} for idx in range(15)]


def _disciplines():
    return [{"id": f"game_{idx}", "name": f"Game UI {idx}"} for idx in range(7)]


def _votes(sha):
    return [
        {"source_family": "native_source", "proof_id": "static-a", "revision": sha,
         "verdict": "CONFORME", "verified": True},
        {"source_family": "browser_qa", "proof_id": "browser-b", "revision": sha,
         "verdict": "CONFORME", "verified": True},
    ]


def test_22_specialties_have_exactly_two_additional_review_roles_not_fake_agents():
    result = build_company_review_triads(_workers(), _disciplines())
    assert result["contract"] == TRIAD_CONTRACT
    assert result["configured_areas"] == result["existing_primary_roles"] == 22
    assert result["additional_review_roles"] == 44
    assert result["total_review_roles"] == 66
    assert len(result["reviewers"]) == 22
    assert all([x["id"] for x in row["roles"]] ==
               ["principal", "verificador", "contraste"] for row in result["reviewers"])
    assert all(row["consensus"] == "NOT_VERIFIED" for row in result["reviewers"])
    assert all(role["vote"] == "ABSTAIN"
               for row in result["reviewers"] for role in row["roles"])
    assert result["state"] == "NOT_RUN"
    assert result["crosschecks_executed"] == result["confirmed_consensus"] == 0
    assert result["external_calls"] == result["paid_credits_consumed"] == 0
    assert result["autonomous_agents_started"] == 0
    assert result["automatic_deploy"] is False
    assert result["automatic_code_changes"] is False


def test_static_metadata_review_does_not_count_as_independent_product_vote():
    first = _workers()[:1]
    record = {"id": "core_zero", "worker_name": first[0]["worker_name"],
              "executed": True, "static_state": "PASS",
              "evidence": [{"path": "safe.py", "state": "READ", "sha256": "a" * 64}]}
    triad = build_company_review_triads(first, [], [record], receipt_state="RECENT")
    row = triad["reviewers"][0]
    assert triad["state"] == "STATIC_CROSSCHECKS_ONLY"
    assert triad["crosschecks_executed"] == 2
    assert triad["independent_votes"] == triad["confirmed_consensus"] == 0
    assert row["roles"][0]["state"] == "PASS"
    assert row["roles"][1]["state"] == "SOURCE_METADATA_PRESENT_UNATTESTED"
    assert row["roles"][2]["state"] == "INDEPENDENT_RUNTIME_OR_FUNCTIONAL_QA_REQUIRED"
    assert all(role["vote"] == "ABSTAIN" for role in row["roles"])
    record["evidence"][0]["sha256"] = "bad"
    bad = build_company_review_triads(first, [], [record], receipt_state="RECENT")
    assert bad["reviewers"][0]["roles"][1]["state"] == "INVALID_SOURCE_METADATA"
    stale = build_company_review_triads(first, [], [record], receipt_state="STALE")
    assert stale["state"] == "NOT_RUN"
    assert stale["reviewers"][0]["roles"][0]["state"] == "UNKNOWN"


def test_visual_review_requires_separate_browser_evidence():
    result = build_company_review_triads(
        [], _disciplines()[:1],
        [{"id": "game_0", "executed": True, "state": "UNKNOWN",
          "evidence": [{"state": "READ", "sha256": "b" * 64}]}],
        receipt_state="RECENT",
    )
    row = result["reviewers"][0]
    assert row["roles"][2]["state"] == "BROWSER_QA_AND_SCREENSHOTS_REQUIRED"
    assert row["consensus"] == "NOT_VERIFIED"
    assert result["browser_executed_here"] is False
    assert result["source_revision_verified"] is False


def test_two_distinct_attested_families_only_propose_visual_candidate():
    sha = "a" * 40
    result = independent_consensus(_votes(sha), verified_revision=sha, risk="VISUAL")
    assert result["state"] == "REVIEW_CANDIDATE"
    assert result["votes_counted"] == 2
    assert result["automatic_approval"] is False


def test_duplicate_source_or_proof_and_wrong_sha_never_make_quorum():
    sha = "a" * 40
    votes = _votes(sha)
    votes[1]["source_family"] = "native_source"
    assert independent_consensus(votes, verified_revision=sha)["state"] == "PENDING_INDEPENDENT_PROOF"
    votes = _votes(sha)
    votes[1]["proof_id"] = "static-a"
    assert independent_consensus(votes, verified_revision=sha)["votes_counted"] == 1
    votes = _votes(sha)
    votes[1]["revision"] = "b" * 40
    assert independent_consensus(votes, verified_revision=sha)["votes_counted"] == 1
    assert independent_consensus(_votes(sha), verified_revision="")["state"] == "UNVERIFIED_REVISION"
    votes = _votes(sha)
    votes[1]["verified"] = False
    assert independent_consensus(votes, verified_revision=sha)["state"] == "PENDING_INDEPENDENT_PROOF"


def test_two_agree_do_not_approve_sensitive_changes_and_disagreement_escalates():
    sha = "a" * 40
    sensitive = independent_consensus(_votes(sha), verified_revision=sha, risk="BILLING")
    assert sensitive["state"] == "CRITICAL_GATES_REQUIRED"
    assert sensitive["automatic_approval"] is False
    votes = _votes(sha)
    votes[1]["verdict"] = "DEFECTO"
    assert independent_consensus(votes, verified_revision=sha)["state"] == "DISAGREEMENT_REQUIRES_REVIEW"
    votes.append({"source_family": "human_review", "proof_id": "human-c", "revision": sha,
                  "verdict": "DEFECTO", "verified": True})
    assert independent_consensus(votes, verified_revision=sha)["state"] == "DEFECT_CANDIDATE"


def test_admin_surface_renders_compact_summary_not_44_extra_cards():
    project = Path(__file__).resolve().parents[1]
    source = (project / "templates" / "admin_company_os.html").read_text("utf-8")
    assert "data-review-triad" in source
    assert "summary.review_triads" in source
    assert "Dos revisores" not in source or "evidencia" in source
    assert "Los controles de código" in source
    assert "for area in triads.reviewers" in source
    company = (project / "engines" / "company_operating_system_engine.py").read_text("utf-8")
    assert "build_company_review_triads" in company
    assert '"review_triads": review_triads' in company
