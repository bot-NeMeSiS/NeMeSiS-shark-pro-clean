#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "templates").rglob("*.html"))


def main() -> int:
    required_groups = {
        "resultado_pendiente": ["Resultado pendiente"],
        "sin_picks": ["Sin picks activos", "No hay picks activos", "No hay picks publicados"],
        "cuotas_pendientes": ["Cuotas pendientes", "cuota pendiente", "Cuota no disponible", "pendiente de cuota"],
        "madrid_time": ["Madrid"],
        "proximo": ["Próximo"],
        "directo": ["En directo"],
    }
    missing = [name for name, terms in required_groups.items() if not any(term in TEXT for term in terms)]
    forbidden = ["Lorem ipsum", "demo data", "fake match"]
    found_forbidden = [term for term in forbidden if term.lower() in TEXT.lower()]
    print(json.dumps({"ok": not missing and not found_forbidden, "missing_terms": missing, "forbidden_terms": found_forbidden}, ensure_ascii=False, indent=2))
    return 0 if not missing and not found_forbidden else 1


if __name__ == "__main__":
    raise SystemExit(main())
