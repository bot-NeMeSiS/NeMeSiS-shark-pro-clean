#!/usr/bin/env python3
"""Validate and report the NeMeSiS Executive Board."""
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
    EXECUTIVE_BOARD_CENTER_CONTRACT,
    EXECUTIVE_BOARD_CONTRACT,
    EXECUTIVE_DIRECTOR_DEFINITIONS,
    EXECUTIVE_REQUIRED_PROPOSAL_FIELDS,
    EXECUTIVE_VOTE_LEVELS,
    STRATEGIC_DECISION_CONTRACT,
    build_executive_board_snapshot,
)
from engines.project_operating_system_engine import build_product_roadmap  # noqa: E402
from engines.sports_platform_contracts import build_sports_platform_contract_registry  # noqa: E402

REPORTS = {
    "board": ROOT / "reports" / "EXECUTIVE_BOARD_REPORT.md",
    "governance": ROOT / "reports" / "PRODUCT_GOVERNANCE_REPORT.md",
    "matrix": ROOT / "reports" / "EXECUTIVE_DECISION_MATRIX.md",
    "roadmap": ROOT / "reports" / "STRATEGIC_ROADMAP_REPORT.md",
    "health": ROOT / "reports" / "PRODUCT_HEALTH_REPORT.md",
}

UNSAFE_GOVERNANCE_RE = re.compile(
    r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe|openai|subprocess|selenium|playwright)\b"
    r"|\b(?:urlopen|Session|post|put|delete)\s*\(",
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


def _director_rows(snapshot: dict) -> list[dict[str, object]]:
    return [
        {
            "director": item.get("name"),
            "area": item.get("area"),
            "estado": item.get("state"),
            "score": item.get("score"),
            "hallazgos": item.get("findings_count"),
            "apoya": ", ".join(item.get("supported_candidates") or []),
            "rechaza": ", ".join(item.get("rejected_candidates") or []),
        }
        for item in snapshot.get("directors", [])
    ]


def _decision_rows(snapshot: dict, limit: int | None = None) -> list[dict[str, object]]:
    rows = []
    candidates = snapshot.get("decision_matrix", [])
    if limit:
        candidates = candidates[:limit]
    for item in candidates:
        rows.append(
            {
                "id": item.get("id"),
                "prioridad": item.get("priority"),
                "clasificacion": item.get("board_classification"),
                "modulo": item.get("module"),
                "pantalla": item.get("screen"),
                "ruta": item.get("route"),
                "coste": item.get("estimated_cost"),
                "riesgo": item.get("risk"),
                "apoyan": ", ".join(item.get("supporters") or []),
                "rechazan": ", ".join(item.get("rejecters") or []),
                "evidencia": item.get("evidence"),
            }
        )
    return rows


def _score_rows(snapshot: dict) -> list[dict[str, object]]:
    return [
        {
            "area": item.get("label"),
            "score": item.get("score"),
            "estado": item.get("state"),
            "justificacion": item.get("justification"),
            "evidencia": ", ".join(item.get("evidence") or []),
        }
        for item in snapshot.get("product_scores", [])
    ]


def _board_report(snapshot: dict) -> str:
    return f"""# Executive Board Report

## Decision

PASS LOCAL.

El Executive Board queda creado como Consejo de Direccion interno read-only sobre el Product Review System. No es chatbot, no usa IA generativa, no aprueba mejoras automaticamente, no modifica produccion, no hace commit, no hace push y no hace deploy.

## Contracts

- {EXECUTIVE_BOARD_CONTRACT}
- {EXECUTIVE_BOARD_CENTER_CONTRACT}
- {STRATEGIC_DECISION_CONTRACT}

## Executive Summary

- Estado: {snapshot['status']}
- Score Board: {snapshot['board_score']}/100
- Directores: {snapshot['director_count']} de {snapshot['directors_expected']}
- Propuestas: {snapshot['proposal_summary']}
- Entorno: {snapshot['environment']}

## Directors

{_table(_director_rows(snapshot), ['director', 'area', 'estado', 'score', 'hallazgos', 'apoya', 'rechaza'])}

## Guardrails

```json
{json.dumps(snapshot['guardrails'], indent=2, ensure_ascii=False)}
```

## Next Action

{snapshot['next_action']}
"""


