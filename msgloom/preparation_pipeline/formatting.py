"""Deterministic content routing and prepared mapping helpers."""

from __future__ import annotations

import json
from pathlib import PurePath

from msgloom.contracts import Limitation, VersionRef
from msgloom.preparation import (
    DocumentFormat,
    DocumentLocation,
    LinkBlock,
    ParserOutput,
    SourceMapping,
    TableBlock,
    TextBlock,
)
from msgloom.sources import CollectedAttachment, CollectedRecord, ContentKind

_EXTENSION_FORMATS = {
    ".doc": DocumentFormat.DOC,
    ".docx": DocumentFormat.DOCX,
    ".ods": DocumentFormat.ODS,
    ".pdf": DocumentFormat.PDF,
    ".xls": DocumentFormat.XLS,
    ".xlsb": DocumentFormat.XLSB,
    ".xlsm": DocumentFormat.XLSM,
    ".xlsx": DocumentFormat.XLSX,
}
_MIME_FORMATS = {
    "application/pdf": DocumentFormat.PDF,
    "application/msword": DocumentFormat.DOC,
    "application/vnd.ms-excel": DocumentFormat.XLS,
    "application/vnd.ms-excel.sheet.binary.macroenabled.12": DocumentFormat.XLSB,
    "application/vnd.ms-excel.sheet.macroenabled.12": DocumentFormat.XLSM,
    "application/vnd.oasis.opendocument.spreadsheet": DocumentFormat.ODS,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentFormat.XLSX,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentFormat.DOCX,
}


def format_for_kind(kind: ContentKind) -> DocumentFormat | None:
    """Map an explicit collected representation to a parser format."""
    return {
        ContentKind.PLAIN: DocumentFormat.TEXT,
        ContentKind.HTML: DocumentFormat.HTML,
        ContentKind.MIME: DocumentFormat.MIME,
        ContentKind.JSON: DocumentFormat.JSON,
    }.get(kind)


def attachment_format(item: CollectedAttachment) -> DocumentFormat | None:
    """Resolve a supported attachment format without trusting source code."""
    direct = format_for_kind(item.content_kind)
    if direct is not None:
        return direct
    mime = (item.content_type or "").split(";", 1)[0].strip().lower()
    if mime in _MIME_FORMATS:
        return _MIME_FORMATS[mime]
    suffix = PurePath(item.name or "").suffix.lower()
    return _EXTENSION_FORMATS.get(suffix)


def metadata_json(record: CollectedRecord) -> str:
    """Retain contextual collected metadata as deterministic structured text."""
    value = {
        "semantic_identity": record.semantic_identity,
        "observed_at": record.observed_at.isoformat(),
        "source_scope": {
            "kind": record.source_scope.kind,
            "identity": record.source_scope.identity,
            "version": record.source_scope.version,
        },
        "metadata": [
            {"name": item.name, "value": item.value} for item in record.metadata
        ],
    }
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def readable_text(output: ParserOutput) -> str | None:
    """Return ordered parser text while retaining tables separately."""
    texts = [block.text for block in output.blocks if isinstance(block, TextBlock)]
    return "\n".join(texts) if texts else None


def parser_limitations(output: ParserOutput) -> tuple[Limitation, ...]:
    """Translate parser gaps into public preparation limitations."""
    return tuple(
        Limitation(f"parser-{item.code}", item.detail) for item in output.limitations
    )


def parsed_mappings(
    owner: VersionRef,
    parsed_index: int,
    output: ParserOutput,
) -> tuple[SourceMapping, ...]:
    """Create mappings accepted by the triage evidence resolver."""
    mappings: list[SourceMapping] = []
    for block_index, block in enumerate(output.blocks):
        field = f"parsed_contents[{parsed_index}].blocks[{block_index}]"
        if isinstance(block, TextBlock):
            mappings.append(
                SourceMapping(source=owner, field=field, location=block.location)
            )
        elif isinstance(block, TableBlock):
            mappings.append(
                SourceMapping(source=owner, field=field, location=block.table.location)
            )
            for cell_index, cell in enumerate(block.table.cells):
                if cell.text is not None:
                    mappings.append(
                        SourceMapping(
                            source=owner,
                            field=f"{field}.table.cells[{cell_index}]",
                            location=cell.location,
                        )
                    )
        elif isinstance(block, LinkBlock):
            continue
    return tuple(mappings)


def primary_mapping(
    source: VersionRef,
    field: str,
    location: object,
) -> SourceMapping | None:
    """Map subject/body only when the accepted resolver can consume it."""
    if not isinstance(location, DocumentLocation):
        return None
    return SourceMapping(source=source, field=field, location=location)
