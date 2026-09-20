"""Run selected real tests against disposable LOCAL SAFE storage."""
import os
from pathlib import Path
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]

def main():
    # Windows spawn imports this module in children. Import must never start QA
    # again or seed another database before the worker has begun.
    sys.path.insert(0, str(ROOT))
    sys.dont_write_bytecode = True
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    output = ROOT / "data/local_dev" / ("candidate-" + uuid.uuid4().hex)
    output.mkdir(parents=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(output)
    tempfile.tempdir = str(output)
    from tools.local_desktop.run_sentinel_local import prepare
    module, store, blocked = prepare(db_name=output.name + ".sqlite", allow_browser=True)
    import pytest
    code = pytest.main(["-q", "-p", "no:cacheprovider", "--log-file="+str(output/"pytest.log"), "--basetemp="+str(output/"temp"), "--junitxml="+str(output/"result.xml"), *sys.argv[1:]])
    print("QA_OUTPUT", output)
    print("BOUNDARY_EVENTS", blocked)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
