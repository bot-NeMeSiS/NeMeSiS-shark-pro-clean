"""Provider maintenance and PWA installation regression coverage. No real provider calls."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from engines import provider_maintenance_engine as provider

ROOT=Path(__file__).resolve().parents[1]


def test_provider_page_snapshot_is_network_free_and_detects_restriction(tmp_path,monkeypatch):
    db=tmp_path/"qa.db"
    with sqlite3.connect(db) as conn:
        conn.execute("""CREATE TABLE api_football_live_sync_state(
            key TEXT,last_sync_at TEXT,status TEXT,fixtures_count INTEGER,error TEXT)""")
        conn.execute("INSERT INTO api_football_live_sync_state VALUES(?,?,?,?,?)",
                     ("live",datetime.now(timezone.utc).isoformat(),"PROVIDER_FAILURE_BACKOFF_FREE_PLAN_RESTRICTED",0,"restricted"))
    monkeypatch.setenv("API_FOOTBALL_KEY","qa-placeholder")
    monkeypatch.setattr(provider.urllib.request,"urlopen",lambda *a,**k: (_ for _ in ()).throw(AssertionError("page read called provider")))
    snap=provider.provider_maintenance_snapshot(str(db))
    row=next(item for item in snap["providers"] if item["key"]=="api_football")
    assert snap["network_calls"]==0 and snap["truth_contract"]["configured_is_not_paid"]
    assert row["connection_state"]=="RESTRICTED"


def test_old_plan_evidence_is_not_current_payment_claim(tmp_path,monkeypatch):
    db=tmp_path/"qa.db"
    old=(datetime.now(timezone.utc)-timedelta(days=3)).isoformat()
    with sqlite3.connect(db) as conn:
        conn.execute("""CREATE TABLE api_exploitation_runs(
            id INTEGER PRIMARY KEY,finished_at TEXT,payload_json TEXT)""")
        conn.execute("INSERT INTO api_exploitation_runs VALUES(?,?,?)",
                     (1,old,json.dumps({"account":{"plan":"Pro","active":True,"quota":{}}})))
    monkeypatch.setenv("API_FOOTBALL_KEY","qa-placeholder")
    row=next(item for item in provider.provider_maintenance_snapshot(str(db))["providers"] if item["key"]=="api_football")
    assert row["billing_state"]=="PLAN_EVIDENCE_STALE"
    assert "caducada" in row["billing_label"].lower()


def test_manual_provider_check_is_persisted_and_becomes_direct_evidence(tmp_path,monkeypatch):
    db=tmp_path/"qa.db"
    monkeypatch.setattr(provider,"_test_api_football",lambda:{
        "ok":True,"connected":True,"http_status":200,"status":"CONNECTED","plan":"Pro",
        "plan_active":True,"plan_end":"2027-01-01","billing_state":"PLAN_REPORTED",
        "quota":{"daily_limit":1000,"daily_used":10},"external_calls":1,"secret_exposed":False,
        "checked_at":datetime.now(timezone.utc).isoformat(),
    })
    result=provider.test_provider_connection("api_football",str(db))
    assert result["persisted"] is True
    row=next(item for item in provider.provider_maintenance_snapshot(str(db))["providers"] if item["key"]=="api_football")
    assert row["connection_state"]=="DIRECT_VERIFIED"
    assert row["manual_check"] is True
    assert "Pro" in row["billing_label"]


def test_identity_and_install_surface_share_dynamic_icon_version():
    brand=(ROOT/"templates/partials/brand_logo.html").read_text()
    base=(ROOT/"templates/base.html").read_text()
    prompt=(ROOT/"templates/partials/pwa_install_prompt.html").read_text()
    js=(ROOT/"static/pwa-install.js").read_text()
    assert "8d0ed4207e73" not in brand
    assert "app_icon_version" in brand
    assert "manifest_json', v=app_icon_version" in base
    assert 'href="/instalar"' in base
    assert 'data-icon-version="{{ app_icon_version }}"' in prompt
    assert "nemesis-pwa-install-dismissed-" in js


def test_install_and_maintenance_routes(app_module):
    client=app_module.app.test_client()
    response=client.get("/instalar")
    assert response.status_code==200
    text=response.get_data(as_text=True)
    assert "Instala NeMeSiS como una app" in text
    assert "Añadir a pantalla de inicio" in text
    assert client.get("/admin/mantenimiento").status_code in (302,303)
    assert client.get("/api/admin/provider-maintenance").status_code==403
