#!/usr/bin/env python3
"""Validate and report the NeMeSiS Product Review System."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.product_review_system_engine import (  # noqa: E402
    PRODUCT_REVIEW_CENTER_CONTRACT,
    PRODUCT_REVIEW_SYSTEM_CONTRACT,
    QUALITY_TEAM_CONTRACT,
    REQUIRED_FINDING_FIELDS,
    REVIEWER_DEFINITIONS,
    build_product_review_system_snapshot,
)
from engines.project_operating_system_engine import build_product_roadmap  # noqa: E402
from engines.sports_platform_contracts import build_sports_platform_contract_registry  # noqa: E402

REPORTS = {
    "system": ROOT / "reports" / "PRODUCT_REVIEW_SYSTEM_REPORT.md",
    "employees": ROOT / "reports" / "DIGITAL_EMPLOYEES_REPORT.md",
    "matrix": ROOT / "reports" / "QUALITY_REVIEW_MATRIX.md",
    "scorecard": ROOT / "reports" / "PRODUCT_SCORECARD.md",
    "team": ROOT / "reports" / "WORLD_CLASS_PRODUCT_TEAM.md",
}

UNSAFE_ENGINE_RE = re.compile(
    r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe|openai|subprocess|selenium|playwright)\b"
    r"|\b(?:execute|executemany|urlopen|Session|post|put|delete)\s*\(",
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


def _reviewer_rows(snapshot: dict) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for reviewer in snapshot.get("reviewers", []):
        counts = reviewer.get("findings_by_priority") or {}
        rows.append(
            {
                "revisor": reviewer.get("name"),
                "estado": reviewer.get("state"),
                "score": reviewer.get("score"),
                "P0": counts.get("P0", 0),
                "P1": counts.get("P1", 0),
                "P2": counts.get("P2", 0),
                "P3": counts.get("P3", 0),
                "evidencia": "; ".join(str(item.get("evidence", "")) for item in (reviewer.get("evidence_checks") or [])[:2]),
            }
        )
    return rows


def _finding_rows(snapshot: dict) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for finding in snapshot.get("findings", []):
        rows.append(
            {
                "prioridad": finding.get("priority"),
                "revisor": finding.get("reviewer"),
                "modulo": finding.get("module"),
                "pantalla": finding.get("screen"),
                "ruta": finding.get("route"),
                "componente": finding.get("component"),
                "evidencia": finding.get("evidence"),
                "propuesta": finding.get("proposal"),
            }
        )
    return rows


def _system_report(snapshot: dict) -> str:
    return f"""# Product Review System Report

## Decision

PASS LOCAL.

El Product Review System queda creado como departamento interno de calidad read-only. No genera IA, no crea chatbot, no ejecuta mejoras, no llama proveedores, no toca Telegram, no toca Stripe, no modifica produccion y no hace deploy ni push.

## Contracts

- {PRODUCT_REVIEW_SYSTEM_CONTRACT}
- {PRODUCT_REVIEW_CENTER_CONTRACT}
- {QUALITY_TEAM_CONTRACT}

## Executive Summary

- Estado: {snapshot['status']}
- Score global: {snapshot['score']}/100
- Revisores: {snapshot['reviewer_count']} de {snapshot['reviewers_expected']}
- Hallazgos: {snapshot['findings_summary']}
- Entorno: {snapshot['environment']}

## Reviewers

{_table(_reviewer_rows(snapshot), ['revisor', 'estado', 'score', 'P0', 'P1', 'P2', 'P3', 'evidencia'])}

## Findings

{_table(_finding_rows(snapshot), ['prioridad', 'revisor', 'modulo', 'pantalla', 'ruta', 'componente', 'evidencia', 'propuesta'])}

## Guardrails

```json
{json.dumps(snapshot['guardrails'], indent=2, ensure_ascii=False)}
```

## Limitations

- Auditoria local basada en archivos, rutas, contratos e informes existentes.
- No certifica produccion.
- Los candidatos de roadmap requieren aprobacion humana.
"""


def _employees_report(snapshot: dict) -> str:
    rows = [
        {
            "revisor": item["name"],
            "modulo": item["module"],
            "responsabilidad": item["responsibility"],
        }
        for item in REVIEWER_DEFINITIONS
    ]
    return f"""# Digital Employees Report

