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


def run_step(label: str, command: list[str], required: bool = True) -> int:
    print(f"[VALIDATE] {label}")
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        level = "ERROR" if required else "WARN"
        print(f"[{level}] {label} falló con código {result.returncode}")
        return result.returncode if required else 0
    print(f"[OK] {label}")
    return 0


def latest_release_zip() -> pathlib.Path | None:
    search_dirs = [ROOT.parent / "releases", ROOT / "release_output", ROOT]
    zips = []
    for directory in search_dirs:
        if directory.exists():
            zips.extend(directory.glob("*RENDER_READY.zip"))
    zips = sorted(zips, key=lambda path: path.stat().st_mtime, reverse=True)
    return zips[0] if zips else None


def main() -> int:
    python = sys.executable
    steps = [
        ("py_compile app.py", [python, "-m", "py_compile", "app.py"]),
        ("compileall núcleo", [python, "-m", "compileall", "-q", "app.py", "engines", "database_manager.py", "services"]),
        ("verificar imports/rutas/templates", [python, "tools/verify_imports_and_routes.py"]),
        ("smoke_check", [python, "tools/smoke_check.py"]),
    ]
    for label, command in steps:
        code = run_step(label, command)
        if code:
            return code

    zip_path = latest_release_zip()
    if zip_path:
        code = run_step("auditar ZIP limpio", [python, "tools/audit_release_zip.py", str(zip_path)])
        if code:
            return code
    else:
        print("[WARN] No hay ZIP Render Ready todavía; se omite auditoría ZIP.")

    if importlib.util.find_spec("pytest") is None:
        print("[ERROR] pytest no está instalado. Para completar tests ejecuta:")
        print("        pip install -r requirements-dev.txt")
        print("        python -m pytest -q")
        return 1

    return run_step("pytest -q", [python, "-m", "pytest", "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
