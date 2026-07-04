from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Autonomous Company Sentinel safely.")
    parser.add_argument("--mode", default="safe_scan")
    parser.add_argument("--runner", default="local")
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    os.environ.setdefault("AUTOMATION_SECRET", "local-autonomous-company-sentinel")
    import app  # noqa: WPS433
    from engines.autonomous_company_sentinel_engine import run_autonomous_company_sentinel

    result = run_autonomous_company_sentinel(
        app.app.test_client(),
        app.APP_VERSION,
        ROOT,
        mode=args.mode,
        runner=args.runner,
        dry_run=True if args.dry_run else True,
        runtime={"app_version": app.APP_VERSION},
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
