"""Synchronous bytes-only parser for native Word preparation."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from msgloom.preparation import (
    DocumentFormat,
    LimitationKind,
    LinkBlock,
    ParserLimitation,
    ParserOutput,
    ParserProvenance,
    ParserRequest,
    TableBlock,
    TextBlock,
)
from msgloom.preparation.parsers.word_extract import extract_docx
from msgloom.preparation.parsers.word_package import validate_docx_package

PARSER_NAME = "msgloom.word"
PARSER_VERSION = "1"
BACKEND = "python-docx-1.2.0+lxml-6.1.3"
SUPPORTED_PROFILE = "word-native-v1"


def _validate_request(request: ParserRequest) -> None:
    expected = (PARSER_NAME, PARSER_VERSION, BACKEND)
    actual = (request.parser.name, request.parser.version, request.parser.backend)
    if actual != expected:
        raise ValueError(
            "Word parser identity does not match the registered implementation"
        )
    if request.config.profile != SUPPORTED_PROFILE:
        raise ValueError("unsupported Word parser profile")
    if request.config.settings:
        raise ValueError("Word parser profile does not accept settings")


def _verify_saved_bytes(request: ParserRequest, content: bytes) -> None:
    if request.source.byte_count != len(content):
        raise ValueError("content byte_count does not match saved-byte provenance")
    if request.source.sha256.lower() != sha256(content).hexdigest():
        raise ValueError("content sha256 does not match saved-byte provenance")


def _text_size(value: str | None) -> int:
    return len(value.encode("utf-8")) if value is not None else 0


def _output_size(output: ParserOutput) -> int:
    total = 0
    for block in output.blocks:
        if isinstance(block, TextBlock):
            total += _text_size(block.text)
            total += sum(
                _text_size(link.target) + _text_size(link.text) for link in block.links
            )
        elif isinstance(block, TableBlock):
            for cell in block.table.cells:
                total += _text_size(cell.text) + _text_size(cell.merged_range)
                total += sum(
                    _text_size(link.target) + _text_size(link.text)
                    for link in cell.links
                )
        elif isinstance(block, LinkBlock):
            total += _text_size(block.link.target) + _text_size(block.link.text)
    for limitation in output.limitations:
        total += _text_size(limitation.code)
        total += _text_size(limitation.detail)
        total += _text_size(limitation.feature)
    return total


def _bounded_output(request: ParserRequest, output: ParserOutput) -> ParserOutput:
    if _output_size(output) > request.limits.output_bytes:
        raise ValueError("Word parser output byte limit exceeded")
    return output


def _unsupported_doc(request: ParserRequest) -> ParserOutput:
    return ParserOutput(
        provenance=ParserProvenance.from_request(request),
        limitations=(
            ParserLimitation(
                kind=LimitationKind.UNSUPPORTED,
                code="legacy-doc-unsupported",
                detail=(
                    "No legacy DOC conversion profile is qualified; the saved "
                    "bytes were not parsed and no conversion process was launched."
                ),
                feature="legacy-doc",
            ),
        ),
    )


def parse(request: ParserRequest, content: bytes) -> ParserOutput:
    """
    Parse already-saved Word bytes without filesystem or network discovery.

    DOCX is validated as a bounded ZIP/XML package before python-docx sees it.
    Hyperlink relationships are retained only as inert data. Legacy DOC returns
    an explicit unsupported result because no conversion profile is qualified.
    Process wall-time and memory ceilings remain the responsibility of the
    isolated worker boundary.
    """
    _validate_request(request)
    _verify_saved_bytes(request, content)
    if request.detected_format is DocumentFormat.DOC:
        return _bounded_output(request, _unsupported_doc(request))
    if request.detected_format is not DocumentFormat.DOCX:
        raise ValueError("Word parser accepts only DOCX or DOC detected formats")

    scan = validate_docx_package(content, request.limits)
    try:
        document = Document(BytesIO(content))
    except (PackageNotFoundError, KeyError, ValueError) as exc:
        raise ValueError("malformed or inconsistent DOCX package") from exc

    blocks, limitations = extract_docx(document, scan)
    output = ParserOutput(
        provenance=ParserProvenance.from_request(request),
        blocks=blocks,
        limitations=limitations,
    )
    return _bounded_output(request, output)
