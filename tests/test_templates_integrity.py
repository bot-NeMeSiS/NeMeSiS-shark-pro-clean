from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app.py"
TEMPLATES_DIR = ROOT / "templates"


def test_render_templates_exist():
    tree = ast.parse(APP_FILE.read_text(encoding="utf-8", errors="replace"))
    templates = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name == "render_template" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    templates.add(first.value)
    missing = sorted(t for t in templates if not (TEMPLATES_DIR / t).exists())
    assert not missing, f"Templates faltantes: {missing}"
