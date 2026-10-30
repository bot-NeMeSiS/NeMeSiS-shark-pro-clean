"""SHARK selected-pick authorization through real LOCAL SAFE HTTP.

This regression deliberately keeps
real Flask routes, password login, CSRF, session validation, SQL selection,
normalization, SHARK answer generation and plan-quota consumption in place.
Only an unrelated upstream sports-summary cache is replaced with an empty
canonical-shaped snapshot. Do not run against a real account or production DB.
VIP in the discussion corresponds to the existing paid ELITE plan, not a new role.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import secrets
import sqlite3
import sys

import pytest
from werkzeug.security import generate_password_hash

from engines.madrid_time_engine import MADRID_TZ


def fixture_match_times(now):
    """Keep fixture dates and display time aligned with the future kickoff."""
    kickoff = now.astimezone(timezone.utc) + timedelta(hours=3)
    local = kickoff.astimezone(MADRID_TZ)
    return local.date().isoformat(), kickoff.isoformat(), local.strftime("%H:%M")


@pytest.fixture
def shark_probe(monkeypatch, tmp_path):
    # The supervisor owns App initialization and the filesystem/network boundary.
    # Importing App here would silently create a different, unsupervised harness.
    a = sys.modules.get("app")
    assert a is not None, "Run through the existing LOCAL SAFE supervisor first"
    assert a.local_safe_mode_enabled(), "This probe is LOCAL SAFE only"
    assert Path(tmp_path).resolve().is_relative_to(Path(a.LOCAL_SAFE_DATA_DIR).resolve())
    path = tmp_path / "shark-selected-pick-probe.sqlite"
    monkeypatch.setattr(a, "DB_PATH", str(path))
    monkeypatch.setattr(a, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(a, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(a, "APP_INITIALIZED", False)
    # Disable TESTING-only synthetic-session fallbacks. Login must create a real
    # revocable identity from an actual owned users row.
    monkeypatch.setitem(a.app.config, "TESTING", False)
    a.seed_core()
    token = secrets.token_hex(10)
    password = secrets.token_urlsafe(30)
    now = datetime.now(timezone.utc)
    stamp = now.isoformat()
    match_date, kickoff_iso, kickoff_time = fixture_match_times(now)
    published_match = "qa-shark-public-match-" + token
    draft_match = "qa-shark-draft-match-" + token
    published_pick = "qa-shark-elite-pick-" + token
    draft_pick = "qa-shark-draft-pick-" + token
    published_canary = "SIMULATED_QA_ELITE_REASON_" + token
    draft_canary = "SIMULATED_QA_DRAFT_REASON_" + token
    users = {}
    with sqlite3.connect(path) as conn:
        for plan in ("FREE", "PRO", "ELITE"):
            ident = "qa-shark-" + plan.lower() + "-" + token
            email = ident + "@example.invalid"
            users[plan] = (ident, email)
            conn.execute(
                """INSERT INTO users
                   (id,name,username,email,password_hash,role,membership,
                    membership_source,membership_expires_at,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (ident, "Owned synthetic " + plan, ident, email,
                 generate_password_hash(password), plan, plan, "admin_manual",
                 (now + timedelta(days=365)).isoformat(), stamp),
            )
        for mid in (published_match, draft_match):
            conn.execute(
                """INSERT INTO matches
                   (id,sport_key,home_team,away_team,competition_name,
                    match_date,kickoff_iso,kickoff_time,status,source)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (mid, "soccer", "QA Norte", "QA Sur", "Liga synthetic QA",
                 match_date, kickoff_iso, kickoff_time, "NS", "SIMULATED_QA"),
            )
        for pid, mid, state, canary in (
            (published_pick, published_match, "published", published_canary),
            (draft_pick, draft_match, "draft", draft_canary),
        ):
            conn.execute(
                """INSERT INTO picks
                   (id,match_id,home_team,away_team,market,selection,reasoning,
                    status,membership_required,odds,bookmaker,source,
                    match_date,created_at,updated_at,published_at,raw_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (pid, mid, "QA Norte", "QA Sur", "1x2", "1", canary,
                 state, "ELITE", 1.8, "Synthetic QA bookmaker", "SIMULATED_QA",
                 match_date, stamp, stamp,
                 stamp if state == "published" else None,
                 json.dumps({"qa_private_marker": canary})),
            )
    # These are upstream collections, not selected-pick/authorization mocks.
    monkeypatch.setattr(a, "get_public_home_sports_summary", lambda *, _home_only=False: {
        "storage_status": "ok", "valid_matches_today": [],
        "valid_live_events": [], "valid_upcoming_matches": [],
        "all_picks": [], "valid_active_picks": [],
    })

    def quota_count(user_id):
        with sqlite3.connect(path) as conn:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='shark_memory'"
            ).fetchone()
            if not exists:
                return 0
            return conn.execute(
                "SELECT COUNT(*) FROM shark_memory WHERE user_id=? AND event_type='client_question'",
                (user_id,),
            ).fetchone()[0]

    def login(plan):
        client = a.app.test_client()
        page = client.get("/cliente-login", base_url="http://127.0.0.1")
        assert page.status_code == 200
        with client.session_transaction(base_url="http://127.0.0.1") as state:
            csrf = state.get("csrf_token")
        assert csrf
        response = client.post(
            "/cliente-login", base_url="http://127.0.0.1",
            data={"login": users[plan][1], "password": password, "csrf_token": csrf},
        )
        assert response.status_code in (302, 303), response.status_code
        with client.session_transaction(base_url="http://127.0.0.1") as state:
            assert state.get("user_id") == users[plan][0]
            assert state.get("auth_session_id"), "Actual login must create revocable session identity"
            csrf = state.get("csrf_token")
        assert csrf
        return client, csrf

    return dict(a=a, path=path, users=users, login=login, quota_count=quota_count,
                published_match=published_match, draft_match=draft_match,
                published_pick=published_pick, draft_pick=draft_pick,
                published_canary=published_canary, draft_canary=draft_canary)


