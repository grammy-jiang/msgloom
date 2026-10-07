"""Guard coverage budgets without rerunning the project test matrix."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from scripts.quality import coverage_gate


def _element(root: ET.Element[str] | None, path: str) -> ET.Element[str]:
    """Require synthetic XML nodes before mutating the tested evidence."""
    if root is None:
        pytest.fail("missing synthetic XML root")
    element = root.find(path)
    if element is None:
        pytest.fail(f"missing synthetic XML node: {path}")
    return element


def _report(path: Path, *, win_paths: bool = False) -> Path:
    """Write synthetic but structurally complete pytest-cov Cobertura evidence."""
    root = ET.Element(
        "coverage",
        {
            "lines-valid": "33335",
            "lines-covered": "29796",
            "branches-valid": "10232",
            "branches-covered": "7605",
            "line-rate": "0.8938",
            "branch-rate": "0.7433",
        },
    )
    sources = ET.SubElement(root, "sources")
    for name in ("msgloom", "message_ingest", "microsoft_graph"):
        directory = f"C:\\build\\{name}" if win_paths else f"/build/{name}"
        ET.SubElement(sources, "source").text = directory
    package = ET.SubElement(ET.SubElement(root, "packages"), "package")
    classes = ET.SubElement(package, "classes")
    for filename in coverage_gate.CRITICAL_FILES:
        name = filename.replace("/", "\\") if win_paths else filename
        record = ET.SubElement(
            classes,
            "class",
            {"filename": name, "line-rate": "0.99", "branch-rate": "0.98"},
        )
        ET.SubElement(
            ET.SubElement(record, "lines"),
            "line",
            {"number": "3", "hits": "1", "branch": "true"},
        )
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return path


@pytest.mark.parametrize("win_paths", [False, True])
def test_complete_coverage_accepts_platform_independent_paths(
    tmp_path: Path, win_paths: bool
) -> None:
    """Read Linux or Windows paths without requiring matching host mounts."""
    summary = coverage_gate.check_report(
        _report(tmp_path / "coverage.xml", win_paths=win_paths)
    )
    if summary.critical_files != len(coverage_gate.CRITICAL_FILES):
        pytest.fail("complete critical file coverage was not recorded")


@pytest.mark.parametrize(
    ("field", "bad_count", "message"),
    [
        ("lines-covered", "28000", "global line coverage"),
        ("branches-covered", "7000", "global branch coverage"),
    ],
)
def test_global_coverage_regression_is_rejected(
    tmp_path: Path, field: str, bad_count: str, message: str
) -> None:
    """Both line and branch regression must stop the CI check."""
    path = _report(tmp_path / "coverage.xml")
    doc = ET.parse(path)
    doc.getroot().set(field, bad_count)
    doc.write(path)
    with pytest.raises(ValueError, match=message):
        coverage_gate.check_report(path)


def test_missing_source_and_missing_critical_module_fail_closed(tmp_path: Path) -> None:
    """An incomplete report cannot pass just by improving the global rate."""
    path = _report(tmp_path / "coverage.xml")
    doc = ET.parse(path)
    _element(doc.getroot(), "./sources/source").text = "/build/other"
    doc.write(path)
    with pytest.raises(ValueError, match="measured source roots"):
        coverage_gate.check_report(path)

    _report(path)
    doc = ET.parse(path)
    critical = _element(doc.getroot(), ".//class")
    critical.attrib["filename"] = "removed.py"
    doc.write(path)
    with pytest.raises(ValueError, match="missing critical file"):
        coverage_gate.check_report(path)


def test_critical_branch_regression_and_fake_branch_data_fail(
    tmp_path: Path,
) -> None:
    """A critical module must have measured branches above its own floor."""
    path = _report(tmp_path / "coverage.xml")
    doc = ET.parse(path)
    record = _element(doc.getroot(), ".//class")
    record.set("branch-rate", "0.01")
    doc.write(path)
    with pytest.raises(ValueError, match="critical branch coverage"):
        coverage_gate.check_report(path)

    _report(path)
    doc = ET.parse(path)
    _element(doc.getroot(), ".//class/lines/line").set("branch", "false")
    doc.write(path)
    with pytest.raises(ValueError, match="no measured branches"):
        coverage_gate.check_report(path)


def test_malformed_or_tiny_coverage_cannot_pass(tmp_path: Path) -> None:
    """An absent, malformed, or nearly empty XML file is not acceptance."""
    missing = tmp_path / "absent.xml"
    with pytest.raises(ValueError, match="coverage XML"):
        coverage_gate.check_report(missing)
    missing.write_text("<coverage")
    with pytest.raises(ValueError, match="coverage XML"):
        coverage_gate.check_report(missing)

    path = _report(tmp_path / "coverage.xml")
    doc = ET.parse(path)
    doc.getroot().set("lines-valid", "2")
    doc.write(path)
    with pytest.raises(ValueError, match="measured line count"):
        coverage_gate.check_report(path)


def test_duplicate_critical_filename_fails_closed(tmp_path: Path) -> None:
    """Ambiguous XML class paths must not select a convenient passing entry."""
    path = _report(tmp_path / "coverage.xml")
    doc = ET.parse(path)
    classes = _element(doc.getroot(), ".//classes")
    duplicate = ET.fromstring(ET.tostring(classes[0]))
    classes.append(duplicate)
    doc.write(path)
    with pytest.raises(ValueError, match="duplicate critical file"):
        coverage_gate.check_report(path)


def test_command_exit_is_nonzero_for_regressed_ci_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The workflow must fail, not merely log a rejected coverage report."""
    path = _report(tmp_path / "coverage.xml")
    document = ET.parse(path)
    document.getroot().set("branches-covered", "0")
    document.write(path)
    if coverage_gate.main([str(path)]) != 1:
        pytest.fail("regressed branch coverage returned success")
    if "global branch coverage" not in capsys.readouterr().err:
        pytest.fail("failed coverage gate did not explain the branch regression")
