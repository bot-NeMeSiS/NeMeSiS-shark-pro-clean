from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from engines.sentinel_reference_visual_engine import run_reference_visual_scan

    result = run_reference_visual_scan(ROOT, browser_available=False)
    target = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "reference_gap_report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
