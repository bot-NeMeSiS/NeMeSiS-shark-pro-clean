"""Budget/ownership adversaries for the isolated server-side binder."""
from contextlib import closing, contextmanager
from copy import deepcopy
import json
import sqlite3
import uuid

import pytest
from test_v990_financial_fixture_binding import case, NOW, match
from engines import client_combi_store as store
from engines import combi_advisor_engine as advisor
from engines import data_vault_engine as vault


@pytest.mark.parametrize("mode,expected_matches", [("direct", 2), ("mixed", 3), ("suggest", 2)])
def test_actual_read_budget_is_batched_in_existing_query_only_transaction(case, monkeypatch, record_property, mode, expected_matches):
    statements = []
    original = store.connection
    @contextmanager
    def traced(path, *, write=False):
        with original(path, write=write) as conn:
            assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
            assert conn.in_transaction
            conn.set_trace_callback(statements.append)
            yield conn
    monkeypatch.setattr(store, "connection", traced)
    body = ({"mode": "suggest", "count": 2} if mode == "suggest" else
            {"pick_ids": ["p0", case["direct"][2]]} if mode == "mixed" else
            {"pick_ids": [case["direct"][0], case["direct"][2]]})
    store.make_preview(case["path"], "elite", {**body, "stake": "0.10"}, now=NOW)
    matches = [sql for sql in statements if sql.upper().startswith("SELECT * FROM MATCHES ")]
    references = [sql for sql in statements if "FROM COMPETITIONS " in sql.upper()]
    record_property("observed_query_budget", {"mode": mode, "matches_selects": len(matches), "reference_selects": len(references),
                                             "query_only": True, "same_BEGIN_transaction": True})
    assert len(matches) == expected_matches
    assert all("WHERE ID IN (" in sql.upper() for sql in matches)
    assert len(references) == 1 and "WHERE KEY IN ('LALIGA')" in references[0].upper()


def test_binding_retains_every_owner_and_never_borrows_winner_price(case):
    with store.connection(case["path"]) as conn:
        originals = store.candidates(conn, {"membership": "ELITE"}, NOW, case["direct"])
        before = deepcopy(originals)
        bound = store._bind_fixture_identity(conn, originals)
    assert originals == before
    assert bound[0]["_verified_fixture_key"] == bound[1]["_verified_fixture_key"]
    assert "_verified_fixture_key" not in bound[2]  # canonical singleton is not a matched-fixture proof
    for original, current in zip(originals, bound):
        assert {key: value for key, value in current.items() if not key.startswith("_verified_fixture")} == original
        assert current["id"] == original["id"] and current["quote_id"] == original["quote_id"]
        assert current["odds"] == original["odds"]


def test_binder_over_200_fails_before_any_sql():
    class NoSQL:
        def execute(self, *args):
            raise AssertionError("over-limit cohort reached SQL")
    with pytest.raises(advisor.CombiError) as caught:
        store._bind_fixture_identity(NoSQL(), [{} for _ in range(201)])
    assert caught.value.code == "IDENTITY_EVIDENCE_UNAVAILABLE"


@pytest.mark.parametrize("invalid", ["missing", "duplicated"])
def test_current_match_association_must_be_complete_and_unique(case, invalid):
    with store.connection(case["path"]) as conn:
        current = store.candidates(conn, {"membership": "ELITE"}, NOW, [case["direct"][0], case["direct"][2]])
    with closing(sqlite3.connect(case["path"])) as conn, conn:
        if invalid == "missing":
            conn.execute("DELETE FROM matches WHERE id='api-one'")
        else:
            conn.execute("INSERT INTO matches SELECT * FROM matches WHERE id='api-one'")
    with store.connection(case["path"]) as conn:
        with pytest.raises(advisor.CombiError) as caught:
            store._bind_fixture_identity(conn, current)
    assert caught.value.code == "IDENTITY_EVIDENCE_UNAVAILABLE"


def test_identity_projection_limit_is_explicit_at_financial_boundary(case):
    with closing(sqlite3.connect(case["path"])) as conn, conn:
        conn.execute("ALTER TABLE matches ADD COLUMN home_team_aliases TEXT")
        conn.execute("UPDATE matches SET home_team_aliases=? WHERE id='api-one'", ("|".join(["Alias"] * 8),))
    with pytest.raises(advisor.CombiError) as caught:
        store.make_preview(case["path"], "elite", {"pick_ids": [case["direct"][0], case["direct"][2]]}, now=NOW)
    assert caught.value.code == "IDENTITY_EVIDENCE_UNAVAILABLE"


def test_reference_contract_error_does_not_fall_back_to_old_hash_only(case, monkeypatch):
    monkeypatch.setattr(vault, "read_competition_references_from_connection", lambda conn, keys:
                        [{"key": "unrequested", "name": "Wrong", "country": "Spain", "source": "API_FOOTBALL", "external_id": "140"}])
    with pytest.raises(advisor.CombiError) as caught:
        store.make_preview(case["path"], "elite", {"pick_ids": [case["direct"][0], case["direct"][2]]}, now=NOW)
    assert caught.value.code == "IDENTITY_EVIDENCE_UNAVAILABLE"


