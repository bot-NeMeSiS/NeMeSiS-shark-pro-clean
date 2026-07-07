from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _python_command() -> str:
    return shutil.which("python") or sys.executable


def detect_browser_qa_environment() -> dict:
    python_cmd = _python_command()
    install_allowed = str(os.getenv("ENABLE_BROWSER_QA_INSTALL") or "").strip() == "1"
    recommended_install = f"{python_cmd} -m pip install playwright"
    recommended_browsers = f"{python_cmd} -m playwright install chromium"
    payload = {
        "ok": True,
        "version": (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig", errors="replace").strip(),
        "generated_by": "check_browser_qa_environment.py",
        "system": platform.system(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "enable_browser_qa_install": install_allowed,
        "playwright_available": False,
        "browsers_available": False,
        "chromium_launch_ok": False,
        "can_capture": False,
        "browser_qa_status": "PACKAGE_MISSING",
        "reason": "",
        "recommended_install_command": f"{recommended_install} && {recommended_browsers}",
        "recommended_package_command": recommended_install,
        "recommended_browser_command": recommended_browsers,
        "note": "No instala dependencias ni descarga navegadores automaticamente salvo ENABLE_BROWSER_QA_INSTALL=1.",
    }
    if str(os.getenv("DISABLE_BROWSER_QA") or "").strip() == "1":
        payload.update({
            "browser_qa_status": "DISABLED_BY_ENV",
            "reason": "DISABLE_BROWSER_QA=1",
        })
        return payload

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        payload["playwright_available"] = True
    except Exception as exc:
        payload.update({
            "browser_qa_status": "PACKAGE_MISSING",
            "reason": f"Playwright no disponible: {exc.__class__.__name__}",
        })
        return payload

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.set_content("<!doctype html><html><body>browser-qa-ok</body></html>")
            browser.close()
        payload.update({
            "browsers_available": True,
            "chromium_launch_ok": True,
            "can_capture": True,
            "browser_qa_status": "AVAILABLE",
            "reason": "",
        })
    except Exception as exc:
        message = str(exc)[:500]
        status = "BROWSERS_MISSING" if "Executable doesn't exist" in message or "playwright install" in message.lower() else "LAUNCH_FAILED"
        payload.update({
            "browsers_available": False,
            "chromium_launch_ok": False,
            "can_capture": False,
            "browser_qa_status": status,
            "reason": f"Playwright instalado, pero Chromium no puede capturar: {exc.__class__.__name__}: {message}",
            "recommended_install_command": recommended_browsers,
        })
    return payload


def main() -> int:
    payload = detect_browser_qa_environment()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
