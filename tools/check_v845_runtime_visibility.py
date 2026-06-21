from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = "V845_SHARK_AI_INTELLIGENCE_PRODUCT_ASSISTANT_FINAL"

base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
app = (ROOT / "app.py").read_text(encoding="utf-8")
version_txt = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()

checks = {
    "version_txt": version_txt == VERSION,
    "app_version": f"APP_VERSION = '{VERSION}'" in app,
    "base_meta": VERSION in base,
    "data_v845_shell": "data-v845-shell" in base,
    "v845_comment": "NEMESIS V845 SHARK AI INTELLIGENCE PRODUCT ASSISTANT ACTIVE" in base,
    "css_marker": "V845 SHARK AI INTELLIGENCE PRODUCT ASSISTANT START" in css,
    "runtime_flag": "has_v845_shark_ai_product_assistant" in app,
    "openai_flag": "openai_configured" in app,
    "engine_importable": importlib.util.find_spec("engines.shark_ai_product_assistant_engine") is not None,
}

missing = [name for name, ok in checks.items() if not ok]
print({"ok": not missing, "missing": missing})
raise SystemExit(0 if not missing else 1)
