from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_app_imports(app_module):
    assert hasattr(app_module, "app")
    assert app_module.app.name == "app"


def test_core_files_compile():
    files = [ROOT / "app.py", ROOT / "database_manager.py"]
    files.extend(sorted((ROOT / "engines").glob("*.py")))
    for file in files:
        if file.exists():
            py_compile.compile(str(file), doraise=True)
