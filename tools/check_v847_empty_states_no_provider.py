from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in [ROOT / "app.py", ROOT / "engines" / "api_sports_provider_engine.py"])
required = ["API-SPORTS no configurada", "Esperando proveedor", "Sin datos reales", "Cuotas pendientes", "Resultado pendiente"]
checks = {item: item in text for item in required}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
