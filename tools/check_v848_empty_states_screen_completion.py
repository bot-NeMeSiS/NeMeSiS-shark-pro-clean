from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in [ROOT / "app.py", ROOT / "engines" / "api_sports_provider_engine.py", ROOT / "static" / "app.css"])
required = ["Esperando proveedor", "Sin datos reales", "Sin picks activos", "Cuotas pendientes", "Resultado pendiente"]
checks = {token: token in text for token in required}
checks["empty_visual"] = "empty-state" in text or "premium-empty" in text
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
