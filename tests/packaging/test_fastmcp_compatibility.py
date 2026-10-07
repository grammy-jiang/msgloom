"""Exercise shared async compatibility and exact FastMCP qualification."""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
from importlib.metadata import version

import pytest

from msgloom.contracts import EvidenceReader, VersionRef
from scripts.handoff_qualification import audit

pytestmark = [
    pytest.mark.fastmcp_compat,
    pytest.mark.skipif(
        os.environ.get("MSGLOOM_FASTMCP_COMPAT") != "1",
        reason="FastMCP compatibility tests require explicit opt-in",
    ),
]


class SyntheticReader:
    """Return controlled bytes through the provider-neutral async protocol."""

    async def read(self, reference: VersionRef) -> bytes:
        """Return synthetic content without starting a service."""
        return f"{reference.kind}:{reference.version}".encode()


def test_fastmcp4_import_and_shared_async_contract() -> None:
    """Prove dependency compatibility without constructing an MCP server."""
    fastmcp = importlib.import_module("fastmcp")
    if version("fastmcp") != "4.0.11":
        pytest.fail("compatibility environment must select FastMCP 4.0.11")
    if fastmcp is None:
        pytest.fail("FastMCP import unexpectedly resolved to no module")
    reader: EvidenceReader = SyntheticReader()
    reference = VersionRef(kind="synthetic", identity="fixture", version="1")
    result = asyncio.run(reader.read(reference))
    if result != b"synthetic:1":
        pytest.fail("shared async evidence boundary changed under FastMCP 4")


def test_runtime_probe_accepts_qualified_fastmcp() -> None:
    """Accept the real locked environment used by compatibility tests."""
    python_version = ".".join(str(part) for part in sys.version_info[:2])
    result = audit.runtime(python_version, True)
    if result["packages"]["fastmcp"] != "4.0.11":
        pytest.fail("runtime probe did not report the qualified FastMCP release")


@pytest.mark.parametrize("unqualified", ["4.0.10", "4.0.12"])
def test_runtime_probe_rejects_other_fastmcp_releases(
    monkeypatch: pytest.MonkeyPatch, unqualified: str
) -> None:
    """Reject both older and newer unqualified FastMCP installations."""

    def installed_version(name: str) -> str:
        return unqualified if name == "fastmcp" else version(name)

    monkeypatch.setattr(audit.importlib.metadata, "version", installed_version)
    python_version = ".".join(str(part) for part in sys.version_info[:2])
    with pytest.raises(ValueError, match="FastMCP"):
        audit.runtime(python_version, True)
