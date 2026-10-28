"""SHARK's featured HTML/briefing must authorize the current stored pick row.

Run with the original LOCAL SAFE supervisor. Real Flask routes, password login,
revocable sessions, original public-summary cache, SQL, lifecycle, entitlement,
Jinja and read-only quota behavior stay in place. All users/rows are owned QA.
"""
from datetime import datetime, timedelta, timezone
import sqlite3
import sys

import pytest

from engines.madrid_time_engine import MADRID_TZ
from test_shark_selected_pick_boundary import fixture_match_times, shark_probe


# The shared fixture isolates unrelated collections for selected-pick tests.
# These tests restore the actual read model instead of supplying cached picks.
REAL_PUBLIC_SUMMARY = getattr(sys.modules.get("app"), "get_public_home_sports_summary", None)


@pytest.mark.parametrize("reference,date_label,time_label", [
    ("2026-01-15T19:30:00+00:00", "2026-01-15", "23:30"),
    ("2026-01-15T20:30:00+00:00", "2026-01-16", "00:30"),
    ("2026-01-15T22:30:00+00:00", "2026-01-16", "02:30"),
    ("2026-10-26T23:06:00+00:00", "2026-10-27", "03:06"),
    ("2026-07-15T19:30:00+00:00", "2026-07-16", "00:30"),
    ("2026-07-15T21:30:00+00:00", "2026-07-16", "02:30"),
    ("2026-03-28T23:30:00+00:00", "2026-03-29", "04:30"),
    ("2026-10-24T23:30:00+00:00", "2026-10-25", "03:30"),
])
def test_fixture_clock_keeps_upcoming_madrid_date_across_midnight_and_dst(reference, date_label, time_label):
    now = datetime.fromisoformat(reference)
    match_date, kickoff_iso, kickoff_time = fixture_match_times(now)
    assert match_date == date_label
    assert kickoff_time == time_label
    assert datetime.fromisoformat(kickoff_iso) - now == timedelta(hours=3)


@pytest.fixture
def featured_probe(shark_probe, monkeypatch):
    a = shark_probe["a"]
    assert REAL_PUBLIC_SUMMARY is not None
    observed = []

    def actual_summary(*args, **kwargs):
        result = REAL_PUBLIC_SUMMARY(*args, **kwargs)
        observed.append(result.get("summary_cache_status"))
        return result

    monkeypatch.setattr(a, "get_public_home_sports_summary", actual_summary)
    shark_probe["summary_observations"] = observed
    return shark_probe


def test_actual_owned_rows_share_the_upcoming_madrid_kickoff(featured_probe):
    # Inspect the real fixture rows, without replacing the application clock,
    # read model, lifecycle or current-principal authorization.
    with sqlite3.connect(featured_probe["path"]) as conn:
        records = conn.execute("""SELECT p.match_date, p.created_at,
            m.match_date, m.kickoff_iso, m.kickoff_time
            FROM picks p JOIN matches m ON m.id=p.match_id ORDER BY p.id""").fetchall()
    assert len(records) == 2
    for pick_date, created_at, match_date, kickoff_iso, kickoff_time in records:
        kickoff = datetime.fromisoformat(kickoff_iso)
        local = kickoff.astimezone(MADRID_TZ)
        assert pick_date == match_date == local.date().isoformat()
        assert kickoff_time == local.strftime("%H:%M")
        assert kickoff - datetime.fromisoformat(created_at) == timedelta(hours=3)
        assert kickoff > datetime.now(timezone.utc)


def _client(probe, plan):
    return probe["a"].app.test_client() if plan == "ANONYMOUS" else probe["login"](plan)[0]


def _counts(probe):
    result = []
    with sqlite3.connect(probe["path"]) as conn:
        for table in ("shark_memory", "shark_context_snapshots"):
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            result.append(conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] if exists else 0)
    return tuple(result)


def _get(probe, client, path):
    before = _counts(probe)
    response = client.get(path, base_url="http://127.0.0.1")
    assert response.status_code == 200, response.get_data(as_text=True)
    assert _counts(probe) == before, "A read must not debit a question or save its snapshot"
    body = response.get_data(as_text=True)
    assert probe["draft_canary"] not in body
    return response, body


@pytest.mark.parametrize("path", ["/shark", "/shark-ai"])
@pytest.mark.parametrize("plan", ["ANONYMOUS", "FREE", "PRO", "ELITE"])
def test_featured_html_uses_actual_principal_and_paid_entitlement(featured_probe, plan, path):
    probe = featured_probe
    _, body = _get(probe, _client(probe, plan), path)
    exposed = probe["published_canary"] in body
    assert exposed == (plan == "ELITE")
    if plan == "ELITE":
        assert "v933-pick-card is-featured" in body, "Positive control must reach the real featured template"


