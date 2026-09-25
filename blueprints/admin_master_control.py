"""V941 adapters over the existing Admin, sports truth, SHARK and Sentinel."""
from contextlib import closing
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import json
import os
import re
import sqlite3
from flask import Blueprint, abort, g, jsonify, make_response, redirect, render_template, request, session
from engines.admin_control_engine import AdminControlStore, Rejected, SECRET_PATTERN
from engines.shark_ai_product_assistant_engine import admin_intent, admin_deterministic_answer, admin_openai_answer

PAGES = {"home":"Inicio", "matches":"Partidos", "live":"Directo", "picks":"Pronósticos",
         "shark":"SHARK", "telegram":"Telegram", "profile":"Perfil", "memberships":"Membresías"}
SAFE_ROUTES = {"/":"home", "/app":"home", "/sports-hub":"home", "/calendar":"matches",
               "/partidos":"matches", "/live":"live", "/picks":"picks", "/shark":"shark",
               "/shark-core":"shark", "/telegram":"telegram", "/profile":"profile", "/plans":"memberships",
               "/membership":"memberships"}
ROUTE_FILES = {"/live":"templates/live.html", "/picks":"templates/picks.html", "/":"templates/home.html"}

def control_store(a):
    return AdminControlStore(a.DB_PATH, a.APP_VERSION)

def _settings_snapshot(a):
    try:
        return {key: value["value"] for key, value in control_store(a).settings().items()}, True
    except (Rejected, sqlite3.Error, OSError, ValueError, TypeError):
        return {"highlights_enabled": False, "banner_enabled": False, "banner_text": ""}, False


def settings_values(a):
    return _settings_snapshot(a)[0]


def _safe_stamp(value):
    if type(value) is not str or len(value) > 48:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.isoformat() if parsed.tzinfo else None
    except ValueError:
        return None


def _operational_state(a, key):
    with closing(sqlite3.connect(Path(a.DB_PATH).resolve().as_uri()+"?mode=ro", uri=True, timeout=.5)) as conn:
        row = conn.execute("SELECT value_json FROM automation_state WHERE key=?", (key,)).fetchone()
        value = json.loads(row[0]) if row else None
        return value if type(value) is dict else {}


def _count(conn, query):
    try:
        return conn.execute(query).fetchone()[0]
    except sqlite3.Error:
        return None

def _safe_call(callback, fallback):
    try:
        return callback()
    except Exception:
        return fallback

