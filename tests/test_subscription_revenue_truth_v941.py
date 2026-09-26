"""V941 commercial truth: access grants never inflate paid subscriptions or MRR."""
import sqlite3

from engines import stripe_payments_engine as billing
from engines import subscription_control_engine as revenue


def make_db(tmp_path):
    path=str(tmp_path/"revenue.sqlite")
    con=sqlite3.connect(path)
    con.execute("""CREATE TABLE users(
        id TEXT PRIMARY KEY, role TEXT, membership TEXT, membership_source TEXT,
        membership_admin_granted INTEGER DEFAULT 0, membership_started_at TEXT,
        membership_expires_at TEXT, created_at TEXT
    )""")
    con.executemany(
        "INSERT INTO users(id,role,membership,membership_source,membership_admin_granted,created_at) VALUES(?,?,?,?,?,?)",
        [
            ("manual-pro","PRO","PRO","admin_manual",1,"2026-09-01"),
            ("stripe-elite","ELITE","ELITE","stripe",0,"2026-09-01"),
            ("free-user","FREE","FREE","free_signup",0,"2026-09-01"),
        ],
    )
    con.commit(); con.close()
    billing.ensure_stripe_schema(path)
    con=sqlite3.connect(path)
    con.execute("UPDATE users SET stripe_subscription_id='sub_elite',stripe_subscription_status='active',stripe_current_period_end='2030-01-01T00:00:00+00:00' WHERE id='stripe-elite'")
    con.execute("""INSERT INTO stripe_subscriptions
        (id,user_id,plan,stripe_subscription_id,status,current_period_end,cancel_at_period_end,last_event_at)
        VALUES('sub_elite','stripe-elite','ELITE','sub_elite','active','2030-01-01T00:00:00+00:00',0,'2026-09-26T08:00:00+00:00')""")
    con.commit(); con.close()
    return path


def test_manual_access_does_not_count_as_paid_or_mrr(tmp_path,monkeypatch):
    path=make_db(tmp_path)
    monkeypatch.setenv("STRIPE_PRICE_PRO_LABEL","9,99 €/mes")
    monkeypatch.setenv("STRIPE_PRICE_ELITE_LABEL","24,99 €/mes")
    result=revenue.subscription_summary(path,apply_rules=False,persist_metrics=False)
    assert result["active_paid"]==1
    assert result["paid_by_tier"]=={"PRO":0,"ELITE":1}
    assert result["manual_access"]==1
    assert result["manual_by_tier"]=={"PRO":1,"ELITE":0}
    assert result["estimated_mrr"]==24.99
    assert result["conversion_rate"]==round(100/3,1)
    assert result["revenue_scope"]=="active_stripe_subscriptions_only"
    assert result["estimated_mrr_verified_by_provider"] is False


def test_trialing_and_past_due_are_not_counted_as_active_mrr(tmp_path):
    path=make_db(tmp_path)
    con=sqlite3.connect(path)
    for status in ("trialing","past_due"):
        con.execute("UPDATE stripe_subscriptions SET status=? WHERE id='sub_elite'",(status,))
        con.commit()
        result=revenue.subscription_summary(path,apply_rules=False,persist_metrics=False)
        assert result["active_paid"]==0
        assert result["estimated_mrr"]==0
        assert result[status if status=="trialing" else "past_due"]==1
    con.close()


def test_manual_grant_never_gets_fake_billing_expiry(tmp_path):
    path=make_db(tmp_path)
    revenue.apply_subscription_rules(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=dict(con.execute("SELECT * FROM subscription_accounts WHERE user_id='manual-pro'").fetchone())
    con.close()
    assert row["source"]=="admin_manual"
    assert row["status"]=="active"
    assert row["current_period_end"] in (None,"")
    assert row["soft_block"]==0


def test_catalog_prices_match_stripe_visible_catalog(monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_PRO_LABEL","12,50 €/mes")
    monkeypatch.setenv("STRIPE_PRICE_ELITE_LABEL","29,90 €/mes")
    assert revenue.product_plan_prices()["PRO"]==12.50
    assert revenue.product_plan_prices()["ELITE"]==29.90


def test_readonly_summary_does_not_need_access_sync_to_report_manual_grants(tmp_path):
    path=make_db(tmp_path)
    con=sqlite3.connect(path)
    con.execute("DELETE FROM subscription_accounts")
    con.commit(); con.close()
    result=revenue.subscription_summary(path,apply_rules=False,persist_metrics=False)
    assert result["manual_access"]==1
    assert result["manual_by_tier"]=={"PRO":1,"ELITE":0}
    assert result["active_paid"]==1
