"""Contract tests for persistence-free parser preparation types."""

from __future__ import annotations

from dataclasses import fields, replace
from typing import Any, cast

import pytest

from msgloom.preparation import (
    BlockRole,
    CellLocation,
    DocumentFormat,
    DocumentLocation,
    LimitationKind,
    LinkBlock,
    MimePartLocation,
    MimePartReference,
    PageLocation,
    ParsedCell,
    ParsedLink,
    ParsedTable,
    ParserConfig,
    ParserIdentity,
    ParserLimitation,
    ParserLimits,
    ParserOutput,
    ParserProvenance,
    ParserRequest,
    SavedByteReference,
    SheetLocation,
    TableBlock,
    TextBlock,
)


def _request() -> ParserRequest:
    return ParserRequest(
        source=SavedByteReference(
            reference="blob:sha256:synthetic",
            sha256="ab" * 32,
            byte_count=128,
        ),
        detected_format=DocumentFormat.XLSX,
        parser=ParserIdentity(
            name="python-calamine",
            version="0.8.2",
            backend="calamine",
        ),
        config=ParserConfig(
            profile="excel-primary-v1",
            settings=(("hidden_sheets", "record"),),
        ),
        limits=ParserLimits(
            wall_time_seconds=10.0,
            memory_bytes=256 * 1024 * 1024,
            decompressed_bytes=64 * 1024 * 1024,
            output_bytes=8 * 1024 * 1024,
            container_members=2048,
        ),
    )


def test_parser_request_binds_saved_bytes_parser_config_and_limits() -> None:
    """The worker request carries only already-saved input identity and policy."""
    request = _request()
    if request.source.reference != "blob:sha256:synthetic":
        pytest.fail("Expected the opaque saved-byte reference to be retained")
    if request.detected_format is not DocumentFormat.XLSX:
        pytest.fail("Expected the detected format to be retained")
    if request.parser.backend != "calamine":
        pytest.fail("Expected the exact parser backend identity")
    if request.config.settings != (("hidden_sheets", "record"),):
        pytest.fail("Expected deterministic parser settings")
    if request.limits.container_members != 2048:
        pytest.fail("Expected bounded container-member policy")


def test_parser_output_preserves_order_locations_links_and_mime_refs() -> None:
    """Structured output retains meaningful order and source mappings."""
    request = _request()
    link = ParsedLink(
        target="https://example.invalid/reference",
        text="reference",
        location=DocumentLocation(part="html", block_index=0),
    )
    cell = ParsedCell(
        row_index=1,
        column_index=1,
        text="7",
        value_type="number",
        location=CellLocation(
            sheet_name="Visible",
            row=3,
            column=2,
            coordinate="B3",
        ),
        formula="SUM(A1:A2)",
        cached_value="7",
        merged_range="B3:C3",
        links=(link,),
    )
    table = ParsedTable(
        row_count=1,
        column_count=1,
        cells=(cell,),
        location=SheetLocation(sheet_name="Visible"),
    )
    output = ParserOutput(
        provenance=ParserProvenance.from_request(request),
        blocks=(
            TextBlock(
                order=0,
                role=BlockRole.PARAGRAPH,
                text="before",
                location=DocumentLocation(part="document", block_index=0),
            ),
            LinkBlock(order=1, link=link),
            TableBlock(order=2, table=table),
            TextBlock(
                order=3,
                role=BlockRole.TEXT,
                text="page text",
                location=PageLocation(page_number=1),
            ),
        ),
        mime_parts=(
            MimePartReference(
                part_ref="1",
                parent_ref=None,
                content_type="multipart/alternative",
                disposition=None,
                content_id=None,
                location=MimePartLocation(part_ref="1"),
            ),
            MimePartReference(
                part_ref="1.2",
                parent_ref="1",
                content_type="text/html",
                disposition=None,
                content_id=None,
                location=MimePartLocation(part_ref="1.2"),
            ),
        ),
        limitations=(
            ParserLimitation(
                kind=LimitationKind.PARTIAL,
                code="embedded-object",
                detail="Embedded object content was not extracted.",
                feature="embedded-object",
                location=DocumentLocation(part="word/document.xml", block_index=3),
            ),
        ),
    )
    if tuple(block.order for block in output.blocks) != (0, 1, 2, 3):
        pytest.fail("Expected contiguous source block order")
    table_block = output.blocks[2]
    if not isinstance(table_block, TableBlock):
        pytest.fail("Expected table block at source order 2")
    cell_location = table_block.table.cells[0].location
    if not isinstance(cell_location, CellLocation):
        pytest.fail("Expected exact spreadsheet cell location type")
    if cell_location.coordinate != "B3":
        pytest.fail("Expected exact spreadsheet cell location")
    if output.mime_parts[1].part_ref != "1.2":
        pytest.fail("Expected MIME tree relationship reference")
    if output.limitations[0].kind is not LimitationKind.PARTIAL:
        pytest.fail("Expected explicit partial-extraction limitation")