## Scope

El termino empleado digital se implementa como revisor determinista, no como asistente ficticio, IA generativa ni chatbot.

## Reviewers

{_table(rows, ['revisor', 'modulo', 'responsabilidad'])}

## Execution Rules

- No inventar observaciones.
- Toda observacion exige evidencia.
- Toda propuesta queda como candidata y requiere decision humana.
- Ningun revisor modifica codigo, datos, produccion, Telegram o Stripe.

## Current State

{_table(_reviewer_rows(snapshot), ['revisor', 'estado', 'score', 'P0', 'P1', 'P2', 'P3', 'evidencia'])}
"""


def _matrix_report(snapshot: dict) -> str:
    rows = []
    for reviewer in snapshot.get("reviewers", []):
        for check in reviewer.get("evidence_checks", []):
            rows.append(
                {
                    "revisor": reviewer.get("name"),
                    "check": check.get("key"),
                    "estado": check.get("state"),
                    "evidencia": check.get("evidence"),
                }
            )
    return f"""# Quality Review Matrix

## Evidence Matrix

{_table(rows, ['revisor', 'check', 'estado', 'evidencia'])}

## Permanent Rule

Un reviewer sin evidencia no puede producir PASS. Un hallazgo sin modulo, pantalla, ruta, componente, evidencia, prioridad, impacto y propuesta no es valido.
"""


def _scorecard_report(snapshot: dict) -> str:
    rows = [
        {
            "revisor": reviewer.get("name"),
            "score": reviewer.get("score"),
            "explicacion": "; ".join(reviewer.get("score_explanation") or []),
        }
        for reviewer in snapshot.get("reviewers", [])
    ]
    return f"""# Product Scorecard

## Global Score

{snapshot['score']}/100

## Why

{'; '.join(snapshot.get('score_explanation') or ['Media explicable por revisor.'])}

## Reviewer Scores

{_table(rows, ['revisor', 'score', 'explicacion'])}

## Finding Summary

```json
{json.dumps(snapshot['findings_summary'], indent=2, ensure_ascii=False)}
```
"""


def _team_report(snapshot: dict) -> str:
    return f"""# World Class Product Team

## Mission

Mantener NeMeSiS en mejora continua mediante una revision profesional, evidence-first y sin ejecucion automatica.

## Operating Model

1. Observar el producto.
2. Registrar evidencia.
3. Clasificar prioridad.
4. Medir impacto de usuario y negocio.
5. Proponer mejora.
6. Convertir solo si existe aprobacion humana.
7. Validar con QA antes de cerrar.

## Current Product Team State

{_table(_reviewer_rows(snapshot), ['revisor', 'estado', 'score', 'P0', 'P1', 'P2', 'P3', 'evidencia'])}

## Next Recommendation