def _ask(probe, plan, selector, *, draft=False, csrf_valid=True):
    client, csrf = probe["login"](plan)
    user_id = probe["users"][plan][0]
    before = probe["quota_count"](user_id)
    key = ("draft_" if draft else "published_") + ("match" if selector in {"match_id", "match"} else "pick")
    response = client.post(
        "/api/shark/ask", base_url="http://127.0.0.1",
        headers={"X-CSRF-Token": csrf if csrf_valid else "invalid-owned-probe-token"},
        json={"question": "Explica el pronostico seleccionado", selector: probe[key],
              # These attacker-controlled fields must never determine the plan.
              "membership": "ADMIN", "user_id": probe["users"]["ELITE"][0]},
    )
    after = probe["quota_count"](user_id)
    payload = response.get_json()
    print("SHARK_BOUNDARY_PROBE " + json.dumps({
        "plan": plan, "selector": selector, "draft": draft,
        "http": response.status_code, "quota_before": before, "quota_after": after,
        "published_marker_exposed": probe["published_canary"] in response.get_data(as_text=True),
        "draft_marker_exposed": probe["draft_canary"] in response.get_data(as_text=True),
        "selected_context_fields": sorted((((payload or {}).get("shark") or {}).get("context") or {}).get("pick", {}).keys()),
    }, ensure_ascii=True), flush=True)
    return response, payload, before, after


@pytest.mark.parametrize("plan", ["FREE", "PRO", "ELITE"])
@pytest.mark.parametrize("selector", ["match_id", "pick_id", "match", "pick"])
def test_selected_published_pick_respects_actual_paid_plan(shark_probe, plan, selector):
    response, payload, before, after = _ask(shark_probe, plan, selector)
    assert response.status_code == 200, response.get_data(as_text=True)
    assert payload["ok"] is True
    assert after == before + 1
    assert payload["usage"]["membership"] == plan
    context = payload["shark"]["context"]
    assert context["user"]["id"] == shark_probe["users"][plan][0]
    assert context["user"]["membership"] == plan
    body = response.get_data(as_text=True)
    if plan == "ELITE":
        assert context["pick"]["id"] == shark_probe["published_pick"]
        assert shark_probe["published_canary"] in body
    else:
        assert shark_probe["published_canary"] not in body
        with sqlite3.connect(shark_probe["path"]) as conn:
            snapshots = conn.execute("SELECT payload_json FROM shark_context_snapshots").fetchall()
        assert all(shark_probe["published_canary"] not in row[0] for row in snapshots)
        assert context.get("pick", {}).get("id") != shark_probe["published_pick"]
    assert shark_probe["draft_canary"] not in body


@pytest.mark.parametrize("plan", ["FREE", "ELITE"])
@pytest.mark.parametrize("selector", ["match_id", "pick_id", "match", "pick"])
def test_selected_draft_is_never_client_advice(shark_probe, plan, selector):
    response, payload, before, after = _ask(shark_probe, plan, selector, draft=True)
    assert response.status_code == 200
    assert payload["ok"] is True
    assert after == before + 1
    body = response.get_data(as_text=True)
    assert shark_probe["draft_canary"] not in body
    assert payload["shark"]["context"].get("pick", {}).get("id") != shark_probe["draft_pick"]


def test_real_csrf_rejects_before_real_quota_or_selected_lookup(shark_probe):
    response, payload, before, after = _ask(shark_probe, "FREE", "match_id", csrf_valid=False)
    assert response.status_code == 403
    assert payload["error"] == "csrf_required"
    assert after == before
    assert shark_probe["published_canary"] not in response.get_data(as_text=True)


