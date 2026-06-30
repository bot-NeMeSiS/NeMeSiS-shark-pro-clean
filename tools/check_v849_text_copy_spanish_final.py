from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
targets=[ROOT/"templates/base.html", ROOT/"templates/admin_api_sports_audit.html", ROOT/"static/app.css"]
bad=["","undefined","lo primo","proximo ","analisis ","competicion ","informacion ","conexion ","membresia ","senales "]
hits=[]
for p in targets:
 t=p.read_text(encoding="utf-8", errors="replace").lower()
 for b in bad:
  if b in t: hits.append(f"{p.name}:{b}")
print({"hits":hits}); raise SystemExit(1 if hits else 0)
