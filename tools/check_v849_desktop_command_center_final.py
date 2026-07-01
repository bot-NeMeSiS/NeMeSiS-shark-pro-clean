from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
base=(ROOT/"templates/base.html").read_text(encoding="utf-8", errors="replace")
css=(ROOT/"static/app.css").read_text(encoding="utf-8", errors="replace")
checks={
 "admin_rail":"v808-admin-rail" in base,
 "client_rail":"v828-client-rail" in base,
 "admin_links": all(x in base for x in ["/admin/data-center","/admin/api-sports","/admin/telegram/command-center","/admin/daily-automation"]),
 "desktop_width":"max-width:1360px" in css,
 "admin_table_style":"ns-admin table" in css,
}
failed=[k for k,v in checks.items() if not v]
print({"checks":checks,"failed":failed}); raise SystemExit(1 if failed else 0)
