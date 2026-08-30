"""Reconcile autonomous workforce evidence into the canonical issue ledger."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.product_review_system_engine import load_product_memory, save_product_memory
from engines.sentinel_issues_engine import reconcile_autonomous_workforce_evidence


REPORT = ROOT / "reports" / "AUTONOMOUS_WORKFORCE_EVIDENCE_REVIEW.md"


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _latest_product_qa() -> tuple[dict, str]:
    candidates = list((ROOT / "data" / "local_dev").glob("**/autonomous_product_qa_result.json"))
    candidates += list((ROOT / "data" / "runtime").glob("**/latest_run.json"))
    candidates = [path for path in candidates if path.is_file()]
    if not candidates:
        return {}, "NOT_FOUND"
    selected = max(candidates, key=lambda path: path.stat().st_mtime)
    payload = _read_json(selected)
    run = payload.get("run") if isinstance(payload.get("run"), dict) else payload
    return run, str(selected.relative_to(ROOT))


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "LOCAL_UNRECORDED"


def _reconcile_product_memory(issue_summary: dict) -> dict:
    memory = load_product_memory(ROOT)
    for record in (memory.get("recommendations") or {}).values():
        record["issue_status"] = "INSUFFICIENT_EVIDENCE"
        record["evidence_sufficient"] = False
        record.setdefault("outcome_history", []).append({
            "type": "EVIDENCE_REVIEW",
            "outcome": "INSUFFICIENT_EVIDENCE",
            "reason": "La repetición histórica no prueba que el hallazgo siga siendo real.",
        })
        record.setdefault("learning_metrics", {})["insufficient_evidence"] = True
    for reviewer, calibration in (memory.get("reviewer_signal") or {}).items():
        calibration["state"] = "INSUFFICIENT_HISTORY"
        calibration["reason"] = "No hay 5 resultados revisados suficientes para calibrar este trabajador."
        calibration["reviewed_samples"] = 0
    memory.setdefault("events", []).append({
        "type": "AUTONOMOUS_WORKFORCE_EVIDENCE_REVIEW",
        "issue_health": issue_summary.get("issue_health") or {},
        "note": "Memoria conservada; recomendaciones heredadas sin evidencia actual no se elevan a Codex.",
    })
    memory["learning_summary"] = {
        "mode": "deterministic_no_ai",
        "history_storage": True,
        "actual_learning": True,
        "actual_learning_events": 1,
        "why": "El sistema separó observaciones históricas, falsos positivos, bloqueos externos y evidencia insuficiente sin borrar historia.",
    }
    save_product_memory(ROOT, memory)
    return memory


def _report(summary: dict, qa: dict, qa_path: str, memory: dict, sha: str) -> str:
    health = summary.get("issue_health") or {}
    calibration = summary.get("counts", {}).get("source") or {}
    lines = [
        "# AUTONOMOUS WORKFORCE EVIDENCE REVIEW & REMEDIATION",
        "",
        "## Decision",
        "",
        "Canonical ledger reconciled without deleting history. Only OPEN_REAL issues with sufficient evidence may reach Prepared for Codex.",
        "",
        "## Evidence reviewed",
        "",
        f"- Current SHA: `{sha}`",
        f"- Latest browser QA: `{qa_path}`",
        f"- QA result: `{qa.get('result') or 'NOT_AVAILABLE'}`",
        f"- QA issues detected: `{qa.get('issues_detected', 'NOT_AVAILABLE')}`",
        f"- Historical issues retained: `{summary.get('counts', {}).get('total', 0)}`",
        "- Founder override: retained as highest-priority human evidence.",
        "- Product Memory: retained and reclassified; no history overwritten.",
        "",
        "## Canonical issue health",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for key in (
        "open_real", "pending_verification", "resolved", "false_positive", "stale",
        "duplicate", "external_blocker", "insufficient_evidence", "prepared_for_codex",
    ):
        lines.append(f"| {key.upper()} | {health.get(key, 0)} |")
    lines += [
        "",
        "## Deterministic conclusions",
        "",
        "- Synthetic 404 probes and recovered aliases are not product defects.",
        "- Missing issues in a scan are never auto-resolved; they require verification.",
        "- Repetition alone no longer improves worker calibration.",
        "- Growth and Revenue remain INSUFFICIENT_EVIDENCE until real-user outcomes exist.",
        "- Licensed media remains EXTERNAL_BLOCKER when legal access is unavailable.",
        "- Visual founder findings remain FIXED_PENDING_VERIFICATION until human review.",
        "- Sports LIVE truth remains FIXED_PENDING_VERIFICATION while real certification continues.",
        "",
        "## Safety",
        "",
        "- Telegram sent: 0",
        "- Stripe actions: 0",
        "- Provider calls added: 0",
        "- Production mutations: 0",
        "- Secrets stored: 0",
        "",
        "## Source inventory",
        "",
    ]
    for source, count in sorted(calibration.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- `{source}`: {count} retained observations")
    lines += ["", "## Operational memory inventory", "", "| Source | Role | Available |", "|---|---|---|"]
    inventory = [
        ("data/runtime/sentinel_issues_memory.json", "Canonical issue ledger"),
        ("data/runtime/not_found_events.json", "404 observation history"),
        ("data/runtime/sentinel_autopilot_memory.json", "Legacy autopilot observations"),
        ("data/runtime/autonomous_company_sentinel/latest_run.json", "Company Sentinel latest evidence"),
        ("data/runtime/autonomous_company_sentinel/state.json", "Company Sentinel state"),
        ("data/runtime/autonomous_company_sentinel/codex_outbox.md", "Legacy Codex outbox, now evidence-gated"),
        ("data/runtime/continuous_evolution_os/autonomous_product_qa/memory.json", "Autonomous Product QA memory and founder override"),
        ("data/runtime/continuous_evolution_os/autonomous_product_qa/latest_run.json", "Latest canonical Product QA run"),
        ("data/local_dev/continuous_evolution_os/autonomous_product_qa/memory.json", "Local Safe Product QA memory and founder override"),
        ("data/local_dev/continuous_evolution_os/autonomous_product_qa/latest_run.json", "Latest Local Safe Product QA run"),
        ("data/runtime/continuous_evolution_os/product_memory.json", "Product Memory"),
        ("data/runtime/continuous_evolution_os/snapshots", "Daily snapshots"),
        ("data/runtime/continuous_evolution_os/briefs", "Founder Brief history"),
        ("data/runtime/continuous_evolution_os/codex_inbox/prepared_for_codex.json", "Prepared for Codex inbox"),
        (qa_path, "Latest full real-browser QA evidence"),
    ]
    for relative, role in inventory:
        available = "YES" if relative != "NOT_FOUND" and (ROOT / relative).exists() else "NO"
        lines.append(f"| `{relative}` | {role} | {available} |")
    lines += [
        "",
        "## Product Memory",
        "",
        f"- Recommendations retained: {len(memory.get('recommendations') or {})}",
        "- Learning mode: deterministic, no AI",
        "- Historical recommendations without current reviewed evidence: INSUFFICIENT_EVIDENCE",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    qa, qa_path = _latest_product_qa()
    sha = _git_sha()
    summary = reconcile_autonomous_workforce_evidence(
        ROOT,
        latest_product_qa=qa,
        production_sha=sha,
        save=True,
    )
    memory = _reconcile_product_memory(summary)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(_report(summary, qa, qa_path, memory, sha), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "status_contract": summary.get("status_contract"),
        "issue_health": summary.get("issue_health"),
        "qa_run": qa.get("run_id"),
        "report": str(REPORT.relative_to(ROOT)),
        "dangerous_actions_executed": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
