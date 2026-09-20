from __future__ import annotations

import sqlite3
from pathlib import Path

from engines import subscription_control_engine as subscriptions


ROOT = Path(__file__).resolve().parents[1]


def _revenue_db(tmp_path):
    path = tmp_path / "revenue-readonly.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE users(
                id TEXT PRIMARY KEY,
                membership TEXT,
                role TEXT,
                created_at TEXT
            )"""
        )
        conn.execute(
            "INSERT INTO users(id,membership,role,created_at) VALUES(?,?,?,?)",
            ("qa-revenue", "PRO", "PRO", "2026-09-20T00:00:00+00:00"),
        )
        conn.commit()
    subscriptions.ensure_subscription_schema(str(path))
    with sqlite3.connect(path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO subscription_accounts(
                user_id,tier,status,source,current_period_start,current_period_end,
                grace_until,soft_block,last_payment_status,created_at,updated_at,payload_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "qa-revenue",
                "PRO",
                "active",
                "stripe",
                "2026-09-20T00:00:00+00:00",
                "2030-09-20T00:00:00+00:00",
                None,
                0,
                "paid",
                "2026-09-20T00:00:00+00:00",
                "2026-09-20T00:00:00+00:00",
                "{}",
            ),
        )
        conn.execute("DELETE FROM revenue_daily_metrics")
        conn.commit()
    return path


def test_subscription_summary_can_be_read_without_persisting_daily_metrics(tmp_path):
    path = _revenue_db(tmp_path)

    result = subscriptions.subscription_summary(
        str(path),
        apply_rules=False,
        persist_metrics=False,
    )

    assert result["ok"] is True
    assert result["active_paid"] == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM revenue_daily_metrics").fetchone()[0] == 0


def test_subscription_summary_persists_metrics_only_when_explicit(tmp_path):
    path = _revenue_db(tmp_path)

    subscriptions.subscription_summary(
        str(path),
        apply_rules=False,
        persist_metrics=True,
    )

    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM revenue_daily_metrics").fetchone()[0] == 1


def test_admin_payments_get_does_not_apply_subscription_rules(app_module, monkeypatch):
    seen = {}

    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
    monkeypatch.setattr(app_module, "payment_readiness_snapshot", lambda _db: {"ok": True})
    monkeypatch.setattr(app_module, "stripe_runtime_status", lambda _db="": {"ok": True})

    def fail_rules(_db):
        raise AssertionError("GET /api/admin/payments must not mutate subscription rules")

    def summary(_db, apply_rules=True, persist_metrics=True):
        seen["apply_rules"] = apply_rules
        seen["persist_metrics"] = persist_metrics
        return {"ok": True, "active_paid": 0}

    monkeypatch.setattr(app_module, "apply_subscription_rules", fail_rules)
    monkeypatch.setattr(app_module, "subscription_summary", summary)

    response = app_module.app.test_client().get("/api/admin/payments")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["read_only"] is True
    assert payload["result"] is None
    assert seen == {"apply_rules": False, "persist_metrics": False}


def test_public_payment_status_paths_do_not_request_db_backed_stripe_summary():
    source = (ROOT / "app.py").read_text(encoding="utf-8")

    home = source.split("def home_light_data(", 1)[1].split("def _v931_provider_context", 1)[0]
    membership = source.split("def membership_page(", 1)[1].split('@app.route("/shark-ai")', 1)[0]
    admin = source.split("def admin_payments_page(", 1)[1].split('@app.route("/api/payments/checkout"', 1)[0]

    assert 'stripe_runtime_status("")' in home
    assert 'stripe_runtime_status("")' in membership
    assert "stripe_runtime_status(DB_PATH)" in admin
    assert "persist_metrics=False" in admin
