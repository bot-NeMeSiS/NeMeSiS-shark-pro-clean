"""Static V941 release gate; no app import, network, database, or release mutation.

Run with the prepared project Python:
    python -B tools/check_admin_master_control.py
Runtime and browser suites must use the supervised LOCAL SAFE runner separately.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    with tempfile.TemporaryDirectory(prefix="nemesis-v941-static-") as temporary:
        command = [
            sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
            "--basetemp", str(Path(temporary) / "pytest"),
            str(ROOT / "tests" / "test_admin_master_release.py"),
        ]
        completed = subprocess.run(command, cwd=ROOT, env=environment, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

