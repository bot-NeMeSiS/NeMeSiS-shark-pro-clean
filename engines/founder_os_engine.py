"""Founder OS company control, billing obligations, alerts and mobile Web Push."""
from __future__ import annotations
import calendar
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable

PROVIDER_CATALOG = {
    "render": {"label":"Render","category":"Infraestructura","criticality":"CRITICAL","config_any":("RENDER_EXTERNAL_URL","APP_PUBLIC_URL"),"enabled_env":"","optional":False},
    "the_odds_api": {"label":"The Odds API","category":"Datos / cuotas","criticality":"CRITICAL","config_any":("THE_ODDS_API_KEY",),"enabled_env":"ENABLE_ODDS_API","optional":False},
    "api_football": {"label":"API-Football","category":"Datos deportivos","criticality":"HIGH","config_any":("API_FOOTBALL_KEY","API_FOOTBALL_API_KEY"),"enabled_env":"ENABLE_API_FOOTBALL_PROVIDER","optional":False},
    "thesportsdb": {"label":"TheSportsDB","category":"Datos / fallback","criticality":"HIGH","config_any":("THESPORTSDB_KEY","THESPORTSDB_API_KEY"),"enabled_env":"","optional":False},
    "telegram": {"label":"Telegram","category":"Comunicaciones","criticality":"HIGH","config_all":("TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID"),"enabled_env":"ENABLE_TELEGRAM_AUTO","optional":False},
    "stripe": {"label":"Stripe","category":"Pagos","criticality":"HIGH","config_any":("STRIPE_SECRET_KEY",),"enabled_env":"PAYMENTS_ENABLED","optional":True},
    "openai": {"label":"OpenAI","category":"IA","criticality":"MEDIUM","config_any":("OPENAI_API_KEY",),"enabled_env":"","optional":True},
}
CADENCES={"monthly","quarterly","yearly","one_time","manual"}
PAYMENT_STATES={"UNKNOWN","PENDING","PAID","WAIVED"}
ALERT_SEVERITIES=("CRITICAL","HIGH","WARNING","INFO")

def utc_now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _safe(value,limit=180): return str(value or "").replace("\r"," ").replace("\n"," ").strip()[:limit]
def _env_present(name): return bool(_safe(os.getenv(name),10000))
def _env_flag(name,default=False):
    if not name: return True
    raw=str(os.getenv(name) or "").strip().lower()
    return default if not raw else raw in {"1","true","yes","on","enabled"}
def _connect(db_path):
    conn=sqlite3.connect(db_path,timeout=30,check_same_thread=False); conn.row_factory=sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=30000"); conn.execute("PRAGMA journal_mode=WAL"); conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.OperationalError: pass
    return conn
def _rows(conn,query,params=()):
    try: return [dict(r) for r in conn.execute(query,tuple(params)).fetchall()]
    except sqlite3.OperationalError: return []
def _one(conn,query,params=()):
    try:
        row=conn.execute(query,tuple(params)).fetchone(); return dict(row) if row else {}
    except sqlite3.OperationalError: return {}
def _table_exists(conn,table): return bool(_one(conn,"SELECT name FROM sqlite_master WHERE type='table' AND name=?",(table,)))
def _parse_json(value):
    try: data=json.loads(str(value or "{}"))
    except Exception: return {}
    return data if isinstance(data,dict) else {}
def _parse_date(value):
    text=_safe(value,10)
    if not text: return None
    try: return date.fromisoformat(text)
    except ValueError: return None
def _float_or_none(value):
    if value in (None,""): return None
    try: return round(max(0.0,float(str(value).replace(",","."))),2)
    except Exception: return None

