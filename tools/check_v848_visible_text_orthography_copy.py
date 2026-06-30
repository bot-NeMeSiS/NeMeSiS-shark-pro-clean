from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
targets = [ROOT / "templates" / "base.html", ROOT / "templates" / "admin_api_sports_audit.html", ROOT / "static" / "app.css"]
bad_tokens = ["", "undefined", "lo primo", "proximo ", "analisis ", "competicion ", "conexion ", "membresia ", "senales "]
hits = []
for path in targets:
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    for token in bad_tokens:
        if token in text:
            hits.append(f"{path.name}:{token}")
print({"hits": hits})
raise SystemExit(1 if hits else 0)
