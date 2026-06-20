from pathlib import Path
import json, os, sys, re
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = "V838_FULL_PRODUCT_ARCHITECTURE_FINAL_REVIEW_AND_COMPLETION"
def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")
def ok(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload.get("ok") else 1)

text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT/"templates").rglob("*.html"))
required = ["Resultado pendiente", "Esperando", "Sin picks", "Cuotas pendientes"]
missing = [x for x in required if x not in text]
forbidden = [x for x in ["Lorem ipsum", "undefined", "{{ title or", "Espa?a", "Andaluc?a"] if x in text]
ok({"ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden})
