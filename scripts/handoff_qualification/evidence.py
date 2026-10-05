"""Validate test artifacts without replacing child process exit semantics."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .execution import Gate


def junit_counts(path: Path) -> dict[str, int]:
    """Count actual cases, including failed, errored and skipped cases."""
    cases = list(ET.parse(path).getroot().iter("testcase"))
    return {
        "tests": len(cases),
        "failures": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
        "skipped": sum(case.find("skipped") is not None for case in cases),
    }


def inspect_artifacts(gate: Gate, record: dict, root: Path) -> None:
    """Hash saved evidence and reject absent or unsuccessful test reports."""
    paths = [Path(record[key]) for key in ("stdout", "stderr")]
    try:
        if gate.junit:
            path = root / gate.junit
            counts = junit_counts(path)
            paths.append(path)
            record["counts"] = counts
            if not counts["tests"] or any(
                counts[key] for key in ("failures", "errors", "skipped")
            ):
                raise ValueError("JUnit has no cases or unsuccessful/skipped cases")
        if gate.coverage:
            path = root / gate.coverage
            coverage = ET.parse(path).getroot()
            if coverage.tag != "coverage" or not list(coverage.iter("class")):
                raise ValueError("coverage XML has no measured classes")
            paths.append(path)
            record["coverage_counts"] = dict(coverage.attrib)
        if gate.contracts:
            output = Path(record["stderr"]).read_text()
            count = re.search(r"Ran (\d+) contracts? in ", output)
            if (
                not count
                or int(count[1]) < 4
                or not re.search(r"^OK$", output, re.MULTILINE)
            ):
                raise ValueError("missing successful minimum four Scrapy contracts")
            record["counts"] = {"contracts": int(count[1])}
    except (OSError, ValueError, ET.ParseError) as exc:
        if record["status"] == "passed":
            record.update(status="failed", reason=f"artifact validation: {exc}")
        else:
            record["artifact_error"] = str(exc)
    record["artifacts"] = [
        {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in paths
        if path.is_file()
    ]
