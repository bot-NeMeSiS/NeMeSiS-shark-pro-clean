#!/usr/bin/env python3
"""Generate V732 production readiness report without external side effects."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.production_readiness_engine import production_readiness_snapshot

VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip() if (ROOT / "VERSION.txt").exists() else "DEV"
VERSION_PREFIX = VERSION.split("_", 1)[0]
REPORT_PATH = ROOT / f"V732_PRODUCTION_READINESS_CONTROL_CENTER_REPORT.md"
SNAPSHOT_JSON = ROOT / "reports" / f"PRODUCTION_READINESS_SNAPSHOT_{VERSION_PREFIX}.json"


def write_report(snapshot: dict) -> None:
    lines = [
        "# V732 Production Readiness Control Center",
        "",
        f"- Versión: `{VERSION}`",
        f"- Score: **{snapshot['score']}/100**",
        f"- Estado: **{snapshot['status']}**",
        f"- Generado: `{snapshot['generated_at']}`",
        "",
        "## Bloqueos",
    ]
    if snapshot["blockers"]:
        lines += [f"- {item}" for item in snapshot["blockers"]]
    else:
        lines.append("- No hay bloqueos estáticos críticos detectados.")
    lines += ["", "## Avisos"]
    if snapshot["warnings"]:
        lines += [f"- {item}" for item in snapshot["warnings"]]
    else:
        lines.append("- No hay avisos estáticos importantes.")
    lines += ["", "## Versión"]
    for key, value in snapshot["version"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines += ["", "## Variables seguras"]
    for item in snapshot["env"]:
        extra = f" esperado `{item['expected']}`" if item.get("expected") else ""
        lines.append(f"- {item['label']}: {item['safe_value']} · severidad {item['severity']}{extra}")
    lines += ["", "## Centros admin"]
    for item in snapshot["admin_centers"]:
        lines.append(f"- {item['label']}: ruta {'OK' if item['route_exists'] else 'FALTA'} · template {'OK' if item['template_exists'] else 'FALTA'}")
    lines += ["", "## Limpieza"]
    lines.append(f"- Prohibidos en raíz: {snapshot['tree']['forbidden_count']}")
    if snapshot["tree"]["forbidden_dirs"]:
        lines.append(f"- Directorios prohibidos: {', '.join(snapshot['tree']['forbidden_dirs'])}")
    lines += ["", "## Checklist Render"]
    for item in snapshot["render_checks"]:
        lines.append(f"- `{item['route']}` → {item['expected']}")
    lines += ["", "## Próximos pasos"]
    lines += [f"- {item}" for item in snapshot["recommended_next_steps"]]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    snapshot = production_readiness_snapshot(ROOT, VERSION)
    (ROOT / "reports").mkdir(exist_ok=True)
    SNAPSHOT_JSON.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(snapshot)
    print(json.dumps({
        "ok": True,
        "version": VERSION,
        "score": snapshot["score"],
        "status": snapshot["status"],
        "blockers": snapshot["blockers"],
        "warnings": snapshot["warnings"],
        "report": str(REPORT_PATH),
        "snapshot_json": str(SNAPSHOT_JSON),
    }, ensure_ascii=False, indent=2))
    # Do not fail local/sandbox for missing Render env; blockers are informational here.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
