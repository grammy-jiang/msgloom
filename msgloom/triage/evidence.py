"""Mechanically ground triage evidence in retained prepared content."""

from __future__ import annotations

import re
from dataclasses import dataclass

from msgloom.contracts import VersionRef
from msgloom.preparation import (
    DocumentLocation,
    PreparedRecord,
    SavedByteReference,
    SourceMapping,
    TableBlock,
    TextBlock,
)

from .models import EvidenceKind, TriageEvidence

_PARSED_FIELD = re.compile(
    r"parsed_contents\[(?P<parsed>\d+)\]\.blocks\[(?P<block>\d+)\]"
    r"(?:\.table\.cells\[(?P<cell>\d+)\])?"
)


class EvidenceGroundingError(ValueError):
    """Carry one opaque evidence-rejection code to reconciliation."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class _ResolvedText:
    """One exact text surface selected by a retained source mapping."""

    text: str


def validate_evidence(
    item: TriageEvidence,
    record: PreparedRecord,
    allowed_primary_sources: set[VersionRef],
) -> None:
    """Validate source membership and mechanical evidence grounding.

    Source statements are literal claims and must occur in the exact mapped
    text (and mapped range when present). Interpretations require an available,
    exact retained mapping, but this structural check does not establish that
    the semantic judgment is correct.
    """
    if item.source_ref not in allowed_primary_sources:
        raise EvidenceGroundingError("evidence-source-mismatch")
    if item.mapping is None:
        _validate_unmapped(item, record)
        return
    if item.mapping not in record.source_mappings:
        raise EvidenceGroundingError("invented-evidence-mapping")
    resolved = _resolve_mapping(record, item.mapping)
    text = _mapped_range(resolved.text, item.mapping)
    if item.kind is EvidenceKind.SOURCE_STATEMENT and item.statement not in text:
        raise EvidenceGroundingError("ungrounded-source-statement")


def _validate_unmapped(item: TriageEvidence, record: PreparedRecord) -> None:
    """Allow only literal statements found in primary subject/body text."""
    if item.kind is not EvidenceKind.SOURCE_STATEMENT:
        raise EvidenceGroundingError("ungrounded-interpretation")
    texts = tuple(value for value in (record.subject, record.body) if value)
    if not any(item.statement in value for value in texts):
        raise EvidenceGroundingError("ungrounded-source-statement")


def _resolve_mapping(record: PreparedRecord, mapping: SourceMapping) -> _ResolvedText:
    """Resolve a closed mapping vocabulary against actual retained content."""
    if mapping.field in {"subject", "body"}:
        return _resolve_primary_text(record, mapping)

    match = _PARSED_FIELD.fullmatch(mapping.field)
    if match is None:
        raise EvidenceGroundingError("unresolvable-evidence-mapping")
    parsed_index = int(match.group("parsed"))
    block_index = int(match.group("block"))
    cell_group = match.group("cell")
    try:
        parsed = record.parsed_contents[parsed_index]
        block = parsed.output.blocks[block_index]
    except IndexError:
        raise EvidenceGroundingError("unresolvable-evidence-mapping") from None
    _validate_parsed_owner(
        record, mapping, parsed.reference, parsed.output.provenance.source
    )

    if cell_group is not None:
        if not isinstance(block, TableBlock):
            raise EvidenceGroundingError("unresolvable-evidence-mapping")
        cell_index = int(cell_group)
        try:
            cell = block.table.cells[cell_index]
        except IndexError:
            raise EvidenceGroundingError("unresolvable-evidence-mapping") from None
        if cell.location != mapping.location or cell.text is None:
            raise EvidenceGroundingError("unresolvable-evidence-mapping")
        return _ResolvedText(cell.text)

    if isinstance(block, TextBlock):
        if block.location != mapping.location:
            raise EvidenceGroundingError("unresolvable-evidence-mapping")
        return _ResolvedText(block.text)
    if not isinstance(block, TableBlock):
        raise EvidenceGroundingError("unresolvable-evidence-mapping")
    return _resolve_table_location(block, mapping)


def _resolve_primary_text(
    record: PreparedRecord,
    mapping: SourceMapping,
) -> _ResolvedText:
    """Resolve a primary subject/body mapping without arbitrary expressions."""
    if mapping.source != record.source:
        raise EvidenceGroundingError("invented-evidence-mapping")
    if not isinstance(mapping.location, DocumentLocation):
        raise EvidenceGroundingError("unresolvable-evidence-mapping")
    value = record.subject if mapping.field == "subject" else record.body
    if value is None:
        raise EvidenceGroundingError("unresolvable-evidence-mapping")
    return _ResolvedText(value)


def _validate_parsed_owner(
    record: PreparedRecord,
    mapping: SourceMapping,
    parsed_ref: VersionRef,
    parsed_source: SavedByteReference,
) -> None:
    """Require the mapping source to own the selected parsed output exactly."""
    if mapping.source == parsed_ref:
        return
    for attachment in record.attachments:
        if (
            attachment.reference == mapping.source
            and attachment.parsed_content_ref == parsed_ref
            and attachment.saved_bytes is not None
            and attachment.saved_bytes == parsed_source
        ):
            return
    raise EvidenceGroundingError("invented-evidence-mapping")


def _resolve_table_location(
    block: TableBlock,
    mapping: SourceMapping,
) -> _ResolvedText:
    """Resolve a table location or one uniquely located cell."""
    table = block.table
    if mapping.location == table.location:
        texts = tuple(
            cell.text
            for cell in sorted(
                table.cells,
                key=lambda item: (item.row_index, item.column_index),
            )
            if cell.text is not None
        )
        return _ResolvedText("\n".join(texts))

    matches = tuple(
        cell
        for cell in table.cells
        if cell.location == mapping.location and cell.text is not None
    )
    if len(matches) != 1:
        raise EvidenceGroundingError("unresolvable-evidence-mapping")
    return _ResolvedText(matches[0].text or "")


def _mapped_range(text: str, mapping: SourceMapping) -> str:
    """Apply an exact retained character range to the resolved text."""
    if mapping.start is None or mapping.end is None:
        return text
    if mapping.end > len(text):
        raise EvidenceGroundingError("invalid-evidence-range")
    return text[mapping.start : mapping.end]
