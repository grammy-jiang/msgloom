"""Portable qualification policy and evidence tests without OS isolation."""

import json
from pathlib import Path

import pytest

from scripts.handoff_qualification import audit


def test_coverage_map_requires_all_spiders_scenarios_and_executed_nodes() -> None:
    """A name list cannot substitute for actual passing coverage evidence."""
    nodes = ["tests/test_fixture.py::test_complete"]
    data = {
        "base_sha": "a" * 40,
        "candidate_sha": "b" * 40,
        "spiders": {name: nodes for name in audit.SPIDERS},
        "scenarios": {str(i): nodes for i in range(1, 14)},
    }
    passed = {("tests.test_fixture", "test_complete")}
    audit.validate_coverage(data, set(audit.SPIDERS), passed, "a" * 40, "b" * 40)
    for field, key in (("spiders", audit.SPIDERS[0]), ("scenarios", "13")):
        broken = json.loads(json.dumps(data))
        del broken[field][key]
        with pytest.raises(ValueError):
            audit.validate_coverage(
                broken,
                set(audit.SPIDERS),
                passed,
                "a" * 40,
                "b" * 40,
            )
    with pytest.raises(ValueError):
        audit.validate_coverage(data, set(audit.SPIDERS), set(), "a" * 40, "b" * 40)
    with pytest.raises(ValueError):
        audit.validate_coverage(data, set(audit.SPIDERS), passed, "a" * 40, "c" * 40)


def test_reverse_import_scan_rejects_a2_and_dynamic_imports(tmp_path: Path) -> None:
    """The reverse boundary includes ordinary and literal dynamic imports."""
    source = tmp_path / "message_ingest"
    source.mkdir()
    for statement in (
        "import msgloom.sources",
        "from msgloom import preparation",
        "from msgloom.preparation_pipeline import intake",
        "import importlib; importlib.import_module('msgloom.sources')",
        "__import__('msgloom.preparation')",
    ):
        (source / "bad.py").write_text(statement)
        with pytest.raises(ValueError):
            audit.reverse_imports(tmp_path)
    (source / "bad.py").write_text(
        "from pathlib import Path\nfrom msgloom.configuration import load_universal_config"
    )
    audit.reverse_imports(tmp_path)


def test_runtime_requires_exact_313_patch(monkeypatch):
    """A patch-number prefix cannot stand in for Python 3.13.5."""
    monkeypatch.setattr(audit.sys, "version_info", (3, 13, 50))
    with pytest.raises(ValueError, match="Python mismatch"):
        audit.runtime("3.13", False)
