#!/usr/bin/env python3
"""Generate a V731 client experience QA report."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.client_experience_guard_engine import client_experience_snapshot

REPORT_MD = ROOT / "V731_CLIENT_EXPERIENCE_QA_REPORT.md"
REPORT_JSON = ROOT / "reports" / "CLIENT_EXPERIENCE_QA_V731.json"


def main() -> int:
    snapshot = client_experience_snapshot(ROOT)
    REPORT_JSON.parent.mkdir(exist_ok=True)
    REPORT_JSON.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# V731 Client Experience QA Report",
        "",
        f"- Estado: **{snapshot['status']}**",
        f"- Score: **{snapshot['score']}/100**",
        f"- Templates cliente escaneados: {snapshot['templates_scanned']}",
        f"- Avisos totales: {snapshot['findings_count']}",
        f"- Avisos importantes: {snapshot['warning_count']}",
        "",
        "## Pantallas críticas",
    ]
    for item in snapshot["critical_screens"]:
        lines.append(
            f"- `{item['route']}` · `{item['template']}`: {item['status']} · "
            f"Hora Madrid: {'sí' if item['uses_madrid_filters'] else 'revisar'} · "
            f"Estado vacío: {'sí' if item['has_empty_state_hint'] else 'revisar'}"
        )
    lines.extend(["", "## Siguiente acción recomendada"])
    for step in snapshot["recommended_next_steps"]:
        lines.append(f"- {step}")
    if snapshot["findings"]:
        lines.extend(["", "## Primeros avisos"])
        for item in snapshot["findings"][:30]:
            lines.append(
                f"- {item['severity']} · {item['category']} · `{item['template']}`:{item.get('line') or '—'} · "
                f"`{item['pattern']}` — {item['message']}"
            )
    lines.extend([
        "",
        "## Notas",
        "- Este control es estático y conservador: no sustituye la revisión visual real en móvil/desktop.",
        "- El objetivo es detectar señales de riesgo antes de publicar, sin modificar datos ni enviar Telegram.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return 0 if snapshot["score"] >= 70 else 1


if __name__ == "__main__":
    raise SystemExit(main())
