"""Keep the executable qualification gate aligned with the Ruff upgrade."""

from types import SimpleNamespace

import pytest

from scripts.handoff_qualification import audit


@pytest.fixture
def runtime_versions(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Supply runtime metadata without installing the product dependency set."""
    versions = {
        "scrapy": "2.19.0",
        "pytest": "9.0.3",
        "pytest-cov": "7.1.0",
        "pytest-xdist": "3.8.0",
        "ruff": "0.16.10",
    }
    monkeypatch.setattr(
        audit,
        "sys",
        SimpleNamespace(version_info=(3, 13, 5), executable="fixture-python"),
    )
    monkeypatch.setattr(
        audit,
        "importlib",
        SimpleNamespace(
            metadata=SimpleNamespace(version=versions.__getitem__),
            import_module=lambda name: SimpleNamespace(__file__="fixture-scrapy"),
        ),
    )
    return versions


def test_runtime_accepts_upgraded_ruff(runtime_versions: dict[str, str]) -> None:
    """The Ruff upgrade must pass the runtime prerequisite gate."""
    result = audit.runtime("3.13", fastmcp=False)
    if result["packages"]["ruff"] != runtime_versions["ruff"]:
        pytest.fail("runtime evidence did not retain the installed Ruff version")


def test_runtime_rejects_previous_ruff(runtime_versions: dict[str, str]) -> None:
    """A stale environment must fail before qualification can continue."""
    runtime_versions["ruff"] = "0.16.9"
    with pytest.raises(ValueError, match=r"ruff must remain 0\.16\.10"):
        audit.runtime("3.13", fastmcp=False)
