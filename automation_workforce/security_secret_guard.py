"""Compatibility Secret Guard backed by the V938 redacted scanner."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_repository_privacy_and_secrets import scan_repository
from automation_workforce.common import write_report


ROOT = Path(__file__).resolve().parents[1]


def run_security_secret_guard(dry_run: bool = True, root: str | Path = ROOT) -> dict[str, Any]:
    result = scan_repository(root, include_privacy=False)
    findings = result.get("secret_findings") or []
    payload = {
        "version": (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig", errors="replace").strip(),
        "ok": not findings,
        "status": "ok" if not findings else "blocked_secret_findings",
        "dry_run": bool(dry_run),
        "files_scanned": int(result.get("files_scanned") or 0),
        "findings_count": len(findings),
        "findings": [
            {
                "path": item.get("path"),
                "line": item.get("line"),
                "type": item.get("type"),
                "severity": item.get("severity"),
                "classification": item.get("classification"),
                "value_hash_prefix": item.get("value_hash_prefix"),
                "value_redacted": True,
            }
            for item in findings
        ],
        "values_printed": False,
        "dangerous_actions_executed": False,
        "safe_message": "Secret Guard revisado sin imprimir valores, sin red y sin modificar produccion.",
    }
    if Path(root).resolve() == ROOT.resolve():
        write_report(
            "V915_SECURITY_SECRET_GUARD_REPORT.md",
            "V915 Security Secret Guard Report",
            payload,
            [
                "- Motor oficial: escaner redactado V938.",
                f"- Archivos revisados: `{payload['files_scanned']}`.",
                f"- Hallazgos confirmados: `{payload['findings_count']}`.",
                "- Valores impresos: `False`.",
                "- Acciones externas o destructivas: `False`.",
            ],
        )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="NeMeSiS Security Secret Guard")
    parser.add_argument("--dry-run", action="store_true", default=True)
    args = parser.parse_args()
    result = run_security_secret_guard(dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
