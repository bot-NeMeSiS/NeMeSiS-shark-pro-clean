import sqlite3

import pytest

from engines import stripe_payments_engine as billing


@pytest.fixture
def account(app_module,tmp_path):
    source=sqlite3.connect(app_module.DB_PATH)
    try:
        schema=source.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()[0]
    finally:
        source.close()
    path=tmp_path/'billing.sqlite'
    with sqlite3.connect(path) as con:
        con.execute(schema)
    billing.ensure_stripe_schema(str(path))
    con=sqlite3.connect(path)
    con.row_factory=sqlite3.Row
    con.execute("INSERT INTO users(id,name,email,password_hash,created_at,role,membership,membership_source,membership_admin_granted,stripe_subscription_id) VALUES('qa-billing','Local QA','billing@example.invalid','invalid_qa_hash','2026-09-19','ELITE','ELITE','stripe',0,'sub_current_qa')")
    yield con
    con.close()


def deliver(con,status='canceled',subscription='sub_current_qa'):
    return billing.apply_subscription_to_user(con,dict(user_id='qa-billing',plan='PRO',status=status,
        subscription_id=subscription,customer_id='cus_local_qa',current_period_end='2030-01-01T00:00:00+00:00',cancel_at_period_end=1),'SIMULATED_QA')


@pytest.mark.parametrize('status',['active','canceled'])
def test_manual_grant_survives_subscription_events(account,status):
    account.execute("UPDATE users SET membership_source='admin_manual',membership_admin_granted=1")
    deliver(account,status)
    row=billing.user_by_id(account,'qa-billing')
    assert (row['membership'],row['membership_source'],row['membership_admin_granted'])==('ELITE','admin_manual',1)
    assert account.execute('SELECT count(*) FROM stripe_subscriptions').fetchone()[0]==1


def test_admin_role_is_not_replaced_by_paid_plan(account):
    account.execute("UPDATE users SET role='ADMIN',membership='ADMIN'")
    deliver(account,'active')
    assert billing.user_by_id(account,'qa-billing')['role']=='ADMIN'


def test_old_subscription_cannot_cancel_current_access(account):
    deliver(account,subscription='sub_previous_qa')
    assert billing.user_by_id(account,'qa-billing')['membership']=='ELITE'


def test_current_paid_cancellation_still_removes_paid_access(account):
    deliver(account)
    assert billing.user_by_id(account,'qa-billing')['membership']=='FREE'


def test_active_cancel_at_period_end_does_not_cancel_early(account):
    deliver(account,'active')
    row=billing.user_by_id(account,'qa-billing')
    assert row['membership']=='PRO'
    assert row['membership_expires_at']=='2030-01-01T00:00:00+00:00'


def test_local_safe_checkout_does_not_contact_stripe_or_write(account,monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('Stripe SDK must remain disconnected')
    monkeypatch.setattr(billing,'stripe_sdk',forbidden)
    result=billing.create_checkout_session('unused',{'id':'qa-billing'},'PRO')
    assert result['status']=='LOCAL_SAFE_BLOCKED'
    assert result['external_calls']==result['membership_changes']==0


@pytest.mark.parametrize('role,plan,expected', [('ADMIN','ELITE','ELITE'),('PRO','PRO','FREE'),('ELITE','ELITE','FREE')])
def test_local_expiration_preserves_admin_authority(app_module, account, monkeypatch, role, plan, expected):
    account.execute("UPDATE users SET role=?,membership=?,membership_expires_at='2000-01-01T00:00:00+01:00'",(role,plan))
    account.commit()
    path = account.execute('PRAGMA database_list').fetchone()[2]
    monkeypatch.setattr(app_module, 'db', lambda: sqlite3.connect(path))
    assert app_module.expire_user_memberships_if_needed('qa-billing')
    row=billing.user_by_id(account,'qa-billing')
    assert row['membership']==expected
    assert row['role']==('ADMIN' if role=='ADMIN' else 'FREE')


@pytest.mark.parametrize('plan,pro,elite', [('FREE',False,False),('PRO',True,False),('ELITE',True,True)])
def test_existing_plan_gates_are_not_bypassed_by_client_presentation(plan,pro,elite):
    from engines.membership_engine import can_access_feature
    user={'role':plan,'membership':plan}
    assert can_access_feature(user,'picks_pro') is pro
    assert can_access_feature(user,'picks_elite') is elite
    assert can_access_feature(user,'auto_picks') is elite
