#!/usr/bin/env python3
"""Audit the project tree and classify files before release."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.codex_daily_automation_engine import audit_tree

REPORT_DIR = ROOT / "reports"


def markdown(report: dict) -> str:
    lines = [
        "# Auditoría de árbol V723",
        "",
        f"- Raíz: `{report['root']}`",
        f"- Archivos: {report['total_files']}",
        f"- Tamaño total: {report['total_size_bytes']} bytes",
        "",
        "## Clasificación",
    ]
    for key, value in report["counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Basura segura detectada"])
    for item in report["safe_trash"][:100]:
        lines.append(f"- `{item['path']}` ({item['reason']})")
    if not report["safe_trash"]:
        lines.append("- Sin basura segura relevante.")
    lines.extend(["", "## Revisar manualmente"])
    for item in report["review"][:100]:
        lines.append(f"- `{item['path']}` ({item['reason']})")
    if not report["review"]:
        lines.append("- Sin elementos dudosos principales.")
    lines.extend(["", "## Carpetas más pesadas"])
    for item in report["largest_folders"][:15]:
        lines.append(f"- `{item['path']}`: {item['size']} bytes")
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORT_DIR.mkdir(exist_ok=True)
    report = audit_tree(ROOT)
    (REPORT_DIR / "PROJECT_TREE_AUDIT_V723.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (REPORT_DIR / "PROJECT_TREE_AUDIT_V723.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "total_files": report["total_files"],
        "counts": report["counts"],
        "safe_trash": len(report["safe_trash"]),
        "review": len(report["review"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
