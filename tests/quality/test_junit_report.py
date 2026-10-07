"""Check that a JUnit artifact is complete and usable on any platform."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from scripts.quality import junit_report


def _xml(path: Path, cases: tuple[str, ...]) -> Path:
    """Build synthetic pytest-compatible JUnit XML."""
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name="fixture")
    for state in cases:
        case = ET.SubElement(suite, "testcase", name=state, classname="unit")
        if state != "passed":
            ET.SubElement(case, state)
    ET.ElementTree(root).write(path, encoding="utf-8")
    return path


def test_two_independent_reports_retained_and_summarized(tmp_path: Path) -> None:
    """Normal and exclusive suites both contribute to the same job summary."""
    normal = _xml(tmp_path / "junit-normal.xml", ("passed", "skipped", "passed"))
    serial = _xml(tmp_path / "junit-exclusive.xml", ("passed",))
    summary = junit_report.summarize((normal, serial))
    if "3 passed" not in summary or "1 skipped" not in summary:
        pytest.fail("JUnit summary lost normal/serial cases")


@pytest.mark.parametrize(
    "cases",
    [
        ("failure", "passed"),
        ("error", "passed"),
        ("skipped",),
        (),
    ],
)
def test_failed_or_vacuous_results_cannot_pass(
    tmp_path: Path, cases: tuple[str, ...]
) -> None:
    """Do not claim a green report from failed, skipped-only or empty results."""
    file = _xml(tmp_path / "junit.xml", cases)
    with pytest.raises(ValueError):
        junit_report.summarize((file,))


def test_missing_or_broken_artifacts_fail_closed(tmp_path: Path) -> None:
    """The CI step must never silently omit an expected JUnit artifact."""
    with pytest.raises(ValueError, match="JUnit"):
        junit_report.summarize((tmp_path / "absent.xml",))
    broken = tmp_path / "bad.xml"
    broken.write_text("<testsuite")
    with pytest.raises(ValueError, match="JUnit"):
        junit_report.summarize((broken,))


def test_cli_publishes_summary_without_external_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GitHub Actions summary is just a portable UTF-8 file append."""
    report = _xml(tmp_path / "junit-fastmcp.xml", ("passed", "passed"))
    destination = tmp_path / "job-summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(destination))
    if junit_report.main([str(report)]) != 0:
        pytest.fail("JUnit summary command returned failure")
    if "2 passed, 0 skipped" not in destination.read_text():
        pytest.fail("GitHub Actions summary lost executed test results")
