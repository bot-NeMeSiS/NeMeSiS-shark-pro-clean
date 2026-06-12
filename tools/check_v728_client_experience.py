#!/usr/bin/env python3
"""Static QA checks for V728 client experience, Madrid time and release cleanliness."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
REPORTS = ROOT / "reports"
CLIENT_TEMPLATES = {
    "home.html", "client_overview.html", "sports_hub.html", "live.html", "calendar.html",
    "picks.html", "combis.html", "shark.html", "telegram.html", "favorites.html",
    "profile.html", "match_detail.html", "match_hub.html", "team_detail.html", "smart_dashboard.html",
    "unified_intelligence_hub.html", "daily_briefing.html",
}
RAW_TIME_PATTERNS = [
    r"kickoff_time\s*\}\}", r"match_time\s*\}\}", r"kickoff_iso\s*\}\}",
    r"commence_time\s*\}\}", r"\+00:00", r"\bUTC\b", r"undefined", r"\bnull\b",
]
REQUIRED_FILTER_FILES = {"sports_hub.html", "live.html", "calendar.html", "match_detail.html", "picks.html", "combis.html"}


def scan_templates() -> dict:
    findings = []
    filter_coverage = {}
    for name in sorted(CLIENT_TEMPLATES):
        path = TEMPLATES / name
        if not path.exists():
            findings.append({"file": name, "severity": "warning", "issue": "template_missing"})
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        filter_coverage[name] = {
            "match_time_short": "match_time_short" in text,
            "match_time_label": "match_time_label" in text,
            "match_date_label": "match_date_label" in text,
        }
        for pattern in RAW_TIME_PATTERNS:
            if re.search(pattern, text, flags=re.I):
                findings.append({"file": name, "severity": "review", "issue": "possible_raw_time_or_placeholder", "pattern": pattern})
    missing_required_filters = [name for name in REQUIRED_FILTER_FILES if not any(filter_coverage.get(name, {}).values())]
    for name in missing_required_filters:
        findings.append({"file": name, "severity": "error", "issue": "missing_madrid_time_filter"})
    return {"findings": findings, "filter_coverage": filter_coverage, "missing_required_filters": missing_required_filters}


def render_markdown(report: dict) -> str:
    lines = [
        "# V728 Visual + Madrid Time QA",
        "",
        f"- Resultado: {'OK' if report['ok'] else 'REVISAR'}",
        f"- Templates cliente revisados: {len(CLIENT_TEMPLATES)}",
        f"- Hallazgos: {len(report['findings'])}",
        "",
        "## Cobertura filtros Madrid",
    ]
    for name, coverage in sorted(report["filter_coverage"].items()):
        used = ", ".join(k for k, v in coverage.items() if v) or "sin filtro directo"
        lines.append(f"- `{name}`: {used}")
    if report["findings"]:
        lines.extend(["", "## Hallazgos a revisar"])
        for item in report["findings"][:80]:
            lines.append(f"- `{item['file']}` · {item['severity']} · {item['issue']} {item.get('pattern','')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    template_report = scan_templates()
    hard_errors = [f for f in template_report["findings"] if f["severity"] == "error"]
    report = {"ok": not hard_errors, **template_report}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "V728_VISUAL_TIME_QA_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(report)
    (REPORTS / "V728_VISUAL_TIME_QA_REPORT.md").write_text(markdown, encoding="utf-8")
    (ROOT / "V728_VISUAL_TIME_QA_REPORT.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "findings": len(report["findings"]), "hard_errors": len(hard_errors)}, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