def _governance_report(snapshot: dict) -> str:
    rows = []
    for item in snapshot.get("backlog_updates", []):
        rows.append(
            {
                "id": item.get("id"),
                "fuente": item.get("source_id"),
                "TOP100": item.get("top100_status"),
                "Master": item.get("master_roadmap_status"),
                "Living": item.get("living_roadmap_status"),
                "aprobacion": "humana obligatoria" if item.get("human_approval_required") else "revisar",
            }
        )
    return f"""# Product Governance Report

## Scope

El gobierno de producto queda organizado en una cadena unica: Product Review observa, Executive Board prioriza, direccion humana decide, QA certifica. Ninguna mejora se ejecuta automaticamente.

## Backlog Sync

{_table(rows, ['id', 'fuente', 'TOP100', 'Master', 'Living', 'aprobacion'])}

## Rules

- Toda propuesta necesita evidencia.
- Toda propuesta necesita modulo, pantalla, ruta, impacto usuario, impacto negocio, coste, dependencias y riesgo.
- Los estados permitidos del backlog son Pendiente, En curso, Completada, Bloqueada y Descartada.
- El Top 10 es una recomendacion de priorizacion, no una aprobacion de ejecucion.
"""


def _matrix_report(snapshot: dict) -> str:
    return f"""# Executive Decision Matrix

## Top 10 Prioritized Improvements

{_table(_decision_rows(snapshot, limit=10), ['id', 'prioridad', 'clasificacion', 'modulo', 'pantalla', 'ruta', 'coste', 'riesgo', 'apoyan', 'rechazan', 'evidencia'])}

## Full Matrix

{_table(_decision_rows(snapshot), ['id', 'prioridad', 'clasificacion', 'modulo', 'pantalla', 'ruta', 'coste', 'riesgo', 'apoyan', 'rechazan', 'evidencia'])}

## Voting Rule

Cada director vota de forma independiente. La clasificacion final CRITICA, ALTA, MEDIA, BAJA o DESCARTADA se deriva de prioridad, area, riesgo y evidencia. No existe aprobacion automatica.
"""


def _roadmap_report(snapshot: dict) -> str:
    rows = []
    for item in snapshot.get("top_10_improvements", []):
        rows.append(
            {
                "id": item.get("id"),
                "estado": item.get("status"),
                "prioridad": item.get("priority"),
                "modulo": item.get("module"),
                "dependencias": ", ".join(item.get("dependencies") or []),
                "documentacion": "EXECUTIVE_DECISION_MATRIX / STRATEGIC_ROADMAP / PRODUCT_HEALTH",
            }
        )
    return f"""# Strategic Roadmap Report

## Active Strategic Shortlist

{_table(rows, ['id', 'estado', 'prioridad', 'modulo', 'dependencias', 'documentacion'])}

## Roadmap Rule

El Executive Board selecciona como maximo 10 mejoras para revision humana. No inicia sprints, no ejecuta codigo y no altera prioridades del Living Roadmap sin autorizacion.
"""


def _health_report(snapshot: dict) -> str:
    return f"""# Product Health Report

## Product Scores

{_table(_score_rows(snapshot), ['area', 'score', 'estado', 'justificacion', 'evidencia'])}

## Area Health

{_table(snapshot.get('area_health', []), ['label', 'score', 'state', 'evidence'])}

## Interpretation

Las puntuaciones se calculan desde directores y hallazgos del Product Review System. Son una lectura local de salud de producto, no una certificacion de produccion.
"""


def write_reports(snapshot: dict) -> None:
    REPORTS["board"].write_text(_board_report(snapshot), encoding="utf-8")
    REPORTS["governance"].write_text(_governance_report(snapshot), encoding="utf-8")
    REPORTS["matrix"].write_text(_matrix_report(snapshot), encoding="utf-8")
    REPORTS["roadmap"].write_text(_roadmap_report(snapshot), encoding="utf-8")
    REPORTS["health"].write_text(_health_report(snapshot), encoding="utf-8")


