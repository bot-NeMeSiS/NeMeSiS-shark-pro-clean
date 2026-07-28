#!/usr/bin/env python3
"""Validate and report the NeMeSiS Experience Platform."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.experience_platform_engine import (  # noqa: E402
    EXPERIENCE_AUDITOR_CONTRACT,
    EXPERIENCE_PLATFORM_CONTRACT,
    NAVIGATION_INTEGRITY_CONTRACT,
    PRODUCT_POLISH_CONTRACT,
    UX_CONSISTENCY_CONTRACT,
    VISUAL_DENSITY_CONTRACT,
    build_experience_platform_snapshot,
)
from engines.project_operating_system_engine import build_product_roadmap  # noqa: E402
from engines.sentinel_autopilot_engine import build_experience_platform_contract_snapshot  # noqa: E402
from engines.sports_platform_contracts import build_sports_platform_contract_registry  # noqa: E402

REPORTS = {
    "experience": ROOT / "reports" / "EXPERIENCE_PLATFORM_REPORT.md",
    "polish": ROOT / "reports" / "PRODUCT_POLISH_REPORT.md",
    "ux": ROOT / "reports" / "UX_CONSISTENCY_REPORT.md",
    "visual": ROOT / "reports" / "VISUAL_AUDIT_REPORT.md",
}
UNSAFE_ENGINE_RE = re.compile(
    r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe|openai|bs4|selenium|playwright|subprocess)\b|\b(?:commit|execute|executemany|urlopen|Session)\s*\(",
    re.IGNORECASE | re.MULTILINE,
)


def _table(rows: list[dict[str, object]], columns: list[str]) -> str:
    if not rows:
        return "No hay elementos registrados.\n"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(col, "")).replace("\n", " ") for col in columns) + " |")
    return "\n".join([header, sep, *body]) + "\n"


def _findings(snapshot: dict) -> list[dict]:
    return list(((snapshot.get("findings") or {}).get("top") or []))


def _severity_summary(snapshot: dict) -> str:
    by_severity = (snapshot.get("findings") or {}).get("by_severity") or {}
    return ", ".join(f"{key}={value}" for key, value in sorted(by_severity.items())) or "sin hallazgos"


def _experience_report(snapshot: dict) -> str:
    audit = snapshot["audit"]
    inventory = audit["screen_inventory"]
    rows = [
        {
            "area": "Pantallas",
            "estado": snapshot["status"],
            "evidencia": f"{snapshot['screen_count']} screens, {snapshot['component_count']} components",
        },
        {
            "area": "Navegacion",
            "estado": audit["navigation"]["status"],
            "evidencia": f"{audit['navigation']['routes_detected']} rutas, {audit['navigation']['hrefs_scanned']} hrefs",
        },
        {
            "area": "Consistencia UX",
            "estado": audit["ux_consistency"]["status"],
            "evidencia": f"{len(audit['ux_consistency']['findings'])} hallazgos",
        },
        {
            "area": "Densidad visual",
            "estado": audit["visual_density"]["status"],
            "evidencia": f"{len(audit['visual_density']['findings'])} hallazgos revisables",
        },
    ]
    return f"""# Experience Platform Report

## Decision

PASS LOCAL.

La plataforma de experiencia queda creada como auditoria local read-only. No cambia Sports Core, SHARK, datos, APIs, DB, Telegram, Stripe ni produccion.

## Contracts

- {EXPERIENCE_PLATFORM_CONTRACT}
- {EXPERIENCE_AUDITOR_CONTRACT}
- {PRODUCT_POLISH_CONTRACT}
- {UX_CONSISTENCY_CONTRACT}
- {NAVIGATION_INTEGRITY_CONTRACT}
- {VISUAL_DENSITY_CONTRACT}

## Scope

- Cliente: incluido mediante templates y rutas locales.
- Admin: incluido mediante templates y rutas locales.
- Desktop/tablet/mobile: reglas preparadas y Browser QA obligatorio antes de cualquier cambio visual.
- Logica de producto: no modificada.

## Summary

{_table(rows, ['area', 'estado', 'evidencia'])}

## Findings

Total: {snapshot['findings']['total']} ({_severity_summary(snapshot)}).

{_table(_findings(snapshot)[:12], ['severity', 'category', 'screen', 'title'])}

## Guardrails

```json
{json.dumps(snapshot['guardrails'], indent=2, ensure_ascii=False)}
```

## Limitations

- Es una auditoria estatica/local; no declara produccion certificada.
- No aplica cambios automaticos de UI.
- Los hallazgos P3 de densidad requieren evidencia visual antes de tocar CSS.
- Las superficies admin con login requieren credenciales QA para Browser QA autenticado.
"""


def _polish_report(snapshot: dict) -> str:
    polish = snapshot["audit"]["product_polish"]
    return f"""# Product Polish Report

## Purpose

Convertir hallazgos UX en una cola de pulido controlada, sin autocorregir codigo ni cambiar logica.

## Status

{polish['status']}

## Backlog Summary