{snapshot['next_action']}
"""


def write_reports(snapshot: dict) -> None:
    REPORTS["system"].write_text(_system_report(snapshot), encoding="utf-8")
    REPORTS["employees"].write_text(_employees_report(snapshot), encoding="utf-8")
    REPORTS["matrix"].write_text(_matrix_report(snapshot), encoding="utf-8")
    REPORTS["scorecard"].write_text(_scorecard_report(snapshot), encoding="utf-8")
    REPORTS["team"].write_text(_team_report(snapshot), encoding="utf-8")


def _validate_snapshot(snapshot: dict) -> list[str]:
    errors: list[str] = []
    if snapshot.get("contract") != PRODUCT_REVIEW_SYSTEM_CONTRACT:
        errors.append("Product Review System contract mismatch")
    if snapshot.get("center_contract") != PRODUCT_REVIEW_CENTER_CONTRACT:
        errors.append("Product Review Center contract mismatch")
    if snapshot.get("quality_team_contract") != QUALITY_TEAM_CONTRACT:
        errors.append("Quality team contract mismatch")
    if snapshot.get("reviewer_count") != len(REVIEWER_DEFINITIONS):
        errors.append("Reviewer count mismatch")
    if snapshot.get("no_generative_ai") is not True or snapshot.get("no_chatbot") is not True:
        errors.append("Generative AI/chatbot guardrail missing")
    if snapshot.get("production_modified") or snapshot.get("deploy_executed") or snapshot.get("push_executed"):
        errors.append("Dangerous execution flag enabled")

    guardrails = snapshot.get("guardrails") or {}
    expected_safe = {
        "generative_ai_calls": 0,
        "external_calls": 0,
        "database_writes": 0,
        "telegram_sends": 0,
        "stripe_calls": 0,
        "chatbot_created": False,
        "production_modified": False,
        "automatic_improvements": False,
        "automatic_commits": False,
        "automatic_push": False,
        "automatic_deploy": False,
    }
    for key, expected in expected_safe.items():
        if guardrails.get(key) != expected:
            errors.append(f"Unsafe guardrail {key}: {guardrails.get(key)!r}")

    for reviewer in snapshot.get("reviewers", []):
        score = reviewer.get("score")
        if not isinstance(score, int) or not 0 <= score <= 100:
            errors.append(f"Invalid score for {reviewer.get('name')}")
        if not reviewer.get("score_explanation"):
            errors.append(f"Missing score explanation for {reviewer.get('name')}")
        if not reviewer.get("evidence_checks"):
            errors.append(f"Missing evidence checks for {reviewer.get('name')}")

    for finding in snapshot.get("findings", []):
        missing = [field for field in REQUIRED_FINDING_FIELDS if not finding.get(field)]
        if missing:
            errors.append(f"Finding missing fields {missing}: {finding.get('id')}")
        if finding.get("priority") not in {"P0", "P1", "P2", "P3"}:
            errors.append(f"Invalid priority in finding {finding.get('id')}")

    for candidate in snapshot.get("roadmap_candidates", []):
        if candidate.get("approved") is not False:
            errors.append(f"Roadmap candidate is pre-approved: {candidate.get('id')}")
        if candidate.get("automatic_execution_allowed") is not False:
            errors.append(f"Roadmap candidate allows automatic execution: {candidate.get('id')}")
        if candidate.get("requires_human_approval") is not True:
            errors.append(f"Roadmap candidate lacks human approval gate: {candidate.get('id')}")
    return errors


def _validate_integration() -> list[str]:
    errors: list[str] = []
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item.get("key"): item for item in registry.get("capabilities", [])}
    if (capabilities.get("product_review_system") or {}).get("state") != "INTEGRATED":
        errors.append("Sports platform registry does not expose product_review_system as INTEGRATED")

    roadmap = build_product_roadmap(ROOT)
    modules = {item.get("name"): item for item in roadmap.get("modules", [])}
    if (modules.get("Product Review System") or {}).get("state") != "COMPLETED":
        errors.append("Product roadmap does not mark Product Review System as COMPLETED")

    for relative in [
        "engines/product_review_system_engine.py",
        "templates/admin_product_review_center.html",
        "tools/check_product_review_system.py",
        "tests/test_product_review_system.py",
    ]:
        if not (ROOT / relative).is_file():
            errors.append(f"Missing required file: {relative}")

    engine_text = (ROOT / "engines" / "product_review_system_engine.py").read_text(encoding="utf-8")
    if UNSAFE_ENGINE_RE.search(engine_text):
        errors.append("Product Review System engine contains unsafe import or executable call")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args()

    snapshot = build_product_review_system_snapshot(ROOT)
    if args.write_reports:
        write_reports(snapshot)
        snapshot = build_product_review_system_snapshot(ROOT)

    errors = _validate_snapshot(snapshot)
    errors.extend(_validate_integration())

    result = {
        "ok": not errors,
        "status": snapshot.get("status"),
        "score": snapshot.get("score"),
        "reviewer_count": snapshot.get("reviewer_count"),
        "findings_summary": snapshot.get("findings_summary"),
        "reports": {key: str(path.relative_to(ROOT)) for key, path in REPORTS.items()},
        "errors": errors,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
