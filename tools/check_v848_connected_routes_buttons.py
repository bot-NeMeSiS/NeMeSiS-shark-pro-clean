from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "templates").glob("*.html"))
required = ["/app", "/partidos", "/calendar", "/live", "/picks", "/shark", "/profile", "/telegram", "/support", "/track-record", "/favorites", "/combis", "/mercados", "/highlights", "/admin/api-sports", "/admin/data-center", "/admin/telegram/command-center", "/admin/shark-ai"]
checks = {route: route in text or route in (ROOT / "app.py").read_text(encoding="utf-8", errors="replace") for route in required}
checks["no_empty_href"] = 'href=""' not in text and "href='#'" not in text
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
