from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


WORKERS = {
    "canonical": {
        "report": "reports/V928_COMPONENT_LIBRARY_QA.md",
        "files": ["templates/components/v928_ui.html", "templates/components/v928_navigation.html", "static/v928-canonical.css"],
        "tokens": ["v928-page", "v928-kpi-card", "v928-mobile-bottom-nav", "v928-admin-sidebar"],
    },
    "admin": {
        "report": "reports/V928_ADMIN_DESKTOP_REFERENCE_QA.md",
        "files": ["templates/admin_dashboard.html", "templates/admin_telegram_command_center.html", "templates/admin_picks.html"],
        "tokens": ["data-v928-template", "v928-admin-command-center", "v928-kpi-grid"],
    },
    "client_desktop": {
        "report": "reports/V928_CLIENT_DESKTOP_REFERENCE_QA.md",
        "files": ["templates/client_app_center.html", "templates/calendar.html", "templates/live.html", "templates/picks.html"],
        "tokens": ["v928-layout-main-aside", "v928-sports-board", "v928-picks-board"],
    },
    "client_mobile": {
        "report": "reports/V928_CLIENT_MOBILE_REFERENCE_QA.md",
        "files": ["templates/components/v928_navigation.html", "static/v928-canonical.css"],
        "tokens": ["v928-mobile-header", "v928-mobile-bottom-nav", "max-width: 820px"],
    },
    "components": {
        "report": "reports/V928_COMPONENT_LIBRARY_QA.md",
        "files": ["templates/components/v928_ui.html"],
        "tokens": ["macro kpi_card", "macro match_card", "macro pick_card", "macro empty_state", "macro provider_status"],
    },
    "real_data": {
        "report": "reports/V928_REAL_DATA_UI_GUARD_QA.md",
        "files": ["templates/admin_picks.html", "templates/admin_automation_center.html", "templates/track_record.html", "templates/home.html"],
        "tokens": ["Sin dato", "Sin pick", "datos reales"],
        "forbidden": ["Arsenal vs Chelsea", "48.732", "125.684", "€18.732", "Real Madrid vs Borussia Dortmund"],
    },
    "responsive": {
        "report": "reports/V928_RESPONSIVE_OVERFLOW_QA.md",
        "files": ["static/v928-canonical.css"],
        "tokens": ["max-width: 430px", "max-width: 820px", "max-width: 980px", "min-width: 1600px", "min-width: 1920px", "overflow-x: auto"],
    },
}


def text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def run_worker(kind: str) -> dict:
    spec = WORKERS[kind]
    findings: list[dict] = []
    combined = ""
    for relative in spec["files"]:
        path = ROOT / relative
        if not path.exists():
            findings.append({"severity": "high", "file": relative, "finding": "missing_file"})
            continue
        combined += "\n" + text(path)
    for token in spec.get("tokens", []):
        if token not in combined:
            findings.append({"severity": "medium", "finding": "missing_required_token", "token": token})
    for token in spec.get("forbidden", []):
        if token.lower() in combined.lower():
            findings.append({"severity": "high", "finding": "reference_demo_data_found", "token": token})
    tasks = [
        {
            "action": "CODEX_PROMPT_REQUIRED" if item["severity"] == "high" else "SAFE_AUTOFIX",
            "recommendation": f"Review {item.get('file') or item.get('token') or item.get('finding')}",
        }
        for item in findings
    ]
    return {
        "worker": kind,
        "status": "ok" if not findings else "review_required",
        "ok": not findings,
        "safe_message": "Static canonical-reference review completed; no production action was performed.",
        "findings": findings,
        "tasks": tasks,
        "next_action": "none" if not findings else "review_findings",
        "report_path": spec["report"],
        "dry_run": True,
    }


def cli(kind: str) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.parse_args()
    result = run_worker(kind)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["ok"] else 1