def ensure_founder_os_schema(db_path):
    conn=_connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS founder_obligations(
        id TEXT PRIMARY KEY,provider_key TEXT,label TEXT NOT NULL,category TEXT,plan TEXT,amount REAL,currency TEXT DEFAULT 'EUR',
        cadence TEXT DEFAULT 'monthly',due_date TEXT,auto_renew INTEGER DEFAULT 0,payment_status TEXT DEFAULT 'UNKNOWN',
        last_paid_at TEXT,notes TEXT,active INTEGER DEFAULT 1,created_by TEXT,created_at TEXT,updated_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS founder_alerts(
        id TEXT PRIMARY KEY,fingerprint TEXT UNIQUE,source TEXT DEFAULT 'generated',severity TEXT DEFAULT 'INFO',category TEXT,
        title TEXT,message TEXT,entity_ref TEXT,due_at TEXT,status TEXT DEFAULT 'OPEN',push_eligible INTEGER DEFAULT 0,
        first_seen_at TEXT,last_seen_at TEXT,last_notified_at TEXT,acknowledged_at TEXT,resolved_at TEXT,payload_json TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS founder_push_subscriptions(
        endpoint_hash TEXT PRIMARY KEY,endpoint TEXT NOT NULL,p256dh TEXT NOT NULL,auth TEXT NOT NULL,user_id TEXT,user_agent TEXT,
        enabled INTEGER DEFAULT 1,created_at TEXT,updated_at TEXT,last_success_at TEXT,last_error_at TEXT)""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_founder_obligations_due ON founder_obligations(active,due_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_founder_alerts_status ON founder_alerts(status,severity,last_seen_at)")
    conn.commit(); conn.close()
    return {"ok":True,"schema":"FOUNDER-OS-V1"}

def _advance_due(raw_due,cadence):
    current=_parse_date(raw_due)
    if not current: return ""
    if cadence=="one_time": return ""
    months={"monthly":1,"quarterly":3,"yearly":12}.get(cadence)
    if not months: return current.isoformat()
    total=current.year*12+current.month-1+months; year,month0=divmod(total,12); month=month0+1
    day=min(current.day,calendar.monthrange(year,month)[1])
    return date(year,month,day).isoformat()

def _effective_state(row,today=None):
    today=today or datetime.now(timezone.utc).date()
    manual=(_safe(row.get("payment_status"),20) or "UNKNOWN").upper()
    due=_parse_date(row.get("due_date"))
    if manual=="WAIVED": return "WAIVED",None
    if not due: return ("PAID" if manual=="PAID" else "UNKNOWN"),None
    days=(due-today).days
    if days<0: return "OVERDUE",days
    if days<=1: return "DUE_NOW",days
    if days<=7: return "DUE_SOON",days
    if days<=30: return "UPCOMING",days
    return ("PAID" if manual=="PAID" else "PENDING"),days

def _public_obligation(row):
    state,days=_effective_state(row)
    return {"id":_safe(row.get("id"),80),"provider_key":_safe(row.get("provider_key"),60),"label":_safe(row.get("label"),140),
        "category":_safe(row.get("category"),80),"plan":_safe(row.get("plan"),100),"amount":row.get("amount"),
        "currency":_safe(row.get("currency"),8) or "EUR","cadence":_safe(row.get("cadence"),20),
        "due_date":_safe(row.get("due_date"),10),"auto_renew":bool(row.get("auto_renew")),
        "payment_status":_safe(row.get("payment_status"),20) or "UNKNOWN","effective_state":state,"days_to_due":days,
        "last_paid_at":_safe(row.get("last_paid_at"),80),"notes":_safe(row.get("notes"),800),"updated_at":_safe(row.get("updated_at"),80)}

def save_obligation(db_path,payload,actor="admin"):
    ensure_founder_os_schema(db_path); payload=dict(payload or {})
    oid=_safe(payload.get("id"),80) or f"obl:{uuid.uuid4().hex[:18]}"
    provider=_safe(payload.get("provider_key"),60).lower()
    if provider not in PROVIDER_CATALOG: provider="other"
    label=_safe(payload.get("label"),140)
    if not label: raise ValueError("La obligación necesita un nombre.")
    cadence=_safe(payload.get("cadence"),20).lower()
    if cadence not in CADENCES: cadence="monthly"
    due=_safe(payload.get("due_date"),10)
    if due and not _parse_date(due): raise ValueError("La fecha de vencimiento no es válida.")
    state=(_safe(payload.get("payment_status"),20) or "PENDING").upper()
    if state not in PAYMENT_STATES: state="PENDING"
    now=utc_now(); conn=_connect(db_path); old=_one(conn,"SELECT * FROM founder_obligations WHERE id=?",(oid,))
    conn.execute("""INSERT OR REPLACE INTO founder_obligations(
        id,provider_key,label,category,plan,amount,currency,cadence,due_date,auto_renew,payment_status,last_paid_at,notes,active,
        created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (oid,provider,label,_safe(payload.get("category"),80) or PROVIDER_CATALOG.get(provider,{}).get("category") or "Empresa",
         _safe(payload.get("plan"),100),_float_or_none(payload.get("amount")),(_safe(payload.get("currency"),8) or "EUR").upper(),
         cadence,due,int(str(payload.get("auto_renew") or "").lower() in {"1","true","yes","on"}),state,old.get("last_paid_at") or "",
         _safe(payload.get("notes"),800),1,old.get("created_by") or _safe(actor,80),old.get("created_at") or now,now))
    conn.commit(); row=_one(conn,"SELECT * FROM founder_obligations WHERE id=?",(oid,)); conn.close()
    return {"ok":True,"obligation":_public_obligation(row)}

def mark_obligation_paid(db_path,obligation_id,actor="admin"):
    ensure_founder_os_schema(db_path); conn=_connect(db_path)
    row=_one(conn,"SELECT * FROM founder_obligations WHERE id=? AND active=1",(_safe(obligation_id,80),))
    if not row: conn.close(); return {"ok":False,"reason":"NOT_FOUND"}
    now=utc_now(); next_due=_advance_due(row.get("due_date"),row.get("cadence") or "manual")
    conn.execute("UPDATE founder_obligations SET payment_status='PAID',last_paid_at=?,due_date=?,updated_at=? WHERE id=?",(now,next_due,now,row["id"]))
    conn.commit(); updated=_one(conn,"SELECT * FROM founder_obligations WHERE id=?",(row["id"],)); conn.close()
    return {"ok":True,"obligation":_public_obligation(updated),"actor":_safe(actor,80)}

def obligations_snapshot(db_path):
    ensure_founder_os_schema(db_path); conn=_connect(db_path)
    items=[_public_obligation(r) for r in _rows(conn,"SELECT * FROM founder_obligations WHERE active=1 ORDER BY COALESCE(due_date,'9999-12-31'),label")]
    conn.close(); counts={k:0 for k in ("OVERDUE","DUE_NOW","DUE_SOON","UPCOMING","PENDING","PAID","UNKNOWN","WAIVED")}
    monthly=0.0
    for item in items:
        counts[item["effective_state"]]=counts.get(item["effective_state"],0)+1
        if item.get("amount") is None: continue
        if item.get("cadence")=="monthly": monthly+=float(item["amount"])
        elif item.get("cadence")=="quarterly": monthly+=float(item["amount"])/3
        elif item.get("cadence")=="yearly": monthly+=float(item["amount"])/12
    return {"items":items,"counts":counts,"known_monthly_cost":round(monthly,2),"currency":"EUR",
            "billing_complete":bool(items) and all(i.get("amount") is not None and i.get("due_date") for i in items)}

def _automation_state(conn,key):
    if not _table_exists(conn,"automation_state"): return {}
    row=_one(conn,"SELECT value_json,updated_at FROM automation_state WHERE key=?",(key,))
    payload=_parse_json(row.get("value_json"))
    if row.get("updated_at") and not payload.get("last_sync"): payload["observed_at"]=row.get("updated_at")
    return payload

def _parse_datetime(value):
    text=_safe(value,100)
    if not text: return None
    try:
        parsed=datetime.fromisoformat(text.replace("Z","+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None: parsed=parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def _nonnegative_int(value):
    try: return max(0,int(value or 0))
    except (TypeError,ValueError): return 0

def sports_data_freshness_snapshot(db_path):
    """Read canonical sports freshness already persisted by the cron; never call providers."""
    ensure_founder_os_schema(db_path); conn=_connect(db_path)
    state_keys=("telegram_tick_last_detail","sports_sync_last_detail")
    for state_key in state_keys:
        detail=_automation_state(conn,state_key)
        compact=detail.get("compact") if isinstance(detail.get("compact"),dict) else {}
        pipeline=compact.get("sports_pipeline") if isinstance(compact.get("sports_pipeline"),dict) else {}
        freshness=pipeline.get("data_freshness") if isinstance(pipeline.get("data_freshness"),dict) else {}
        if not freshness:
            continue
        state=(_safe(freshness.get("state"),80) or "NOT_ESTABLISHED").upper()
        if state not in {"ESTABLISHED","PARTIAL","NOT_ESTABLISHED"}: state="NOT_ESTABLISHED"
        observed_at=_safe(detail.get("finished_at") or detail.get("called_at") or detail.get("observed_at") or compact.get("now_madrid"),100)
        observed_dt=_parse_datetime(observed_at)
        age_seconds=max(0,int((datetime.now(timezone.utc)-observed_dt).total_seconds())) if observed_dt else None
        result={
            "contract":"NEMESIS-FOUNDER-SPORTS-FRESHNESS-V1",
            "state":state,
            "entity_timestamps_evaluated":bool(freshness.get("entity_timestamps_evaluated")),
            "scope":_safe(freshness.get("scope"),120) or "MATCH_ROWS_CANONICAL_PROVIDER_CLOCKS",
            "total":_nonnegative_int(freshness.get("total")),
            "fresh":_nonnegative_int(freshness.get("fresh")),
            "observed":_nonnegative_int(freshness.get("observed")),
            "stale":_nonnegative_int(freshness.get("stale")),
            "not_established":_nonnegative_int(freshness.get("not_established")),
            "reason":_safe(freshness.get("reason"),500) or "La evidencia no incluye una explicación de frescura.",
            "observed_at":observed_at,
            "evidence_age_seconds":age_seconds,
            "source_state_key":state_key,
            "provider_calls":0,
        }
        conn.close()
        return result
    conn.close()
    return {
        "contract":"NEMESIS-FOUNDER-SPORTS-FRESHNESS-V1",
        "state":"NOT_ESTABLISHED",
        "entity_timestamps_evaluated":False,
        "scope":"MATCH_ROWS_CANONICAL_PROVIDER_CLOCKS",
        "total":0,"fresh":0,"observed":0,"stale":0,"not_established":0,
        "reason":"Founder OS todavía no tiene una observación persistida de frescura deportiva.",
        "observed_at":"","evidence_age_seconds":None,"source_state_key":"","provider_calls":0,
    }

def _provider_evidence(conn,key):
    if key=="the_odds_api":
        s=_automation_state(conn,"odds_events_sync"); q=s.get("quota") if isinstance(s.get("quota"),dict) else {}
        return {"state":_safe(s.get("status") or ("CACHE_REUSED" if s.get("skipped") else ""),80) or "UNKNOWN",
                "observed_at":_safe(s.get("last_sync") or s.get("time") or s.get("observed_at"),80),
                "external_calls":int(s.get("external_calls") or 0),"error_present":bool(s.get("errors")),
                "quota":{k:int(q.get(k) or 0) for k in ("requests_used","requests_remaining","observed_calls") if q.get(k) is not None}}
    if key=="thesportsdb":
        s=_automation_state(conn,"sportsdb_feed_sync")
        return {"state":_safe(s.get("status"),80) or "UNKNOWN","observed_at":_safe(s.get("last_sync") or s.get("time") or s.get("observed_at"),80),
                "external_calls":int(s.get("external_calls") or 0),"processed":int(s.get("processed") or 0),"error_present":bool(s.get("errors"))}
    if key=="api_football" and _table_exists(conn,"api_football_live_sync_state"):
        r=_one(conn,"SELECT * FROM api_football_live_sync_state WHERE key='live'")
        return {"state":_safe(r.get("status"),80) or "UNKNOWN","observed_at":_safe(r.get("last_sync_at"),80),
                "external_calls":int(r.get("external_calls") or 0),"processed":int(r.get("fixtures_count") or 0),"error_present":bool(r.get("error"))}
    if key=="telegram" and _table_exists(conn,"telegram_delivery_memory"):
        r=_one(conn,"SELECT status,sent_at_madrid,created_at FROM telegram_delivery_memory ORDER BY created_at DESC LIMIT 1")
        return {"state":_safe(r.get("status"),80) or "UNKNOWN","observed_at":_safe(r.get("sent_at_madrid") or r.get("created_at"),80),
                "error_present":str(r.get("status") or "").upper() in {"FAILED","ERROR"}}
    if key=="stripe" and _table_exists(conn,"payment_webhook_events"):
        r=_one(conn,"SELECT status,received_at,verified FROM payment_webhook_events ORDER BY received_at DESC LIMIT 1")
        return {"state":_safe(r.get("status"),80) or "NO_EVENTS","observed_at":_safe(r.get("received_at"),80),"verified":bool(r.get("verified")),"error_present":False}
    return {"state":"NO_LOCAL_EVIDENCE","observed_at":"","error_present":False}

def _configured(spec):
    all_names=tuple(spec.get("config_all") or ()); any_names=tuple(spec.get("config_any") or ())
    if all_names and not all(_env_present(x) for x in all_names): return False
    if any_names and not any(_env_present(x) for x in any_names): return False
    return bool(all_names or any_names) or spec.get("label")=="Render"

def providers_snapshot(db_path,obligations=None):
    ensure_founder_os_schema(db_path); obligations=obligations or obligations_snapshot(db_path)
    grouped={}
    for i in obligations.get("items") or []: grouped.setdefault(i.get("provider_key") or "other",[]).append(i)
    conn=_connect(db_path); items=[]
    for key,spec in PROVIDER_CATALOG.items():
        configured=_configured(spec); enabled=_env_flag(spec.get("enabled_env"),False) if spec.get("enabled_env") else None
        evidence=_provider_evidence(conn,key); obs=grouped.get(key,[]); states=[x.get("effective_state") for x in obs]
        billing="OVERDUE" if "OVERDUE" in states else "DUE_NOW" if "DUE_NOW" in states else "DUE_SOON" if "DUE_SOON" in states else "PAID" if obs and all(s=="PAID" for s in states) else "TRACKED" if obs else "UNKNOWN"
        plan=next((_safe(x.get("plan"),100) for x in obs if x.get("plan")),"")
        estate=_safe(evidence.get("state"),80) or "UNKNOWN"
        operational="NOT_CONFIGURED" if not configured else "DISABLED" if enabled is False else estate if estate!="NO_LOCAL_EVIDENCE" else "CONFIGURED"
        items.append({"key":key,"label":spec["label"],"category":spec["category"],"criticality":spec["criticality"],"optional":bool(spec.get("optional")),
                      "configured":configured,"enabled":enabled,"operational_state":operational,"evidence":evidence,
                      "billing_state":billing,"billing_tracked":bool(obs),"obligations":len(obs),"plan":plan or "UNKNOWN"})
    conn.close()
    return {"items":items,"configured":sum(1 for i in items if i["configured"]),"total":len(items),"billing_tracked":sum(1 for i in items if i["billing_tracked"])}

def _alert_id(fp): return "fa:"+hashlib.sha1(fp.encode()).hexdigest()[:22]
def _upsert_alert(conn,a):
    now=utc_now(); old=_one(conn,"SELECT * FROM founder_alerts WHERE fingerprint=?",(a["fingerprint"],))
    status=old.get("status") if old.get("status") in {"OPEN","ACK"} else "OPEN"
    conn.execute("""INSERT OR REPLACE INTO founder_alerts(id,fingerprint,source,severity,category,title,message,entity_ref,due_at,status,push_eligible,
        first_seen_at,last_seen_at,last_notified_at,acknowledged_at,resolved_at,payload_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (old.get("id") or _alert_id(a["fingerprint"]),a["fingerprint"],"generated",a["severity"],a["category"],a["title"],a["message"],a.get("entity_ref") or "",
         a.get("due_at") or "",status,int(bool(a.get("push_eligible"))),old.get("first_seen_at") or now,now,old.get("last_notified_at") or "",
         old.get("acknowledged_at") or "","",json.dumps(a.get("payload") or {},ensure_ascii=False)[:3000]))

def sync_generated_alerts(db_path,obligations=None,providers=None,sports_freshness=None):
    ensure_founder_os_schema(db_path); obligations=obligations or obligations_snapshot(db_path); providers=providers or providers_snapshot(db_path,obligations); sports_freshness=sports_freshness or sports_data_freshness_snapshot(db_path)
    desired={}; billing_map={"OVERDUE":("CRITICAL",True,"Pago vencido"),"DUE_NOW":("HIGH",True,"Pago vence ahora"),"DUE_SOON":("WARNING",True,"Pago próximo"),"UPCOMING":("INFO",False,"Renovación próxima")}
    for i in obligations.get("items") or []:
        if i.get("effective_state") not in billing_map: continue
        sev,push,prefix=billing_map[i["effective_state"]]; fp=f"billing:{i['id']}:{i.get('due_date') or 'unknown'}"
        amount=f"{i.get('amount'):.2f} {i.get('currency')}" if isinstance(i.get("amount"),(int,float)) else "importe por completar"
        desired[fp]={"fingerprint":fp,"severity":sev,"category":"BILLING","title":f"{prefix}: {i['label']}",
                     "message":f"{amount} · vencimiento {i.get('due_date') or 'sin fecha'}","entity_ref":i["id"],"due_at":i.get("due_date") or "","push_eligible":push}
    for i in providers.get("items") or []:
        if i.get("optional") and not i.get("configured"): continue
        if not i.get("configured"):
            fp=f"provider:{i['key']}:not_configured"; desired[fp]={"fingerprint":fp,"severity":"HIGH","category":"PROVIDER","title":f"{i['label']} sin configurar","message":"El proveedor no tiene la configuración mínima requerida.","entity_ref":i["key"],"push_eligible":True}; continue
        op=str(i.get("operational_state") or "").upper()
        if any(t in op for t in ("ERROR","FAIL","RESTRICT","BACKOFF")):
            fp=f"provider:{i['key']}:{op}"; desired[fp]={"fingerprint":fp,"severity":"WARNING","category":"PROVIDER","title":f"{i['label']} requiere atención","message":f"Estado operativo: {op}","entity_ref":i["key"],"push_eligible":True}
    sports_state=str(sports_freshness.get("state") or "NOT_ESTABLISHED").upper()
    if sports_state=="NOT_ESTABLISHED":
        fp="sports_data:freshness:not_established"; desired[fp]={"fingerprint":fp,"severity":"HIGH","category":"SPORTS_DATA","title":"Frescura deportiva no establecida","message":_safe(sports_freshness.get("reason"),500),"entity_ref":"sports_data_freshness","push_eligible":True}
    elif sports_state=="PARTIAL":
        fp="sports_data:freshness:partial"; desired[fp]={"fingerprint":fp,"severity":"WARNING","category":"SPORTS_DATA","title":"Frescura deportiva parcial","message":f"Stale: {_nonnegative_int(sports_freshness.get('stale'))} · sin reloj: {_nonnegative_int(sports_freshness.get('not_established'))} · muestra: {_nonnegative_int(sports_freshness.get('total'))}","entity_ref":"sports_data_freshness","push_eligible":True}
    conn=_connect(db_path)
    for a in desired.values(): _upsert_alert(conn,a)
    for row in _rows(conn,"SELECT id,fingerprint FROM founder_alerts WHERE source='generated' AND status IN ('OPEN','ACK')"):
        if row.get("fingerprint") not in desired: conn.execute("UPDATE founder_alerts SET status='RESOLVED',resolved_at=?,last_seen_at=? WHERE id=?",(utc_now(),utc_now(),row["id"]))
    conn.commit(); conn.close(); return {"ok":True,"active_generated":len(desired)}

def alerts_snapshot(db_path):
    ensure_founder_os_schema(db_path); conn=_connect(db_path)
    rows=_rows(conn,"""SELECT * FROM founder_alerts WHERE status IN ('OPEN','ACK') ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'WARNING' THEN 3 ELSE 4 END,last_seen_at DESC LIMIT 100"""); conn.close()
    items=[{"id":_safe(r.get("id"),80),"severity":_safe(r.get("severity"),20) or "INFO","category":_safe(r.get("category"),40),"title":_safe(r.get("title"),180),"message":_safe(r.get("message"),500),"entity_ref":_safe(r.get("entity_ref"),100),"due_at":_safe(r.get("due_at"),80),"status":_safe(r.get("status"),20),"push_eligible":bool(r.get("push_eligible")),"last_seen_at":_safe(r.get("last_seen_at"),80),"last_notified_at":_safe(r.get("last_notified_at"),80)} for r in rows]
    counts={s:sum(1 for i in items if i["severity"]==s and i["status"]=="OPEN") for s in ALERT_SEVERITIES}
    return {"items":items,"counts":counts,"open":sum(counts.values())}

def acknowledge_alert(db_path,alert_id):
    ensure_founder_os_schema(db_path); conn=_connect(db_path)
    conn.execute("UPDATE founder_alerts SET status='ACK',acknowledged_at=? WHERE id=? AND status='OPEN'",(utc_now(),_safe(alert_id,80))); changed=conn.total_changes; conn.commit(); conn.close()
    return {"ok":bool(changed),"acknowledged":bool(changed)}

def push_configuration():
    public=_safe(os.getenv("VAPID_PUBLIC_KEY"),500); private=bool(_safe(os.getenv("VAPID_PRIVATE_KEY"),10000)); subject=_safe(os.getenv("VAPID_SUBJECT"),300) or "https://bot-apuestas-crgf.onrender.com"; enabled=_env_flag("FOUNDER_PUSH_ENABLED",False)
    return {"enabled":enabled,"configured":bool(enabled and public and private and subject),"public_key":public,"private_key_present":private,"subject_present":bool(subject)}

def save_push_subscription(db_path,subscription,user_id="admin",user_agent=""):
    ensure_founder_os_schema(db_path); subscription=dict(subscription or {}); endpoint=_safe(subscription.get("endpoint"),2000); keys=subscription.get("keys") if isinstance(subscription.get("keys"),dict) else {}; p=_safe(keys.get("p256dh"),1000); auth=_safe(keys.get("auth"),500)
    if not endpoint.startswith("https://") or not p or not auth: raise ValueError("Suscripción push inválida.")
    hid=hashlib.sha256(endpoint.encode()).hexdigest(); now=utc_now(); conn=_connect(db_path); old=_one(conn,"SELECT created_at FROM founder_push_subscriptions WHERE endpoint_hash=?",(hid,))
    conn.execute("""INSERT OR REPLACE INTO founder_push_subscriptions(endpoint_hash,endpoint,p256dh,auth,user_id,user_agent,enabled,created_at,updated_at,last_success_at,last_error_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",(hid,endpoint,p,auth,_safe(user_id,100),_safe(user_agent,300),1,old.get("created_at") or now,now,"",""))
    conn.commit(); conn.close(); return {"ok":True,"subscription_id":hid[:12]}

def push_snapshot(db_path):
    ensure_founder_os_schema(db_path); cfg=push_configuration(); conn=_connect(db_path)
    count=_one(conn,"SELECT COUNT(*) AS total FROM founder_push_subscriptions WHERE enabled=1").get("total") or 0
    last=_one(conn,"SELECT last_success_at,last_error_at FROM founder_push_subscriptions WHERE enabled=1 ORDER BY updated_at DESC LIMIT 1"); conn.close()
    return {**cfg,"subscriptions":int(count),"last_success_at":_safe(last.get("last_success_at"),80),"last_error_at":_safe(last.get("last_error_at"),80)}

def _send_push(db_path,payload):
    cfg=push_configuration()
    if not cfg["configured"]: return {"ok":False,"status":"NOT_CONFIGURED","sent":0,"failed":0}
    try: from pywebpush import webpush
    except Exception: return {"ok":False,"status":"PYWEBPUSH_UNAVAILABLE","sent":0,"failed":0}
    private=str(os.getenv("VAPID_PRIVATE_KEY") or "").replace("\\n","\n"); conn=_connect(db_path); subs=_rows(conn,"SELECT * FROM founder_push_subscriptions WHERE enabled=1"); sent=failed=0
    for sub in subs:
        try:
            webpush(subscription_info={"endpoint":sub["endpoint"],"keys":{"p256dh":sub["p256dh"],"auth":sub["auth"]}},data=json.dumps(payload,ensure_ascii=False),vapid_private_key=private,vapid_claims={"sub":str(os.getenv("VAPID_SUBJECT") or "https://bot-apuestas-crgf.onrender.com")},ttl=120)
            sent+=1; conn.execute("UPDATE founder_push_subscriptions SET last_success_at=?,last_error_at='',updated_at=? WHERE endpoint_hash=?",(utc_now(),utc_now(),sub["endpoint_hash"]))
        except Exception as exc:
            failed+=1; code=getattr(getattr(exc,"response",None),"status_code",None); enabled=0 if code in {404,410} else 1
            conn.execute("UPDATE founder_push_subscriptions SET enabled=?,last_error_at=?,updated_at=? WHERE endpoint_hash=?",(enabled,utc_now(),utc_now(),sub["endpoint_hash"]))
    conn.commit(); conn.close(); return {"ok":bool(sent),"status":"SENT" if sent else "NO_DELIVERY","sent":sent,"failed":failed}

def test_founder_push(db_path):
    return _send_push(db_path,{"title":"NeMeSiS Founder","body":"Prueba de notificación del Founder OS.","url":"/admin/founder-os#inbox","severity":"INFO","tag":"founder-test"})

def dispatch_pending_founder_push(db_path,limit=5):
    obligations=obligations_snapshot(db_path); providers=providers_snapshot(db_path,obligations); sports_freshness=sports_data_freshness_snapshot(db_path); sync_generated_alerts(db_path,obligations,providers,sports_freshness); cfg=push_configuration()
    if not cfg["configured"]: return {"ok":True,"status":"NOT_CONFIGURED","sent":0,"alerts_checked":0}
    conn=_connect(db_path); rows=_rows(conn,"""SELECT * FROM founder_alerts WHERE status='OPEN' AND push_eligible=1 ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 ELSE 3 END,last_seen_at DESC LIMIT ?""",(max(1,min(int(limit),20)),)); conn.close()
    repeat=max(15,min(int(os.getenv("FOUNDER_PUSH_REPEAT_MINUTES","60") or 60),1440)); now=datetime.now(timezone.utc); sent=failed=checked=0
    for a in rows:
        checked+=1; should=not a.get("last_notified_at")
        if not should and a.get("severity")=="CRITICAL":
            try: should=(now-datetime.fromisoformat(str(a["last_notified_at"]).replace("Z","+00:00")).astimezone(timezone.utc))>=timedelta(minutes=repeat)
            except Exception: should=True
        if not should: continue
        result=_send_push(db_path,{"title":_safe(a.get("title"),180) or "NeMeSiS Founder","body":_safe(a.get("message"),500),"url":"/admin/founder-os#inbox","severity":_safe(a.get("severity"),20),"tag":_safe(a.get("fingerprint"),120)})
        sent+=int(result.get("sent") or 0); failed+=int(result.get("failed") or 0)
        if result.get("sent"):
            c=_connect(db_path); c.execute("UPDATE founder_alerts SET last_notified_at=? WHERE id=?",(utc_now(),a["id"])); c.commit(); c.close()
    return {"ok":True,"status":"SENT" if sent else "NO_DUE_DELIVERY","sent":sent,"failed":failed,"alerts_checked":checked}

def founder_os_snapshot(db_path):
    obligations=obligations_snapshot(db_path); providers=providers_snapshot(db_path,obligations); sports_freshness=sports_data_freshness_snapshot(db_path); sync_generated_alerts(db_path,obligations,providers,sports_freshness); alerts=alerts_snapshot(db_path); push=push_snapshot(db_path)
    health="CRITICAL" if alerts["counts"].get("CRITICAL") else "ATTENTION" if alerts["counts"].get("HIGH") or alerts["counts"].get("WARNING") else "HEALTHY"
    return {"contract":"NEMESIS-FOUNDER-OS-V1","generated_at":utc_now(),"health_state":health,"alerts":alerts,"obligations":obligations,"providers":providers,"sports_data_freshness":sports_freshness,"push":push,
            "safety":{"secrets_visible":False,"charges_executed":False,"memberships_modified":False,"dangerous_actions_one_tap":False}}

def founder_alert_tick(db_path):
    try: return dispatch_pending_founder_push(db_path)
    except Exception as exc: return {"ok":False,"status":"CONTROLLED_ERROR","safe_error":type(exc).__name__,"sent":0}
