from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


WORKERS = {
    "canonical": {
        "report": "reports/V933_COMPONENT_CONSISTENCY_QA.md",
        "files": ["templates/components/v933_ui.html", "templates/components/v933_navigation.html", "static/v933-product.css"],
        "tokens": ["v933-page", "macro kpi_card", "v933-mobile-bottom-nav", "v933-admin-sidebar"],
    },
    "admin": {
        "report": "reports/V933_ADMIN_UI_QA.md",
        "files": ["templates/admin_dashboard.html", "templates/admin_telegram_command_center.html", "templates/admin_picks.html"],
        "tokens": ["data-v933-template", "v933-admin-command-center", "v933-kpi-grid"],
    },
    "client_desktop": {
        "report": "reports/V933_CLIENT_DESKTOP_QA.md",
        "files": ["templates/client_app_center.html", "templates/calendar.html", "templates/live.html", "templates/picks.html"],
        "tokens": ["v933-two-col", "v933-sports-board", "v933-picks-board"],
    },
    "client_mobile": {
        "report": "reports/V933_CLIENT_MOBILE_QA.md",
        "files": ["templates/components/v933_navigation.html", "static/v933-product.css"],
        "tokens": ["v933-mobile-header", "v933-mobile-bottom-nav", "max-width: 800px", "safe-area-inset-bottom"],
    },
    "components": {
        "report": "reports/V933_COMPONENT_CONSISTENCY_QA.md",
        "files": ["templates/components/v933_ui.html"],
        "tokens": ["macro kpi_card", "macro match_card", "macro pick_card", "macro empty_state", "macro provider_state"],
    },
    "real_data": {
        "report": "reports/V933_REAL_DATA_PRESENTATION_QA.md",
        "files": ["templates/admin_picks.html", "templates/admin_automation_center.html", "templates/track_record.html", "templates/home.html"],
        "tokens": ["Sin dato", "Sin pick", "datos reales"],
        "forbidden": ["Arsenal vs Chelsea", "48.732", "125.684", "€18.732", "Real Madrid vs Borussia Dortmund"],
    },
    "responsive": {
        "report": "reports/V933_CLIENT_MOBILE_QA.md",
        "files": ["static/v933-product.css"],
        "tokens": ["max-width: 430px", "max-width: 800px", "max-width: 1180px", "safe-area-inset-bottom", "overflow-x: auto"],
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
