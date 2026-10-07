"""MIME relationship, decoding, and attachment regressions."""

from __future__ import annotations

from email.message import EmailMessage
from typing import cast

import pytest

from msgloom.preparation.contracts import (
    DocumentFormat,
    MimePartLocation,
    TextBlock,
)
from msgloom.preparation.parsers.mime_html import parse
from tests.parser_mime_html.conftest import parser_request


def _complex_mime() -> bytes:
    message = EmailMessage()
    message["Subject"] = "Synthetic"
    message.set_content("Plain café.", charset="utf-8")
    message.add_alternative(
        '<p>HTML <a href="https://example.invalid/ref">reference</a>.</p>',
        subtype="html",
        charset="utf-8",
    )
    alternatives = cast(list[EmailMessage], message.get_payload())
    html_part = alternatives[1]
    html_part.add_related(
        b"not-a-real-image",
        maintype="image",
        subtype="png",
        cid="<synthetic-image>",
        disposition="inline",
    )
    message.add_attachment(
        b"binary attachment body",
        maintype="application",
        subtype="octet-stream",
        filename="synthetic.bin",
    )
    return message.as_bytes()


def test_mime_preserves_stable_tree_and_skips_binary_body() -> None:
    """Mixed, alternative, and related parts retain stable tree metadata."""
    content = _complex_mime()
    output = parse(parser_request(content, DocumentFormat.MIME), content)

    expected = (
        ("1", None, "multipart/mixed"),
        ("1.1", "1", "multipart/alternative"),
        ("1.1.1", "1.1", "text/plain"),
        ("1.1.2", "1.1", "multipart/related"),
        ("1.1.2.1", "1.1.2", "text/html"),
        ("1.1.2.2", "1.1.2", "image/png"),
        ("1.2", "1", "application/octet-stream"),
    )
    actual = tuple(
        (part.part_ref, part.parent_ref, part.content_type)
        for part in output.mime_parts
    )
    if actual != expected:
        pytest.fail(f"Unexpected MIME tree: {actual!r}")

    text = "\n".join(
        block.text for block in output.blocks if isinstance(block, TextBlock)
    )
    if "Plain café." not in text or "HTML reference." not in text:
        pytest.fail("Expected independently extracted plain and HTML alternatives")
    if "binary attachment body" in text or "not-a-real-image" in text:
        pytest.fail("Binary MIME payloads must not become readable body text")

    codes = {item.code for item in output.limitations}
    for code in (
        "mime-alternative-not-resolved",
        "mime-embedded-content-skipped",
        "mime-attachment-not-extracted",
    ):
        if code not in codes:
            pytest.fail(f"Expected explicit MIME limitation {code}")


def test_mime_provenance_is_exact_request_identity() -> None:
    """The worker output copies request provenance without reinterpretation."""
    content = b"Content-Type: text/plain; charset=utf-8\r\n\r\nhello"
    request = parser_request(content, DocumentFormat.MIME)
    output = parse(request, content)
    if output.provenance.source != request.source:
        pytest.fail("Expected exact source provenance")
    if output.provenance.parser != request.parser:
        pytest.fail("Expected exact parser provenance")
    if output.provenance.config != request.config:
        pytest.fail("Expected exact parser configuration provenance")
    if output.provenance.detected_format is not DocumentFormat.MIME:
        pytest.fail("Expected exact detected-format provenance")


@pytest.mark.parametrize(
    ("content", "expected_code"),
    [
        (
            (
                b"Content-Type: text/plain; charset=x-msgloom-unknown\r\n"
                b"Content-Transfer-Encoding: 8bit\r\n\r\nsecret-body"
            ),
            "mime-unsupported-charset",
        ),
        (
            (
                b"Content-Type: text/plain; charset=utf-8\r\n"
                b"Content-Transfer-Encoding: base64\r\n\r\n%%%"
            ),
            "mime-decoding-defect",
        ),
    ],
)
def test_mime_decoding_failures_are_safe_limitations(
    content: bytes,
    expected_code: str,
) -> None:
    """Charset and transfer defects are visible without echoing source bodies."""
    output = parse(parser_request(content, DocumentFormat.MIME), content)
    codes = {item.code for item in output.limitations}
    if expected_code not in codes:
        pytest.fail(f"Expected safe decoding limitation {expected_code}")
    details = " ".join(item.detail for item in output.limitations)
    if "secret-body" in details or "%%%" in details:
        pytest.fail("Limitation detail must not echo source bodies")


