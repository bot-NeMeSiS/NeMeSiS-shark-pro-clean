#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "V832_GITHUB_RENDER_CODEX_AUTOMATION_WORKFLOW.md"


def main() -> int:
    text = REPORT.read_text(encoding="utf-8", errors="replace") if REPORT.exists() else ""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="replace") if (ROOT / ".gitignore").exists() else ""
    checks = {
        "report_exists": REPORT.exists(),
        "source_of_truth": "C:\\Users\\aloha\\OneDrive\\Escritorio\\NeMeSiS shark pro" in text,
        "github_desktop": "GitHub Desktop" in text,
        "render_runtime": "/api/runtime-version" in text and "/api/automation/master-tick" in text,
        "rollback": "Rollback" in text or "rollback" in text,
        "gitignore_db": "*.db" in gitignore and ".env" in gitignore,
        "gitignore_release": "release_output/" in gitignore and "*.zip" in gitignore,
    }
    ok = all(checks.values())
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
