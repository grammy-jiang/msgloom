"""R3 closure tests for saved-source codec, WAL, and replay boundaries."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest

from msgloom.persistence.semantic import SemanticDataRegistry
from msgloom.preparation.records import PreparedSourceType
from msgloom.sources import (
    MAX_COLLECTED_SELECTION_BYTES,
    CollectedSelectionCodec,
    ContentKind,
    SavedSourceReader,
    SavedSourceReaderConfig,
    SourceReferenceError,
)
from msgloom.sources._snapshot import capture_selection, decode_selection


def _reader(fixture: dict[str, object]) -> SavedSourceReader:
    return SavedSourceReader(
        SavedSourceReaderConfig(
            catalog_path=cast(Path, fixture["database"]),
            evidence_roots=(cast(Path, fixture["evidence_root"]),),
        )
    )


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def test_codec_rejects_model_copy_bypass_without_warning_or_value_leak(
    saved_catalog,
) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)
        source = next(
            ref
            for ref in await reader.list_versions(
                PreparedSourceType.OUTLOOK_EMAIL,
                source_id=cast(str, saved_catalog["source_id"]),
                limit=10,
            )
            if ref.version == "obs-current"
        )
        selection = await reader.read_selection(source)
        body = selection.record.body
        if body is None:
            pytest.fail("Synthetic Outlook record has no body")

        bad_kind = selection.model_copy(
            update={
                "record": selection.record.model_copy(
                    update={"body": body.model_copy(update={"kind": "plain"})}
                )
            }
        )
        with pytest.raises(SourceReferenceError, match="snapshot is invalid"):
            await reader.encode_selection(bad_kind)

        private_marker = "synthetic-private-marker"
        bad_subject = selection.model_copy(
            update={
                "record": selection.record.model_copy(
                    update={"subject": {private_marker: "value"}}
                )
            }
        )
        with pytest.raises(SourceReferenceError) as caught:
            await reader.encode_selection(bad_subject)
        if private_marker in str(caught.value):
            pytest.fail("Malformed nested value leaked through public codec error")

        bad_record = selection.record.model_copy(
            update={"body": body.model_copy(update={"kind": "plain"})}
        )
        with pytest.raises(SourceReferenceError, match="collected record is invalid"):
            capture_selection(bad_record)
        await reader.close()

    asyncio.run(scenario())


def test_codec_is_registry_compatible_and_rejects_noncanonical_shapes(
    saved_catalog,
) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)
        source = next(
            ref
            for ref in await reader.list_versions(
                PreparedSourceType.OUTLOOK_EMAIL,
                source_id=cast(str, saved_catalog["source_id"]),
                limit=10,
            )
            if ref.version == "obs-current"
        )
        selection = await reader.read_selection(source)
        codec = CollectedSelectionCodec()
        if codec.max_bytes != MAX_COLLECTED_SELECTION_BYTES:
            pytest.fail("Collected selection codec ceiling changed unexpectedly")
        registry = SemanticDataRegistry((codec,))
        encoded = registry.encode(
            "synthetic-selection",
            codec.kind,
            codec.schema_version,
            selection,
        )
        if registry.decode(encoded.reference, encoded.payload) != selection:
            pytest.fail("Semantic registry did not replay collected selection")

        data = encoded.payload
        malformed = (
            data.replace(b'{"record":', b'{"record":null,"record":', 1),
            data[:-1] + b',"unknown":1}',
            data[:-1] + b',"nonfinite":NaN}',
            data + b"\n",
        )
        for payload in malformed:
            with pytest.raises(ValueError):
                codec.decode(payload)

        parsed = json.loads(data)
        parsed["record"]["subject"] = 7
        with pytest.raises(ValueError):
            codec.decode(_canonical(parsed))

        with pytest.raises(SourceReferenceError, match="configured limit"):
            decode_selection(data, len(data) - 1)
        with pytest.raises(ValueError, match="codec byte limit"):
            codec.decode(b"x" * (codec.max_bytes + 1))
        await reader.close()

    asyncio.run(scenario())


def test_restart_replay_preserves_locations_kinds_metadata_and_byte_identity(
    saved_catalog,
) -> None:
    async def scenario() -> None:
        reader = _reader(saved_catalog)
        source = next(
            ref
            for ref in await reader.list_versions(
                PreparedSourceType.OUTLOOK_EMAIL,
                source_id=cast(str, saved_catalog["source_id"]),
                limit=10,
            )
            if ref.version == "obs-current"
        )
        selection = await reader.read_selection(source)
        encoded = await reader.encode_selection(selection)
        await reader.close()

        with sqlite3.connect(cast(Path, saved_catalog["database"])) as connection:
            connection.execute(
                "UPDATE message_surfaces SET status = 'failed' "
                "WHERE surface LIKE 'attachment_raw:%'"
            )

        restarted = _reader(saved_catalog)
        replay = await restarted.decode_selection(encoded)
        if replay != selection:
            pytest.fail("Restart replay changed the captured selection")
        record = replay.record
        if record.body is None or record.body.kind is not ContentKind.HTML:
            pytest.fail("Body content kind did not survive restart replay")
        if record.body.location not in record.source_locations:
            pytest.fail("Body source location did not survive restart replay")
        if not record.metadata:
            pytest.fail("Provider-neutral metadata did not survive restart replay")
        if (
            record.source_bytes is None
            or record.body.saved_bytes != record.source_bytes
        ):
            pytest.fail("Graph response byte identity changed during replay")
        graph_bytes = await restarted.load_saved_bytes(record.source_bytes)
        if record.body.content is None:
            pytest.fail("Synthetic Outlook body content is unavailable")
        if graph_bytes == record.body.content.encode("utf-8"):
            pytest.fail("Extracted body text was mislabeled as whole-response bytes")
        if b'"body"' not in graph_bytes:
            pytest.fail("Whole Graph response evidence was not replayable")
        if not record.attachments or record.attachments[0].saved_bytes is None:
            pytest.fail("Captured attachment byte identity was lost")
        attachment = record.attachments[0].saved_bytes
        if await restarted.load_saved_bytes(attachment) != b"synthetic attachment":
            pytest.fail("Captured attachment bytes changed across restart")
        await restarted.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("failure_point", ("setup", "query"))
def test_sqlite_failure_closes_open_connection(saved_catalog, failure_point) -> None:
    real_connect = sqlite3.connect
    opened = []

    class FailingConnection(sqlite3.Connection):
        was_closed = False

        def execute(self, sql, parameters=()):
            setup_failure = failure_point == "setup" and sql == "PRAGMA query_only = ON"
            query_failure = failure_point == "query" and sql.startswith(
                "SELECT observation_id, message_id"
            )
            if setup_failure or query_failure:
                raise sqlite3.OperationalError("synthetic catalog failure")
            return super().execute(sql, parameters)

        def close(self) -> None:
            self.was_closed = True
            super().close()

    def failing_connect(*args, **kwargs):
        kwargs["factory"] = FailingConnection
        connection = real_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    async def scenario() -> None:
        with patch("msgloom.sources._catalog.sqlite3.connect", failing_connect):
            reader = _reader(saved_catalog)
            with pytest.raises(SourceReferenceError, match="catalog query failed"):
                await reader.list_versions(
                    PreparedSourceType.OUTLOOK_EMAIL,
                    source_id=cast(str, saved_catalog["source_id"]),
                    limit=10,
                )
            await reader.close()

    asyncio.run(scenario())
    if not opened or any(not connection.was_closed for connection in opened):
        pytest.fail("SQLite failure leaked an opened connection")


def test_active_wal_catalog_remains_readable_without_reader_writes(
    saved_catalog,
) -> None:
    database = cast(Path, saved_catalog["database"])
    writer = sqlite3.connect(database)
    try:
        mode = writer.execute("PRAGMA journal_mode=WAL").fetchone()
        if mode is None or mode[0].lower() != "wal":
            pytest.fail("Synthetic catalog did not enter WAL mode")
        writer.execute(
            "UPDATE message_observations SET parent_folder_id = ? "
            "WHERE observation_id = 'obs-current'",
            ("synthetic-wal-folder",),
        )
        writer.commit()
        tables = (
            "source_bindings",
            "raw_http_evidence",
            "messages",
            "message_observations",
            "message_surfaces",
            "attachments",
        )
        before = {
            table: writer.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in tables
        }
        writer.execute("BEGIN IMMEDIATE")
        writer.execute(
            "UPDATE messages SET is_removed = is_removed WHERE message_id = 'message'"
        )

        async def scenario() -> None:
            reader = _reader(saved_catalog)
            source = next(
                ref
                for ref in await reader.list_versions(
                    PreparedSourceType.OUTLOOK_EMAIL,
                    source_id=cast(str, saved_catalog["source_id"]),
                    limit=10,
                )
                if ref.version == "obs-current"
            )
            record = await reader.read(source)
            if record.source_bytes is None:
                pytest.fail("Committed saved evidence was unavailable in WAL mode")
            data = await reader.load_saved_bytes(record.source_bytes)
            if b'"id":"message"' not in data:
                pytest.fail("WAL read returned the wrong saved evidence")
            await reader.close()

        asyncio.run(scenario())
        writer.rollback()
        after = {
            table: writer.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in tables
        }
        if after != before:
            pytest.fail("Read-only source adapter changed A1 source tables")
    finally:
        if writer.in_transaction:
            writer.rollback()
        writer.close()


def test_saved_evidence_rejects_fifo_without_opening_it(saved_catalog) -> None:
    from msgloom.sources._catalog import EvidenceRow
    from msgloom.sources._io import EvidenceFiles
    from msgloom.sources.models import SourceEvidenceError

    root = cast(Path, saved_catalog["evidence_root"])
    fifo = root / "synthetic.fifo"
    os.mkfifo(fifo)
    row = EvidenceRow(
        evidence_id="synthetic-fifo",
        source_id=cast(str, saved_catalog["source_id"]),
        observed_at="2026-09-29T00:00:00+00:00",
        purpose="synthetic",
        response_body_sha256=hashlib.sha256(b"").hexdigest(),
        response_body_path=str(fifo),
        response_body_bytes=0,
    )
    files = EvidenceFiles((root,), 1024)
    try:
        with pytest.raises(SourceEvidenceError, match="not a regular file"):
            files.read(row)
    finally:
        files.close()
