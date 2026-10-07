"""Reject malformed exact Contact references before reading saved data."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from urllib.parse import quote

import pytest

from msgloom.contracts import VersionRef
from msgloom.sources import (
    SavedSourceReader,
    SavedSourceReaderConfig,
    SourceReferenceError,
)


@pytest.mark.parametrize("selection", (False, True))
@pytest.mark.parametrize(
    "ordinal",
    (
        "synthetic-private-marker",
        "",
        "-1",
        "+0",
        "0 ",
        "01",
        "1_0",
        "０",
        "1" * 21,
        "9223372036854775808",
    ),
)
def test_malformed_delta_ordinal_has_one_opaque_public_failure(
    tmp_path: Path, ordinal: str, selection: bool
) -> None:
    """Both public read methods reject invalid noncanonical SQLite ordinals."""
    database = tmp_path / "catalog.sqlite3"
    sqlite3.connect(database).close()
    root = tmp_path / "evidence"
    root.mkdir()
    source = VersionRef(
        "contact",
        "synthetic-source/folder%3Asynthetic-folder/synthetic-contact",
        f"delta/synthetic-run/{quote(ordinal, safe='')}/synthetic-evidence",
    )

    async def exercise() -> None:
        reader = SavedSourceReader(
            SavedSourceReaderConfig(
                catalog_path=database,
                evidence_roots=(root,),
            )
        )
        try:
            with pytest.raises(SourceReferenceError) as caught:
                if selection:
                    await reader.read_selection(source)
                else:
                    await reader.read(source)
            if str(caught.value) != "Contact delta ordinal is malformed":
                pytest.fail("malformed ordinal exposed a different public error")
            if caught.value.__cause__ is not None:
                pytest.fail("malformed ordinal exposed a chained private value")
        finally:
            await reader.close()

    asyncio.run(exercise())
