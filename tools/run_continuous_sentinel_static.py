from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_continuous_sentinel_static.sqlite"))
    os.environ.setdefault("DAILY_AUTOMATION_DRY_RUN", "1")
    os.environ.setdefault("ENABLE_AUTO_TELEGRAM_PRO", "0")

    import app as app_module
    from engines.continuous_shark_sentinel_engine import run_continuous_sentinel_cycle

    result = run_continuous_sentinel_cycle(app_module.app.test_client(), app_module.APP_VERSION, mode="quick", dry_run=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
