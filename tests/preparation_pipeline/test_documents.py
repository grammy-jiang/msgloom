"""Representative production parser coverage through the A2 handler."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    VersionRef,
)
from msgloom.preparation import (
    DocumentFormat,
    DocumentLocation,
    NativeRelationship,
    PreparedRecord,
    PreparedSourceType,
    SavedByteReference,
)
from msgloom.preparation_pipeline import PreparationHandler
from msgloom.sources import (
    CollectedAttachment,
    CollectedRecord,
    CollectedSourceReader,
    ContentKind,
)
from msgloom.sources._snapshot import capture_selection
from tests.parser_pdf.fixtures import build_text_pdf
from tests.parser_word.test_word_regressions import _simple_docx

from .helpers import open_store, plan, profiles


def _saved(name: str, content: bytes) -> SavedByteReference:
    return SavedByteReference(
        reference=f"fixture:{name}",
        sha256=hashlib.sha256(content).hexdigest(),
        byte_count=len(content),
    )


def test_spreadsheet_pdf_word_and_missing_content_are_explicit(tmp_path: Path) -> None:
    """Production parser registry handles common attachments without invention."""

    async def exercise() -> None:
        xls = Path("tests/parser_excel/fixtures/synthetic-cell-values.xls").read_bytes()
        pdf = build_text_pdf(b"Synthetic PDF text")
        docx = _simple_docx()
        opaque = b"synthetic unsupported bytes"
        payloads = {
            "fixture:sheet.xls": xls,
            "fixture:file.pdf": pdf,
            "fixture:file.docx": docx,
            "fixture:unknown.bin": opaque,
        }
        source = VersionRef("onedrive_item", "synthetic-item", "v1")
        scope = VersionRef("source_scope", "synthetic-drive", "v1")
        attachments = (
            CollectedAttachment(
                reference=VersionRef("attachment", "sheet.xls", "v1"),
                name="sheet.xls",
                content_type="application/vnd.ms-excel",
                content_kind=ContentKind.BINARY,
                byte_count=len(xls),
                inline=False,
                saved_bytes=_saved("sheet.xls", xls),
                location=DocumentLocation(part="attachment"),
            ),
            CollectedAttachment(
                reference=VersionRef("attachment", "file.pdf", "v1"),
                name="file.pdf",
                content_type="application/pdf",
                content_kind=ContentKind.BINARY,
                byte_count=len(pdf),
                inline=False,
                saved_bytes=_saved("file.pdf", pdf),
                location=DocumentLocation(part="attachment"),
            ),
            CollectedAttachment(
                reference=VersionRef("attachment", "file.docx", "v1"),
                name="file.docx",
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
                content_kind=ContentKind.BINARY,
                byte_count=len(docx),
                inline=False,
                saved_bytes=_saved("file.docx", docx),
                location=DocumentLocation(part="attachment"),
            ),
            CollectedAttachment(
                reference=VersionRef("attachment", "missing.bin", "v1"),
                name="missing.bin",
                content_type="application/octet-stream",
                content_kind=ContentKind.BINARY,
                byte_count=None,
                inline=False,
                saved_bytes=None,
                location=DocumentLocation(part="attachment"),
            ),
            CollectedAttachment(
                reference=VersionRef("attachment", "unknown.bin", "v1"),
                name="unknown.bin",
                content_type="application/octet-stream",
                content_kind=ContentKind.BINARY,
                byte_count=len(opaque),
                inline=False,
                saved_bytes=_saved("unknown.bin", opaque),
                location=DocumentLocation(part="attachment"),
            ),
        )
        record = CollectedRecord(
            source=source,
            source_scope=scope,
            source_type=PreparedSourceType.ONEDRIVE,
            semantic_identity="onedrive:synthetic",
            observed_at=datetime(2026, 9, 29, tzinfo=UTC),
            source_time=datetime(2026, 9, 29, tzinfo=UTC),
            subject="synthetic files",
            sender=None,
            author=None,
            recipients=(),
            source_content_kind=ContentKind.JSON,
            source_bytes=None,
            body=None,
            alternate_bodies=(),
            attachments=attachments,
            relationships=(NativeRelationship(kind="source_scope", target=scope),),
            metadata=(),
            source_locations=(DocumentLocation(part="synthetic"),),
            limitations=(),
        )
        selection = capture_selection(record)

        class FixtureReader:
            async def read_selection(self, requested):
                if requested != source:
                    pytest.fail("unexpected source")
                return selection

            async def load_saved_bytes(self, reference):
                try:
                    return payloads[reference.reference]
                except KeyError:
                    pytest.fail("unexpected byte reference")

        store = await open_store(tmp_path / "documents.sqlite3")
        try:
            handler = PreparationHandler(
                store,
                cast(CollectedSourceReader, FixtureReader()),
                plan(
                    source,
                    attempt=AttemptIdentity("documents-attempt"),
                    parser_profiles=profiles(
                        DocumentFormat.JSON,
                        DocumentFormat.XLS,
                        DocumentFormat.PDF,
                        DocumentFormat.DOCX,
                    ),
                ),
            )
            outcome = await handler.run(
                OperationRequest(
                    execution=ExecutionIdentity("documents-execution"),
                    caller="test",
                    capability=PhaseCapability.PREPARE,
                    target_inputs=(source,),
                )
            )
            if not outcome.result_refs:
                pytest.fail("document preparation produced no durable results")
            prepared_ref = next(
                ref for ref in outcome.result_refs if ref.kind == "prepared"
            )
            saved = await store.get_result(prepared_ref.result_id)
            if saved is None or saved.semantic_data_ref is None:
                pytest.fail("prepared document result is missing")
            value = await store.load_semantic_data(saved.semantic_data_ref)
            if not isinstance(value, PreparedRecord):
                pytest.fail("prepared document result has wrong type")
            formats = {
                item.output.provenance.detected_format for item in value.parsed_contents
            }
            for expected in (
                DocumentFormat.XLS,
                DocumentFormat.PDF,
                DocumentFormat.DOCX,
            ):
                if expected not in formats:
                    pytest.fail(f"production parser did not retain {expected}")
            codes = {
                item.code
                for attachment in value.attachments
                for item in attachment.limitations
            }
            if "missing-attachment-bytes" not in codes:
                pytest.fail("missing attachment was not an explicit limitation")
            if "unsupported-attachment-format" not in codes:
                pytest.fail("unsupported attachment was not an explicit limitation")
            if outcome.status.value != "incomplete":
                pytest.fail("missing content did not make operation incomplete")
        finally:
            await store.close()

    asyncio.run(exercise())