@pytest.mark.parametrize("plan", ["ANONYMOUS", "FREE", "PRO"])
def test_legacy_free_pick_row_still_requires_minimum_pro(featured_probe, plan):
    probe = featured_probe
    with sqlite3.connect(probe["path"]) as conn:
        conn.execute("UPDATE picks SET membership_required=? WHERE id=?", ("FREE", probe["published_pick"]))
    _, body = _get(probe, _client(probe, plan), "/shark")
    assert (probe["published_canary"] in body) == (plan == "PRO")


@pytest.mark.parametrize("tier", ["UNKNOWN", "ADMIN"])
@pytest.mark.parametrize("plan", ["PRO", "ELITE"])
def test_raw_unknown_or_admin_tier_does_not_normalize_into_featured_customer_advice(featured_probe, plan, tier):
    probe = featured_probe
    with sqlite3.connect(probe["path"]) as conn:
        conn.execute("UPDATE picks SET membership_required=? WHERE id=?", (tier, probe["published_pick"]))
    _, body = _get(probe, _client(probe, plan), "/shark")
    assert probe["published_canary"] not in body


@pytest.mark.parametrize("path", ["/shark", "/shark-ai"])
def test_shared_summary_primed_by_elite_never_authorizes_free_or_anonymous(featured_probe, path):
    probe = featured_probe
    elite = _client(probe, "ELITE")
    _, allowed = _get(probe, elite, path)
    assert probe["published_canary"] in allowed
    assert "refreshed" in probe["summary_observations"]
    for plan in ("FREE", "ANONYMOUS", "PRO"):
        _, body = _get(probe, _client(probe, plan), path)
        assert probe["published_canary"] not in body
        assert probe["summary_observations"][-1] == "hit", "Exercise the real shared summary cache"
    _, allowed_again = _get(probe, elite, path)
    assert probe["published_canary"] in allowed_again, "Filtering must not mutate the shared sports payload"


def _revoke_pick(probe, mutation):
    with sqlite3.connect(probe["path"]) as conn:
        if mutation == "deleted":
            conn.execute("DELETE FROM picks WHERE id=?", (probe["published_pick"],))
        elif mutation == "draft":
            conn.execute("UPDATE picks SET status=? WHERE id=?", ("draft", probe["published_pick"]))
        else:
            assert mutation == "unknown_tier"
            conn.execute("UPDATE picks SET membership_required=? WHERE id=?", ("UNKNOWN", probe["published_pick"]))


@pytest.mark.parametrize("path", ["/shark", "/shark-ai"])
@pytest.mark.parametrize("mutation", ["draft", "unknown_tier", "deleted"])
def test_cached_featured_row_does_not_override_current_stored_authorization(featured_probe, mutation, path):
    probe = featured_probe
    client = _client(probe, "ELITE")
    _, allowed = _get(probe, client, path)
    assert probe["published_canary"] in allowed
    _revoke_pick(probe, mutation)
    _, body = _get(probe, client, path)
    assert probe["summary_observations"][-1] == "hit"
    assert probe["published_canary"] not in body


@pytest.mark.parametrize("path", ["/shark", "/shark-ai"])
def test_expired_real_membership_cannot_keep_cached_featured_advice(featured_probe, path):
    probe = featured_probe
    client = _client(probe, "ELITE")
    _, allowed = _get(probe, client, path)
    assert probe["published_canary"] in allowed
    with sqlite3.connect(probe["path"]) as conn:
        conn.execute("UPDATE users SET membership_expires_at=? WHERE id=?",
                     ((datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), probe["users"]["ELITE"][0]))
    _, body = _get(probe, client, path)
    assert probe["summary_observations"][-1] == "hit"
    assert probe["published_canary"] not in body
    with client.session_transaction(base_url="http://127.0.0.1") as session:
        assert session["membership"] == "FREE"


@pytest.mark.parametrize("tier", ["UNKNOWN", "ADMIN"])
@pytest.mark.parametrize("plan", ["PRO", "ELITE"])
def test_briefing_does_not_authorize_a_coerced_unknown_or_admin_tier(featured_probe, plan, tier):
    probe = featured_probe
    with sqlite3.connect(probe["path"]) as conn:
        conn.execute("UPDATE picks SET membership_required=? WHERE id=?", (tier, probe["published_pick"]))
    response, body = _get(probe, _client(probe, plan), "/api/shark/briefing")
    assert response.is_json
    assert probe["published_canary"] not in body


@pytest.mark.parametrize("mutation", ["draft", "unknown_tier", "deleted"])
def test_briefing_rechecks_current_raw_row_after_shared_cache_hit(featured_probe, mutation):
    probe = featured_probe
    client = _client(probe, "ELITE")
    _, allowed = _get(probe, client, "/api/shark/briefing")
    assert probe["published_canary"] in allowed, "Positive control must traverse the real JSON briefing"
    _revoke_pick(probe, mutation)
    response, body = _get(probe, client, "/api/shark/briefing")
    assert response.is_json
    assert probe["summary_observations"][-1] == "hit"
    assert probe["published_canary"] not in body
