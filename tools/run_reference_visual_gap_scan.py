from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.sentinel_reference_visual_engine import run_reference_visual_scan


def main() -> int:
    parser = argparse.ArgumentParser(description="V899 reference visual gap scan.")
    parser.add_argument("--dry-run", action="store_true", help="Do not run browser captures; still writes manifest/gap report.")
    parser.add_argument("--browser", action="store_true", help="Try browser QA when Playwright is available.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    result = run_reference_visual_scan(
        ROOT,
        browser_available=False,
        run_browser=bool(args.browser and not args.dry_run),
        base_url=args.base_url,
    )
    out = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "reference_gap_report.json"
    payload = {
        "ok": True,
        "dry_run": bool(args.dry_run),
        "reference_count": result.get("reference_count"),
        "manifest_count": (result.get("manifest") or {}).get("reference_count"),
        "gap_count": len((result.get("product_gap_report") or {}).get("gaps") or []),
        "browser_available": (result.get("browser_result") or {}).get("browser_available", False),
        "report_path": str(out),
        "issues": result.get("issues", []),
        "no_exact_visual_claim": True,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
