"""Safe governance of the acting Vice President. No network or DB calls."""
from engines.company_vicepresidency_engine import (
    ADVISORS, CONTRACT, action_policy, build_executive_readout,
    build_vicepresidency_snapshot,
)

NATIVE = "NEMESIS-NATIVE-WORKFORCE-REVIEW-V1"


def fixture_receipt():
    return {
        "contract": NATIVE, "receipt_id": "NWR-test",
        "finished_at_madrid": "2026-10-31T23:15:00+01:00",
        "results": [
            {"id": "technical_director", "worker_name": "Technical Director Worker",
             "executed": True, "state": "FAIL"},
            {"id": "game_motion", "worker_name": "Game Motion",
             "executed": True, "state": "UNKNOWN"},
            {"id": "not_run", "worker_name": "Missing",
             "executed": False, "state": "FAIL"},
        ],
    }


def test_president_retains_financial_and_production_control():
    for action in ("DEPLOY", "EDIT_CODE", "MERGE_PR", "CHANGE_PRICES",
                   "CHANGE_USERS", "SEND_TELEGRAM", "DELETE_DATA",
                   "CHANGE_SECRETS", "INCREASE_API_BUDGET"):
        policy = action_policy(action)
        assert policy["approval_required"] and not policy["approval_issued"]
        assert not policy["may_run_safe_local_step"]
        assert not policy["may_spend_money"]
        assert not policy["may_change_production"]


def test_unknown_and_dangerous_actions_fail_closed():
    assert action_policy("UNKNOWN_ACTION")["policy"] == "UNRECOGNIZED_DENIED"
    assert action_policy("CHARGE_CARD")["policy"] == "FORBIDDEN_TO_AUTOMATION"
    assert not action_policy("BULK_SEND_TELEGRAM")["may_run_safe_local_step"]
    assert action_policy("READ_VERIFIED_RECEIPTS")["may_run_safe_local_step"]
    assert action_policy("PREPARE_WORK_ORDER")["policy"] == "PROPOSE_ONLY"


def test_hourly_readout_counts_only_executed_and_creates_no_votes():
    result = build_executive_readout(fixture_receipt())
    assert result["executed"] == 2 and result["static_failed"] == 1
    assert result["static_unknown"] == 1 and result["static_passed"] == 0
    assert [a["area_id"] for a in result["priorities"]] == [
        "technical_director", "game_motion"]
    assert result["independent_votes"] == 0
    assert not result["production_certified"]
    assert not result["automatic_changes_authorized"]
    assert result["external_calls"] == result["paid_credits_consumed"] == 0


def test_missing_or_wrong_receipts_never_claim_work():
    for receipt in (None, {}, {"contract": "OTHER", "results": fixture_receipt()["results"]}):
        result = build_executive_readout(receipt)
        assert result["state"] == "NO_VERIFIED_RECEIPT"
        assert result["executed"] == 0 and result["priorities"] == []


def test_stale_native_receipt_does_not_certify_operating_workers():
    workers = [{"worker_name": "Technical Director Worker", "area": "Técnica"}]
    game = [{"id": "game_motion", "name": "Motion"}]
    board = build_vicepresidency_snapshot(
        workers, game, {"state": "STALE", "receipt": fixture_receipt()},
        {"state": "RECENT_RECEIPT"}, {"configured_areas": 2},
    )
    assert board["contract"] == CONTRACT
    assert board["president"]["retains_control"]
    assert board["vicepresident"]["state"] == "AWAITING_RECENT_REVIEW"
    assert board["cron"]["state"] == "RECENT_RECEIPT"
    assert not board["cron"]["certifies_all_workers"]
    assert board["reviewed_static_specialists"] == 0 and board["agenda"] == []
    assert board["production_mutations"] == board["autonomous_agents_started"] == 0
    assert board["crosscheck"]["independent_votes"] == 0
    assert len(board["advisory_council"]) == len(ADVISORS) == 10
    assert all(not s["can_authorize"] for s in board["advisory_council"])


def test_recent_native_receipt_only_certifies_static_checks():
    board = build_vicepresidency_snapshot(
        [{"worker_name": "Technical Director Worker", "area": "Técnica"}],
        [{"id": "game_motion", "name": "Motion"}],
        {"state": "RECENT", "receipt": fixture_receipt()},
        {"state": "STALE_RECEIPT"}, {"configured_areas": 2},
    )
    assert board["vicepresident"]["state"] == "RECENT_STATIC_COORDINATION"
    assert board["reviewed_static_specialists"] == 2
    assert [r["static_outcome"] for r in board["assignments"]] == ["FAIL", "UNKNOWN"]
    assert not any(r["execution_certified"] for r in board["assignments"])
    assert board["agenda"][0]["priority"] == "P1"
    assert board["cron"]["state"] == "STALE_RECEIPT"
    assert not board["crosscheck"]["approval_issued"]


def test_advisors_are_only_review_roles_and_cost_nothing():
    board = build_vicepresidency_snapshot([], [], {}, {}, {})
    assert len({r["id"] for r in board["advisory_council"]}) == 10
    assert all(r["state"] == "ADVISORY_ROLE_DEFINED" for r in board["advisory_council"])
    assert board["additional_services"] == board["additional_paid_calls"] == 0
