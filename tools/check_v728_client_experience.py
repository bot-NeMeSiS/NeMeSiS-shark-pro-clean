#!/usr/bin/env python3
"""Current client experience + Madrid-time QA using the canonical client guard."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.client_experience_guard_engine import client_experience_snapshot

REPORTS = ROOT / "reports"


def scan_templates() -> dict:
    snapshot = client_experience_snapshot(ROOT)
    findings = []
    filter_coverage = {}
    for screen in snapshot.get("critical_screens", []):
        name = str(screen.get("template") or "")
        filter_coverage[name] = {
            "uses_madrid_filters": bool(screen.get("uses_madrid_filters")),
            "needs_time_filter": bool(screen.get("needs_time_filter")),
            "time_status_ok": bool(screen.get("time_status_ok")),
        }
        if not screen.get("exists"):
            findings.append({"file": name, "severity": "error", "issue": "template_missing"})
        elif screen.get("needs_time_filter") and not screen.get("time_status_ok"):
            findings.append({"file": name, "severity": "error", "issue": "missing_madrid_time_filter"})
    for item in snapshot.get("findings", []):
        findings.append({
            "file": item.get("template"),
            "severity": "warning" if item.get("severity") == "WARN" else "info",
            "issue": item.get("category") or "review",
            "pattern": item.get("pattern") or "",
        })
    hard_errors = [item for item in findings if item["severity"] == "error"]
    return {
        "ok": not hard_errors and snapshot.get("status") == "OK",
        "score": snapshot.get("score"),
        "status": snapshot.get("status"),
        "findings": findings,
        "hard_errors": hard_errors,
        "filter_coverage": filter_coverage,
        "critical_screens": snapshot.get("critical_screens", []),
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# V728 Visual + Madrid Time QA",
        "",
        f"- Resultado: {'OK' if report['ok'] else 'REVISAR'}",
        f"- Guard cliente: `{report.get('score')}/100 · {report.get('status')}`",
        f"- Pantallas críticas revisadas: `{len(report.get('critical_screens') or [])}`",
        f"- Hallazgos: `{len(report.get('findings') or [])}`",
        f"- Errores: `{len(report.get('hard_errors') or [])}`",
        "",
        "## Cobertura Madrid",
    ]
    for item in report.get("critical_screens", []):
        lines.append(
            f"- `{item.get('route')}` → `{item.get('template')}` · "
            f"exists=`{str(bool(item.get('exists'))).lower()}` · "
            f"time_ok=`{str(bool(item.get('time_status_ok'))).lower()}`"
        )
    informational = [item for item in report.get("findings", []) if item.get("severity") != "error"]
    if informational:
        lines.extend(["", "## Hallazgos informativos"])
        for item in informational[:80]:
            lines.append(
                f"- `{item.get('file')}` · {item.get('severity')} · "
                f"{item.get('issue')} {item.get('pattern','')}"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    report = scan_templates()
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "V728_VISUAL_TIME_QA_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = render_markdown(report)
    (REPORTS / "V728_VISUAL_TIME_QA_REPORT.md").write_text(markdown, encoding="utf-8")
    (ROOT / "V728_VISUAL_TIME_QA_REPORT.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({
        "ok": report["ok"],
        "score": report["score"],
        "status": report["status"],
        "findings": len(report["findings"]),
        "hard_errors": len(report["hard_errors"]),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
