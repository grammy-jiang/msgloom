"""Synthetic prepared-data fixtures with no provider content."""

from datetime import UTC, datetime
from pathlib import Path

from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    Limitation,
    SemanticDataRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.preparation import (
    BlockRole,
    CellLocation,
    DocumentFormat,
    DocumentLocation,
    FilteringDecision,
    FilteringDisposition,
    NativeRelationship,
    PageLocation,
    ParsedCell,
    ParsedTable,
    ParserConfig,
    ParserIdentity,
    ParserLimitation,
    ParserOutput,
    ParserProvenance,
    PreparedAttachment,
    PreparedParty,
    PreparedRecipient,
    PreparedRecord,
    PreparedSourceType,
    RecipientRole,
    ReferencedParserOutput,
    SavedByteReference,
    SheetLocation,
    SourceMapping,
    TableBlock,
    TextBlock,
)
from msgloom.preparation.contracts import LimitationKind


def phase1_url(path: Path) -> str:
    """Return the file-backed SQLite URL used by synthetic tests."""
    return f"sqlite:///{path}"


def saved_bytes() -> SavedByteReference:
    """Return an evidence-owned synthetic attachment reference."""
    return SavedByteReference(
        reference="evidence:synthetic-attachment",
        sha256="ab" * 32,
        byte_count=128,
    )


def parser_output() -> ParserOutput:
    """Return ordered parser content with exact table and page locations."""
    provenance = ParserProvenance(
        source=saved_bytes(),
        detected_format=DocumentFormat.XLSX,
        parser=ParserIdentity("python-calamine", "0.8.2", "calamine"),
        config=ParserConfig("excel-primary-v1"),
    )
    table = ParsedTable(
        row_count=1,
        column_count=1,
        cells=(
            ParsedCell(
                row_index=1,
                column_index=1,
                text="42",
                value_type="number",
                location=CellLocation("Budget", 7, 2, "B7"),
            ),
        ),
        location=SheetLocation("Budget"),
    )
    return ParserOutput(
        provenance=provenance,
        blocks=(
            TextBlock(
                order=0,
                role=BlockRole.PARAGRAPH,
                text="Attachment heading",
                location=DocumentLocation("workbook", 0),
            ),
            TableBlock(order=1, table=table),
            TextBlock(
                order=2,
                role=BlockRole.TEXT,
                text="Page note",
                location=PageLocation(1),
            ),
        ),
        limitations=(
            ParserLimitation(
                kind=LimitationKind.PARTIAL,
                code="synthetic-gap",
                detail="Synthetic unsupported workbook feature.",
                location=CellLocation("Budget", 7, 2, "B7"),
            ),
        ),
    )


def prepared_record(
    *, body: str = "Please review the attached budget."
) -> PreparedRecord:
    """Return one complete synthetic prepared source record."""
    source = VersionRef("outlook_email", "message-1", "v3")
    parsed_ref = VersionRef("parsed_content", "attachment-1", "parser-v1")
    attachment_ref = VersionRef("attachment", "attachment-1", "v1")
    return PreparedRecord(
        source=source,
        source_type=PreparedSourceType.OUTLOOK_EMAIL,
        sender=PreparedParty(identity="sender-1", display_name="Synthetic Sender"),
        author=PreparedParty(identity="author-1", display_name="Synthetic Author"),
        recipients=(
            PreparedRecipient(
                party=PreparedParty(identity="recipient-1"),
                role=RecipientRole.TO,
            ),
        ),
        source_time=datetime(2026, 9, 29, 7, 15, tzinfo=UTC),
        subject="Synthetic budget review",
        body=body,
        relationships=(
            NativeRelationship(
                kind="in_reply_to",
                target=VersionRef("outlook_email", "message-0", "v2"),
            ),
        ),
        attachments=(
            PreparedAttachment(
                reference=attachment_ref,
                saved_bytes=saved_bytes(),
                parsed_content_ref=parsed_ref,
                limitations=(),
            ),
        ),
        parsed_contents=(
            ReferencedParserOutput(reference=parsed_ref, output=parser_output()),
        ),
        limitations=(Limitation("synthetic", "Synthetic preparation limitation."),),
        source_mappings=(
            SourceMapping(
                source=source,
                field="body",
                location=DocumentLocation("message-body", 0),
                start=0,
                end=len(body),
            ),
            SourceMapping(
                source=attachment_ref,
                field="parsed_contents[0].blocks[1]",
                location=CellLocation("Budget", 7, 2, "B7"),
            ),
        ),
        filtering=FilteringDecision(disposition=FilteringDisposition.PENDING),
    )


def prepared_result(
    reference: SemanticDataRef | None, *, result_id: str = "prepared-1"
) -> StageResult:
    """Return one acceptable prepared stage result with exact lineage."""
    return StageResult(
        result_id=result_id,
        kind="prepared",
        schema_version="1",
        execution=ExecutionIdentity(f"execution-{result_id}"),
        attempt=AttemptIdentity(f"attempt-{result_id}"),
        input_refs=(),
        source_versions=(VersionRef("outlook_email", "message-1", "v3"),),
        prepared_versions=(VersionRef("prepared", result_id, "v1"),),
        topic_versions=(),
        configuration_version="config-v1",
        code_version="build-v1",
        rule_version="filter-rules-v1",
        status=TerminalStatus.COMPLETE,
        acceptable=True,
        semantic_data_ref=reference,
    )
