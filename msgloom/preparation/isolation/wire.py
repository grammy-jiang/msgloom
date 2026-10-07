"""Strict bounded JSON wire format for the parser process boundary."""

from __future__ import annotations

import json
from typing import Any

from msgloom.preparation.contracts import (
    BlockRole,
    CellLocation,
    DocumentFormat,
    DocumentLocation,
    LimitationKind,
    LinkBlock,
    MimePartLocation,
    MimePartReference,
    PageLocation,
    ParsedBlock,
    ParsedCell,
    ParsedLink,
    ParsedTable,
    ParserConfig,
    ParserIdentity,
    ParserLimitation,
    ParserOutput,
    ParserProvenance,
    SavedByteReference,
    SheetLocation,
    SourceLocation,
    TableBlock,
    TextBlock,
)

type JsonObject = dict[str, Any]


def _unique_object(pairs: list[tuple[str, Any]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _loads(payload: bytes) -> Any:
    try:
        return json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid parser JSON payload") from exc


def _dumps(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _object(value: object, keys: set[str]) -> JsonObject:
    if not isinstance(value, dict):
        raise TypeError("wire value must be an object")
    if set(value) != keys:
        raise ValueError("wire object fields do not match schema")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("wire text value must be a string")
    return value


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _text(value)


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("wire integer value must be an integer")
    return value


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("wire numeric value must be a number")
    return float(value)


def _array(value: object) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError("wire collection must be an array")
    return value


def _source(value: object) -> SavedByteReference:
    data = _object(value, {"reference", "sha256", "byte_count"})
    return SavedByteReference(
        reference=_text(data["reference"]),
        sha256=_text(data["sha256"]),
        byte_count=_integer(data["byte_count"]),
    )


def _identity(value: object) -> ParserIdentity:
    data = _object(value, {"name", "version", "backend"})
    return ParserIdentity(
        name=_text(data["name"]),
        version=_text(data["version"]),
        backend=_optional_text(data["backend"]),
    )


def _config(value: object) -> ParserConfig:
    data = _object(value, {"profile", "settings"})
    settings: list[tuple[str, str]] = []
    for item in _array(data["settings"]):
        pair = _array(item)
        if len(pair) != 2:
            raise ValueError("parser setting must have two values")
        settings.append((_text(pair[0]), _text(pair[1])))
    return ParserConfig(profile=_text(data["profile"]), settings=tuple(settings))


def _encode_location(location: object) -> JsonObject:
    if isinstance(location, PageLocation):
        return {"type": "page", "page_number": location.page_number}
    if isinstance(location, SheetLocation):
        return {"type": "sheet", "sheet_name": location.sheet_name}
    if isinstance(location, CellLocation):
        return {
            "type": "cell",
            "sheet_name": location.sheet_name,
            "row": location.row,
            "column": location.column,
            "coordinate": location.coordinate,
        }
    if isinstance(location, DocumentLocation):
        return {
            "type": "document",
            "part": location.part,
            "block_index": location.block_index,
        }
    if isinstance(location, MimePartLocation):
        return {"type": "mime", "part_ref": location.part_ref}
    raise TypeError("unsupported source location")


def _decode_location(value: object) -> SourceLocation:
    if not isinstance(value, dict) or not isinstance(value.get("type"), str):
        raise TypeError("source location must be a tagged object")
    tag = value["type"]
    if tag == "page":
        data = _object(value, {"type", "page_number"})
        return PageLocation(page_number=_integer(data["page_number"]))
    if tag == "sheet":
        data = _object(value, {"type", "sheet_name"})
        return SheetLocation(sheet_name=_text(data["sheet_name"]))
    if tag == "cell":
        data = _object(value, {"type", "sheet_name", "row", "column", "coordinate"})
        return CellLocation(
            sheet_name=_text(data["sheet_name"]),
            row=_integer(data["row"]),
            column=_integer(data["column"]),
            coordinate=_text(data["coordinate"]),
        )
    if tag == "document":
        data = _object(value, {"type", "part", "block_index"})
        index = data["block_index"]
        return DocumentLocation(
            part=_text(data["part"]),
            block_index=None if index is None else _integer(index),
        )
    if tag == "mime":
        data = _object(value, {"type", "part_ref"})
        return MimePartLocation(part_ref=_text(data["part_ref"]))
    raise ValueError("unknown source location tag")


def _encode_link(link: ParsedLink) -> JsonObject:
    return {
        "target": link.target,
        "text": link.text,
        "location": None if link.location is None else _encode_location(link.location),
    }


def _decode_link(value: object) -> ParsedLink:
    data = _object(value, {"target", "text", "location"})
    location = data["location"]
    return ParsedLink(
        target=_text(data["target"]),
        text=_optional_text(data["text"]),
        location=None if location is None else _decode_location(location),
    )


def _encode_cell(cell: ParsedCell) -> JsonObject:
    return {
        "row_index": cell.row_index,
        "column_index": cell.column_index,
        "text": cell.text,
        "value_type": cell.value_type,
        "location": _encode_location(cell.location),
        "formula": cell.formula,
        "cached_value": cell.cached_value,
        "merged_range": cell.merged_range,
        "links": [_encode_link(link) for link in cell.links],
    }


def _decode_cell(value: object) -> ParsedCell:
    data = _object(
        value,
        {
            "row_index",
            "column_index",
            "text",
            "value_type",
            "location",
            "formula",
            "cached_value",
            "merged_range",
            "links",
        },
    )
    return ParsedCell(
        row_index=_integer(data["row_index"]),
        column_index=_integer(data["column_index"]),
        text=_optional_text(data["text"]),
        value_type=_optional_text(data["value_type"]),
        location=_decode_location(data["location"]),
        formula=_optional_text(data["formula"]),
        cached_value=_optional_text(data["cached_value"]),
        merged_range=_optional_text(data["merged_range"]),
        links=tuple(_decode_link(item) for item in _array(data["links"])),
    )


def _encode_table(table: ParsedTable) -> JsonObject:
    return {
        "row_count": table.row_count,
        "column_count": table.column_count,
        "cells": [_encode_cell(cell) for cell in table.cells],
        "location": _encode_location(table.location),
    }


def _decode_table(value: object) -> ParsedTable:
    data = _object(value, {"row_count", "column_count", "cells", "location"})
    return ParsedTable(
        row_count=_integer(data["row_count"]),
        column_count=_integer(data["column_count"]),
        cells=tuple(_decode_cell(item) for item in _array(data["cells"])),
        location=_decode_location(data["location"]),
    )


def _encode_block(block: object) -> JsonObject:
    if isinstance(block, TextBlock):
        return {
            "type": "text",
            "order": block.order,
            "role": block.role.value,
            "text": block.text,
            "location": _encode_location(block.location),
            "links": [_encode_link(link) for link in block.links],
        }
    if isinstance(block, TableBlock):
        return {
            "type": "table",
            "order": block.order,
            "table": _encode_table(block.table),
        }
    if isinstance(block, LinkBlock):
        return {
            "type": "link",
            "order": block.order,
            "link": _encode_link(block.link),
        }
    raise TypeError("unsupported parsed block")


def _decode_block(value: object) -> ParsedBlock:
    if not isinstance(value, dict) or not isinstance(value.get("type"), str):
        raise TypeError("parsed block must be a tagged object")
    tag = value["type"]
    if tag == "text":
        data = _object(value, {"type", "order", "role", "text", "location", "links"})
        return TextBlock(
            order=_integer(data["order"]),
            role=BlockRole(_text(data["role"])),
            text=_text(data["text"]),
            location=_decode_location(data["location"]),
            links=tuple(_decode_link(item) for item in _array(data["links"])),
        )
    if tag == "table":
        data = _object(value, {"type", "order", "table"})
        return TableBlock(
            order=_integer(data["order"]),
            table=_decode_table(data["table"]),
        )
    if tag == "link":
        data = _object(value, {"type", "order", "link"})
        return LinkBlock(
            order=_integer(data["order"]),
            link=_decode_link(data["link"]),
        )
    raise ValueError("unknown parsed block tag")


def _encode_provenance(provenance: ParserProvenance) -> JsonObject:
    return {
        "source": {
            "reference": provenance.source.reference,
            "sha256": provenance.source.sha256,
            "byte_count": provenance.source.byte_count,
        },
        "detected_format": provenance.detected_format.value,
        "parser": {
            "name": provenance.parser.name,
            "version": provenance.parser.version,
            "backend": provenance.parser.backend,
        },
        "config": {
            "profile": provenance.config.profile,
            "settings": [list(item) for item in provenance.config.settings],
        },
    }


def _decode_provenance(value: object) -> ParserProvenance:
    data = _object(value, {"source", "detected_format", "parser", "config"})
    return ParserProvenance(
        source=_source(data["source"]),
        detected_format=DocumentFormat(_text(data["detected_format"])),
        parser=_identity(data["parser"]),
        config=_config(data["config"]),
    )


def encode_output(output: ParserOutput) -> bytes:
    """Encode parser output with explicit tags for every union member."""
    return _dumps(
        {
            "provenance": _encode_provenance(output.provenance),
            "blocks": [_encode_block(block) for block in output.blocks],
            "mime_parts": [
                {
                    "part_ref": part.part_ref,
                    "parent_ref": part.parent_ref,
                    "content_type": part.content_type,
                    "disposition": part.disposition,
                    "content_id": part.content_id,
                    "location": _encode_location(part.location),
                }
                for part in output.mime_parts
            ],
            "limitations": [
                {
                    "kind": item.kind.value,
                    "code": item.code,
                    "detail": item.detail,
                    "feature": item.feature,
                    "location": (
                        None
                        if item.location is None
                        else _encode_location(item.location)
                    ),
                }
                for item in output.limitations
            ],
        }
    )


def decode_output(payload: bytes) -> ParserOutput:
    """Decode output, rejecting unknown fields, tags, and coercions."""
    data = _object(
        _loads(payload),
        {"provenance", "blocks", "mime_parts", "limitations"},
    )
    mime_parts: list[MimePartReference] = []
    for value in _array(data["mime_parts"]):
        part = _object(
            value,
            {
                "part_ref",
                "parent_ref",
                "content_type",
                "disposition",
                "content_id",
                "location",
            },
        )
        location = _decode_location(part["location"])
        if not isinstance(location, MimePartLocation):
            raise TypeError("MIME part location must be a MIME location")
        mime_parts.append(
            MimePartReference(
                part_ref=_text(part["part_ref"]),
                parent_ref=_optional_text(part["parent_ref"]),
                content_type=_text(part["content_type"]),
                disposition=_optional_text(part["disposition"]),
                content_id=_optional_text(part["content_id"]),
                location=location,
            )
        )
    limitations: list[ParserLimitation] = []
    for value in _array(data["limitations"]):
        item = _object(value, {"kind", "code", "detail", "feature", "location"})
        location = item["location"]
        limitations.append(
            ParserLimitation(
                kind=LimitationKind(_text(item["kind"])),
                code=_text(item["code"]),
                detail=_text(item["detail"]),
                feature=_optional_text(item["feature"]),
                location=None if location is None else _decode_location(location),
            )
        )
    return ParserOutput(
        provenance=_decode_provenance(data["provenance"]),
        blocks=tuple(_decode_block(item) for item in _array(data["blocks"])),
        mime_parts=tuple(mime_parts),
        limitations=tuple(limitations),
    )
