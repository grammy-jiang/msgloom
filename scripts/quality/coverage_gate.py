"""
Validate retained branch-aware pytest-cov evidence without rerunning tests.

Floors derive from successful GitHub Actions run 37696390151 (Python
3.12/3.13/3.14). Keep this table the single source of threshold values.
Coverage must be measured after both normal and exclusive tox commands:
the first pytest invocation alone is not the completed coverage result.

Low-coverage Teams content traversal requires meaningful integration tests
before a higher floor; never treat these budgets as proof of test adequacy.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

EXPECTED_SOURCES = frozenset({"msgloom", "message_ingest", "microsoft_graph"})
MIN_GLOBAL_LINE = Decimal("0.88")
MIN_GLOBAL_BRANCH = Decimal("0.73")
MIN_MEASURED_LINES = 32_000
MIN_MEASURED_BRANCHES = 9_700

# Each tuple is (minimum line rate, minimum branch rate). The selected files
# span acquisition, auth, persistence, delivery, graph protocol, and rendering.
# All have real branch opportunities in the reviewed baseline report.
CRITICAL_FILES: dict[str, tuple[Decimal, Decimal]] = {
    "acquisition/source_context.py": (Decimal("0.84"), Decimal("0.72")),
    "auth/session.py": (Decimal("0.82"), Decimal("0.64")),
    "catalog/stores/microsoft/outlook/_email_inventory.py": (
        Decimal("0.84"),
        Decimal("0.78"),
    ),
    "delivery/part.py": (Decimal("0.92"), Decimal("0.82")),
    "persistence/intake_completion.py": (Decimal("0.85"), Decimal("0.78")),
    "preparation/isolation/runner.py": (Decimal("0.81"), Decimal("0.68")),
    "protocol/__init__.py": (Decimal("0.95"), Decimal("0.95")),
    "reporting/renderer.py": (Decimal("0.80"), Decimal("0.60")),
    "triage_pipeline/io_mixin.py": (Decimal("0.81"), Decimal("0.63")),
}


@dataclass(frozen=True)
class CoverageSummary:
    """State completed evidence rates and the number of guarded source files."""

    line_rate: Decimal
    branch_rate: Decimal
    critical_files: int


def _rate(value: str | None, context: str) -> Decimal:
    """Reject malformed, nonfinite, or impossible XML coverage fractions."""
    if value is None:
        raise ValueError(f"invalid {context}: missing rate")
    try:
        rate = Decimal(value)
    except (TypeError, InvalidOperation) as exc:
        raise ValueError(f"invalid {context}: {value!r}") from exc
    if not rate.is_finite() or not Decimal(0) <= rate <= Decimal(1):
        raise ValueError(f"invalid {context}: {value!r}")
    return rate


def _counts(root: ET.Element, kind: str, minimum: int) -> Decimal:
    """Use unrounded counters rather than the XML's formatted rate."""
    try:
        valid = int(root.attrib[f"{kind}-valid"])
        covered = int(root.attrib[f"{kind}-covered"])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"missing or invalid {kind} counters") from exc
    if valid < minimum:
        label = "line" if kind == "lines" else "branch"
        raise ValueError(f"measured {label} count {valid} below {minimum}")
    if covered < 0 or covered > valid:
        raise ValueError(f"invalid {kind} covered count {covered}/{valid}")
    return Decimal(covered) / Decimal(valid)


def check_report(path: Path) -> CoverageSummary:
    """Fail closed on absent, incomplete, or regressed coverage XML."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ValueError(f"coverage XML missing or invalid: {path}") from exc
    if root.tag != "coverage":
        raise ValueError("coverage XML has unexpected root")
    sources = {
        (item.text or "").replace("\\", "/").rstrip("/").split("/")[-1]
        for item in root.findall("./sources/source")
    }
    if sources != EXPECTED_SOURCES:
        raise ValueError(
            f"measured source roots {sorted(sources)} differ from "
            f"{sorted(EXPECTED_SOURCES)}"
        )

    line_rate = _counts(root, "lines", MIN_MEASURED_LINES)
    branch_rate = _counts(root, "branches", MIN_MEASURED_BRANCHES)
    if line_rate < MIN_GLOBAL_LINE:
        raise ValueError(
            f"global line coverage {line_rate:.2%} below {MIN_GLOBAL_LINE:.0%}"
        )
    if branch_rate < MIN_GLOBAL_BRANCH:
        raise ValueError(
            f"global branch coverage {branch_rate:.2%} below {MIN_GLOBAL_BRANCH:.0%}"
        )

    classes: dict[str, list[ET.Element]] = {}
    for item in root.findall("./packages/package/classes/class"):
        filename = (item.get("filename") or "").replace("\\", "/")
        classes.setdefault(filename, []).append(item)

    for filename, (line_floor, branch_floor) in CRITICAL_FILES.items():
        found = classes.get(filename, [])
        if not found:
            raise ValueError(f"missing critical file: {filename}")
        if len(found) != 1:
            raise ValueError(f"duplicate critical file: {filename}")
        item = found[0]
        if not any(
            line.get("branch") == "true" for line in item.findall("./lines/line")
        ):
            raise ValueError(f"no measured branches for critical file: {filename}")
        module_line = _rate(item.get("line-rate"), f"{filename} line-rate")
        module_branch = _rate(item.get("branch-rate"), f"{filename} branch-rate")
        if module_line < line_floor:
            raise ValueError(
                f"critical line coverage {filename}: "
                f"{module_line:.2%} below {line_floor:.0%}"
            )
        if module_branch < branch_floor:
            raise ValueError(
                f"critical branch coverage {filename}: "
                f"{module_branch:.2%} below {branch_floor:.0%}"
            )

    return CoverageSummary(line_rate, branch_rate, len(CRITICAL_FILES))


def main(argv: list[str] | None = None) -> int:
    """Validate exactly one completed tox coverage XML artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_xml", type=Path)
    args = parser.parse_args(argv)
    try:
        summary = check_report(args.coverage_xml)
    except ValueError as exc:
        print(f"coverage gate FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        f"coverage gate PASS: lines={summary.line_rate:.2%}, "
        f"branches={summary.branch_rate:.2%}, "
        f"critical modules={summary.critical_files}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
