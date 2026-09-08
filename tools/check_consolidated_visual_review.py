"""Focused offline browser evidence for founder findings H01-H09."""
from __future__ import annotations

import argparse
from datetime import datetime as RealDatetime, timedelta
import json
import logging
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import threading
from unittest.mock import patch
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.local_desktop.run_local_desktop import configure_local_environment
from tools import run_autonomous_product_qa as qa

MADRID = ZoneInfo("Europe/Madrid")
FIXED = RealDatetime(2026, 9, 7, 16, 0, tzinfo=MADRID)


class FrozenMeta(type):
    def __instancecheck__(cls, obj):
        return isinstance(obj, RealDatetime)


class FrozenDatetime(RealDatetime, metaclass=FrozenMeta):
    offset = timedelta(0)
    @classmethod
    def now(cls, tz=None):
        value = FIXED + cls.offset
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)

    @classmethod
    def utcnow(cls):
        return (FIXED + cls.offset).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--scenario", choices=["populated","partial","empty"], default="populated")
    parser.add_argument("--only", default="")
    parser.add_argument("--widths", default="390,430,360,1366")
    parser.add_argument("--surfaces-json", help="Explicitly reviewed local HTML routes only")
    args = parser.parse_args()
    output = ROOT / ".tmp_reference_review/consolidated_h01_h09" / args.label
    output.mkdir(parents=True, exist_ok=False)
    db = ROOT / "data/local_dev" / ("consolidated_" + args.label + ".sqlite")
    if db.exists():
        raise SystemExit("Use a new isolated QA database.")
    configure_local_environment("offline_safe", 5000, db.name)
    os.environ["NEMESIS_QA_CLIENT_NAME"] = "Cliente de prueba con nombre largo"
    qa.seed_database(db)
    password = secrets.token_urlsafe(24)
    qa._seed_extra(db, password, FIXED)
    import app as module
    module.DB_PATH = str(db)
    module.app.config.update(TESTING=True)
    module._SEEDED_DB_PATH = str(db)
    module._SEEDING_DB_PATH = None
    module.APP_INITIALIZED = True
    rendered_templates = []
    from flask import template_rendered
    def remember_template(sender, template, **extra):
        rendered_templates.append(template.name)
    template_rendered.connect(remember_template, module.app, weak=False)
    qa._seed_extra(db, password, FIXED)
    qa._apply_data_scenario(db, args.scenario, FIXED)
    clock_patches = []
    for mod in list(sys.modules.values()):
        filename = getattr(mod, "__file__", "") or ""
        if filename.startswith(str(ROOT)) and "site-packages" not in filename:
            if getattr(mod, "datetime", None) is RealDatetime:
                p = patch.object(mod, "datetime", FrozenDatetime)
                p.start()
                clock_patches.append(p)
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    server = make_server("127.0.0.1", 0, module.app, threaded=False)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    rows = []
    errors = []
    interactions = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for view_index,(width,height) in enumerate([(390,844),(430,932),(360,800),(1366,768),(834,1194)]):
                if str(width) not in args.widths.split(","):
                    continue
                FrozenDatetime.offset = timedelta(seconds=view_index)
                ctx = browser.new_context(viewport={"width":width,"height":height},locale="es-ES",
                    timezone_id="Europe/Madrid",service_workers="block")
                ctx.route("**/*", qa._route_guard)
                page = ctx.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                surfaces = [("match","/match/m-1","client"),("live_match","/match/m-2","client"),
                    ("upcoming_match","/match/m-3","client"),("home","/app","client"),
                    ("admin_data_marketplace","/admin/data-marketplace","admin"),
                    ("admin_real_launch","/admin/real-launch","admin"),
                    ("admin","/admin/dashboard","admin"),
                    ("track_record","/track-record","client"),("membership","/memberships","client"),
                    ("telegram","/telegram","client"),("partidos","/calendar","client"),
                    ("profile","/profile","client"),("picks","/picks","client"),("directo","/live","client")]
                if args.surfaces_json:
                    surfaces = [tuple(row) for row in json.loads(Path(args.surfaces_json).read_text(encoding="utf-8"))]
                for key,route,role in surfaces:
                    if args.only and key not in args.only.split(","):
                        continue
                    ctx.clear_cookies()
                    if role != "public":
                        qa._set_role_cookie(ctx,module,role)
                    rendered_templates.clear()
                    try:
                        response=page.goto(url+route,wait_until="domcontentloaded",timeout=15000)
                        page.wait_for_timeout(350)
                    except Exception as exc:
                        rows.append({"surface":key,"route":route,"role":role,"viewport":[width,height],
                            "http":0,"overflow":False,"result":"NOT_RUN","reason":type(exc).__name__,
                            "geometry":{"match_text_status":"NOT_RUN","heading_covered":False}})
                        (output/"progress.json").write_text(json.dumps(rows,ensure_ascii=False),encoding="utf-8")
                        continue
                    page.evaluate("document.activeElement?.blur();window.scrollTo(0,0)")
                    page.wait_for_timeout(100)
                    geometry=qa.inspect_text_geometry(page)
                    computed=page.evaluate("""() => ['main','main h1','.grid.compact-grid','.metric'].map(selector=>{const n=document.querySelector(selector);if(!n)return {selector};const s=getComputedStyle(n);const rules=[];function scan(list){for(const r of list){if(r.selectorText){try{if(n.matches(r.selectorText)&&/padding|font-size|grid-template-columns|border/.test(r.style.cssText))rules.push(r.cssText)}catch{}}else if(r.cssRules)scan(r.cssRules)}}for(const sheet of document.styleSheets){try{scan(sheet.cssRules)}catch{}}return {selector,classes:n.className,padding:s.paddingTop,font:s.fontSize,grid:s.gridTemplateColumns,border:s.border,rules:rules.slice(-18)}})""")
                    shot=output/f"{key}_{width}.png"
                    page.screenshot(path=str(shot))
                    bootstrap_checks = {}
                    if route == '/admin-bootstrap' and width <= 430:
                        page.evaluate('window.scrollTo(0,500)')
                        page.goto(url+'/local-safe', wait_until='domcontentloaded', timeout=15000)
                        page.go_back(wait_until='domcontentloaded', timeout=15000)
                        page.evaluate('window.scrollTo(0,0)')
                        page.locator('main h1').evaluate("n => n.style.fontSize = (parseFloat(getComputedStyle(n).fontSize)*1.3)+'px'")
                        bootstrap_checks['return_text130'] = qa.inspect_text_geometry(page)
                        page.screenshot(path=str(output/f'{key}_{width}_text130.png'))
                        banner = page.locator('[data-local-safe-banner]')
                        banner.evaluate("n => {n.style.height='400px';n.style.zIndex='99999'}")
                        bootstrap_checks['negative_overlap_detected'] = qa.inspect_text_geometry(page)['heading_covered']
                        banner.evaluate("n => {n.style.removeProperty('height');n.style.removeProperty('z-index')}")
                    row={"surface":key,"route":route,"role":role,"viewport":[width,height],
                        "scenario":"SIMULATED_QA_"+args.scenario.upper(),"clock":(FIXED+FrozenDatetime.offset).isoformat(),
                        "tree":qa._visual_tree_fingerprint(),"http":response.status,
                        "capture":str(shot),"crop":None,"geometry":geometry,
                        "templates":list(dict.fromkeys(rendered_templates)),
                        "computed":computed,
                        "final_path":urlparse(page.url).path,
                        "heading":page.locator('main h1:not(.sr-only)').all_text_contents(),
                        "overflow":page.evaluate("document.documentElement.scrollWidth>innerWidth+1")}
                    if bootstrap_checks:
                        row['bootstrap_checks'] = bootstrap_checks
                    if key=="track_record":
                        row["text"]=page.locator(".v933-track-record").inner_text()
                        with module.app.test_request_context("/track-record"):
                            record=module.v742_track_record_context()
                            row["record"]={k:record.get(k) for k in ("won","lost","void","stake_total","profit","roi","winrate","evaluable_total","decided_total","by_month")}
                            row["learning"]=[module.get_v937_pick_learning(p) for p in record.get("recent_results",[])]
                    if key in ("admin_data_marketplace","admin_real_launch"):
                        row["shell"]=page.locator("main").evaluate("(n)=>({classes:n.className,padding:getComputedStyle(n).paddingTop,top:n.getBoundingClientRect().top})")
                        page.evaluate("window.scrollTo(0,500)")
                        page.evaluate("window.scrollTo(0,0)")
                        page.wait_for_timeout(150)
                        row["after_return"]=qa.inspect_text_geometry(page)
                    if key=="picks":
                        row["decorations"]=page.evaluate("""() => ['before','after'].map(p=>{const s=getComputedStyle(document.body,'::'+p);return {pseudo:p,clip:s.clipPath,background:s.backgroundImage,transform:s.transform}})""")
                    if key=="telegram":
                        row["primary_action"]=page.locator("#vincular button").evaluate("(n)=>({visible:n.getClientRects().length>0,text:n.textContent,top:n.getBoundingClientRect().top})")
                    if key in ("membership","partidos","favorites_page"):
                        for summary in page.locator("details > summary").all():
                            summary.click()
                            interactions.append({"route":route,"label":summary.inner_text(),"open":summary.evaluate("(n)=>n.parentElement.open")})
                        page.evaluate("window.scrollTo(0,0)")
                    if key in ("match","live_match","upcoming_match") and width in (390,430):
                        page.locator(".v944-match-header").evaluate("""root => {
                            for (const n of root.querySelectorAll('strong,span,time,small')) {
                                const size=parseFloat(getComputedStyle(n).fontSize);
                                n.style.fontSize=(size*1.3)+'px';
                            }
                            for (const n of root.querySelectorAll('.v944-match-team strong'))
                                n.textContent+=' Club Deportivo Nombre Largo QA';
                        }""")
                        row["enlarged"]=qa.inspect_text_geometry(page)
                        enlarged=output/f"{key}_{width}_text130.png"
                        page.screenshot(path=str(enlarged))
                        row["enlarged_capture"]=str(enlarged)
                    rows.append(row)
                    (output/"progress.json").write_text(json.dumps(rows,ensure_ascii=False),encoding="utf-8")
                # Negative and positive detector controls use only an isolated blank page.
                page.goto("about:blank")
                page.set_content('<div class="v944-match-header__status"><span>Final</span><section class="v944-score-widget"><strong>2-0</strong></section><time>Domingo, 30 de agosto - 21:00</time></div>')
                positive=qa.inspect_text_geometry(page)
                page.add_style_tag(content=".v944-score-widget,time{position:absolute;top:40px;left:20px}")
                negative=qa.inspect_text_geometry(page)
                interactions.append({"detector_control":True,"width":width,
                    "positive":positive["match_text_status"],"negative":negative["match_text_status"]})
                ctx.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join()
        for p in reversed(clock_patches):
            p.stop()
    result={"base":os.popen("git rev-parse HEAD").read().strip(),"tree":qa._visual_tree_fingerprint(),
        "origin":"SIMULATED_QA","clock":FIXED.isoformat(),"rows":rows,
        "interactions":interactions,"page_errors":errors}
    (output/"evidence.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    failures=[r["surface"]+str(r["viewport"]) for r in rows if not r["http"] or r["http"]>=500 or r["overflow"]
        or (r.get('bootstrap_checks') and (r['bootstrap_checks']['return_text130']['heading_covered'] or not r['bootstrap_checks']['negative_overlap_detected']))
        or r["geometry"]["match_text_status"] == "FAIL" or r["geometry"]["heading_covered"]
        or r.get("enlarged",{}).get("match_text_overlap")
        or (r.get("primary_action") and not r["primary_action"]["visible"])
        or any(d["clip"] != "none" for d in r.get("decorations",[]))]
    print(json.dumps({"output":str(output),"captures":len(rows),"failures":failures,"page_errors":len(errors)},ensure_ascii=False))
    return bool(failures or errors)


if __name__=="__main__":
    raise SystemExit(main())
