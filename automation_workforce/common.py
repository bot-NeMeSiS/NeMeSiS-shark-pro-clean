from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
RUNTIME = ROOT / "data" / "runtime" / "autonomous_company_sentinel"
OUTBOX = RUNTIME / "outbox" / "codex_outbox.md"
VERSION = "V919_BROWSER_QA_RESULTS_IMPORT_VALIDATION_AND_VISUAL_QUEUE_GATE_FINAL"


def madrid_now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_text(rel: str, default: str = "") -> str:
    path = ROOT / rel
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_report(name: str, title: str, payload: dict[str, Any], lines: list[str] | None = None) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / name
    body = [f"# {title}", "", f"- Generado: `{madrid_now_iso()}`", f"- Version: `{payload.get('version') or VERSION}`", ""]
    for key, value in payload.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            body.append(f"- {key}: `{value}`")
    if lines:
        body.extend(["", "## Detalle", *lines])
    body.extend(["", "## Politica", "- No expone secretos.", "- No envia Telegram real.", "- No toca pagos ni DB real destructivamente.", "- No declara produccion sin runtime real."])
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def mask_secret(value: str | None) -> str:
    if not value:
        return "***missing***"
    return "***configured***"


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def python_executable() -> str:
    candidate = ROOT / ".venv" / "Scripts" / "python.exe"
    return str(candidate) if candidate.exists() else sys.executable


def run_command(args: list[str], timeout: int = 120) -> dict[str, Any]:
    try:
        result = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
        return {
            "command": " ".join(args),
            "returncode": result.returncode,
            "ok": result.returncode == 0,
            "stdout_tail": (result.stdout or "")[-3000:],
            "stderr_tail": (result.stderr or "")[-3000:],
        }
    except Exception as exc:
        return {"command": " ".join(args), "returncode": -1, "ok": False, "error": str(exc)[:500]}


def version_identity() -> dict[str, Any]:
    return {
        "version": read_text("VERSION.txt").strip().lstrip("\ufeff"),
        "app_version": read_text("APP_VERSION").strip().lstrip("\ufeff"),
        "app_py_has_version": read_text("app.py").find(read_text("VERSION.txt").strip().lstrip("\ufeff")) >= 0,
    }


def workflow_arg_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true", default=True)
    return parser


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
