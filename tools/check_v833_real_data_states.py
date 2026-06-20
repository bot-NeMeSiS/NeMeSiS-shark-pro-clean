#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def main() -> int:
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in TEMPLATES.glob("*.html"))
    checks = {
        "resultado_pendiente": "Resultado pendiente" in text,
        "sin_picks": "Sin picks activos" in text or "No hay picks activos" in text,
        "esperando_datos": "Esperando datos" in text or "Esperando proveedor" in text or "Esperando datos reales" in text,
        "cuotas_no_fake": "Cuotas pendientes" in text or "cuota" in text.lower(),
        "no_fake_minute_text": "minuto inventado" not in text.lower(),
        "no_demo_literal": "Lorem ipsum" not in text and "datos demo" not in text.lower() and "partido demo" not in text.lower(),
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
