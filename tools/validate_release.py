"""Release validation helper for NeMeSiS SHARK PRO.

Run from project root:
    python tools/validate_release.py
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]


def run_step(label: str, command: list[str]) -> int:
    print(f"[VALIDATE] {label}")
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        print(f"[ERROR] {label} falló con código {result.returncode}")
    else:
        print(f"[OK] {label}")
    return result.returncode


def main() -> int:
    python = sys.executable
    steps = [
        ("py_compile app.py", [python, "-m", "py_compile", "app.py"]),
        ("compileall", [python, "-m", "compileall", "-q", "."]),
        ("smoke_check", [python, "tools/smoke_check.py"]),
    ]
    for label, command in steps:
        code = run_step(label, command)
        if code:
            return code

    if importlib.util.find_spec("pytest") is None:
        print("[ERROR] pytest no está instalado. Ejecuta:")
        print("        pip install -r requirements.txt")
        print("        pytest -q")
        return 1

    return run_step("pytest -q", [python, "-m", "pytest", "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
