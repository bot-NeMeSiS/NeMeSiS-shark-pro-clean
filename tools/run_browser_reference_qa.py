from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.browser_visual_qa_engine import run_browser_visual_qa


def main() -> int:
    parser = argparse.ArgumentParser(description="V899 optional browser reference QA.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--timeout-ms", type=int, default=12000)
    args = parser.parse_args()
    payload = run_browser_visual_qa(ROOT, base_url=args.base_url, timeout_ms=args.timeout_ms)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
