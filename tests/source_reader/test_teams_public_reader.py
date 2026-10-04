"""Qualify Teams through the public saved-source selection and replay API."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

from msgloom.preparation.records import PreparedSourceType
from msgloom.sources import SavedSourceReader, SavedSourceReaderConfig
from tests.source_reader.test_teams_saved_history import _add_history
from tests.source_reader.test_teams_saved_selection import _add_later_edit
from tests.source_reader.test_teams_saved_source import SOURCE, _build_fixture


def test_public_teams_selection_replays_after_catalog_changes(tmp_path: Path) -> None:
    """Public list/read/read-many and snapshot replay share the Teams adapter."""
    fixture = _build_fixture(tmp_path)
    config = SavedSourceReaderConfig(
        catalog_path=fixture.database,
        evidence_roots=(fixture.evidence_root,),
    )

    async def exercise() -> None:
        reader = SavedSourceReader(config)
        try:
            chats = await reader.list_versions(
                PreparedSourceType.TEAMS_CHAT_MESSAGE, source_id=SOURCE, limit=10
            )
            channels = await reader.list_versions(
                PreparedSourceType.TEAMS_CHANNEL_MESSAGE, source_id=SOURCE, limit=10
            )
            if set(chats) != {fixture.chat_a, fixture.chat_b}:
                pytest.fail("Public reader did not list both scoped chat observations")
            if set(channels) != {fixture.channel_root, fixture.channel_reply}:
                pytest.fail("Public reader did not list channel root and reply")
            selected = await reader.read_selection(fixture.chat_a)
            encoded = await reader.encode_selection(selected)
            records = await reader.read_many((fixture.chat_a, fixture.channel_reply))
            if (
                records[0] != selected.record
                or records[1].source != fixture.channel_reply
            ):
                pytest.fail("Public read-many changed caller order or adapter mapping")
        finally:
            await reader.close()
        _add_history(fixture)
        _add_later_edit(fixture)
        reopened = SavedSourceReader(config)
        try:
            replay = await reopened.decode_selection(encoded)
            if replay != selected:
                pytest.fail("Public snapshot replay changed after catalog mutation")
            if replay.record.source_bytes is None:
                pytest.fail("Public snapshot lost its exact raw evidence reference")
            saved = await reopened.load_saved_bytes(replay.record.source_bytes)
            if saved != (fixture.evidence_root / "chat-a-v1.bin").read_bytes():
                pytest.fail("Public byte replay did not return original evidence")
            fresh = await reopened.read_selection(fixture.chat_a)
            if fresh.selection == selected.selection:
                pytest.fail("Fresh selection ignored later additive history")
            if fresh.record.body != selected.record.body:
                pytest.fail("Later history rewrote the selected old message body")
            if await reopened.read(fixture.chat_a) != fresh.record:
                pytest.fail("Public read bypassed the selected Teams adapter")
        finally:
            await reopened.close()

    asyncio.run(exercise())


def test_public_teams_read_needs_no_acquisition_runtime(tmp_path: Path) -> None:
    """A new process reads committed Teams data with provider imports forbidden."""
    fixture = _build_fixture(tmp_path)
    script = """
import asyncio
import importlib.abc
import sys
from pathlib import Path

class AcquisitionBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'scrapy', 'msal', 'microsoft_graph', 'message_ingest'}:
            raise RuntimeError('Saved-source read imported acquisition runtime')
        return None

sys.meta_path.insert(0, AcquisitionBlocker())
from msgloom.preparation.records import PreparedSourceType
from msgloom.sources import SavedSourceReader, SavedSourceReaderConfig

async def main():
    reader = SavedSourceReader(SavedSourceReaderConfig(
        catalog_path=Path(sys.argv[1]), evidence_roots=(Path(sys.argv[2]),)))
    try:
        for kind in (PreparedSourceType.TEAMS_CHAT_MESSAGE,
                     PreparedSourceType.TEAMS_CHANNEL_MESSAGE):
            refs = await reader.list_versions(kind, source_id=sys.argv[3], limit=10)
            if len(refs) != 2:
                raise RuntimeError('Wrong public Teams version inventory')
            for ref in refs:
                selected = await reader.read_selection(ref)
                if selected.record.source_bytes is None:
                    raise RuntimeError('Missing source evidence')
                await reader.load_saved_bytes(selected.record.source_bytes)
    finally:
        await reader.close()

asyncio.run(main())
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(fixture.database),
            str(fixture.evidence_root),
            SOURCE,
        ],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr[-4000:])
