"""Keep version-stamped parser identities in sync with installed libraries."""

from importlib import import_module, metadata

import pytest

from msgloom.preparation.contracts import DocumentFormat
from msgloom.preparation.isolation.registry import PRODUCTION_REGISTRY


@pytest.mark.parametrize(
    ("format_", "package", "prefix"),
    [
        (DocumentFormat.HTML, "selectolax", "stdlib-email+selectolax-"),
        (DocumentFormat.PDF, "pypdfium2", "pypdfium2-"),
    ],
)
def test_parser_identity_tracks_exact_runtime_dependency(
    format_: DocumentFormat, package: str, prefix: str
) -> None:
    entry = PRODUCTION_REGISTRY.resolve(format_)
    installed_backend = f"{prefix}{metadata.version(package)}"
    if entry.identity.backend != installed_backend:
        pytest.fail(f"registry backend differs from installed {package} version")
    if import_module(entry.module).BACKEND != installed_backend:
        pytest.fail(f"parser backend differs from installed {package} version")


def test_excel_parser_identity_tracks_exact_calamine_and_openpyxl_versions() -> None:
    """Native parser library upgrades must change the backend identity."""
    entry = PRODUCTION_REGISTRY.resolve(DocumentFormat.XLSX)
    installed_backend = (
        f"python-calamine-{metadata.version('python-calamine')}"
        f"+openpyxl-{metadata.version('openpyxl')}"
    )
    if entry.identity.backend != installed_backend:
        pytest.fail("Excel registry backend differs from installed libraries")
    if import_module(entry.module).BACKEND != installed_backend:
        pytest.fail("Excel module backend differs from installed libraries")
