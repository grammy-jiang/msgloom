"""Publish existing pytest JUnit evidence without rerunning test suites."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from xml.etree import ElementTree as ET


def summarize(files: tuple[Path, ...]) -> str:
    """Validate every expected report and aggregate executed test counts."""
    if not files:
        raise ValueError("JUnit reports are required")
    passed = skipped = 0
    for path in files:
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError) as exc:
            raise ValueError(f"missing or malformed JUnit report: {path}") from exc
        if root.tag not in {"testsuites", "testsuite"}:
            raise ValueError(f"invalid JUnit report root: {path}")
        cases = list(root.iter("testcase"))
        if not cases:
            raise ValueError(f"JUnit report contains no test cases: {path}")
        for case in cases:
            if case.find("failure") is not None or case.find("error") is not None:
                raise ValueError(f"JUnit report includes failures or errors: {path}")
            if case.find("skipped") is not None:
                skipped += 1
            else:
                passed += 1
    if not passed:
        raise ValueError("JUnit reports contain no executed tests")
    return f"{passed} passed, {skipped} skipped across {len(files)} report(s)"


def main(argv: list[str] | None = None) -> int:
    """Write one readable Actions job summary after validating all reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("junit", nargs="+", type=Path)
    args = parser.parse_args(argv)
    try:
        summary = summarize(tuple(args.junit))
    except ValueError as exc:
        parser.exit(1, f"JUnit evidence invalid: {exc}\n")
    print(f"JUnit: {summary}")
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with Path(target).open("a", encoding="utf-8") as output:
            output.write(f"### JUnit test results\n\n{summary}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
