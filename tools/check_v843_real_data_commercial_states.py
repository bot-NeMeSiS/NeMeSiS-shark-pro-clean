from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
required_terms = [
    "Próximo",
    "En directo",
    "Resultado",
    "Resultado pendiente",
    "Esperando proveedor",
    "Sin datos reales",
    "Sin picks activos",
    "Cuotas pendientes",
    "Conectar Telegram",
    "Madrid",
]

combined = []
for path in list((ROOT / "templates").glob("*.html")) + [ROOT / "app.py"] + list((ROOT / "engines").glob("*.py")):
    if path.exists():
        combined.append(path.read_text(encoding="utf-8", errors="ignore"))
text = "\n".join(combined)
visible_text = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in (ROOT / "templates").glob("*.html")
)

missing = [term for term in required_terms if term not in text]
forbidden_client_terms = ["Lorem ipsum", "undefined", ">None<", ">null<", "datos demo", "partido demo"]
forbidden_found = [term for term in forbidden_client_terms if term.lower() in visible_text.lower()]

payload = {
    "ok": not missing and not forbidden_found,
    "missing_terms": missing,
    "forbidden_found": forbidden_found,
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
