from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "release_output" / "NeMeSiS_SHARK_PRO_V845_SHARK_AI_INTELLIGENCE_PRODUCT_ASSISTANT_FINAL_RENDER_READY.zip"
forbidden = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", ".env", ".db", ".sqlite", ".sqlite3", ".zip")
bad = []
with zipfile.ZipFile(ZIP) as zf:
    for name in zf.namelist():
        low = name.lower()
        if any(marker in low for marker in forbidden):
            if not low.endswith(".env.example") and not low.endswith(".env.render.clean"):
                bad.append(name)
ok = not bad
print({"ok": ok, "forbidden_count": len(bad), "zip": str(ZIP)})
raise SystemExit(0 if ok else 1)