def master_snapshot(a):
    """Bounded local evidence. No health probe, provider call, migration or task write."""
    counts = {}
    db_ok = False
    try:
        with closing(sqlite3.connect(Path(a.DB_PATH).resolve().as_uri()+"?mode=ro", uri=True, timeout=.2)) as conn:
            conn.execute("PRAGMA query_only=ON")
            db_ok = conn.execute("SELECT 1").fetchone()[0] == 1
            for key, query in {
                "users":"SELECT COUNT(*) FROM users",
                "pro":"SELECT COUNT(*) FROM users WHERE upper(coalesce(membership,role,'FREE'))='PRO'",
                "elite":"SELECT COUNT(*) FROM users WHERE upper(coalesce(membership,role,'FREE'))='ELITE'",
                "matches":"SELECT COUNT(*) FROM matches",
                "picks":"SELECT COUNT(*) FROM picks WHERE lower(coalesce(status,''))='published'",
                "pending":"SELECT COUNT(*) FROM telegram_queue WHERE lower(status) IN ('pending','queued')",
                "failed":"SELECT COUNT(*) FROM telegram_queue WHERE lower(status)='failed'",
                "sent":"SELECT COUNT(*) FROM telegram_queue WHERE lower(status)='sent'",
            }.items():
                counts[key] = _count(conn, query)
    except sqlite3.Error:
        pass
    sports = _safe_call(a.get_public_home_sports_summary, {})
    provider = _safe_call(a.v945_provider_health_snapshot, {})
    telegram = _safe_call(a.v928_telegram_overview_fast, {})
    automation = _safe_call(a.v928_automation_overview_fast, {})
    from engines.sentinel_issues_engine import load_sentinel_issues_memory, sentinel_issues_memory_path
    from engines.reliability_engine import reliability_snapshot, LEARNING
    memory = {"issues":[]}
    memory_available = False
    sentinel = {"available":False,"open":None,"last_scan":None}
    try:
        if sentinel_issues_memory_path(a.BASE_DIR).is_file():
            memory = load_sentinel_issues_memory(a.BASE_DIR)
            memory_available = memory.get("_storage_revision") != "unreadable"
            known = memory.get("issues")
            if type(known) is list and _safe_stamp(memory.get("last_scan_madrid")):
                sentinel = {"available":True,"open":sum(1 for item in known if type(item) is dict and item.get("status") in ("OPEN_REAL", "VERIFICATION_FAILED")),
                            "last_scan":_safe_stamp(memory.get("last_scan_madrid"))}
    except (OSError,ValueError,TypeError):
        pass
    jobs = automation.get("jobs") if type(automation.get("jobs")) is list else []
    job_failures = sum(1 for job in jobs if type(job) is dict and job.get("last_result") in ("ERROR","FAILED","FAILURE"))
    today = sports.get("valid_matches_today_count")
    today = today if type(today) is int and 0 <= today <= 10**9 else None
    live = len(sports["valid_live_events"]) if isinstance(sports.get("valid_live_events"), list) else None
    if not db_ok or sports.get("storage_status") != "ok":
        today = live = None
    facts = [{"label":label,"value":value} for label,value in (
        ("Usuarios",counts.get("users")),("PRO",counts.get("pro")),("ELITE",counts.get("elite")),
        ("Partidos guardados",counts.get("matches")),("Partidos hoy",today),("Directos confirmados",live),
        ("Pronósticos publicados",counts.get("picks")),("Telegram pendiente",counts.get("pending")),
        ("Telegram fallidos",counts.get("failed")),("Telegram enviados",counts.get("sent")))]
    areas = [
        {"key":"app","label":"Aplicación","state":"OK","detail":"Esta petición se ha atendido.","href":"/api/health"},
        {"key":"db","label":"Base de datos","state":"OK" if db_ok else "SIN DATOS","detail":"Lectura local disponible." if db_ok else "No se pudo verificar la lectura.","href":"/admin/data-vault"},
        {"key":"sports","label":"Datos deportivos","state":"OK" if today else "ATENCIÓN" if today == 0 else "SIN DATOS","detail": "Recuento de Sports Truth; no prueba cobertura completa.","href":"/admin/data-center"},
        {"key":"picks","label":"Pronósticos","state":"OK" if counts.get("picks") else "SIN DATOS","detail":"Solo publicaciones persistidas; no mide rentabilidad.","href":"/admin/picks"},
        {"key":"telegram","label":"Telegram","state":"ATENCIÓN" if counts.get("failed") else "SIN DATOS","detail":"Cola local; configuración y entregas no certifican disponibilidad actual.","href":"/admin/telegram/command-center"},
        {"key":"jobs","label":"Automatizaciones","state":"ATENCIÓN" if job_failures else "SIN DATOS","detail":"Ejecuciones persistidas; próxima ejecución no confirmada.","href":"/admin/daily-automation"},
        {"key":"shark","label":"SHARK","state":"OK","detail":"Diagnóstico local disponible; IA externa bajo demanda.","href":"/admin/shark-ai"},
        {"key":"sentinel","label":"Sentinel","state":"ATENCIÓN" if sentinel["open"] else "OK" if sentinel["available"] else "SIN DATOS","detail":("Incidencias abiertas guardadas: "+str(sentinel["open"])+". Lectura local; no certifica producción.") if sentinel["available"] else "No hay memoria de incidencias disponible.","href":"/admin/sentinel-issues"},
        {"key":"payments","label":"Pagos","state":"SIN DATOS","detail":"Configurado no equivale a cobros o webhook verificados.","href":"/admin/payments"},
        {"key":"release","label":"Release","state":"SIN DATOS","detail":"Estado GitHub no disponible desde este runtime.","href":"/admin/release-office"},
    ]
    providers = []
    provider_names = {"api_football":"API-Football / API-Sports", "sportsdb":"TheSportsDB", "the_odds":"The Odds API"}
    status_names = {"NO_CONFIGURADA":"No configurada", "REVISAR_PLAN_ACCESO":"Revisar acceso/plan",
                    "OPERATIVA":"Última respuesta operativa", "CACHE":"Usando caché",
                    "SIN_VERIFICACION_RECIENTE":"Sin verificación reciente", "OPERATIVA_FALLBACK":"Fallback operativo"}
    for p in (provider.get("providers") if type(provider.get("providers")) is list else [])[:3]:
        if type(p) is not dict or type(p.get("key")) is not str or p["key"] not in provider_names:
            continue
        key = p["key"]
        status = p.get("status") if type(p.get("status")) is str and p["status"] in status_names else "SIN_VERIFICACION_RECIENTE"
        processed = p.get("processed") if type(p.get("processed")) is int and 0 <= p["processed"] <= 10**9 else None
        providers.append({"key":key,"label":provider_names[key],"configured":p.get("configured") if type(p.get("configured")) is bool else None,
                          "status":status,"status_label":status_names[status],"observed_at":_safe_stamp(p.get("observed_at")),"processed":processed})
        areas.append({"key":key,"label":provider_names[key],"state":"ATENCIÓN" if status in ("NO_CONFIGURADA","REVISAR_PLAN_ACCESO") else "SIN DATOS",
                      "detail":"Última evidencia persistida; abrir APIs para fecha, caché y cuota.","href":"/admin/data-center"})
    values, settings_readable = _settings_snapshot(a)
    if not settings_readable:
        areas.append({"key":"settings","label":"Configuración","state":"SIN DATOS",
                      "detail":"Lectura no válida; banner y highlights desactivados por seguridad hasta recuperar el ajuste.","href":"/admin/dashboard"})
    recommendations = [{"title":x["label"],"evidence":x["detail"],"href":x["href"]} for x in areas if x["state"] == "ATENCIÓN"][:6]
    audit = _safe_call(lambda:control_store(a).list_audit(20), [])
    for event in audit:
        event["reversible"] = event.get("action_id") in ("settings.update","settings.rollback") and event.get("verification") == "VERIFIED"
        stamp = event.get("timestamp")
        event["timestamp"] = datetime.fromtimestamp(stamp, timezone.utc).isoformat() if type(stamp) in (int,float) and 0 <= stamp <= 253402300799 else None
    render_sha = os.getenv("RENDER_GIT_COMMIT","")
    runtime = {"app_version":a.APP_VERSION,
               "version_file":_safe_call(lambda:(a.BASE_DIR/"VERSION.txt").read_text().strip(),"Desconocida"),
               "commit":render_sha if re.fullmatch("[a-fA-F0-9]{40}",render_sha) else "Desconocido",
               "github":"Estado GitHub no disponible desde este runtime.",
               "db":"Lectura disponible" if db_ok else "Sin verificación", "app_path":"app.py",
               "deployment":"Sin certificación de despliegue"}
    # Read the existing Company Sentinel artifact. Missing/stale observations
    # remain unknown; never probe GitHub/Render while opening the dashboard.
    persisted_identity = {}
    try:
        identity_path = Path(a.BASE_DIR)/"data/runtime/autonomous_company_sentinel/render_alignment.json"
        if identity_path.is_file() and identity_path.stat().st_size <= 65536:
            saved = json.loads(identity_path.read_text(encoding="utf-8"))
            persisted_identity = saved.get("identity", {}) if isinstance(saved, dict) else {}
    except (OSError, ValueError):
        pass
    if not isinstance(persisted_identity, dict):
        persisted_identity = {}
    identity = {k:persisted_identity.get(k) for k in ("main_sha", "candidate_sha", "deployed_sha", "render_sha", "production_observed_at", "deployed_version")}
    identity.update(runtime_version=a.APP_VERSION,
        app_version=_safe_call(lambda:(a.BASE_DIR/"APP_VERSION").read_text().strip(), None),
        version_file=runtime["version_file"])
    # A Render environment SHA describes this process, not a remote API lookup.
    runtime["render_reported_sha"] = runtime["commit"]
    identity["runtime_sha"] = render_sha if re.fullmatch("[a-fA-F0-9]{40}", render_sha) else None
    missing_tests = [r["test"] for r in LEARNING if not (a.BASE_DIR/r["test"]).is_file()]
    from engines.navigation_integrity_engine import _NavigationHTMLParser
    unbound = []
    for name in ("admin_dashboard.html", "admin_users.html", "admin_picks.html"):
        try:
            parser = _NavigationHTMLParser("templates/"+name)
            parser.feed((a.BASE_DIR/"templates"/name).read_text(encoding="utf-8"))
            unbound.extend(name+":"+str(e.get("line")) for e in parser.entries if e["kind"]=="button" and not e.get("has_identifier"))
        except (OSError, ValueError):
            unbound.append(name+": lectura no disponible")
    reliability = reliability_snapshot(memory, {"identity":identity, "memory_available":memory_available,
        "jobs":jobs, "providers":providers, "sync_at":provider.get("job_finished_at"),
        "queue_samples":memory.get("reliability_queue_samples", []), "missing_tests":missing_tests, "unbound_buttons":unbound})
    configured = a.env_present("OPENAI_API_KEY") and a.env_present("OPENAI_MODEL")
    return {"version":a.APP_VERSION,"generated_at":a.now_iso(),"areas":areas,"facts":facts,"providers":providers,
            "recommendations":recommendations,"runtime":runtime,"settings":values,"settings_readable":settings_readable,"sentinel":sentinel,"reliability":reliability,
            "audit":audit,"actions":[x for x in control_store(a).registry() if x["action_id"] != "telegram.retry_failed"],
            "ai":{"configured":configured,"privacy":"Solo tema y datos agregados; el mensaje original no se transmite al proveedor.","state":"IA avanzada disponible bajo demanda; conexión no verificada." if configured else "IA avanzada no configurada. Diagnóstico del sistema disponible."},
            "external_calls":0,"source":"LOCAL_PERSISTED_EVIDENCE",
            "telegram":{"last_sent_at":_safe_stamp(telegram.get("last_sent_at"))},
            "job_last_cycle":_safe_stamp(provider.get("job_finished_at"))}