def test_suggestion_subset_save_persists_no_operation_local_proof(case):
    result = store.make_preview(case["path"], "elite", {"mode": "suggest", "count": 2, "stake": "0.10"}, now=NOW)
    body = {"pick_ids": [leg["id"] for leg in result["legs"]], "stake": "0.10", "revision": result["revision"], "request_id": uuid.uuid4().hex}
    saved = store.save_draft(case["path"], "elite", body, now=NOW)
    with closing(sqlite3.connect(case["path"])) as conn, conn:
        stored = conn.execute("SELECT payload_json FROM client_combi_drafts WHERE id=?", (saved["id"],)).fetchone()[0]
    assert "verified_fixture" not in stored
    payload = json.loads(stored)
    assert payload["revision"] == result["revision"]
    assert payload["legs"] == result["legs"]


def test_strong_bindings_do_not_override_conservative_event_key_and_advisor_stays_pure(case, monkeypatch):
    # Native singletons carry independently checked own raw proof. Canonical
    # singletons alone deliberately carry no verified-fixture marker.
    with closing(sqlite3.connect(case["path"])) as conn, conn:
        conn.execute("UPDATE matches SET competition_key='' WHERE id IN ('api-one','api-other')")
    with store.connection(case["path"]) as conn:
        current = store.candidates(conn, {"membership": "ELITE"}, NOW, [case["direct"][0], case["direct"][2]], bind_fixtures=True)
    assert current[0]["_verified_fixture_key"] != current[1]["_verified_fixture_key"]
    current[1]["event_key"] = current[0]["event_key"]
    def no_sql(*args, **kwargs):
        raise AssertionError("pure advisor attempted SQL")
    monkeypatch.setattr(sqlite3, "connect", no_sql)
    with pytest.raises(advisor.CombiError) as caught:
        advisor.preview(current, "0.10", user={"membership": "ELITE"}, now=NOW)
    assert caught.value.code == "DUPLICATE_EVENT"
    with pytest.raises(advisor.CombiError) as caught:
        advisor.suggest(current, 2, user={"membership": "ELITE"})
    assert caught.value.code == "INSUFFICIENT_EVIDENCE"


def test_complete_native_alias_proof_groups_without_a_requested_pk(case):
    replacement = match("sports-one", "60001")
    replacement["competition_key"] = ""
    replacement["home_team"] = "Granada"
    raw = json.loads(replacement["raw_json"])
    raw["teams"]["home"]["name"] = "Granada"
    replacement["raw_json"] = json.dumps(raw)
    with closing(sqlite3.connect(case["path"])) as conn, conn:
        conn.execute("UPDATE matches SET " + ",".join('"' + field + '"=?' for field in replacement) + " WHERE id='sports-one'", tuple(replacement.values()))
        conn.execute("UPDATE matches SET competition_key='' WHERE id='api-one'")
        conn.execute("DROP TABLE competitions")
    with store.connection(case["path"]) as conn:
        current = store.candidates(conn, {"membership": "ELITE"}, NOW, case["direct"][:2], bind_fixtures=True)
    assert current[0]["event_key"] != current[1]["event_key"]
    assert current[0]["_verified_fixture_key"] == current[1]["_verified_fixture_key"]
    assert {leg["_verified_fixture_basis"] for leg in current} == {"PROVIDER_NATIVE_FIXTURE"}
    with pytest.raises(advisor.CombiError) as caught:
        store.make_preview(case["path"], "elite", {"pick_ids": case["direct"][:2]}, now=NOW)
    assert caught.value.code == "DUPLICATE_EVENT"


def incoherent_singleton_raw(case):
    raw = json.loads(case["rows"][0]["raw_json"])
    raw["fixture"]["id"] = 999999
    with closing(sqlite3.connect(case["path"])) as conn, conn:
        conn.execute("UPDATE matches SET raw_json=? WHERE id='api-one'", (json.dumps(raw),))


def test_canonical_singleton_with_incoherent_raw_does_not_receive_fixture_marker(case):
    incoherent_singleton_raw(case)
    with store.connection(case["path"]) as conn:
        current = store.candidates(conn, {"membership": "ELITE"}, NOW, [case["direct"][0], case["direct"][2]], bind_fixtures=True)
    invalid = next(leg for leg in current if leg["match_id"] == "api-one")
    assert "_verified_fixture_key" not in invalid


def test_incoherent_canonical_singleton_preserves_prices_and_emits_missing_identity_warning(case):
    incoherent_singleton_raw(case)
    ids = [case["direct"][0], case["direct"][2]]
    before = open(case["path"], "rb").read()
    result = store.make_preview(case["path"], "elite", {"pick_ids": ids, "stake": "0.10"}, now=NOW)
    assert result["status"] == "DRAFT" and result["total_odds"] == "3.0400"
    assert [leg["id"] for leg in result["legs"]] == ids
    assert [leg["match_id"] for leg in result["legs"]] == ["api-one", "api-other"]
    assert [leg["quote_id"] for leg in result["legs"]] == ["q0", "q2"]
    assert any("identidad" in message.lower() for message in result["warnings"])
    assert result["probability"] is None and open(case["path"], "rb").read() == before
