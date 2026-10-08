"""Closed MIME, HTML, UTF-8 text, and JSON parser implementation."""

from __future__ import annotations

import json

from msgloom.preparation.contracts import (
    BlockRole,
    DocumentFormat,
    DocumentLocation,
    LimitationKind,
    ParserOutput,
    ParserProvenance,
    ParserRequest,
)
from msgloom.preparation.parsers.mime_html_html import extract_html
from msgloom.preparation.parsers.mime_html_limits import ExtractionState
from msgloom.preparation.parsers.mime_html_mime import extract_mime

PARSER_NAME = "msgloom.mime-html"
PARSER_VERSION = "1"
BACKEND = "stdlib-email+selectolax-0.4.13"
SUPPORTED_PROFILES = frozenset({"mime-html-v1"})
SUPPORTED_SETTINGS = frozenset[str]()

_ALLOWED_FORMATS = frozenset(
    {
        DocumentFormat.MIME,
        DocumentFormat.HTML,
        DocumentFormat.TEXT,
        DocumentFormat.JSON,
    }
)


def _validate_request(request: ParserRequest) -> None:
    """Reject routing, identity, or configuration drift."""
    if request.detected_format not in _ALLOWED_FORMATS:
        raise ValueError(
            f"unsupported format for {PARSER_NAME}: {request.detected_format.value}"
        )
    parser = request.parser
    if (
        parser.name != PARSER_NAME
        or parser.version != PARSER_VERSION
        or parser.backend != BACKEND
    ):
        raise ValueError("parser identity does not match the MIME/HTML registry entry")
    if request.config.profile not in SUPPORTED_PROFILES:
        raise ValueError("unsupported MIME/HTML parser profile")
    if any(key not in SUPPORTED_SETTINGS for key, _ in request.config.settings):
        raise ValueError("unsupported MIME/HTML parser setting")


def _decode_utf8(
    content: bytes,
    state: ExtractionState,
    *,
    location: DocumentLocation,
) -> str | None:
    """Decode direct HTML, text, or JSON bytes strictly as UTF-8."""
    if not state.consume_decoded(len(content), location=location):
        return None
    try:
        return content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        state.add_limitation(
            LimitationKind.UNSUPPORTED,
            "invalid-utf8",
            "Input bytes are not valid UTF-8 for this detected format.",
            feature="encoding",
            location=location,
        )
        return None


def _reject_json_constant(value: str) -> None:
    """Reject non-standard JSON constants without retaining their value."""
    raise ValueError("non-standard JSON constant")


def _parse_text(
    content: bytes,
    state: ExtractionState,
    *,
    part_name: str,
) -> None:
    """Decode exact UTF-8 text without semantic inference."""
    location = DocumentLocation(part=part_name, block_index=0)
    text = _decode_utf8(content, state, location=location)
    if text is None:
        return
    if not text:
        state.add_limitation(
            LimitationKind.MISSING,
            "empty-content",
            "Input contained no readable text.",
            feature="text",
            location=location,
        )
        return
    state.add_text(BlockRole.TEXT, text, location)


def _parse_json(content: bytes, state: ExtractionState) -> None:
    """Validate JSON while retaining its exact decoded representation."""
    location = DocumentLocation(part="json", block_index=0)
    text = _decode_utf8(content, state, location=location)
    if text is None:
        return
    if not text:
        state.add_limitation(
            LimitationKind.MISSING,
            "empty-content",
            "Input contained no JSON document.",
            feature="json",
            location=location,
        )
        return
    try:
        json.loads(text, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, RecursionError, ValueError):
        state.add_limitation(
            LimitationKind.PARTIAL,
            "invalid-json",
            "Input was not a valid standard JSON document.",
            feature="json",
            location=location,
        )
        return
    state.add_text(BlockRole.TEXT, text, location)


def _parse_html(content: bytes, state: ExtractionState) -> None:
    """Decode UTF-8 HTML and run local Lexbor structural extraction."""
    location = DocumentLocation(part="html", block_index=0)
    text = _decode_utf8(content, state, location=location)
    if text is None:
        return
    if not text:
        state.add_limitation(
            LimitationKind.MISSING,
            "empty-content",
            "Input contained no HTML content.",
            feature="html",
            location=location,
        )
        return
    extract_html(text, state, part_name="html")


def parse(request: ParserRequest, content: bytes) -> ParserOutput:
    """
    Parse one saved source payload synchronously inside the isolated worker.

    The caller owns saved-byte hash/count verification, process limits, output
    codec validation, persistence, and stage completion. This function performs
    no file, network, provider, database, or environment access.
    """
    if not isinstance(content, bytes):
        raise TypeError("parser content must be bytes")
    _validate_request(request)
    state = ExtractionState(request.limits)

    if request.detected_format is DocumentFormat.MIME:
        extract_mime(content, state)
    elif request.detected_format is DocumentFormat.HTML:
        _parse_html(content, state)
    elif request.detected_format is DocumentFormat.TEXT:
        _parse_text(content, state, part_name="text")
    else:
        _parse_json(content, state)

    return ParserOutput(
        provenance=ParserProvenance.from_request(request),
        blocks=tuple(state.blocks),
        mime_parts=tuple(state.mime_parts),
        limitations=tuple(state.limitations),
    )