@pytest.mark.parametrize("path", ["/shark", "/shark-ai"])
@pytest.mark.parametrize("selector", ["pick", "pick_id", "match", "match_id"])
def test_quick_get_aliases_never_disclose_elite_advice_to_free(shark_probe, path, selector):
    client, _ = shark_probe["login"]("FREE")
    target = shark_probe["published_pick" if selector in {"pick", "pick_id"} else "published_match"]
    before = shark_probe["quota_count"](shark_probe["users"]["FREE"][0])
    response = client.get(path, base_url="http://127.0.0.1",
                          query_string={"q": "pick", selector: target})
    assert response.status_code == 200
    assert shark_probe["published_canary"] not in response.get_data(as_text=True)
    assert shark_probe["quota_count"](shark_probe["users"]["FREE"][0]) == before


@pytest.mark.parametrize("state", ["draft", "archived", "telegram_test", "unknown", None])
def test_unpublished_or_unknown_state_is_not_selected(shark_probe, state):
    with sqlite3.connect(shark_probe["path"]) as conn:
        conn.execute("UPDATE picks SET status=? WHERE id=?", (state, shark_probe["published_pick"]))
    response, payload, _, _ = _ask(shark_probe, "ELITE", "pick_id")
    assert response.status_code == 200
    assert shark_probe["published_canary"] not in response.get_data(as_text=True)
    assert not payload["shark"]["context"]["pick"]


@pytest.mark.parametrize("state", ["published", "won", "lost", "void", "publicado", "ganado"])
def test_authorized_published_and_resolved_ids_remain_available(shark_probe, state):
    with sqlite3.connect(shark_probe["path"]) as conn:
        conn.execute("UPDATE picks SET status=? WHERE id=?", (state, shark_probe["published_pick"]))
    response, payload, _, _ = _ask(shark_probe, "ELITE", "pick_id")
    assert response.status_code == 200
    assert payload["shark"]["context"]["pick"]["id"] == shark_probe["published_pick"]
    assert shark_probe["published_canary"] in response.get_data(as_text=True)


@pytest.mark.parametrize("tier", ["UNKNOWN", "ADMIN"])
@pytest.mark.parametrize("selector", ["match_id", "pick_id"])
def test_raw_unsupported_or_admin_tier_does_not_coerce_to_customer_plan(shark_probe, tier, selector):
    with sqlite3.connect(shark_probe["path"]) as conn:
        conn.execute("UPDATE picks SET membership_required=? WHERE id=?",
                     (tier, shark_probe["published_pick"]))
    response, payload, _, _ = _ask(shark_probe, "ELITE", selector)
    assert response.status_code == 200
    assert shark_probe["published_canary"] not in response.get_data(as_text=True)
    assert not payload["shark"]["context"]["pick"]


@pytest.mark.parametrize("plan", ["FREE", "PRO"])
def test_legacy_free_label_still_obeys_paid_advice_policy(shark_probe, plan):
    with sqlite3.connect(shark_probe["path"]) as conn:
        conn.execute("UPDATE picks SET membership_required='FREE' WHERE id=?",
                     (shark_probe["published_pick"],))
    response, payload, _, _ = _ask(shark_probe, plan, "pick_id")
    assert response.status_code == 200
    exposed = shark_probe["published_canary"] in response.get_data(as_text=True)
    assert exposed is (plan == "PRO")


def test_match_chooses_latest_authorized_pick_not_latest_for_another_plan(shark_probe):
    older = "owned-pro-pick"
    marker = "SIMULATED_QA_PRO_REASON"
    stamp = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    with sqlite3.connect(shark_probe["path"]) as conn:
        conn.execute("""INSERT INTO picks
            (id,match_id,home_team,away_team,market,selection,reasoning,status,
             membership_required,odds,bookmaker,source,match_date,created_at,updated_at,published_at)
            SELECT ?,match_id,home_team,away_team,market,selection,?,'published',
                   'PRO',odds,bookmaker,source,match_date,?,?,? FROM picks WHERE id=?""",
            (older, marker, stamp, stamp, stamp, shark_probe["published_pick"]))
    response, payload, _, _ = _ask(shark_probe, "PRO", "match_id")
    assert response.status_code == 200
    assert payload["shark"]["context"]["pick"]["id"] == older
    assert marker in response.get_data(as_text=True)
    assert shark_probe["published_canary"] not in response.get_data(as_text=True)
    assert payload["shark"]["context"]["match"]["id"] == shark_probe["published_match"]


def test_expired_paid_membership_does_not_expose_selected_advice(shark_probe):
    with sqlite3.connect(shark_probe["path"]) as conn:
        conn.execute("UPDATE users SET membership_expires_at=? WHERE id=?",
                     ((datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),
                      shark_probe["users"]["ELITE"][0]))
    response, payload, _, _ = _ask(shark_probe, "ELITE", "pick_id")
    assert response.status_code == 200
    assert payload["usage"]["membership"] == "FREE"
    assert shark_probe["published_canary"] not in response.get_data(as_text=True)
