from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
templates="\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT/"templates").glob("*.html"))
app=(ROOT/"app.py").read_text(encoding="utf-8", errors="replace")
routes=["/app","/partidos","/calendar","/live","/picks","/shark","/profile","/telegram","/support","/track-record","/favorites","/combis","/mercados","/highlights","/admin/api-sports","/admin/data-center","/admin/telegram/command-center","/admin/shark-ai","/logout"]
checks={r:(r in templates or r in app) for r in routes}
checks["no_empty_href"]='href=""' not in templates and "href='#'" not in templates
failed=[k for k,v in checks.items() if not v]
print({"checks":checks,"failed":failed}); raise SystemExit(1 if failed else 0)
