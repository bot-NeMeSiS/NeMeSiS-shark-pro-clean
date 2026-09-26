"""Deterministic projections over Sentinel evidence; no network, tasks or writes."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from engines.admin_control_engine import SECRET_PATTERN


def safe_text(value, limit=500):
    if not isinstance(value, str):
        return ""
    if SECRET_PATTERN.search(value) or "Traceback (" in value:
        return "[redacted]"
    return " ".join(value.split())[:limit]


def scrub(value, depth=0):
    if depth > 6:
        return None
    if isinstance(value, str):
        return safe_text(value, 4000)
    if isinstance(value, dict):
        return {safe_text(str(k), 80): scrub(v, depth+1) for k,v in list(value.items())[:80]
                if not re.search(r"password|secret|token|authorization|cookie|api.?key|traceback", str(k), re.I)}
    if isinstance(value, list):
        return [scrub(v, depth+1) for v in value[:100]]
    return value if value is None or type(value) in (int, float, bool) else None


def stamp(value):
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def sha(value):
    return value.lower() if isinstance(value, str) and re.fullmatch(r"[a-fA-F0-9]{40}", value) else None


def fingerprint(issue):
    # Namespace a stable rule by its surface and provider/job. Never trust a
    # supplied digest, truncate evidence into identity, or merge by a keyword.
    keys = ("area", "route", "file", "component", "provider", "job", "exception_type", "error_code")
    identity = [safe_text(issue.get(k), 2000) for k in keys]
    stable = safe_text(issue.get("stable_key"), 2000)
    identity += [stable] if stable and stable != "[redacted]" else [safe_text(issue.get("title"), 2000), safe_text(issue.get("evidence"), 4000)]
    return sha256(json.dumps(identity, ensure_ascii=True).encode()).hexdigest()


def verification_valid(issue, now=None):
    proof = issue.get("verification_record")
    if not isinstance(proof, dict) or proof.get("result") != "PASS":
        return False
    checked, last = stamp(proof.get("checked_at")), stamp(issue.get("last_seen"))
    now = now or datetime.now(timezone.utc)
    return bool(checked and last and last <= checked <= now and
                sha(issue.get("fix_sha")) and sha(proof.get("sha")) == sha(issue.get("fix_sha")) and
                proof.get("seen_count") == issue.get("seen_count") and
                proof.get("fingerprint") == fingerprint(issue) and
                all(safe_text(issue.get(k)) not in ("", "[redacted]") for k in
                    ("root_cause", "corrective_action", "regression_test", "prevention", "detection")) and
                safe_text(proof.get("evidence_ref")) not in ("", "[redacted]") and
                proof.get("scope") in ("LOCAL_QA", "CI", "PRODUCTION"))


LEARNING = [
    {"rule": "CACHE_REUSED != CURRENT_PROVIDER_OPERATIONAL", "origin": "PR91", "test": "tests/test_provider_health_evidence.py", "detail": "Una cache o ciclo historico no confirma disponibilidad actual."},
    {"rule": "UNKNOWN_ODDS != ZERO_ODDS", "origin": "Contrato deportivo", "test": "tests/test_telegram_visual_premium.py", "detail": "Cuota ausente conserva estado desconocido, no valor cero."},
    {"rule": "HEALTH_200 != DEPLOYMENT_CERTIFIED", "origin": "Contrato de produccion", "test": "tests/test_reliability.py", "detail": "Una respuesta HTTP no certifica revision desplegada."},
    {"rule": "VERSION_MATCH != SHA_ALIGNMENT", "origin": "Contrato de produccion", "test": "tests/test_reliability.py", "detail": "Version coincidente con SHA ausente sigue UNKNOWN."},
    {"rule": "FIX_APPLIED != VERIFIED", "origin": "Regresiones PR92", "test": "tests/test_reliability.py", "detail": "Requiere prueba posterior ligada a la revision y recurrencia."},
    {"rule": "INTERNAL_INTERFACE_CHANGE -> DEPENDENTS MUST BE CHECKED", "origin": "Incidente comunicado STATIC_ROOT", "test": "tests/test_telegram_visual_premium.py", "detail": "telegram_visual_card_engine.STATIC_ROOT fue un contrato interno roto. Consumidores y pruebas deben evolucionar juntos; no se inventan fecha ni commit del incidente."},
    {"rule": "check/sprint label != deployed runtime version", "origin": "PR92", "test": "tests/test_admin_master_release.py", "detail": "Runtime, sprint/check y Release Candidate son identidades distintas."},
    {"rule": "PICK_INTERNAL -> PRONÓSTICO_UI_ES", "origin": "V941 terminology contract", "test": "tests/test_pronosticos_terminology.py", "detail": "El backend conserva pick/picks; toda etiqueta española de producto usa Pronóstico/Pronósticos."},
    {"rule": "MATCHES_SECTION_INTERNAL -> CALENDARIO_UI_ES", "origin": "V941 terminology contract", "test": "tests/test_calendar_terminology.py", "detail": "La sección visible se llama Calendario; partido/partidos se conserva al hablar de encuentros concretos."},
    {"rule": "PRODUCT_LANGUAGE -> CLEAR_ES_CLIENT_ADMIN", "origin": "V941 terminology contract", "test": "tests/test_product_language_clarity.py", "detail": "Cliente y Admin priorizan español claro; términos técnicos solo se mantienen cuando aportan contexto y se explican."},
    {"rule": "ONE_RECURRING_OWNER -> NO_DUPLICATE_SCHEDULERS", "origin": "V941 automation cleanup", "test": "tests/test_automation_schedule_minimal.py", "detail": "Render programa solo cron maestro y backup diario; scheduler/daily/highlights/grading/Sentinel separados quedan manuales o incluidos en el maestro."},
    {"rule": "CANONICAL_BROWSER_MATRIX -> CLIENT_ADMIN_PC_MOBILE", "origin": "V941 release QA", "test": "tests/test_canonical_browser_matrix_v941.py", "detail": "Cliente real y Admin canónico se recorren en Chromium PC/móvil; FREE/PRO/ELITE se verifican además con preview aislado."},
]


def related_incidents(query, issues):
    """Structured comparison: exact identity or multiple independent signals."""
    matches = []
    for issue in issues:
        exact_id = query.get("id") and query["id"] == issue.get("id")
        keys = [k for k in ("route", "file", "component", "provider", "job", "exception_type", "error_code")
                if query.get(k) and query.get(k) == issue.get(k)]
        exact_fp = bool(query.get("stable_key") and fingerprint(query) == fingerprint(issue))
        level = "CONFIRMADO" if exact_id or exact_fp else "SIMILAR" if len(keys) >= 3 else "POSIBLE RELACIÓN" if len(keys) >= 2 else None
        if level:
            matches.append({"id": safe_text(issue.get("id")), "relation": level, "indicators": keys,
                            "seen_count": issue.get("seen_count"), "root_cause": safe_text(issue.get("root_cause")) or None})
    ranks = {"CONFIRMADO":0, "SIMILAR":1, "POSIBLE RELACIÓN":2}
    matches.sort(key=lambda item:ranks[item["relation"]])
    return {"state": matches[0]["relation"] if matches else "SIN EVIDENCIA", "matches": matches[:20]}


def production_drift(identity, now=None):
    now = now or datetime.now(timezone.utc)
    fields = {k: sha(identity.get(k)) for k in ("main_sha", "candidate_sha", "deployed_sha", "render_sha", "runtime_sha")}
    versions = {k: safe_text(identity.get(k), 180) or None for k in ("runtime_version", "app_version", "version_file", "deployed_version")}
    versions = {k:v if v and re.fullmatch(r"V[0-9]+[A-Za-z0-9_]*", v) else None for k,v in versions.items()}
    mismatches = []
    observed = stamp(identity.get("production_observed_at"))
    fresh = bool(observed and 0 <= (now-observed).total_seconds() <= 3600)
    # Candidate and main MAY differ. Compare them explicitly, but deployment is
    # expected to follow main; an unpublished candidate is not production drift.
    for a,b in (("main_sha", "deployed_sha"), ("deployed_sha", "render_sha")):
        if fresh and fields[a] and fields[b] and fields[a] != fields[b]:
            mismatches.append(a+" != "+b)
    local = [versions[k] for k in ("runtime_version", "app_version", "version_file") if versions[k]]
    if len(set(local)) > 1:
        mismatches.append("runtime / APP_VERSION / VERSION.txt")
    if fresh and fields["deployed_sha"] and fields["runtime_sha"] == fields["deployed_sha"] and versions["runtime_version"] and versions["deployed_version"] and versions["runtime_version"] != versions["deployed_version"]:
        mismatches.append("same SHA / divergent runtime version")
    # Matching versions never promote a missing SHA to known/aligned.
    known = all(fields[k] for k in ("main_sha", "deployed_sha", "render_sha"))
    state = "ERROR" if identity.get("evidence_error") is True else "MISALIGNED_CONFIRMED" if mismatches else "ALIGNED_CONFIRMED" if known and fresh and len(local)==3 else "UNKNOWN"
    return {"state": state, **fields, **versions, "production_observed_at": observed.isoformat() if observed else None,
            "evidence_fresh": fresh, "mismatches": mismatches,
            "candidate_matches_main": fields["candidate_sha"] == fields["main_sha"] if fields["candidate_sha"] and fields["main_sha"] else None,
            "deployment_certified": False, "note": "Alineacion de evidencia no equivale a certificacion integral de produccion."}


def risk_radar(evidence, now=None):
    now = now or datetime.now(timezone.utc)
    alerts = []
    def add(code, state, fact, reason, impact, href):
        alerts.append({"code": code, "state": state, "evidence": safe_text(fact), "reason": reason, "impact": impact, "action": "Revisar evidencia", "href": href})
    def age_check(code, at, seconds, href, label):
        d = stamp(at)
        if not d or d > now:
            add(code, "DESCONOCIDO", label+": fecha no verificable", "Falta una observacion valida.", "No permite confirmar actividad reciente.", href)
        elif (now-d).total_seconds() > seconds:
            add(code, "ATENCIÓN", label+": "+d.isoformat(), "Supera el umbral de "+str(seconds)+" segundos.", "Datos o automatizacion pueden estar atrasados.", href)
    if evidence.get("memory_available") is not True:
        add("incident_memory", "DESCONOCIDO", "Memoria no disponible o no confirmada.", "No equivale a cero incidentes.", "No se puede comprobar recurrencia historica.", "/admin/sentinel-issues")
    for j in evidence.get("jobs", []):
        if isinstance(j, dict) and j.get("enabled") is True:
            thresholds = {"telegram_tick":1800, "daily_run":7200, "pick_grading":43200, "highlights_sync":86400, "data_backup":172800}
            if j.get("name") in thresholds:
                age_check("job:"+j["name"], j.get("last_run"), thresholds[j["name"]], "/admin/daily-automation", "Ultima ejecucion "+j["name"])
    age_check("sync", evidence.get("sync_at"), 3600, "/admin/data-center", "Sincronizacion deportiva")
    for p in evidence.get("providers", []):
        if isinstance(p, dict) and p.get("configured") is True:
            age_check("provider:"+safe_text(p.get("key")), p.get("observed_at"), 3600, "/admin/data-center", "Ciclo del proveedor "+safe_text(p.get("key")))
            if p.get("status") == "CACHE":
                age_check("cache:"+safe_text(p.get("key")), p.get("cache_observed_at"), 3600, "/admin/data-center", "Origen de cache")
    samples = evidence.get("queue_samples") or []
    valid = []
    for sample in samples[-4:]:
        d = stamp(sample.get("at")) if isinstance(sample, dict) else None
        n = sample.get("failed") if isinstance(sample, dict) else None
        if d and 0 <= (now-d).total_seconds() <= 86400 and type(n) is int and n >= 0:
            valid.append((d,n))
    if len(valid) == 4 and all(valid[i][0] < valid[i+1][0] and valid[i][1] < valid[i+1][1] for i in range(3)):
        add("queue_growth", "OBSERVAR", "Fallidos en cuatro observaciones: "+str([n for _,n in valid]), "Tres incrementos consecutivos, aunque haya entregas.", "Riesgo de acumulacion de mensajes.", "/admin/telegram/command-center")
    elif len(valid) < 4 or not all(valid[i][0] < valid[i+1][0] for i in range(3)):
        add("queue_trend", "DESCONOCIDO", "Menos de cuatro ciclos con fecha y recuento.", "No se puede inferir tendencia.", "El contador actual no demuestra crecimiento.", "/admin/telegram/command-center")
    for issue in evidence.get("issues", []):
        count = issue.get("seen_count", 1)
        if issue.get("reopened_count", 0) and issue.get("status") in ("OPEN_REAL", "VERIFICATION_FAILED"):
            add("reappeared:"+safe_text(issue.get("id")), "INCIDENTE", "Reaparecio tras una correccion: "+safe_text(issue.get("id")), "La evidencia actual invalida la verificacion anterior.", "Regresion conocida activa.", "/admin/sentinel-issues")
        elif type(count) is int and count > 1 and issue.get("status") not in ("RESOLVED", "FALSE_POSITIVE", "DUPLICATE"):
            add("recurrence:"+safe_text(issue.get("id")), "RIESGO ALTO", str(count)+" observaciones de "+safe_text(issue.get("id")), "Identidad de fallo repetida.", "Puede afectar a consumidores dependientes.", "/admin/sentinel-issues")
    drift = production_drift(evidence.get("identity") or {}, now)
    if drift["state"] != "ALIGNED_CONFIRMED":
        add("production_identity", "INCIDENTE" if drift["state"] == "MISALIGNED_CONFIRMED" else "DESCONOCIDO", drift["state"]+": "+", ".join(drift["mismatches"]), "Identidad de produccion divergente o sin evidencia suficiente.", "No se puede certificar la revision desplegada.", "/admin/final-release")
    for key, reason in (("missing_tests", "Falta prueba critica en la candidata."), ("unbound_buttons", "Control sin accion comprobable.")):
        for item in (evidence.get(key) or [])[:30]:
            add(key+":"+safe_text(item), "ATENCIÓN", safe_text(item), reason, "Regresion sin barrera suficiente.", "/admin/sentinel-workflow")
    ranks = {"NORMAL":0,"DESCONOCIDO":1,"OBSERVAR":2,"ATENCIÓN":3,"RIESGO ALTO":4,"INCIDENTE":5}
    state = max((a["state"] for a in alerts), key=ranks.get, default="NORMAL")
    return {"state":state, "alerts":alerts, "drift":drift, "unknown_count":sum(a["state"]=="DESCONOCIDO" for a in alerts), "probabilities":None}


def reliability_snapshot(memory, evidence, now=None):
    issues = [scrub(i) for i in memory.get("issues", []) if isinstance(i, dict)]
    radar = risk_radar({**evidence, "issues":issues}, now)
    compact = [{k:i.get(k) for k in ("id","fingerprint","title","status","area","route","provider","job","component","error_code","exception_type","file","stable_key","first_seen","last_seen","seen_count","reopened_count","root_cause","fix_sha","pr","regression_test","corrective_action","prevention","detection","verification_record")} for i in issues[:50]]
    for i in compact:
        i["trend"] = "RECURRENTE" if (i.get("seen_count") or 1)>1 else "UNA OBSERVACION"
    timeline = [{"issue_id":i.get("id"), **h} for i in issues for h in (i.get("history") or []) if isinstance(h,dict)]
    timeline.sort(key=lambda h:str(h.get("at_madrid") or ""), reverse=True)
    return {"state":radar["state"], "radar":radar, "issues":compact, "total_issues":len(issues) if evidence.get("memory_available") is True else None,
            "memory_available":evidence.get("memory_available") is True, "timeline":timeline[:30],
            "learning":LEARNING, "source":"LOCAL_PERSISTED_EVIDENCE", "external_calls":0,
            "note":"REPARADO != RESUELTO. Verificacion registrada por Admin conserva alcance y referencia; no ejecuta pruebas ni certifica produccion automaticamente."}


def internal_interface_failures(root):
    """Derive the contract from current consumers, not a frozen symbol list.

    A joint provider/consumer refactor passes; removing only a used interface
    fails. The focused historical target avoids importing application modules.
    """
    import ast
    target = root / "engines/telegram_visual_card_engine.py"
    tree = ast.parse(target.read_text(encoding="utf-8-sig"))
    declared = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            declared.add(n.name)
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in n.targets if isinstance(n, ast.Assign) else [n.target]:
                declared.update(x.id for x in ast.walk(t) if isinstance(x, ast.Name))
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            declared.update(a.asname or a.name.split('.')[0] for a in n.names)
    failures = []
    files = [root/'app.py'] + [p for folder in ('tests','engines','blueprints','tools') for p in (root/folder).rglob('*.py')]
    for p in files:
        if not p.is_file() or p == target:
            continue
        consumer = ast.parse(p.read_text(encoding='utf-8-sig'))
        aliases = set()
        referenced = set()
        for n in ast.walk(consumer):
            if isinstance(n, ast.ImportFrom) and n.module == 'engines':
                aliases.update(a.asname or a.name for a in n.names if a.name == 'telegram_visual_card_engine')
            elif isinstance(n, ast.Import):
                aliases.update(a.asname for a in n.names if a.name == 'engines.telegram_visual_card_engine' and a.asname)
            elif isinstance(n, ast.ImportFrom) and n.module == 'engines.telegram_visual_card_engine':
                referenced.update(a.name for a in n.names if a.name != '*')
        for n in ast.walk(consumer):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in aliases:
                referenced.add(n.attr)
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'setattr' and len(n.args) >= 2:
                if isinstance(n.args[0], ast.Name) and n.args[0].id in aliases and isinstance(n.args[1], ast.Constant) and isinstance(n.args[1].value, str):
                    referenced.add(n.args[1].value)
        failures.extend(str(p.relative_to(root))+': '+name for name in sorted(referenced-declared))
    return failures
