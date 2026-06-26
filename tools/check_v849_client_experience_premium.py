from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
base=(ROOT/"templates/base.html").read_text(encoding="utf-8", errors="replace")
css=(ROOT/"static/app.css").read_text(encoding="utf-8", errors="replace")
checks={
 "client_links": all(x in base for x in ["/app","/partidos","/live","/picks","/shark","/profile","/telegram","/support"]),
 "logout": "/logout" in base,
 "premium_states": all(x in (ROOT/"engines/api_sports_provider_engine.py").read_text(encoding="utf-8") for x in ["Sin datos reales","Esperando proveedor","Sin picks activos"]),
 "buttons": ".btn.primary" in css and "min-height:44px" in css,
 "no_demo_copy": "demo visible" not in base.lower(),
}
failed=[k for k,v in checks.items() if not v]
print({"checks":checks,"failed":failed}); raise SystemExit(1 if failed else 0)
