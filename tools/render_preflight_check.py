#!/usr/bin/env python3
"""Preflight remoto para Render sin depender de Flask local.

Uso:
    python tools/render_preflight_check.py https://bot-apuestas-crgf.onrender.com

Comprueba rutas públicas/cliente/admin-login/API después de desplegar.
No envía Telegram, no toca pagos reales y no necesita secrets.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
DEFAULT_PATHS = [
    "/",
    "/membresias",
    "/login",
    "/registro",
    "/admin-login",
    "/app",
    "/mi-cuenta",
    "/live",
    "/calendar",
    "/picks",
    "/combis",
    "/mercados",
    "/telegram",
    "/shark",
    "/api/health",
    "/api/runtime-version",
    "/api/live/diagnostics",
]

@dataclass
class RemoteResult:
    path: str
    status_code: int | None
    ok: bool
    note: str = ""


def fetch(base_url: str, path: str) -> RemoteResult:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req = urllib.request.Request(url, headers={"User-Agent": "NeMeSiS-Render-Preflight/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            status = int(response.status)
            return RemoteResult(path, status, status < 500, "OK" if status < 500 else "server error")
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        return RemoteResult(path, status, status < 500, "HTTPError aceptable" if status < 500 else "server error")
    except Exception as exc:
        return RemoteResult(path, None, False, f"exception: {exc}")


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python tools/render_preflight_check.py https://tu-app.onrender.com")
        return 2
    base_url = sys.argv[1].strip()
    results = [fetch(base_url, path) for path in DEFAULT_PATHS]
    report = {
        "ok": all(item.ok for item in results),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": base_url,
        "tested": len(results),
        "failed": [asdict(item) for item in results if not item.ok],
        "results": [asdict(item) for item in results],
    }
    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "V784_RENDER_PREFLIGHT_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
