"""List or explicitly execute the finite A1-to-A2 qualification plan."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# A direct script invocation must find its sibling package from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.handoff_qualification.execution import run_plan
from scripts.handoff_qualification.plan import (
    build_plan,
    listed_plan,
    parser,
)


def main() -> int:
    """List by default; require exact identity before explicit execution."""
    cli = parser()
    args = cli.parse_args()
    if args.execute and not (args.base and args.candidate):
        cli.error("--execute requires --base and --candidate exact SHAs")
    gates = build_plan(args)
    if not args.execute:
        print(json.dumps(listed_plan(gates), indent=2, sort_keys=True))
        return 0
    try:
        result = run_plan(
            args.source_root,
            args.output_root,
            args.base,
            args.candidate,
            gates,
            guard_host=True,
        )
    except (OSError, ValueError) as exc:
        print(f"qualification blocked: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    # External exact-candidate review is deliberately outside this runner.
    # Exit 2 never represents completed Task15, even if every gate passed.
    return 2 if result["status"] == "automated_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
