"""Eligibility must be fresh, coherent and equivalent to independent public rules."""
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest
from engines import v935_launch_trust_engine as trust

NOW = datetime(2026, 11, 11, 12, tzinfo=ZoneInfo("Europe/Madrid"))


def pick():
    return dict(id="owned-pick", match_id="owned-match", home_team="Home", away_team="Away",
                competition_name="League", kickoff_iso=(NOW+timedelta(hours=4)).isoformat(),
                match_status="NS", status="published", market="1x2", selection="Home",
                odds=1.8, odds_source="qa", source="qa", odds_updated_at=NOW.isoformat(), stake=1)


@pytest.mark.parametrize("status", ["draft", "review", "approved", "published", "live", "cancelled", "archived"])
@pytest.mark.parametrize("match_status", ["NS", "LIVE", "FT", "PST", "SUSP"])
@pytest.mark.parametrize("change", [{}, {"result_status":"won"}, {"odds":0}, {"selection":None},
                                   {"odds_updated_at":(NOW-timedelta(hours=2)).isoformat()}])
def test_assessment_agrees_with_independent_public_rules(status, match_status, change):
    row = {**pick(), "status":status, "match_status":match_status, **change,
           "v935_match_lifecycle":"UPCOMING", "v935_lifecycle":"WON",
           "v935_publishable":True, "v935_evaluable":True, "v935_quality":{"status":"PASS"}}
    original = deepcopy(row)
    expected_row = dict(row)
    expected_row["v935_match_lifecycle"] = trust.normalize_match_lifecycle(trust._pick_match_view(row), NOW)
    expected = dict(expected_row, v935_lifecycle=trust.normalize_pick_lifecycle(expected_row, NOW),
                    v935_odds=trust._pick_odds_state(expected_row, NOW),
                    v935_quality=trust.get_pick_data_quality(expected_row, NOW),
                    v935_publishable=trust.is_pick_publishable(expected_row, NOW),
                    v935_evaluable=trust.is_pick_evaluable(expected_row, NOW))
    actual = trust.enrich_pick_lifecycle(row, NOW)
    assert actual == expected
    assert row == original
    # Output objects remain independent, as in the previous public contract.
    actual["v935_odds"]["status"] = "CHANGED_BY_CONSUMER"
    assert actual["v935_quality"]["odds"]["status"] != "CHANGED_BY_CONSUMER"


def test_new_time_and_source_mutation_revoke_old_eligibility():
    row = pick()
    fresh = trust.enrich_pick_lifecycle(row, NOW)
    assert fresh["v935_publishable"] is True
    stale = trust.enrich_pick_lifecycle(fresh, NOW+timedelta(hours=2))
    assert stale["v935_odds"]["status"] == "STALE"
    assert stale["v935_publishable"] is False
    row["selection"] = None
    revoked = trust.enrich_pick_lifecycle({**fresh, **row}, NOW)
    assert revoked["v935_lifecycle"] == "INCOMPLETE"
    assert revoked["v935_publishable"] is False
    assert revoked["v935_evaluable"] is False


def test_enrichment_observes_each_source_dependency_once(monkeypatch):
    calls = dict(complete=0, lifecycle=0, odds=0)
    for name, key in [("is_pick_complete", "complete"), ("normalize_match_lifecycle", "lifecycle"),
                      ("_pick_odds_state", "odds")]:
        original = getattr(trust, name)
        def observe(*args, _original=original, _key=key, **kwargs):
            calls[_key] += 1
            return _original(*args, **kwargs)
        monkeypatch.setattr(trust, name, observe)
    result = trust.enrich_pick_lifecycle(pick(), NOW)
    assert result["v935_publishable"] is True
    assert calls == dict(complete=1, lifecycle=1, odds=1)
