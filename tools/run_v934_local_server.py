"""Launch a local V934 QA server with an isolated temporary database."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5011)
    parser.add_argument("--session-secret", default="v934-browser-qa-local-only")
    args = parser.parse_args()
    os.environ["DB_PATH"] = str(Path(tempfile.gettempdir()) / "nemesis_v934_browser_qa.sqlite")
    os.environ["FLASK_SECRET_KEY"] = args.session_secret
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["STRIPE_SECRET_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""
    from app import app

    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