@pytest.mark.parametrize(
    "kind",
    [
        LimitationKind.MISSING,
        LimitationKind.UNSUPPORTED,
        LimitationKind.PARTIAL,
        LimitationKind.ENCRYPTED,
        LimitationKind.SCANNED,
    ],
)
def test_all_required_limitation_kinds_are_explicit(kind: LimitationKind) -> None:
    """Missing, unsupported, partial, encrypted, and scanned are first-class."""
    limitation = ParserLimitation(
        kind=kind,
        code=f"synthetic-{kind.value}",
        detail="Synthetic limitation.",
    )
    if limitation.kind is not kind:
        pytest.fail(f"Expected limitation kind {kind.value}")


def test_parser_output_cannot_mark_application_attempt_complete() -> None:
    """Worker output deliberately exposes no durable attempt-completion field."""
    field_names = {field.name for field in fields(ParserOutput)}
    forbidden = {"status", "complete", "completed", "attempt_status", "result_id"}
    overlap = field_names & forbidden
    if overlap:
        pytest.fail(f"ParserOutput must not own Application completion: {overlap}")


def test_output_rejects_noncontiguous_block_order() -> None:
    """Meaningful order cannot be represented by gaps or duplicate positions."""
    with pytest.raises(ValueError, match="contiguous and zero-based"):
        ParserOutput(
            provenance=ParserProvenance.from_request(_request()),
            blocks=(
                TextBlock(
                    order=1,
                    role=BlockRole.TEXT,
                    text="out of order",
                    location=DocumentLocation(part="document"),
                ),
            ),
        )


def test_contracts_reject_invalid_digest_limits_and_duplicate_settings() -> None:
    """Invalid worker inputs fail before a parser process is launched."""
    with pytest.raises(ValueError, match="64 hexadecimal"):
        SavedByteReference(reference="blob:x", sha256="bad", byte_count=1)
    with pytest.raises(ValueError, match="positive"):
        ParserLimits(
            wall_time_seconds=0,
            memory_bytes=1,
            decompressed_bytes=1,
            output_bytes=1,
            container_members=1,
        )
    with pytest.raises(ValueError, match="duplicate parser setting"):
        ParserConfig(profile="x", settings=(("mode", "a"), ("mode", "b")))


def test_saved_byte_reference_accepts_zero_byte_evidence() -> None:
    """An empty persisted object is still valid parser input evidence."""
    source = SavedByteReference(
        reference="blob:sha256:empty",
        sha256="00" * 32,
        byte_count=0,
    )
    if source.byte_count != 0:
        pytest.fail("Expected empty saved-byte evidence to retain byte_count=0")


@pytest.mark.parametrize("byte_count", [-1, True, 1.5])
def test_saved_byte_reference_rejects_invalid_byte_counts(
    byte_count: object,
) -> None:
    """Saved byte counts are nonnegative integers, never booleans/fractions."""
    with pytest.raises((TypeError, ValueError), match="byte_count"):
        SavedByteReference(
            reference="blob:sha256:invalid-count",
            sha256="00" * 32,
            byte_count=cast(Any, byte_count),
        )


@pytest.mark.parametrize(
    "wall_time",
    [0, -1, float("nan"), float("inf"), float("-inf"), True, "1"],
)
def test_parser_limits_reject_invalid_wall_times(wall_time: object) -> None:
    """Wall time is a finite positive real number, excluding booleans."""
    with pytest.raises((TypeError, ValueError), match="wall_time_seconds"):
        replace(_request().limits, wall_time_seconds=cast(Any, wall_time))


