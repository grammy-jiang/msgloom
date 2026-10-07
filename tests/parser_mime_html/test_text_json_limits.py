"""Plain-text, JSON, closed-format, and resource-limit regressions."""

from __future__ import annotations

import pytest

from msgloom.preparation.contracts import (
    DocumentFormat,
    ParserIdentity,
    ParserRequest,
    TextBlock,
)
from msgloom.preparation.parsers.mime_html import (
    BACKEND,
    PARSER_NAME,
    PARSER_VERSION,
    parse,
)
from tests.parser_mime_html.conftest import parser_request


def test_text_is_strict_utf8_and_empty_input_is_visible() -> None:
    """Text parsing is mechanical UTF-8 decoding with explicit gaps."""
    valid = "Unicode café 世界".encode()
    output = parse(parser_request(valid, DocumentFormat.TEXT), valid)
    if len(output.blocks) != 1 or not isinstance(output.blocks[0], TextBlock):
        pytest.fail("Expected one text block")
    if output.blocks[0].text != "Unicode café 世界":
        pytest.fail("Expected exact Unicode text")

    invalid = b"broken \xff"
    invalid_output = parse(parser_request(invalid, DocumentFormat.TEXT), invalid)
    if invalid_output.blocks:
        pytest.fail("Invalid UTF-8 must not produce text")
    if "invalid-utf8" not in {x.code for x in invalid_output.limitations}:
        pytest.fail("Expected invalid UTF-8 limitation")

    empty = b""
    empty_output = parse(parser_request(empty, DocumentFormat.TEXT), empty)
    if "empty-content" not in {x.code for x in empty_output.limitations}:
        pytest.fail("Expected explicit empty-content limitation")


def test_json_validates_but_preserves_exact_structure_order_and_numbers() -> None:
    """JSON remains source JSON text rather than an inferred provider schema."""
    content = rb'{"z":1.00,"a":[3,{"nested":-2.5e+3}],"text":"caf\u00e9"}'
    output = parse(parser_request(content, DocumentFormat.JSON), content)
    if len(output.blocks) != 1 or not isinstance(output.blocks[0], TextBlock):
        pytest.fail("Expected one validated JSON text block")
    if output.blocks[0].text != content.decode("utf-8"):
        pytest.fail("JSON representation must preserve exact order and numbers")

    invalid = b'{"a": 1,, "secret": "body"}'
    invalid_output = parse(parser_request(invalid, DocumentFormat.JSON), invalid)
    if invalid_output.blocks:
        pytest.fail("Invalid JSON must not produce a semantic block")
    codes = {x.code for x in invalid_output.limitations}
    if "invalid-json" not in codes:
        pytest.fail("Expected invalid JSON limitation")
    details = " ".join(x.detail for x in invalid_output.limitations)
    if "secret" in details or "body" in details:
        pytest.fail("Invalid JSON details must not echo source content")


def test_closed_format_and_parser_identity_are_enforced() -> None:
    """This implementation cannot be selected for another parser family."""
    content = b"plain"
    unsupported = parser_request(content, DocumentFormat.PDF)
    with pytest.raises(ValueError, match="unsupported format"):
        parse(unsupported, content)

    request = parser_request(content, DocumentFormat.TEXT)
    wrong = ParserRequest(
        source=request.source,
        detected_format=request.detected_format,
        parser=ParserIdentity(
            name="other.parser",
            version=PARSER_VERSION,
            backend=BACKEND,
        ),
        config=request.config,
        limits=request.limits,
    )
    with pytest.raises(ValueError, match="parser identity"):
        parse(wrong, content)

    if (PARSER_NAME, PARSER_VERSION, BACKEND) != (
        "msgloom.mime-html",
        "1",
        "stdlib-email+selectolax-0.4.12",
    ):
        pytest.fail("Parser identity constants changed unexpectedly")


def test_decoded_and_output_limits_stop_readable_content() -> None:
    """Decoded-byte and semantic-output ceilings fail closed with limitations."""
    content = b"abcdefghij"
    decoded = parse(
        parser_request(
            content,
            DocumentFormat.TEXT,
            decompressed_bytes=5,
        ),
        content,
    )
    if decoded.blocks:
        pytest.fail("Decoded-byte limit must stop text extraction")
    if "decoded-bytes-limit" not in {x.code for x in decoded.limitations}:
        pytest.fail("Expected decoded-byte limit")

    output = parse(
        parser_request(
            content,
            DocumentFormat.TEXT,
            output_bytes=5,
        ),
        content,
    )
    if output.blocks:
        pytest.fail("Output-byte limit must stop oversized semantic text")
    if "output-bytes-limit" not in {x.code for x in output.limitations}:
        pytest.fail("Expected output-byte limit")


def test_json_rejects_nonstandard_constants() -> None:
    """NaN and Infinity are not accepted as standard JSON numbers."""
    for content in (b'{"n": NaN}', b'{"n": Infinity}'):
        output = parse(parser_request(content, DocumentFormat.JSON), content)
        if "invalid-json" not in {x.code for x in output.limitations}:
            pytest.fail("Expected non-standard JSON constant to be rejected")


def test_parser_configuration_is_closed_and_explicit() -> None:
    """Unknown profiles and settings cannot silently change parser semantics."""
    content = b"plain"
    request = parser_request(content, DocumentFormat.TEXT)

    unknown_profile = ParserRequest(
        source=request.source,
        detected_format=request.detected_format,
        parser=request.parser,
        config=type(request.config)(profile="unknown-profile"),
        limits=request.limits,
    )
    with pytest.raises(ValueError, match="unsupported MIME/HTML parser profile"):
        parse(unknown_profile, content)

    unknown_setting = ParserRequest(
        source=request.source,
        detected_format=request.detected_format,
        parser=request.parser,
        config=type(request.config)(
            profile="mime-html-v1",
            settings=(("mystery", "enabled"),),
        ),
        limits=request.limits,
    )
    with pytest.raises(ValueError, match="unsupported MIME/HTML parser setting"):
        parse(unknown_setting, content)


def test_html_low_member_and_output_limits_remain_safe() -> None:
    """HTML fixes still fail closed under structural and semantic ceilings."""
    content = b"<p>alpha<br>beta</p><p>gamma</p>"
    member_limited = parse(
        parser_request(content, DocumentFormat.HTML, container_members=2),
        content,
    )
    if "container-member-limit" not in {
        item.code for item in member_limited.limitations
    }:
        pytest.fail("Expected HTML structural member limitation")

    output_limited = parse(
        parser_request(content, DocumentFormat.HTML, output_bytes=4),
        content,
    )
    if output_limited.blocks:
        pytest.fail("Low output limit must not emit oversized HTML text")
    if "output-bytes-limit" not in {item.code for item in output_limited.limitations}:
        pytest.fail("Expected HTML output-byte limitation")
