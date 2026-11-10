"""Manual CompanyOS legacy transition planner; default is strictly read-only.

No HTTP endpoint, scheduled caller or authorization is provided by this tool.
Production execution requires a separately reviewed owner-cessation record and
a NEW human decision for the exact plan. Reference IDs alone prove neither.
"""
from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from engines.companyos_legacy_transition import TransitionError, inspect, transition


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--expected", required=True, help="Reviewed JSON identity of root, marker, SHA and instance; no secrets.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--rollback", action="store_true", help="Only while active scheduler.lock is absent; never replace a new owner.")
    parser.add_argument("--cessation-reference")
    parser.add_argument("--authorization-reference")
    args = parser.parse_args(argv)
    try:
        expected = json.loads(args.expected)
        context = {"sha": os.getenv("RENDER_GIT_COMMIT"), "instance": os.getenv("HOSTNAME")}
        if args.execute or args.rollback:
            result = transition(args.storage_root, expected, context=context,
                                cessation_reference=args.cessation_reference,
                                authorization_reference=args.authorization_reference, rollback=args.rollback)
        else:
            result = inspect(args.storage_root, expected, context=context)
        print(json.dumps({"ok": True, **result}, sort_keys=True))
        return 0
    except TransitionError as exc:
        print(json.dumps({"ok": False, "code": str(exc), "automatic_retry": False}))
    except (OSError, ValueError, TypeError):
        print(json.dumps({"ok": False, "code": "UNVERIFIED_OPERATION_NO_AUTOMATIC_RETRY", "automatic_retry": False}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
