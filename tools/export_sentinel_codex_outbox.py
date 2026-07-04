from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
OUTBOX = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "codex_outbox.md"


def main() -> int:
    if not OUTBOX.exists():
        print("Sin outbox generado todavía. Ejecuta tools/run_autonomous_company_sentinel.py --mode safe_scan --dry-run")
        return 1
    print(OUTBOX.read_text(encoding="utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
