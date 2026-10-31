"""Bounded three-role review protocol for Company OS.

A second opinion is useful only when its evidence is independent. This module
creates reviewer responsibilities and inspects evidence *metadata*; it does not
start agents, call providers, vote from the same receipt three times, or approve
code, billing, publishing, or deployment.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

TRIAD_CONTRACT = "NEMESIS-COMPANY-REVIEW-TRIAD-V1"
TRIAD_ROLES = ("principal", "verificador", "contraste")
EVIDENCE_FAMILIES = {"native_source", "browser_qa", "production_observation", "human_review"}
_SHA_RE = re.compile(r"[0-9a-fA-F]{40}\Z")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")


def _source_metadata_state(record: dict[str, Any], fresh: bool) -> str:
    """Assess only evidence *structure*. A digest is not a certified source."""
    if not fresh or not record or record.get("executed") is not True:
        return "NO_RECENT_EXECUTION"
    evidence = record.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return "NO_SOURCE_EVIDENCE"
    for item in evidence:
        if not isinstance(item, dict):
            return "INVALID_SOURCE_METADATA"
        if item.get("state") != "READ":
            return "INCOMPLETE_SOURCE_EVIDENCE"
        digest = item.get("sha256")
        if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
            return "INVALID_SOURCE_METADATA"
    return "SOURCE_METADATA_PRESENT_UNATTESTED"


def _review_for_area(identifier: str, title: str, group: str, record: dict[str, Any], fresh: bool) -> dict[str, Any]:
    executed = bool(fresh and record and record.get("executed") is True)
    original = record.get("static_state") if group == "company_core" else record.get("state")
    original = original if executed and original in {"PASS", "FAIL", "UNKNOWN"} else "UNKNOWN"
    integrity = _source_metadata_state(record, fresh)
    # The third reviewer challenges coverage and asks for *different evidence*.
    # It cannot manufacture browser or production observations from a source scan.
    needed = "BROWSER_QA_AND_SCREENSHOTS_REQUIRED" if (group == "game_ui" or identifier in {
        "client_experience", "qa_visual", "crest_identity", "routes_buttons", "spanish_copy",
    }) else "INDEPENDENT_RUNTIME_OR_FUNCTIONAL_QA_REQUIRED"
    roles = [
        {"id": "principal", "name": "Analista principal", "scope": "native_static",
         "executed": executed, "state": original, "vote": "ABSTAIN",
         "limitation": "El análisis del código no demuestra cómo se ve o funciona producción."},
        {"id": "verificador", "name": "Verificador de evidencia", "scope": "source_metadata",
         "executed": executed, "state": integrity, "vote": "ABSTAIN",
         "limitation": "Valida cobertura y formato de hashes, no la verdad del resultado ni el SHA desplegado."},
        {"id": "contraste", "name": "Revisor crítico independiente", "scope": "missing_proof",
         "executed": executed, "state": needed if executed else "NO_RECENT_EXECUTION", "vote": "ABSTAIN",
         "limitation": "Requiere pruebas de otro canal; no reutiliza el voto del analista."},
    ]
    return {"id": identifier, "title": title, "group": group, "roles": roles,
            "role_count": 3, "independent_votes": 0, "consensus": "NOT_VERIFIED",
            "automatic_changes_authorized": False}


def build_company_review_triads(
    workers: Iterable[dict[str, Any]], disciplines: Iterable[dict[str, Any]],
    native_records: Iterable[dict[str, Any]] = (), *, receipt_state: str = "NOT_RUN",
) -> dict[str, Any]:
    """Expose 15+7 responsibilities with two bounded cross-check roles each.

    Review data must come from the already-authenticated, existing receipt
    loader. No source reads, filesystem writes, external calls or new timers.
    """
    records = [r for r in native_records if isinstance(r, dict)]
    by_name = {str(r.get("worker_name") or ""): r for r in records}
    by_id = {str(r.get("id") or ""): r for r in records}
    fresh = receipt_state == "RECENT"
    triads: list[dict[str, Any]] = []
    for index, item in enumerate(workers):
        if not isinstance(item, dict):
            continue
        name = str(item.get("worker_name") or "")[:120]
        if name:
            record = by_name.get(name, {})
            identifier = str(record.get("id") or "core_" + str(index))[:80]
            triads.append(_review_for_area(identifier, str(item.get("area") or name)[:120], "company_core", record, fresh))
    for item in disciplines:
        if not isinstance(item, dict):
            continue
        identifier = str(item.get("id") or "")[:80]
        if identifier:
            triads.append(_review_for_area(identifier, str(item.get("name") or identifier)[:120],
                                           "game_ui", by_id.get(identifier, {}), fresh))
    executed_crosschecks = sum(
        role["executed"] for area in triads for role in area["roles"] if role["id"] != "principal"
    )
    return {
        "contract": TRIAD_CONTRACT, "state": "STATIC_CROSSCHECKS_ONLY" if executed_crosschecks else "NOT_RUN",
        "configured_areas": len(triads), "existing_primary_roles": len(triads),
        "additional_review_roles": len(triads) * 2, "total_review_roles": len(triads) * 3,
        "crosschecks_executed": executed_crosschecks, "independent_votes": 0,
        "confirmed_consensus": 0, "consensus_state": "PENDING_INDEPENDENT_EVIDENCE",
        "source_revision_verified": False, "browser_executed_here": False,
        "external_calls": 0, "paid_credits_consumed": 0, "autonomous_agents_started": 0,
        "automatic_code_changes": False, "automatic_deploy": False,
        "reviewers": triads,
        "limits": "Los dos revisores adicionales son controles locales; no equivalen a personal, modelos ni una certificación de producto.",
    }


def independent_consensus(
    votes: Iterable[dict[str, Any]], *, verified_revision: str = "", risk: str = "VISUAL",
) -> dict[str, Any]:
    """2/3 is *advisory* only, never an authorization to merge/deploy.

    The caller must independently attest evidence before setting "verified";
    this function is not a trust boundary or a verification of an external
    attestation. Browser, production and human observations must have different
    source families, distinct proof IDs and the exact verified revision.
    """
    if not _SHA_RE.fullmatch(str(verified_revision or "")):
        return {"state": "UNVERIFIED_REVISION", "votes_counted": 0, "automatic_approval": False}
    accepted: list[dict[str, str]] = []
    families: set[str] = set()
    proof_ids: set[str] = set()
    for entry in list(votes)[:3]:
        if not isinstance(entry, dict) or entry.get("verified") is not True:
            continue
        family = str(entry.get("source_family") or "")
        proof = str(entry.get("proof_id") or "")
        verdict = str(entry.get("verdict") or "").upper()
        if (family not in EVIDENCE_FAMILIES or family in families
                or not proof or len(proof) > 160 or proof in proof_ids
                or verdict not in {"CONFORME", "DEFECTO"}
                or str(entry.get("revision") or "").lower() != verified_revision.lower()):
            continue
        accepted.append({"source_family": family, "proof_id": proof, "verdict": verdict})
        families.add(family)
        proof_ids.add(proof)
    conforming = sum(x["verdict"] == "CONFORME" for x in accepted)
    defective = sum(x["verdict"] == "DEFECTO" for x in accepted)
    state = "PENDING_INDEPENDENT_PROOF"
    if conforming >= 2:
        state = "REVIEW_CANDIDATE" if risk == "VISUAL" else "CRITICAL_GATES_REQUIRED"
    elif defective >= 2:
        state = "DEFECT_CANDIDATE"
    elif conforming and defective:
        state = "DISAGREEMENT_REQUIRES_REVIEW"
    return {"state": state, "votes_counted": len(accepted),
            "conforming": conforming, "defective": defective, "automatic_approval": False}
