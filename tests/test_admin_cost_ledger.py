"""Private company cost ledger: isolated SQLite, immutable corrections and real Admin HTTP."""
import hashlib
import sqlite3
import uuid

import pytest

from engines import company_cost_ledger as ledger


def row(**overrides):
    data = {
        "provider": "render",
        "month": "2026-10",
        "amount": "8.25",
        "currency": "USD",
        "status": "DECLARED",
        "request_id": uuid.uuid4().hex,
        "reference_note": "Test receipt",
    }
    return {**data, **overrides}


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "nemesis-costs.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO users VALUES ('preserved')")
    return str(path)


def test_empty_read_does_not_create_schema_modify_db_or_infer_zero(db):
    before = hashlib.sha256(open(db, "rb").read()).hexdigest()
    data = ledger.snapshot(db, "2026-10")
    assert data["state"] == "NOT_INITIALIZED"
    assert data["totals"] == {} and data["no_evidence_is_zero"] is False
    assert data["provider_calls"] == data["payment_actions"] == 0
    assert hashlib.sha256(open(db, "rb").read()).hexdigest() == before
    with sqlite3.connect(db) as conn:
        assert not conn.execute("SELECT name FROM sqlite_master WHERE name='company_cost_entries'").fetchone()


def test_write_and_read_keep_currency_and_evidence_separate(db):
    ledger.record_cost(db, row(status="PAID"), "admin")
    ledger.record_cost(db, row(provider="thesportsdb", currency="EUR", status="ESTIMATED", amount="10,00"), "admin")
    ledger.record_cost(db, row(provider="api_football", currency="EUR", status="INVOICED", amount="20"), "admin")
    data = ledger.snapshot(db, "2026-10")
    assert data["entry_count"] == 3 and data["state"] == "READABLE"
    assert data["totals"]["USD"]["PAID"]["amount"] == "8.25"
    assert data["totals"]["EUR"]["ESTIMATED"]["amount"] == "10.00"
    assert data["totals"]["EUR"]["INVOICED"]["amount"] == "20.00"
    assert "EUR" not in data["totals"]["USD"]
    assert data["income_state"] == "NOT_RECONCILED"
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT id FROM users").fetchone()[0] == "preserved"


def test_idempotent_replay_never_double_counts(db):
    payload = row(status="DECLARED")
    first = ledger.record_cost(db, payload, "admin")
    second = ledger.record_cost(db, payload, "admin")
    assert first["id"] == second["id"] and second["repeated"] is True
    assert ledger.snapshot(db, "2026-10")["entry_count"] == 1
    with pytest.raises(ValueError):
        ledger.record_cost(db, {**payload, "amount": "123.45"}, "admin")


def test_void_retains_audit_and_removes_active_total(db):
    first = ledger.record_cost(db, row(), "admin")
    ledger.void_cost(db, first["id"], "admin", "Asiento duplicado")
    state = ledger.snapshot(db, "2026-10")
    assert state["rows"][0]["voided_at"]
    assert state["entry_count"] == 0 and state["totals"] == {}
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM company_cost_entries").fetchone()[0] == 1
        assert [r[0] for r in conn.execute("SELECT action FROM company_cost_audit ORDER BY id")] == ["CREATE", "VOID"]
    with pytest.raises(ValueError):
        ledger.void_cost(db, first["id"], "admin", "Repetir anulación")


@pytest.mark.parametrize("changes", [
    {"amount": "-1"}, {"amount": "NaN"}, {"amount": "1.999"},
    {"amount": "0"}, {"amount": "1000001"},
    {"currency": "GBP"}, {"month": "2026-13"},
    {"provider": "paypal"}, {"status": "AUTOVERIFIED"},
    {"request_id": "bad"}, {"reference_note": "token=secret"},
])
def test_invalid_values_fail_closed_without_data_mutation(db, changes):
    before = hashlib.sha256(open(db, "rb").read()).hexdigest()
    with pytest.raises(ValueError):
        ledger.record_cost(db, row(**changes), "admin")
    assert hashlib.sha256(open(db, "rb").read()).hexdigest() == before


def test_missing_database_is_not_created(tmp_path):
    missing = str(tmp_path / "missing.sqlite")
    assert ledger.snapshot(missing)["state"] == "READ_UNAVAILABLE"
    with pytest.raises(ValueError):
        ledger.record_cost(missing, row(), "admin")
    assert not (tmp_path / "missing.sqlite").exists()


def test_prior_month_not_falsely_added_to_current_month(db):
    ledger.record_cost(db, row(month="2026-09", amount="40", currency="EUR"), "admin")
    assert ledger.snapshot(db, "2026-10")["totals"] == {}
    assert ledger.snapshot(db, "2026-09")["totals"]["EUR"]["DECLARED"]["amount"] == "40.00"


@pytest.fixture
def admin_browser(app_module, tmp_path, monkeypatch):
    a = app_module
    monkeypatch.setattr(a, "DB_PATH", str(tmp_path / "private-app.sqlite"))
    monkeypatch.setattr(a, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(a, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(a, "APP_INITIALIZED", False)
    monkeypatch.setattr(a, "LOCAL_SAFE_DATA_DIR", tmp_path)
    a.seed_core()
    a.app.config.update(TESTING=True)
    client = a.app.test_client()
    with client.session_transaction() as session:
        session.update(user_id="SIMULATED_QA_admin", user_role="ADMIN", membership="ADMIN")
        token = a.generate_csrf_token(session)
    return a, client, token


def test_admin_cost_routes_protected_and_csrf(admin_browser):
    a, client, token = admin_browser
    anon = a.app.test_client()
    assert anon.get("/admin/finanzas").status_code == 302
    assert anon.get("/api/admin/company-costs").status_code == 403
    assert anon.post("/admin/finanzas", data=row()).status_code == 302
    assert client.get("/api/admin/company-costs").status_code == 200
    assert client.get("/admin/finanzas").status_code == 200
    assert client.get("/admin/costes").status_code == 200
    assert client.post("/admin/finanzas", data=row()).status_code == 403
    payload = row()
    response = client.post("/admin/finanzas", data={**payload, "csrf_token": token})
    assert response.status_code == 303, response.get_data(as_text=True)[:300]
    assert client.get("/api/admin/company-costs?month=2026-10").get_json()["ledger"]["entry_count"] == 1


def test_csrf_required_for_void_and_finance_link_visible(admin_browser):
    _, client, token = admin_browser
    payload = row()
    client.post("/admin/finanzas", data={**payload, "csrf_token": token})
    # Access the client DB from the test fixture; no raw session data is persisted.
    # The API is admin-only; it contains safe non-sensitive cost fields.
    costs = client.get("/api/admin/company-costs?month=2026-10").get_json()["ledger"]
    ident = costs["rows"][0]["id"]
    assert client.post("/admin/finanzas/void/" + ident, data={"reason":"Duplicado"}).status_code == 403
    assert client.post("/admin/finanzas/void/" + ident, data={"csrf_token":token, "reason":"Duplicado"}).status_code == 303
    assert client.get("/api/admin/company-costs?month=2026-10").get_json()["ledger"]["entry_count"] == 0
    company = client.get("/admin/company-os")
    assert company.status_code == 200
    assert "/admin/finanzas" in company.get_data(as_text=True)