def _proposal_view(p):
    out = dict(p)
    out.update({k:v for k,v in (p.get("action") or {}).items() if k in ("label","risk_level","description","confirmation_phrase")})
    out["proposal_id"] = p.get("id") or p.get("proposal_id")
    preview = p.get("preview") or {}
    for key in ("before","after","impact"):
        out[key] = preview.get(key, p.get(key))
    return out


def _preview_links(html, plan, viewport="390"):
    """Preserve rendering but constrain every anchor to the simulated context."""
    from html import escape
    from html.parser import HTMLParser
    from urllib.parse import urlsplit, parse_qs, urlencode
    viewport = viewport if viewport in ("390","768","1440") else "390"
    class PreviewParser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.parts=[]
        def handle_starttag(self,tag,attrs):
            if tag in ("button", "input", "select", "textarea"):
                safe = [(k,v) for k,v in attrs if k not in ("disabled", "formaction") and not k.startswith("on")]
                safe.append(("disabled", None))
                self.parts.append("<"+tag+"".join(" "+k+("=\""+escape(v,quote=True)+"\"" if v is not None else "") for k,v in safe)+">")
                return
            if tag != "a":
                self.parts.append(self.get_starttag_text());return
            data=dict(attrs); parsed=urlsplit(data.get("href") or "")
            page=None
            if not parsed.scheme and not parsed.netloc:
                if parsed.path in ("/admin/client-preview","/admin/client-preview/frame"):
                    candidate=parse_qs(parsed.query).get("page",["home"])[0]
                    page=candidate if candidate in PAGES else None
                else:
                    page=SAFE_ROUTES.get(parsed.path)
            safe=[(k,v) for k,v in attrs if k not in ("href","target","download","ping") and not k.startswith("on")]
            if page:
                preferred = parse_qs(parsed.query).get("viewport",[viewport])[0]
                width = preferred if preferred in ("390","768","1440") else viewport
                safe.append(("href","/admin/client-preview?"+urlencode({"page":page,"plan":plan,"viewport":width})))
            else:
                safe.extend((("aria-disabled","true"),("tabindex","-1")))
            self.parts.append("<a"+"".join(" "+k+("=\""+escape(v,quote=True)+"\"" if v is not None else "") for k,v in safe)+">")
        def handle_startendtag(self,tag,attrs): self.handle_starttag(tag,attrs)
        def handle_endtag(self,tag): self.parts.append("</"+tag+">")
        def handle_data(self,data): self.parts.append(data)
        def handle_entityref(self,name): self.parts.append("&"+name+";")
        def handle_charref(self,name): self.parts.append("&#"+name+";")
        def handle_comment(self,data): self.parts.append("<!--"+data+"-->")
        def handle_decl(self,decl): self.parts.append("<!"+decl+">")
    parser=PreviewParser()
    parser.feed(html);parser.close()
    return "".join(parser.parts)


