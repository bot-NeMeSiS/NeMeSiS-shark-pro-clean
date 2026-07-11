from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(url: str, timeout: float = 35.0) -> None:
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except Exception as exc:
            last_error = f"{exc.__class__.__name__}: {str(exc)[:120]}"
            time.sleep(0.4)
    raise RuntimeError(f"local_server_unavailable: {last_error}")


def main() -> int:
    port = free_port()
    output = ROOT / "reports" / "V930_browser_qa"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nemesis_v930_browser_") as temp_dir:
        safe_secret = "v930-local-browser-qa-only"
        temp_db = str(Path(temp_dir) / "v930_browser.sqlite")
        env = dict(os.environ)
        env.update({
            "DB_PATH": temp_db,
            "PORT": str(port),
            "SECRET_KEY": safe_secret,
            "FLASK_DEBUG": "0",
            "ENABLE_AUTOMATED_RENDER_DEPLOY": "0",
            "TELEGRAM_BOT_TOKEN": "",
            "TELEGRAM_CHAT_ID": "",
            "AUTOMATION_SECRET": "",
            "STRIPE_SECRET_KEY": "",
            "STRIPE_WEBHOOK_SECRET": "",
            "OPENAI_API_KEY": "",
            "API_FOOTBALL_KEY": "",
            "API_SPORTS_KEY": "",
            "THE_ODDS_API_KEY": "",
        })
        command = [
            sys.executable,
            "-c",
            "from app import app; app.run(host='127.0.0.1', port=int(__import__('os').environ['PORT']), debug=False, use_reloader=False)",
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        try:
            previous_db = os.environ.get("DB_PATH")
            previous_secret = os.environ.get("SECRET_KEY")
            os.environ["DB_PATH"] = temp_db
            os.environ["SECRET_KEY"] = safe_secret
            from tools import run_browser_reference_qa as browser_qa

            base_url = f"http://127.0.0.1:{port}"
            wait_for_server(base_url + "/api/runtime-version")
            detail_route = "/match/v930-no-real-match-in-temporary-db"
            if detail_route not in browser_qa.CLIENT_ROUTES:
                browser_qa.CLIENT_ROUTES.append(detail_route)
            payload = browser_qa.run_browser_reference_qa(
                base_url=base_url,
                output=output,
                desktop=True,
                mobile=True,
                admin_safe=True,
                no_login_required=True,
                timeout=20000,
                write_json=True,
                v928_matrix=True,
                safe_mock_sessions=True,
                safe_session_secret=safe_secret,
            )
        finally:
            if 'previous_db' in locals():
                if previous_db is None:
                    os.environ.pop("DB_PATH", None)
                else:
                    os.environ["DB_PATH"] = previous_db
            if 'previous_secret' in locals():
                if previous_secret is None:
                    os.environ.pop("SECRET_KEY", None)
                else:
                    os.environ["SECRET_KEY"] = previous_secret
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=4)

    captures = payload.get("screenshots") or []
    summary = {
        "ok": bool(payload.get("ok")),
        "version": payload.get("version"),
        "screenshots_captured": int(payload.get("screenshots_captured") or 0),
        "routes_captured": len(set(payload.get("routes_captured") or [])),
        "viewport_profiles": payload.get("viewport_profiles") or [],
        "overflow_issues": len(payload.get("overflow_issues") or []),
        "errors": len([item for item in captures if item.get("error")]),
        "temporary_database": True,
        "external_provider_calls": 0,
        "telegram_sent": False,
        "payments_executed": False,
        "pixel_perfect_claim_allowed": False,
        "detail_route_status": next((item.get("status") for item in captures if item.get("route") == detail_route), None),
        "detail_route_classification": "BLOCKED_BY_REAL_DATA",
    }
    (output / "v930_browser_matrix_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0 if summary["ok"] and summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