def test_mime_member_limit_stops_tree_expansion() -> None:
    """Container-member ceilings produce partial output instead of overrun."""
    content = _complex_mime()
    request = parser_request(
        content,
        DocumentFormat.MIME,
        container_members=3,
    )
    output = parse(request, content)
    if len(output.mime_parts) > 3:
        pytest.fail("MIME parser exceeded the container member limit")
    if "container-member-limit" not in {x.code for x in output.limitations}:
        pytest.fail("Expected explicit member-limit limitation")


def test_mime_locations_are_parser_local_and_stable() -> None:
    """Readable MIME body blocks retain parser-local part references."""
    content = b"Content-Type: text/plain; charset=utf-8\r\n\r\nhello"
    output = parse(parser_request(content, DocumentFormat.MIME), content)
    if len(output.blocks) != 1:
        pytest.fail("Expected one plain-text body block")
    block = output.blocks[0]
    if not isinstance(block, TextBlock):
        pytest.fail("Expected a text block")
    if not isinstance(block.location, MimePartLocation):
        pytest.fail("Expected MIME part source mapping")
    if block.location.part_ref != "1":
        pytest.fail("Expected root MIME part reference 1")


def test_attached_message_subtree_is_metadata_only() -> None:
    """Attached message/rfc822 descendants remain metadata, not body text."""
    outer = EmailMessage()
    outer.set_content("MAIN BODY")
    attached = EmailMessage()
    attached.set_content("ATTACHED MESSAGE BODY")
    outer.add_attachment(attached)
    content = outer.as_bytes()

    output = parse(parser_request(content, DocumentFormat.MIME), content)
    text = "\n".join(
        block.text for block in output.blocks if isinstance(block, TextBlock)
    )
    if "MAIN BODY" not in text or "ATTACHED MESSAGE BODY" in text:
        pytest.fail("Attached message body must not enter readable body output")
    types = tuple(part.content_type for part in output.mime_parts)
    if "message/rfc822" not in types or "text/plain" not in types:
        pytest.fail("Attached message subtree relationships must remain metadata")
    if "mime-attachment-not-extracted" not in {
        item.code for item in output.limitations
    }:
        pytest.fail("Expected attachment coverage limitation")


def test_multipart_attachment_descendants_are_metadata_only() -> None:
    """A multipart attachment retains children but suppresses their text."""
    outer = EmailMessage()
    outer.set_content("VISIBLE")
    attached = EmailMessage()
    attached.make_mixed()
    child = EmailMessage()
    child.set_content("HIDDEN CHILD")
    attached.attach(child)
    attached["Content-Disposition"] = "attachment"
    outer.make_mixed()
    outer.attach(attached)
    content = outer.as_bytes()

    output = parse(parser_request(content, DocumentFormat.MIME), content)
    text = "\n".join(
        block.text for block in output.blocks if isinstance(block, TextBlock)
    )
    if "VISIBLE" not in text or "HIDDEN CHILD" in text:
        pytest.fail("Multipart attachment descendants must remain metadata-only")
    if len(output.mime_parts) < 4:
        pytest.fail("Expected multipart attachment descendants in MIME metadata")


def test_malformed_multipart_shape_is_explicit_and_safe() -> None:
    """Malformed multipart source exposes generic structural coverage gaps."""
    content = (
        b"Content-Type: multipart/mixed; boundary=missing\r\n"
        b"MIME-Version: 1.0\r\n\r\n"
        b"https://provider.invalid/private-body"
    )
    output = parse(parser_request(content, DocumentFormat.MIME), content)
    codes = {item.code for item in output.limitations}
    if not ({"mime-parser-defect", "mime-embedded-content-skipped"} <= codes):
        pytest.fail(f"Expected malformed multipart limitations, got {codes!r}")
    details = " ".join(item.detail for item in output.limitations)
    if "provider.invalid" in details or "private-body" in details:
        pytest.fail("Malformed MIME limitation details must not echo source")
