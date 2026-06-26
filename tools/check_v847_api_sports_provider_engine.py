from pathlib import Path
import sys
import tempfile
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engines import api_sports_provider_engine as engine  # noqa: E402

db_path = str(Path(tempfile.gettempdir()) / "nemesis_v847_provider_check.db")
status = engine.get_api_sports_status(db_path)
dry = engine.api_sports_safe_request("fixtures", {"next": 1}, dry_run=True)
checks = {
    "status_has_guard": isinstance(status.get("usage_guard"), dict),
    "dry_run_no_network": dry.get("dry_run") is True and "would_call_provider" in dry,
    "configured_bool": isinstance(engine.is_api_sports_configured(), bool),
    "safe_no_secret": "key" not in str(status).lower(),
    "fallback_explain": "message" in engine.explain_api_sports_provider_state(db_path),
    "cache_helpers": isinstance(engine.get_cached_api_sports_matches(db_path), list) and isinstance(engine.get_cached_api_sports_live(db_path), list),
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