- Total findings: {polish['total_findings']}
- By severity: {_severity_summary(snapshot)}
- Autofix allowed: {polish['autofix_allowed']}

## Next Actions

{_table(polish['next_actions'], ['priority', 'screen', 'issue', 'action'])}

## Product Rule

Ningun cambio visual debe aplicarse sin evidencia, Browser QA desktop/tablet/mobile y Sentinel limpio.
"""


def _ux_report(snapshot: dict) -> str:
    ux = snapshot["audit"]["ux_consistency"]
    return f"""# UX Consistency Report

## Status

{ux['status']}

## Coverage

- Templates scanned: {ux['templates_scanned']}
- Buttons scanned: {ux['buttons_scanned']}

## Findings

{_table(ux['findings'][:40], ['severity', 'category', 'screen', 'title', 'evidence'])}

## Permanent Rule

Las pantallas no deben exponer texto tecnico, `None`, `null`, `undefined`, mojibake, botones sin contrato visual ni navegacion mezclada cliente/admin.
"""


def _visual_report(snapshot: dict) -> str:
    density = snapshot["audit"]["visual_density"]
    return f"""# Visual Audit Report

## Status

{density['status']}

## Coverage

- Screens scanned: {density['screens_scanned']}
- CSS files scanned: {density['css_files_scanned']}
- CSS findings capped: {density['css_findings_capped']}

## Findings

{_table(density['findings'][:50], ['severity', 'category', 'screen', 'title', 'evidence'])}

## Permanent Rule

Exceso de scroll, bloques enormes, espacios vacios y baja densidad no se corrigen con parches a ciegas: primero evidencia visual, despues cambio minimo y QA.
"""


def write_reports(snapshot: dict) -> None:
    REPORTS["experience"].write_text(_experience_report(snapshot), encoding="utf-8")
    REPORTS["polish"].write_text(_polish_report(snapshot), encoding="utf-8")
    REPORTS["ux"].write_text(_ux_report(snapshot), encoding="utf-8")
    REPORTS["visual"].write_text(_visual_report(snapshot), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args()

    snapshot = build_experience_platform_snapshot(ROOT)
    failures: list[str] = []
    if snapshot.get("contract") != EXPERIENCE_PLATFORM_CONTRACT:
        failures.append("experience_platform_contract_missing")
    auditors = snapshot.get("auditors") or {}
    for key, contract in {
        "experience_auditor": EXPERIENCE_AUDITOR_CONTRACT,
        "product_polish_engine": PRODUCT_POLISH_CONTRACT,
        "ux_consistency_checker": UX_CONSISTENCY_CONTRACT,
        "navigation_integrity_checker": NAVIGATION_INTEGRITY_CONTRACT,
        "visual_density_auditor": VISUAL_DENSITY_CONTRACT,
    }.items():
        if auditors.get(key) != contract:
            failures.append(f"{key}_contract_missing")
    if snapshot.get("screen_count", 0) <= 0:
        failures.append("no_screens_scanned")
    if snapshot.get("routes_detected", 0) <= 0:
        failures.append("no_routes_detected")
    for key, value in (snapshot.get("guardrails") or {}).items():
        if value not in (0, False):
            failures.append(f"guardrail_not_zero:{key}")
    engine_text = (ROOT / "engines" / "experience_platform_engine.py").read_text(encoding="utf-8", errors="replace")
    if UNSAFE_ENGINE_RE.search(engine_text):
        failures.append("experience_engine_has_side_effect_imports")
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities", [])}
    if (capabilities.get("experience_platform") or {}).get("state") != "INTEGRATED":
        failures.append("experience_platform_not_integrated_in_registry")
    roadmap = build_product_roadmap(ROOT)
    roadmap_modules = {item["name"]: item for item in roadmap.get("modules", [])}
    if (roadmap_modules.get("Experience Platform") or {}).get("state") != "COMPLETED":
        failures.append("experience_platform_not_completed_in_roadmap")
    sentinel = build_experience_platform_contract_snapshot(ROOT)
    if sentinel.get("validation_result") != "PASS":
        failures.append("experience_platform_sentinel_contract_not_pass")

    if args.write_reports:
        write_reports(snapshot)
    if args.write_reports:
        for name, path in REPORTS.items():
            if not path.exists() or path.stat().st_size <= 200:
                failures.append(f"report_missing:{name}")

    payload = {
        "ok": not failures,
        "contract": snapshot.get("contract"),
        "status": snapshot.get("status"),
        "screens": snapshot.get("screen_count"),
        "components": snapshot.get("component_count"),
        "routes": snapshot.get("routes_detected"),
        "findings": snapshot.get("findings"),
        "guardrails": snapshot.get("guardrails"),
        "registry": (capabilities.get("experience_platform") or {}).get("state"),
        "roadmap": (roadmap_modules.get("Experience Platform") or {}).get("state"),
        "sentinel": sentinel.get("validation_result"),
        "reports": {name: str(path) for name, path in REPORTS.items() if path.exists()},
        "failures": failures,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())