@pytest.mark.parametrize(
    "field",
    ["memory_bytes", "decompressed_bytes", "output_bytes", "container_members"],
)
@pytest.mark.parametrize("invalid", [0, -1, True, 1.5, float("nan")])
def test_parser_limits_require_strict_positive_integer_ceilings(
    field: str,
    invalid: object,
) -> None:
    """Byte/member ceilings cannot be fractional, boolean, zero, or negative."""
    with pytest.raises((TypeError, ValueError), match=field):
        replace(_request().limits, **{field: cast(Any, invalid)})


@pytest.mark.parametrize("invalid", [True, 1.5])
def test_source_coordinates_require_strict_integers(invalid: object) -> None:
    """Page, row, column, and document indexes retain exact integer locations."""
    value = cast(Any, invalid)
    with pytest.raises(TypeError, match="page_number"):
        PageLocation(page_number=value)
    with pytest.raises(TypeError, match="row"):
        CellLocation(sheet_name="S", row=value, column=1, coordinate="A1")
    with pytest.raises(TypeError, match="column"):
        CellLocation(sheet_name="S", row=1, column=value, coordinate="A1")
    with pytest.raises(TypeError, match="block_index"):
        DocumentLocation(part="document", block_index=value)


@pytest.mark.parametrize("invalid", [True, 1.5])
def test_table_coordinates_counts_and_block_orders_require_integers(
    invalid: object,
) -> None:
    """Structured indexes/counts cannot silently coerce booleans or fractions."""
    value = cast(Any, invalid)
    location = CellLocation(sheet_name="S", row=1, column=1, coordinate="A1")
    with pytest.raises(TypeError, match="row_index"):
        ParsedCell(
            row_index=value,
            column_index=1,
            text=None,
            value_type=None,
            location=location,
        )
    with pytest.raises(TypeError, match="column_index"):
        ParsedCell(
            row_index=1,
            column_index=value,
            text=None,
            value_type=None,
            location=location,
        )
    with pytest.raises(TypeError, match="row_count"):
        ParsedTable(
            row_count=value,
            column_count=1,
            cells=(),
            location=SheetLocation(sheet_name="S"),
        )
    with pytest.raises(TypeError, match="column_count"):
        ParsedTable(
            row_count=1,
            column_count=value,
            cells=(),
            location=SheetLocation(sheet_name="S"),
        )
    with pytest.raises(TypeError, match="order"):
        TextBlock(
            order=value,
            role=BlockRole.TEXT,
            text="x",
            location=DocumentLocation(part="document"),
        )


def _mime_part(part_ref: str, parent_ref: str | None) -> MimePartReference:
    return MimePartReference(
        part_ref=part_ref,
        parent_ref=parent_ref,
        content_type="multipart/mixed" if parent_ref is None else "text/plain",
        disposition=None,
        content_id=None,
        location=MimePartLocation(part_ref=part_ref),
    )


def test_parser_output_requires_declared_acyclic_mime_parents() -> None:
    """MIME parent refs stay inside the declared tree and cannot form cycles."""
    provenance = ParserProvenance.from_request(_request())
    output = ParserOutput(
        provenance=provenance,
        mime_parts=(_mime_part("1", None), _mime_part("1.1", "1")),
    )
    if output.mime_parts[1].parent_ref != "1":
        pytest.fail("Expected declared MIME parent relationship to be retained")

    with pytest.raises(ValueError, match="declared MIME part"):
        ParserOutput(
            provenance=provenance,
            mime_parts=(_mime_part("1.1", "1"),),
        )
    with pytest.raises(ValueError, match="cycle"):
        ParserOutput(
            provenance=provenance,
            mime_parts=(_mime_part("1", "1.1"), _mime_part("1.1", "1")),
        )


def test_contract_collections_reject_mutable_list_inputs() -> None:
    """Frozen contracts do not retain mutable caller-owned collection lists."""
    with pytest.raises(TypeError, match="settings must be a tuple"):
        ParserConfig(profile="x", settings=cast(Any, [["mode", "safe"]]))
    with pytest.raises(TypeError, match="blocks must be a tuple"):
        ParserOutput(
            provenance=ParserProvenance.from_request(_request()),
            blocks=cast(Any, []),
        )