def register_admin_master(a):
    bp = Blueprint("admin_master", __name__)
    def protected(fn):
        @wraps(fn)
        def guard(*args, **kwargs):
            if not a.is_admin_session():
                return a.admin_json_forbidden() if request.path.startswith("/api/") else redirect("/admin-login?next=/admin/dashboard")
            if request.method != "GET" and not a.validate_csrf(session, a.request_csrf_token()):
                return jsonify(ok=False,message="La confirmación ha caducado. Recarga la página."),403
            try:
                return fn(*args, **kwargs)
            except Rejected as exc:
                return jsonify(ok=False,message="La propuesta no es válida o ya no coincide con el estado actual.",error=exc.code),exc.status
            except (sqlite3.Error, OSError):
                return jsonify(ok=False,message="No se pudo acceder al control operativo. No se ha confirmado el cambio."),503
        return guard
    def owner():
        # Opaque authenticated identity; no cookie/session ID stored in audit.
        ident = session.get("user_id")
        if type(ident) is not str or not ident:
            raise Rejected("authenticated_admin_identity_required",403)
        return ident
    def body(required, optional=()):
        if request.content_length and request.content_length > 8192:
            raise Rejected("payload_too_large",413)
        value = request.get_json(silent=True)
        if type(value) is not dict or not set(required) <= set(value) or set(value) - set(required) - set(optional):
            raise Rejected("invalid_json")
        return value
    def propose(action_id,parameters,origin="manual",request_key=None):
        store=control_store(a); store.initialize()
        return _proposal_view(store.propose(owner(),action_id,parameters,origin=origin,request_key=request_key))
    def create_improvement(params):
        from engines.sentinel_issues_engine import load_sentinel_issues_memory, normalize_sentinel_issue, upsert_sentinel_issues, save_sentinel_issues_memory, generate_issue_prompt, copy_issue_text
        from engines.sentinel_improvement_workflow_engine import build_workflow_from_sentinel_result
        root = a.LOCAL_SAFE_DATA_DIR if a.local_safe_mode_enabled() else a.BASE_DIR
        memory=load_sentinel_issues_memory(root)
        candidate=normalize_sentinel_issue({"title":params["title"],"evidence":params["detail"],"route":params["route"],
            "file":ROUTE_FILES.get(params["route"],"Por determinar"),"status":"INSUFFICIENT_EVIDENCE",
            "recommendation":"Reproducir la solicitud, definir criterios de aceptación y validar permisos, datos reales y experiencia móvil/PC.",
            "validation":["pytest tests/test_admin_master_http.py","python tools/check_admin_master_control.py"],
            "source":"shark_admin"},source="shark_admin")
        candidate["codex_prompt"] = generate_issue_prompt(candidate)
        candidate["copy_text"] = copy_issue_text(candidate)
        memory["issues"]=upsert_sentinel_issues(memory.get("issues",[]),[candidate])
        save_sentinel_issues_memory(memory,root)
        workflow=build_workflow_from_sentinel_result({"issues":[candidate]},a.APP_VERSION)
        saved=load_sentinel_issues_memory(root)
        # Generated from the approved, validated parameters; never a model tool call.
        codex_prompt = generate_issue_prompt(candidate)
        if not SECRET_PATTERN.search(codex_prompt):
            g.admin_master_codex_prompt = codex_prompt
        return {"ok":any(i.get("id")==candidate["id"] for i in saved["issues"]), "status":"PENDING_REVIEW",
                "issue_id":candidate["id"],"task_id":workflow["improvement_tasks"][0]["task_id"] if workflow["improvement_tasks"] else "",
                "codex_prompt":generate_issue_prompt(candidate)}
    def scan_sentinel(params):
        result = a._v892_sentinel_issues_summary(save_memory=True,mode="quick",include_autopilot=False,include_visual=False)
        if type(result) is not dict or type(result.get("issues")) is not list:
            return {"ok":False,"status":"ERROR"}
        # Explicit scan, never a GET: retain real observations for early warning.
        from engines.sentinel_issues_engine import load_sentinel_issues_memory, save_sentinel_issues_memory
        memory = load_sentinel_issues_memory(a.BASE_DIR)
        failed = next((f["value"] for f in master_snapshot(a)["facts"] if f["label"]=="Telegram fallidos"), None)
        if type(failed) is int:
            memory["reliability_queue_samples"] = (memory.get("reliability_queue_samples", []) + [{"at":datetime.now(timezone.utc).isoformat(), "failed":failed}])[-20:]
            save_sentinel_issues_memory(memory, a.BASE_DIR)
        return {**result,"ok":True,"status":"COMPLETED"}
    def record_verification(params):
        from engines.sentinel_issues_engine import record_issue_verification
        return record_issue_verification(params["issue_id"], params, a.BASE_DIR)
    def resolve_issue(params):
        from engines.sentinel_issues_engine import update_issue_status
        return update_issue_status(params["issue_id"], "RESOLVED", a.BASE_DIR, note="Admin Master Control: cierre con verificacion vigente")
    def verify_issue_record(params, result):
        from engines.sentinel_issues_engine import load_sentinel_issues_memory
        saved = load_sentinel_issues_memory(a.BASE_DIR)
        expected = "VERIFIED" if params.get("result")=="PASS" else "VERIFICATION_FAILED" if params.get("result")=="FAIL" else "RESOLVED"
        return result.get("ok") is True and any(i.get("id")==params["issue_id"] and i.get("status")==expected for i in saved["issues"])
    def verify_sports(params,result):
        if type(result) is not dict or result.get("ok") is not True or not result.get("finished_at"):
            return False
        # Independent connection bypasses any stale request-time read snapshot.
        saved = _operational_state(a,"sports_sync_operational_state")
        return saved.get("finished_at") == result["finished_at"] and saved.get("ok") is True and saved.get("status") == result.get("status")
    def verify_sentinel(params,result):
        from engines.sentinel_issues_engine import load_sentinel_issues_memory
        if type(result) is not dict or result.get("ok") is not True or not result.get("last_scan_madrid"):
            return False
        saved = load_sentinel_issues_memory(a.BASE_DIR)
        return saved.get("last_scan_madrid") == result["last_scan_madrid"] and type(saved.get("issues")) is list
    def verify_improvement(params,result):
        from engines.sentinel_issues_engine import load_sentinel_issues_memory
        if type(result) is not dict or result.get("ok") is not True or not result.get("issue_id"):
            return False
        root = a.LOCAL_SAFE_DATA_DIR if a.local_safe_mode_enabled() else a.BASE_DIR
        saved = load_sentinel_issues_memory(root)
        return any(item.get("id") == result["issue_id"] for item in saved.get("issues",[]) if type(item) is dict)
    def handlers():
        return {
            "sentinel.record_verification":record_verification,
            "sentinel.resolve":resolve_issue,
            "sports.sync":lambda p:a.run_sports_sync_cycle(force=False,trigger_type="manual_admin"),
            "telegram.dry_run":lambda p:a.telegram_reliability_dry_run(),
            "sentinel.scan":scan_sentinel,
            "sentinel.create_improvement":create_improvement,
            # A retry path is intentionally not bound to process-all: it could send unrelated queue entries.
        }
    @bp.get("/api/admin/master-control")
    @protected
    def snapshot():
        return jsonify(ok=True,**master_snapshot(a))
    @bp.post("/api/admin/master-control/proposals")
    @protected
    def proposal():
        payload=body(("action_id","parameters"),("request_key",))
        if payload.get("action_id")=="telegram.retry_failed":
            raise Rejected("retry_requires_existing_telegram_command_center",409)
        return jsonify(ok=True,proposal=propose(payload.get("action_id"),payload.get("parameters"),request_key=payload.get("request_key")))
    @bp.post("/api/admin/master-control/execute")
    @protected
    def execute():
        payload=body(("proposal_id","confirmation"))
        callbacks=handlers()
        verifiers={
            "sentinel.record_verification":verify_issue_record,
            "sentinel.resolve":verify_issue_record,
            "sports.sync":verify_sports,
            "telegram.dry_run":lambda p,r:type(r) is dict and r.get("sent") is False and r.get("trigger_type")=="dry_run" and type(r.get("message_preview")) is str,
            "sentinel.scan":verify_sentinel,
            "sentinel.create_improvement":verify_improvement,
        }
        result=control_store(a).confirm(owner(),payload.get("proposal_id"),handlers=callbacks,verifiers=verifiers,confirmation=payload.get("confirmation"))
        if result.get("ok") and result.get("verification") == "VERIFIED" and getattr(g,"admin_master_codex_prompt",None):
            result["result"]["codex_prompt"] = g.admin_master_codex_prompt
        return jsonify(ok=True,result=result)
    @bp.post("/api/admin/master-control/rollback")
    @protected
    def rollback():
        ident = body(("audit_id",))["audit_id"]
        if type(ident) is str and re.fullmatch(r"[1-9][0-9]{0,12}", ident):
            ident = int(ident)
        return jsonify(ok=True,proposal=propose("settings.rollback",{"audit_id":ident}))

    @bp.post("/api/admin/master-control/cancel")
    @protected
    def cancel():
        payload = body(("proposal_id",))
        return jsonify(ok=True,result=control_store(a).cancel(owner(),payload["proposal_id"]))
    @bp.post("/api/admin/master-control/chat")
    @protected
    def chat():
        payload=body(("message",))
        message=payload.get("message")
        if type(message) is not str or not 1<=len(message.strip())<=1200 or SECRET_PATTERN.search(message):
            raise Rejected("invalid_or_sensitive_prompt")
        # Reuse persistent security rate limiting, no process-only quota.
        address=owner()
        rate=a.rate_limit_status(a.DB_PATH,event_type="admin_ai_request",ip_address=address,path_like="/api/admin/master-control/chat",limit=12,minutes=1)
        if rate.get("blocked"):
            return jsonify(ok=False,message="Espera un minuto antes de continuar."),429
        a.record_security_event(a.DB_PATH,event_type="admin_ai_request",ip_address=address,path=request.path,success=False,method="POST",user_id=address,reason="admin_ai_request_count")
        intent=admin_intent(message)
        if intent.get("action_id"):
            if intent["action_id"]=="telegram.retry_failed":
                return jsonify(ok=True,kind="RECOMMENDATION",message="El reintento real se gestiona en el Command Center Telegram, con sus filtros y confirmación. No se ha enviado nada.",recommendations=[{"title":"Telegram","href":"/admin/telegram/command-center","evidence":"Revisar fallidos y entregas inciertas antes de enviar."}])
            return jsonify(ok=True,kind="PROPOSAL",message="Revisa el cambio exacto y confirma para aplicarlo.",proposal=propose(intent["action_id"],intent["parameters"],"SHARK proposal"))
        if intent.get("kind") == "CLARIFICATION":
            store = control_store(a)
            pending = _safe_call(lambda:store.list_proposals(owner()), [])
            pending = next((p for p in pending if p["state"] == "PENDING" and p["expires"] > store.clock() and p["app_version"] == a.APP_VERSION), None)
            if pending:
                return jsonify(ok=True,kind="PROPOSAL",message="Esta es tu propuesta pendiente. Revisa los cambios antes de aprobar; no se ha ejecutado nada.",proposal=_proposal_view(pending),reused=True)
            return jsonify(ok=True,**intent)
        if intent.get("kind") == "BLOCKED":
            return jsonify(ok=True,**intent)
        state=master_snapshot(a)
        answer=admin_deterministic_answer(message,state)
        if state["ai"]["configured"] and not a.local_safe_mode_enabled() and not answer.get("local_only"):
            advanced=admin_openai_answer(message,state,api_key=os.getenv("OPENAI_API_KEY",""),model=os.getenv("OPENAI_MODEL",""))
            if advanced:
                answer.update(message="RECOMENDACIÓN IA (contrastar con las evidencias): "+advanced,source="OPENAI")
            else:
                answer["message"]="SHARK AI no disponible temporalmente. "+answer["message"]
        else:
            answer["message"]=state["ai"]["state"]+" "+answer["message"]
        # Session stores only last intent category, never prompts or third-party data.
        session["admin_ai_last_kind"]=answer["kind"]
        return jsonify(ok=True,**answer)
    @bp.get("/admin/client-preview")
    @bp.get("/admin/client-preview/frame")
    @protected
    def preview():
        page=request.args.get("page","home"); plan=request.args.get("plan","FREE")
        if page not in PAGES or plan not in ("FREE","PRO","ELITE"):
            abort(400)
        g.admin_preview_user={"id":"","role":plan,"membership":plan,"name":"Vista simulada"}
        summary=_safe_call(a.get_public_home_sports_summary,{})
        matches=summary.get("valid_live_events",[]) if page=="live" else summary.get("valid_matches_today",[]) if page=="home" else summary.get("valid_upcoming_matches",[])
        picks=[]
        rank={"FREE":0,"PRO":1,"ELITE":2}
        for item in summary.get("valid_active_picks",[])[:12]:
            required=str(item.get("membership_required") or item.get("required_plan") or item.get("membership") or "PRO").upper()
            if rank[plan] >= rank.get(required,3):
                picks.append(item)
        preview_settings = settings_values(a)
        matches = [dict(item) for item in matches if type(item) is dict]
        if preview_settings.get("highlights_enabled") is not True:
            for item in matches:
                item["has_highlights"] = False
                item["highlight_url"] = ""
                item["highlights_url"] = ""
        from engines.membership_engine import membership_context, get_membership_limits
        html=render_template("admin_client_preview.html",page=page,preview_title=PAGES[page],plan=plan,
                             matches=matches[:12],picks=picks,pages=PAGES,current_user=g.admin_preview_user,
                             settings=preview_settings,preview_membership=membership_context({"membership":plan}),
                             preview_plan_limits={tier:get_membership_limits(tier) for tier in ("FREE","PRO","ELITE")})
        html = _preview_links(html, plan, request.args.get("viewport","390"))
        response=make_response(html)
        response.headers["Cache-Control"]="private, no-store"
        response.headers["Content-Security-Policy"]="default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; script-src 'none'; connect-src 'none'; form-action 'none'; frame-ancestors 'self'; sandbox allow-same-origin"
        return response
    @bp.after_request
    def private(response):
        response.headers["Cache-Control"]="private, no-store"
        response.headers["X-Content-Type-Options"]="nosniff"
        return response
    a.app.register_blueprint(bp)
