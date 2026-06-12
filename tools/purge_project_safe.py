#!/usr/bin/env python3
"""Safe purge helper for generated trash. Defaults to dry-run."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.audit_project_tree import audit_tree

REPORT_DIR = ROOT / "reports"
PROTECTED_DIRS = {".git", ".venv", "venv", "env", "release_output", "release", "releases"}


def should_delete_item(item: dict, include_venv: bool = False) -> bool:
    path = Path(item["path"])
    parts = set(path.parts)
    if parts & PROTECTED_DIRS and not include_venv:
        return False
    return item.get("category") == "BASURA_SEGURA" and bool(item.get("auto_delete"))


def delete_path(path: Path) -> dict:
    if not path.exists():
        return {"path": str(path), "status": "missing"}
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return {"path": str(path), "status": "deleted"}


def markdown(result: dict) -> str:
    lines = [
        "# Purga segura V726",
        "",
        f"- Modo: {result['mode']}",
        f"- Candidatos: {len(result['candidates'])}",
        f"- Ejecutados: {len(result['actions'])}",
        "",
        "## Candidatos",
    ]
    for item in result["candidates"][:200]:
        lines.append(f"- `{item['path']}`: {item['reason']}")
    lines.append("")
    lines.append("## Acciones")
    if result["actions"]:
        for item in result["actions"][:200]:
            lines.append(f"- `{item['path']}`: {item['status']}")
    else:
        lines.append("- No se eliminó nada.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Elimina los candidatos seguros.")
    parser.add_argument("--dry-run", action="store_true", help="Solo lista candidatos.")
    parser.add_argument("--include-venv", action="store_true", help="Permite eliminar entornos virtuales.")
    args = parser.parse_args()
    mode = "apply" if args.apply else "dry-run"
    report = audit_tree(ROOT)
    candidates = [item for item in report["items"] if should_delete_item(item, include_venv=args.include_venv)]
    actions = []
    if args.apply:
        for item in candidates:
            actions.append(delete_path(ROOT / item["path"]))
    result = {
        "ok": True,
        "mode": mode,
        "include_venv": bool(args.include_venv),
        "candidates": candidates,
        "actions": actions,
        "note": "Por defecto no elimina .venv para no romper la validación local de Codex.",
    }
    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "V726_PURGE_REPORT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md = markdown(result)
    (REPORT_DIR / "V726_PURGE_REPORT.md").write_text(md, encoding="utf-8")
    (ROOT / "V726_PURGE_REPORT.md").write_text(md, encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "mode": mode,
        "candidates": len(candidates),
        "actions": len(actions),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
