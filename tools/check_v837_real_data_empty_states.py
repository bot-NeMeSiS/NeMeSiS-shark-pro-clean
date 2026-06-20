#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "templates").rglob("*.html"))


def main() -> int:
    groups = {
        "proximo": ["Próximo"],
        "directo": ["En directo"],
        "resultado_pendiente": ["Resultado pendiente"],
        "sin_picks": ["Sin picks activos", "No hay picks activos", "No hay picks publicados"],
        "cuotas_pendientes": ["Cuotas pendientes", "cuota pendiente", "Cuota no disponible", "pendiente de cuota"],
        "madrid": ["Madrid"],
        "fallback": ["fallback", "Sin logo real", "Escudo"],
    }
    missing = [name for name, terms in groups.items() if not any(term in TEXT for term in terms)]
    forbidden = [term for term in ["Lorem ipsum", "demo data", "fake match"] if term.lower() in TEXT.lower()]
    mojibake_tokens = [chr(0x00C3), chr(0x00C2), chr(0x00F0) + chr(0x009F), "{{ title or"]
    mojibake = any(token in TEXT for token in mojibake_tokens)
    print(json.dumps({"ok": not missing and not forbidden and not mojibake, "missing": missing, "forbidden": forbidden, "mojibake": mojibake}, ensure_ascii=False, indent=2))
    return 0 if not missing and not forbidden and not mojibake else 1


if __name__ == "__main__":
    raise SystemExit(main())
