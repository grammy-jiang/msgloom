"""Exercise only the shared typed/async boundary with FastMCP 4 installed."""

from __future__ import annotations

import asyncio
import importlib
import os
from importlib.metadata import version

import pytest

from msgloom.contracts import EvidenceReader, VersionRef

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
    if version("fastmcp") != "4.0.10":
        pytest.fail("compatibility environment must select FastMCP 4.0.10")
    if fastmcp is None:
        pytest.fail("FastMCP import unexpectedly resolved to no module")
    reader: EvidenceReader = SyntheticReader()
    reference = VersionRef(kind="synthetic", identity="fixture", version="1")
    result = asyncio.run(reader.read(reference))
    if result != b"synthetic:1":
        pytest.fail("shared async evidence boundary changed under FastMCP 4")