def _validate_snapshot(snapshot: dict) -> list[str]:
    errors: list[str] = []
    if snapshot.get("contract") != EXECUTIVE_BOARD_CONTRACT:
        errors.append("Executive Board contract mismatch")
    if snapshot.get("center_contract") != EXECUTIVE_BOARD_CENTER_CONTRACT:
        errors.append("Executive Board Center contract mismatch")
    if snapshot.get("decision_contract") != STRATEGIC_DECISION_CONTRACT:
        errors.append("Strategic Decision contract mismatch")
    if snapshot.get("director_count") != len(EXECUTIVE_DIRECTOR_DEFINITIONS):
        errors.append("Director count mismatch")
    if snapshot.get("directors_expected") != len(EXECUTIVE_DIRECTOR_DEFINITIONS):
        errors.append("Director expected count mismatch")
    if len(snapshot.get("top_10_improvements") or []) > 10:
        errors.append("Top 10 contains more than 10 items")
    if snapshot.get("no_chatbot") is not True or snapshot.get("no_generative_ai") is not True:
        errors.append("Chatbot/generative AI guardrail missing")
    if snapshot.get("automatic_execution_allowed") is not False or snapshot.get("no_automatic_decisions") is not True:
        errors.append("Automatic execution/decision guardrail missing")

    guardrails = snapshot.get("guardrails") or {}
    expected = {
        "generative_ai_calls": 0,
        "external_calls": 0,
        "database_writes": 0,
        "telegram_sends": 0,
        "stripe_calls": 0,
        "chatbot_created": False,
        "production_modified": False,
        "automatic_execution": False,
        "automatic_decisions": False,
        "automatic_push": False,
        "automatic_deploy": False,
        "commit_created": False,
    }
    for key, value in expected.items():
        if guardrails.get(key) != value:
            errors.append(f"Unsafe guardrail {key}: {guardrails.get(key)!r}")

    director_names = {item.get("name") for item in snapshot.get("directors", [])}
    expected_directors = {item["name"] for item in EXECUTIVE_DIRECTOR_DEFINITIONS}
    if director_names != expected_directors:
        errors.append("Director set mismatch")

    for director in snapshot.get("directors", []):
        if not director.get("what_works") or not director.get("what_does_not_work"):
            errors.append(f"Director lacks operating review: {director.get('name')}")
        if not director.get("should_not_touch"):
            errors.append(f"Director lacks no-touch guardrail: {director.get('name')}")

    for candidate in snapshot.get("decision_matrix", []):
        missing = [field for field in EXECUTIVE_REQUIRED_PROPOSAL_FIELDS if not candidate.get(field)]
        if missing:
            errors.append(f"Candidate {candidate.get('id')} missing fields {missing}")
        if candidate.get("approved") is not False:
            errors.append(f"Candidate is pre-approved: {candidate.get('id')}")
        if candidate.get("automatic_execution_allowed") is not False:
            errors.append(f"Candidate allows automatic execution: {candidate.get('id')}")
        if candidate.get("board_classification") not in EXECUTIVE_VOTE_LEVELS:
            errors.append(f"Invalid board classification: {candidate.get('id')}")
        vote_levels = {vote.get("classification") for vote in candidate.get("votes", [])}
        if not vote_levels.issubset(set(EXECUTIVE_VOTE_LEVELS)):
            errors.append(f"Invalid vote level in {candidate.get('id')}")
        if len(candidate.get("votes", [])) != len(EXECUTIVE_DIRECTOR_DEFINITIONS):
            errors.append(f"Vote count mismatch in {candidate.get('id')}")

    for score in snapshot.get("product_scores", []):
        if not isinstance(score.get("score"), int) or not 0 <= score.get("score") <= 100:
            errors.append(f"Invalid product score {score.get('label')}")
        if not score.get("justification"):
            errors.append(f"Missing product score justification {score.get('label')}")
    return errors


def _validate_integration() -> list[str]:
    errors: list[str] = []
    for relative in [
        "templates/admin_executive_board_center.html",
        "tools/check_executive_board.py",
        "tests/test_executive_board.py",
        "engines/product_review_system_engine.py",
    ]:
        if not (ROOT / relative).is_file():
            errors.append(f"Missing required file: {relative}")
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item.get("key"): item for item in registry.get("capabilities", [])}
    if (capabilities.get("executive_board") or {}).get("state") != "INTEGRATED":
        errors.append("Platform registry does not mark executive_board as INTEGRATED")
    roadmap = build_product_roadmap(ROOT)
    modules = {item.get("name"): item for item in roadmap.get("modules", [])}
    if (modules.get("Executive Board") or {}).get("state") != "COMPLETED":
        errors.append("Product roadmap does not mark Executive Board as COMPLETED")
    source = (ROOT / "engines" / "product_review_system_engine.py").read_text(encoding="utf-8")
    executive_section = source.split("EXECUTIVE_BOARD_CONTRACT", 1)[-1]
    if UNSAFE_GOVERNANCE_RE.search(executive_section):
        errors.append("Executive Board governance extension contains unsafe imports or calls")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args()

    snapshot = build_executive_board_snapshot(ROOT)
    if args.write_reports:
        write_reports(snapshot)
        snapshot = build_executive_board_snapshot(ROOT)

    errors = _validate_snapshot(snapshot)
    errors.extend(_validate_integration())
    result = {
        "ok": not errors,
        "status": snapshot.get("status"),
        "board_score": snapshot.get("board_score"),
        "director_count": snapshot.get("director_count"),
        "proposal_summary": snapshot.get("proposal_summary"),
        "top_10": [item.get("id") for item in snapshot.get("top_10_improvements", [])],
        "reports": {key: str(path.relative_to(ROOT)) for key, path in REPORTS.items()},
        "errors": errors,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
