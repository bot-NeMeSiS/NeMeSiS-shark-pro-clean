from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
texts = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "templates").rglob("*.html"))

required = {
    "resultado_pendiente": "Resultado pendiente" in texts,
    "esperando": "Esperando" in texts,
    "sin_picks": "Sin picks" in texts or "No hay picks activos" in texts,
    "cuotas_pendientes": "Cuotas pendientes" in texts,
    "madrid_time": "Madrid" in texts,
}
forbidden = ["Lorem ipsum", "{{ title or", "undefined", "None"]
hits = [token for token in forbidden if token in texts]

payload = {"ok": all(required.values()) and not hits, "checks": required, "forbidden_hits": hits}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
