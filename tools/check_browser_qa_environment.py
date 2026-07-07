from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def detect_browser_qa_environment() -> dict:
    playwright_available = False
    browsers_available = False
    reason = ""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        playwright_available = True
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                browser.close()
            browsers_available = True
        except Exception as exc:
            browsers_available = False
            reason = f"Playwright instalado, pero Chromium no puede arrancar: {exc.__class__.__name__}"
    except Exception as exc:
        playwright_available = False
        reason = f"Playwright no disponible: {exc.__class__.__name__}"

    python_cmd = shutil.which("python") or sys.executable
    recommended = f"{python_cmd} -m pip install playwright && {python_cmd} -m playwright install chromium"
    if playwright_available and not browsers_available:
        recommended = f"{python_cmd} -m playwright install chromium"

    payload = {
        "ok": True,
        "version": (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig", errors="replace").strip(),
        "playwright_available": playwright_available,
        "browsers_available": browsers_available,
        "can_capture": bool(playwright_available and browsers_available),
        "recommended_install_command": recommended,
        "reason": "" if playwright_available and browsers_available else reason,
        "note": "No instala dependencias ni descarga navegadores automaticamente.",
    }
    return payload


def main() -> int:
    print(json.dumps(detect_browser_qa_environment(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
